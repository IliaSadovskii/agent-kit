---
name: ship
description: Own a feature end-to-end — choose it, scope it, design it, plan it, build it, test it, open the pull request, and review what landed in it. Interaction is front-loaded and ends at design approval; after that the run is autonomous.
argument-hint: "[task] [--deep|--quick] [--manual] [--no-ideate] [--rebootstrap] [--brief spec-path] [--stage design|build|review|deliver]"
disable-model-invocation: true
---

# Ship

One command owns an entire feature: choose → ideate → design → plan → build → test → open the
pull request → review it → CI → docs.

Interaction is front-loaded on purpose. A complete task specification agreed up front produces
better work than one assembled across many turns, so task selection, product scoping, and technical
design all happen before any code. **Design approval is the final interactive gate.** After it,
`${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md` applies: ambiguities become documented assumptions,
owner-only work becomes recorded manual actions, and only an insurmountable blocker stops the run.

## Arguments

`$ARGUMENTS`

- `--deep` and `--quick` set the depth `brainstorming` designs at — a two-round conversation that
  goes into the mechanics, or the shortest honest design the feature can have. With neither, the
  depth is judged from the feature and stated in one line before the questions start, so it can be
  moved. Neither flag changes anything after design approval, and `--quick` never drops a question
  about something expensive to reverse. Under `--brief` neither applies: the sketch was already
  designed at the depth its brief agreed.
- `--rebootstrap` reruns the project interview.
- `--no-ideate` skips product scoping and builds the task as written.
- `--manual` keeps the user in the loop after design approval — read
  `${CLAUDE_PLUGIN_ROOT}/rules/interactive-mode.md` instead of the autonomous rule. It changes
  nothing before design approval.
- `--brief <spec-path>` — the file is a design sketch the owner already approved, typically written
  by a `sprint` brief. **There are no interactive gates at all**: the autonomous rule applies from
  the first step, because the run may be headless with nobody watching. Skip Task
  and Ideate — the sketch is the chosen, scoped task. A sibling `upstream.md` next to the spec,
  when present, records what actually happened to the features this one builds on; read it with
  the sketch — the sketch was written against those features as imagined, `upstream.md` is the
  diff against reality. An `orientation.md` one directory above the spec, when present, is what the
  brief worked out once for the whole batch about this repository; read it instead of rediscovering
  the same ground. Design still runs `brainstorming`'s exploration and alternatives, but as
  expansion rather than interview: every decision the sketch settles is settled, and anything it
  leaves open becomes an autonomous default in the Run log. When exploration proves the sketch
  wrong on a point, don't stop to ask — deviate by this ladder: implementation mechanics the
  sketch never fixed are yours to choose; a settled technical approach that cannot work as written
  is replaced by the most reasonable one that still reaches the sketch's goal — the best path, not
  the smallest diff — recorded as a deviation; and the product behavior and scope the owner
  approved are never quietly substituted. If the goal itself proves unreachable, that is this
  feature's terminal blocker: report it rather than shipping a different feature. Incompatible with
  `--manual`; for the two gates below, a brief counts as a supplied free-text task.

  **Don't rewrite the sketch.** It is an approved design carrying its own scope, settled decisions
  and done-means, and restating those in a fresh document buys nothing while being carried for the
  rest of the run. `brainstorming` does not write its own spec document under `--brief`; there is
  already an approved one. Copy the sketch to `docs/specs/<date>-<slug>-design.md` and commit it as
  this feature's spec — a
  sprint keeps its sketches outside git, and `agent-kit:reviewer`, `docs-reflection` and a later
  review round all look for the spec under `docs/specs/`. Append to that copy only what exploration
  actually changed: mechanics the sketch left open that you have now settled, and deviations you
  took. The sketch itself is the owner's approved record and stays as it is, so a retry reads the
  same brief this run did. Bound the exploration the same way — read the documents and sections the sketch names, not
  whole files around them.
