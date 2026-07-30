# Knowledge and gates — design

Status: proposed, not implemented. Written 2026-07-30.

Two contracts, one idea: replace *"the agent believes it is done"* with *"here is a command that
answers yes or no."* One contract governs a pipeline step, the other governs what the project knows.
They meet at a single point — the `verification` slot supplies the commands a step gate runs.

---

## 1. What is broken today

**A step settles itself.** The `Stop` hook checks that a step has *a line* in the plan's Run log,
not that the step passed. `- step Test — done` is written by hand and the hook is satisfied. The
guarantee today is "the pipeline reached its end", not "each step was carried out".

**`skipped` is a universal exit.** `- step Security — skipped: <any reason>` closes any step. The
reason is unconstrained, so the constraint does not exist.

**Documentation has no contract.** The manifest records *paths* to whatever documents exist. That
was right for a kit that reads docs opportunistically; it fails for `mvp` / `sprint`, which
*depend* on specific knowledge being present. Missing knowledge does not stop a run — it makes the
run invent, and the owner finds out from the code.

**Five writers, no structure.** `idea-interview`, `ideate`, `docs-reflection`, ship's Docs step and
`screens` all write documentation, coordinated by prose conventions.

---

## 2. Contract one — the step gate

### The rule

A step is closed by the **gate**, never by the agent. The agent asks; the gate runs the criteria
from config and writes the verdict itself. The agent cannot declare a step done: run state is
outside its reach (a hook blocks writes) and the only path into that file is passing the checks.

### Files

| What | Where | Written by | Purpose |
|---|---|---|---|
| Pipeline definition | `.agent-kit/project/pipelines.yml` | human (seeded from a template) | steps, entry/exit criteria, loop limits |
| Run state | `.agent-kit/runs/<branch>.yml` | gate only | machine truth: what closed, attempts, evidence |
| Run log | `docs/plans/<...>.md` | agent | human narrative: assumptions, deviations, manual actions |

Ownership follows the existing boundary: `pipelines.yml` belongs to the project and survives plugin
updates; the gate script and hooks belong to the plugin.

### Step shape

```yaml
commands:                      # single source of the project's commands;
  test: make test              # instructions.md points here rather than duplicating
  lint: make lint
  e2e: make e2e

limits:
  total_attempts: 40
  wall_clock: 6h

pipelines:
  ship:
    steps:
      - name: Design
        requires: []
        done_when:
          - exists: docs/specs/*-design.md
          - approved_by_owner: true      # satisfied by the brief under --brief
        max_attempts: 1

      - name: Test
        done_when:
          - run: ${test}
          - run: ${e2e}
        max_attempts: 3
        on_exhausted: block              # block | continue | escalate

      - name: Review
        done_when:
          - agent: reviewer
            rubric: docs/specs/*-design.md
            verdict: no_blocking_findings
        max_attempts: 2

      - name: PR
        done_when:
          - run: gh pr view --json url -q .url
        max_attempts: 1
        skippable_when: no_remote        # named, not arbitrary
```

Three fields answer entry and exit:

- `requires:` — preconditions. What must hold to enter.
- `done_when:` — postconditions. All checks must pass.
- `max_attempts` / `on_exhausted` — loop control.

### Check kinds

Keep the set small; it is not a programming language.

| Kind | Meaning |
|---|---|
| `run:` | shell command, exit 0 passes |
| `exists:` | glob matches at least one file |
| `git:` | `tree_clean`, `commits_on_branch`, `pushed` |
| `approved_by_owner:` | the owner confirmed (autonomous: the brief) |
| `agent:` | grader subagent with a rubric, verdict via structured output |

`agent:` is the only non-mechanical kind. It costs tokens and time and its verdict is probabilistic
— use it only where mechanics cannot reach (diff against design, docs against code). The grader
always runs with a **fresh context**: whoever wrote the code is a poor judge of whether the code is
ready, because they remember the intent and fill in from it.

### Step lifecycle

The agent talks to the gate with three commands:

```
step start <Name>     checks requires; opens the step; prints what will close it
step settle <Name>    runs done_when; writes the verdict
step skip <Name>      only if optional, or skippable_when fired
```

`settle` is the loop:

- **all checks pass** → `done` written with evidence (which command, which exit code, when); exit 0;
  the step is closed permanently.
- **something fails** → non-zero exit, and the gate prints *what* failed: check name, exit code, the
  tail of the output. State records `attempt N failed`. The agent fixes and calls `settle` again.
