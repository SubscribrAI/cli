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
    "CLI-REFERENCE.md",
    "bin/install.js",
    "bin/subscribr.js",
    "package.json",
    "plugin.json",
    "skills/subscribr-api/SKILL.md",
    "skills/subscribr-api/references/endpoints.md",
    "skills/subscribr-api/references/operations.json",
    "skills/subscribr-api/references/provenance.json",
    "subscribr.py",
}
# Hosts a shipped file may name. `subscribr.com` is deliberately absent and
# deliberately banned below: it is a parked third-party domain, and this
# allowlist blessing it is why it reached customers twice.
ALLOWED_URL_HOSTS = {
    "agent-plugins.org",
    "github.com",
    "subscribr.ai",
    # README badges and the npm package page they link to.
    "img.shields.io",
    "www.npmjs.com",
    # Documentation examples inside generated request-body samples.
    "example.com",
    "partner.example.com",
    "youtube.com",
    "www.youtube.com",
}
BANNED_URL_HOSTS = {"subscribr.com", "www.subscribr.com"}
# The Video slice has five shapes and each one is fail-closed against drift:
# a read (GET, `video:read`, no write safety); a staging/discard write
# (non-GET, `video:edit`, idempotency AND concurrency both required); the
# single publish write (`videoApplyRevision`, `video:publish`, same write
# safety as an edit write); a quote (`videoQuoteVideo`, `video:generate`,
# idempotency AND concurrency both unsupported — it spends nothing and there
# is nothing to retry into); and a generation write (`videoCreateVideo`,
# `videoCancelVideo`, `video:generate`, idempotency required but concurrency
# unsupported — there is no revision to conflict with). A new operation that
# matches none of these shapes — or one that moves between them — must fail
# this check loudly rather than pass unnoticed.
VIDEO_PUBLISH_OPERATIONS = {"videoApplyRevision"}
VIDEO_QUOTE_OPERATIONS = {"videoQuoteVideo"}
VIDEO_GENERATE_WRITE_OPERATIONS = {"videoCreateVideo", "videoCancelVideo"}
VIDEO_EDIT_WRITE_SAFETY = {"idempotency": "required", "concurrency": "required", "retry": "same-key"}
VIDEO_QUOTE_WRITE_SAFETY = {"idempotency": "unsupported", "concurrency": "unsupported", "retry": "never"}
VIDEO_GENERATE_WRITE_SAFETY = {"idempotency": "required", "concurrency": "unsupported", "retry": "same-key"}
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

    declared = {"package.json", "plugin.json", "LICENSE", "README.md", "CLI-REFERENCE.md", "subscribr.py"}
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
            host = urlparse(raw_url.rstrip(".,;:)]}`")).hostname
            if host in BANNED_URL_HOSTS:
                fail(
                    f"banned URL host {host!r} in {relative}: we do not control it, "
                    "and a token sent there is a leaked credential. Use subscribr.ai."
                )
            if host not in ALLOWED_URL_HOSTS:
                fail(f"unapproved URL host {host!r} in {relative}")

    plugin = json.loads((ROOT / "plugin.json").read_text())
    if plugin.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        fail("plugin manifest must target Agent Plugins 1.0.0")
    if plugin.get("name") != "subscribr-cli" or plugin.get("version") != package["version"]:
        fail("plugin manifest identity must match the published package")

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
    if not video_operations:
        fail("operation metadata is missing the public Video operation surface")
    for named, label in (
        (VIDEO_PUBLISH_OPERATIONS, "videoApplyRevision"),
        (VIDEO_QUOTE_OPERATIONS, "videoQuoteVideo"),
        (VIDEO_GENERATE_WRITE_OPERATIONS, "videoCreateVideo/videoCancelVideo"),
    ):
        if named - set(video_operations):
            fail(f"operation metadata is missing {label}")

    for operation_id, operation in video_operations.items():
        if operation["method"] == "GET":
            if operation["abilities"] != ["video:read"] or operation["write_safety"] is not None:
                fail(f"public Video read {operation_id} must require only video:read and carry no write safety")
            continue

        if operation_id in VIDEO_QUOTE_OPERATIONS:
            if operation["abilities"] != ["video:generate"] or operation["write_safety"] != VIDEO_QUOTE_WRITE_SAFETY:
                fail(f"{operation_id} must require video:generate with idempotency and concurrency both unsupported")
            continue

        if operation_id in VIDEO_GENERATE_WRITE_OPERATIONS:
            if operation["abilities"] != ["video:generate"] or operation["write_safety"] != VIDEO_GENERATE_WRITE_SAFETY:
                fail(f"{operation_id} must require video:generate with idempotency required and concurrency unsupported")
            continue

        if operation["write_safety"] != VIDEO_EDIT_WRITE_SAFETY:
            fail(f"public Video write {operation_id} must require both idempotency and concurrency")

        if operation_id in VIDEO_PUBLISH_OPERATIONS:
            if operation["abilities"] != ["video:publish"]:
                fail(f"{operation_id} must require video:publish")
        elif operation["abilities"] != ["video:edit"]:
            fail(f"public Video write {operation_id} must require video:edit")

    print(f"package verification passed: {len(EXPECTED_PACKAGE_FILES)} allowlisted files, {len(operation_ids)} operations, provenance current")


if __name__ == "__main__":
    main()
