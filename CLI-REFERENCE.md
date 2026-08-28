# CLI reference

This page covers how the CLI actually works: request shape, error handling, retries, exit codes, the Agent Plugin and MCP relationship, and how to regenerate the CLI from Subscribr's API contract. For what the CLI is and what you can do with it, see [README.md](README.md).

## Command shape

The command tree is generated directly from Subscribr's OpenAPI contract, so it stays in sync with the real API. Business rules — what a Team is allowed to do, how conflicts are resolved, and so on — always live on the server. The CLI gives you a typed way to call it, nothing more.

Every command follows `subscribr <domain> <action> [flags]`. Path parameters and body fields are both plain flags, named after the contract's fields with underscores written as hyphens (`voice_id` becomes `--voice-id`):

- For a read command, extra flags become query parameters.
- For a write command, extra flags become JSON body fields.
- `--body` accepts a whole JSON object or array in one go, either inline or as `@file.json`. It cannot be combined with individual field flags in the same call.
- `--idempotency-key` and `--if-match` are sent as transport headers, never as body fields. The CLI refuses a call that omits a header its operation requires, and refuses one that supplies a header the operation does not support.
- Results print as JSON on stdout. Errors go to stderr, with the exit codes below.

## Discovery

| Command | Answers |
|---|---|
| `subscribr help` | which domains exist |
| `subscribr <domain> help` | which actions exist, and their required flags |
| `subscribr <domain> <action> --help` | every field, its type and range, and an example body |

All three are local and make no network call, so use them instead of probing the API to learn a request shape.

## Retries, idempotency, and polling

The CLI retries reads automatically. It also retries writes, but only when you pass `--idempotency-key`, so a retried write can never be applied twice by accident. A write without an idempotency key is never retried automatically.

When the server sends `Retry-After`, the CLI honors it exactly, whether given in seconds or as an HTTP date. If the wait is longer than five seconds, the CLI returns control to the caller instead of blocking, so a script decides whether to wait it out. A retried write uses the identical payload and idempotency key.

Long-running work, such as an Agent Mode script run, returns an operation you can poll:

```bash
subscribr operations get-operation --operation <uuid>
```

`Ctrl-C` stops the CLI. It does not cancel the underlying server-side work.

## Exit codes

| Code | Meaning |
|---|---|
| `2` | Authentication or authorization failed |
| `3` | Validation failed, or the resource was not found |
| `4` | Revision or concurrency conflict |
| `5` | Rate limited |
| `6` | Transient server or network failure |
| `64` | CLI usage error |

## Contract and provenance

- `skills/subscribr-api/references/operations.json` — generated route/ability/safety metadata
- `skills/subscribr-api/references/endpoints.md` — generated endpoint appendix
- `skills/subscribr-api/references/provenance.json` — immutable artifact digests
- `skills/subscribr-api/SKILL.md` — generated: Main's canonical skill body plus `scripts/cli-addendum.md`

## The bundled Python CLI

`subscribr-install-skill` normally installs only the agent skill, atomically replacing its own `skills/subscribr-api` directories so no stale generated reference lingers. To also install a fully self-contained Python CLI, with no npm dependency at runtime, use:

```bash
subscribr-install-skill --with-cli
```

This creates `./.subscribr-cli/` with `subscribr.py` and its generated operation metadata. Run it with `python3 .subscribr-cli/subscribr.py help`. Use `--cli-dir tools/subscribr-cli` to choose another bundle directory, and `--force` only when you intend to replace an existing bundle.

## Agent Plugin and MCP

This npm package is also an [Agent Plugins](https://agent-plugins.org/) 1.0.0 package. Its portable `plugin.json` identifies the package, and `skills/subscribr-api/` contains the Agent Skill. The `subscribr` executable is the primary surface for deterministic API automation: it covers the complete public Customer API contract, with explicit idempotency, concurrency, retry, and polling behavior.

Subscribr's hosted MCP server is complementary, rather than a CLI wrapper. Use `https://subscribr.ai/mcp/subscribr` for conversational, OAuth-capable clients that need the curated Projects, workspace, and Intel workflows. This package intentionally does not declare that remote MCP server in `mcp.json`: Agent Plugins 1.0 has no portable OAuth or credential-reference field, and a package must never ship a bearer token. Connect MCP through the client-specific flow on Subscribr's Integrations page.

For coding agents, install the skill and invoke `subscribr` for full API automation. For conversational agents, connect the hosted MCP server. Both surfaces enforce the same server-side authorization and write-safety rules.

## Development

```bash
npm test
npm pack --dry-run
python3 scripts/verify_package.py
```

The package intentionally uses only the Python and Node standard libraries.

### Regenerating from the contract

Everything under `skills/subscribr-api/` is generated. The inputs all live in the Main app repository, which owns the contract and the canonical skill body:

```bash
python3 scripts/sync_contract.py \
  --openapi  ../subscribr/openapi/subscribr-v1.json \
  --manifest ../subscribr/resources/generated/api-operation-manifest.json \
  --skill    ../subscribr/resources/agent-skills/subscribr-api/SKILL.md
```

Run `php artisan api:contract` in the Main repository first, so the manifest matches the contract. `SKILL.md` is composed from Main's canonical body, plus this package's `scripts/cli-addendum.md`; edit the addendum for CLI-specific guidance, and edit Main for anything that applies to every transport. Never edit the generated files directly — they carry provenance digests.
