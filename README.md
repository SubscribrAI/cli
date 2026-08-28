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
- **Check in on Subscribr Video.** Today, read-only: your Channels, custom voices, custom avatars, and reference media.

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

# Read-only access to Subscribr Video
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

Don't know what a command needs? Ask the CLI itself — none of these touch the network:

```bash
subscribr help                          # every domain that exists
subscribr <domain> help                 # every action in that domain
subscribr <domain> <action> --help      # every field, its type, and an example
```

## Subscribr Video: what's available today

The `video` domain currently supports nine read-only operations: capability discovery, Channel list/detail, custom voice list/detail, custom avatar list/detail, and reference media list/detail. All of them require the `video:read` permission on your Team-bound API token.

This is an opt-in feature. If your Team does not have access, you get a `video_capability_unavailable` error; if your Team has not connected Subscribr Video, you get `video_provisioning_required`. Neither of these means something went wrong on the network — do not retry them as if they did. Asset reads are owner/admin-only until Channel-scoped authorization ships.

This CLI does not yet ship quote, project, render, cancellation, artifact, or revision operations for Subscribr Video. Don't assume they exist just because the product supports them.

For YouTube research, separate from Subscribr Video, use the Intel video operations instead.

## Want the technical details?

Request/response conventions, exit codes, the retry and idempotency model, how this package ships as an Agent Plugin, and how to regenerate the CLI from Subscribr's API contract, all live in [CLI-REFERENCE.md](CLI-REFERENCE.md).
