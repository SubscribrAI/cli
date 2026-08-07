#!/usr/bin/env python3
"""Regenerate CLI contract artifacts from Main's canonical OpenAPI output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    "skills/subscribr-api/SKILL.md",
    "skills/subscribr-api/references/endpoints.md",
    "skills/subscribr-api/references/operations.json",
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def operation_metadata(
    contract: dict[str, Any],
    source_sha256: str,
    required_operation_ids: list[str] | None = None,
) -> dict[str, Any]:
    operations: dict[str, dict[str, Any]] = {}
    discovered_operation_ids: list[str] = []

    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue

            operation_id = operation["operationId"]
            command = operation["x-cli-command"]
            group = operation["x-skill-group"]
            key = f"{group}.{command}"
            if key in operations:
                raise ValueError(f"Duplicate CLI command metadata: {key}")

            operations[key] = {
                "abilities": operation.get("x-required-abilities", []),
                "method": method.upper(),
                "operation_id": operation_id,
                "path": path,
                "query_parameters": [
                    parameter["name"]
                    for parameter in operation.get("parameters", [])
                    if parameter.get("in") == "query"
                ],
                "write_safety": (
                    dict(sorted(operation["x-write-safety"].items()))
                    if operation.get("x-write-safety") is not None
                    else None
                ),
            }
            discovered_operation_ids.append(operation_id)

    return {
        "_generated": "DO NOT EDIT: generated from openapi/subscribr-v1.json",
        "base_url": contract["servers"][0]["url"],
        "contract_version": contract["info"]["version"],
        "manifest_version": contract["x-subscribr-operation-manifest-version"],
        "operations": dict(sorted(operations.items())),
        "required_operation_ids": required_operation_ids or discovered_operation_ids,
        "source_sha256": source_sha256,
        "supported_contract_range": f"^{contract['info']['version']}",
    }


def validate_manifest(
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    source_sha256 = manifest.get("source_sha256")
    if (
        not isinstance(source_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None
    ):
        raise ValueError("Operation manifest does not contain a valid canonical source hash")
    if manifest.get("contract_version") != contract["info"]["version"]:
        raise ValueError("Operation manifest contract version does not match the OpenAPI contract")
    if manifest.get("manifest_version") != contract["x-subscribr-operation-manifest-version"]:
        raise ValueError("Operation manifest version does not match the OpenAPI contract")

    generated = operation_metadata(contract, source_sha256)
    manifest_operations = manifest.get("operations", [])
    if not isinstance(manifest_operations, list):
        raise ValueError("Operation manifest operations must be a list")

    expected = {
        operation["operation_id"]: {
            "abilities": operation["abilities"],
            "method": operation["method"],
            "path": operation["path"],
        }
        for operation in manifest_operations
    }
    actual = {
        operation["operation_id"]: {
            "abilities": operation["abilities"],
            "method": operation["method"],
            "path": operation["path"],
        }
        for operation in generated["operations"].values()
    }
    if (
        len(expected) != len(manifest_operations)
        or len(actual) != len(generated["operations"])
        or expected != actual
    ):
        raise ValueError("Operation manifest routes do not exactly match the OpenAPI contract")


def endpoint_reference(contract: dict[str, Any]) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue

            groups.setdefault(operation["x-skill-group"], []).append(
                {
                    "abilities": operation.get("x-required-abilities", []),
                    "method": method.upper(),
                    "operation_id": operation["operationId"],
                    "path": path,
                    "write_safety": operation.get("x-write-safety"),
                }
            )

    lines = [
        "# Subscribr API Operations",
        "",
        "<!-- Generated from openapi/subscribr-v1.json. Do not edit. -->",
        "",
        "Subscribr Video public operations use `/api/v1/video/...` as capability slices ship. Intel video lookup/search remains available for YouTube research.",
        "",
    ]
    for group, operations in sorted(groups.items()):
        lines.extend([
            f"## {group.replace('-', ' ').title()}",
            "",
            "| Method | Path | Operation | Abilities | Safety |",
            "|---|---|---|---|---|",
        ])
        for operation in operations:
            abilities = ", ".join(f"`{ability}`" for ability in operation["abilities"])
            write_safety = operation["write_safety"]
            safety = "read" if write_safety is None else (
                f"idempotency={write_safety['idempotency']}; "
                f"concurrency={write_safety['concurrency']}"
            )
            lines.append(
                f"| `{operation['method']}` | `{operation['path']}` | "
                f"`{operation['operation_id']}` | {abilities} | {safety} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.openapi.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    # Main's checksum also covers its runtime-hydrated Voice Profile schema, so
    # the generated manifest is the checksum authority. Exact route signature
    # validation below binds that manifest to the supplied OpenAPI contract.
    source_sha256 = manifest.get("source_sha256")
    operations_path = ROOT / "skills/subscribr-api/references/operations.json"
    endpoints_path = ROOT / "skills/subscribr-api/references/endpoints.md"
    provenance_path = ROOT / "skills/subscribr-api/references/provenance.json"

    validate_manifest(contract, manifest)
    assert isinstance(source_sha256, str)
    write_json(
        operations_path,
        operation_metadata(
            contract,
            source_sha256,
            [operation["operation_id"] for operation in manifest["operations"]],
        ),
    )
    endpoints_path.write_text(endpoint_reference(contract), encoding="utf-8")
    write_json(provenance_path, {
        "contract_version": contract["info"]["version"],
        "manifest_version": contract["x-subscribr-operation-manifest-version"],
        "source_sha256": source_sha256,
        "artifacts": {relative: sha256(ROOT / relative) for relative in ARTIFACTS},
    })


if __name__ == "__main__":
    main()
