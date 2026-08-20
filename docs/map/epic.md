# Sector: epic

Sources read in full: `plugins/agent-kit/skills/epic/SKILL.md`,
`plugins/agent-kit/skills/epic/references/finish.md`, `plugins/agent-kit/verification.yml`, plus
targeted reads of `plugins/agent-kit/scripts/orchestrate.py`, `plugins/agent-kit/hooks/stop.py`,
`plugins/agent-kit/scripts/runfile.py`, `plugins/agent-kit/scripts/check.py` (check_epic,
run_defects, --state, --run), `plugins/agent-kit/templates/run.json`,
`plugins/agent-kit/templates/batch.json`, and the referenced `rules/preflight.md`,
`rules/closing.md`, `rules/window.md`, `skills/sprint/references/close.md`,
`skills/audit/SKILL.md` (headers only, as context for the hand-off — full mapping of those files
belongs to other sectors).

## NODES

`id | kind | label | one-sentence description | source file:line`

| id | kind | label | description | source |
|---|---|---|---|---|
| cmd:epic | cmd | `/agent-kit:epic` | Whole-scope command: gate once, then compose/hand off batches until the scope is built, audited and proved, as one PR. | plugins/agent-kit/skills/epic/SKILL.md:1-18 |
| gate:tmux-check | gate | tmux precondition | `command -v tmux`; without it the driver cannot give a feature its own session. | epic/SKILL.md:35-37 |
| gate:epic-check | gate | `check.py --epic` | Fatal-or-silent precondition check: MVP bounds, scenarios, `commands.run`/`commands.test`, verification catalogue answered. | epic/SKILL.md:40,44-46; check.py:849-921 |
| gate:status-state | gate | `check.py --status --state` | Preflight: run-in-flight lines, entry counts, scenarios described/covered, tests-mutation line, audits. | epic/SKILL.md:41,46-60; check.py:3261-3303 |
| gate:derive-inlist | gate | Derive the in-list | Maps owner's scope choice (MVP bounds / planned / owed / named list) to entry keys not yet built. | epic/SKILL.md:62-101 |
| gate:entries-settle | gate | Settle open blocks | `check.py --entries <keys>` prints open `[assumed]`/`[stale]` blocks on built+planned entries; owner settles the expensive ones on screen. | epic/SKILL.md:83-101 |
| gate:order-batches | gate | Order and batch | Derives build order from scenario-step/entry preconditions; groups into ~5-entry batches, one topic each; assigns each scenario's e2e test to the feature closing its last step. | epic/SKILL.md:103-115 |
| gate:price | gate | Price in hours | Prices the scope from `docs/runs/*.json` `spent`, or ~1h/feature fallback; prices audit separately; prices any content-heavy entries by counted items. | epic/SKILL.md:122-141 |
| gate:harness | gate | Say what proves it | Names the e2e harness that will prove the finish line, or says none exists and what building one costs. | epic/SKILL.md:143-147 |
| gate:parts-seen | gate | Parts seen by owner | Reports "Parts: N recorded, M walked, K derived"; walks any unread part the scope builds on, live, at the gate. | epic/SKILL.md:149-164 |
| gate:invented-record | gate | Record what the conversation invents | Anything the owner describes that is not in the description gets written down (as an assumption or as a new `planned` entry) before the run starts. | epic/SKILL.md:166-173 |
| gate:rank-questions | gate | Rank questions and blocks | Puts the ~5 most consequential entries and the highest-stakes open blocks up as owner choices; rest decided and recorded silently. | epic/SKILL.md:175-187 |
| gate:screen | gate | The one screen | Single combined screen: scope+finish line, batches in order, price, audit cost, unread parts, "this scope or narrower?" — one round of asking. | epic/SKILL.md:189-205 |
| phase:gate | phase | Gate phase | `step: "gate"`; the only owner conversation in the whole run. | epic/SKILL.md:221 |
| phase:building | phase | Building phase | `step: "building"`; batches run one after another via the driver. | epic/SKILL.md:222,272 |
| phase:auditing | phase | Auditing phase | `step: "auditing"`; up to 3 waves of lens audits + fix batches. | epic/SKILL.md:222; finish.md:1-72 |
| phase:proving | phase | Proving phase | `step: "proving"`; scenario e2e coverage, epic-scoped verification kinds, fresh-worktree boot check. | epic/SKILL.md:222; finish.md:74-131 |
| phase:done | phase | Done/finish | `step: "done"`; PR closing summary written, then step set — session closes via Stop hook. | epic/SKILL.md:222-229; finish.md:133-172 |
| script:check.py | script | `scripts/check.py` | Multi-purpose CLI: `--epic`, `--status --state`, `--entries`, `--run`, `--sync`, `--manual`. | plugins/agent-kit/scripts/check.py |
| script:orchestrate.py | script | `scripts/orchestrate.py` (the driver) | Drives one batch's children one session at a time; hands back to `epic --advance` when the batch (or run) is done. | plugins/agent-kit/scripts/orchestrate.py:1-14 |
| script:runfile.py | script | `scripts/runfile.py` | Shared run-file model: `kind()`, `TERMINAL`, `STALE_AFTER`, `project_root()`, `resume_command()`. | plugins/agent-kit/scripts/runfile.py |
| hook:stop.py | hook | Stop hook | Blocks a turn ending while a non-epic run is mid-step; for `epic` lets steps end turns; closes the hand-back session once the epic reaches a terminal step. | plugins/agent-kit/hooks/stop.py:1-24,88-131,189-199 |
| hook:guard.py | hook | Guard (PreToolUse) | Referenced only: refuses merge/force-push/push-to-default during any run in flight, including epic's proving phase. | plugins/agent-kit/hooks/guard.py:28,229 |
| session:gate-session | session | The gate session | The session running bare `/agent-kit:epic`; ends after starting the driver on batch 1. | epic/SKILL.md:20-27,272-285 |
| session:advance-session | session | `--advance` session | Started by the driver's hand-back after a batch closes; decides what follows, starts it, ends. | epic/SKILL.md:23,292-360; orchestrate.py:1182-1201 |
| session:resume-session | session | `--resume` session | Started by hand (owner/operator) when a run stalled; reconstructs state, restarts driver or advances. | epic/SKILL.md:24,374-396 |
| session:driver-process | session | Driver process | `orchestrate.py`, launched with `nohup`, detaches itself from the tmux control-group before doing anything, runs a batch's children in order. | epic/SKILL.md:274-281; orchestrate.py:1229-end |
| session:batch-close | session | Batch-closing session | `/agent-kit:sprint --close <dir>`, started by the driver at the end of a batch's children; writes docs/runs record, PR body/digest. | orchestrate.py:1150-1170; sprint/references/close.md:1-40 |
| session:audit-child | session | Audit-lens child session | `/agent-kit:audit <lens> --run <dir>`, started by the driver as a batch child, one lens = one unit of work. | finish.md:23-28; audit/SKILL.md:20-49 |
| file:run.json-epic | file | Epic's own run.json | `.agent-kit/runs/<date>-epic-<slug>/run.json`; `command:"epic"`, `step`, `entries`, `children` (batch slugs, epic-owned list), `window`, `finish`, `model`. | epic/SKILL.md:209-244; templates/run.json |
| file:run.json-batch | file | A batch's run.json | `command:"sprint"`, `parent` = epic run, children = features (`deliver:"branch"`, `gate:"none"`), own `model`, chained bases. | epic/SKILL.md:246-256 |
| file:frame-child | file | Frame child run file | First child of any batch of ≥3; `/agent-kit:sprint --frame <dir>`; produces `frame` map of feature dependencies. | epic/SKILL.md:251-256; templates/run.json (`_frame`) |
| file:docs-runs-json | file | `docs/runs/<slug>.json` | Durable batch record: `pr`, `branches`, `spent`, counts — survives machine loss; feeds next epic's price and `next`'s branch cleanup. | templates/batch.json; epic/SKILL.md:296-301 |
| file:docs-audits | file | `docs/audits/<lens>.md` | One file per lens, rewritten whole each wave; carries forward findings from narrower walks. | finish.md:49-52 |
| file:docs-technical-debt | file | `docs/technical_debt.md` | The ledger; "owed" scope reads it; batches close/add items into it. | epic/SKILL.md:71 (owed scope); templates/run.json (`_deferred`,`_closed_debt`) |
| file:product-md | file | `docs/knowledge/product.md` | Holds MVP bounds section (marker/heading), read by `check_epic`. | check.py:849-877 |
| file:scenarios-md | file | `docs/knowledge/scenarios.md` | Holds scenario headings, read by `check_epic` and by `scenarios()` for described/covered counts. | check.py:882-885,3164,3261-3263 |
| file:project-yml | file | `.agent-kit/project.yml` | `commands.run`/`commands.test`/`commands.e2e`/`commands.mutate`, `verification` catalogue answers. | check.py:886-921; SKILL.md:44 |
| file:verification-yml | file | `plugins/agent-kit/verification.yml` | Catalogue of verification kinds; `runs: epic` ones (`end_to_end`, `contract`, `performance`, `security`) are gathered in the proving phase. | verification.yml:1-92 |
| file:control | file | Batch `control` file | Owner instruction channel (`stop`, `skip <slug>`) the driver reads once per child. | epic/SKILL.md:341; orchestrate.py:1032-1052 |
| ext:tmux | ext | tmux | Session/window mechanism the whole kit's sessions run inside; required for the driver to give each feature its own session. | epic/SKILL.md:35-37 |
| ext:gh | ext | GitHub CLI | Used (by close/orchestrate, not epic itself) to open/rewrite the one pull request. | orchestrate.py imports check via subprocess `gh`... (see check.py:1339 for pattern) |
| ext:git-worktree | ext | `git worktree add` | Used in the proving phase to boot the branch fresh, isolated from the run's own working tree. | finish.md:109-119,163-172 |
| rule:preflight | rule | `rules/preflight.md` | Shared reaction table to what `check.py` finds (run in flight, unsettled blocks, missing knowledge, etc.), read by epic's gate. | rules/preflight.md |
| rule:closing | rule | `rules/closing.md` | Shared "how a command speaks" rule: first line, language, soft spots, next command — read before the gate session closes. | rules/closing.md |
| rule:window | rule | `rules/window.md` | Defines the control-window role the gate session becomes after closing: reports, never decides, never asks. | rules/window.md |
| rule:asking | rule | `rules/asking.md` | Referenced for how the gate's single screen is built (pre-fetched numbers, one round). | epic/SKILL.md:189-200 (referenced, not fully read here) |
| rule:pull-requests | rule | `rules/pull-requests.md` | Settles that the finish does not re-review the whole diff. | finish.md:148-150 |

