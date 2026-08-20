# Sector: fix, accept, next

Files read in full:
- `plugins/agent-kit/skills/fix/SKILL.md`
- `plugins/agent-kit/skills/accept/SKILL.md`
- `plugins/agent-kit/skills/next/SKILL.md`
- `plugins/agent-kit/rules/preflight.md`
- `plugins/agent-kit/rules/closing.md`
- `plugins/agent-kit/rules/audit-boxes.md`
- `plugins/agent-kit/rules/craft.md`
- `plugins/agent-kit/rules/pull-requests.md`
- `plugins/agent-kit/scripts/check.py` (argparse block lines 3599-3728, tail lines 3728-3897, `--run` handler 3670-3700)
- `plugins/agent-kit/templates/run.json` (field shapes referenced by all three)

README category labels (`plugins/agent-kit/README.md:21,26,27`): `fix` = build, `accept` = check,
`next` = orient.

---

## Command: fix

### NODES

`cmd:fix | command | /agent-kit:fix | small, cheap repair command: cause, failing test, minimal change, deliver | skills/fix/SKILL.md:1-6`
`phase:fix-invoke | phase | Invocation | three input sources: owner's words, red output, --pr <n> | skills/fix/SKILL.md:14-18`
`gate:not-a-fix | gate | "When this is not a fix" | boundary: new behaviour, a product decision, or a rewrite ends the run early | skills/fix/SKILL.md:20-34`
`script:check-bare | script | check.py . (bare) | knowledge check, mechanical, seconds; exit 0 clean/silent, exit 1 with findings | skills/fix/SKILL.md:40-42; scripts/check.py:3827-3844,3897`
`rule:preflight | rule | rules/preflight.md | reaction table to what check.py found, incl. "run in flight" refusal | skills/fix/SKILL.md:44`
`rule:craft | rule | rules/craft.md | four rules on code craft, read before cause-finding and handed to reviewer | skills/fix/SKILL.md:46-48,119-121`
`phase:fix-branch | phase | Branch / run file setup | clean tree required; branch naming; run.json created | skills/fix/SKILL.md:51-60`
`file:run-json | file | .agent-kit/runs/<slug>/run.json | run record: task, cause, suite+proved_at, review, manual, notes | skills/fix/SKILL.md:54-60; templates/run.json`
`phase:fix-cause | phase | Find the cause | read code along symptom path until "this line, this condition"; name missing test | skills/fix/SKILL.md:62-75`
`gate:entry-contradiction | gate | entry vs code contradiction | expensive fork shared with ship: mark/ask/record, not resolved here | skills/fix/SKILL.md:70-71`
`gate:cause-not-found | gate | cause won't come out | stop after ~1hr / flaky repro, report ruled-out, suspicion, next step | skills/fix/SKILL.md:73-75`
`phase:fix-prove | phase | Prove it, then change it | write failing test first at existing seam, confirm it fails for the right reason | skills/fix/SKILL.md:77-89`
`gate:flake-exception | gate | failure a test cannot hold | flake/env/race: say so in run file, name alternative, expect reviewer question | skills/fix/SKILL.md:87-89`
`phase:fix-change | phase | Minimal change | fix only the cause; neighbouring issues go to docs/technical_debt.md | skills/fix/SKILL.md:91-94`
`phase:fix-verify | phase | Verify | 4 steps: full suite, mutation/manual-undo proof, --owed verification, app exercise | skills/fix/SKILL.md:96-114`
`script:check-owed | script | check.py . --owed | prints kinds of verification this project owes + command for each | skills/fix/SKILL.md:106-108; scripts/check.py:3624-3626,3664-3665`
`file:project-yml | file | project.yml (commands, commands.mutate) | source of test/type/lint commands and optional mutation command | skills/fix/SKILL.md:98-102`
`file:technical-debt | file | docs/technical_debt.md | ledger for neighbouring issues not fixed | skills/fix/SKILL.md:93,145`
`agent:reviewer | subagent | agent-kit:reviewer | reviews change against craft.md (path handed explicitly); returns verdict + findings | skills/fix/SKILL.md:118-123`
`phase:fix-deliver | phase | Deliver | review record, PR (new or onto existing --pr branch), close run file, check --run, closing.md | skills/fix/SKILL.md:116-141`
`rule:pull-requests | rule | rules/pull-requests.md | PR shape: 3 open answers, cause in first lines, "what was hard" | skills/fix/SKILL.md:125-128; rules/pull-requests.md`
`script:check-run | script | check.py . --run .agent-kit/runs/<slug> | judges closing run file for what a finished run may not leave behind; exit 1 if defects, 0 if none | skills/fix/SKILL.md:136-138; scripts/check.py:3670-3700`
`rule:closing | rule | rules/closing.md | first-line intro, thin-spots close, next-command line | skills/fix/SKILL.md:140; rules/closing.md`
`session:pr-branch | ext | branch claude/fix-<slug> or PR's own branch | delivered artifact | skills/fix/SKILL.md:52,130-131`
`ext:gh-pr | ext | GitHub pull request | new PR, or commit+push onto existing --pr's branch | skills/fix/SKILL.md:125-131`
`gate:no-refactor | gate | "What this command does not do" | refuses refactor, entry rewrite, merge, symptom-less work | skills/fix/SKILL.md:143-148`

