---
name: subscribr-api
description: Use Subscribr's REST API, CLI, and MCP server for Projects board management, scripts, ideas, YouTube Intel research, templates, strict voice profiles, notifications, and webhooks. Use when a user asks to automate or inspect Subscribr data.
---

# Subscribr API

Use the canonical operation list in [references/endpoints.md](references/endpoints.md). Never invent a route from a noun in the product UI.

## Connection

- Base URL: `https://subscribr.com`
- REST prefix: `/api/v1`
- OpenAPI: `https://subscribr.com/openapi.json`
- Authentication: `Authorization: Bearer <token>`
- Create a Team-bound token in Subscribr Developer Settings. A token cannot switch Teams after creation.

Start with `getTeam` and `listChannels` when Team or Channel context is unknown. Treat `403` as a permission, entitlement, or Team-binding failure; do not retry it as a transient error.

## Safe writes

- Send a unique `Idempotency-Key` on every operation marked `idempotency=required`.
- Send the exact strong `ETag` as `If-Match` when concurrency is required.
- On a timeout, retry the identical request with the same idempotency key. Never change the body under an existing key.
- A `409 revision_conflict` means reload the resource and ask before applying the change again.
- Project archive, promotion, idea generation, and voice commits may use preview/commit receipts. Show the effect preview and stop for explicit user approval before commit.

## Projects board

Use `listProjects` for the board and `getProject` for one card. Project IDs are versioned typed strings such as `project:v1:idea:42` and `project:v1:script:93`; preserve the complete value. Use `expected_revision`/`If-Match` and idempotency when creating, editing, moving, promoting, archiving, restoring, commenting, or changing production metadata.

The external stages are the existing Kanban stages. Do not manufacture a different workflow. A disabled occupied Recording column can be read and moved out of, but cannot receive new cards unless enabled for the Channel.

## Templates and voices

Built-in templates are stable descriptors and are never created by a list call. Only custom templates can be created, updated, archived, or restored.

Voice writes are deliberately strict:

1. Call `validateVoiceProfile` with the complete Voice Profile v2 document.
2. Present its normalized profile, diff, warnings, checksum, target ID, and expiry.
3. After explicit approval, call `commitVoiceProfile` with the unchanged normalized profile and receipt. Include `If-Match` for updates.

Legacy voice profiles remain readable but are not writable until a complete v2 profile validates. Do not remove unknown fields or fill missing fields heuristically; validation is fail-closed.

## YouTube research and Subscribr Video

Keep using the Intel video lookup/search operations for open-world YouTube research and tracked-channel MCP research tools. The generic `getOperation` route may poll an operation ID already returned by a public API operation, but it does not publish a Video capability. Subscribr Video is Subscribr's video-production surface. Do not invent Video REST or CLI commands until the canonical public `/api/v1/video/...` operation metadata ships; that future slice must add capability discovery, channel setup, quotes, renders, artifacts, cancellation, and revisions together.

## MCP

Use `https://subscribr.com/mcp/subscribr/v2` for new ChatGPT, Claude, and other MCP connections. It exposes the compact semantic catalog and interactive Projects board. The original `https://subscribr.com/mcp/subscribr` endpoint remains a 16-tool compatibility surface for existing integrations; do not use it when a workflow requires Projects, Tasks, notifications, templates, or strict Voice Profile management.

Prefer MCP inside conversational hosts and REST/CLI for deterministic automation. Tools and embedded Apps still enforce the same Team, Channel, role, revision, idempotency, and confirmation rules as REST.

When an MCP host cannot render Apps, use the structured/text tool fallback. Never treat widget visibility or hidden App fields as authorization.

## Errors

Customer API errors use one envelope with `error.code`, `error.message`, `error.retryable`, and optional bounded field errors/current revision/retry delay. Log correlation IDs, not tokens, receipts, profiles, prompts, or signed URLs.