## EDGES

`from-id -> to-id | mechanism | trigger/condition | source file:line`

- cmd:epic -> gate:tmux-check | invokes | bare invocation, before anything else | epic/SKILL.md:35-37
- cmd:epic -> gate:epic-check | invokes | after tmux check | epic/SKILL.md:40
- gate:epic-check -> script:check.py | invokes | `check.py . --epic` | epic/SKILL.md:40; check.py:849
- gate:epic-check -> cmd:epic | blocks | fatal finding (no bounds/scenarios/commands/unanswered verification kinds) → run does not start, offer `blueprint` | epic/SKILL.md:44-46; check.py:875,888,904-921
- cmd:epic -> gate:status-state | invokes | `check.py . --status --state` | epic/SKILL.md:41
- gate:status-state -> script:check.py | invokes | reads scenarios described/covered, tests-mutation state, audits history | check.py:3261-3303
- gate:derive-inlist -> file:product-md | reads | maps owner's prose scope to entry keys via MVP bounds section and entry headings | epic/SKILL.md:79-81
- gate:derive-inlist -> file:docs-technical-debt | reads | for "what is owed" scope | epic/SKILL.md:71
- gate:entries-settle -> script:check.py | invokes | `check.py . --entries <keys>` prints open blocks, names bad keys | epic/SKILL.md:89-93
- gate:entries-settle -> file:product-md | writes | transcribed answers into entries, block deleted, committed `docs(knowledge):` before batch 1 | epic/SKILL.md:95-96
- gate:order-batches -> gate:invented-record | hands-off | scenario/entry ordering also decides which feature writes which scenario's e2e test | epic/SKILL.md:108-115
- gate:price -> file:docs-runs-json | reads | rate taken from `docs/runs/*.json` `spent`, else ~1h/feature fallback | epic/SKILL.md:125-128
- gate:harness -> file:project-yml | reads | names `stack.md`/commands harness that will prove the finish line | epic/SKILL.md:143-147
- gate:screen -> cmd:epic | blocks | the one owner round; run does not proceed until answered | epic/SKILL.md:189-205
- gate:screen -> phase:gate | returns-to | answer settles scope, batches, model, price into `finish` | epic/SKILL.md:189-244
- phase:gate -> file:run.json-epic | writes | `step:"gate"`, then `entries`, `children`, `window`, `finish`, `model` | epic/SKILL.md:209-244
- phase:gate -> file:run.json-batch | writes | writes only the next/first batch's run file (sprint-shaped), never batches ahead | epic/SKILL.md:246-249
- phase:gate -> file:frame-child | writes | for a batch of ≥3, writes a frame child exactly as sprint's SKILL.md does | epic/SKILL.md:251-256
- phase:gate -> ext:git-worktree | hands-off | branch `epic/<slug>` created off the session's current branch (not default) | epic/SKILL.md:258-262
- phase:gate -> session:driver-process | spawns | `nohup python3 orchestrate.py <first batch>/ >> driver.out 2>&1 &`, moves itself out of tmux control group | epic/SKILL.md:272-281; orchestrate.py (DETACHED section, end of file)
- phase:gate -> file:run.json-epic | writes | `step:"building"` set right before starting the driver | epic/SKILL.md:272
- session:gate-session -> rule:closing | invokes | close per rules/closing.md | epic/SKILL.md:283
- session:gate-session -> rule:window | delegates | stays as the control window after closing | epic/SKILL.md:283-290
- session:driver-process -> script:orchestrate.py | invokes | drives batch's `children` list, one `claude` session per child | orchestrate.py:1-14,1043-1128
- session:driver-process -> session:audit-child | spawns | when a batch child's `prompt` names `/agent-kit:audit <lens> --run <dir>` (an "errand", not a `ship`) | orchestrate.py:833-843; finish.md:23-28
- session:driver-process -> session:batch-close | spawns | `/agent-kit:sprint --close <dir>` once all children in `children` are seen | orchestrate.py:1150-1153
- session:batch-close -> file:docs-runs-json | writes | closing session writes durable record: `pr`, `branches`, `spent`, counts | epic/SKILL.md:296-301; templates/batch.json
- session:driver-process -> file:run.json-batch | writes | `step` per child, `step:"closing"`→`"done"`/`"blocked"` on the batch itself | orchestrate.py:1128-1170
- session:driver-process -> session:advance-session | spawns/hands-off | `hand_back()`: starts `/agent-kit:epic --advance <epic dir>` on the epic's own `model`, only if batch's `parent`'s `command` is `epic`/`mvp` | orchestrate.py:1216-1236
- session:driver-process -> file:run.json-epic | writes | writes hand-back session name into epic's `session` field, read later by stop hook | orchestrate.py:1230-1236
- session:advance-session -> script:check.py | invokes | `check.py . --run <closed batch dir>` — "did it really close" gate before doing anything else | epic/SKILL.md:294-298
- script:check.py -> session:advance-session | blocks | non-silent output means the batch closed badly — named in report/PR, not silently redone | epic/SKILL.md:301-307
- session:advance-session -> file:run.json-batch | writes | writes next batch's run file (+ frame child if ≥3) when `children` still has entries left | epic/SKILL.md:311-313
- session:advance-session -> session:driver-process | spawns | starts driver on next batch | epic/SKILL.md:311-313; epic/SKILL.md:272-281
- session:advance-session -> phase:auditing | invokes | when the in-list is fully built: `step:"auditing"`, moves to finish.md | epic/SKILL.md:314
- session:advance-session -> phase:proving | invokes | when the audit is done: `step:"proving"` | epic/SKILL.md:315
- session:advance-session -> phase:done | invokes | when scenarios pass: writes PR finish, then `step:"done"` | epic/SKILL.md:316
- session:advance-session -> file:run.json-epic | writes | may reorder/drop/add batches in `children`; sets a dropped batch's own `step:"skipped"` | epic/SKILL.md:335-341
- session:advance-session -> file:control | writes | can stop the run by writing `stop` into the current batch's control file | epic/SKILL.md:341
- phase:auditing -> file:run.json-epic | reads/writes | `finish.lenses` chosen and written here (not at the gate) | epic/SKILL.md:217-219; finish.md:54-60
- phase:auditing -> file:run.json-batch | writes | one batch per wave, one child per lens-unit-of-work | finish.md:17-21
- phase:auditing -> session:audit-child | spawns | child's whole `prompt` is `/agent-kit:audit <lens> --run <its own dir>` | finish.md:23-28
- session:audit-child -> file:docs-audits | writes | `docs/audits/<lens>.md` rewritten whole per wave | finish.md:49-52; audit/SKILL.md description
- phase:auditing -> phase:auditing | loops-to | wave repeats while a lens still returns real (non-minor) gaps, up to `finish.waves` (default 3) | finish.md:62-72
- phase:auditing -> phase:proving | hands-off | once waves exhausted or all lenses return only minors/"also noticed" | finish.md:65-72
- phase:proving -> script:check.py | invokes | `check.py . --state` to count scenarios described vs covered by e2e test | finish.md:78-84
- phase:proving -> file:verification-yml | reads | runs the kinds this project answered for whose `runs: epic` | finish.md:96-103; verification.yml (end_to_end, contract, performance, security)
- phase:proving -> ext:git-worktree | invokes | `git worktree add /tmp/<slug>-preview epic/<slug>`, boots via `commands.run`, walks scenarios there | finish.md:109-119
- phase:proving -> phase:auditing | loops-to (recovery) | a scenario with no e2e test becomes one more sprint composed from the scenarios lens | finish.md:86-90
- phase:done -> file:docs-runs-json | reads | the run does not itself flip entries to `built`; that is `check.py --sync` after PR merges | finish.md:135-139
- phase:done -> ext:gh | hands-off | closing summary written into the one pull request | finish.md:141-146
- phase:done -> file:run.json-epic | writes | `step:"done"` written **last**, after the summary | finish.md:143-146; epic/SKILL.md:316-323
- file:run.json-epic -> hook:stop.py | reads | Stop hook reads epic's own `session` field and `step` to know when to close the hand-back session | stop.py:108-130
- hook:stop.py -> session:advance-session | invokes(closes) | `finished_epic()` finds this session's own epic at a terminal step within `STALE_AFTER`(24h) and calls `close_myself` | stop.py:108-130,192-199
- hook:stop.py -> session:gate-session/advance-session | blocks | for non-epic runs, blocks turn-end mid-step; for `epic` kind specifically, **never blocks** (steps belong to the run, not the turn) | stop.py:91-96
- hook:guard.py -> phase:proving | blocks | (context only) guard leaves the proving phase's real merges/pushes alone per its own exception list | guard.py:28,229 (full mapping belongs to guard's own sector)
- session:resume-session -> file:run.json-epic | reads | rebuilds run state: which batches terminal, which current, which children unfinished | epic/SKILL.md:381-384
- session:resume-session -> session:driver-process | spawns | starts driver on the current (incomplete) batch, or calls `--advance` if that batch is done | epic/SKILL.md:383-384
- session:resume-session -> session:driver-process | refuses | never starts a second driver over a live one; trusts the driver's own live-session check | epic/SKILL.md:394-396

