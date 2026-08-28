# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.1] - 2026-08-27

The first release with a full public project setup. No behavior changed: the CLI, its commands, and its API surface are identical to 2.1.0.

### Added

- `AGENTS.md`, so an AI agent working on this repository finds the test commands and the generated-file rule in the standard place.
- `CONTRIBUTING.md` and `SECURITY.md`.
- `CHANGELOG.md`, starting with this release.
- `CLI-REFERENCE.md`, holding the request conventions, exit codes, retry and idempotency model, and the contract regeneration steps.
- A Claude Code plugin manifest, at `.claude-plugin/`. You can now install the skill with `/plugin marketplace add https://github.com/SubscribrAI/cli`, as an alternative to the npm path. A test keeps its version in step with the other manifests.
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

[Unreleased]: https://github.com/SubscribrAI/cli/compare/v2.1.1...HEAD
[2.1.1]: https://github.com/SubscribrAI/cli/releases/tag/v2.1.1
[2.1.0]: https://www.npmjs.com/package/@subscribrai/cli/v/2.1.0
