# Sector: ship

Files read in full: `plugins/agent-kit/skills/ship/SKILL.md`, `plugins/agent-kit/agents/reviewer.md`,
`plugins/agent-kit/rules/preflight.md`, `plugins/agent-kit/rules/closing.md`,
`plugins/agent-kit/rules/asking.md`, `plugins/agent-kit/rules/craft.md`,
`plugins/agent-kit/rules/pull-requests.md`, `plugins/agent-kit/rules/channels.md`,
`plugins/agent-kit/rules/window.md`, `plugins/agent-kit/hooks/guard.py`,
`plugins/agent-kit/templates/run.json`. Skimmed for hand-off points:
`plugins/agent-kit/scripts/check.py` (run_defects, CLI flags), `plugins/agent-kit/scripts/orchestrate.py`
(driver), `plugins/agent-kit/skills/next/SKILL.md`, `plugins/agent-kit/skills/sprint/SKILL.md`,
`plugins/agent-kit/skills/epic/SKILL.md`, `plugins/agent-kit/skills/fix/SKILL.md`.

## NODES

cmd:ship | command | `/agent-kit:ship [key\|task]` | build one feature end to end: design, build, verify, review, PR | plugins/agent-kit/skills/ship/SKILL.md:1-6
agent:reviewer | subagent | `agent-kit:reviewer` | read-only diff review against the approved entry, the run file, craft.md, stack.md | plugins/agent-kit/agents/reviewer.md:1-6
script:check | script | `scripts/check.py` | knowledge/manifest/run-file linter with many CLI modes (`--brief`, `--owed`, `--run`, `--pr-body`, `--pr-base`, `--manual`, `--tests`, `--sync`, `--state`, `--status`, `--offline`) | plugins/agent-kit/scripts/check.py:3599-3648
script:orchestrate | script | `scripts/orchestrate.py <run-dir>` | the driver: starts one `claude` session per batch child, watches its run file, hands over on size, applies control/skip/stop | plugins/agent-kit/scripts/orchestrate.py:1-16
hook:guard | hook | `hooks/guard.py` (PreToolUse/Bash) | refuses `gh pr merge`, force-push, push-to-default always while a run is in flight; refuses the declared e2e/scenarios command and branch-switching specifically inside a registered `ship` session | plugins/agent-kit/hooks/guard.py:1-41,213-263
rule:preflight | rule | `rules/preflight.md` | shared reaction table to the knowledge check's findings, used by every build command | plugins/agent-kit/rules/preflight.md:1
rule:closing | rule | `rules/closing.md` | how every command opens (one line, who/what/where) and closes (thin spots, next command) | plugins/agent-kit/rules/closing.md:1
rule:asking | rule | `rules/asking.md` | how to put a question to the owner: AskUserQuestion, options not prose, recommendation + expense | plugins/agent-kit/rules/asking.md:1
rule:craft | rule | `rules/craft.md` | 4 rules read by ship, fix, and the reviewer: don't fake green, a stand-in proves the stand-in, nothing not asked for, mark the door out | plugins/agent-kit/rules/craft.md:1-13
rule:channels | rule | `rules/channels.md` | who-writes/reads/closes table for every field/file the kit uses | plugins/agent-kit/rules/channels.md:1
rule:pull-requests | rule | `rules/pull-requests.md` | PR shape: 3 open answers, everything else folded, size ceilings, sections in order | plugins/agent-kit/rules/pull-requests.md:1
rule:window | rule | `rules/window.md` | the owner's control-window session during a batch: reports, never asks, relays `skip`/`stop` | plugins/agent-kit/rules/window.md:1
tpl:run-json | template | `templates/run.json` | shape of `.agent-kit/runs/<slug>/run.json`, closed field list | plugins/agent-kit/templates/run.json:1
tpl:manual | template | `templates/manual.md` | copied to `docs/manual.md` on first manual action | plugins/agent-kit/rules/craft.md:267 (referenced), plugins/agent-kit/templates/manual.md
tpl:technical-debt | template | `templates/technical_debt.md` | copied to `docs/technical_debt.md` on first debt line | plugins/agent-kit/skills/ship/SKILL.md:298
tpl:workflow | template | `templates/workflow.yml` | CI workflow a task-only `ship` may generate for a new pipeline | plugins/agent-kit/rules/channels.md:49
file:run-file | file | `.agent-kit/runs/<slug>/run.json` | this run's memory and hand-off; created at Design, updated every step | plugins/agent-kit/skills/ship/SKILL.md:103-129
file:run-log | file | `.agent-kit/runs/<slug>/run.log` | driver's own trace; ship never writes it | plugins/agent-kit/skills/ship/SKILL.md:123-126
file:knowledge | file | `docs/knowledge/*.md` | blueprint entries; ship reads sections via `check.py --brief`, writes only the machine `state:` line and `[assumed]`/`[stale]`/`[found]` blocks | plugins/agent-kit/skills/ship/SKILL.md:81-97,283-296
file:project-yml | file | `.agent-kit/project.yml` | manifest: `commands.{test,lint,types,mutate,run,e2e}`, `verification`, `stage`, `language`; ship reads only, never writes | plugins/agent-kit/rules/channels.md:48
file:stack-md | file | `docs/knowledge/stack.md` | library map + `[frame …]` block; ship reads for design/craft, writes `[found …]` blocks | plugins/agent-kit/skills/ship/SKILL.md:190-193,291-292
file:technical-debt-md | file | `docs/technical_debt.md` | ledger of understood-and-not-done work; ship appends/deletes lines | plugins/agent-kit/skills/ship/SKILL.md:271-272,297-299
file:manual-md | file | `docs/manual.md` | copied from run's `manual` records when a run delivers its own PR | plugins/agent-kit/skills/ship/SKILL.md:267; rules/channels.md:39
file:gitignore | file | `.gitignore` | ship adds `.agent-kit/runs/` if missing | plugins/agent-kit/skills/ship/SKILL.md:128-129
ext:git | external | `git` CLI | clean-tree check, branch creation, commits, diff, push, rev-parse | plugins/agent-kit/skills/ship/SKILL.md:99-101,372,394-407,431-433
ext:gh | external | `gh` CLI | `gh pr create` (via pull-requests.md), `gh pr checks` | plugins/agent-kit/skills/ship/SKILL.md:391
ext:project-suite | external | `commands.test`/`lint`/`types` from project.yml | the declared suite, run once at Verify | plugins/agent-kit/skills/ship/SKILL.md:312-314
ext:project-mutate | external | `commands.mutate` from project.yml | mutation testing over `{files}` = changed files | plugins/agent-kit/skills/ship/SKILL.md:322-333
ext:project-run | external | `commands.run` from project.yml | starts the app for manual exercise | plugins/agent-kit/skills/ship/SKILL.md:351-356
ext:security-review | external | `/security-review` (Claude Code slash command) | run on trigger surfaces (auth, untrusted parsing, money, files/processes, migration, outbound call) | plugins/agent-kit/skills/ship/SKILL.md:442-444
session:ship-run | session | one `claude` session invoked as `/agent-kit:ship [--run <dir>]` | executes the phases below | plugins/agent-kit/skills/ship/SKILL.md throughout
gate:owner-present | decision | `gate: owner` vs `gate: none` in run file | governs whether ship waits on a question or records an assumption | plugins/agent-kit/skills/ship/SKILL.md:59,201-204
gate:expensive-fork | decision | "is this fork expensive" | asked (with owner) or recorded as assumption (headless) | plugins/agent-kit/skills/ship/SKILL.md:25-29
gate:entry-vs-code | decision | entry promises X, code does Y | write unmet-marked test + `unmet` line always; ask which side is wrong only with owner present | plugins/agent-kit/skills/ship/SKILL.md:31-52
gate:deliver-mode | decision | `deliver: "pr"` vs `deliver: "branch"` | branch mode stops after step 3 of Deliver (push + review), no PR opened | plugins/agent-kit/skills/ship/SKILL.md:409-413
gate:touched-product | decision | `git diff --name-only <base>...HEAD` before Review | tests/fixtures/lock-files/docs-only diff skips the reviewer entirely | plugins/agent-kit/skills/ship/SKILL.md:429-440

