# Project Instructions

## Git Workflow

**Always use feature branches. Never commit directly to `master`.**

Before starting any implementation work:
1. Create a feature branch: `git checkout -b feat/<short-description>`
2. Do all work and commits on that branch
3. When complete, push and open a PR: `git push -u origin <branch>` then `gh pr create`

`master` has branch protection — direct pushes are blocked by GitHub.

Branch naming convention:
- `feat/<description>` — new features
- `fix/<description>` — bug fixes
- `docs/<description>` — documentation only
- `chore/<description>` — maintenance, deps, tooling

---

## fh6-relay Release Workflow

After any PR touching `fh6-relay/` is approved and merged to `master`:

1. Bump the version in `fh6-relay/package.json` (and `package-lock.json`):
   ```bash
   cd fh6-relay && npm version patch --no-git-tag-version
   ```
   Use `patch` for bug fixes, `minor` for new features, `major` for breaking changes.

2. Commit and push directly to `master`:
   ```bash
   git add fh6-relay/package.json fh6-relay/package-lock.json
   git commit -m "chore(relay): bump version to <new-version>"
   git push origin master
   ```

3. Tag the commit to trigger the release workflow:
   ```bash
   git tag v<new-version> && git push origin v<new-version>
   ```

The `🏁 Build & Release fh6-relay.exe` workflow fires on `v*` tags, runs Jest tests, builds the NSIS installer with electron-builder, and publishes it as a GitHub Release automatically.

---

## Forza Horizon 6 — UDP Telemetry Spec

Always read `docs/fh6-telemetry-spec.md` before working on any telemetry-related code (packet parsing, field access, struct layout, or UDP listener logic).
