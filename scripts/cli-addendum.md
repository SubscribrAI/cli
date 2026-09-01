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

Every command below is live, but still depends on Subscribr Video being
enabled for the calling Team, so do not assume it works before trying it: a
disabled capability returns a typed `video_capability_unavailable` error, and
a Team that has not connected Subscribr Video gets `video_provisioning_required`.
A bare `404` with no typed error body means the resource itself was not
found, the same as anywhere else in the API — it is not a sign the operation
is missing.

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
| `video replace-with-media --project <id> --block-key <key> --media-asset-id <id> ...` | `videoReplaceWithMedia` | swaps a visual block for an image from the Team's media library; the image must be at least the video's canvas size or the request is rejected; replacing a real-photo block spends a credit, a slide/illustration/stock block is free |
| `video show-presenter --project <id> ...` | `videoShowPresenter` | |
| `video discard-edit --project <id> --item <id>` | `videoDiscardEdit` | discard any staged edit by its item id |
| `video apply-revision --project <id> ...` | `videoApplyRevision` | publishes a new, immutable video revision; confirm with the user first |

`video apply-revision` and `video create-video` both return `202` with an
operation. Poll either with `operations get-operation --operation <uuid>`,
the same generic poller used everywhere else in this CLI.

### The Review & Fix loop

Follow this order for every agent-driven video edit:

1. `video get-editable-content --project <id>` — read the current content,
   note the response `ETag`, and check `edit_availability`. A customer
   normally gets one revision round: `can_start_new_pass` says whether a
   fresh pass may begin (an already-active pass can still be resumed even
   when this is false), and `edit_window_ends_at` is when that stops being
   true.
2. Stage each change (`add-overlay`, `update-captions`, `edit-slide-text`,
   `regenerate-visual`, `replace-with-media`, `show-presenter`,
   `remove-music`, ...) with `--if-match <the ETag you just read>` and a
   fresh `--idempotency-key` on every call. Re-read the `ETag` after each
   accepted write; it advances on every staged change.
3. Review the staged result with `video get-revision-manifest` and
   `video get-revision-pass` before publishing anything. Use
   `video discard-edit` or `video remove-staged-overlay` to drop a staged
   change you no longer want.
4. Before publishing, re-check `edit_availability.can_apply` from a fresh
   `video get-editable-content` call. Applying spends the customer's
   revision round, so confirm it is still true, then call
   `video apply-revision` only after the user has explicitly approved the
   staged changes. It publishes a new, immutable video revision — there is
   no undo.
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