## EDGES

session:ship-run -> rule:closing | reads | first line of every step: say who/what/where | plugins/agent-kit/skills/ship/SKILL.md:18
session:ship-run -> script:check | invokes | `check.py .` before anything else (knowledge check) | plugins/agent-kit/skills/ship/SKILL.md:69-71
session:ship-run -> rule:preflight | reads | react to check.py's findings, plus ship-specific rows | plugins/agent-kit/skills/ship/SKILL.md:73-79
session:ship-run -> script:check | invokes | `check.py . --brief <entry-key>` — one-call read of project corner, entry, named entries, library map + craft.md | plugins/agent-kit/skills/ship/SKILL.md:81-93
session:ship-run -> rule:craft | hands-off | craft.md pulled in by the `--brief` read, same call | plugins/agent-kit/skills/ship/SKILL.md:82-84
session:ship-run -> file:project-yml | reads | when building from `task` not entry: read `.agent-kit/project.yml` + `stack.md` together | plugins/agent-kit/skills/ship/SKILL.md:96-97
session:ship-run -> ext:git | invokes | clean tree required; branch `claude/<slug>` cut from freshly-pulled default, unless run file names branch/base already | plugins/agent-kit/skills/ship/SKILL.md:99-101
session:ship-run -> file:run-file | writes | created at Design; `step` set on entry to each phase; closed with `done`/`blocked` | plugins/agent-kit/skills/ship/SKILL.md:103-114
session:ship-run -> file:run-file | reads | `--run <dir>` means resume from `step`, including after an account-limit kill | plugins/agent-kit/skills/ship/SKILL.md:110-114
session:ship-run -> file:gitignore | writes | adds `.agent-kit/runs/` if absent | plugins/agent-kit/skills/ship/SKILL.md:128-129
hook:stop -> session:ship-run | blocks | (referenced, not this sector) stop hook refuses to end turn mid-step; matches on `session` field | plugins/agent-kit/templates/run.json:22
script:orchestrate -> session:ship-run | spawns | one `claude` session per batch child, prompt `/agent-kit:ship --run <dir>` unless run file's `prompt` overrides | plugins/agent-kit/scripts/orchestrate.py:7,846
script:orchestrate -> session:ship-run | invokes | types the handoff line when context has grown past budget: "finish the task you are on ... do not start the next task" | plugins/agent-kit/scripts/orchestrate.py:43-46
session:ship-run -> file:run-file | writes | `handoff` (≤2000 chars, 4 answers) written before stopping; consumer empties it on pickup | plugins/agent-kit/skills/ship/SKILL.md:131-166
session:ship-run -> file:run-file | reads | on resuming a handoff: read note, move durable bits into owning fields, empty `handoff`, continue from `step` | plugins/agent-kit/skills/ship/SKILL.md:160-166
session:ship-run -> file:run-file | reads | `parent` names another run → read its run file first (approach, assumptions, deviations) before designing | plugins/agent-kit/skills/ship/SKILL.md:182-186
session:ship-run -> gate:owner-present | invokes | Design's "wait for go only if expensive fork" decision | plugins/agent-kit/skills/ship/SKILL.md:201-204
session:ship-run -> rule:asking | invokes | how the go/no-go and expensive-fork questions are put | plugins/agent-kit/skills/ship/SKILL.md:60-61,201
session:ship-run -> file:run-file | writes | `waiting_on` set before asking; on answer, cleared and appended to `answers` | plugins/agent-kit/skills/ship/SKILL.md:206-211
session:ship-run -> script:check | invokes | `check.py . --owed` — prints verification kinds this project checks itself for | plugins/agent-kit/skills/ship/SKILL.md:213-222
session:ship-run -> file:run-file | writes | Design ends: `approach`, `seams`, `verified` (kind + tests-or-why), `tasks` list all set | plugins/agent-kit/skills/ship/SKILL.md:224-233
session:ship-run -> file:run-file | writes | each closed task writes its closing SHA into `tasks[].commit` alongside `done: true` | plugins/agent-kit/skills/ship/SKILL.md:235-238
session:ship-run -> file:knowledge | writes | `[assumed …]` block under the entry when a decision is `expensive: true` | plugins/agent-kit/skills/ship/SKILL.md:264,286-289
session:ship-run -> file:run-file | writes | `assumptions[]` (`expensive` bool always answered), `deviations[]`, `unmet[]`, `notes` | plugins/agent-kit/skills/ship/SKILL.md:258-297
session:ship-run -> file:knowledge | writes | test marked `agent-kit:unmet <entry key>` beside the code; comment findable by grep in any language | plugins/agent-kit/skills/ship/SKILL.md:37-42,265
session:ship-run -> file:run-file | writes | `manual[]` records with a `proof` command; and a line in `docs/manual.md` copied from `tpl:manual` when this run opens its own PR | plugins/agent-kit/skills/ship/SKILL.md:267
session:ship-run -> file:knowledge | writes | `[found …]` block under `stack.md` for a ready-made answer the library map lacks | plugins/agent-kit/skills/ship/SKILL.md:269,291-292
session:ship-run -> file:knowledge | writes | `[stale …]` block under an entry whose prose this feature makes false | plugins/agent-kit/skills/ship/SKILL.md:270,293-295
session:ship-run -> file:technical-debt-md | writes | line for work understood and not done; deletes line + `closed_debt` entry when finished | plugins/agent-kit/skills/ship/SKILL.md:271-272,297-299
session:ship-run -> tpl:technical-debt | reads | copies template to `docs/technical_debt.md` if project has none | plugins/agent-kit/skills/ship/SKILL.md:298-299
session:ship-run -> ext:project-suite | invokes | run declared `test`/`lint`/`types` once; `git rev-parse HEAD` recorded into `proved_at` | plugins/agent-kit/skills/ship/SKILL.md:312-321
session:ship-run -> ext:project-mutate | invokes | `commands.mutate` substituting `{files}` = `git diff --name-only <base>...HEAD`; results into `mutation.killed`/`survived`, or `why` if absent | plugins/agent-kit/skills/ship/SKILL.md:322-333
session:ship-run -> file:run-file | writes | `verified[]` records completed with `command` and `result` for every kind listed at design | plugins/agent-kit/skills/ship/SKILL.md:335-349
session:ship-run -> ext:project-run | invokes | starts app and exercises the changed surface, or records "nothing to open" | plugins/agent-kit/skills/ship/SKILL.md:351-356
session:ship-run -> file:run-file | writes | `suite` field with what ran and what it returned; rerun once more after fixes | plugins/agent-kit/skills/ship/SKILL.md:358-359
hook:guard -> ext:project-run/e2e | blocks | refuses the project's declared `commands.e2e` (or any command that is a superset match) from running inside a registered `ship` session | plugins/agent-kit/hooks/guard.py:222-248
session:ship-run -> ext:git | invokes | commit and push the branch (Deliver step 1) | plugins/agent-kit/skills/ship/SKILL.md:372
session:ship-run -> agent:reviewer | spawns | given: base branch to diff against, run file path, the entries, expanded path of `rules/craft.md` | plugins/agent-kit/skills/ship/SKILL.md:423-426
agent:reviewer -> ext:git | invokes | `git diff <base>...HEAD` (only source of the diff, never against default unless told) | plugins/agent-kit/agents/reviewer.md:14-16
agent:reviewer -> file:knowledge | reads | entries named in the run file + `stack.md` | plugins/agent-kit/agents/reviewer.md:16
agent:reviewer -> file:run-file | reads | approach, task list, assumptions, deviations already recorded | plugins/agent-kit/agents/reviewer.md:17
agent:reviewer -> rule:craft | reads | at the path given by ship; asked five questions, one of them out of craft.md | plugins/agent-kit/agents/reviewer.md:19-22
agent:reviewer -> ext:git | invokes | `git show <sha> --stat` per closed task to verify the commit's work is present | plugins/agent-kit/agents/reviewer.md:48-51
agent:reviewer -> session:ship-run | returns-to | ordered findings (`file:line — severity — what — fix`) plus a merge-without-reading verdict | plugins/agent-kit/agents/reviewer.md:96-118
session:ship-run -> file:run-file | writes | `review.findings[]` (severity, what) as they arrive, before fixing any; then `closed`/`how` per finding; `review.verdict`, `review.security` | plugins/agent-kit/skills/ship/SKILL.md:373-379
session:ship-run -> ext:security-review | invokes | on trigger surfaces only; else skipped and PR says why | plugins/agent-kit/skills/ship/SKILL.md:442-444
session:ship-run -> ext:project-suite | invokes | rerun suite after the one round of fixes | plugins/agent-kit/skills/ship/SKILL.md:380
session:ship-run -> agent:reviewer | spawns | re-run only if the fix round changed structure, not lines | plugins/agent-kit/skills/ship/SKILL.md:455-456
session:ship-run -> rule:pull-requests | reads | shape rule for the PR body it opens | plugins/agent-kit/skills/ship/SKILL.md:381
session:ship-run -> script:check | invokes | `check.py . --pr-body <file>` and `check.py . --pr-base <base>` before opening/editing | plugins/agent-kit/rules/pull-requests.md:34-43
session:ship-run -> ext:gh | invokes | `gh pr create` (implied by pull-requests.md) — never merges | plugins/agent-kit/skills/ship/SKILL.md:381; rules/pull-requests.md:4
hook:guard -> ext:gh | refuses | `gh pr merge` always blocked while any run is in flight | plugins/agent-kit/hooks/guard.py:249-252
hook:guard -> ext:git | refuses | force-push and push-to-default-branch always blocked while any run is in flight | plugins/agent-kit/hooks/guard.py:253-262
hook:guard -> ext:git | refuses | `git checkout`/`switch` moving the shared checkout's branch from an unregistered session while a run holds that tree | plugins/agent-kit/hooks/guard.py:213-221
session:ship-run -> file:knowledge | writes | entry's machine line set to `state: building (pr: <n>)`, committed and pushed on this branch — only when NOT inside a batch | plugins/agent-kit/skills/ship/SKILL.md:382-390
session:ship-run -> ext:gh | invokes | `gh pr checks` (or closest equivalent) to read CI; fixes own-fault failures, bounds the wait | plugins/agent-kit/skills/ship/SKILL.md:391-394
session:ship-run -> file:run-file | writes | close: `step: "done"`, `suite`, `pr`, any `blocker` | plugins/agent-kit/skills/ship/SKILL.md:395
session:ship-run -> script:check | invokes | `check.py . --run .agent-kit/runs/<slug>` read-back before finishing (also used mid-run at handoff) | plugins/agent-kit/skills/ship/SKILL.md:147-149,399-401
session:ship-run -> rule:closing | reads | final closing shape: what's thin, then next command | plugins/agent-kit/skills/ship/SKILL.md:417-419
gate:deliver-mode -> session:ship-run | blocks | `deliver: "branch"` stops the run after Deliver step 3 (push+review); no PR, no CI wait | plugins/agent-kit/skills/ship/SKILL.md:409-413
gate:touched-product -> agent:reviewer | refuses | diff touching only tests/fixtures/lock-files/docs skips the reviewer; ship states so in `review.verdict` | plugins/agent-kit/skills/ship/SKILL.md:429-440
gate:touched-product -> ext:security-review | refuses | same diff-touch test decides whether `/security-review` runs | plugins/agent-kit/skills/ship/SKILL.md:440
cmd:next -> cmd:ship | hands-off | offers `/agent-kit:ship <key>` for one missing entry, or a task-only ship for CI/skeleton/dependency-bump work | plugins/agent-kit/skills/next/SKILL.md:152,208-212
cmd:sprint -> session:ship-run | delegates | composes a batch's `run.json` children with `command: "ship"`, `entries`/`task`, optionally pre-filled `approach`/`tasks` | plugins/agent-kit/skills/sprint/SKILL.md:161,190-191
script:orchestrate -> file:run-file | reads | `children`, applies `frame`'s `needs` map, watches transcript mtime for hand-over sizing | plugins/agent-kit/scripts/orchestrate.py (throughout)
cmd:epic -> script:orchestrate | invokes | runs `ship` per feature and the closing session per batch via the driver | plugins/agent-kit/skills/epic/SKILL.md:16
cmd:fix -> rule:craft | reads | fix shares craft.md, asking.md, unmet-marking with ship but needs less context | plugins/agent-kit/skills/fix/SKILL.md:11,24,45,71,108-111

