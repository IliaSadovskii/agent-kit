---
name: ship
description: Own a feature end-to-end — choose it, scope it, design it, plan it, build it, test it, review it, and open the pull request. Interaction is front-loaded and ends at design approval; after that the run is autonomous.
argument-hint: "[task] [--manual] [--no-ideate] [--rebootstrap]"
disable-model-invocation: true
---

# Ship

One command owns an entire feature: choose → ideate → design → plan → build → test → review →
security → PR → docs.

Interaction is front-loaded on purpose. A complete task specification agreed up front produces
better work than one assembled across many turns, so task selection, product scoping, and technical
design all happen before any code. **Design approval is the final interactive gate.** After it,
`${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md` applies: ambiguities become documented assumptions,
owner-only work becomes recorded manual actions, and only an insurmountable blocker stops the run.

## Arguments

`$ARGUMENTS`

- `--rebootstrap` reruns the project interview.
- `--no-ideate` skips product scoping and builds the task as written.
- `--manual` keeps the user in the loop after design approval — read
  `${CLAUDE_PLUGIN_ROOT}/rules/interactive-mode.md` instead of the autonomous rule. It changes
  nothing before design approval.
- Remaining free text is the chosen task and skips roadmap task selection.

Either mode records autonomous decisions in the PR's Assumptions and owner-only work in Manual
actions.

## Before you start

Read `.agent-kit/project/manifest.yml` (language, bootstrap state, source paths), then
`.agent-kit/project/instructions.md`, `README.md`, and whichever `manifest.sources.*` documents the
task actually touches. Never assume fixed documentation paths.

