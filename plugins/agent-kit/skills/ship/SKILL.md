---
name: ship
description: Own a feature end-to-end — choose it, scope it, design it, plan it, build it, test it, review it, and open the pull request. Interaction is front-loaded and ends at design approval; after that the run is autonomous.
argument-hint: "[task] [--manual] [--no-ideate] [--rebootstrap] [--brief spec-path]"
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
- `--brief <spec-path>` — the file is a design sketch the owner already approved, typically written
  by a `sprint` brief the evening before. **There are no interactive gates at all**: the autonomous
  rule applies from the first step, because the run may be headless with nobody watching. Skip Task
  and Ideate — the sketch is the chosen, scoped task. A sibling `upstream.md` next to the spec,
  when present, records what actually happened to the features this one builds on; read it with
  the sketch — the sketch was written against those features as imagined, `upstream.md` is the
  diff against reality. Design still runs `brainstorming`'s exploration and alternatives, but as
  expansion rather than interview: every decision the sketch settles is settled, and anything it
  leaves open becomes an autonomous default in the Run log. When exploration proves the sketch
  wrong on a point, don't stop to ask — deviate by this ladder: implementation mechanics the
  sketch never fixed are yours to choose; a settled technical approach that cannot work as written
  is replaced by the most reasonable one that still reaches the sketch's goal — the best path, not
  the smallest diff — recorded as a deviation; and the product behavior and scope the owner
  approved are never quietly substituted. If the goal itself proves unreachable, that is this
  feature's terminal blocker: report it rather than shipping a different feature. The expanded
  spec is still written and committed. Incompatible with `--manual`; for the two gates below, a
  brief counts as a supplied free-text task.
- Remaining free text is the chosen task and skips roadmap task selection.

Either mode appends autonomous decisions and owner-only work to the plan's Run log as they happen;
the PR step assembles its Assumptions and Manual actions from that section, not from memory.

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
  inspect current code and recent history, propose 2–3 next coherent chunks, and let the user choose
  — as one structured choice per `${CLAUDE_PLUGIN_ROOT}/rules/presenting.md`, not an essay.
- **Ideate** — unless `--no-ideate`, run `ideate` scoped to the chosen feature: ask whether it is
  the best version of itself, agree what is in and out, and optionally roadmap what is deferred. The
  user may decline and build the roadmap version unchanged. Skipped when the project has no product
  docs to judge the feature against.
- **Design** — run `brainstorming`: explore the codebase, clarify behavior, compare approaches,
  present a design, and get explicit approval. No implementation code before approval. After
  approval, write the feature spec and enter autonomous mode. Under `--brief` this step is
  expansion, not interview — see Arguments.
- **Plan** — run `writing-plans` for an executable implementation plan. No approval gate.
- **Build** — implement the approved design task by task using the project's conventions. Keep
  commits coherent and verification close to the changed behavior. The always-on rule about reaching
  for what already exists applies hardest here: before each new helper, look in the project, the
  framework, and the installed dependencies — and the library map in the registered coding
  standards names where this ecosystem keeps its ready-made answers. Stay inside the architecture
  stance those standards record. If the project has a language server enabled,
  find-references and go-to-definition find an existing helper far more reliably than searching for
  the name you would have picked.
- **Test** — see below.
- **Review** — see below.
- **Security** — see below.
- **PR** — push the branch and open a pull request following `.github/pull_request_template.md` and
  `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`. Never merge. Then check CI — `gh pr checks`, or
  the closest the session has: a red pipeline is part of this step, not the owner's problem. Fix
  in-scope failures, rerun the verification the fix put at risk, and push again; if CI cannot be
  observed from the session, say so in the PR. If the project has the official `code-review` plugin
  enabled, run `/code-review:code-review` on the open PR now — the plugin command carries the
  plugin's name, it needs a pull request to exist, which is why it lands here rather than in Review,
  and unlike the bundled `/code-review` an agent may invoke it.
  Treat what it returns as a review round: fix in scope, rerun what the fixes put at risk, push. If
  no PR mechanism exists after every safe fallback, report that as the terminal blocker once the
  branch is pushed.
- **Docs** — run `docs-reflection`. No-op by default. If living docs genuinely diverged, open a
  separate docs-only PR from the default branch; otherwise mark docs as current in the feature PR.

The pipeline is complete when the feature PR exists with CI green or its state reported, and docs
reflection is resolved — or when an insurmountable blocker has been reported with the branch left
in a recoverable state. When the owner's review comes back later, `/agent-kit:address` closes that
round; it is not part of this run.

## The run log

The plan ends with a `## Run log` section, and it is the run's working memory. The moment you adopt
an assumption, deviate from the approved design, skip a verification layer, or meet something only
the owner can do, append one line there and commit it with the task — never hold it for the PR
step. A run this long outlives its own context: what is not in the run log or the code does not
survive, and it is also how a resumed session finds out where the last one stood.

## The two gates

Technical setup and product bootstrap are separate concerns, and only one of them is a gate.

**Technical setup — part of every run, never a gate.** Without it nobody knows this project's test
command. If `.agent-kit/project/manifest.yml` is missing, run the setup half of `idea-interview`:
detect the stack, ask the communication language, record the paths of the documents that already
exist, generate the coding standards and `scripts/cloud-setup.sh`, and write the manifest and
`.agent-kit/project/instructions.md`. No product interview, no separate PR — commit it with the
feature. Then load the source paths, repairing a stale one in place rather than duplicating the
document it points at.