## PHASE SPINE

0. **Opening line** (`rule:closing`) — before the check, before anything: one line, project's language, which run/what/where it lands. Entry: session starts. Exit: immediately proceeds.
1. **Knowledge check** — `check.py .`; react per `rule:preflight` plus ship's two extra rows (an `unmet` promise on an entry about to be touched → read that test first; entry already `built` → ask if this is a change). Entry: after opening line. Exit: no stop condition here except "a run is already in flight" (see Refusals).
2. **Brief read** — `check.py . --brief <key>` (one call: project corner, entry, named entries, library map, craft.md) OR, task-only, read `project.yml` + `stack.md` together. Entry: check reacted to. Exit: nothing else is read yet ("read nothing else yet").
3. **Branch setup** — working tree must be clean (blocker if not); create `claude/<slug>` off freshly-pulled default, unless run file already names branch/base. Exit: branch ready, run file existing or about to be created.
4. **Design** (skipped if run file already carries approach+tasks) — read parent run file if `parent` set; else read code the entry touches (callers, stored data); settle approach, name seams; put up one screen (goal/approach/diagram-if-flow-changes/givens/defaults); wait for go only on an expensive fork (`gate:owner-present`, `rule:asking`), else state-and-start; `check.py . --owed` to get verification kinds; write one `verified` record per kind (tests-to-write or `why`) into run file. Exit: run file holds approach, seams, `verified`, and a task list where each task is the smallest independently-verifiable unit.
5. **Build** — task by task, one commit each; write test before code (default), covering every `verified` kind in the same commit as the change (exception: presentation-shape lines, written after and run once against unfixed code); record findings live into the fields in the "What you found" table (assumptions/unmet/manual/deviations/[found]/[stale]/debt/notes) as they occur, not at the end; each closed task writes its commit SHA. Exit: all tasks done, entry's lines covered or explicitly marked unmet with design's sign-off.
6. **Verify** — (1) cover the entry: every line has a naming test, unmet-marked lines count only if design decided so; (2) run declared suite once, record `proved_at` = `git rev-parse HEAD`, rerun on every subsequent suite run; (3) run `commands.mutate` over changed files, record `killed`/`survived` or `why`+command if absent; (4) run every `verified` kind listed at design, complete each record's `command`+`result`, note where a kind would have caught this and the project refused it; (5) start the app via `commands.run` and exercise the changed surface if one exists, or say there is none. Fix failures, rerun suite once more at the end. Never run `commands.e2e` here (guard hook blocks it; belongs to whatever integrates a batch), except when the task itself is a scenario, marked `agent-kit:scenario <heading>`.
7. **Deliver** — 1) commit+push branch; 2) Review (see below), findings written to `review.findings` as they arrive, closed/how as fixed; 3) one round of fixes + rerun at-risk parts + suite; 4) open PR per `rule:pull-requests` (never merge); 5) set entry's `state: building (pr: <n>)`, commit+push — **skipped entirely inside a batch**, the closing session does this later for the whole batch; 6) `gh pr checks` (bounded wait, fix own-fault failures, report design-level failures as blockers); 7) close run file (`step: "done"`, `suite`, `pr`, blockers) and read it back with `check.py . --run <dir>`; report any entry-text drift found by the check in the PR only. **`deliver: "branch"` short-circuits after step 3**: push, close run file with branch name, no PR, no CI wait.
8. **Review** (sub-procedure invoked inside Deliver step 2) — `git diff --name-only <base>...HEAD` first; if only tests/fixtures/lock-files/docs changed, skip the reviewer (and the security pass) and say so in `review.verdict`; otherwise spawn `agent-kit:reviewer` with base branch, run file path, entries, expanded `craft.md` path; on a trigger surface (auth/permissions, untrusted-input parsing, money, files/processes, migration, outbound call), also run `/security-review`; one round of fixes for everything critical/major/entry-departing/security; re-spawn reviewer only if the fix round changed structure. Never a third pass (no `code-review` plugin, no `/code-review`) — that belongs to the batch/epic level, decided once in `rules/pull-requests.md`.
9. **Closing** (`rule:closing`) — say what is thin (not what was done); name the one next command.