## PHASE SPINE

1. **gate** (`step:"gate"`) — entry: bare `/agent-kit:epic` invocation. Preconditions: `tmux` present; `check.py --epic` silent (MVP bounds, ≥1 scenario, `commands.run`/`commands.test` present and runnable, verification catalogue fully answered) — epic/SKILL.md:35-46, check.py:849-921. Body: derive in-list from chosen scope, settle open knowledge blocks, order into batches, price in hours, name the proving harness, report unread parts, record invented material, rank questions/blocks, ask the one screen. Exit: owner answers the single screen → write `run.json` (`entries`, `children`=[first batch], `window`, `finish`, `model`), write the first batch's run file (+frame child if ≥3), create `epic/<slug>` branch, set `step:"building"`, start the driver, close the gate session into the control window. — epic/SKILL.md:207-290

2. **building** (`step:"building"`, epic's own file; the driven batch files carry `step: building/closing/done/blocked`) — entry: driver started on a batch. Body: driver runs each batch child (`ship` by default, or whatever `prompt` names) in sequence, respecting `needs`/`frame`; closes the batch via `sprint --close`; hands back to a fresh `epic --advance` session naming the epic's `model`. Exit for one batch: `--advance` finds batches left in `children` → writes/starts the next one, loops back into **building**. Exit for the whole phase: the in-list is built (no batches left) → `--advance` sets `step:"auditing"`. — epic/SKILL.md:292-323; finish.md's ordering line 1 "the in-list is built"

3. **auditing** (`step:"auditing"`) — entry: `--advance` after last building batch. Preconditions/setup: lenses chosen here (not at the gate) from what was actually built, written into `finish.lenses` with the reason; `tests`/`scenarios` lenses scoped to the run's own `entries`, `deps`/`security`/`conventions` run unscoped. Body: wave = audit → fix sprint(s) → re-audit; one batch per wave (one child per lens's unit of work), audit child's whole prompt is `/agent-kit:audit <lens> --run <dir>`. Exit condition per wave: a lens returning only minors/"also noticed" is not re-run; a lens with real gaps loops the wave again, capped at `finish.waves` (default 3, set once at the gate and never raised). Exit for the phase: all lenses quiet or cap reached (remainder named in the PR, not dropped) → `--advance` sets `step:"proving"`. — finish.md:1-72