### EDGES

`cmd:fix -> phase:fix-invoke | invokes | any of the 3 argument forms | skills/fix/SKILL.md:14-18`
`phase:fix-invoke -> gate:not-a-fix | blocks | cause turns out to be missing feature / product decision / rewrite | skills/fix/SKILL.md:20-34`
`gate:not-a-fix -> ext:hand-off-blueprint | hands-off | "this was never built" | skills/fix/SKILL.md:23-24` (see cross-command)
`gate:not-a-fix -> file:technical-debt | writes | fix would be a rewrite: one line, cause named | skills/fix/SKILL.md:32-34`
`phase:fix-invoke -> script:check-bare | invokes | "Before you start", mechanical, seconds | skills/fix/SKILL.md:40-42`
`script:check-bare -> rule:preflight | delegates | react to findings | skills/fix/SKILL.md:44`
`rule:preflight -> gate:run-in-flight | blocks | a run of this kit holds the checkout | rules/preflight.md:29-46`
`phase:fix-invoke -> rule:craft | reads | four craft rules, before cause-finding | skills/fix/SKILL.md:46-48`
`phase:fix-invoke -> file:run-json | reads | entry covering the broken behaviour, "as its own section" | skills/fix/SKILL.md:45-46`
`phase:fix-branch -> ext:git | invokes | checkout PR branch (--pr) or branch claude/fix-<slug> off freshly pulled default | skills/fix/SKILL.md:51-52`
`phase:fix-branch -> file:run-json | writes | task, cause (later), suite+proved_at, review, manual, notes | skills/fix/SKILL.md:54-60`
`phase:fix-cause -> gate:entry-contradiction | blocks | cause is entry-vs-code contradiction | skills/fix/SKILL.md:70-71`
`phase:fix-cause -> gate:cause-not-found | refuses | ~1hr in, cause won't surface | skills/fix/SKILL.md:73-75`
`phase:fix-cause -> phase:fix-prove | loops-to | cause named at line/condition granularity | skills/fix/SKILL.md:64,77`
`phase:fix-prove -> gate:flake-exception | blocks | failure a test cannot hold (flake/env/race) | skills/fix/SKILL.md:87-89`
`phase:fix-prove -> phase:fix-change | loops-to | test fails for the found reason | skills/fix/SKILL.md:84-91`
`phase:fix-change -> file:technical-debt | writes | tidy-ups/neighbouring defects, one line each | skills/fix/SKILL.md:92-93`
`phase:fix-change -> phase:fix-verify | loops-to | change made | skills/fix/SKILL.md:96`
`phase:fix-verify -> file:project-yml | reads | commands: tests/types/lint, once at end; commands.mutate | skills/fix/SKILL.md:98-102`
`phase:fix-verify -> file:run-json | writes | mutation{killed,survived} or manual-undo proof | skills/fix/SKILL.md:100-105`
`phase:fix-verify -> script:check-owed | invokes | list of verification kinds owed | skills/fix/SKILL.md:106-108`
`phase:fix-verify -> file:run-json | writes | verified[]: kind, command, result-or-why | skills/fix/SKILL.md:106-111`
`script:check-run -> gate:owed-unfinished | blocks | "the check refuses a finished run that is silent about one" | skills/fix/SKILL.md:110-111`
`phase:fix-verify -> file:run-json | writes | suite: what was opened in running app and seen, or "not exercised" | skills/fix/SKILL.md:113-114`
`phase:fix-verify -> phase:fix-deliver | loops-to | verification complete | skills/fix/SKILL.md:116`
`phase:fix-deliver -> agent:reviewer | spawns | change touched the product (test-only fix skips) | skills/fix/SKILL.md:118-119`
`agent:reviewer -> rule:craft | reads | path handed explicitly by fix, else must report the question unasked | skills/fix/SKILL.md:119-121`
`agent:reviewer -> file:run-json | returns-to | verdict + findings, one record each (severity, closed) | skills/fix/SKILL.md:121-123`
`gate:review-open-finding -> phase:fix-deliver | blocks | a critical/major finding left open blocks step: done | skills/fix/SKILL.md:122-123`
`phase:fix-deliver -> rule:pull-requests | reads | shape of the PR body | skills/fix/SKILL.md:125`
`phase:fix-deliver -> ext:gh-pr | invokes | new PR (default path) with cause in first lines | skills/fix/SKILL.md:125-128`
`phase:fix-deliver -> ext:gh-pr | invokes | --pr <n>: commit onto that branch, push, no new PR/branch | skills/fix/SKILL.md:130-131`
`phase:fix-deliver -> file:run-json | writes | close: step: done, suite, pr, deferred items | skills/fix/SKILL.md:133`
`phase:fix-deliver -> script:check-run | invokes | check.py . --run .agent-kit/runs/<slug>, silent unless a finished run overreaches | skills/fix/SKILL.md:134-138`
`phase:fix-deliver -> rule:closing | delegates | thin spots, where they live, next command | skills/fix/SKILL.md:140`
`gate:no-refactor -> file:technical-debt | writes | refactor/tidy/second-defect ideas, never applied here | skills/fix/SKILL.md:143-148`
`gate:no-refactor -> ext:blueprint | hands-off | entry rewrite is never fix's to do | skills/fix/SKILL.md:146`

