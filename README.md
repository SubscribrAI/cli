# Subscribr CLI

Zero-dependency Python transport wrapper and agent skill for the canonical [Subscribr Customer API](https://subscribr.com/youtube-api).

The CLI route map is generated from Subscribr's OpenAPI contract. It includes Projects board management, scripts and Agent Mode cancellation, ideas, asynchronous operation polling, Team token CRUD, Intel research, templates, strict voice validation/commit, thumbnails, notifications, tasks, webhooks, and the current Subscribr Video read surface. Domain rules remain server-owned.

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
subscribr video list-capabilities
subscribr video list-channels
subscribr video get-channel --video-channel stch_01hz3k9pb1z7c5m2r6n0y4x2a2
subscribr video list-voices --page 1 --per-page 20
subscribr video get-voice --voice 820e8400-e29b-41d4-a716-446655440003
subscribr video list-avatars --page 1 --per-page 20
subscribr video get-avatar --avatar 820e8400-e29b-41d4-a716-446655440002
subscribr video list-media-assets --page 1 --per-page 20
subscribr video get-media-asset --media-asset 820e8400-e29b-41d4-a716-446655440006
```

Path parameters are shown by `<domain> help`. Other flags become query parameters for reads or JSON fields for writes. `--body` accepts a JSON object/array; `--idempotency-key` and `--if-match` become transport headers. JSON results go to stdout; errors go to stderr with stable exit classes.

Exit codes: `2` authentication/authorization, `3` validation/not found, `4` revision/conflict, `5` rate limiting, `6` transient server/network failure, and `64` CLI usage.

The CLI retries reads and idempotency-keyed writes only. Non-idempotent writes are never retried automatically. For eligible retries, `Retry-After` is honored as either seconds or an HTTP date. Delays above five seconds are returned to the caller instead of making the CLI wait, and the CLI never retries before a valid requested delay. A write retry uses the identical payload and idempotency key. Poll a returned operation with `subscribr operations get-operation --operation <uuid>`; `Ctrl-C` never silently cancels server work.

## Contract and provenance

- `skills/subscribr-api/references/operations.json` — generated route/ability/safety metadata
- `skills/subscribr-api/references/endpoints.md` — generated endpoint appendix
- `skills/subscribr-api/references/provenance.json` — immutable artifact digests
- `skills/subscribr-api/SKILL.md` — authored workflow guidance

### Subscribr Video availability

The `video` domain currently exposes exactly nine read operations: capability discovery; Channel list/detail; custom voice list/detail; custom avatar list/detail; and reference media list/detail. They all require `video:read` on the Team-bound API token (API key).

This slice is default-off. A Team without read access receives the typed `video_capability_unavailable` error; a Team that has not connected Subscribr Video receives `video_provisioning_required`. Do not retry either response as an unclassified network failure. Asset reads are owner/admin-only until Channel-scoped asset authorization ships. Channel reads retain the server's Team and Channel visibility rules.

Subscribr Video quote, project, render, cancellation, artifact, and revision writes are not shipped in this CLI slice. Do not infer them from product nouns or from the generic operation poller. `operations get-operation` only polls an operation ID returned by an already-shipped public operation.

YouTube research remains available separately through the Intel video operations.

## Agent Plugin and MCP

This npm package is also an [Agent Plugins](https://agent-plugins.org/) 1.0.0 package. Its portable `plugin.json` identifies the package and its `skills/subscribr-api/` directory contains the Agent Skill. The bundled `subscribr` executable is the primary surface for deterministic API automation: it covers the complete public Customer API contract with explicit idempotency, concurrency, retry, and polling behavior.

Subscribr's hosted MCP server is complementary rather than a CLI wrapper. Use `https://subscribr.ai/mcp/subscribr` for conversational, OAuth-capable clients that need the curated Projects, workspace, and Intel workflows. This package intentionally does not declare that remote MCP server in `mcp.json`: Agent Plugins 1.0 has no portable OAuth or credential-reference field, and a package must never ship a bearer token. Connect MCP through the client-specific OAuth flow in Subscribr's AI Integrations page.

For coding agents, install the skill and invoke `subscribr` for full API automation. For conversational agents, connect the hosted MCP server. Both surfaces enforce the same server-side authorization and write-safety rules.

## Development

```bash
npm test
npm pack --dry-run
python3 scripts/verify_package.py
```

The package intentionally uses only the Python and Node standard libraries.
