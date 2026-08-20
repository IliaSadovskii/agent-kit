# Sector: blueprint

Sources read in full: `plugins/agent-kit/skills/blueprint/SKILL.md` (573 lines), `references/blocks.md` (50
lines), `references/doors.md` (62 lines). Also read: `rules/knowledge-writing.md`, `rules/channels.md`,
`rules/asking.md`, `rules/closing.md`, `rules/preflight.md`, `templates/project.yml`,
`templates/where-things-are.md`, `templates/technical_debt.md`, `templates/knowledge/product.md` (header),
`verification.yml`, `scripts/check.py` (argparse block only), `hooks/guard.py` (`holds_tree`/`verdict`),
and every "blueprint" hit across `plugins/` and `scripts/` (fix, ship, sprint, sprint/frame.md,
sprint/close.md, next, epic, advise, advise/code.md, accept, README.md, hooks/stop.py, hooks/guard.py,
scripts/runfile.py, scripts/measure.py, scripts/validate.sh, agents/reviewer.md, audit/references/*.md).

## NODES

cmd:blueprint | cmd | blueprint | the project's knowledge layer — interviews the owner and writes docs/knowledge/, project.yml, and the CLAUDE.md map | SKILL.md:1-6
phase:blueprint:preflight | phase | Always-run check | `python3 check.py . --status`, run first, unconditionally, never inferred | SKILL.md:48-54
phase:blueprint:talk | phase | The owner talks | open question, not a menu; the owner says whatever they came to say, any length/order | SKILL.md:56-76
phase:blueprint:read | phase | Read what is written on what they touched | reads only the entries/slots/parts the telling reaches, unless the telling covers the whole product | SKILL.md:77-84
phase:blueprint:compare | phase | Put the reading up before writing | one screen: new / refines / contradicts / unchanged, per entry touched | SKILL.md:86-109
phase:blueprint:debt-split | phase | Sort telling into description vs debt | 3-way test: changes what the product must do → entry; does it badly → ledger line; does not work → ledger line | SKILL.md:111-136
phase:blueprint:write | phase | Write it | writes into slots per knowledge-writing.md, commits per slot, reports names not prose | SKILL.md:138-142
phase:blueprint:gaps | phase | Then the gaps, and only then | asks only what step 5's filter allows, ordered: MVP-blocking, expensive-to-get-wrong, everything else (taken silently as assumption) | SKILL.md:144-168
gate:blueprint:contradiction | gate | Contradiction fork | owner picks: description wrong (rewrite prose) vs product wrong (not blueprint's — goes to ledger/fix) | SKILL.md:94,106-109; doors.md:44-51
gate:blueprint:gap-tier1 | gate | MVP-blocking gaps | asked as choices — MVP bounds, scenarios and endings; epic's gate refuses to start without them | SKILL.md:149-150
gate:blueprint:gap-tier2 | gate | Expensive-to-get-wrong gaps | asked as choices — stored shapes, permissions, money, outside contracts | SKILL.md:151-152
gate:blueprint:gap-tier3 | gate | Everything else | never asked — taken as a recorded `[assumed …]` decision, shown as a list at the end | SKILL.md:153-156
gate:blueprint:verification-walk | gate | Walk verification.yml with the owner | one line per kind: a command, or `no <date> <reason>`; never a bare "yes" | SKILL.md:267-303
gate:blueprint:e2e | gate | What runs the scenarios end to end | names a tool+location or states plainly there is none; written into `commands.e2e` | SKILL.md:305-317
gate:blueprint:scenario-endings | gate | Every scenario's ending read back as a choice | multiple-choice, never prose-with-yes-or-no | SKILL.md:339-342
gate:blueprint:assumed-block | gate | Resolve `[assumed …]` | yes/no on the recorded decision; write answer into entry, delete block | blocks.md:15
gate:blueprint:found-block | gate | Resolve `[found …]` | confirm library belongs, add to stack.md map, delete block | blocks.md:16
gate:blueprint:accepted-block | gate | Resolve `[accepted …]` | not re-asked — interview only the fields the record declares, write entry, delete block | blocks.md:18,29-31
gate:blueprint:frame-block | gate | Resolve `[frame …]` (only once batch merged) | read against the code, fold what held into decisions per area, delete block; what departed is the owner's to settle | blocks.md:19,24-27
gate:blueprint:older-kit | gate | Knowledge written by an older kit | pairs the two field/section lists with the owner, fills for entries that matter now, `[assumed …]` for filled-without-asking | SKILL.md:410-440
gate:blueprint:recall-followup | gate | After `--recall`, one round of choices | right as it stands / change this / rework the part | doors.md:28-30
gate:blueprint:used-it-fork | gate | After the owner has used the product | same fork as gate:blueprint:contradiction — description vs product | doors.md:41-58
gate:blueprint:branch-check | gate | Look at the branch before first commit | is it a spent (merged) feature branch? if so, branch from default instead | SKILL.md:503-504
gate:blueprint:in-flight-source | gate | Which branch to knowledge-read from while a run is in flight | always the default branch, never the run's own branch | SKILL.md:516-524
inv:blueprint:bare | invocation | `blueprint` (bare or with words) | the one door — words after the command are the telling already done; bare, ask for it | SKILL.md:33
inv:blueprint:recall | invocation | `blueprint --recall [part]` | reads the project back out loud, in the owner's language; changes nothing until asked | SKILL.md:34; doors.md:8-33
inv:blueprint:check | invocation | `blueprint --check` | mechanical audit, seconds, asks nothing; runs `check.py . --status --sync` | SKILL.md:35,559-573
script:check.py | script | check.py | the mechanical rule engine behind every `--check`/preflight call across the kit | SKILL.md:568-570
file:docs/knowledge/* | file | docs/knowledge/ slot files | one file per slot: product, actors, entities, actions, screens, integrations, scenarios, stack | SKILL.md:186-201; templates/knowledge/*
file:project.yml | file | .agent-kit/project.yml | language, commands, tests.unmet, commands.mutate, knowledge verdicts, verification, checks | SKILL.md:187-189; templates/project.yml
file:claude-md-block | file | CLAUDE.md `<!-- agent-kit:where -->` block | the map of where the project keeps its knowledge, written between markers only | SKILL.md:191-201; templates/where-things-are.md
file:technical_debt | file | docs/technical_debt.md | ledger for product-behaves-correctly-but-badly / does-not-work-at-all complaints and run-created leftover work | SKILL.md:118-136; templates/technical_debt.md
file:verification.yml | file | plugins/agent-kit/verification.yml | the kit's own catalogue of verification kinds, walked with the owner at gate:blueprint:verification-walk | SKILL.md:267-270; verification.yml:1-98
rule:knowledge-writing | rule | rules/knowledge-writing.md | shared with `advise`: template shape, project language, `state: planned` only, cascade-write-whole-or-none, hash via check.py --record, commit-per-slot | SKILL.md:13,140,199-201
rule:asking | rule | rules/asking.md | choices not prose, 2-4 options, recommendation first, batch independent questions, `gate: none` → recorded assumption | SKILL.md:37-39
rule:channels | rule | rules/channels.md | who-writes/reads/closes every durable record in the kit, incl. all five block kinds | SKILL.md:550-552
rule:closing | rule | rules/closing.md | how every command opens (one line) and closes (thin spots, next command) | SKILL.md:469-486
rule:preflight | rule | rules/preflight.md | the shared reaction table every *build* command has to the check's findings (not blueprint itself, but read to place blueprint's role as the offered fix) | referenced via check.py output; preflight.md:1-92
tpl:project.yml | tpl | templates/project.yml | source template blueprint copies/fills for `.agent-kit/project.yml` | SKILL.md:188
tpl:where-things-are | tpl | templates/where-things-are.md | source template for the CLAUDE.md block | SKILL.md:192
tpl:technical_debt | tpl | templates/technical_debt.md | copied when the project has none yet | SKILL.md:122-124
tpl:knowledge-slot | tpl | templates/knowledge/*.md | one per slot; each declares its own `fields:` and section shape | rule:knowledge-writing:15-21
ext:git-worktree | ext | git worktree | `git worktree add ../<project>-knowledge <default branch>` — blueprint's own tree while a run is in flight | SKILL.md:512-513
ext:git-diff | ext | git diff | `git diff <default>...<run-branch> -- docs/knowledge/` — read-only look at an in-flight run's knowledge writes | SKILL.md:522-524
ext:git-commit-push | ext | git commit/push | one commit per slot, pushed when there is a remote; onto checked-out branch normally, or a branch+PR while a run is in flight or default is protected | SKILL.md:492-505,530-534
hook:guard | hook | hooks/guard.py | refuses a branch-move in this checkout while a run holds it (`holds_tree`/`verdict`); this is *why* blueprint must take its own worktree | SKILL.md:513-514; guard.py:183-262
hook:stop | hook | hooks/stop.py | matches only on a registered driver-child session name, so leaves blueprint sessions untouched | stop.py:12-17
script:runfile.py | script | scripts/runfile.py | classifies `blueprint` as command-type `errand` (vs feature/batch/epic) | runfile.py:52-55
script:measure.py | script | scripts/measure.py | regex that recognizes `/agent-kit:blueprint` invocations when measuring sessions | measure.py:45-46
cmd:fix | cmd | fix | writes the entry when a "fix" turns out to be an undescribed feature; never rewrites an entry itself | fix/SKILL.md:24,146
cmd:ship | cmd | ship | builds against blueprint's entries; never re-decides what blueprint settled; leaves `[assumed]`, `[stale]`, `[found]` blocks and debt/unmet-test lines for blueprint | ship/SKILL.md:20-23,264-271,462
cmd:sprint | cmd | sprint | asks nothing the blueprint already answers; on a marked-test/entry contradiction, hands the "entry is wrong" branch to blueprint | sprint/SKILL.md:61,122-125
cmd:epic | cmd | epic | refuses to start without MVP bounds/scenarios/commands.run/commands.test — offers blueprint; branches from the branch a blueprint run left knowledge on, not from default | epic/SKILL.md:44-45,60,159,258-262
cmd:next | cmd | next | ranks blueprint's raw check data into a recommendation (rung 6,7,9); recommends blueprint for open blocks, thin knowledge, empty repo | next/SKILL.md:148-149,179-202,244-249
cmd:advise | cmd | advise | shares rules/knowledge-writing.md with blueprint; writes only what the owner answered in front of it, via `[accepted …]` blocks that blueprint later finishes; commits differently (PR) than blueprint (no PR) | SKILL.md:11-13,410-440; advise/SKILL.md:60,257-271
cmd:accept | cmd | accept | hands unanswered blocks over to blueprint narrowed to its run's blocks; changes nothing itself | accept/SKILL.md:77-82,122-124
agent:reviewer | agent | agent-kit:reviewer | reads the blueprint entries named in a run file, and stack.md, to judge a diff | reviewer.md:16
session:owner-worktree | session | Owner's blueprint worktree session | the tree blueprint stands up for itself while a run is in flight (`../<project>-knowledge`) | SKILL.md:512-513

## EDGES

inv:blueprint:bare -> phase:blueprint:preflight | invokes | always, before anything else | SKILL.md:48-54
phase:blueprint:preflight -> script:check.py | invokes | `python3 check.py . --status` | SKILL.md:53
phase:blueprint:preflight -> phase:blueprint:talk | returns-to | after the check prints, unconditionally proceeds to step 1 | SKILL.md:41-46,56
phase:blueprint:talk -> phase:blueprint:read | hands-off | telling is captured, narrowed to what it touches (or the whole knowledge if the telling covers the whole product) | SKILL.md:77-84
phase:blueprint:read -> phase:blueprint:compare | hands-off | reading complete, comparison is written up per entry touched | SKILL.md:86-101
phase:blueprint:compare -> gate:blueprint:contradiction | blocks | only when a row is "contradicts" | SKILL.md:94,103-109
gate:blueprint:contradiction -> phase:blueprint:write | returns-to | owner picks "description wrong" → prose rewritten | doors.md:46
gate:blueprint:contradiction -> file:technical_debt | writes | owner picks "product wrong" → ledger line, not blueprint's to fix | doors.md:47
phase:blueprint:compare -> phase:blueprint:debt-split | hands-off | non-contradiction rows are stated and written, not asked | SKILL.md:103-104,111-136
phase:blueprint:debt-split -> file:technical_debt | writes | "does it badly" or "does not work at all" | SKILL.md:126-136
phase:blueprint:debt-split -> phase:blueprint:write | hands-off | "changes what the product must do" rows | SKILL.md:130,138
phase:blueprint:write -> file:docs/knowledge/* | writes | per rule:knowledge-writing, one commit per slot as settled | SKILL.md:140-142; knowledge-writing.md:59-62
phase:blueprint:write -> phase:blueprint:gaps | hands-off | after writing, "then the gaps, and only then" | SKILL.md:144-146
phase:blueprint:gaps -> gate:blueprint:gap-tier1 | blocks | MVP bounds/scenarios/endings missing | SKILL.md:149-150
phase:blueprint:gaps -> gate:blueprint:gap-tier2 | blocks | stored shapes/permissions/money/outside contracts missing | SKILL.md:151-152
phase:blueprint:gaps -> gate:blueprint:gap-tier3 | refuses | (refuses to *ask*) everything else is taken as an assumption, listed at the end | SKILL.md:153-156
phase:blueprint:gaps -> gate:blueprint:verification-walk | blocks | during the stack/application-type part of the finished-description list | SKILL.md:267-303
gate:blueprint:verification-walk -> file:project.yml | writes | one line per kind under `verification:` | SKILL.md:270-276
gate:blueprint:verification-walk -> gate:blueprint:e2e | hands-off | asked in the same breath, but this one is never derived/drafted | SKILL.md:305-311
gate:blueprint:e2e -> file:project.yml | writes | `commands.e2e` field | SKILL.md:313-317
phase:blueprint:gaps -> gate:blueprint:scenario-endings | blocks | across-parts scenarios step | SKILL.md:339-342
gate:blueprint:assumed-block -> file:docs/knowledge/* | writes | answer written into entry, block deleted | blocks.md:15
gate:blueprint:found-block -> file:docs/knowledge/* | writes | stack.md library map updated, block deleted | blocks.md:16
gate:blueprint:accepted-block -> file:docs/knowledge/* | writes | remaining declared fields interviewed and written, block deleted | blocks.md:18
gate:blueprint:frame-block -> file:docs/knowledge/* | writes | folded into stack.md decisions per area, block deleted — ONLY once that batch's PR has merged | blocks.md:19,24-27
gate:blueprint:older-kit -> file:docs/knowledge/* | writes | fills the fields that matter now; rest left outstanding, `[assumed …]` where filled unasked | SKILL.md:427-433
cmd:blueprint -> script:check.py | invokes | `--check` runs `python3 check.py . --status --sync` | SKILL.md:35
inv:blueprint:check -> script:check.py | invokes | mechanical only, exit code 1 when findings, silent when clean | SKILL.md:563-566
script:check.py -> file:project.yml | writes | `--sync` moves an entry's state once its PR has merged — the one thing `--check` writes, never as a preflight | SKILL.md:35
inv:blueprint:recall -> file:docs/knowledge/* | reads | retells a part's content out loud, never shows the file | doors.md:9-26
inv:blueprint:recall -> gate:blueprint:recall-followup | hands-off | after the retelling | doors.md:28
gate:blueprint:recall-followup -> phase:blueprint:talk | hands-off | "change this"/"rework the part" become an ordinary interview on that part | doors.md:29-30
gate:blueprint:used-it-fork -> phase:blueprint:write | returns-to | description-wrong branch: rewrite prose | doors.md:46
gate:blueprint:used-it-fork -> file:technical_debt | writes | product-wrong branch: ledger line marked `owner`, or entry reverted to `state: planned` if never built | doors.md:47
cmd:blueprint -> ext:git-worktree | invokes | while a run of the kit is in flight, blueprint takes its own tree instead of the shared checkout | SKILL.md:512-513
hook:guard -> cmd:blueprint | refuses | `holds_tree`/`verdict` in guard.py refuses a branch-switch of the shared checkout to any unregistered session including blueprint's | guard.py:183-262; SKILL.md:513-514
cmd:blueprint -> ext:git-diff | invokes | reads (never builds on) the in-flight run's own branch for docs/knowledge/ changes | SKILL.md:516-524
gate:blueprint:branch-check -> ext:git-commit-push | invokes | decides which branch to commit onto before the first commit | SKILL.md:503-505
phase:blueprint:write -> ext:git-commit-push | invokes | normal path: commits land on the checked-out branch, no PR of its own | SKILL.md:492-505
phase:blueprint:write -> gate:blueprint:branch-check | blocks | fallback to branch+PR only if default branch is protected, or run in flight | SKILL.md:501,530-534
cmd:blueprint -> file:claude-md-block | writes | between `<!-- agent-kit:where -->` markers, refreshed when layout changes | SKILL.md:191-201; where-things-are.md
cmd:blueprint -> tpl:project.yml | reads | template for `.agent-kit/project.yml` | SKILL.md:188
cmd:blueprint -> tpl:where-things-are | reads | template for the CLAUDE.md block | SKILL.md:192
cmd:blueprint -> tpl:technical_debt | reads | copied only if the project has no ledger yet | SKILL.md:122-124
cmd:blueprint -> tpl:knowledge-slot | reads | per rule:knowledge-writing, write from the template not from memory | knowledge-writing.md:19-21
cmd:blueprint -> file:verification.yml | reads | walked top to bottom with the owner | SKILL.md:267-270
cmd:blueprint -> rule:knowledge-writing | delegates | shape, language, state, hashing, commit rules | SKILL.md:13,140,199-201
cmd:blueprint -> rule:asking | delegates | every question format | SKILL.md:37-39
cmd:blueprint -> rule:channels | delegates | who may close which block | SKILL.md:550-552
cmd:blueprint -> rule:closing | delegates | opening/closing lines of the session | SKILL.md:469-486
cmd:fix -> cmd:blueprint | hands-off | when a "fix" turns out to be an undescribed feature, stop and point to blueprint | fix/SKILL.md:24
cmd:ship -> cmd:blueprint | hands-off | `[assumed]`/`[stale]`/`[found]` blocks left for blueprint to close; entry prose never rewritten by ship | ship/SKILL.md:264,269-270,462
cmd:sprint -> cmd:blueprint | hands-off | on a test/entry contradiction, "entry is wrong" branch hands wording to blueprint | sprint/SKILL.md:122-125
cmd:sprint -> file:docs/knowledge/* | writes | closing session applies `[stale …]` blocks left by children, sets `state: building (pr: n)`, but only within the two named limits, else block stays for blueprint | sprint/close.md:185-219
cmd:epic -> cmd:blueprint | hands-off | refuses to start on missing MVP bounds/scenarios/commands; also offers before/after run for thin `walked`/`derived` parts | epic/SKILL.md:44-45,60,159
cmd:epic -> file:docs/knowledge/* | reads | branches from the branch a blueprint run left knowledge on (not default) | epic/SKILL.md:258-262
cmd:next -> cmd:blueprint | hands-off | rungs 6,7,9,10 and the three overrides (no docs/knowledge/, empty repo) recommend blueprint | next/SKILL.md:148-149,179-202,244-249
cmd:advise -> file:docs/knowledge/* | writes | `[accepted …]` blocks only, via rule:knowledge-writing, committed with a PR (unlike blueprint) | SKILL.md:11-13; advise/SKILL.md:257-271
cmd:advise -> cmd:blueprint | hands-off | `[accepted …]` blocks finished by blueprint; "nothing written at all" case names blueprint | advise/SKILL.md:60,269-271
cmd:accept -> cmd:blueprint | hands-off | hands unanswered run blocks to blueprint narrowed to that run | accept/SKILL.md:77-82
agent:reviewer -> file:docs/knowledge/* | reads | the entries named in the run file, plus stack.md, to judge a diff | reviewer.md:16
hook:stop -> cmd:blueprint | hands-off | matches only on registered driver-child sessions, so blueprint sessions are left untouched by construction | stop.py:12-17
script:runfile.py -> cmd:blueprint | reads | classifies it as command type `errand` | runfile.py:52-55
script:measure.py -> cmd:blueprint | reads | regex recognizes `/agent-kit:blueprint` invocations for session accounting | measure.py:45-46
cmd:blueprint -> file:project.yml | writes | `.agent-kit/project.yml` — no build command may edit it | channels.md:48
cmd:blueprint -> file:technical_debt | writes | debt lines from step 3's fork and from doors.md's used-it fork | SKILL.md:118-136; doors.md:47

## IO TABLE

cmd:blueprint | docs/knowledge/*.md (existing entries touched by the telling); .agent-kit/project.yml; docs/technical_debt.md; plugins/agent-kit/verification.yml; templates/project.yml, templates/where-things-are.md, templates/technical_debt.md, templates/knowledge/*.md; owner's own documents referenced via `source:`; project's CLAUDE.md | docs/knowledge/*.md; .agent-kit/project.yml; docs/technical_debt.md (append/delete lines); CLAUDE.md between `<!-- agent-kit:where -->` markers
inv:blueprint:check / script:check.py | docs/knowledge/*.md, .agent-kit/project.yml, run files under .agent-kit/runs/, templates/ (for shape comparison) | .agent-kit/project.yml → an entry's `state:` line only, via `--sync`, once its PR has merged
inv:blueprint:recall | docs/knowledge/*.md | nothing (unless it hands off into the ordinary interview)

## OWNER GATES

- **gate:blueprint:contradiction** (step 3) — triggers when the telling contradicts a recorded entry. Options: description is wrong (rewrite the prose — blueprint's only), or the product is wrong (not blueprint's, goes to the ledger). Blocks until answered; this is the one contradiction always asked in step 3, everything else in step 3 is stated not asked. SKILL.md:94,103-109
- **gate:blueprint:gap-tier1** (step 5) — MVP bounds, scenarios, scenario endings. Asked as choices because `epic`'s gate refuses to start without them. Blocks. SKILL.md:149-150
- **gate:blueprint:gap-tier2** (step 5) — stored shapes, permissions, money, an outside contract. Asked as choices because wrong here is expensive. Blocks. SKILL.md:151-152
- **gate:blueprint:gap-tier3** (step 5) — everything else. Explicitly *not* asked — taken as a decision, recorded as `[assumed …]`, listed at the end as "here is what I decided for you." Does not block. SKILL.md:153-156
- **gate:blueprint:verification-walk** — walked top to bottom against `verification.yml`, per kind: propose what's already there, cost/benefit, recommendation; owner picks. Every answer must be a command or a dated refusal, never a bare "yes". Blocks (interview, not fire-and-forget). SKILL.md:267-303
- **gate:blueprint:e2e** — "what runs the scenarios end to end." Never derived/drafted, always asked — because `epic` stops on "every scenario passes" and a guard hook keys off `commands.e2e`. Blocks. SKILL.md:305-317
- **gate:blueprint:scenario-endings** — every scenario's ending read back as multiple choice, never prose-with-a-yes-or-no ("A wall of text with a yes-or-no under it gets a yes"). Blocks. SKILL.md:339-342
- **gate:blueprint:assumed-block / found-block / accepted-block / frame-block / older-kit** — resolving the five block kinds and the older-kit field/section gaps; see NODES/EDGES above and blocks.md.
- **`--recall` follow-up** — one round: right as it stands / change this / rework the part. Blocks only if "change" or "rework" picked, else ends the session. doors.md:28-30
- **used-it fork** (doors.md) — same shape as gate:blueprint:contradiction, triggered by "what did not match after using it." Blocks per complaint.
- **What to never ask** (filter, SKILL.md:347-397): never asks how it's stored, which request/index/schema, protocols/headers/table shape, how it's layered/which pattern/where logic lives. Always asks: what the person sees and in what order, what happens when it fails, what's kept about them, **who may not** (always asked, unlike "who may" which the code can show), what costs money.

## REFUSALS AND EXITS

- **"When the check found nothing and the owner brought nothing"** — say so in one line and stop; name `/agent-kit:next` or `/agent-kit:epic` (if entries are `planned`) instead. "An interview invented to fill the silence is the one thing an owner cannot check." SKILL.md:166-168
- **Scope refusal**: "What this command does not do" — never builds, starts, or instruments the app; never writes scripts or installs dependencies; never produces quality/audit reports; never decides what gets worked on first. A three-hour audit started from an owner's doubt-question is still refused — answer from knowledge+code, name what can't be answered, offer the right command. SKILL.md:170-179
- **`holds_tree` / guard.py refusal**: while a run of the kit holds this checkout, guard.py refuses any branch-switch by a session it did not register — including a `blueprint` session — forcing the git-worktree-of-its-own path rather than blocking blueprint outright. guard.py:183-262; SKILL.md:513-514
- **Spent feature branch**: on a branch whose PR already merged, blueprint says so and branches from default instead, rather than committing onto a dead branch. SKILL.md:503-504
- **Protected default branch**: only case where blueprint falls back to a branch + pull request of its own (and says so). SKILL.md:500-501
- **`[frame …]` block**: not deletable/foldable until its batch has actually merged — premature closing costs every later run the reason its code looks the way it does. blocks.md:19,24-27; gate:blueprint:frame-block
- **`[accepted …]` block**: never re-opened/re-asked once written — asking again "is how a list stops being read." blocks.md:29-31

## PROMISES MADE TO OTHER PARTS

What blueprint guarantees:
- It is the **only** writer of entry prose (`docs/knowledge/*.md`) and of `.agent-kit/project.yml` — no build command may write either (channels.md:44,48). Build commands may only move an entry's `state:` line and leave blocks.
- It is the **only** decider of what an entry *requires* — "one decider, one trigger" (SKILL.md:15-16).
- It is the **only** closer of `[found …]` and (jointly with a build command / batch-closer under channels.md) of `[assumed …]` and `[stale …]`; sole closer of `[frame …]` and `[accepted …]`. blocks.md; channels.md rows 29-33.
- `commands.e2e` and `verification.yml` answers it writes are load-bearing: `epic`'s gate refuses to start without `commands.e2e`/MVP bounds/scenarios; the guard hook's `verdict()` reads `e2e` to decide whether a ship command is illegally re-running the whole product (guard.py `verdict`). check.py --state surfaces stale/missing verification answers to every gate.
- The CLAUDE.md `<!-- agent-kit:where -->` block is the *only* thing this kit ever writes into that file — a promise other commands and outside agents rely on to find the knowledge without a map of their own. where-things-are.md:1-9

What blueprint relies on others to have done:
- Relies on `ship`/`fix`/`sprint`/`epic` to leave `[assumed …]`, `[stale …]`, `[found …]` blocks rather than silently deciding — its own "second run costs minutes rather than hours" claim depends on this. blocks.md:42-43
- Relies on the driver/guard hook (`hooks/guard.py`, `hooks/stop.py`) to keep the shared checkout safe from a live run while blueprint edits knowledge in its own worktree.
- Relies on `check.py` to be the single source of mechanical truth (states, fields, references, orphans, hashes, block kinds) so blueprint's own judgment is reserved for what a program cannot decide (pairing old/new field lists, judging contradictions). SKILL.md:417-425,568-573
- Relies on `sprint`'s closing session to fill `[frame …]`'s `pr: ?` with the real PR number before blueprint can ever fold it in. sprint/close.md:49-51,185-219

## UNCERTAIN / CONTRADICTORY

- **Exact wording of the `--check` command differs between two spots in the same file.** The invocation table (SKILL.md:35) says `--check` runs `python3 check.py . --status --sync`; the closing section "What `--check` does" (SKILL.md:559-566) describes the same behavior only in prose without repeating the flags. Not a contradiction in substance, but the `--sync` flag's exact interaction with `--status` (are they always paired, or does `--sync` only apply "not as a preflight") is stated once as a combined invocation and once as a rule about when `--sync` may run — I did not find the flags spelled out separately in `check.py`'s own argparse help beyond `--sync`'s one-line help text, so I cannot independently confirm whether `--check` ever calls `--sync` without `--status` or vice versa.
- **Who exactly may close `[assumed …]` and `[stale …]` blocks** is stated in two places with slightly different phrasing: `blocks.md` says "ask it as yes-or-no... write the answer... delete the block" (implying blueprint), while `channels.md`'s table row says closer is "`blueprint`; **or a build command with the owner present**, writing down the answer they just gave" — i.e. `channels.md` is more permissive than `blocks.md`'s own text reads in isolation. `blocks.md:5-8` explicitly defers to `channels.md` as the authority, so this is likely intentional layering rather than a real contradiction, but a reader of `blocks.md` alone would come away with a narrower picture than `channels.md` gives.
- **Whether `blueprint --check`'s exit code changes on "knowledge written by an older kit" or "unmet promises."** SKILL.md:564-566 explicitly carves these two out as "listed whenever they exist and change no code" — but the same file elsewhere (SKILL.md:439-440) repeats "it changes no exit code" only for the older-kit case, not restating it for unmet promises in that spot. Read together they agree, but it is stated once compactly and I note it because a careless reading of only SKILL.md:439-440 might assume unmet promises do affect exit code.
- **Where exactly the "second exception to asking.md" (owner-doing-the-talking) ends and ordinary choice-asking resumes** is a matter of judgment call each run — SKILL.md:37-39 states step 1 (the telling) is the one exception, but step 5's tier-1/tier-2 gaps and the verification walk are clearly choice-based, while doors.md's `--recall` follow-up round is also choice-based. The document is consistent on this, but a reader could conflate "the owner talks" (unstructured) with the subsequent gap interview (structured) since both happen inside one session — the SKILL.md text is careful to separate them but it is dense.
- **The precise scope of "a telling that covers the whole product does mean reading the whole thing"** (SKILL.md:82-84) versus step 2's normal narrow read (SKILL.md:77-81) leaves undefined exactly how a session judges "covers the whole product" versus "one part in detail" when the owner's language is ambiguous — the document does not give a mechanical test for this boundary, only two illustrative extremes.