- **attempts exhausted** → `blocked` with the history of every attempt; then `on_exhausted`: stop,
  continue with an explicit note in the PR, or wake the owner with a push.

The attempt counter lives in state, not in the agent's head — so it survives compaction, context
loss and session restart. A resumed session learns "Test failed twice, here is how" from the file.

### Hooks

| Hook | Role |
|---|---|
| `SessionStart` | if an unfinished run exists for this branch, inject its state — a fresh or compacted session knows where it stands |
| `PreToolUse: Bash` | existing guard, plus refuse shell writes to `.agent-kit/runs/**` |
| `PreToolUse: Write\|Edit` | **new.** Refuse tool writes to `.agent-kit/runs/**`. Without it the whole construction is paper |
| `Stop` | reads state, not markdown. Holds the turn while any step lacks a terminal verdict; also catches a step marked done with no evidence record |

Every hook fails open on a parse error, as `stop-guard.py` already does. A wedged hook is worse than
no hook.

### Deliberate limits

Steps and gates are configurable; **behavior is not**. The YAML says *what to check* for a step to
count as closed. It does not describe *how* the agent works — that stays prose in the skills. No
branching, no conditional routing: a pipeline is a linear list of steps, some optional, some
skippable under a named condition. No new commands from YAML. Once branching exists, this needs
visualization and a debugger, and that is a separate product.

---

## 3. Contract two — the knowledge contract

### The rule

The kit does not need a *file format*. It needs **filled slots** — questions its pipelines must have
answers to. Free form, required content. The project's own documents stay where they are, in their
own style; the kit indexes them, never relocates or rewrites them.

### Files

```
.agent-kit/knowledge/
  contract.yml    human decisions: each slot's status, where entries live, annotations
  index.yml       derived: facts extracted from the docs, plus section hashes
```

The project's `docs/` remain the source of truth. The kit **derives** the machine index from them
and re-derives it when the prose changes. The owner never writes this YAML.

### Slot statuses

Three terminal states; a slot must be in one of them before any build command runs:

```
filled          answered, and it passes the slot's own readiness criterion
not_applicable  not relevant to this product, with a reason
open_question    a known unknown, accepted deliberately
```

Two states are forbidden: `empty` (nobody looked) and `conflicts` (sources disagree).

The bar is **"every slot has a deliberate verdict"**, not "every slot is filled". Demanding
literal fullness is dangerous: a slot the project does not need but is required to fill gets filled
with invention, and invented knowledge is worse than a gap — the agent treats a gap with caution and
a fabricated answer as the owner's decision.

### Readiness per slot

*Filled* must not mean *there is text*. Each slot carries its own criterion — the `done_when` idea
applied to knowledge:

| Slot | Filled when |
|---|---|
| `entities` | every entity names its states, allowed transitions and key relations |
| `actors` | every actor says how it comes to exist and what it can do that others cannot |
| `mvp_bounds` | an explicit in-list and an explicit out-list; no "and so on" |
| `scenarios` | each one walks end to end on concrete data |
| `verification` | the commands actually run and return zero — checked mechanically |
| `deferred_seams` | each deferred item names the one decision in the MVP that keeps it cheap later |

Some are mechanical (run the command, parse the map, resolve the path). The rest are judged by a
grader whose rubric asks **"can an implementer act on this without asking?"** — actionability, not
completeness. The two are different, and the kit needs the second.

### Singular slots and collections

- **Singular** — one answer per project: `north_star`, `architecture_stance`, `verification`.
- **Collection** — one entry per instance: `actors`, `entities`, `actions` (actor × action),
  `screens`, `integrations`.

A collection has a two-level contract:

1. **Set completeness** — are all instances enumerated? Checked by cross-reference; catches
   "described three actions out of twelve".
2. **Entry shape** — each entry answers the same fixed questions. For an action:
   who → what triggers it → preconditions → what happens step by step → which entities change and to
   which status → what the initiator sees → what other actors see → what can go wrong.

### Actors, not roles

Roles are one kind of initiator. Generalizing the slot to `actors` keeps the cross-checks working on
projects with no roles at all:

| Actor kind | Where |
|---|---|
| user role | multi-user product |
| operator | single-user app, CLI |
| external system | webhook, integration, calling code of a library |
| schedule | cron, periodic run |
| the product itself | automatic actions, background rules |

"Every action has an initiator" and "every actor has actions" then hold for a data pipeline and a
library as well as for a marketplace.

### Anchors