- `--stage <design|build|review|deliver>` — run one stage of the pipeline and stop, so a long feature
  is carried by several short sessions instead of one that ends four times larger than it began.
  Only meaningful with `--brief`, because the handoff between stages has to be on disk rather than in
  someone's head. The stages and what each leaves behind:

  | Stage | Steps | Leaves behind |
  |---|---|---|
  | `design` | Gate, Design, Plan | spec and plan committed, Run log opened with what orientation found |
  | `build` | Build, Test | code and tests committed, declared suite green |
  | `review` | PR, Review | pull request open, findings fixed and pushed |
  | `deliver` | CI, Docs | pipeline green or reported, docs resolved, a stacked PR converted to draft |

  **The handoff between stages is a file, not an assumption.** `handoff.yml` sits beside the spec —
  the one path every stage is given — and carries the facts a fresh session cannot derive:

  ```yaml
  branch: claude/knowledge-contract     # written before design starts; design creates it
  base: claude/command-cleanup          # what this feature builds on; main for an independent one
  plan: docs/plans/2026-07-31-knowledge-contract.md
  stage: build                          # the last stage that finished
  suite: "scripts/validate.sh → 0, 114 checks"
  pr: null
  ```

  Each stage reads it first, `git switch`es to `branch` before anything else, and updates it as the
  last thing it does. `design` creates the branch named there — never work on the branch you were
  handed, which under a sprint is the *previous feature's* and would put this feature's commits into
  that feature's pull request. `base` is what `agent-kit:reviewer` must diff against. If the file
  names no finished stage before yours, stop and report rather than rebuilding its work.

  This is a record, not a gate: nothing here proves a stage did what it claims. It exists so a later
  stage is never left guessing, which is a different problem from a stage overstating itself.

  `design` is the exception to the Run log's "steps still ahead" template, because its own steps are
  finished by the time the plan exists: it writes `**Steps:** Gate, Design, Plan` and settles all
  three in the same commit. Writing the whole pipeline there instead makes the `Stop` hook demand
  Build through Docs from the one stage running on the most expensive tier.

  **Each stage rewrites the Run log's `**Steps:**` line with its own steps** as it starts, and leaves
  every settled line already in the log untouched. The `Stop` hook reads the first `**Steps:**` it
  finds and holds the turn until each name on it has a line, so a stage that appends a second header
  is guarded against its predecessor's list — already satisfied — and can end anywhere it likes.
  Rewriting is what keeps the guarantee: the header says what *this* session owes, the settled lines
  below accumulate across all four.

  Everything a later stage needs is the spec, the plan, the Run log and the commits. If you find
  yourself wanting something that lives only in the previous session's context, that is a defect in
  what the previous stage recorded — write such things into the Run log as they happen, which is what
  it is for. Without this flag one session runs the whole pipeline, which is right when a person is
  watching.
- Remaining free text is the chosen task and skips roadmap task selection. A screen id in it — `S7`,
  alone or inside a sentence — is a task about a screen the project's map already knows; see "Screen
  references" below.

Either mode appends autonomous decisions and owner-only work to the plan's Run log as they happen;
the PR step assembles its Assumptions and Manual actions from that section, not from memory.

## Before you start

**Under `--stage`, only the `design` stage does this.** It also owns the Gate, and it writes what it
concluded into the Run log — the language, the test command, the source paths that matter, whether
the playbook was current, and the outcome of the Gate, including a bootstrap warning the pull request
still owes the owner three stages later. Later stages read the spec, the plan, that Run log, and the batch's
`orientation.md` and the sibling `upstream.md` when they exist; they do not re-read the manifest,
re-derive the project's conventions, or re-run the freshness check. Orientation paid four times is most of what splitting a
feature into stages was meant to save.

The registered coding standards are the exception, and **every stage that writes code reads them** —
`build`, `review` when it fixes findings, `deliver` when it fixes CI. Their library map and
architecture stance are what the Build step works inside and what `agent-kit:reviewer` judges the
diff against. A stage forbidden to read the standards it will be measured by is a false economy, and
the code `review` and `deliver` write is judged by nobody at all.

Read `.agent-kit/project/manifest.yml` (language, bootstrap state, source paths), then
`.agent-kit/project/instructions.md`, `README.md`, and whichever `manifest.sources.*` documents the
task actually touches. Never assume fixed documentation paths.

Then run `stack-playbook`'s freshness check on the registered coding standards: current costs
seconds and no words; missing or stale is repaired before design, because the design is about to
rely on what the playbook knows. Under `--brief` this happens without questions — the playbook's
close-out goes to the run record instead of the owner.

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
- **Plan** — run `writing-plans` for an executable implementation plan. No approval gate. Under
  `--brief` the plan is a task list with its verification, not a document: the spec already says what
  is being built and what done means, and the plan's lasting job is to host the Run log.
