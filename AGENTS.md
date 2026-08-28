# AGENTS.md

Instructions for an AI agent working on this repository's own code. If you are an agent trying to *use* the Subscribr API on a user's behalf, read [`skills/subscribr-api/SKILL.md`](skills/subscribr-api/SKILL.md) instead — this file is for people, and agents, changing this CLI itself.

## What this repo is

A zero-dependency npm package (`@subscribrai/cli`): a Python CLI (`subscribr.py`) for the Subscribr Customer API, an Agent Skill (`skills/subscribr-api/`), and a small Node installer (`bin/`). See [README.md](README.md) for what it does, and [CLI-REFERENCE.md](CLI-REFERENCE.md) for how it works.

## Setup and commands

```bash
npm test                        # Python unittest suite + Node install tests
python3 scripts/verify_package.py   # package allowlist, file modes, provenance digests
npm pack --dry-run               # confirm the actual tarball contents
```

Run all three before proposing a change is done. `npm publish` runs `npm test` and `verify_package.py` automatically via `prepack`, so a broken check blocks publishing, not just this repo's CI.

## The one rule that matters most

**Never hand-edit anything under `skills/subscribr-api/`.** Every file there — `SKILL.md`, `references/operations.json`, `references/endpoints.md`, `references/provenance.json` — is generated from Subscribr's OpenAPI contract in the Main app repository, and carries a digest in `provenance.json` that `verify_package.py` checks. A hand edit will be silently overwritten by the next regeneration, or fail verification first.

To change anything in that directory, edit the source in Main and regenerate:

```bash
python3 scripts/sync_contract.py \
  --openapi  ../subscribr/openapi/subscribr-v1.json \
  --manifest ../subscribr/resources/generated/api-operation-manifest.json \
  --skill    ../subscribr/resources/agent-skills/subscribr-api/SKILL.md
```

`scripts/cli-addendum.md` is the one exception: it's this package's own content, appended to Main's canonical `SKILL.md` body during regeneration. Edit it directly for CLI-specific guidance.

## Releasing

Follow [RELEASING.md](RELEASING.md). Two steps need a human: `npm publish` asks for a one-time password in a browser, and `main` requires a passing CI check before a merge.

## Other invariants tests enforce

- `package.json`, `plugin.json`, and the `VERSION` constant in `subscribr.py` must agree. `test_declared_versions_stay_in_lockstep` checks this.
- `README.md` must document every currently-shipped `video` action, and must not imply that unshipped Subscribr Video operations (quote, render, cancel, and so on) exist. `test_authored_docs_define_the_video_slice_and_its_boundaries` checks this against the literal command list.
- `scripts/verify_package.py`'s `EXPECTED_PACKAGE_FILES` must match `package.json`'s `files` field exactly, file mode included (`0o755` for the three executables, `0o644` for everything else). Adding a shipped file means updating both.
- Nothing in the package may reference `subscribr.com` — it's a parked third-party domain, not ours. Only `subscribr.ai` is a valid base URL.

## Style

Match the existing code and docs: no unnecessary abstraction, no comments that just restate the code, plain language in user-facing text. This package intentionally has zero runtime dependencies — don't add one.
