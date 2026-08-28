---
name: subscribr-api
description: Use Subscribr's REST API, CLI, and MCP server for Projects, scripts, ideas, YouTube Intel research, templates, strict voice profiles, notifications, webhooks, and Subscribr Video capability, Channel, and custom-asset reads. Use when a user asks to automate or inspect Subscribr data.
---

# Subscribr API

Use the canonical operation list in [references/endpoints.md](references/endpoints.md). Never invent a route from a noun in the product UI.

## Connection

- Base URL: `https://subscribr.ai`
- REST prefix: `/api/v1`
- OpenAPI: `https://subscribr.ai/openapi.json`
- Authentication: `Authorization: Bearer <token>`
- Create a Team-bound token at `https://subscribr.ai/integrations`. A token cannot switch Teams after creation.
- Every plan can use the API, including free. Plans limit the work, not the access: generations spend credits, some features are plan-dependent, and all endpoints are rate limited.

`https://subscribr.ai` is the only API host. Any other spelling of the name is not Subscribr, and a token sent there is a leaked credential.

## Start here

Run these three in order before any real work. Each one answers a question the later calls depend on.

1. `getTeam` — confirms the token works and shows which Team it is bound to.
2. `listChannels` — returns the Channel IDs that almost every other operation needs.
3. `getTeamCredits` — confirms there is budget before you start a generation that spends it.

Then read the operation you intend to call, and only then call it.

## Learn the request shape before you send it

Most write failures are guessed request bodies, not permission problems. Never infer a field name from the product UI or from a similar-looking operation.

- With the CLI: `subscribr <domain> <action> --help` prints required fields, optional fields, types, ranges, and an example body. This never makes a network call.
- With plain REST: read the operation's `requestBody` schema in `https://subscribr.ai/openapi.json`. The referenced schema's `required` array is authoritative.

A `422` names the fields it rejected in `error.field_errors`, keyed by field name. Read them and correct the request; do not retry the same body.

Treat `403` as a permission, entitlement, or Team-binding failure; do not retry it as a transient error.

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

## Transcripts

`get_youtube_video` (any video) and `get_research_video` (a video on a channel you track) both accept `include_transcript`. It is
off by default because each fetch calls an external provider and takes seconds.

Read the response rather than assuming: `has_transcript` tells you whether one
came back, `transcript_truncated` whether it was cut, and
`transcript_unavailable_reason` why not. Plenty of videos simply have no
transcript — that is a normal outcome, not an error to retry.

Two limits apply, and both are reported through
`transcript_unavailable_reason` rather than as failures:

- A per-minute ceiling for every workspace. If you hit it, stop; do not loop.
- A monthly allowance on free workspaces. When it is gone, continue without
  transcripts rather than asking the operator to upgrade repeatedly.

## YouTube research and Subscribr Video

Keep using the Intel video lookup/search operations for open-world YouTube research and tracked-channel MCP research tools. Subscribr Video is the video-production surface.

Use a Team-bound API token (API key) with `video:read`; a token cannot switch Teams. Start with capability discovery, then read Channels or assets through `videoListCapabilities`, `videoListChannels`, `videoGetChannel`, `videoListVoices`, `videoGetVoice`, `videoListAvatars`, `videoGetAvatar`, `videoListMediaAssets`, and `videoGetMediaAsset`.

The Video slice is default-off. Treat `video_capability_unavailable` as an explicit Team capability denial, `video_provisioning_required` as a missing connection, and `video_configuration_not_ready` as a retryable rollout/configuration state. Asset reads are owner/admin-only in this slice.

Subscribr Video also ships generation, gated by `video:generate`. Call `videoQuoteVideo` for a priced estimate; it creates nothing and spends nothing, and supports no idempotency or concurrency, so quote as often as needed. Call `videoCreateVideo` to start a render; it requires `Idempotency-Key` and returns a pollable `operation`, not a finished video — poll it, then read the project with `videoGetProject`. Call `videoCancelVideo` to cancel a project in any non-terminal status; it also requires `Idempotency-Key`, refunds the full quoted charge upstream, and is an idempotent no-op on a project that already reached a terminal status.

Subscribr Video also ships a Review & Fix facade for an existing project. Read a project with `videoListProjects`, `videoGetProject`, and `videoGetProjectDownload`. Read what can change with `videoGetEditableContent`, `videoGetRevisionManifest`, `videoListOverlayTemplates`, `videoGetQualityReport`, and `videoGetRevisionPass`. Stage or discard a change with `video:edit`: `videoAddOverlay`, `videoRemoveStagedOverlay`, `videoUpdateOverlay`, `videoRemoveOverlay`, `videoUpdateCaptions`, `videoRemoveMusic`, `videoEditSlideText`, `videoRegenerateVisual`, `videoShowPresenter`, and `videoDiscardEdit`. Every staging write needs `Idempotency-Key` and `If-Match`; call `videoGetEditableContent` or `videoGetRevisionManifest` first and send its response `ETag` back as `If-Match`.

