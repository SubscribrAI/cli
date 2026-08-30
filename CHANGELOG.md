# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-08-28

Ships as `@subscribrai/cli`. Adds the Subscribr Video Review & Fix surface — reads, staging writes, and publish — plus generation (quote/create/cancel) and a generic file-download convenience.

### Added

- Subscribr Video project and revision reads: `video list-projects`, `video get-project`, `video get-project-download`, `video get-editable-content`, `video get-revision-manifest`, `video list-overlay-templates`, `video get-quality-report`, and `video get-revision-pass`.
- Subscribr Video revision-staging and discard writes, each requiring `--idempotency-key` and `--if-match`: `video add-overlay`, `video remove-staged-overlay`, `video update-overlay`, `video remove-overlay`, `video update-captions`, `video remove-music`, `video edit-slide-text`, `video regenerate-visual`, `video show-presenter`, and `video discard-edit`. A `409 revision_conflict` on any of them returns `error.current_revision`; retry the identical write with that value as the new `--if-match`.
- `video apply-revision`, which publishes the staged changes as a new, immutable video revision. Requires the `video:publish` ability (staging writes require `video:edit`); confirm with the user before calling it, then poll the returned operation with `operations get-operation`.
- `--output <path>`, for any command whose response carries a `download_url` (for example `video get-project-download`). Streams the file straight to disk instead of printing the signed URL, and never sends your bearer token to the signed URL's own host.
- `video quote-video`, `video create-video`, and `video cancel-video`, for generating a new video. `quote-video` returns `required_credits` and spends nothing, so an agent can price a generation before committing to it; quote and charge always agree. `create-video` requires `--idempotency-key`, so a replayed submit converges on the same video instead of billing twice, and returns `202` with an operation to poll with `operations get-operation`, the same as `apply-revision`. `cancel-video` works at any point before the video finishes, is a harmless no-op once it has, and refunds the full charge. All three require the `video:generate` ability, separate from `video:edit`/`video:publish` — a token can edit and publish without ever being able to spend.
- A `404` on any of the 22 operations above that carries no typed Subscribr error body now explains itself: the operation may not be deployed or enabled for this Team yet, rather than a generic validation failure. A disabled-but-deployed capability still returns the typed `video_capability_unavailable` error, unchanged; a genuine not-found on a deployed route is also typed and is not affected. `README.md` and the skill's CLI addendum both say so up front.

### Changed

- Renamed the Claude Code plugin from `subscribr` to `subscribr-cli`, and adopted the official plugin manifest schema. The Subscribr app publishes a separate `subscribr` plugin for its hosted MCP connector, and the two names collided. This one is the CLI and its API skill; that one is the MCP connector. The npm package is unaffected, because the plugin manifests do not ship in it.
- `scripts/verify_package.py`'s Video guard no longer checks the surface against a frozen list of nine read operations. It now enforces five shapes instead: a read must be GET, require only `video:read`, and carry no write safety; a staging or discard write must require `video:edit` with both idempotency and concurrency; `apply-revision` must require `video:publish` with the same write safety; `quote-video` must require `video:generate` with idempotency and concurrency both unsupported; and `create-video`/`cancel-video` must require `video:generate` with idempotency required and concurrency unsupported.

## [2.1.1] - 2026-08-27

The first release with a full public project setup. No behavior changed: the CLI, its commands, and its API surface are identical to 2.1.0.

### Added

- `AGENTS.md`, so an AI agent working on this repository finds the test commands and the generated-file rule in the standard place.
- `CONTRIBUTING.md` and `SECURITY.md`.
- `CHANGELOG.md`, starting with this release.
- `CLI-REFERENCE.md`, holding the request conventions, exit codes, retry and idempotency model, and the contract regeneration steps.
- A Claude Code plugin manifest, at `.claude-plugin/`. You can now install the skill with `/plugin marketplace add https://github.com/SubscribrAI/cli`, as an alternative to the npm path. A test keeps its version in step with the other manifests. (Renamed to `subscribr-cli` in 2.2.0.)
- Documentation for the `thumbnails` domain, which the CLI has always shipped but never described.
- npm version and license badges in the README.

### Changed

- Rewrote `README.md` for a reader who has never used Subscribr. It now explains the product first, lists what you can do with the CLI, and moves the deep technical material to `CLI-REFERENCE.md`.
- Updated the positioning to match Subscribr today: one YouTube content engine covering research, ideas, thumbnails, scripts, and video, usable by a person or by an AI agent on the same plan.
- Pointed the repository metadata at `github.com/SubscribrAI/cli`.

## [2.1.0] - 2026-08-27

The first release under the `@subscribrai` scope.

### Changed

- Renamed the package from `@giltotherescue/subscribr-cli` to `@subscribrai/cli`. The command names `subscribr`, `subscribr-cli`, and `subscribr-install-skill` are unchanged.
- Deprecated every version of `@giltotherescue/subscribr-cli` on npm, with a notice pointing at the new name.

[Unreleased]: https://github.com/SubscribrAI/cli/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/SubscribrAI/cli/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/SubscribrAI/cli/releases/tag/v2.1.1
[2.1.0]: https://www.npmjs.com/package/@subscribrai/cli/v/2.1.0
