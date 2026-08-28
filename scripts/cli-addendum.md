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

| CLI command | Operation |
|---|---|
| `video list-capabilities` | `videoListCapabilities` |
| `video list-channels` | `videoListChannels` |
| `video get-channel --video-channel <id>` | `videoGetChannel` |
| `video list-voices --page <n> --per-page <1-100>` | `videoListVoices` |
| `video get-voice --voice <uuid>` | `videoGetVoice` |
| `video list-avatars --page <n> --per-page <1-100>` | `videoListAvatars` |
| `video get-avatar --avatar <uuid>` | `videoGetAvatar` |
| `video list-media-assets --page <n> --per-page <1-100>` | `videoListMediaAssets` |
| `video get-media-asset --media-asset <uuid>` | `videoGetMediaAsset` |

Start with `video list-capabilities`. The generic operation poller never creates
or exposes a Video write.