`videoApplyRevision` (`video:publish`) publishes the staged changes as a new immutable revision. This cannot be undone the way a staged edit can. Show the staged change list and stop for explicit user approval before you call it.

Every Subscribr Video capability is named above by its `operationId`. If an operation is not named in this document, it does not exist yet — do not invent it.

## MCP

Use `https://subscribr.ai/mcp/subscribr` for ChatGPT, Claude, and other MCP connections. It is the canonical customer MCP endpoint and exposes the focused semantic catalog plus interactive Projects, Intel, and Script apps.

Prefer MCP inside conversational hosts and REST/CLI for deterministic automation. Tools and embedded Apps still enforce the same Team, Channel, role, revision, idempotency, and confirmation rules as REST.

When an MCP host cannot render Apps, use the structured/text tool fallback. Never treat widget visibility or hidden App fields as authorization.

## Errors

Customer API errors use one envelope: `error.code`, `error.message`, `error.retryable`, plus `error.field_errors` on validation failures and, where relevant, the current revision and a retry delay.

Act on `error.code`, not on the message text. Retry only when `error.retryable` is true. Log correlation IDs, not tokens, receipts, profiles, prompts, or signed URLs.

## Using the CLI

The shared rules above apply to every transport. This section is what the
`subscribr` executable adds on top of them.

### First run

```bash
export SUBSCRIBR_API_TOKEN=...      # Team-bound token
subscribr doctor                    # base URL, token, Team, role, plan
subscribr channels list-channels    # the Channel IDs other commands need
```

`subscribr doctor` is the only command worth running blind. It reports where
requests are going and whether the credential works, so a failure there is a
setup problem and never a bad request.

### Discovery

| Command | Answers |
|---|---|
| `subscribr help` | which domains exist |
| `subscribr <domain> help` | which actions exist, and their required flags |
| `subscribr <domain> <action> --help` | every field, its type and range, and an example body |

All three are local. None of them makes a network call, so use them freely
instead of probing the API to learn a shape.

### Passing arguments

Path parameters and body fields are both plain flags: `--channel 42
--title "..." --length 1200`. Flag names are the contract's field names with
underscores written as hyphens, so `voice_id` is `--voice-id`.

For a whole body at once use `--body '<json>'` or `--body @file.json`. `--body`
cannot be combined with individual field flags for the same call.

`--idempotency-key` and `--if-match` become transport headers, never body
fields. The CLI refuses a call that omits one the operation requires, and
refuses one that supplies a header the operation does not support, so a usage
error here costs nothing.

### Environment

| Variable | Purpose |
|---|---|
| `SUBSCRIBR_API_TOKEN` | required; the Team-bound token |
| `SUBSCRIBR_API_BASE_URL` | override the host for local or staging conformance |
| `SUBSCRIBR_CA_BUNDLE` | trust a development root (Herd, Valet, mkcert) when using a local host |
| `PYTHON` | interpreter used by the `subscribr` shim |

Never pass a token on the command line, and never commit one. Read it from the
environment or a secret store.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `2` | authentication, authorization, or missing token |
| `3` | validation or not found |
| `4` | revision conflict |
| `5` | rate limited |
| `6` | transient server or network failure |
| `64` | CLI usage error — nothing was sent |

Reads and idempotency-keyed writes retry automatically; other writes never do.
`Retry-After` is honoured as seconds or an HTTP date, and a requested delay over
five seconds is handed back to you rather than slept through.

### Long-running work

Asynchronous operations return an operation ID. Poll it with
`subscribr operations get-operation --operation <uuid>`. There is no `--wait`;
`Ctrl-C` stops local polling and never cancels server-side work.

### Subscribr Video commands

Reads need `video:read`. Staging and discard writes need `video:edit`.
Publishing a revision needs `video:publish`. Generating a video needs
`video:generate` — a separate ability from `video:edit`/`video:publish`, so a
token can be scoped to stage and publish edits without ever being able to
spend credits, or the other way around.

Every staging write and `apply-revision` require `--idempotency-key` and
`--if-match` with the current strong `ETag`. `create-video` and
`cancel-video` require `--idempotency-key` only — there is no existing
revision for either to hold `--if-match` against. `quote-video` requires
neither: it has no state to key and nothing to retry into.

