# Subscribr CLI

[![npm version](https://img.shields.io/npm/v/@subscribrai/cli.svg)](https://www.npmjs.com/package/@subscribrai/cli)
[![license](https://img.shields.io/npm/l/@subscribrai/cli.svg)](LICENSE)

A command-line tool for [Subscribr](https://subscribr.ai) — the all-in-one YouTube content engine, built to work the same way whether a human runs it from the website or an AI agent runs it through the API.

## What is Subscribr?

Subscribr takes a YouTube channel from idea to finished video, in one subscription:

- Research any Channel or video, including competitors, for what's winning right now.
- Turn research into ideas, then move each idea across a Projects board: idea, packaging, script, production.
- Package each idea with titles, hooks, and AI-generated thumbnails.
- Write full scripts in a Channel's own voice, using a Voice Profile trained on real examples.
- Render finished video, through Subscribr Video: custom voices, custom avatars, and reusable media assets.

A human can do all of this from the website. An AI agent can do the same work through the same API, on the same plan and credits, including free. This CLI, and the skill it installs, is how a coding agent, or you from a terminal, reaches that API directly.

## What can I do with this CLI?

- **Manage your Projects board from the terminal.** Create, move, and update Projects without opening the website.
- **Automate your content pipeline.** Script the repetitive parts: bulk-create ideas, move a batch of Projects to the next stage, or cancel a stuck script run.
- **Pull YouTube research on demand.** Look up a Channel or video, and read a transcript, from a script or a scheduled job.
- **Generate and track thumbnails.** Start a thumbnail generation run for an idea, check its progress, and see how much of your Team's monthly thumbnail allowance is left.
- **Keep every script on-brand.** Validate and commit a Voice Profile once, so every script that follows matches your Channel's tone.
- **Hand it to an AI agent.** Install this as a skill for Claude Code, or another AI coding agent, so the agent can do all of the above for you, using your own Team's permissions.
- **Review and fix a rendered video.** Read the editable content and revision manifest, stage overlay, caption, music, slide, and visual edits, then publish a new revision with `apply-revision`.

## Install

```bash
npm install --global @subscribrai/cli
export SUBSCRIBR_API_TOKEN=...
subscribr doctor
```

Run `subscribr doctor` first. It checks that your token works and tells you the base URL, Team, role, and plan it is bound to, so a setup problem shows up immediately, instead of as a confusing error later.

Create a Team-bound token at [subscribr.ai/integrations](https://subscribr.ai/integrations). Never share this token, or commit it to a repository.

Prefer not to install anything globally? Run it directly instead:

```bash
npx -p @subscribrai/cli subscribr doctor
```

### Environment variables

| Variable | Purpose |
|---|---|
| `SUBSCRIBR_API_TOKEN` | **Required.** Your Team-bound API token. |
| `SUBSCRIBR_API_BASE_URL` | Point at a local or staging server instead of production. |
| `SUBSCRIBR_CA_BUNDLE` | Trust a local dev certificate (Herd, Valet, mkcert), when using a local `SUBSCRIBR_API_BASE_URL`. Not needed in production. |
| `PYTHON` | Which Python interpreter the `subscribr` command uses. Defaults to `python3`. |

### Add it to your AI coding agent

Installing the npm package gives you the `subscribr` command. It does not, by itself, teach an AI coding agent how to use that command well. For that, install the bundled skill into your project:

```bash
subscribr-install-skill
```

This adds a `subscribr-api` skill that Claude Code, and other agents that support the Agent Skills format, read automatically. From then on, an agent working in your project can call `subscribr` correctly on its own.

## Try it out

```bash
# Look around
subscribr team get-team
subscribr channels list-channels
subscribr projects list-projects --channel-id 42

# Move a Project forward, and cancel a script run
subscribr projects move-project --project project:v1:idea:7 \
  --stage scripting --idempotency-key move-7-1 --if-match '"project-r3"'
subscribr scripts cancel-script-agent-run --script 93 --run 18 \
  --idempotency-key cancel-18-1

# Templates and voices
subscribr templates create-template --channel 42 \
  --body '{"name":"Explainer","prompt":"Write a structured explainer..."}' \
  --idempotency-key template-1
subscribr voices validate-voice-profile --channel 42 --body @voice.json

# Thumbnails
subscribr thumbnails create-thumbnail-generation --channel 42 \
  --idea-id 7 --num-variations 3
subscribr thumbnails get-thumbnail-generation --channel 42 --run-id 128
subscribr thumbnails get-thumbnail-usage

# Subscribr Video: reads, staging writes, and publish
subscribr video list-capabilities
subscribr video list-channels
subscribr video get-channel --video-channel stch_01hz3k9pb1z7c5m2r6n0y4x2a2
subscribr video list-voices --page 1 --per-page 20
subscribr video get-voice --voice 820e8400-e29b-41d4-a716-446655440003
subscribr video list-avatars --page 1 --per-page 20
subscribr video get-avatar --avatar 820e8400-e29b-41d4-a716-446655440002
subscribr video list-media-assets --page 1 --per-page 20
subscribr video get-media-asset --media-asset 820e8400-e29b-41d4-a716-446655440006
subscribr video get-editable-content --project proj_01hz3k9pb1z7c5m2r6n0y4x2a2
subscribr video add-overlay --project proj_01hz3k9pb1z7c5m2r6n0y4x2a2 \
  --template lower_third --inputs '{"text":"New product launch"}' \
  --playhead-time 42 --idempotency-key overlay-1 --if-match '"revision-r4"'
subscribr video apply-revision --project proj_01hz3k9pb1z7c5m2r6n0y4x2a2 \
  --idempotency-key apply-1 --if-match '"revision-r5"'
subscribr operations get-operation --operation 9f8b6b0e-6b8e-4b8e-8b8e-6b8e4b8e8b8e
subscribr video get-project-download --project proj_01hz3k9pb1z7c5m2r6n0y4x2a2 \
  --output ./final.mp4
```

Don't know what a command needs? Ask the CLI itself — none of these touch the network:

```bash
subscribr help                          # every domain that exists
subscribr <domain> help                 # every action in that domain
subscribr <domain> <action> --help      # every field, its type, and an example
```

## Subscribr Video: what's available today

The `video` domain exposes capability discovery; Channel, custom voice, custom avatar, and reference media reads; Project reads (project, download, editable content, revision manifest, overlay templates, quality report, revision pass); and the Review & Fix revision-staging writes (add/update/remove overlay, remove a staged overlay, update captions, remove music, edit slide text, regenerate a visual, show the presenter, discard a staged edit) plus `apply-revision`, which publishes a new immutable video revision.

Reads require `video:read`. Staging and discard writes require `video:edit`. `apply-revision` requires `video:publish`. Every write requires `--idempotency-key` and `--if-match` with the current strong ETag — read the ETag from `video get-editable-content` or `video get-revision-manifest` before staging a change.

This slice is default-off. A Team without read access receives the typed `video_capability_unavailable` error; a Team that has not connected Subscribr Video receives `video_provisioning_required`. Do not retry either response as an unclassified network failure. Asset reads are owner/admin-only until Channel-scoped asset authorization ships. Channel reads retain the server's Team and Channel visibility rules.

`video apply-revision` publishes a new, immutable video revision — there is no undo. Confirm the staged changes with the user before calling it, then poll the returned operation with `operations get-operation`. Download and inspect the finished video with `video get-project-download --output <path>` before telling the user the edit is done; a successful publish is not proof the video is correct. A `409 revision_conflict` on any video write carries `error.current_revision`; retry the identical write with that value as `--if-match` instead of re-fetching the manifest.

For YouTube research, separate from Subscribr Video, use the Intel video operations instead.

## Want the technical details?

Request/response conventions, exit codes, the retry and idempotency model, how this package ships as an Agent Plugin, and how to regenerate the CLI from Subscribr's API contract, all live in [CLI-REFERENCE.md](CLI-REFERENCE.md).
