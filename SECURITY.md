# Security policy

## Reporting a vulnerability

Do not open a public issue for a security problem.

Report it privately to **security@subscribr.ai**. Include:

- what the problem is, and what an attacker gains from it,
- the steps to reproduce it,
- the version of the package you tested,
- anything you already know about a fix.

We aim to confirm your report within three business days. We will tell you when we ship a fix, and we will credit you in the release notes if you want that.

This policy covers the `@subscribrai/cli` package and this repository. Report a problem in the Subscribr API or the Subscribr web application to the same address.

## Supported versions

We support the current published version on npm. Update to it before you report a problem.

## Your API token

Your `SUBSCRIBR_API_TOKEN` is a Team-bound credential. Treat it as a password:

- Set it in the environment, or read it from a secret store.
- Never pass a token as a command-line argument. Other users on the machine can read a process list, and your shell writes the command to a history file.
- Never commit a token, and never paste one into a chat or an issue.
- Revoke a token you no longer need, at [subscribr.ai/integrations](https://subscribr.ai/integrations).

The CLI reads the token only from the environment, and never writes it to stdout, to stderr, or to a log.

## What this package does, and does not do

- It sends requests to `https://subscribr.ai` only. `SUBSCRIBR_API_BASE_URL` can override the host for local development; a check in `scripts/verify_package.py` blocks any other production host from appearing in a shipped file.
- It has no runtime dependencies. There is no third-party package in the install tree to audit.
- It runs no `postinstall` script. `npm install` copies files and runs nothing. `subscribr-install-skill` writes the Agent Skill into your project only when you run it yourself.
- It uses the system trust store for TLS. `SUBSCRIBR_CA_BUNDLE` adds a development root, and only applies when you set a local base URL.
