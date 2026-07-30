# Sprint brief — knowledge contract and step gates

Input for `/agent-kit:sprint`. The design is settled in
[`knowledge-and-gates.md`](knowledge-and-gates.md); **read it first — it is the spec, this file is
the queue.** The brief phase should confirm the batch below, not re-derive it. Anything already
decided in the spec's section 8 is closed: do not re-open it.

Theme: **make every pipeline step verifiable, and give the kit a knowledge contract to stand on.**

---

## Batch — seven features, strict dependency order

Each stage is one `ship --brief` run. Later stages assume earlier ones landed; branches stack.

| # | Feature | Depth | Depends on |
|---|---|---|---|
| 0 | Command cleanup | light | — |
| 1 | Knowledge contract, mechanical half | normal | — |
| 2 | Collections, anchors, index, cross-checks | deep | 1 |
| 3 | Step gate: run state, gate script, hooks | deep | — |
| 4 | `pipelines.yml` in the project | normal | 3 |
| 5 | Feedback arc: annotations and `--resolve` | normal | 1, 2 |
| 6 | Knowledge gate in front of commands | normal | 1, 5 |

Stage 3 is independent of 1–2 and may run in parallel with them if the queue allows.

### 0 — Command cleanup

Absorb `debug` into `fix` as an internal skill invoked when the cause is unknown. Absorb `address`
into `fix --pr <n>` — same execution contract, different input source; the review-round pipeline is
preserved whole, only the entry point moves. Absorb `screens-riff` into `riff` on a screen theme,
**keeping its ability to write proposals onto the screen map** — losing that artifact would make
this a downgrade.

`docs` is **not** touched here. It is absorbed at stage 7, when blueprint's `--check` exists.
`riff` stays; its survival is decided later on evidence.

Breaking change to a published plugin: bump the minor version, record every move in `CHANGELOG.md`,
add a `migrations/<version>.md` note naming where each command went.

Done when: `scripts/validate.sh` is green, no skill references a removed skill, README's command
table matches reality.

### 1 — Knowledge contract, mechanical half

`.agent-kit/knowledge/contract.yml`: the slot list from the spec's section 3, slot statuses
(`filled` / `not_applicable` / `open_question`, with `empty` and `conflicts` forbidden as terminal
states), singular slots only — collections come at stage 2. Plus `--check` covering what needs no
grader: source paths resolve, section hashes match, the `verification` commands actually run and
return zero.

No grader, no anchors, no collections in this stage.

Done when: `--check` runs against this repository and reports honestly; a deliberately stale source
is detected.

### 2 — Collections, anchors, index, cross-checks

Collection slots, the anchor convention (`<!-- kit: <key> -->`, placed by the agent on the owner's
approval, its own line so heading renames do not break it), the derived `index.yml`, grader-based
entry parsing cached against section hashes, and the cross-checks from the spec.

**Verification is the point of this stage:** run the parser against `/projects/realest` (read-only,
never write there) and put the report in the PR — entries found, cross-check findings, and the
measured cost of the parse in wall-clock and tokens. That measurement closes open question 1.

### 3 — Step gate

`.agent-kit/runs/<branch>.yml`, the gate script with `step start` / `settle` / `skip`, checks of
kind `run` / `exists` / `git`, attempt counting and `on_exhausted`. `Stop` moves onto run state
instead of parsing the plan's markdown. New `PreToolUse: Write|Edit` hook refusing writes to
`.agent-kit/runs/**`, and the Bash guard extended to match. Skips become named-only.

**Editing hooks here is safe and testable without a human.** The plugin runs from
`~/.claude/plugins/cache/agent-kit/agent-kit/<version>/`, not from this working tree, so repo edits
are inert until `claude plugin update`. Test the hooks by piping crafted JSON events into the
scripts directly and asserting the decision, exactly as a unit test would.

Every hook must fail open on a parse error, as `stop-guard.py` already does.

### 4 — `pipelines.yml` in the project

Project-owned pipeline definitions seeded from a plugin template whose defaults reproduce current
behavior. `commands:` block becomes the single source of the project's commands. Validation of the
file — referenced commands exist, globs parse, limits present — in `scripts/validate.sh` and once at
run start.

### 5 — Feedback arc

Assumption tagging (which slot the assumption stood in for), annotations on slots with the record
shape from the spec, deduplication, the cost-of-being-wrong filter, `blueprint --resolve`, and the
report line in the PR naming what needs the owner and what it costs.

`blueprint` does not exist yet at this point: implement `--resolve` as the entry point it will
later own, and wire the writing side from `ship` / `sprint`.

### 6 — Knowledge gate in front of commands

`--check` ahead of every build command including `fix`; `--resolve` and interview only when the work
touches the slots concerned; blast-radius filtering per command; sprint's pass moved into the brief
so no headless child ever asks. Silent when clean.

---

## Constraints for every run in this batch

- **Autonomous contract.** After the brief, nothing asks the owner until the final report. Anything
  unresolved becomes a logged assumption, per the kit's own rules.
- **Repository conventions.** Code, identifiers, paths, commit messages and documents under `docs/`
  are English; the PR description is Russian (`manifest.language: ru`). Work on `claude/` branches.
  Never merge — the owner merges.
- **Verification.** `scripts/validate.sh` is this repository's test command and must stay green.
  Scripts added in stages 1–3 need their own tests; there is no test framework here, so plain
  executable checks invoked from `validate.sh` are the right shape.
- **The kit is not bootstrapped on itself** (`manifest.bootstrapped: false`): there is no roadmap to
  select tasks from, and none is needed — every feature in this batch is named here.
- **`/projects/realest` is a read-only test corpus.** Read its docs freely; never write there.
- **Ownership boundary holds.** Everything under `plugins/agent-kit/` is the plugin's and is replaced
  by an update; `.agent-kit/project/**` and `.agent-kit/knowledge/**` belong to the project.

## Out of scope

- `mvp` — not designed; its own session after this batch.
- `blueprint` proper (stage 7) — deliberately excluded. Its shape depends on stages 1–2 proving out,
  and it is cheaper to build once on a validated contract than to rewrite it.
- Removing `riff` or `docs`.

## Where the owner is needed

Merging the integration PR. Nothing else.
