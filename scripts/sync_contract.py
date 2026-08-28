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


def resolve_ref(contract: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a local JSON pointer such as `#/components/schemas/Foo`."""
    if not ref.startswith("#/"):
        raise ValueError(f"Only local schema references are supported: {ref}")
    node: Any = contract
    for segment in ref[2:].split("/"):
        segment = segment.replace("~1", "/").replace("~0", "~")
        node = node[segment]
    if not isinstance(node, dict):
        raise ValueError(f"Schema reference did not resolve to an object: {ref}")
    return node


def json_type_label(schema: dict[str, Any]) -> str:
    """A compact, agent-readable type for one request field."""
    declared = schema.get("type")
    if isinstance(declared, list):
        # OpenAPI 3.1 nullable fields arrive as ["string", "null"].
        concrete = [entry for entry in declared if entry != "null"]
        declared = concrete[0] if concrete else "null"
    if declared is None:
        if "enum" in schema:
            declared = "string"
        elif "properties" in schema:
            declared = "object"
        else:
            return "value"
    if declared == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            return f"{json_type_label(items)}[]"
        return "array"
    return str(declared)


def body_fields(contract: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any] | None:
    """
    Flatten an operation's JSON request body into the field list an agent needs
    before it can make a valid call.

    Without this, `<domain> help` shows only path parameters, so every write is
    a guess and the server answers with 422. Only the top level is described;
    nested object shapes stay the contract's job.
    """
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None

    schema = ((request_body.get("content") or {}).get("application/json") or {}).get("schema")
    if not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        schema = resolve_ref(contract, schema["$ref"])

    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None

    required = [name for name in schema.get("required", []) if name in properties]
    fields = {}
    for name, property_schema in properties.items():
        if isinstance(property_schema, dict) and "$ref" in property_schema:
            property_schema = resolve_ref(contract, property_schema["$ref"])
        if not isinstance(property_schema, dict):
            property_schema = {}
        field: dict[str, Any] = {"type": json_type_label(property_schema)}
        if "enum" in property_schema:
            field["enum"] = property_schema["enum"]
        for constraint in ("minimum", "maximum", "minLength", "maxLength"):
            if constraint in property_schema:
                field[constraint] = property_schema[constraint]
        description = property_schema.get("description")
        if isinstance(description, str) and description.strip():
            field["description"] = description.strip()
        fields[name] = field

    example = ((request_body.get("content") or {}).get("application/json") or {}).get("example")

    metadata: dict[str, Any] = {
        "required": required,
        "fields": dict(sorted(fields.items())),
        "body_required": bool(request_body.get("required", False)),
    }
    if isinstance(example, (dict, list)):
        metadata["example"] = example
    return metadata


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
                "body": body_fields(contract, operation),
                "method": method.upper(),
                "operation_id": operation_id,
                "path": path,
                "query_parameters": [
                    parameter["name"]
                    for parameter in operation.get("parameters", [])
                    if parameter.get("in") == "query"
                ],
                "summary": (operation.get("summary") or "").strip() or None,
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


def compose_skill(canonical: str, addendum: str) -> str:
    """
    The shared skill body has one author: Main's
    `resources/agent-skills/subscribr-api/SKILL.md`. This package appends only
    its CLI-specific section.

    Both repositories used to author the whole file, and they drifted — the
    domain, the Video error codes, and the MCP wording all disagreed depending
    on whether an agent installed from npm or fetched the hosted copy.
    """
    body = canonical.rstrip("\n")
    extra = addendum.strip("\n")
    if not extra:
        return body + "\n"
    return f"{body}\n\n{extra}\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--skill",
        type=Path,
        required=True,
        help="Main's canonical resources/agent-skills/subscribr-api/SKILL.md",
    )
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
    skill_path = ROOT / "skills/subscribr-api/SKILL.md"
    # Build input, not a shipped file: it must not sit next to SKILL.md where
    # an agent reading the skill directory would treat it as guidance.
    addendum_path = ROOT / "scripts/cli-addendum.md"

    validate_manifest(contract, manifest)
    assert isinstance(source_sha256, str)

    skill_path.write_text(
        compose_skill(
            args.skill.read_text(encoding="utf-8"),
            addendum_path.read_text(encoding="utf-8") if addendum_path.is_file() else "",
        ),
        encoding="utf-8",
    )
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
