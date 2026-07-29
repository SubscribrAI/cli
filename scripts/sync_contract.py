#!/usr/bin/env python3
"""Regenerate CLI contract artifacts from Main's canonical OpenAPI output."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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


def operation_metadata(contract: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    operations: dict[str, dict[str, Any]] = {}
    required_operation_ids: list[str] = []

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
                "write_safety": operation.get("x-write-safety"),
            }
            required_operation_ids.append(operation_id)

    return {
        "_generated": "DO NOT EDIT: generated from openapi/subscribr-v1.json",
        "base_url": contract["servers"][0]["url"],
        "contract_version": contract["info"]["version"],
        "manifest_version": contract["x-subscribr-operation-manifest-version"],
        "operations": dict(sorted(operations.items())),
        "required_operation_ids": required_operation_ids,
        "source_sha256": source_sha256,
        "supported_contract_range": f"^{contract['info']['version']}",
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", type=Path, required=True)
    parser.add_argument("--endpoints", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.openapi.read_text(encoding="utf-8"))
    source_sha256 = sha256(args.openapi)
    operations_path = ROOT / "skills/subscribr-api/references/operations.json"
    endpoints_path = ROOT / "skills/subscribr-api/references/endpoints.md"
    provenance_path = ROOT / "skills/subscribr-api/references/provenance.json"

    write_json(operations_path, operation_metadata(contract, source_sha256))
    shutil.copyfile(args.endpoints, endpoints_path)
    write_json(provenance_path, {
        "contract_version": contract["info"]["version"],
        "manifest_version": contract["x-subscribr-operation-manifest-version"],
        "source_sha256": source_sha256,
        "artifacts": {relative: sha256(ROOT / relative) for relative in ARTIFACTS},
    })


if __name__ == "__main__":
    main()