4. **proving** (`step:"proving"`) — entry: `--advance` after audit phase ends. Body: `check.py --state` counts scenarios described vs. covered by an `agent-kit:scenario <heading>`-tagged e2e test; a gap becomes a scenarios-lens-composed fix sprint (recovery, not the plan — the gate already assigned test ownership); run every epic-scoped verification kind the project answered for (`verification.yml` → `runs: epic`: `end_to_end`, `contract`, `performance`, `security`), reporting each by name/result, refusals stated as facts; boot the app once via `commands.run` in a **fresh worktree** (`git worktree add /tmp/<slug>-preview epic/<slug>`), not the run's own tree, and walk what the scenarios walk; anything manual that could be scripted goes into `commands.run`, the rest into Manual actions. Exit: every scenario inside the bounds has a test and passes, suite green on the fresh worktree → `--advance` proceeds to **done**. — finish.md:74-131

5. **done** (`step:"done"`, terminal) — entry: proving phase satisfied. Body: write the PR's closing summary (what the product does, which scenarios are proved and by which tests, what the audit left, every assumption taken without the owner, what did not happen, the untested-elsewhere-suite caveat, every stand-in a proof went through), no fresh full-diff review (already reviewed twice: per-entry reviewer + audit lenses), repeat the fresh-worktree preview line. Exit: `step:"done"` is written **last**, after the summary — the Stop hook then closes the `--advance` session at the end of the first turn that finds the run terminal, since nothing else will. — finish.md:133-172; epic/SKILL.md:316-323; stop.py:108-130,192-199