- **Build** — implement the approved design task by task using the project's conventions. Keep
  commits coherent and verification close to the changed behavior. The always-on rule about reaching
  for what already exists applies hardest here: before each new helper, look in the project, the
  framework, and the installed dependencies — and the library map in the registered coding
  standards names where this ecosystem keeps its ready-made answers. Stay inside the architecture
  stance those standards record. If the project has a language server enabled,
  find-references and go-to-definition find an existing helper far more reliably than searching for
  the name you would have picked.
- **Test** — see below.
- **PR** — push the branch and open a pull request — or reuse the one already open on this branch, a
  normal outcome after a resumed stage, updating its description and settling the step as
  `done: reused #<n>` — following `.github/pull_request_template.md` and
  `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, **ready rather than draft**, and never merge. It
  opens here, before the review, for one reason: the `code-review` plugin needs a pull request to
  exist and declines a draft, so a PR opened after the reviews cannot be reviewed by it at all. An
  early PR also starts CI while the review wave runs. If a stacked feature must end up as a draft —
  `sprint` requires it, since such a PR cannot land code — the conversion is the last thing the run
  does, which under `--stage` means the `deliver` stage and not this one, including when that stage
  ends on a blocker. Leaving it to whoever records the feature means a run that died leaves a stacked
  PR one click from moving code sideways. If no PR
  mechanism exists after every safe fallback, report that as the terminal blocker once the branch is
  pushed, and run the review wave on the branch diff instead.
- **Review** — one wave over the frozen diff. See below. The pull request was opened before the
  findings existed, so finish this step by writing them into its description — the Review section the
  pull-request rule asks for is written here, not at PR time.
- **CI** — check the pipeline (`gh pr checks`, or the closest the session has). A red build is part
  of this step, not the owner's problem: fix in-scope failures, rerun the verification the fix put at
  risk, and push. Bound the waiting — a pipeline still pending after a reasonable window settles as
  `- step CI — reported: still pending after <n>` and says so in the PR, rather than polling until
  something kills the session. Your mandate here is the build, not the product: formatting, lint, a
  flake, the workflow's own configuration are yours to fix, and a failure that needs the feature's
  code changed is a blocker to report — this stage runs on the cheapest tier, holds no build context,
  and nothing reviews what it writes. Report it by settling the step as
  `- step CI — blocked: <why>` and saying so in the pull request; a caller reading the Run log sees a
  blocked step and records the feature as blocked rather than done. If CI cannot be observed from the session, say so in the PR.
- **Docs** — run `docs-reflection` against the divergences the Build and Test steps recorded in the
  Run log. A docs-only PR cut from the default branch is the interactive default; inside a sprint the
  update stays on the feature branch, because a branch off `main` describes a repository that does not
  have this feature yet. Either way end the step back on the feature branch — the plan and the `Stop`
  hook are both keyed to it, and a stage that finishes elsewhere leaves its steps unsettled and
  unguarded. Under `--stage` this session did not write the implementation, and `docs-reflection` is
  right that a fresh context cannot see what drifted while the code was being written — the Run log
  is how that knowledge crosses the boundary, which is why the earlier stage owes those lines.
  No-op by default; when nothing diverged, mark docs as current in the feature PR.
  The project's screen map is the one exception: when this feature changed what the app shows, the
  map is updated on the feature branch and pushed to this PR, because a card marked `implemented`
  points at code that only exists here. That push lands after the CI step declared the pipeline green, so
  check the pipeline once more afterwards — the map is a script the project may lint or build.

**Under `--stage` the run is complete when this stage's steps are settled — the next step is not
yours**, and the autonomous rule's "work through to a reviewed pull request" means through to the end
of your stage. Without `--stage`, the pipeline is complete when the feature PR exists with CI green
or its state reported, and docs reflection is resolved — or when an insurmountable blocker has been reported with the branch left
in a recoverable state. When the owner's review comes back later, `/agent-kit:fix --pr` closes that
round; it is not part of this run.

## The run log

The plan ends with a `## Run log` section, and it is the run's working memory. The moment you adopt
an assumption, deviate from the approved design, skip a verification layer, or meet something only
the owner can do, append one line there and commit it with the task — never hold it for the PR
step. A run this long outlives its own context: what is not in the run log or the code does not
survive, and it is also how a resumed session finds out where the last one stood.