### PHASE SPINE

1. Invocation (owner words / red output / `--pr <n>`) → not-a-fix boundary check
2. Knowledge check (`check.py .`) + preflight reaction + craft.md + relevant entry section
3. Clean tree, branch (`claude/fix-<slug>` or checkout `--pr <n>`'s branch), open run.json
4. Find the cause (read code path to line/condition; name the missing/wrong test) — entry-contradiction fork or cause-not-found stop can end this here
5. Prove it: write failing test first at existing seam, run, confirm it fails for the right reason (flake exception possible)
6. Change the least that makes it pass; sweep-ups go to technical_debt.md
7. Verify: full suite once at end → mutation/manual-undo proof → `--owed` verification kinds → app exercise if reachable
8. Deliver: reviewer (if product touched) → PR (new, or commit+push onto `--pr`'s branch) → close run file → `check.py --run` → closing.md

### IO TABLE

| Reads | Writes |
|---|---|
| entry covering the broken behaviour (as a section, not opened whole) | `.agent-kit/runs/<slug>/run.json` (task, cause, suite, proved_at, review, manual, notes, verified, mutation, deferred, step) |
| `rules/craft.md`, `rules/preflight.md`, `rules/pull-requests.md`, `rules/closing.md` | `docs/technical_debt.md` (neighbouring defects, rewrite candidates) |
| `project.yml` → `commands` (tests/types/lint), `commands.mutate` | git branch `claude/fix-<slug>` or commit onto `--pr <n>`'s branch |
| `check.py --owed` output | pull request (new, or update to existing) |
| code along the symptom's path | run file closing fields |

### OWNER GATES

- None that *wait* mid-run inside fix itself — no explicit "ask the owner" question is posed by fix's own text beyond the shared entry-contradiction fork (mark/ask/record "exactly as ship does" — ship's asking behaviour is outside this sector).
- `--pr <n>` implies an owner already opened a review round; fix answers it, does not initiate a new question.
- `flake exception`: "expect the reviewer to ask" — deferred to reviewer, not the owner directly, within this file's text.

### REFUSALS AND EXITS

- **Run in flight** (via `rules/preflight.md`): fix is explicitly named among commands that must not start while another run of the kit holds the checkout (`rules/preflight.md:35`: "That is `ship`, `fix`, `sprint`, `epic` and `next`"). Says which run/step, stops; offers wait or worktree if code-free (not fix's case since fix writes code).
- **Not a fix** (`skills/fix/SKILL.md:20-34`): missing feature → hand to blueprint/ship; product decision → record in entry, stop; rewrite → write to technical_debt.md, let owner decide.
- **Cause won't come out** (`skills/fix/SKILL.md:73-75`): stop and report ruled-out causes, suspicion, next look — no change made.
- **Flake exception** (`skills/fix/SKILL.md:87-89`): cannot write a holding test — record in run file, name alternative proof.
- **check.py --run refuses silently-incomplete finished run** (`skills/fix/SKILL.md:110-111,134-138`): a `fix` cannot close `step: done` if silent on an owed verification kind.
- **Review open finding**: a critical/major finding not `closed` blocks `step: done` (`skills/fix/SKILL.md:122-123`).
- **What this command does not do** (`skills/fix/SKILL.md:143-148`): explicit refusal list — no refactor, no entry rewrite, no merge, no symptom-less "looks wrong" work.

---

## Command: accept

### NODES

`cmd:accept | command | /agent-kit:accept [pr#] | reads a finished run's PR + run files, says mergeable-or-not and what needs hands, in order | skills/accept/SKILL.md:1-6`
`gate:no-diff-read | gate | "You do not read the diff" | boundary: accept never re-reviews the diff itself | skills/accept/SKILL.md:20-24`
`script:gh-pr-view | script | gh pr view <n> --json title,body,mergeable,statusCheckRollup | reads PR metadata/CI state | skills/accept/SKILL.md:29`
`script:check-status-state | script | check.py . --status --state | reads project knowledge + branch/PR/run state | skills/accept/SKILL.md:30`
`file:batch-json | file | docs/runs/*.json | batch-level run records (answers, unmet, manual, blockers, deviations, notes) | skills/accept/SKILL.md:33-36`
`file:run-json-live | file | .agent-kit/runs/*/run.json | still-on-machine run records, same fields | skills/accept/SKILL.md:33-36`
`phase:accept-verdict | phase | Block 1: verdict | one line: mergeable now / after N steps / not mergeable, CI/conflicts override | skills/accept/SKILL.md:46-48`
`phase:accept-manual | phase | Block 2: manual actions | numbered, ordered, from docs/manual.md merged with runs' manual records | skills/accept/SKILL.md:50-61`
`script:check-manual | script | check.py . --manual | runs proofs, deletes done lines, before listing what's left | skills/accept/SKILL.md:56-57`
`phase:accept-waiting | phase | Block 3: waiting on a decision | every timed-out waiting_on, every assumption-because-nobody-was-there, body's owner items; each with a recommendation | skills/accept/SKILL.md:62-65`
`phase:accept-decisions | phase | Block 4: decisions taken without them | expensive ones named, rest as count; offers to settle now before merge | skills/accept/SKILL.md:67-81`
`ext:blueprint-narrowed | ext | /agent-kit:blueprint, narrowed to this run's blocks | owns the prose; accept hands off, never writes itself | skills/accept/SKILL.md:78-81`
`phase:accept-unproven | phase | Block 5: what is not proven | agent-kit:unmet tests, no-e2e scenarios, never-exercised parts, CI-elsewhere-unproven, stand-in seams | skills/accept/SKILL.md:83-101`
`phase:accept-worktree | phase | Block 6: how to look at it | worktree command, free port, first scenario to click through | skills/accept/SKILL.md:103-105`
`rule:audit-boxes | rule | rules/audit-boxes.md | accept is one of 3 sessions allowed to tick an audit box | skills/accept/SKILL.md:112-113`
`script:check-sync | script | check.py . --sync | moves entry state line when its PR has merged | skills/accept/SKILL.md:115`
`gate:accept-no-write | gate | "does not fix, merge, answer, open" | accept's action boundary | skills/accept/SKILL.md:117-118`
`rule:closing-accept | rule | rules/closing.md | thin-spots + next-command line | skills/accept/SKILL.md:122-124`

### EDGES

`cmd:accept -> script:gh-pr-view | invokes | reads title/body/mergeable/statusCheckRollup | skills/accept/SKILL.md:29`
`cmd:accept -> script:check-status-state | invokes | reads project knowledge state | skills/accept/SKILL.md:30`
`cmd:accept -> file:batch-json | reads | for answers/unmet/manual/blockers/deviations/notes | skills/accept/SKILL.md:33-36`
`cmd:accept -> file:run-json-live | reads | same fields, while still on this machine | skills/accept/SKILL.md:33-36`
`gate:no-diff-read -> cmd:accept | blocks | diff itself is never opened; reviewer + audit already covered it | skills/accept/SKILL.md:20-24,97-101`
`cmd:accept -> phase:accept-verdict | invokes | after reading gh+check.py+run files | skills/accept/SKILL.md:41-48`
`phase:accept-verdict -> gate:not-mergeable | blocks | red CI or conflicts overrides everything else in the line | skills/accept/SKILL.md:47-48`
`phase:accept-manual -> script:check-manual | invokes | run proofs first, before listing | skills/accept/SKILL.md:56-58`
`phase:accept-manual -> file:manual-md | reads | docs/manual.md merged with run files' manual records | skills/accept/SKILL.md:52-54`
`phase:accept-waiting -> ext:owner | hands-off | each waiting_on / assumption-fork / body item, with accept's own recommendation | skills/accept/SKILL.md:63-65`
`phase:accept-decisions -> script:check-status-state | reads | check.py names entries carrying expensive decisions | skills/accept/SKILL.md:69`
`phase:accept-decisions -> ext:blueprint-narrowed | hands-off | offer to settle now, before merge, while branch still open | skills/accept/SKILL.md:71-81`
`phase:accept-unproven -> file:run-json-live | reads | suite, proved_at, seams proved against stand-ins | skills/accept/SKILL.md:94-96`
`phase:accept-worktree -> ext:git-worktree | hands-off | worktree command for the branch | skills/accept/SKILL.md:103-105`
`accept -> rule:audit-boxes | delegates | tick box it itself verified done | skills/accept/SKILL.md:112-113`
`accept -> script:check-sync | invokes | entry still building whose PR merged, on clean tree | skills/accept/SKILL.md:114-116`
`gate:accept-no-write -> ext:merge | refuses | accept never merges | skills/accept/SKILL.md:14,117-118`
`gate:accept-no-write -> ext:diff-fix | refuses | accept never fixes | skills/accept/SKILL.md:117-118`
`accept -> rule:closing-accept | delegates | ends per closing.md | skills/accept/SKILL.md:122-124`

### PHASE SPINE

1. Read only: `gh pr view` + `check.py --status --state` + run files (batch `docs/runs/*.json` and live `.agent-kit/runs/*/run.json`) — never the diff
2. Block 1 — verdict (mergeable now / after N steps / not mergeable)
3. Block 2 — manual actions, numbered/ordered, proofs run first via `check.py --manual`
4. Block 3 — what's waiting on a decision, each with a recommendation
5. Block 4 — decisions taken without the owner; offer to settle now via blueprint, before merge
6. Block 5 — what is not proven (unmet, no-e2e, never-exercised, CI-elsewhere, stand-in seams)
7. Block 6 — worktree command + first scenario
8. Two permitted writes (audit-boxes tick, `check.py --sync`), only on clean tree; then closing.md

### IO TABLE

| Reads | Writes |
|---|---|
| `gh pr view <n> --json title,body,mergeable,statusCheckRollup` | `docs/audits/<lens>.md` — tick a box it itself verified done (own `docs(audits):` commit) |
| `check.py . --status --state` | entry `state:` line via `check.py . --sync` (own `docs(knowledge):` commit) |
| `check.py . --manual` (executes proofs, deletes done lines) | *(nothing else — no PR edits, no merges, no code, no answers)* |
| `docs/runs/*.json` (batch records) | |
| `.agent-kit/runs/*/run.json` (live records) | |
| `docs/manual.md` | |
| `docs/technical_debt.md` implicitly via check.py counts | |

### OWNER GATES

- Block 3 explicitly hands unresolved `waiting_on` items and assumed forks to the owner, each with accept's own recommended side — "a question handed over without a recommendation is work handed over" (skills/accept/SKILL.md:64-65).
- Block 4 **offers to settle decisions right there in the conversation** — the one place accept solicits live owner input — but does not write the answer itself; hands off to `/agent-kit:blueprint` (skills/accept/SKILL.md:71-81).
- Does accept "wait"? No — it is a synchronous read-and-report command; it does not block pending an owner reply, it just structures the offer for the owner to answer in the same session before merge.

### REFUSALS AND EXITS

- **Never reads the diff** — explicit boundary (skills/accept/SKILL.md:20-26).
- **Never guesses a value out of prose** — unproven stays unproven if no run file backs it (skills/accept/SKILL.md:38-39).
- **Does not send the owner to review the diff again** — explicit refusal, reviewer/audit already did it (skills/accept/SKILL.md:97-101).
- **"does not fix, does not merge, does not answer its own questions, and does not open anything"** — the command's own boundary line (skills/accept/SKILL.md:117-118).
- Writes are fenced to exactly two kinds and only on a clean tree (skills/accept/SKILL.md:110-116) — otherwise presumably reported rather than written (not explicit, but implied by "on a clean tree" condition).

---

## Command: next

### NODES

`cmd:next | command | /agent-kit:next | cold-start orientation: reads state+knowledge, names one next command, changes/starts nothing | skills/next/SKILL.md:1-6,16-17`
`gate:run-in-flight-next | gate | "A run of this kit in flight here" | next refuses to recommend/act while a live run holds the checkout | skills/next/SKILL.md:19-25`
`rule:preflight-next | rule | rules/preflight.md "A run is already in flight here" | shared refusal text; next is on the list of commands that must not start | skills/next/SKILL.md:24; rules/preflight.md:29-46`
`phase:next-bookkeeping | phase | Four bookkeeping writes | manual-done, audit-box-done, building→merged sync, delivered-branch delete — the only writes even while a run is in flight | skills/next/SKILL.md:26-90`
`script:check-manual-next | script | check.py . --manual | run first, before anything else is read; writes only done lines out of docs/manual.md | skills/next/SKILL.md:33-43,102-105`
`rule:audit-boxes-next | rule | rules/audit-boxes.md | next is one of 3 sessions allowed to tick a box | skills/next/SKILL.md:45-47`
`script:check-sync-next | script | check.py . --sync | moves entry state line building→its true state | skills/next/SKILL.md:48-54`
`script:git-branch-delete | script | git branch -D <branch>… && git push origin --delete <branch>… | deletes only branches check.py names as delivered | skills/next/SKILL.md:56-69`
`script:check-status-state-next | script | check.py . --status --state | the one read: knowledge findings, planned/debt/promises/notes, branches/PRs/CI/runs/lens-ages | skills/next/SKILL.md:93-113`
`gate:no-offline | gate | never --offline | offline blinds rungs 3-5 (PR/CI visibility); flag no longer in --help | skills/next/SKILL.md:107-109`
`phase:next-ladder | phase | The ladder | 11 ranked rungs, first that fires is the recommendation | skills/next/SKILL.md:136-260`
`gate:override-no-knowledge | gate | override: no docs/knowledge/ at all | forces blueprint regardless of ladder | skills/next/SKILL.md:244-245`
`gate:override-empty-repo | gate | override: empty repository | forces blueprint then epic | skills/next/SKILL.md:246-248`
`gate:override-mvp-unfinished | gate | override: MVP bounds not reached | swaps rungs 9/10 order | skills/next/SKILL.md:249-254`
`phase:next-report | phase | What you say | 3 blocks: Where it stands / What is in the way / Next | skills/next/SKILL.md:262-286`

### EDGES

`cmd:next -> script:check-manual-next | invokes | first of all, before anything else is read | skills/next/SKILL.md:33-43,102-105`
`script:check-manual-next -> file:manual-md | writes | only lines whose own proof command exits 0 | skills/next/SKILL.md:34-43,102-105`
`cmd:next -> gate:run-in-flight-next | blocks | check prints the in-flight run first | skills/next/SKILL.md:19-25`
`gate:run-in-flight-next -> rule:preflight-next | delegates | rule and offer are defined there | skills/next/SKILL.md:24`
`gate:run-in-flight-next -> phase:next-bookkeeping | hands-off | four facts are still writable even when a run is in flight | skills/next/SKILL.md:26-27`
`cmd:next -> rule:audit-boxes-next | delegates | tick a box, only if tree clean & branch already merged | skills/next/SKILL.md:45-47,84-87`
`cmd:next -> script:check-sync-next | invokes | entry building whose PR merged | skills/next/SKILL.md:48-54`
`cmd:next -> script:git-branch-delete | invokes | only branches check.py calls delivered, by name | skills/next/SKILL.md:56-69`
`phase:next-bookkeeping -> file:knowledge-entry | writes | entry state: line, own docs(knowledge): commit | skills/next/SKILL.md:74-83`
`phase:next-bookkeeping -> file:docs-audits | writes | ticked box, own docs(audits): commit | skills/next/SKILL.md:74-83`
`phase:next-bookkeeping -> file:manual-md | writes | own docs(manual): commit | skills/next/SKILL.md:74-83`
`cmd:next -> script:check-status-state-next | invokes | the one mechanical read, after --manual | skills/next/SKILL.md:93-96`
`script:check-status-state-next -> gate:no-offline | refuses | --offline never used, would blind rungs 3-5 | skills/next/SKILL.md:107-109`
`cmd:next -> phase:next-ladder | invokes | rank findings top-down | skills/next/SKILL.md:136-138`
`phase:next-ladder -> gate:override-no-knowledge | blocks | no docs/knowledge/ | skills/next/SKILL.md:244-245`
`phase:next-ladder -> gate:override-empty-repo | blocks | empty repository | skills/next/SKILL.md:246-248`
`phase:next-ladder -> gate:override-mvp-unfinished | blocks | MVP bounds not reached | skills/next/SKILL.md:249-254`
`phase:next-ladder -> ext:fix | hands-off | rung 4: CI failing | skills/next/SKILL.md:146`
`phase:next-ladder -> ext:blueprint | hands-off | rung 6 waiting_on/assumed; rung 7 knowledge not ready; rung 9 debt/unkept promises/[accepted]/blocks-under-built | skills/next/SKILL.md:148-149,151,193-202`
`phase:next-ladder -> ext:audit | hands-off | rung 8: blind spot (lens never ran / stale / no-e2e scenarios) | skills/next/SKILL.md:150,219-231`
`phase:next-ladder -> ext:sprint | hands-off | rung 9 debt-as-batch or ~5 planned entries; rung 10 ~5 entries | skills/next/SKILL.md:151-152,155-159`
`phase:next-ladder -> ext:epic | hands-off | rung 9/10 whole list; empty-repo override; MVP-bounds-closed later version | skills/next/SKILL.md:151-152,246-248`
`phase:next-ladder -> ext:ship | hands-off | rung 10 single entry; rung 8's "nothing runs the suite" names an ordinary ship building CI | skills/next/SKILL.md:152,204-213`
`phase:next-ladder -> ext:resume-commands | hands-off | rung 2: check names exact resume command per run kind (epic --resume, sprint --resume, ship --run, or the original errand prompt) | skills/next/SKILL.md:233-240`
`phase:next-ladder -> phase:next-report | loops-to | first firing rung becomes "Next" line | skills/next/SKILL.md:262-286`

### PHASE SPINE

1. `check.py --manual` first (writes only proven-done manual lines) — changes what's about to be read
2. Refusal check: run of this kit in flight here? If yes and this session isn't that run: stop, name which run/step, still allowed the four bookkeeping writes
3. Bookkeeping pass (up to 4 kinds): manual-done lines already handled above; tick finished audit boxes; `--sync` entries `building`→merged; delete branches check.py calls delivered — each its own `docs(...)` commit, default branch, no PR, only on clean tree / already-merged branch
4. The one mechanical read: `check.py --status --state` (never `--offline`)
5. Two licensed extra reads only when the ladder is about to recommend them: newest audit work list (unticked boxes), or `docs/technical_debt.md` first lines
6. The ladder: 11 ranked rungs top-down, three overrides (no knowledge / empty repo / MVP bounds not reached), first firing rung wins
7. Report: Where it stands / What is in the way (≤5) / Next (one command + reason + 2-3 alternatives)

### IO TABLE

| Reads | Writes |
|---|---|
| `check.py . --manual` output | `docs/manual.md` — deletes lines whose proof passed (own `docs(manual):` commit) |
| `check.py . --status --state` output | `docs/audits/<lens>.md` — tick verified-done boxes (own `docs(audits):` commit) |
| `docs/audits/*` newest work list (only when about to recommend that lens) | entry `state:` line via `check.py . --sync` (own `docs(knowledge):` commit) |
| `docs/technical_debt.md` first lines (only when about to recommend debt work) | `git branch -D <branch>… && git push origin --delete <branch>…` — only branches check.py names delivered |
| — never: code, transcripts, run logs, entries read whole for their own sake | — never: entry prose, anything outside the four fenced facts |

### OWNER GATES

- next never asks a live question mid-run; it is entirely read-then-recommend. The "Next" line is directed at the owner to act on afterward, not a wait state.
- The report explicitly separates "manual actions cleared automatically" (fact, not owner-facing blocker) from "what is in the way" (skills/next/SKILL.md:269-271).

### REFUSALS AND EXITS

- **A run is already in flight**: next itself is named among commands that must not start when another run holds the checkout (`rules/preflight.md:35`, `skills/next/SKILL.md:19-25`) — but unlike fix/ship/sprint/epic, next still performs its four fenced bookkeeping writes even in this state, because those writes touch no code and match the exception carved out at `skills/next/SKILL.md:26-27`.
- **Never `--offline`**: explicitly forbidden, not merely discouraged — "It is a test seam, not a setting, and no longer appears in `--help`" (skills/next/SKILL.md:107-109).
- **Branch deletion refusal**: never deletes a branch check.py could not judge delivered — "one left standing costs a line... one deleted on a guess costs work nobody can get back" (skills/next/SKILL.md:63-66).
- **Branch-switch refusal**: only switches branches when it costs nothing (clean tree, current branch already merged); otherwise leaves audit boxes alone and says so (skills/next/SKILL.md:84-86).
- **Protected-branch push refusal**: a rejected push is accepted as an answer — keeps commit local, says so, does not route around branch protection (skills/next/SKILL.md:88-89).
- **"If the honest answer is nothing needs doing, say that and stop"** — refuses to invent a recommendation to fill the slot (skills/next/SKILL.md:285-286).
- **Rung 8 "say it once and let it go"** — refuses to re-raise a passed-over finding on the next run (skills/next/SKILL.md:215-217).

---

## CROSS-COMMAND

- **fix → blueprint**: when the cause "was never built," fix stops and says so; `blueprint` is named as the command that writes the entry (`skills/fix/SKILL.md:23-24`). Also for entry-vs-code contradiction fork ("mark, ask or record it exactly as `ship` does") — resolution belongs to blueprint/ship's shared mechanism, not fix (`skills/fix/SKILL.md:70-71`).
- **fix → reviewer**: spawns `agent-kit:reviewer` when the change touched the product, handing it the path to `rules/craft.md` explicitly so one of its five questions can be answered (`skills/fix/SKILL.md:118-121`).
- **fix ↔ existing PR**: `--pr <n>` makes fix operate directly inside an open pull request's review round — same pipeline, no new branch, no new PR (`skills/fix/SKILL.md:18,51-52,130-131`).
- **fix output → next/accept**: fix's closed run file (`step: done`, `suite`, `pr`, deferred items) is exactly the record `accept` later reads (`skills/accept/SKILL.md:33-36`) and that `next`'s `--sync`/branch-delete bookkeeping later consumes once its PR merges.
- **accept → blueprint**: Block 4 explicitly "hands over to `/agent-kit:blueprint`, narrowed to this run's blocks, which owns the prose and may put an entry back to `planned`" (`skills/accept/SKILL.md:78-81`). Closing line names blueprint "for the prose a run was not allowed to write" (`skills/accept/SKILL.md:124`).
- **accept ← ship/sprint/epic**: accept reads what those commands (and their children) left behind — `docs/runs/*.json` (batch level) and `.agent-kit/runs/*/run.json` (still-local) — never writing anything those commands produced (`skills/accept/SKILL.md:33-36`).
- **accept — reviewer/audit, not re-run**: explicitly declines to send the owner back to re-review the diff, because `agent-kit:reviewer` (per feature) and the audit's lenses (per branch) already did that pass (`skills/accept/SKILL.md:97-101`).
- **next — the universal fallback**: `rules/closing.md:75-79` — every other command, when nothing project-wide follows from its own work, names `/agent-kit:next` as the closing recommendation. It is the generic hand-off target of the whole kit.
- **next → fix**: rung 4 of the ladder (CI failing, on a PR or default branch) names `/agent-kit:fix` (`skills/next/SKILL.md:146`).
- **next → blueprint / audit / sprint / epic / ship**: rungs 6, 7, 8, 9, 10 each name one of these by the table at `skills/next/SKILL.md:141-153`, with the size-based sprint/epic/ship judgement spelled out at 155-159.
- **next → resume flags of epic/sprint/ship**: rung 2 hands back the exact resume invocation check.py itself names beside a mid-flight run — `/agent-kit:epic --resume <dir>`, `/agent-kit:sprint --resume <dir>`, `/agent-kit:ship --run <dir>`, or an errand's original prompt (`skills/next/SKILL.md:233-240`).
- **Shared preflight mechanism**: fix and next are both named, alongside ship/sprint/epic, as commands that must not start while a run of this kit is in flight (`rules/preflight.md:29-46`); accept is not on that list — nothing in accept's or preflight's text places accept under this refusal, and accept's own boundary ("changes nothing, decides nothing") is presumably why (see UNCERTAIN below).
- **Shared rules**: fix and (implicitly, via the four-fact bookkeeping) accept and next all read `rules/audit-boxes.md` — the three sessions named as allowed to tick a box are "the session that closes a batch, `next`, and `accept`" (`rules/audit-boxes.md:5-6`); `check.py --sync` is likewise shared by `blueprint --check`, `next`, and `accept` under the same fence (`skills/blueprint/SKILL.md:35`).
- **`rules/pull-requests.md`** is shared by fix (and other build commands) for the PR body shape; accept reads the PR body accept produces nothing of its own, only reads what pull-requests.md-shaped bodies from other commands wrote.
- **`rules/closing.md`** is the shared closing mechanism used verbatim by fix and accept (both cite it directly for their sign-off); next's own closing section ("What you say") is structurally identical in spirit (first line / thin spots / next command) but is written out in next's own SKILL.md rather than delegated by reference — next's "What you say" section (skills/next/SKILL.md:262-286) does not cite `rules/closing.md` by path, unlike fix and accept.

## UNCERTAIN / CONTRADICTORY

1. **Is `accept` subject to the "run in flight" preflight refusal?** `rules/preflight.md:35` lists exactly "`ship`, `fix`, `sprint`, `epic` and `next`" as the commands that must not start while another run is in flight, and explicitly says `blueprint` and `advise` are exempted "and never stop." `accept` is named in neither list. Given accept "changes nothing and decides nothing" (`skills/accept/SKILL.md:14`) it plausibly behaves like blueprint/advise, but the text never says so affirmatively — this is a gap, not a stated rule.
2. **Does `next`'s reading of `check.py --status --state` ever return a nonzero-but-actionable exit code that changes next's own control flow**, or does next just parse the printed lines regardless of exit code? SKILL.md never mentions checking the script's exit status, only "what it found" — consistent with check.py's own design (prints findings, `return 1`), but next's text treats this purely as a report to read, not a gate to branch on.
3. **fix's "entry-contradiction" fork** ("mark, ask or record it exactly as `ship` does") is explicitly deferred to `ship`'s behavior, which is outside this sector — the exact mechanism (who is asked, what gets written where) is not in fix's own file and could not be verified here without reading `ship/SKILL.md`.
4. **`next`'s closing block** does not cite `rules/closing.md` by path (unlike fix and accept, which do), even though its three-block report structure (Where it stands / What is in the way / Next) closely mirrors closing.md's "first line / thin spots / next command" shape. Whether this is intentional (next predates or deliberately diverges from the shared rule) or an oversight is not stated anywhere read.
5. **accept's block 4 "offer to settle... here"** is described as live, in-conversation work, but accept's own boundary line says "You do not write it" — meaning even if the owner answers accept's live offer, accept itself does not record the answer; it must hand the answer to blueprint. The exact mechanics of that hand-off (does accept literally invoke blueprint in the same session, or just recommend it as the closing line?) are not fully specified — SKILL.md text reads as advisory framing ("the offer hands over to `/agent-kit:blueprint`") rather than a mechanical invocation.