Note: `blocked` is a parallel terminal outcome available at the run level and at the batch level, always with the reason written to the PR/report first, before the field is set. — epic/SKILL.md:322-323,362-365

## IO TABLE

| node-id | reads | writes |
|---|---|---|
| gate:epic-check | `docs/knowledge/product.md`, `docs/knowledge/scenarios.md`, `.agent-kit/project.yml` (via check_epic) | Report lines only (no file writes) |
| gate:status-state | `.agent-kit/project.yml`, `docs/knowledge/scenarios.md`, `docs/audits/*.md`, run files under `.agent-kit/runs/` | none |
| gate:entries-settle | `docs/knowledge/*.md` (open `[assumed]`/`[stale]` blocks) | `docs/knowledge/*.md` (transcribed answers, blocks deleted), one `docs(knowledge):` commit |
| gate:order-batches / whole gate | `docs/knowledge/scenarios.md`, `docs/knowledge/product.md` (MVP bounds), `docs/runs/*.json` (`spent`) | `.agent-kit/runs/<epic-slug>/run.json`, `.agent-kit/runs/<first-batch>/run.json` (+ frame child run.json) |
| session:driver-process | epic's `run.json`, batch's `run.json`, each child's `run.json`, `control` file | each child's `step`/`blockers`/`needs`/`frame` fields, batch's `step`/`spent`, epic's `session` field (on hand-back) |
| session:batch-close | batch `run.json`, every child's `run.json` | branch `epic/<slug>` (fast-forwarded, or `sprint/<slug>` outside an epic), the one PR (opened by batch 1, body rewritten + digest comment by later batches), `docs/runs/<slug>.json` |
| session:audit-child | its own run file's `entries`/`task`, the codebase, `docs/knowledge/*.md` | `docs/audits/<lens>.md` (whole file rewritten), its own run file's `step`/commit |
| session:advance-session | closed batch's `docs/runs/<slug>.json` record (via `check.py --run`), epic's `run.json`, batch run files | epic's `run.json` (`step`, `children`, `finish.lenses` at audit entry), next batch's run file, `control` file (to stop) |
| phase:proving | `.agent-kit/project.yml` → `verification`, `verification.yml`, `docs/knowledge/scenarios.md` via `check.py --state` | test files (`agent-kit:scenario` tags), `commands.run` edits, the PR's Manual actions section |
| phase:done | all of the above run files and `docs/audits/*.md` | the PR closing summary; epic `run.json` `step:"done"` |
| hook:stop.py | the epic's own `run.json` (`session`, `step`, `kind`), `STALE_AFTER` clock | closes the tmux session (via `claude-close` or `tmux kill-session`); no file writes |

