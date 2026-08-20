# Sector: sprint

Files read in full: `plugins/agent-kit/skills/sprint/SKILL.md`, `.../skills/sprint/references/frame.md`,
`.../skills/sprint/references/close.md`, `.../rules/window.md`, `.../templates/batch.json`, plus
`plugins/agent-kit/scripts/orchestrate.py` (read for the hand-off contract only — another sector maps
orchestrate itself) and targeted excerpts of `rules/closing.md`, `rules/preflight.md`,
`templates/run.json`, `skills/next/SKILL.md`, `skills/epic/SKILL.md`, `skills/runfile.py`.

## NODES

`id | kind | label | one-sentence description | source file:line`

| id | kind | label | description | source |
|---|---|---|---|---|
| cmd:sprint | cmd | `/agent-kit:sprint` | Four-roled command: brief, frame child, close child, window. | skills/sprint/SKILL.md:1-25 |
| phase:brief-knowledge | phase | Knowledge check | `check.py --status` before asking anything; reacts per preflight.md. | skills/sprint/SKILL.md:38-56 |
| phase:brief-compose | phase | Compose the batch | Ask only forking questions, propose set+order, present as one screen. | skills/sprint/SKILL.md:58-132 |
| phase:brief-no-theme | phase | With no theme | Sorts owed-vs-missing piles, asks which pile, then which candidates. | skills/sprint/SKILL.md:82-132 |
| phase:brief-write-runs | phase | Write run files | tmux check, batch run.json, frame child run.json, feature run.jsons, check.py --run per child. | skills/sprint/SKILL.md:134-230 |
| phase:brief-start-driver | phase | Start the driver | `nohup orchestrate.py <batch dir>/ >> driver.out 2>&1 &` | skills/sprint/SKILL.md:232-253 |
| phase:brief-become-window | phase | Then stay, as the window | Brief session becomes the window session; one line, then stop and wait. | skills/sprint/SKILL.md:255-267 |
| gate:tmux-check | gate | tmux installed? | `command -v tmux`; if missing, offer `/agent-kit:ship` per feature instead. | skills/sprint/SKILL.md:136-139 |
| gate:pile-first | gate | Which pile first | With no theme: "close what is owed" vs "build what is missing", skipped if one pile empty. | skills/sprint/SKILL.md:101-110 |
| gate:candidates | gate | Which candidates | Screen of candidate items with cost, ask which the batch takes. | skills/sprint/SKILL.md:103-104 |
| gate:composition-qs | gate | Composition/order/fork/assumption/reachability questions | Up to 5 kinds of forking questions asked per rules/asking.md. | skills/sprint/SKILL.md:64-76 |
| gate:promise-side | gate | Which side is wrong (unkept promise) | Owner says product or entry is wrong, for each unkept-promise candidate. | skills/sprint/SKILL.md:121-132 |
| script:check-status | script | `check.py --status` | Prints planned entries, open assumptions, unkept promises, debt. | skills/sprint/SKILL.md:43-44 |
| script:check-brief | script | `check.py --brief <key>` | Prints stack.md whole plus one entry section; used by frame child. | frame.md:23-26 |
| script:check-run | script | `check.py --run <dir>` | Validates a queued child's run file before driver starts; frame's tool for entries+code overlap; close's tool for "what moved". | skills/sprint/SKILL.md:171-175, close.md:207-211 |
| script:orchestrate | script | `orchestrate.py <run-dir>` | The driver: builds children in order, watches sessions, handles limits/stalls/handoff, starts frame/close. | orchestrate.py:1-13 |
| session:brief | session | Brief session | Composes batch with owner; later becomes window. | skills/sprint/SKILL.md:16-18 |
| session:driver | session | Driver (background process) | `orchestrate.py`, not an agent/session itself — a detached process. | orchestrate.py:1-45 |
| session:frame | session | Frame child session | First child of batch≥3; started by driver with `--frame`. | frame.md:1-16 |
| session:feature-N | session | Feature child session(s) | `ship` sessions, one per feature, started in queue order. | orchestrate.py:832-846 |
| session:close | session | Closing session | Started by driver with `--close`; opens the one PR for the batch. | close.md:1-10 |
| session:window | session | Window session | Whoever the driver types `[driver]` news at; answers owner, relays skip/stop. | rules/window.md:1-17 |
| tpl:run-json | tpl | `templates/run.json` | Shape every run file (batch, frame, feature) follows. | skills/sprint/SKILL.md:142 |
| tpl:batch-json | tpl | `templates/batch.json` | Shape of `docs/runs/<slug>.json`, the durable batch record. | close.md:228-232 |
| file:batch-run | file | `.agent-kit/runs/<batch>/run.json` | The batch's own run file: slug, command, gate, base, window, model, children, control. | skills/sprint/SKILL.md:144-149 |
| file:frame-run | file | `.agent-kit/runs/<batch>-00-frame/run.json` | Frame child's run file: step, gate:none, branch, deliver:branch, needs:[], prompt, frame map. | skills/sprint/SKILL.md:158-164, frame.md:101-123 |
| file:feature-run | file | `.agent-kit/runs/<batch>-NN-<feature>/run.json` | One per feature: command:ship, entries/task, gate, branch, base/parent, needs, deliver:branch, step, model. | skills/sprint/SKILL.md:188-224 |
| file:control | file | `.agent-kit/runs/<batch>/control` | One-line instruction file: `skip <slug>` or `stop`, written by window, read+deleted by driver between features. | rules/window.md:87-111, orchestrate.py:547 |
| file:driver-out | file | `.agent-kit/runs/<batch>/driver.out` | Driver's stdout/stderr, redirected explicitly (never /dev/null). | skills/sprint/SKILL.md:239-241 |
| file:run-log | file | `.agent-kit/runs/<...>/run.log` | Driver's own event trace; only record of *when* things happened; no agent writes it. | rules/window.md:22-23 |
| file:stack-md | file | `docs/knowledge/stack.md` | Read once by brief; frame appends a `[frame …]` block to it. | skills/sprint/SKILL.md:56, frame.md:6,42-51 |
| file:docs-runs-json | file | `docs/runs/<batch slug>.json` | Durable batch record, written by close per `templates/batch.json`. | close.md:221-263 |
| file:technical-debt | file | `docs/technical_debt.md` | Ledger close writes closed/added debt into. | close.md:112-121 |
| file:manual-md | file | `docs/manual.md` | Manual-actions record close writes into. | close.md:123-129 |
| file:project-yml | file | `.agent-kit/project.yml` | Read by brief (candidates/source) and by close (language). | skills/sprint/SKILL.md:53, close.md:16 |
| file:pr-body | file | Pull request body | Composed by close: What did not happen, Manual actions, Assumptions, Proven, per-feature blocks, Review. | close.md:63-149 |
| rule:window | rule | rules/window.md | Governs the window role fully (this is its full text — sector's 4th role). | rules/window.md |
| rule:closing | rule | rules/closing.md | First/last-line shape every session (incl. sprint's four) must follow. | rules/closing.md:1-50 |
| rule:preflight | rule | rules/preflight.md | Reaction table to knowledge-check findings; owner-gate for `[assumed]`/`[stale]` blocks. | rules/preflight.md:13-93 |
| rule:asking | rule | rules/asking.md | How brief phrases owner questions (referenced, not fully read here). | skills/sprint/SKILL.md:77 |
| rule:pull-requests | rule | rules/pull-requests.md | Section order/shape for the batch PR (referenced). | close.md:67 |
| rule:audit-boxes | rule | rules/audit-boxes.md | How close ticks audit work-list boxes (referenced). | close.md:132 |
| ext:tmux | ext | tmux | Multiplexer giving each child/session its own visible pane; required. | skills/sprint/SKILL.md:136-139 |
| ext:git-gh | ext | git / gh | Branch, push, PR creation, `gh pr checks`. | close.md:25-29,139-141,181 |
| agent:ship | agent | `ship` command | Builds one feature per feature-run; not mapped here (own sector). | skills/sprint/SKILL.md:9-14 |
| agent:epic | agent | `epic` command | Caller of sprint's machinery as its own batch mechanism (hand-off target). | orchestrate.py:1180-1220 |
| cmd:next | cmd | `/agent-kit:next` | Reads `docs/runs/*.json` `branches`/`parked` to retire delivered branches. | close.md:247-249, next/SKILL.md:56-68 |
| cmd:accept | cmd | `/agent-kit:accept` | Downstream reader implied by "what sprint produces" (see PROMISES section). | task instructions |

## EDGES

`from-id -> to-id | mechanism | trigger/condition | source file:line`

| from | to | mechanism | trigger/condition | source |
|---|---|---|---|---|
| cmd:sprint | phase:brief-knowledge | invokes | `/agent-kit:sprint [theme]` with no `--frame/--close/--window/--resume` | skills/sprint/SKILL.md:16-19 |
| phase:brief-knowledge | script:check-status | invokes | first action of the brief | skills/sprint/SKILL.md:42-44 |
| script:check-status | phase:brief-compose | returns-to | prints planned/assumed/promises/debt | skills/sprint/SKILL.md:49-56 |
| phase:brief-knowledge | rule:preflight | delegates | "React per rules/preflight.md" | skills/sprint/SKILL.md:46 |
| phase:brief-compose | gate:composition-qs | invokes | when different answers fork the road | skills/sprint/SKILL.md:60-76 |
| phase:brief-compose | rule:asking | delegates | question shape/order | skills/sprint/SKILL.md:77 |
| cmd:sprint | phase:brief-no-theme | invokes | called with no theme | skills/sprint/SKILL.md:82-84 |
| phase:brief-no-theme | gate:pile-first | invokes | unless one pile is empty | skills/sprint/SKILL.md:101-110 |
| gate:pile-first | gate:candidates | loops-to | after pile chosen | skills/sprint/SKILL.md:103-104 |
| phase:brief-no-theme | gate:promise-side | invokes | for a batch composed of unkept promises | skills/sprint/SKILL.md:121-125 |
| phase:brief-compose | phase:brief-write-runs | hands-off | batch and order agreed / "finding nothing to ask" | skills/sprint/SKILL.md:62-63,134 |
| phase:brief-write-runs | gate:tmux-check | invokes | before writing anything | skills/sprint/SKILL.md:136-139 |
| gate:tmux-check | phase:brief-write-runs | refuses | tmux missing → offers `/agent-kit:ship` per feature instead, batch not composed | skills/sprint/SKILL.md:138-139 |
| phase:brief-write-runs | file:batch-run | writes | batch run.json per templates/run.json | skills/sprint/SKILL.md:144-149 |
| phase:brief-write-runs | file:frame-run | writes | when batch has ≥3 features | skills/sprint/SKILL.md:158-164,183-186 |
| phase:brief-write-runs | file:feature-run | writes | one per feature | skills/sprint/SKILL.md:188-224 |
| phase:brief-write-runs | script:check-run | invokes | on every queued child, before driver starts | skills/sprint/SKILL.md:171-175 |
| script:check-run | phase:brief-write-runs | returns-to | brief is "the only session that can act on what it says" | skills/sprint/SKILL.md:169 |
| phase:brief-write-runs | phase:brief-start-driver | hands-off | once run files pass check | skills/sprint/SKILL.md:232 |
| phase:brief-start-driver | script:orchestrate | spawns | `nohup python3 orchestrate.py <batch dir>/ >> driver.out 2>&1 &` | skills/sprint/SKILL.md:234-237 |
| script:orchestrate | file:driver-out | writes | stdout/stderr | skills/sprint/SKILL.md:239-241 |
| phase:brief-start-driver | phase:brief-become-window | hands-off | driver started | skills/sprint/SKILL.md:255 |
| phase:brief-become-window | session:window | becomes | brief session stays, follows rules/window.md | skills/sprint/SKILL.md:261-262 |
| session:driver | session:frame | spawns | first child if ≥3 features, `claude` session running `/agent-kit:sprint --frame <dir>` | orchestrate.py:6-8, 832-846 |
| session:driver | session:feature-N | spawns | in queue order, prompt = child's `prompt` or default `/agent-kit:ship --run <dir>` | orchestrate.py:832-846 |
| session:driver | session:close | spawns | after all children terminal, `/agent-kit:sprint --close <dir>`, `hand_over=false` | orchestrate.py:1143-1149 |
| session:frame | file:stack-md | writes | commits `[frame …]` block on its own branch, pushes | frame.md:42-51,98-99 |
| session:frame | script:check-brief | invokes | one call per entry, first call unbriefed to read map | frame.md:23-26 |
| session:frame | file:docs-runs-json | reads | `per_feature` off newest 1-2 batch records | frame.md:30-36 |
| session:frame | file:frame-run | writes | `frame` map {slug: [needed slugs]}, then `step:"done"`, `notes` | frame.md:101-123,126-130 |
| session:driver | file:frame-run | reads | polls `step`; on terminal, `apply_frame()` reads `frame` field | orchestrate.py:889-946, 802-810 |
| session:driver | file:feature-run | writes | writes each feature's `needs` from frame map (only if not already authored) | orchestrate.py:914-936 |
| session:driver | file:batch-run | writes | re-sorts `children` by `order_by_needs`, prepends frame slug | orchestrate.py:944-945 |
| session:driver | file:batch-run | writes | `blockers` += frame-defect lines (no map, cycle, stray names) | orchestrate.py:947-966 |
| session:feature-N | agent:ship | delegates | prompt is `/agent-kit:ship --run <child dir>` (own sector) | orchestrate.py:832-846 |
| session:driver | file:feature-run | reads | polls transcript mtime, `step`, `handoff`, assumptions, blockers | orchestrate.py:619-822 |
| session:driver | session:feature-N | blocks | idle > `--hang` minutes and gone → "continue" nudge, then restart, then `step:"blocked"` | orchestrate.py:776-820, build():822-827 |
| session:driver | file:feature-run | writes | `blockers` += `run_defects()` findings (`audit()`), even for a built feature | orchestrate.py:849-864 |
| session:driver | session:window | invokes | `tell()` types `[driver] ...` news lines, once-per-driver WINDOW_RULE first | orchestrate.py:593-609 |
| session:window | file:control | writes | `skip <slug>` or `stop`, one line | rules/window.md:87-111 |
| session:driver | file:control | reads | `take_control()` between features, then deletes file | orchestrate.py:547, 1043-1058 |
| session:driver | session:feature-N | blocks | control=`skip <slug>` or a needed slug was skipped → child `step:"skipped"`, not started | orchestrate.py:1044-1046,1099-1108 |
| session:driver | session:feature-N | refuses | control=`stop` → remaining children `step:"skipped"`, loop still finishes then closes | orchestrate.py:1047-1050,1067-1071 |
| session:close | file:batch-run | reads | run.json + every child's run.json | close.md:14-19 |
| session:close | file:project-yml | reads | for language | close.md:16 |
| session:close | ext:git-gh | invokes | `git fetch`, `git branch -f sprint/<slug> <tip>`, `git push -u origin sprint/<slug>` | close.md:25-29 |
| session:close | ext:git-gh | invokes | `gh pr create` per feature (offered command, not run) | close.md:139-141 |
| session:close | ext:git-gh | invokes | `gh pr checks` after opening batch PR, waits reasonable window | close.md:181 |
| session:close | file:pr-body | writes | one PR for the batch, composed per rule:pull-requests | close.md:63-149 |
| session:close | rule:pull-requests | delegates | section order/shape | close.md:67 |
| session:close | file:technical-debt | writes | delete closed_debt lines, add deferred lines | close.md:112-121 |
| session:close | file:manual-md | writes | merge children's `manual` records | close.md:123-129 |
| session:close | rule:audit-boxes | delegates | ticking audit work-list boxes | close.md:132 |
| session:close | file:stack-md | writes | entries → `state: building (pr: <n>)`; apply `[stale …]` blocks within limits; fill frame block's `pr: ?` | close.md:184-219 |
| session:close | script:check-run | invokes | "which records moved while the batch ran" over batch dir | close.md:206-211 |
| session:close | file:docs-runs-json | writes | from templates/batch.json, same commit as ledger | close.md:221-263 |
| session:close | file:batch-run | writes | `pr`, `branch`, `suite`, `blockers`, `step:"done"` | close.md:265-268 |
| session:driver | file:batch-run | reads | polls close's `step`; terminal or `own_pr()` → `step:"done"`; else `step:"blocked"` | orchestrate.py:1150-1163 |
| session:driver | session:window | invokes | final `tell()`: "the batch is finished, pull request N" or "was never closed" | orchestrate.py:1157,1163-1165 |
| session:driver | agent:epic | hands-off | `hand_back()`: if `parent`'s `command` is `epic`/`mvp`, starts `<parent>-advance` session with `/agent-kit:epic --advance <dir>` | orchestrate.py:1178-1218 |
| cmd:sprint | session:frame | invokes | `/agent-kit:sprint --frame <run dir>` (only ever typed by driver) | skills/sprint/SKILL.md:21 |
| cmd:sprint | session:close | invokes | `/agent-kit:sprint --close <run dir>` (only ever typed by driver) | skills/sprint/SKILL.md:22 |
| cmd:sprint | session:window | invokes | `/agent-kit:sprint --window <run dir>` (a fresh session standing beside a run) | skills/sprint/SKILL.md:23 |
| cmd:sprint | script:orchestrate | invokes | `/agent-kit:sprint --resume <run dir>` restarts driver over same dir | skills/sprint/SKILL.md:269-273 |
| cmd:next | file:docs-runs-json | reads | `branches`/`parked` to know which to delete | close.md:247-249 |
| agent:epic | file:docs-runs-json | reads | `--advance` checks it via `check.py --run` for closedness | epic/SKILL.md:295-301 |

## ROLE SPINES

**brief** (`/agent-kit:sprint [theme]`, or no theme):
1. Knowledge check (`check.py --status`) → react per preflight.
2. Read `project.yml`, batch source, per-candidate entry sections, `stack.md` once.
3. (No theme only) ask which pile first (owed vs missing, skip if one empty) → present chosen pile → ask which candidates.
4. Compose batch: ask composition/order/fork/assumption/reachability questions per `asking.md`; present batch+order as one screen.
5. (Unkept-promise batch only) for each candidate, ask which side is wrong (product or entry).
6. Check tmux installed.
7. Write batch run.json, frame run.json (if ≥3 features), feature run.jsons.
8. Read back every child with `check.py --run`.
9. Start the driver (`nohup orchestrate.py`).
10. Become the window: one line, then stop and wait.

**frame** (`/agent-kit:sprint --frame <dir>`, started only by driver):
1. Say who you are, one line.
2. Read own run file / batch's run file, pull each feature's entry via `check.py --brief`.
3. Read `per_feature` from newest 1-2 `docs/runs/*.json`.
4. Read code only where two features' entries look like they meet.
5. Write `[frame …]` block under `stack.md` (or state "nothing to say" + files checked); commit, push on own branch.
6. Write `frame` map (needs-of per feature) into own run file.
7. Close: `step:"done"`, branch, `notes` (files opened + what was skipped).

**close** (`/agent-kit:sprint --close <dir>`, started only by driver, after all children terminal):
1. Say who you are, one line.
2. Read batch run.json + every child's run.json + `project.yml`.
3. Force/fast-forward the batch branch to the last successfully-built child, push (`sprint/<slug>` normally, `epic/<slug>` inside an epic).
4. Compose the one pull request (or rewrite the epic's persistent PR body + append digest comment): What did not happen, Manual actions, Assumptions (+deviations), Proven, per-feature collapsed blocks, Review.
5. Move the ledger: delete `closed_debt`, add `deferred` to `docs/technical_debt.md`; merge `manual` into `docs/manual.md`; tick audit boxes.
6. Update knowledge: entries → `building (pr:n)`; apply `[stale …]` blocks (within limits); fill frame's `pr: ?`; run `check.py --run` for drift and report it.
7. Write `docs/runs/<batch slug>.json` from `templates/batch.json`, same commit as ledger.
8. Close own run file: `pr`, `branch`, `suite`, `blockers`, `step:"done"`.
9. Report: thin spots, parked features, expensive assumptions, what to run next.

**window** (`/agent-kit:sprint --window <dir>`, or the brief session persisting):
Not phased — a standing loop: read on demand (`run.json`s, `run.log` tail; never a child transcript) → answer owner in 3-4 lines → relay `[driver]` news as one plain sentence → on owner request, write `skip <slug>` or `stop` to `control` and say it takes effect after the current feature → never asks the owner anything itself, only reports + names where a finding surfaces.

**resume** (`/agent-kit:sprint --resume <dir>`):
Restart the driver over the same run directory only. Children already at a PR or a blocker are left alone; the rest run in order. Nothing is rewritten unless the owner changed their mind about a specific feature.

## IO TABLE

`node-id | reads | writes`

| node | reads | writes |
|---|---|---|
| phase:brief-knowledge | (invokes check.py --status) | — |
| phase:brief-compose | project.yml, batch source, candidate entry sections, stack.md | — |
| phase:brief-write-runs | check.py --run output | file:batch-run, file:frame-run, file:feature-run, `.gitignore` (adds `.agent-kit/runs/` if absent) |
| script:orchestrate | file:batch-run, file:feature-run, file:frame-run, file:control, transcripts | file:batch-run (`step`,`children`,`session`,`spent`,`blockers`,`window` event), file:feature-run (`session`,`needs`,`step`,`spent`,`blockers`), file:control (deletes), file:driver-out (via redirect), file:run-log (events) |
| session:frame | frame's run.json / batch's run.json, entries via check.py --brief, docs/runs/*.json (`per_feature`), code at feature intersections | file:stack-md (`[frame …]` block), file:frame-run (`frame` map, `step`, `notes`) |
| session:feature-N | own run file (own sector: ship) | own run file, branch commits |
| session:close | file:batch-run, every file:feature-run, file:project-yml | git branch/push, file:pr-body, file:technical-debt, file:manual-md, audit work-list boxes, file:stack-md (state lines, `[stale]` blocks, frame `pr:` field), file:docs-runs-json, file:batch-run (`pr`,`branch`,`suite`,`blockers`,`step`) |
| session:window | file:batch-run, each child's `run.json` (`step`,`branch`,`pr`,`assumptions`,`blockers`,`waiting_on`), tail of `run.log` | file:control |
| cmd:next | file:docs-runs-json (`branches`,`parked`) | deletes local/remote git branches |
| agent:epic | file:docs-runs-json (via check.py --run), sprint's SKILL.md (writes batch run files itself, "ordinary sprint run file") | batch run files identical in shape to sprint's |

## OWNER GATES

In order, as they occur during a brief:

1. **Preflight owner gates** (per `rules/preflight.md`, ridden through by sprint since `gate` applies "once per run and before any work starts"):
   - open slot/incomplete entry in scope → stop, name it, offer `/agent-kit:blueprint`. Run waits.
   - `[assumed …]` blocks on in-scope entries → shown, offered to settle now; answer is written into the entry and the block deleted in a `docs(knowledge):` commit before building starts. Run waits for answer.
   - `[stale …]` blocks on in-scope entries → applied the same way (transcribe, never decide). Run waits.
   - a declared verification command that starts nothing → stop, name it, offer `/agent-kit:blueprint`. Run waits.
   - unanswered/stale verification-kind answers → say in one line, offer `/agent-kit:blueprint`, never asked directly here. Does not block.
   (rules/preflight.md:13-93)

2. **Pile first** (no-theme only) — "close what is owed" vs "build what is missing", each with its count. Skipped if one pile is empty. Effect: decides which list of candidates comes next. Run waits. (SKILL.md:101-110)

3. **Which candidates** — one screen, a line per candidate with cost, asking which the batch takes. Effect: composes `children`. Run waits. (SKILL.md:103-104,64-76)

4. **Composition/order/fork/assumption/reachability questions** (theme or themed no-theme path) — asked only where different answers fork the road; per `rules/asking.md`, options + recommendation first, batched in one round. Effect: which features, their `needs`, gate (owner/none) per feature, whether an expensive fork is asked live or recorded as `[assumed …]`. Run waits. (SKILL.md:60-76)

5. **Which side is wrong** (unkept-promise batch only) — for each promise candidate, owner says whether the product or the entry is wrong. Effect: becomes the child's `task`, quoting the exact test line to delete. Left undecided → stays marked, stays on the list (not closed by unmarking alone). Run waits. (SKILL.md:121-132)

6. **Model choice** — implicit gate: owner may name a model in the invocation or in answer to the composition screen; otherwise batch's own file takes the brief's running model, children take install default unless told cheaper. Does not block. (SKILL.md:206-219)

During the run (via the window, not the brief):
7. **skip <slug>** — owner tells the window to drop a feature; takes effect after the current feature finishes. (rules/window.md:92-103)
8. **stop** — owner tells the window to finish the current feature then close the batch as-is; resumable via `--resume`. (rules/window.md:92-99)

The window itself never asks the owner anything (rules/window.md:54-77) — findings from children are reported as statements naming where they will surface (the pull request's Assumptions section), and the owner's only lever is `stop`.

## REFUSALS, STALLS AND RECOVERY

- **No tmux** → brief refuses to write a batch at all; offers `/agent-kit:ship` per feature instead. (SKILL.md:136-139; orchestrate.py:153-159 refuses to even start the driver without tmux)
- **Two features, or one topic already ordered** → brief skips the frame child entirely, says so. (SKILL.md:183-186)
- **A child stalls** (idle > `--hang` minutes, still alive) → driver sends one `"continue"` nudge once; if that doesn't resolve it, restarts the session fresh (max 1 restart) or gives up and marks `step:"blocked"`, `blockers` note. (orchestrate.py:770-822, `build()`)
- **A child's session dies** (`gone`) → same restart-once-then-blocked path. (orchestrate.py:776-822)
- **Account limit (429)** → driver reads reset time from transcript tail, sleeps until then + 60s, types `"continue"` into the still-alive session (context intact); if wait exceeds `--max-wait` hours (default 6), treats it as a weekly limit and stops the whole run, telling the window. (orchestrate.py:757-772)
- **Overloaded (529)** → retries after 120s. (orchestrate.py:774-776)
- **Context-ceiling handoff** — a feature session (not frame, not close: `hand_over` only for `runfile.kind==feature`) past `--ceiling` (default 210k) tokens over its floor by ≥`--room` (default 40k) is asked, once, to close its run file, fill `handoff`, and stop; driver starts a fresh numbered session (`-2`, `-3`, …) on the same prompt once the `handoff` note lands. (orchestrate.py:657-745, handoff_due doc 424-479)
- **Frame left no map** — apply_frame finds no `frame` dict but the prompt shows it was a real `--frame` invocation → logs a defect into the batch's `blockers`, batch falls back to prior queue order (each feature "needs" its predecessor). (orchestrate.py:889-912)
- **Frame named a circular `needs`** → queue left in written order, feature slugs in the circle named in a `blockers` defect. (orchestrate.py:941-949, order_by_needs 516-544)
- **Frame named a feature outside the batch** → that name is dropped from the map, defect logged naming it. (orchestrate.py:937-948)
- **A feature is skipped** (owner `skip`, or a `needs` dependency was itself skipped) → `step:"skipped"`, and anything that needed it is skipped too (cascades forward). (orchestrate.py:1097-1108)
- **`stop`** — remaining queued children marked `step:"skipped"`, loop proceeds straight to closing. Not mid-feature: only takes effect at the boundary between features. (orchestrate.py:1063-1071, window.md:96-99)
- **A child closed with defects** (`run_defects()`) — feature is still counted "built" (branch pushed, reviewed) but the defects are appended to `blockers`, told to the window; not parked. (orchestrate.py:849-864)
- **Closing session itself fails to reach a terminal step** → batch `step:"blocked"`, told to window: "the batch was never closed — its branch, its pull request body and its digest need finishing by hand." (orchestrate.py:1157-1165)
- **Empty `children`** → driver logs "no children to build — handing back", tells window, calls `hand_back()` (only meaningful inside an epic) and exits. (orchestrate.py:998-1007)
- **`--resume`** — restarts the driver over the same directory; children already at a PR or a blocker are untouched, the rest continue in order; nothing in run files is rewritten except by explicit owner decision. (SKILL.md:269-273)
- **Two drivers over one run** — `orchestrate.py`'s `main()` refuses to start if any non-terminal child already has a live tmux session, printing an error and exiting 1. (orchestrate.py:169-176)
- **Driver dies with its own launching session** — before touching the run file, `orchestrate.py` tries to detach itself into its own cgroup/systemd unit; if it cannot, it warns loudly that closing the launching session will kill the driver. (orchestrate.py:145-163)

## PROMISES MADE TO OTHER PARTS

**With `orchestrate.py` (the driver, mapped elsewhere) — the hand-off contract:**
- Driver is given a directory (`.agent-kit/runs/<batch>/`) whose `run.json.children` names features to build in order; it holds no judgement of its own — every opinion belongs to a session it starts. (orchestrate.py:6-13)
- It types one of two prompts into each child: the run file's own `prompt` field verbatim if present (a command, never a path — see `templates/run.json:_prompt`), else the default `/agent-kit:ship --run <dir>`. sprint's `--frame` and `--close` are examples of the first form. (orchestrate.py:832-846, templates/run.json:87)
- It expects each child to close by turning its own `run.json.step` terminal (`done`, `blocked`, `skipped`) — that's the only signal it watches; a child with a pushed branch but no terminal step is judged "blocked" unless the branch is found already pushed. (orchestrate.py:815-827, TERMINAL = ("done","blocked","skipped"), runfile.py:39)
- It expects the frame child to leave its map in its own run file's `frame` field (not in prose); it turns that into `needs` on every other child and re-sorts `children` by dependency, doing the arithmetic itself while treating the map as the frame session's judgement. (orchestrate.py:889-946)
- It expects a feature child to leave `needs` (list of slugs) or nothing (falls back to `parent`, i.e., chain order); `[]` is read as a deliberate "needs nothing" answer, distinct from the field being absent. (SKILL.md:199-203; orchestrate.py:1095-1103)
- It expects the closing child to end with a terminal `step` or an `own_pr()`; anything else is judged "close-failed" and the batch is `blocked`.
- It reads/writes `assumptions[].expensive` on every child and relays the first one via `tell()` — a promise `ship` makes and the driver actually consumes (unlike some other spare fields). (orchestrate.py:966-984)
- It reads `blockers` (accumulating defects it itself may add) and never clears them.
- It writes `spent.sessions` per child (from its own session count) and accumulates `spent.hours/features/sessions` on the batch file across `--resume`s. (orchestrate.py:815-820, 1128-1140)
- It relies on `window` in the batch's run file to know where to post news; absence just means no narrator, never an error.
- On an empty queue or a finished batch whose `parent`'s `command` is `epic`/`mvp`, it starts `<parent>-advance` and hands off — that's the sprint/epic seam, entirely inside orchestrate, not sprint's own prose.

**With `ship` (own sector):** sprint's brief writes feature run files that `ship` reads and closes; sprint never designs or reviews the feature itself — "you do not build anything and you do not design the features" (SKILL.md:12-14). `deliver: "branch"` tells `ship` to push and stop rather than open its own PR.

**With `epic`:** a batch inside an epic is "an ordinary sprint run file" with `parent` naming the epic run, chained children, `gate:"none"` (epic/SKILL.md:246-248). The closing session behaves differently inside an epic: it fast-forwards the persistent `epic/<slug>` branch instead of creating `sprint/<slug>`, and rewrites the one epic PR's body instead of opening a new PR (close.md:31-36, 151-179). Epic's `--advance` step trusts `docs/runs/<slug>.json`'s presence (via `check.py --run`) as proof a batch is closed, and reads `spent` from it to price the next batch's scope (epic/SKILL.md:295-301, 125).

**With `blueprint`:** the `[frame …]` block's `pr: ?` is filled by close with the PR number; `blueprint` closes/reads the block months later using that number to tell whether the batch ever merged (frame.md:89-90, close.md:50-53). `[assumed …]`/`[stale …]` blocks close's applies or leaves for blueprint follow the same "transcribe, never decide" rule as preflight's owner gate.

**With `next`:** `docs/runs/<batch slug>.json`'s `branches` (every child's branch, including frame's and parked ones) and `parked` are the only record `next` can use to tell which branches a merged PR already delivered and safely delete — without it, branches become unanswerable by git after a squash merge (close.md:234-249, next/SKILL.md:56-68). `next` also reads a run's `step` (rung 2 of its ladder) and, for a non-terminal sprint run, recommends `/agent-kit:sprint --resume <dir>` by name (next/SKILL.md:234-236).

**With a later `sprint`/`epic` gate:** `docs/runs/<slug>.json`'s `spent` and `per_feature` are the only measured cost data in the project; a later frame child reads `per_feature` to decide what to split before building anything, and an epic's gate prices its next batch's scope from `spent` (close.md:253-260, frame.md:30-36, epic/SKILL.md:125).

**What sprint produces that `accept` reads:** not established in the five files read — no reference to `/agent-kit:accept` appears in sprint's own SKILL.md, frame.md, close.md, or window.md, nor did it surface in the epic/next greps. See UNCERTAIN below.

## UNCERTAIN / CONTRADICTORY

- **`accept` is never named anywhere in sprint's own files**, and no grep hit connected `accept` to sprint's outputs. The task brief asked "what sprint produces that accept/next/epic later read" — `next` and `epic` are well documented (above), but I found no explicit contract with a command called `accept` in this codebase; it may not exist under that name, or the connection is indirect (e.g., through the merged pull request and `docs/runs/*.json` generically, read by whatever an `accept` command is). Flagging rather than inventing one.
- **Where does the theme/"list of work" argument actually get parsed?** `SKILL.md`'s table just says `/agent-kit:sprint <theme>` → the brief; the file never shows the argument being read into a variable or distinguishes a theme string from "a list of work" beyond prose in *Compose the batch*. The mechanics of turning `$ARGUMENTS` into "batch source" are left entirely to judgement, not shown as a parsing step.
- **`gate` on the batch's own run file** (`"gate": "owner"` in the batch.json example, SKILL.md:147) is never explained for the batch level — the per-feature `gate` (owner/none) is well specified (SKILL.md:191-193), but what the batch-level `gate` field itself controls (if anything, versus being vestigial/copied from `templates/run.json`'s shape) is not stated in any of the five sector files.
- **Frame child's own `gate`** is hardcoded `"none"` in the template (SKILL.md:161) — consistent with "nobody is present" (frame.md:3), but not cross-checked against `runfile.py`/`orchestrate.py` for whether `gate` is read by the driver at all for non-feature children; from the orchestrate.py excerpts read, `gate` was never referenced by the driver — it appears to be purely a signal read by the session itself (`ship`, in `rules/preflight.md`), not by orchestrate.py. Not contradictory, just worth flagging that "the frame session decides how to act on `gate:none`" rather than the driver enforcing it.
- **`docs/design/sprint.md`** is referenced by orchestrate.py's own docstring ("See docs/design/sprint.md for why the driver is a loop rather than an agent", orchestrate.py:12) but was out of scope for this sector per the task's file list — not read, so the *why* behind the loop-vs-agent design is asserted by the code comment but not verified here.
- **Close.md says "You never run them yourself" about e2e tests** (close.md:102-104) — this is a strong claim about the closing session's behavior that has no corresponding refusal mechanism shown in orchestrate.py; it is pure prose discipline, unenforced by any script in this sector as far as I read.
- **The `window` field's owner-reachability semantics** overlap with per-feature `gate: owner|none` (SKILL.md:75, 191-193) — the brief asks "whether the owner is reachable while it runs" as one of five composition questions, but it's unclear whether this single answer sets `gate` uniformly for all features or is decided per-feature; SKILL.md's feature-run-file section implies per-feature (`gate: "owner"` when the owner said they are reachable), suggesting it's asked once but could in principle differ per feature — not made explicit either way.
