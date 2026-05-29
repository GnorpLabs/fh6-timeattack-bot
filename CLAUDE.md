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

## Forza Horizon 6 — UDP Telemetry Spec

Always read `docs/fh6-telemetry-spec.md` before working on any telemetry-related code (packet parsing, field access, struct layout, or UDP listener logic).