## OWNER GATES

The single conversation of an entire epic run, in order (epic/SKILL.md:29-205):

1. **Scope choice** — trigger: always, first substantive question. Options: MVP bounds (default when nothing said) / everything still `planned` / everything owed (debt+open audit items+broken promises) / a list the owner names. Effect: fixes the in-list and the finish line for the whole run, non-negotiable afterwards. Waits: yes, this is part of the one screen. — SKILL.md:62-77
2. **Expensive open blocks / decisions on entries the scope touches** — trigger: `check.py --entries` surfaces `[assumed]`/`[stale]` blocks ranked by what they touch (stored data, permissions, money, outside contracts) on built-and-planned entries alike. Options: settle each on the screen. Effect: transcribed into the entry, block deleted, committed before batch 1; unsettled ones stand as written. Waits: yes, same screen. — SKILL.md:83-101,182-187
3. **Ranked entry decisions** — trigger: the ~5 (of a typical 20) entries about to be built whose decisions are most expensive to get wrong. Options: owner's call per decision. Effect: decided on the spot; the rest the run decides and records itself. Waits: yes. — SKILL.md:175-180
4. **The harness / finish-mechanism gap** — trigger: `scenarios: N described, M with an end-to-end test` shows M=0 or no `commands.e2e`. Effect: stated as a fact on the screen (finish cannot be reached mechanically); offer of `/agent-kit:blueprint` to build a harness, priced as its own batch if wanted now. Waits: as part of the one screen; can be deferred to after this run. — SKILL.md:50-60,143-147
5. **Whether tests can be proven to fail** — trigger: no `commands.mutate`. Effect: stated as a fact beside the price (every feature reports mutation as "not run" all night). Not separately asked — offer is one line: before this run, or not at all. — SKILL.md:57-60
6. **Unread description parts** — trigger: `check.py --state` "Parts: N recorded, M walked, K derived." Effect: stated as fact; a part the scope only mentions waits (offered `/agent-kit:blueprint` after this run); a part the scope **builds on** is walked live, right at the gate, before the run starts. Waits: yes for the "builds on" case. — SKILL.md:149-164
7. **Content-heavy entries** — trigger: an entry whose scope is unbounded writing work (copy, seed data, cards). Effect: the actual count is found before the screen and shown, plus the fact that no test will say the content is *right*. Waits: as part of the one screen (informational, not really a choice). — SKILL.md:130-137
8. **Audit cost as a separate choice** — trigger: always, once lenses are estimated as roughly as costly as the build itself. Effect: shown as "two waves against one, with what each costs" — a choice on the screen. Waits: yes. — SKILL.md:139-141
9. **Model** — trigger: always. Effect: default is the model the gate session itself is running on; shown on the screen beside the price; a cheaper model the owner names is pushed to the children's run files only, never to the epic's own file. Waits: yes, part of the one screen. — SKILL.md:231-244
10. **Final: "this scope, or narrower?"** — trigger: closes the screen. Options with counts, one round only (per `rules/asking.md`). Effect: locks everything above into `finish` and the run files; starts the driver. Waits: yes — this is the entire wait of the whole run. — SKILL.md:189-205

