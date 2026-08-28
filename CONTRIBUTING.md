# Contributing

Thanks for your interest in this project. This document explains how to make a change, and which parts of the repository you must not edit by hand.

## Before you start

Open an [issue](https://github.com/SubscribrAI/cli/issues) first for anything larger than a typo. Much of this package is generated from Subscribr's API contract, so the right fix is often in a different repository. An issue saves you from writing a change that cannot be merged.

## Setup

The package uses only the Python and Node standard libraries. There is nothing to install.

```bash
git clone https://github.com/SubscribrAI/cli.git
cd cli
npm test
```

You need Python 3.12 or later, and Node 18 or later.

## Before you open a pull request

Run all three checks. CI runs the same three on every pull request.

```bash
npm test                            # Python unittest suite, and Node install tests
python3 scripts/verify_package.py   # file allowlist, file modes, provenance digests
npm pack --dry-run                  # the real tarball contents
```

## Do not edit the generated files

Everything under `skills/subscribr-api/` is generated from Subscribr's OpenAPI contract, and carries a digest in `references/provenance.json`. `verify_package.py` checks those digests. A hand edit fails verification, or the next regeneration overwrites it.

To change that content, edit the source in the Main application repository, then regenerate:

```bash
python3 scripts/sync_contract.py \
  --openapi  ../subscribr/openapi/subscribr-v1.json \
  --manifest ../subscribr/resources/generated/api-operation-manifest.json \
  --skill    ../subscribr/resources/agent-skills/subscribr-api/SKILL.md
```

`scripts/cli-addendum.md` is the one exception. It belongs to this package, and the regeneration appends it to the canonical skill body. Edit it directly for guidance that applies only to the CLI.

[AGENTS.md](AGENTS.md) lists the other invariants the tests enforce.

## Style

Match the code and the documentation that is already there:

- Keep the package free of runtime dependencies. Do not add one.
- Write plain language in anything a user reads.
- Write a comment only when the code cannot explain itself.

## Commit messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format, because the changelog is grouped by type:

```
feat(video): add avatar detail reads
fix(cli): stop sending an unsupported If-Match header
docs(readme): document the thumbnails domain
chore(skill): resync after a contract change
```

## Releases

Maintainers publish releases. Follow [RELEASING.md](RELEASING.md) — the order of the steps matters, and it lists the failures that are easy to hit.

The version in `package.json`, `plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `subscribr.py` must always agree; a test enforces this. Record every user-visible change in [CHANGELOG.md](CHANGELOG.md).

## Reporting a security problem

Do not open a public issue for a security problem. Follow [SECURITY.md](SECURITY.md).