The kit needs a machine anchor inside the owner's prose. An HTML comment is invisible when rendered
and does not disturb the text:

```markdown
### Создание оффера застройщиком
<!-- kit: developer.create_offer -->
```

**The agent places anchors, never the owner.** With existing docs, blueprint finds the entry
boundaries, shows the list — "found 23 actions, here is where the anchors go" — and writes them in
one commit on a single yes. This is the only moment the kit touches the owner's files, and it asks.
On a greenfield project the anchors are there from the start because blueprint authors the documents.

The anchor is its own line, not part of the heading, so renaming a heading does not break the
binding. Deleting a section is reported by `--check` as a missing entry.

If the owner refuses anchors, the fallback is a key → `file#heading` map. It works but drifts when
headings are renamed; anchors are the default.

### Derived index

Blueprint reads each entry **as prose** — no required subheadings, the form is the owner's — and
extracts the structural facts:

```yaml
# .agent-kit/knowledge/index.yml  (derived, regenerable)
actions:
  developer.create_offer:
    source: docs/user-stories/DEVELOPER_SELLER.md#L47
    rev: a3f1c9d                      # hash of the section when parsed
    actor: developer
    trigger: "opened a buyer request"
    entities_written: [ offer ]
    statuses_set: [ offer.pending ]
    reads: [ lot, request ]
    screens: [ S12 ]
    gaps: []

entities:
  offer:
    states: [ pending, accepted, rejected, withdrawn, expired ]
    created_by: [ developer.create_offer, agency.create_offer, system.direct_offer ]
```

Extraction is done by a grader **once per entry, cached against the section hash**. Rewriting one
document re-parses one entry, not fifty. The same pass judges entry shape and records what is
missing in `gaps`.

### Cross-checks — the highest-value part

Once entries are keyed, the checks are key comparisons rather than reasoning: fast, deterministic,
and they catch exactly the class of problem that reading with your eyes misses.

- an action sets a status → **does that status exist in the entity's lifecycle?**
- an action is available to an actor → **does the actor have that right in the access model?**
- a screen is on the map → **is there an actor who reaches it and an action launched from it?**
- an entity is created → **is there an action that creates it, and one that closes it?**

The screen map (`screens.data.js`) stays the authority for screens; actions reference screens by id
and the cross-check validates the reference. No duplication.

### Sample check output

```
$ blueprint --check

slots        38 filled · 1 not_applicable · 1 open_question
actions      23 entries · 2 findings
entities      7 entries · 1 finding

⚠ actions/broker.accept_offer
  sets deal.created — no `created` state in entities/deal
  (states are: draft, active, closed, cancelled)

⚠ actors/support
  declared, but no action is attributed to it

⚠ entities/complex
  no action creates it — is the reference book maintained by hand?

stale        docs/OFFERS.md changed since last parse (3 entries)
```

---

## 4. Blueprint — the single write point

One command owns the knowledge layer, in three modes plus a story pass:

```
blueprint              resume where the last session stopped
blueprint --check      audit only: filled, stale, conflicting
blueprint --resolve    walk pending annotations only (minutes)
blueprint --revisit X  deliberately rewrite one slot
blueprint --stories    walk the stories against current knowledge
```

### Idempotence and resumption

Every run is the same cycle: read state → verify freshness → work only on what is empty, stale or
conflicting. Three things make it reliable:

1. **Write after each slot, not at the end.** A killed session costs at most one slot. Same
   principle as the Run log: what is not on disk did not survive the context.
2. **Work list in dependency order.** Actors before scenarios, entities before invariants, MVP
   bounds after scenarios. Resumption takes the next slot whose dependencies are closed, not the
   next empty one.
3. **Deliberate exit.** "Enough for today" is a legal ending, and blueprint offers a pause when
   context runs short rather than degrading through the last twenty minutes of a session.

### The story pass

Separate from slots, and it is what actually decides whether `mvp` can execute: walk eight to ten
concrete scenarios with real names and real numbers through the assembled knowledge, step by step.
Wherever the answer is "well, we would add another field", the knowledge is wrong — and you see it
in five minutes rather than five weeks. Stories are recorded and re-walked on later runs.

### Other writers, demoted

- `ideate` / `riff` — append to the roadmap only, on an explicit yes. The roadmap is a queue, not
  knowledge.
- `docs-reflection` and ship's Docs step — fold into `--check`. One algorithm, called from two
  places.
- `screens` — owns the screen map, a machine artifact, its own category.

Five writers become three with non-overlapping lanes.

---

## 5. The feedback arc