**Nothing else is ever asked.** Every `--advance` and every child runs with `gate:"none"`; an expensive fork becomes a recorded assumption surfaced in the PR, never a wait. — SKILL.md:202-205,350-353

## REFUSALS, STALLS AND RECOVERY

- **Gate refuses to start**: `check.py --epic` fatal (no MVP bounds/marker, <2 filled bound-lists, no scenarios, missing/non-functional `commands.run`/`commands.test`, unreadable or unanswered verification catalogue) → says what's missing, offers `/agent-kit:blueprint`, run never begins. — epic/SKILL.md:44-46; check.py:849-921
- **No tmux** → said before the owner answers anything, run does not start. — epic/SKILL.md:35-37
- **A batch closes badly** (`check.py --run <batch dir>` prints output instead of staying silent) → `--advance` does **not** redo the work; names it as blocked/named in the report and PR. — epic/SKILL.md:294-307
- **A batch ends blocked** → does not stop the run; its features' entries stay `planned`, named in the PR as what did not happen; the next batch still starts. — epic/SKILL.md:362-365
- **Dirty working tree before a batch** → `--advance` reports it and stops (does not start the batch); `--resume` continues once the tree is clean. — epic/SKILL.md:367-369
- **The driver stalls** (session dies, account limit, restart fails) → `orchestrate.py` restarts/nudges per its own stall logic (outside this sector); ultimately, if nothing recovers, the run sits until `--resume`. — epic/SKILL.md:376-378
- **Hand-back session fails to start** (`launcher.start` fails in `hand_back`) → driver logs "stalled", tells the window: `"<slug> needs /agent-kit:epic --resume — the next batch did not start"`; no further driver runs until then. — orchestrate.py:1237-1239; epic/SKILL.md:294 (mirrors this warning)
- **A hand-back/advance session dies before starting anything or before writing a next step** → nothing watches it; run sits until `--resume`. — epic/SKILL.md:376-378
- **A previously-finished epic's hand-back session is never closed** by anything else → the Stop hook's `finished_epic()` closes it, but only if the run file's `step` is terminal *and* was written within `STALE_AFTER` (24h); a session tied to an epic finished over a day ago is no longer auto-closed by this mechanism. — stop.py:108-130
- **`--resume` reconstructs**: reads the epic's own `run.json` and every batch's `run.json` to determine which batches are terminal, which is current, which of the current batch's children are unfinished; asks the owner nothing (`finish` already holds every gate answer); starts the driver on the current batch (it skips terminal children) or calls `--advance` if that batch is already done. If run files were lost/rolled back, a batch is rewritten under the ordinary gate rules — including, if forgotten, the frame child for batches of ≥3 (explicitly flagged as the thing that gets missed). — epic/SKILL.md:374-392
- **Never starts a second driver over a live one** — trusts the driver's own live-session refusal rather than guessing. — epic/SKILL.md:394-396
- **Owner-initiated stop** — writing `stop` into the current batch's `control` file; the driver reads it once per child transition (`skip <slug>` is the other recognized instruction). — epic/SKILL.md:341; orchestrate.py:1032-1052
- **Non-epic runs vs epic runs at the Stop hook**: for any *other* kind of run, the Stop hook blocks turn-ending while `step` is non-terminal (`unfinished()`); for `epic` specifically this check is skipped outright — its steps (`gate`,`building`,`auditing`,`proving`) are understood to legitimately span turns/sessions. — stop.py:91-96

## PROMISES MADE TO OTHER PARTS

