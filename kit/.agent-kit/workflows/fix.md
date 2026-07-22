# Fix workflow

A lightweight path for small, local, low-risk changes — a bug fix, a copy tweak, a small refactor,
a dependency bump. It trades the heavy `ship` pipeline for a short one while keeping the guarantees
that matter. Follow `.agent-kit/engine.md` and the active provider adapter. Never merge PRs.

## When to use

Choosing `fix` versus `ship` is the user's call — there is no automatic heuristic. The user knows
the size of the task and picks the path in `/go` (or accepts an offer in free text). Use `fix` when
the change is genuinely small, local, and low-risk.

## Pipeline

1. **Understand** — read the request and the surrounding code until the change is well understood.
   Confirm the scope is genuinely small and local before touching anything.
2. **Change** — make the change on a non-main branch, following the project coding standards. Keep
   it focused; do not expand the blast radius.
3. **Test** — verify only the affected paths: add or adjust tests for the changed behavior and run
   the relevant tests/lint. Do not weaken a valid test to obtain green output.
4. **Review** — delegate an independent, read-only diff review to `reviewer`. Fix critical/major
   correctness and maintainability findings and rerun affected verification. As part of this pass,
   quickly scan the diff for obvious risks (injected input, exposed secrets, unsafe file/process
   use); this replaces the full `ship` security pass, not a deep audit.
5. **PR** — ensure commits are on a non-main branch, push it, and open a pull request with available
   GitHub tooling. Follow `.github/pull_request_template.md` and `.agent-kit/rules/pull-requests.md`.
   Never merge.

## What `fix` skips relative to `ship`

Feature ideation, the design approval gate, writing plans, plan review, and the full independent
security pass. Everything else `ship` guarantees is kept: project coding standards, work on a branch
never `main`, tests for the affected behavior, an independent diff review, and opening a PR.

## Soft escalation

If mid-fix the task turns out to be materially larger than a small change — it needs a design, a new
domain model, or contract changes — stop and offer to switch to `ship` rather than forcing a big
task through the light path silently. The user decides whether to escalate.