It also carries the run's own position in the pipeline, and that part is not optional. Open the Run
log, when the plan is written, with the branch and the steps still ahead of you:

```markdown
**Branch:** claude/<branch>
**Steps:** Build, Test, PR, Review, CI, Docs
```

Under `--stage` this line is **rewritten** by each stage to that stage's own steps, and earlier
stages' settled lines stay where they are. The one exception: a stage **relaunched from scratch**
clears its own lines from the attempt that died, or the guard is satisfied by work the new attempt
never did. A stage picked up with `--resume` is the same attempt continuing and clears nothing. See see the `--stage` argument for why appending a second header
instead would switch the guard off for every stage after the first.

Then settle each step as it ends, one line each — `- step Review — done`,
`- step CI — skipped: no pipeline configured`, `- step PR — blocked: no remote configured`. A
`Stop` hook reads this against the branch you are on and refuses to end the turn while a step has
no line, because a long context loses its ordering to whatever instruction is freshest: a review
prompt read inline can reassign the role, and the turn ends with a report where a pull request was
due. So settle a step the moment it actually ends rather than in a batch at the end, and when you
stop on a blocker, write it against the step it blocked. Every outcome settles a step; only silence
does not.

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

## Screen references

A task that names a screen id — `S7` on its own, or "rebuild S7 with the saved filters" — is work on
a screen the project's map already describes. Resolve it at the Task step, before Ideate scopes
anything. The grammar is a standalone `S<digits>` token, so `S7Adapter` and `TLS7` are not screen
references.

Find the map at `.agent-kit/project/manifest.yml` → `sources.screens`, and at
`docs/screens/screens.data.js` when that key is empty or its path is gone — the manifest template
ships the key empty, so look on disk before concluding there is no map. The file is read under
`${CLAUDE_PLUGIN_ROOT}/skills/screens/references/format.md`.

The entry seeds the task definition: `title` and `purpose` say what the screen is for, `layout` says
what is on it, `status` says whether this run builds it or changes something that exists, and every
transition with the id at either end says what it must be reachable from and where it leads. That is
input, not a finished spec — Ideate still runs unless `--no-ideate` or `--brief` applies, and Design
still explores the code. A `status` of `rejected` is the owner's own decision not to have this
screen: say so before building it, rather than quietly reviving what the map remembers them
dropping.

Two things stop the run before design rather than guessing, and both name `/agent-kit:screens`:

- **The id is not in the map** — say so and list the ids that are. A near miss is usually a typo the
  owner fixes in one word.
- **The project has no map** — say so and stop. Never fall back to reading `S7` as prose: a task
  about a screen nobody can look at is exactly what this resolution exists to prevent.

Under `--brief` the sketch is the approved unit of work, so an id inside it is a cross-reference
rather than the task: read the map entry as context for the design expansion, and when the map or
the id is missing write that in the Run log and carry on with the sketch, rather than blocking a run
nobody is watching.

Building the screen does not update the map. The Docs step does that, so that exactly one step
writes the file — and `screens.data.js` is the only part of it a feature ever writes, since the
viewer beside it is plugin-owned wherever it sits.

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
2. **Delegate to the `agent-kit:tester` agent**, which writes across the chosen layers and proves the
   behaviours carrying real risk can fail — not every assertion, which costs more than the feature it
   covers. Carry into the Run log both its report of deliberately skipped layers and its list of which
   behaviours it proved and which it did not, so the pull request's Testing section can say which is
   which.
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

**Record the result in the Run log, not just the verdict** — which suites ran, what they cover, and
what they returned. Under `--stage` the session that writes the pull request is not the one that ran
the tests, and the PR owes a Testing section naming the run result; without that line it either
reruns everything or invents it. Note there too any documentation this feature has visibly diverged
from as you go: the Docs step runs a stage later, in a context that never saw the implementation.

If a layer the design called for could not be written, record which one and why in the Run log so
it reaches the PR next to Assumptions. An unproven feature that says so is fine; one that looks
proven is not.

## Review

**One wave over a frozen diff, then one round of fixes.** Commit and push everything first, so every
pass judges the same code, and start them without fixing anything in between. What matters is the
single fix round at the end, not literal concurrency: `agent-kit:reviewer` is a subagent you can
launch alongside others, while `/code-review:code-review` and `/security-review` expand into this
context and take their turn. Fixing between passes is what used to cost three rounds of
fix-and-reverify over a diff that barely changed between them.