Sufficiency is **not** determined at interview time; it is discovered by execution. Blueprint is not
required to be perfect — the loop is what makes it converge.

### Assumptions are gaps with a guess attached

`ship` and `sprint` already append assumptions to the Run log. When the agent records one, it tags
**which slot it stood in for**. At the end of the run those tags become annotations on slots. This
catches everything, not only what the agent thought to flag, and needs no new machinery.

The next blueprint then asks a qualitatively better question. Not *"tell me more about entities"*
but:

> In the run I assumed a cancelled request is kept with status `cancelled` rather than deleted. Correct?

A guess is the best possible form of a question.

### Filter by cost of being wrong

If every autonomous micro-decision becomes a question, the next blueprint is two hundred questions
and the owner stops running it. An annotation is raised only where the guess was **expensive to
reverse** — data model, permissions, money, a public contract — or where the agent's own confidence
was low. Everything else stays in the Run log as history.

### Two outcomes, not one

- **Gap** — no knowledge existed, the agent guessed → annotation carrying the guess.
- **Conflict** — knowledge existed but the code or another slot disagrees → `conflicts`, and more
  serious. A wrong answer is worse than a missing one: the agent is cautious around a gap and
  confident around wrong knowledge.

### Annotation record

An annotation lives *on* a slot and does not replace its status — status is about the knowledge,
an annotation about one point inside it. A slot can be `filled` and still carry open annotations.

```yaml
annotations:
  - from_run: claude/offer-roles
    at: 2026-08-02
    key: entities.request
    missing: "lifecycle of a cancelled request"
    assumed: "kept with status cancelled"
    cost_if_wrong: data_model
    resolved: false
```

Deduplicated by (slot, key, question hash) so three runs hitting the same gap raise one annotation.

### Reporting

The PR and the run report carry the price, not a vague instruction: *"12 assumptions, 3 need your
decision: request lifecycle, broker rights on another party's lot, commission rounding. Resolve
with `/agent-kit:blueprint --resolve`."* The owner sees the cost before deciding to spend time.

---

## 6. The knowledge gate in front of commands

All four build commands sit on the same knowledge layer. The gate is uniform; what differs is the
blast radius of the work.

Three distinct actions, often conflated:

| Action | Cost | Asks |
|---|---|---|
| `--check` | seconds; mechanical: source hashes, slot presence, verification commands actually run | no |
| `--resolve` | minutes; pending annotations only | yes |
| full interview | hours | yes |

**`--check` runs ahead of everything, including `fix`.** It is cheap and non-interactive.

**`--resolve` and the interview fire only when the work touches the slots concerned.** Otherwise a
typo fix opens a conversation about entity lifecycles and the owner starts hating the kit within a
week.

### Coverage is universal, annotation filtering is by blast radius

- `fix` — a CSS change is untouched by an annotation about request lifecycle; carry on.
- `ship` — the feature touches an entity with an open annotation → close it before starting.
- `sprint` — blast radius is the whole batch, so the filter is wider and fires **in the brief**.
- `mvp` — touches everything, so every annotation applies.

### Autonomy is a hard constraint

`sprint`'s contract is that nothing asks the owner after the brief's last question. A `--resolve`
inside a headless child would deadlock: nobody is there to answer and the session waits.

So: **the blueprint pass for a sprint lives in the brief, not in each child run.** Children run with
`--check` only, and whatever is missing becomes a logged assumption, i.e. an annotation for the
morning. General rule: **an autonomous run never asks — it assumes and marks.**

### Gate outcomes

- **clean** → proceed silently;
- **gaps in slots inside the blast radius** → interactive: one line and an offer to close;
  autonomous: refuse to start, or start with explicit degradation recorded in the report — policy
  per command. For `mvp` refuse: building a whole application on sand costs more than waiting;
- **conflict** → always surfaced, in every mode.

### One UX rule

**Silent when clean.** Not a line of audit output if everything is current. One line if the gate did
something. A screen only when it actually needs something from the owner. A gate that greets you on
every `fix` is a tax, and taxes get routed around.

Blueprint stops being a command you must remember and becomes a **layer the other four stand on**.

---

## 7. Command set after the cleanup

Nine become six and a half:

| Command | Note |
|---|---|
| `blueprint` | new. The knowledge layer: interview, check, resolve, stories |
| `mvp` | new. From blueprint to a running prototype — **pipeline not yet designed** |
| `ship` | one feature to a PR |
| `sprint` | a batch of features, autonomous |
| `fix` | something is wrong: your words, a PR review, or an observed failure |
| `screens` | the screen map |
| `riff` | under review — decide after the first blueprint |

