#!/usr/bin/env python3
"""Zero-dependency CLI transport for the canonical Subscribr Customer API."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

VERSION = "2.0.0"
METADATA_PATH = Path(__file__).resolve().parent / "skills" / "subscribr-api" / "references" / "operations.json"
BODY_METHODS = {"POST", "PUT", "PATCH"}
EXIT_AUTH = 2
EXIT_VALIDATION = 3
EXIT_CONFLICT = 4
EXIT_RATE_LIMIT = 5
EXIT_TRANSIENT = 6
EXIT_USAGE = 64


def load_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    if not isinstance(metadata.get("operations"), dict):
        raise RuntimeError("CLI operation metadata is invalid.")
    return metadata


METADATA = load_metadata()
ROUTES = METADATA["operations"]

# Compatibility aliases preserve the original concise commands while route
# authority remains entirely in generated metadata.
ALIASES = {
    "team.get": "team.get-team",
    "team.get-credits": "team.get-team-credits",
    "scripts.agent-generate": "scripts.start-script-agent-run",
    "scripts.agent-poll": "scripts.get-script-agent-run",
    "scripts.agent-cancel": "scripts.cancel-script-agent-run",
}


class CliError(Exception):
    def __init__(self, message: str, exit_code: int = 1, detail: Any = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.detail = detail


def api_base() -> str:
    return os.environ.get("SUBSCRIBR_API_BASE_URL", METADATA["base_url"]).rstrip("/")


def get_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    token = os.environ.get("SUBSCRIBR_API_TOKEN")
    if not token:
        raise CliError(
            "SUBSCRIBR_API_TOKEN is not set. Create a Team-bound token at https://subscribr.com/developer.",
            EXIT_AUTH,
        )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"subscribr-cli/{VERSION}",
    }
    headers.update(extra or {})
    return headers


def status_exit_code(status: int) -> int:
    if status in (401, 403):
        return EXIT_AUTH
    if status in (400, 404, 405, 422):
        return EXIT_VALIDATION
    if status in (409, 412):
        return EXIT_CONFLICT
    if status == 429:
        return EXIT_RATE_LIMIT
    if status >= 500:
        return EXIT_TRANSIENT
    return 1


def retryable(method: str, headers: dict[str, str]) -> bool:
    return method in {"GET", "HEAD", "OPTIONS"} or "Idempotency-Key" in headers


def request(
    method: str,
    path: str,
    body: Any = None,
    extra_headers: dict[str, str] | None = None,
    max_attempts: int = 3,
) -> Any:
    headers = get_headers(extra_headers)
    data = json.dumps(body).encode("utf-8") if body is not None else (b"{}" if method in BODY_METHODS else None)
    req = urllib.request.Request(api_base() + path, data=data, headers=headers, method=method)
    can_retry = retryable(method, headers)

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {"status": "ok", "http_code": response.status}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                detail = raw
            if can_retry and error.code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                delay = min(float(retry_after), 5.0) if retry_after and retry_after.isdigit() else min(0.25 * (2 ** (attempt - 1)), 2.0)
                time.sleep(delay)
                continue
            raise CliError(f"HTTP {error.code}", status_exit_code(error.code), detail) from error
        except urllib.error.URLError as error:
            if can_retry and attempt < max_attempts:
                time.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
                continue
            raise CliError("Subscribr API is temporarily unreachable.", EXIT_TRANSIENT, str(error.reason)) from error

    raise CliError("Subscribr API request failed.", EXIT_TRANSIENT)


def extract_path_params(template: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", template)


def try_json_parse(value: str) -> Any:
    if value.startswith(("{", "[", '"')) or value in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", value):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
    return value


def parse_extra_args(args: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    index = 0
    while index < len(args):
        argument = args[index]
        if not argument.startswith("--"):
            raise CliError(f"Unexpected argument: {argument}", EXIT_USAGE)
        key = argument[2:].replace("-", "_")
        if index + 1 < len(args) and not args[index + 1].startswith("--"):
            result[key] = try_json_parse(args[index + 1])
            index += 2
        else:
            result[key] = True
            index += 1
    return result


def resolve_route(domain: str, action: str) -> tuple[str, dict[str, Any]]:
    key = f"{domain}.{action}"
    key = ALIASES.get(key, key)
    if key not in ROUTES:
        raise CliError(f"Unknown command: {domain}.{action}", EXIT_USAGE)
    return key, ROUTES[key]


def build_request(route: dict[str, Any], arguments: dict[str, Any]) -> tuple[str, str, Any, dict[str, str]]:
    method = route["method"]
    path = route["path"]
    arguments = dict(arguments)
    raw_body = arguments.pop("body", None)
    if isinstance(raw_body, str) and raw_body.startswith("@"):
        try:
            with Path(raw_body[1:]).open(encoding="utf-8") as handle:
                raw_body = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise CliError(f"Unable to read JSON body file: {error}", EXIT_USAGE) from error
    headers: dict[str, str] = {}
    for argument, header in (("idempotency_key", "Idempotency-Key"), ("if_match", "If-Match")):
        value = arguments.pop(argument, None)
        if value is not None:
            headers[header] = str(value)

    write_safety = route.get("write_safety") or {}
    idempotency = write_safety.get("idempotency")
    concurrency = write_safety.get("concurrency")
    if idempotency == "required" and "Idempotency-Key" not in headers:
        raise CliError("This operation requires --idempotency-key.", EXIT_USAGE)
    if idempotency == "unsupported" and "Idempotency-Key" in headers:
        raise CliError("This operation does not support --idempotency-key.", EXIT_USAGE)
    if concurrency == "required" and "If-Match" not in headers:
        raise CliError("This operation requires --if-match with the current strong ETag.", EXIT_USAGE)
    if concurrency == "unsupported" and "If-Match" in headers:
        raise CliError("This operation does not support --if-match.", EXIT_USAGE)

    for parameter in extract_path_params(path):
        if parameter not in arguments:
            raise CliError(f"Missing required path param: --{parameter.replace('_', '-')}", EXIT_USAGE)
        path = path.replace(f"{{{parameter}}}", urllib.parse.quote(str(arguments.pop(parameter)), safe=""))

    if raw_body is not None and method not in BODY_METHODS:
        raise CliError("--body is only supported for POST, PUT, and PATCH operations.", EXIT_USAGE)
    if raw_body is not None and not isinstance(raw_body, (dict, list)):
        raise CliError("--body must be a JSON object or array.", EXIT_USAGE)
    if raw_body is not None:
        if arguments:
            fields = ", ".join(f"--{key.replace('_', '-')}" for key in sorted(arguments))
            raise CliError(f"--body cannot be combined with request fields ({fields}) for this operation.", EXIT_USAGE)
        body = raw_body
    elif method in BODY_METHODS:
        body = arguments or None
    else:
        body = None
        if arguments:
            path += "?" + urllib.parse.urlencode(arguments, doseq=True)
    return method, path, body, headers


def split_transport_options(args: list[str]) -> tuple[list[str], bool]:
    wait = False
    remaining: list[str] = []
    for argument in args:
        if argument == "--wait":
            wait = True
            continue
        remaining.append(argument)
    return remaining, wait


def print_domains() -> None:
    domains = sorted({key.split(".", 1)[0] for key in ROUTES})
    print("Subscribr CLI — canonical API domains:\n")
    for domain in domains:
        count = sum(key.startswith(domain + ".") for key in ROUTES)
        print(f"  {domain:16s} ({count} actions)")
    print(f"\nTotal: {len(ROUTES)} operations (contract {METADATA['contract_version']})")
    print("\nUsage: subscribr <domain> <action> [--key value ...]")


def print_domain_help(domain: str) -> None:
    actions = {key: value for key, value in ROUTES.items() if key.startswith(domain + ".")}
    if not actions:
        raise CliError(f"Unknown domain: {domain}", EXIT_USAGE)
    print(f"Subscribr CLI — {domain} actions:\n")
    for key, route in sorted(actions.items()):
        action = key.split(".", 1)[1]
        required = " ".join(f"--{name.replace('_', '-')} <value>" for name in extract_path_params(route["path"]))
        print(f"  {action:34s} {route['method']:6s} {route['path']}")
        if required:
            print(f"  {'':34s} required: {required}")


def run(args: list[str]) -> int:
    if not args or args[0] in ("help", "--help", "-h"):
        print_domains()
        return 0
    if args[0] in ("version", "--version", "-V"):
        print(VERSION)
        return 0
    domain = args[0]
    if len(args) < 2 or args[1] in ("help", "--help", "-h"):
        print_domain_help(domain)
        return 0
    _, route = resolve_route(domain, args[1])
    command_args, wait = split_transport_options(args[2:])
    if wait:
        raise CliError(
            "Automatic waiting is unavailable. Poll with `operations get-operation --operation <uuid>` instead.",
            EXIT_USAGE,
        )
    method, path, body, headers = build_request(route, parse_extra_args(command_args))
    print(json.dumps(request(method, path, body, headers), indent=2, ensure_ascii=False))
    return 0


def main() -> None:
    try:
        raise SystemExit(run(sys.argv[1:]))
    except KeyboardInterrupt:
        print("Waiting stopped locally; no server-side operation was cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except CliError as error:
        payload = {"error": True, "message": str(error)}
        if error.detail is not None:
            payload["detail"] = error.detail
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(error.exit_code)


if __name__ == "__main__":
    main()