## IO TABLE

session:ship-run | file:run-file (own), file:knowledge (entry+named entries+state line), file:project-yml, file:stack-md, file:run-file of `parent`, output of check.py --brief/--owed/--pr-body/--pr-base/--run, git diff/log, files the diff touches | file:run-file (all fields), file:knowledge (state line, [assumed]/[stale]/[found] blocks, agent-kit:unmet test comments), file:technical-debt-md, file:manual-md, file:gitignore, product code + tests, git commits/branch/push, PR body
agent:reviewer | git diff <base>...HEAD, file:run-file (approach/tasks/assumptions/deviations), file:knowledge (named entries + stack.md), rule:craft, files the diff touches | nothing (read-only) — returns findings text to caller
script:check | file:run-file, file:knowledge, file:project-yml, git state, docs/technical_debt.md, docs/manual.md, docs/runs/*.json | terminal output only (no file writes attributed to ship's use of it, except via `--sync`/`--record` which ship does not invoke)
hook:guard | run files under `.agent-kit/runs/`, project.yml (`commands.e2e`, `verification`), tmux session name | PreToolUse deny decision (no file writes)
script:orchestrate | run files, run.log, transcript mtimes, `control` file | run.log, `control` (deletes after reading), starts/kills sessions, writes `session`/`base`/`branch`/`needs` fields on children

## OWNER GATES

1. **Expensive fork at Design** — trigger: a decision that is expensive to reverse (stored data shape, external contract, permission boundary, money) surfaces while settling the approach. Options: put up via `rule:asking` (AskUserQuestion, recommendation first, options not prose). Effect: run waits (`waiting_on` set) until answered, then cleared into `answers`. Unattended (`gate: none`): never asked; becomes a recorded assumption (`assumptions[]`, `expensive: true`, `[assumed …]` block under the entry) and the run carries on. — plugins/agent-kit/skills/ship/SKILL.md:25-29,201-211
2. **Entry-vs-code contradiction** — trigger: entry promises what the standing code does not do. Effect always: write the test marked `agent-kit:unmet <key>`, `unmet` line in run file, regardless of gate. With owner present: ALSO ask which side is wrong (mark the same way, ask; answer becomes product work now or goes to blueprint via the PR). With `gate: none`: the mark and the `unmet` line are the whole of the move — no question. — plugins/agent-kit/skills/ship/SKILL.md:31-52
3. **Entry already `built`** (preflight row) — trigger: check.py flags the target entry as already built. Only asked when a person typed the command; stop and ask if this is a change to it. Not stated whether this differs headless (preflight.md is silent here beyond the general gate rule) — see Uncertain section.
4. **Piled-up `[assumed]`/`[stale]` blocks on entries in scope** — trigger: preflight's check surfaces prior blocks. Only at the gate of a run a person just typed (`epic`, `sprint`, a `ship` by hand) — never in a driver-raised session whatever `gate` says. Options via `rule:asking`: settle now, hand to `/agent-kit:blueprint` first, or build as-is. Asked once per run. `gate: none` and every driver-started session: section does not exist — blocks followed as written, left for `accept`. — plugins/agent-kit/rules/preflight.md:56-84
5. **"A run is already in flight"** — not a question but a hard stop for a person-typed command (see Refusals below); the owner can overrule in one sentence ("build anyway"), at which point ship works in a worktree instead of the shared tree. — plugins/agent-kit/rules/preflight.md:24-54

## REFUSALS, RETRIES AND EXITS

- **Dirty working tree** at start → reported as a blocker, not worked around. plugins/agent-kit/skills/ship/SKILL.md:99-100
- **A run of this kit already in flight in this checkout**, command typed by a person → do not start; say which run/step; offer to wait, or take a worktree of its own if the work touches no code; owner can overrule and ship then works in a worktree. Does not apply to the session that *is* that run. plugins/agent-kit/rules/preflight.md:24-54
- **Guard hook (mechanical, not ship's own logic)**: while any kit run is in flight in this project — refuses `gh pr merge`, force-push, push to default branch, unconditionally. Inside a session registered as a `ship` specifically — also refuses the project's declared `commands.e2e` (unless it's actually one of the project's own declared verification commands sharing a substring) and refuses `git checkout`/`switch` moving the shared checkout's branch when a run other than this session holds that tree (offers `git worktree add` instead). Fails open with a loud message if the guard module itself cannot load. plugins/agent-kit/hooks/guard.py:213-263
- **Review finds a critical or major issue** → not `step: done` until closed; one round of fixes required; run file's `review.findings[].closed` is what the check enforces at `done` — check.py refuses a finished run with an open critical/major finding. plugins/agent-kit/skills/ship/SKILL.md:379; scripts/check.py:2589-2596 (the `run_defects` check)
- **Suite stays red** → "fix what fails, then run the suite once more at the end" — no explicit retry bound stated beyond that one extra pass; a failure needing a design change becomes a "blocker to report in the pull request" rather than an infinite fix loop (stated explicitly for CI failures at step 6, implied for the suite generally). plugins/agent-kit/skills/ship/SKILL.md:358-359,393-394
- **CI pending** → bounded wait; reported as "pending" rather than polled until the session is killed. plugins/agent-kit/skills/ship/SKILL.md:393-394
- **`verified` kind left silent** (no `result` and no `why`) → check.py refuses a finished feature that is silent about a declared kind — this is the mechanism, not ship's own prose, that catches a written-but-never-run test. plugins/agent-kit/skills/ship/SKILL.md:342-345; scripts/check.py:2671-2678
- **`mutation` left empty** when `commands.mutate` is declared → check.py refuses at `done` unless `why` + the command actually run are both given. plugins/agent-kit/skills/ship/SKILL.md:322-333; scripts/check.py:2636-2648
- **`deliver: "pr"` but `pr` empty and no blockers** → check.py refuses: a run that owed a PR closed with no number. scripts/check.py:2708-2712
- **Task marked done with no commit SHA, or a SHA the repo doesn't have** → check.py refuses (checked continuously, not only at `done`). scripts/check.py:2544-2556
- **Handoff note without `approach`/`tasks` filled, or over 2000 chars** → check.py refuses (checked whenever the file's judged, so the outgoing session can still fix it). scripts/check.py:2420-2432
- **Loop-back "one round of fixes"**: after review returns findings, ship fixes everything critical/major/entry-departing/security once, reruns suite; re-spawns the reviewer only if the fix changed structure (not for line-level fixes) — bounded to essentially one extra reviewer pass, never a third full pass over the same diff (explicitly ruled out — cites 6.7M-token cost for 2 findings vs 0.66M for 12). plugins/agent-kit/skills/ship/SKILL.md:453-456
- **Handoff instead of finishing** (not a failure, a designed exit): driver decides when context has grown past budget; ship finishes the current task to its commit, closes it, writes `handoff`, stops — must not start the next task and must not fake `step: "done"` to escape. plugins/agent-kit/skills/ship/SKILL.md:131-149
- **Owner's `stop` via the control window** mid-batch (not ship's own mechanism, but affects it): driver applies it only at the boundary between features, never mid-feature — a half-built feature is never killed. plugins/agent-kit/rules/window.md:96-107

## PROMISES MADE TO OTHER PARTS

- To **whatever launched it** (driver, sprint, epic, or a person): a run file left in a state any reader (resuming session, closing session, check.py) can act on without re-deriving anything — approach, seams, tasks with commits, assumptions with `expensive` always answered, `unmet` lines, `manual` records with executable `proof`, `verified` kinds all completed, `mutation` bound, `suite` bound to `proved_at` on the delivered branch, `review.findings` all closed of critical/major.
- To the **closing session of a batch**: ship never sets the entry's `state: building (pr: n)` line itself when inside a batch — it relies on the closing session to do that for the whole chain from the batch's own PR. plugins/agent-kit/skills/ship/SKILL.md:388-390
- To **blueprint**: never rewrites knowledge prose itself; only appends machine state lines and `[assumed]`/`[stale]`/`[found]` blocks for blueprint to fold in or resolve. plugins/agent-kit/skills/ship/SKILL.md:462
- To **the reviewer**: hands it a stable base branch, the run file, the entries, and an already-expanded `craft.md` path (reviewer cannot resolve `${CLAUDE_PLUGIN_ROOT}` itself).
- To **whatever integrates a batch / runs scenarios**: ship explicitly does not run `commands.e2e` (guard-enforced) and does not decide the product's scenarios — that's left to what composes the batch.
- Relies on **`sprint`/`epic`** to have already written `command: "ship"`, `entries`/`task`, and optionally `approach`/`tasks` into the run file before starting it, and to have set `gate`, `deliver`, `parent`, `base` correctly.
- Relies on **the driver (`orchestrate.py`)** to be the only one starting a second session against a shared checkout, to apply `handoff` hand-over correctly, and to be the sole writer of `run.log`/`control`/`session`.
- Relies on **`blueprint`** to have written `project.yml`'s `commands.*` and `verification` answers already — ship never edits `project.yml`, only reads it, and never installs anything mid-run to make a missing verification command work.

## UNCERTAIN / CONTRADICTORY

- **"Entry already `built`" gate and headless behavior**: `rules/preflight.md` row says "say so and ask whether this is a change to it" but does not spell out what happens under `gate: none` / inside a driver-started session for this specific row (unlike the `[assumed]`-blocks row, which explicitly says "gate: none... follow them as written"). Left ambiguous whether an unattended `ship` on an already-built entry stops, assumes "yes, this is a change," or proceeds silently. plugins/agent-kit/rules/preflight.md:10-22
- **Where exactly the reviewer is spawned from**: SKILL.md says "The `agent-kit:reviewer` agent" without naming the mechanism (Task tool / Agent tool) explicitly — inferred from the repo's agent definitions and the `Agent`-tool convention, not stated in SKILL.md itself.
- **Bound on suite retries**: "Fix what fails, then run the suite once more at the end" (SKILL.md:358) does not state what happens if the second run is still red — whether this becomes a `blocker` automatically or ship keeps iterating; only CI (step 6) has an explicit bounded-wait rule. Left to be inferred from `rule:craft`'s "the door out is marked" (a blocker is a legitimate result) but not spelled out as a loop bound for the suite specifically.
- **`--tests`, `--state`, `--status`, `--sync`, `--record` flags of check.py**: these exist in the script (confirmed by argparse) but SKILL.md and the rules ship reads do not show ship itself invoking them — they appear to belong to other commands (`next`, `blueprint`, `accept`). Listed here for completeness of the script's surface, not claimed as part of ship's own flow.
- **Exact wording of the `[frame …]` block enforcement**: craft.md/SKILL.md describe it as binding "whether or not you would have chosen it," and the reviewer treats a quiet departure from it as a finding "even where what it did is defensible on its own" — this is a strong, almost contradictory-sounding rule (consistency overriding local correctness) worth flagging as intentional-but-unusual rather than an error.
- **`templates/manual.md` and `templates/technical_debt.md`** were not opened in full (out of scope per instructions — "read enough of any rules/*.md ship points at"); their exact shape is asserted only from SKILL.md's description of how ship uses them, not from reading the templates themselves.
