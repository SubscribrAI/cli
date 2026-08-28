# Releasing

How to publish a new version of `@subscribrai/cli`. Follow the order exactly. Each step exists because skipping it caused a real problem.

## Before you start

You need:

- Publish rights in the `subscribrai` npm organization.
- `npm whoami` returns your user. If it does not, run `npm login`.
- **A browser.** npm asks for a one-time password and opens a URL. No script and no AI agent can complete that step for you.

## The order that matters

Publish from a committed, merged state. **Never publish from a dirty working tree.** Version `2.1.0` shipped this way once, and the published package matched no commit in the repository, so no tag could ever describe it honestly.

Tag **after** the publish succeeds. A tag for a version that failed to publish is worse than no tag.

## Steps

**1. Decide the version.** Follow [semver](https://semver.org/): patch for a fix or documentation, minor for a new command, major for a break. A generated contract change that adds operations is usually a minor.

**2. Bump the version in all five files.** They must agree, and `test_declared_versions_stay_in_lockstep` fails if they do not:

- `package.json`
- `plugin.json`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `VERSION` in `subscribr.py`

**3. Write the changelog entry** in `CHANGELOG.md`, under a new version heading, and update the link definitions at the bottom.

**4. Run every check.**

```bash
npm test
python3 scripts/verify_package.py
npm pack --dry-run
```

**5. Open a pull request, and wait for CI.** `main` is protected: CI must pass, and the branch must be current. Merge with a squash.

**6. Update your local main.**

```bash
git checkout main && git pull --ff-only origin main
git status --short          # must print nothing
```

**7. Publish.** Run this yourself, in your own terminal, because of the one-time password:

```bash
npm publish --access public
```

`--access public` is required. A scoped package publishes private without it.

**8. Confirm the registry has it.** Allow up to a minute for propagation:

```bash
npm view @subscribrai/cli version
```

**9. Tag the merged commit, and push the tag.**

```bash
git tag -a v<version> -m "v<version> — <summary>"
git push origin v<version>
```

**10. Create the GitHub release.**

```bash
gh release create v<version> --title "v<version> — <summary>" --notes "<notes from CHANGELOG.md>"
```

## Things that go wrong

**The tests fail on a document, not on code.** `README.md` carries invariants that tests enforce. It must name every shipped `video` action, and it must contain the exact strings `video_capability_unavailable`, `video_provisioning_required`, `Team-bound`, `owner/admin-only`, `quote`, and `revision`. Rewriting that section freely breaks the build. See `test_authored_docs_define_the_video_slice_and_its_boundaries`.

**`verify_package.py` fails after you add a file.** Two places must agree: the `files` array in `package.json`, and `EXPECTED_PACKAGE_FILES` in `scripts/verify_package.py`. The script also checks the file mode. Use `0o755` for `subscribr.py`, `bin/install.js`, and `bin/subscribr.js`, and `0o644` for everything else.

**`verify_package.py` rejects a URL.** Any host in a shipped file must appear in `ALLOWED_URL_HOSTS`. This check exists because a parked third-party domain reached customers twice.

**You cannot publish a lower version.** npm refuses it, and there is no override. Unpublishing a package's only version blocks the whole name for 24 hours, and a used version number can never be reused. Always move forward.

**You edited a generated file.** Nothing under `skills/subscribr-api/` is hand-written. See [AGENTS.md](AGENTS.md) for how to regenerate it.

## Publishing a contract change

When Subscribr's API contract changes, regenerate before you release:

```bash
# In the Main repository first:
php artisan api:contract

# Then here:
python3 scripts/sync_contract.py \
  --openapi  ../subscribr/openapi/subscribr-v1.json \
  --manifest ../subscribr/resources/generated/api-operation-manifest.json \
  --skill    ../subscribr/resources/agent-skills/subscribr-api/SKILL.md
```

Then follow the steps above from step 1.