In a hosted session, missing dependencies are a recoverable setup action via the project's
idempotent `scripts/cloud-setup.sh` — not a question for the user. A long autonomous run is what
[auto mode](https://code.claude.com/docs/en/permission-modes) is for; if the session is not in it,
say so once at the start and continue.

## Pipeline

- **Gate** — two different things have to be true before a feature, and they are not the same gate.
  See "The two gates" below.
- **Task** — use the free-text task when supplied. Otherwise read the idea and roadmap sources,
  inspect current code and recent history, propose 2–3 next coherent chunks, and let the user choose.
- **Ideate** — unless `--no-ideate`, run `ideate` scoped to the chosen feature: ask whether it is
  the best version of itself, agree what is in and out, and optionally roadmap what is deferred. The
  user may decline and build the roadmap version unchanged. Skipped when the project has no product
  docs to judge the feature against.
- **Design** — run `brainstorming`: explore the codebase, clarify behavior, compare approaches,
  present a design, and get explicit approval. No implementation code before approval. After
  approval, write the feature spec and enter autonomous mode.
- **Plan** — run `writing-plans` for an executable implementation plan. No approval gate.
- **Build** — implement the approved design task by task using the project's conventions. Keep
  commits coherent and verification close to the changed behavior. The always-on rule about reaching
  for what already exists applies hardest here: before each new helper, look in the project, the
  framework, and the installed dependencies. If the project has a language server enabled,
  find-references and go-to-definition find an existing helper far more reliably than searching for
  the name you would have picked.
- **Test** — see below.
- **Review** — see below.
- **Security** — see below.
- **PR** — push the branch and open a pull request following `.github/pull_request_template.md` and
  `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`. Never merge. If no PR mechanism exists after every
  safe fallback, report that as the terminal blocker once the branch is pushed.
- **Docs** — run `docs-reflection`. No-op by default. If living docs genuinely diverged, open a
  separate docs-only PR from the default branch; otherwise mark docs as current in the feature PR.

The pipeline is complete when the feature PR exists and docs reflection is resolved — or when an
insurmountable blocker has been reported with the branch left in a recoverable state.

## The two gates

`bootstrapped` used to be one flag doing two jobs, which made "I know exactly what I want built"
wait behind "first write a roadmap". They are separate concerns.

**Technical setup — required for every run.** Without it you cannot run this project's tests, and
nothing downstream works. It is cheap and mostly detection, so just do it; it is part of the run,
not a gate the owner has to clear.

If `.agent-kit/project/manifest.yml` is missing, run the setup half of `idea-interview`: detect the
stack, ask the communication language, record the paths of whatever documents already exist,
generate the coding standards and `scripts/cloud-setup.sh`, and write the manifest and
`.agent-kit/project/instructions.md`. No product interview, no separate PR — commit it with the
feature. Then load the source paths, repairing a stale one in place rather than duplicating the
document it points at.

**Product bootstrap — required only when the kit has to choose the work.** Proposing 2–3 sensible
next chunks is impossible without a roadmap, and judging whether a feature is the best version of
itself is impossible without a north star. So this gate binds exactly when you did not say what to
build.

- `bootstrapped: false` or `--rebootstrap`, **and no free-text task**: run the full
  `idea-interview`. It surveys the owner, records or generates the core docs, provisions the shared
  scaffolding, updates the manifest, and opens a separate bootstrap PR. Stop there and ask the owner
  to merge it before a feature — a feature built on an unreviewed roadmap inherits its mistakes.
- `bootstrapped: false` **with a free-text task**: build it. The owner already made the choice this
  gate exists to protect. Skip Task and Ideate, and **say what is missing out loud**, once, before
  starting: this project has no roadmap or product idea recorded, so task selection and product
  scoping are unavailable, and design decisions will be judged against the code alone. Repeat it as
  a line in the PR description, next to Assumptions.

That last case is deliberately not blocked and deliberately not silent. Nothing stops a project from
running this way forever, and it will work — just less well, because every autonomous default is
made against the code instead of against a stated intent. The owner sees the notice on every pull
request and runs `--rebootstrap` when they have had enough of it.

## Test

The bar is not "the tests pass". It is that someone can merge this without reading the diff. Every
step below exists to move toward that.

1. **Provision what the verification plan asked for.** The design named the layers, the seams, and
   the tooling gap. Install what it said the session could install, add it to the project's
   `scripts/cloud-setup.sh` so the next session and CI inherit it, and record it in
   `.agent-kit/project/instructions.md` with the command that runs it. Anything the session cannot
   install becomes a manual action in the PR, together with what stays unproven without it. A tool
   that fails to install is a recoverable failure — try a safe alternative, and if none works, say
   which layer you lost.
2. **Delegate to the `agent-kit:tester` agent.** It writes across the layers the design chose and
   proves each new behavior can fail. Its report names the layers it skipped; carry that into the PR
   rather than dropping it.
3. **Run the project's full declared suite** — tests, type checker, and lint. Static analysis is a
   test layer, not a formality: a type error is a failing test. Fix product defects; never weaken a
   valid assertion for green output.
4. **Confirm it against the running app with `/verify`** when the feature changed something a person
   can see — an endpoint, a screen, a command. A green suite on an app that does not start is
   exactly the failure this catches. Skip it only when there is no runnable surface, and say so.
5. **Clean the code with `/simplify`.** Four agents review the change in parallel for reuse of
   existing helpers, simplification, efficiency, and whether it sits at the right level of
   abstraction, and apply the fixes. It does not look for bugs — that is `/code-review` at the next
   step — so this is the pass that keeps the diff worth reading. Rerun the suite afterwards.
6. **Check the suite is trustworthy, not just green.** Two things disqualify it, and both are
   defects you fix rather than notes you write down:
   - A test that passed without the behavior being present. The tester agent proves each new test
     can fail; if any could not be made to fail, that behavior is uncovered.
   - A flaky test. If anything passes on a rerun with no change, treat it as a real defect —
     ordering, shared state, time, or a genuine race — and fix it or quarantine it loudly. One known
     flake teaches everyone to ignore red, and then the whole suite stops meaning anything.

If a layer the design called for could not be written, say which one and why, in the PR, next to
Assumptions. An unproven feature that says so is fine. An unproven feature that looks proven is not.

## Review

Two different questions, and one tool does not answer both.

1. **Is the code correct?** Run `/code-review`, the bundled multi-agent review. It reads the
   branch diff in its own context, scores each finding for confidence, and drops the ones that do
   not survive — which is exactly the separate filtering pass this kit would otherwise have to
   build. Pass an effort level to match the change: `medium` for a routine feature, `high` or
   `xhigh` for anything security-sensitive, concurrent, or wide. Fix what it returns.
2. **Is it the feature that was approved?** `/code-review` does not know about the design. Delegate
   to the `agent-kit:reviewer` agent, which reads the diff against the approved spec, the plan, the
   project instructions, and the registered coding standards, and reports where the implementation
   drifted. Fix critical and major findings.

Then rerun the verification the fixes put at risk. Both passes run on finished work in a fresh
context — that is the point, and it is the one place in this pipeline where delegation is worth its
cost. Do not add a third opinion on top.

A reviewer asked to find gaps will find some even when the work is sound. Fix what affects
correctness or the approved requirements; record the rest as deliberately deferred rather than
building defensive scaffolding around it.

If `/code-review` is unavailable in the session, say so and have `agent-kit:reviewer` cover
correctness as well, at a wider brief.

## Security

A distinct pass, not a corner of the code review. Use the strongest capability the session actually
has, in this order:

1. `/security-review` — the bundled pass over the branch diff. Always available; start here.
2. The `claude-security` plugin, if the project has it enabled: a deeper multi-agent scan whose
   findings are challenged by an independent verifier panel before they are reported. Worth it when
   the feature touches authentication, payments, file handling, or untrusted input.
3. If neither is available, run an adversarial security pass in a fresh subagent context covering
   injection, authentication and authorization, secrets and data exposure, unsafe deserialization,
   file and process handling, and dependency and configuration risk.

Fix every critical and high finding. Document consciously deferred ones in the PR.