**Product bootstrap — a gate, and only on choosing the work.** Proposing sensible next chunks is
impossible without a roadmap, and judging whether a feature is the best version of itself is
impossible without a north star.

- `bootstrapped: false` or `--rebootstrap`, **and no free-text task**: run the full
  `idea-interview` — it surveys the owner, records or generates the core docs, provisions the shared
  scaffolding, updates the manifest, and opens a bootstrap PR. Stop there and ask the owner to merge
  it first: a feature built on an unreviewed roadmap inherits its mistakes.
- `bootstrapped: false` **with a free-text task**: build it. The owner already made the choice this
  gate protects. Skip Task and Ideate, and say once before starting, and again in the PR, that this
  project has no roadmap or product idea recorded — so task selection and product scoping are
  unavailable, and every autonomous default will be judged against the code rather than a stated
  intent. Not blocked, and not silent: the owner sees it on every review and runs `--rebootstrap`
  when they have had enough.

## Test

The bar is not "the tests pass" — it is that someone can merge this without reading the diff.

1. **Provision what the verification plan asked for.** The design named the layers, the seams, and
   the tooling gap. Install what it said the session could install, add it to the project's
   `scripts/cloud-setup.sh` and to `.agent-kit/project/instructions.md` so later sessions and CI
   inherit it, and record anything the session cannot install in the Run log as a manual action
   stating what stays unproven without it. A failed install is recoverable: try a safe alternative,
   and if none works, say which layer you lost. If the CI workflow registered as
   `manifest.sources.ci` is one the kit generated or the owner approved, add the new layer there
   too; a CI the project brought with it is not yours to edit — record the gap in the Run log as a
   manual action.
2. **Delegate to the `agent-kit:tester` agent**, which writes across the chosen layers and proves
   each new behavior can fail. Carry its report of deliberately skipped layers into the Run log.
3. **Run the project's full declared suite** — tests, type checker, and lint. Static analysis is a
   test layer, not a formality: a type error is a failing test. Fix product defects; never weaken a
   valid assertion for green output. A test that passes on a rerun with no change is a defect too —
   one known flake teaches everyone to ignore red, and then nothing in the suite means anything.
4. **Confirm it against the running app** when the feature changed something a person can see — an
   endpoint, a screen, a command. Start the app with the project's own commands and exercise the
   changed surface directly; a green suite on an app that does not start is exactly the failure this
   catches. Do this yourself: `/verify` does the same thing better, but like `/code-review` it can
   only be started by a person typing it, so it is a line for the PR description, not a step you can
   run. Skip the check only when there is no runnable surface, and say so.

If a layer the design called for could not be written, record which one and why in the Run log so
it reaches the PR next to Assumptions. An unproven feature that says so is fine; one that looks
proven is not.

## Review

Claude Code's bundled `/code-review` is a better bug-finder than anything this kit can write: a fan
of independent agents, then a separate pass that scores each finding for confidence and drops the
weak ones. It is also the one tool here an agent cannot start — only a person typing it can. Do not
write it into this step as though you could, and do not stop the run to ask the owner to type it:
after design approval they may be asleep, and a pipeline that waits for a human never finishes.

So check first whether the project has the official `code-review` plugin enabled, because it decides
how wide this step needs to be. That plugin is a fan of five independent reviewers plus a
confidence-scoring pass — around a dozen agents on its own — and the PR step runs it once the pull
request exists. Correctness reviewed once, well, beats correctness reviewed three times.

**With the `code-review` plugin available** — delegate to `agent-kit:reviewer` for the question
nothing else can answer: is this the feature that was approved, against the spec, the plan, the
project instructions, and the registered coding standards. Leave the bug hunt to the PR step. Do not
add the `pr-review-toolkit` specialists by default here; reach for them only when the change earns a
lens the generic fan will underweight — error handling and fallbacks
(`pr-review-toolkit:silent-failure-hunter`), whether the new tests would catch a regression
(`pr-review-toolkit:pr-test-analyzer`), or types that permit invalid states
(`pr-review-toolkit:type-design-analyzer`).

**Without it** — `agent-kit:reviewer` carries both questions, correctness included, and the
`pr-review-toolkit` specialists are worth spawning concurrently if that plugin is there, because
nothing downstream will look again.

Either way this is one wave, not two. Plugin agents carry their plugin's name, which is why the
scoped names above are what you delegate to.

Fix critical and major findings, then rerun the verification the fixes put at risk. A reviewer asked
to find gaps will find some even when the work is sound: fix what affects correctness or the approved
requirements, and record the rest as deliberately deferred rather than building defensive scaffolding
around it. When several reviewers report the same thing, that is one finding, not three.

On a diff large enough that a human would find it a slog to read, follow with `/simplify`, which an
agent *can* invoke: four agents cover reuse of existing helpers, simplification, efficiency, and
level of abstraction, and apply the fixes. It does not hunt for bugs, so it adds no second opinion on
correctness — it makes the result readable. Skip it on a small change, and rerun the suite after it,
since it edits the code.

The bundled review is not lost, it is deferred: the PR description offers `/code-review` on this
branch as a one-keystroke second opinion for the owner, and the PR step runs the `code-review`
plugin's model-invocable equivalent on the open pull request.

Count the agents this step spawns before you spawn them. With the plugin present the whole feature
should come to roughly one reviewer here, a dozen in the PR step, and `/simplify` only if the diff
earned it. If you find yourself planning more than that, you are buying agreement rather than
information.

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