- **To the driver (`orchestrate.py`)**: epic writes batch run files it starts (`command:"sprint"`, `children` of features, `deliver:"branch"`, `gate:"none"`, chained `parent`/`base`), and the driver treats a non-`ship`/non-feature child (e.g. an audit lens) by reading its `prompt` field verbatim rather than assuming `ship` — this is the entire contract for inserting non-`ship` work (finish.md:23-28, orchestrate.py:836-843, templates/run.json `_prompt`). Epic promises never to write more than the batch about to start (no look-ahead composition). — epic/SKILL.md:249
- **To `sprint --close`**: the closing session is trusted to fast-forward `epic/<slug>` instead of creating a `sprint/<slug>` branch, and to rewrite the one PR's body + add a digest comment for every batch after the first, rather than opening a new PR. — sprint/references/close.md:31-38
- **To the audit lens (`audit <lens> --run <dir>`)**: epic (via the auditing phase) promises to put everything a lens needs into that lens's own run file — `entries` as the area, `task` for wave number/whether-last/what-moved/what's-settled — never into the prompt string itself; the lens is trusted to read both and to rewrite `docs/audits/<lens>.md` whole. — finish.md:29-52
- **To `next`/`accept`/gates of future epics**: `docs/runs/<slug>.json` (`spent`, `branches`, `pr`, counts) is the durable record epic's own gate reads to price the next run, and that `next` reads to clean up delivered branches. Epic never marks an entry `built` itself — that is `check.py --sync`'s job once the PR merges — a rule explicitly called out as a mistake made on a real run (finish.md:135-139).
- **To the Stop hook**: epic promises to write its own session name into `session` on every `--advance`/hand-back session it starts (orchestrate.py:1230), and to set `step:"done"`/`"blocked"` only after all summary writing is finished, because the hook closes the session at the first turn *after* that field goes terminal (finish.md:143-146; stop.py:108-130).
- **To the guard hook**: implicitly relies on the guard's exception for the proving phase's real merges/pushes and the closing session's PR operations (guard.py:28,229) — full contract belongs to the guard/orchestrate sector, not re-derived here.
- **To `sprint` proper (non-epic)**: epic explicitly reuses sprint's batch shape unchanged ("Each batch is an ordinary sprint run file" — SKILL.md:246) and its frame-child convention verbatim from `sprint/SKILL.md` ("Write **only the batch you are about to start**" / frame child written "exactly as `sprint/SKILL.md` writes one" — SKILL.md:251-253).
- **To `blueprint`**: every gap epic finds that only `blueprint` may fix (missing MVP bounds, missing scenarios, no `commands.mutate`, unread description parts, unanswered verification kinds) is *offered*, never patched by epic itself. — SKILL.md:44-46,58-60,156-164; rules/preflight.md's verification-kinds row

## UNCERTAIN / CONTRADICTORY

- **`gh` invocation for opening/updating the PR** is never shown explicitly inside the files read for this sector — `close.md`'s excerpt (lines 1-40) covers only the branch fast-forward/push; the actual `gh pr create`/`gh pr edit` call is presumably further down `close.md`, outside this sector's mandated reading list. Not verified here.
- **Exact wording/mechanics of `rules/asking.md`** (referenced three times as governing the gate's single screen and its pre-fetched numbers) was not read in full — only inferred from epic/SKILL.md's citations. Another sector may own it.
- **What exactly `finish.waves` defaults to when the gate does not set it** — SKILL.md says "three waves" is fixed at the gate and "not raised later by anything" (SKILL.md:119-120), while finish.md separately says "three by default" (finish.md:67-68) as if it were a program default rather than a gate decision. Not contradictory in effect (both land on 3), but it's unclear from these two files alone whether 3 is hard-coded somewhere in `check.py`/templates or purely a convention the gate is instructed to write. `templates/run.json`'s `_finish` comment describes `waves` as settled at the gate, consistent with SKILL.md, so the finish.md "three by default" reads as restating the same convention, not a second source of truth — but this was not traced into code.
- **How `check_epic`'s "at least one scenario" fatal check reconciles with `finish.md`'s stronger requirement** ("every scenario inside the bounds passes") — the gate check only requires scenarios to exist at all (check.py:882-885), not that they're inside the chosen scope; the *scope-relative* scenario check only happens later, in the proving phase via `check.py --state`. This is a real two-stage design (weak gate check, strong proving check), not a contradiction, but worth flagging as something another sector (or a full reading of `check.py`'s `scenarios()` function) should confirm doesn't silently pass an epic whose in-scope batches close no scenarios at all until the very last phase.
- **Where exactly the driver's stall/restart/limit-handling logic lives** was only skimmed (orchestrate.py:780-800 fragment) — the task said to record only the hand-off contract with orchestrate, so the full stall machinery (restart(), watch(), nudge threshold) was deliberately left unmapped; flagged here so the orchestrate-owning sector doesn't assume it was covered.
- **`ext:gh` node** is included on inference (every PR-opening/rewriting action must go through `gh`, referenced elsewhere in check.py e.g. line 1339/1405) but no direct `gh` call was observed inside the epic-owned files themselves; treat this node as low-confidence / likely belongs entirely to the sprint-close sector.