| CLI command | Operation | Notes |
|---|---|---|
| `video quote-video --name <n> --script <s> ...` | `videoQuoteVideo` | returns `required_credits` and spends nothing; quote and charge always agree |
| `video create-video --name <n> --script <s> ... --idempotency-key <key>` | `videoCreateVideo` | a replayed submit with the same key converges on the same video instead of billing twice; returns `202` with an operation |
| `video cancel-video --project <id> --idempotency-key <key>` | `videoCancelVideo` | works at any point before the video finishes, is a harmless no-op once it has, and refunds the full charge |
| `video list-capabilities` | `videoListCapabilities` | start here |
| `video list-channels` | `videoListChannels` | |
| `video get-channel --video-channel <id>` | `videoGetChannel` | |
| `video list-voices --page <n> --per-page <1-100>` | `videoListVoices` | |
| `video get-voice --voice <uuid>` | `videoGetVoice` | |
| `video list-avatars --page <n> --per-page <1-100>` | `videoListAvatars` | |
| `video get-avatar --avatar <uuid>` | `videoGetAvatar` | |
| `video list-media-assets --page <n> --per-page <1-100>` | `videoListMediaAssets` | |
| `video get-media-asset --media-asset <uuid>` | `videoGetMediaAsset` | |
| `video list-projects` | `videoListProjects` | the Project board for Subscribr Video |
| `video get-project --project <id>` | `videoGetProject` | |
| `video get-project-download --project <id>` | `videoGetProjectDownload` | returns a signed `download_url`; pass `--output <path>` to save the file directly instead of printing the URL |
| `video get-editable-content --project <id>` | `videoGetEditableContent` | read this first; capture its `ETag` before staging any edit |
| `video get-revision-manifest --project <id>` | `videoGetRevisionManifest` | every staged, unpublished change, and its current `ETag` |
| `video list-overlay-templates --project <id>` | `videoListOverlayTemplates` | |
| `video get-quality-report --project <id>` | `videoGetQualityReport` | |
| `video get-revision-pass --project <id> --pass <id>` | `videoGetRevisionPass` | |
| `video add-overlay --project <id> ...` | `videoAddOverlay` | stage a new overlay |
| `video remove-staged-overlay --project <id> --item <id>` | `videoRemoveStagedOverlay` | discard a staged, not-yet-published overlay |
| `video update-overlay --project <id> --overlay <id> ...` | `videoUpdateOverlay` | stage a change to an already-published overlay |
| `video remove-overlay --project <id> --overlay <id>` | `videoRemoveOverlay` | stage removal of an already-published overlay |
| `video update-captions --project <id> ...` | `videoUpdateCaptions` | |
| `video remove-music --project <id> ...` | `videoRemoveMusic` | |
| `video edit-slide-text --project <id> ...` | `videoEditSlideText` | |
| `video regenerate-visual --project <id> ...` | `videoRegenerateVisual` | |
| `video show-presenter --project <id> ...` | `videoShowPresenter` | |
| `video discard-edit --project <id> --item <id>` | `videoDiscardEdit` | discard any staged edit by its item id |
| `video apply-revision --project <id> ...` | `videoApplyRevision` | publishes a new, immutable video revision; confirm with the user first |

`video apply-revision` and `video create-video` both return `202` with an
operation. Poll either with `operations get-operation --operation <uuid>`,
the same generic poller used everywhere else in this CLI.

### The Review & Fix loop

Follow this order for every agent-driven video edit:

1. `video get-editable-content --project <id>` — read the current content and
   note the response `ETag`.
2. Stage each change (`add-overlay`, `update-captions`, `edit-slide-text`,
   `regenerate-visual`, `show-presenter`, `remove-music`, ...) with
   `--if-match <the ETag you just read>` and a fresh `--idempotency-key` on
   every call. Re-read the `ETag` after each accepted write; it advances on
   every staged change.
3. Review the staged result with `video get-revision-manifest` and
   `video get-revision-pass` before publishing anything. Use
   `video discard-edit` or `video remove-staged-overlay` to drop a staged
   change you no longer want.
4. Call `video apply-revision` only after the user has explicitly approved
   the staged changes. It publishes a new, immutable video revision — there
   is no undo.
5. Poll the returned operation with `operations get-operation --operation
   <uuid>` until it reaches a terminal state.
6. Download the finished video with `video get-project-download --project
   <id> --output <path>` and inspect it.

If a staging write or `video apply-revision` returns `409 revision_conflict`,
do not re-fetch the manifest first. Retry the identical write immediately
with the same `--idempotency-key` and `error.current_revision` from the
response body as the new `--if-match`.

A `202` accepted, a successful staging call, or a ready-looking preview is
**not** proof the video is good. Only the downloaded final artifact is. Do
not tell the user an edit is done until you have downloaded and inspected
that file.
