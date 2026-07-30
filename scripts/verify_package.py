#!/usr/bin/env python3
"""Fail closed on CLI package drift, unsafe contents, or provenance mismatch."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACKAGE_FILES = {
    "LICENSE",
    "README.md",
    "bin/install.js",
    "bin/subscribr.js",
    "package.json",
    "skills/subscribr-api/SKILL.md",
    "skills/subscribr-api/references/endpoints.md",
    "skills/subscribr-api/references/operations.json",
    "skills/subscribr-api/references/provenance.json",
    "subscribr.py",
}
ALLOWED_URL_HOSTS = {"subscribr.com", "github.com"}
VIDEO_READ_OPERATIONS = {
    "videoGetAvatar",
    "videoGetChannel",
    "videoGetMediaAsset",
    "videoGetVoice",
    "videoListAvatars",
    "videoListCapabilities",
    "videoListChannels",
    "videoListMediaAssets",
    "videoListVoices",
}
SECRET = re.compile(r"(?:sk_live_|sk_test_|ghp_|github_pat_)[A-Za-z0-9_-]{16,}")
URL = re.compile(r"https?://[^\s<>\"'`]+")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    print(f"package verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    package = json.loads((ROOT / "package.json").read_text())
    cli = (ROOT / "subscribr.py").read_text()
    if f'VERSION = "{package["version"]}"' not in cli:
        fail("package and CLI versions differ")

    provenance = json.loads((ROOT / "skills/subscribr-api/references/provenance.json").read_text())
    operations = json.loads((ROOT / "skills/subscribr-api/references/operations.json").read_text())
    if provenance["source_sha256"] != operations["source_sha256"]:
        fail("OpenAPI source provenance differs")
    for relative, expected in provenance["artifacts"].items():
        if sha256(ROOT / relative) != expected:
            fail(f"artifact digest differs: {relative}")

    declared = {"package.json", "LICENSE", "README.md", "subscribr.py"}
    for entry in package["files"]:
        if entry.endswith("/"):
            declared.update(str(path.relative_to(ROOT)) for path in (ROOT / entry).rglob("*") if path.is_file())
    if declared != EXPECTED_PACKAGE_FILES:
        fail(f"package allowlist differs: {sorted(declared ^ EXPECTED_PACKAGE_FILES)}")

    for relative in EXPECTED_PACKAGE_FILES:
        path = ROOT / relative
        if path.is_symlink():
            fail(f"symlink is not allowed: {relative}")
        normalized = Path(os.path.normpath(relative))
        if normalized.is_absolute() or ".." in normalized.parts:
            fail(f"unsafe path: {relative}")
        mode = stat.S_IMODE(path.stat().st_mode)
        expected_mode = 0o755 if relative in {"subscribr.py", "bin/install.js", "bin/subscribr.js"} else 0o644
        if mode != expected_mode:
            fail(f"unexpected mode {oct(mode)} for {relative}")
        if SECRET.search(path.read_text(errors="ignore")):
            fail(f"possible secret in {relative}")
        for raw_url in URL.findall(path.read_text(errors="ignore")):
            host = urlparse(raw_url.rstrip(".,;:)]}")).hostname
            if host not in ALLOWED_URL_HOSTS:
                fail(f"unapproved URL host {host!r} in {relative}")

    operation_ids = {operation["operation_id"] for operation in operations["operations"].values()}
    required_operation_ids = set(operations["required_operation_ids"])
    if not operation_ids or operation_ids != required_operation_ids:
        fail("operation metadata does not exactly cover the canonical required operation IDs")
    if "getOperation" not in operation_ids:
        fail("operation metadata is missing the public getOperation polling route")
    video_operations = {
        operation["operation_id"]: operation
        for key, operation in operations["operations"].items()
        if key.startswith("video.")
    }
    if set(video_operations) != VIDEO_READ_OPERATIONS:
        fail("operation metadata does not contain exactly the nine public Video reads")
    if any(
        operation["method"] != "GET"
        or operation["abilities"] != ["video:read"]
        or operation["write_safety"] is not None
        for operation in video_operations.values()
    ):
        fail("public Video operations must remain read-only and require video:read")

    print(f"package verification passed: 10 allowlisted files, {len(operation_ids)} operations, provenance current")


if __name__ == "__main__":
    main()