Absorbed, not deleted:

- `debug` → internal skill, invoked by `fix` when the cause is unknown — **stage 0**;
- `address` → `fix --pr <n>`, same execution contract, different input source — **stage 0**;
- `screens-riff` → `riff` on a screen theme, keeping the ability to write proposals onto the map —
  **stage 0**;
- `docs` → blueprint's `--check` mode — **stage 7, not stage 0**. There is nothing to absorb it into
  until blueprint exists; removing it earlier would drop the capability for six stages.

Removing commands is a breaking change for a published marketplace plugin: bump the minor version,
record the moves in the changelog, add a `migrations/` note.

---

## 8. Decisions taken and questions still open

### Decided — implement as stated, do not re-litigate

1. **Blueprint is exempt from the knowledge gate.** It is what fills knowledge; requiring knowledge
   ahead of it is circular. It *does* run under the step gate, for state and resumption.
2. **Knowledge is pinned per run.** A run reads knowledge at start and works against that snapshot;
   mid-run edits are invisible to it. Recorded in the run state file. Prevents a six-hour run from
   seeing knowledge shift under it, and is what makes `--check`-at-start meaningful.
3. **The owner overrides the grader, and the override is recorded.** Marked `accepted_as_is` on the
   slot so the same disagreement is not re-opened at every check.
4. **Annotations survive work that never landed.** A closed-unmerged PR does not delete them; they
   are marked as coming from unlanded work. A question about the data model stays valid regardless
   of that PR's fate.
5. **Annotations are deduplicated** by (slot, key, question hash). Three runs hitting one gap raise
   one annotation.
6. **Anchors removed by hand** are reported by `--check`; the kit re-proposes and never silently
   re-adds.
7. **Contract versioning.** Slots added by a later kit version appear as `empty` in existing
   projects and are asked at the next blueprint, with a note under `migrations/`.
8. **Language.** Knowledge prose follows `manifest.language`; slot ids and rubrics stay English. The
   grader judges non-English prose against an English rubric.

### Still open

1. **Grader cost on first adoption.** Realest is roughly 23 actions + 7 entities + slots — on the
   order of 40–50 grader calls for the initial parse. Resolved by **measurement at stage 2**, not by
   discussion: run the parse against realest and record wall-clock and token cost in the PR. If it
   is expensive, cut by running mechanical checks first, batching entries per document, and caching
   harder against section hashes.
2. **`mvp` is not designed.** Its pipeline — skeleton batch composition, deploy/preview step,
   assumption journal, screenshots — was sketched in conversation but never specified. **Out of
   scope for this batch**; it gets its own design session after stages 0–7 land.
3. **`riff`'s survival.** Kept for now. Decide after the first real blueprint run, on evidence of
   whether the owner reaches for it. Removing it would also remove `ideate`'s broad scope.

---

## 9. Order of work

Each stage is useful on its own; the kit stays usable throughout.

**Stage 0 — cleanup.** Absorb `debug` and `address` into `fix`, and `screens-riff` into `riff`.
`docs` stays until stage 7 — there is nothing to absorb it into yet. Fewer pipelines to migrate onto
gates afterwards. Breaking release.

**Stage 1 — knowledge contract, mechanical half.** `contract.yml`, slot statuses, singular slots,
`--check` on hashes and the verification commands. No grader, no collections yet. Already worth
having: staleness detection.

**Stage 2 — collections and cross-checks.** Anchors, the derived index, entry-shape grading with
hash caching, the key cross-checks. This is where the contract starts finding real problems.

**Stage 3 — step gate.** Run state, the gate script with `run` / `exists` / `git` checks, `Stop`
moved onto state, write protection on `.agent-kit/runs/**`, named skips. Closes both of the holes in
section 1.

**Stage 4 — `pipelines.yml` in the project.** Configurable steps, checks and limits, seeded from a
template with the current behavior as the default.

**Stage 5 — the feedback arc.** Assumption tagging, annotations, `--resolve`, reporting in the PR.

**Stage 6 — the knowledge gate on commands.** `--check` ahead of everything, blast-radius filtering,
sprint's pass inside the brief.

**Stage 7 — `blueprint` proper.** The full interview, the story pass, adoption of an existing
project's docs. It comes last because everything above defines what it must produce.

**Stage 8 — `mvp`.** Design first, then build, on top of a knowledge layer that is by then real.