The wave has three distinct questions in it, and no pass answers another's:

- **Is this the feature that was approved?** `agent-kit:reviewer`, against the spec, the plan, the
  project instructions, and the registered coding standards. Tell it in the delegation whether the
  `code-review` plugin is running on this pull request — that is what decides whether correctness is
  also its job — and give it the base branch to diff against, which for a stacked feature is its
  parent's branch and not the default one. Left to itself it diffs against the default branch and
  reviews every ancestor feature along with this one. Nothing else can answer it, because
  nothing else reads the spec. Work built correctly but to the wrong design is invisible to every
  other pass here.
- **Where are the bugs?** The official `code-review` plugin if the project has it enabled — five
  independent reviewers plus a pass that scores each finding for confidence and drops the weak ones.
  Invoke `/code-review:code-review` on the pull request the previous step opened. Claude Code's
  bundled `/code-review` is stronger still but only a person typing it can start it, so do not write
  it into this step and do not stop the run to ask for it — offer it in the PR description as the
  owner's one-keystroke second opinion. Without the plugin, `agent-kit:reviewer` carries this
  question too.

  **The plugin reports by posting a comment on the pull request, and returns nothing to you.** Go and
  read that comment; findings you never read cannot be deduplicated with anyone else's. It also
  declines silently in several cases — a draft, a closed PR, one it has already reviewed, or one it
  judges automated — and it posts nothing at all when every finding scored below its confidence bar,
  which looks exactly like never having run. So establish which happened: if no comment appeared,
  say so in the Run log by name and have `agent-kit:reviewer` carry the bug hunt, rather than
  recording a review that did not occur. A repeat run after the fix round will be declined as
  already-reviewed; that is expected, and it is why there is one fix round rather than several.
- **What breaks under hostile input?** `/security-review` over the diff; the `claude-security`
  plugin instead if the project has it enabled and the feature touches authentication, payments,
  file handling, or untrusted input; failing both, an adversarial pass in a fresh subagent covering
  injection, authorization, secrets and data exposure, unsafe deserialization, file and process
  handling, and dependency and configuration risk.

Add a `pr-review-toolkit` specialist only when the change earns a lens the generic fan underweights:
error handling and fallbacks (`silent-failure-hunter`), whether the new tests would catch a
regression (`pr-test-analyzer`), types that permit invalid states (`type-design-analyzer`). Plugin
agents carry their plugin's name, which is why the scoped names above are what you delegate to.

**Scale the wave to what the diff actually touches.** A change with no executable surface — prose,
documentation, configuration a machine never runs — earns the conformance question and nothing else:
settle the security pass as a named skip with that reason rather than spending a dozen agents proving
that markdown has no injection flaws. A change to parsing, authorization, money, or process handling
earns the whole wave and possibly a specialist.

Then **reconcile the findings against each other before fixing anything.** Deduplication removes
findings that say the same thing; reconciliation removes findings the others have made pointless — a
reviewer saying the approach is wrong and the module should go takes twenty line-level findings
inside that module with it, and a security pass saying an input path must be removed cancels the
request for tests over it. Structural findings win; act on them first and drop what they moot,
rather than paying for both.

Then **one round of fixes**: from what survives, fix every critical or high security finding, fix what affects
correctness or the approved requirements, and record the rest as deliberately deferred rather than
building defensive scaffolding around it. A security finding is not "correctness" and does not fall
under the approved requirements — it has its own bar, and it survived the merge of the old Security
step into this wave. Rerun what the fixes put at risk plus the project's declared suite, once, at the end — and when the
fix round changed structure rather than lines, send the fix diff back through `agent-kit:reviewer`
once. The code written in this step is the one part of the feature nobody else will look at: the
argument that a cheaper build stage is safe rests on this wave reading it, and this wave does not
read itself.

On a diff large enough that a human would find it a slog to read, follow with `/simplify`, which an
agent *can* invoke: four agents cover reuse, simplification, efficiency, and level of abstraction,
and apply the fixes. It hunts no bugs — it makes the result readable. Skip it on a small change, and
rerun the suite after it, since it edits code.

Count the agents before you spawn them. With the plugin present a whole feature is roughly one
reviewer, one security pass, the plugin's own fan, and `/simplify` only if the diff earned it. More
than that and you are buying agreement rather than information.

