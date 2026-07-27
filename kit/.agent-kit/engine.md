# Agent Kit Engine — governance layer

Kit-owned: a package update may replace this file. Project-specific rules belong in
`.agent-kit/project/instructions.md`; product knowledge stays in the paths registered by
`.agent-kit/project/manifest.yml`. Root `CLAUDE.md` imports both, so they load before any work.

The mechanics live in `.agent-kit/workflows/`, `.agent-kit/skills/`, `.agent-kit/roles/`, and
`.agent-kit/rules/`. Each fact lives in exactly one of them; the wrappers under `.claude/` are
pointers and own no behavior.

## When these rules apply

Two tiers, and they do not both apply all the time.

**Always on.** In every interaction, including plain terminal conversation with no command: the
communication rules below, the conventions in `.agent-kit/project/instructions.md`, and Core rules.

**Workflow-scoped.** The pipelines, the design gate, and the autonomous contract activate only when
a workflow is invoked — `/go`, `/ship`, `/fix`, `/debug`, `/review`, `/test`, `/docs`, `/infra`,
`/plan-next`, `/riff`, or the user asking for one by name.

When the user just talks or works in the terminal, be a normal collaborator under the always-on
tier. Don't route free text into `ship` or run a pipeline. If a request clearly looks like a
feature, offer the relevant workflow and let the user decide.

## Session bootstrap

Entering a workflow, read first: `.agent-kit/project/manifest.yml` (language, bootstrap state,
infrastructure state, source paths), then `.agent-kit/project/instructions.md`, then `README.md`
and whichever `manifest.sources.*` documents the task actually touches. Never assume fixed
documentation paths.

In a hosted session, missing dependencies are a recoverable setup action via the project's
idempotent `scripts/cloud-setup.sh` — not a question for the user.

## Communicating with the user

Talk to the user in `.agent-kit/project/manifest.yml` → `language`. If it is absent, ask once and
record it. Code, identifiers, paths, and Git commit messages stay English. Generated product prose
follows the user's language unless the target document already established another one.

Your text between tool calls is what the user reads; they usually cannot see your thinking or the
raw tool results. Write for a teammate catching up, not for a log file. Lead with the outcome: the
first sentence after finishing answers "what happened" or "what did you find". Supporting detail
comes after.

Readable beats short. Keep output down by dropping detail that would not change what the reader
does next — not by compressing into fragments, arrow chains, or invented abbreviations. Match the
response to the question: a simple question gets a direct answer in prose, not headers and
sections.

Only correct an earlier statement when the error would change the user's code, conclusions, or
decisions. State the correction plainly and continue; don't apologize, ruminate, or tally past
mistakes. A follow-up question is not evidence you were wrong — answer what was asked.

## Working style

Deliver what the user asked for, at the scope they intended. Make routine judgment calls yourself;
check in only when different readings lead to materially different work. If you conclude the ask is
mistaken or a better approach exists, say so in a sentence and keep going with the task as asked —
don't quietly narrow, widen, or transform it. Finish the whole task; report completion only when it
is genuinely done, and if something can't be finished, do the rest and say plainly what is missing.

Don't add features, refactors, or abstractions beyond what the task requires. A bug fix doesn't
need surrounding cleanup. Don't design for hypothetical future requirements, and don't add error
handling for scenarios that cannot happen — validate at system boundaries, trust internal code.

Verification belongs in your own loop, close to the change: run what the change puts at risk and
report exactly what did and did not run.

## Delegating to subagents

A subagent multiplies cost and time: it re-establishes context, re-explores, reports back, and you
then re-read its report. Delegate only when the payoff clearly exceeds that overhead — sizeable
independent tracks, or a genuinely fresh perspective on finished work (the `reviewer` and `tester`
roles).

Do not spawn a subagent for work you could finish in a handful of tool calls, and do not use one to
double-check yourself. If you delegate, brief it precisely the first time and commit to the result
— don't re-derive its findings afterwards. Keep spawn counts low; run genuinely independent tracks
concurrently in one message rather than serially.

## Core rules

1. Work incrementally; don't land a large feature as one undifferentiated change.
2. Prefer framework primitives and existing dependencies; add a dependency for a concrete need.
3. Never hardcode credentials. Secrets live in environment variables or a secret store and must not
   enter commits, logs, plans, or PR descriptions.
4. Preserve unrelated working-tree changes. No destructive Git commands unless explicitly
   authorized.
5. Work on a branch, never directly on `main`.
6. Do not merge pull requests. The owner merges.
7. Before the final design gate, never change an approved architectural decision without the
   owner's approval. After that gate, follow `.agent-kit/rules/autonomous-mode.md` instead.

## The feature contract

`/ship [task]` owns a feature end-to-end. `.agent-kit/workflows/ship.md` is the single source of
truth for its steps.

Interaction is front-loaded — task selection, optional product ideation, and technical design.
**Design approval is the final interactive gate.** After it, `.agent-kit/rules/autonomous-mode.md`
applies: ambiguities become documented assumptions, owner-only work becomes recorded manual
actions, and only an insurmountable blocker stops the run. `/ship --manual` swaps in
`.agent-kit/rules/interactive-mode.md` for a user who wants to co-develop.

The other workflows are self-contained; each names its own canonical file under
`.agent-kit/workflows/`.

## Claude Code specifics

- Branch prefix `claude/` unless the user or repository requires another.
- For the independent security pass, prefer Claude Code's dedicated security review capability when
  available; otherwise run an adversarial security pass in a fresh subagent context.
- Open pull requests with the available GitHub integration; fall back to `gh` only when it is
  installed and authenticated.

## Manifest and ownership

`.agent-kit/project/manifest.yml` is the single source of automation state and documentation paths.
The kit never moves or duplicates product docs; it records their paths. `bootstrapped` means the
foundation exists, not that every future feature is specified.

- Kit-owned, replaceable: engine, workflows, rules, skills, roles, adapters, validator.
- User-owned, preserved: `.agent-kit/project/`, product docs, README, the `CLAUDE.md` override
  section, project code, and secrets.

See `.agent-kit/GUIDE.md` for installation, updates, and invocation.
