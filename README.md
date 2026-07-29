# Subscribr CLI

Zero-dependency Python transport wrapper and agent skill for the canonical [Subscribr Customer API](https://subscribr.com/youtube-api).

The CLI route map is generated from Subscribr's OpenAPI contract. It includes Projects board management, scripts and Agent Mode cancellation, ideas, asynchronous operation polling, Team token CRUD, Intel research, templates, strict voice validation/commit, thumbnails, notifications, tasks, and webhooks. Domain rules remain server-owned.

## Install

```bash
npm install --global @giltotherescue/subscribr-cli
export SUBSCRIBR_API_TOKEN=sk_live_...
subscribr help
```

Create a Team-bound token at <https://subscribr.com/developer>. Override the production server for local or staging conformance with `SUBSCRIBR_API_BASE_URL`.

Both `subscribr` and `subscribr-cli` launch the API CLI. To install the bundled agent skill into the current project:

```bash
subscribr-install-skill
```

The installer atomically replaces its own `subscribr-api` skill directories so removed generated references do not linger. To install the optional self-contained Python CLI bundle, use `subscribr-install-skill --with-cli`. It creates `./.subscribr-cli/` with `subscribr.py` and its generated operation metadata; run `python3 .subscribr-cli/subscribr.py help`. Use `--cli-dir tools/subscribr-cli` to choose another bundle directory and `--force` only when you intend to replace an existing bundle.

## Examples

```bash
subscribr team get-team
subscribr team list-api-tokens
subscribr channels list-channels
subscribr projects list-projects --channel-id 42
subscribr projects move-project --project project:v1:idea:7 \
  --stage scripting --idempotency-key move-7-1 --if-match '"project-r3"'
subscribr scripts cancel-script-agent-run --script 93 --run 18 \
  --idempotency-key cancel-18-1
subscribr templates create-template --channel 42 \
  --body '{"name":"Explainer","prompt":"Write a structured explainer..."}' \
  --idempotency-key template-1
subscribr voices validate-voice-profile --channel 42 --body @voice.json
```

Path parameters are shown by `<domain> help`. Other flags become query parameters for reads or JSON fields for writes. `--body` accepts a JSON object/array; `--idempotency-key` and `--if-match` become transport headers. JSON results go to stdout; errors go to stderr with stable exit classes.

Exit codes: `2` authentication/authorization, `3` validation/not found, `4` revision/conflict, `5` rate limiting, `6` transient server/network failure, and `64` CLI usage.

The CLI retries reads and idempotency-keyed writes only. A retry uses the identical payload and key. Poll a returned operation with `subscribr operations get-operation --operation <uuid>`; `Ctrl-C` never silently cancels server work.

## Contract and provenance

- `skills/subscribr-api/references/operations.json` — generated route/ability/safety metadata
- `skills/subscribr-api/references/endpoints.md` — generated endpoint appendix
- `skills/subscribr-api/references/provenance.json` — immutable artifact digests
- `skills/subscribr-api/SKILL.md` — authored workflow guidance

YouTube research remains available through the Intel video operations. Subscribr Video is Subscribr's video-production surface; its public Main API commands will be added only when the canonical `/api/v1/video/...` OpenAPI operations ship. Until then, this CLI deliberately has no Video discovery, configuration, quote, render, artifact, cancellation, or revision command. The generic operation endpoint only polls an operation ID already returned by a public API operation.

## Development

```bash
npm test
npm pack --dry-run
python3 scripts/verify_package.py
```

The package intentionally uses only the Python and Node standard libraries.
