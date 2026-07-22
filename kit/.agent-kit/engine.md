# Agent Kit Engine — governance layer

This is the provider-neutral governance layer for the autonomous development kit. It is kit-owned:
package updates may replace it. Project-specific rules belong in `.agent-kit/project/instructions.md`; product
knowledge stays in the paths registered by `.agent-kit/project/manifest.yml`.

Every supported adapter must load this file before work begins:

- Claude Code imports it from root `CLAUDE.md`.
- Codex root `AGENTS.md` explicitly requires reading it before any task action.

The mechanics live in `.agent-kit/workflows/`, `.agent-kit/skills/`, `.agent-kit/roles/`, and
`.agent-kit/rules/`. Provider discovery files under `.claude/`, `.agents/`, and `.codex/` are thin
adapters only and must not own workflow behavior.

## When these rules apply

This file has two tiers, and they do NOT both apply all the time:

- **Always on — project baseline.** In every interaction, including plain terminal conversation
  with no command, honour: the communication language (below), the shared conventions in
  `.agent-kit/project/instructions.md` (stack, commands, coding standards, "work on a branch, never
  `main`"), and the safety items in Core rules (never hardcode secrets, preserve unrelated changes,
  never merge PRs, verification proportional to risk). This tier makes the agent a good citizen of
  the repository without dragging it into any pipeline.

- **Workflow-scoped — the product/meta machinery.** Everything else here — the two modes, the full
  session bootstrap, the design gate, the autonomous contract, and the ordered pipelines — activates
  ONLY when a kit workflow is explicitly invoked: an entry-point command/skill (`/go`, `/ship`,
  `/infra`, `/plan-next`, `/riff`) or the user explicitly asking to run one.

**Default when the user just talks or works in the terminal without invoking a workflow:** behave as
a normal, competent collaborator under the project baseline. Do NOT route the request into `ship`,
do NOT force a product/meta mode choice, and do NOT run the feature pipeline. If a free-text request
clearly looks like building a feature, you may *offer* to route it through the entry point — but
never enter a workflow without the user's go-ahead.

## Session bootstrap

When entering a workflow (see scope above), before acting:

1. Read `.agent-kit/project/manifest.yml` for language, bootstrap state, infrastructure state, and source
   paths.
2. Read `.agent-kit/project/instructions.md` for shared project commands and conventions.
3. Read the active provider adapter in `.agent-kit/platforms/`.
4. Read `README.md` and the product sources referenced by `manifest.sources.*` when they are
   relevant to the task. Never assume fixed documentation paths.
5. In a hosted session, ensure declared dependencies are available. Use the provider setup phase
   or the project's idempotent `scripts/cloud-setup.sh`; a missing dependency is normally a
   recoverable setup action, not a user question.

## Communication language

Communicate with the user in `.agent-kit/project/manifest.yml` → `language`. If it is absent, ask once and
record it. Code, identifiers, file paths, and Git commit messages remain English. Generated product
prose follows the user's language unless the target document already establishes another language.

## Two modes of work

- **Product mode** builds application features, normally through the autonomous `ship` workflow.
  Its design gate and ordered pipeline are mandatory.
- **Meta mode** changes this kit, its docs process, roles, workflows, or adapters. Work as a normal
  collaborator with proportional planning; do not launch the product feature pipeline unless the
  user explicitly asks.

Within a workflow, if unsure which mode applies, ask one concise question before writing files.
(Outside a workflow this choice does not arise — see "When these rules apply".)

## Core rules

1. Work incrementally; do not implement large features as one undifferentiated change.
2. Briefly outline a plan before substantial changes.
3. Never change an approved architectural decision without the owner's explicit approval before
   the final design gate. After that gate, follow the autonomous deviation rule instead of stopping.
4. Prefer framework primitives and existing dependencies; add dependencies only for a concrete need.
5. Never hardcode credentials. Real secrets belong in environment variables or provider secret
   stores and must not enter commits, logs, plans, or PR descriptions.
6. Preserve unrelated working-tree changes. Never use destructive Git commands unless explicitly
   authorized.
7. Run verification proportional to risk and report exactly what did and did not run.
8. Do not merge pull requests. The owner merges.

## Autonomous feature contract

Feature development starts through `ship`:

- Claude Code: `/ship [task]`
- Codex: `$ship [task]`

The canonical ordered pipeline is `.agent-kit/workflows/ship.md`. Interaction is front-loaded:
bootstrap/task selection, optional feature ideation, and technical design approval. **Design
approval is the final interactive gate.** After approval the agent must continue through spec,
plan, independent plan review, implementation, tests, independent code review, independent
security review, PR, and docs reflection without asking routine questions.

Read `.agent-kit/rules/autonomous-mode.md` immediately after approval. Ambiguities become documented
assumptions; owner-only follow-up becomes manual actions; only an insurmountable blocker may stop the
run. The `ship --manual` variant swaps in `.agent-kit/rules/interactive-mode.md` instead —
checkpoints and a consultative posture for a user who wants to co-develop.

## Other workflows

- `go` is the single entry-point router: it reads project state and dispatches to the right
  workflow/skill (or bootstrap, or nothing). Canonical behavior is `.agent-kit/workflows/go.md`.
- `infra` provisions local/cloud infrastructure interactively; canonical behavior is
  `.agent-kit/workflows/infra.md`.
- `plan-next` is read-only roadmap preview; canonical behavior is
  `.agent-kit/workflows/plan-next.md`.
- `riff` is a standalone strategic product brainstorm; canonical behavior is
  `.agent-kit/workflows/riff.md`.

## Manifest and ownership

`.agent-kit/project/manifest.yml` is the single source of automation state and documentation paths. The kit
never moves or duplicates user product docs; it only records their paths. `bootstrapped` means the
project foundation exists, not that every future feature is fully specified.

Ownership boundaries:

- Kit-owned, replaceable: engine, workflows, rules, canonical skills/roles, adapters, validator.
- User-owned, preserved: `.agent-kit/project/instructions.md`, `.agent-kit/project/manifest.yml`, product docs, README,
  root `CLAUDE.md`/`AGENTS.md` override sections, project code, and secrets.

See `.agent-kit/GUIDE.md` for installation, updates, and provider invocation details.
