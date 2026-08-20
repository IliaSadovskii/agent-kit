# Merged graph

Sources: 11 sector reports (`blueprint.md`, `ship.md`, `sprint.md`, `epic.md`, `fix-accept-next.md`,
`audit-advise.md`, `rules.md`, `hooks-runfile.md`, `orchestrate.md`, `check.md`, `data-and-scripts.md`).
`seams.md` never appeared — no twelfth sector was merged.

Sector abbreviations used in the `sources` column:
`BP` blueprint · `SH` ship · `SP` sprint · `EP` epic · `FAN` fix/accept/next · `AA` audit/advise ·
`RU` rules · `HR` hooks+runfile · `OR` orchestrate · `CH` check.py · `DS` data-and-scripts.

Mechanism vocabulary normalized to: `invokes`, `reads`, `writes`, `spawns`, `delegates`,
`hands-off`, `blocks`, `refuses`, `returns-to`, `loops-to`, `becomes`, `imports`, `closes`.

---

## CANONICAL NODES BY LAYER

### (a) Commands and invocations — 20

```
cmd:blueprint          | cmd | /agent-kit:blueprint | the knowledge layer: interviews the owner, writes docs/knowledge/, project.yml and the CLAUDE.md map | BP SH SP EP FAN AA CH DS
cmd:ship               | cmd | /agent-kit:ship [key|task] | build one feature end to end: design, build, verify, review, PR | SH BP SP EP FAN OR CH DS
cmd:fix                | cmd | /agent-kit:fix | small cheap repair: cause, failing test, minimal change, deliver | FAN BP SH CH DS
cmd:sprint             | cmd | /agent-kit:sprint | four-roled batch command: brief, frame child, closing child, window | SP BP SH EP FAN OR CH DS
cmd:epic               | cmd | /agent-kit:epic | whole-scope run: gate once, then batches until built, audited and proved, as one PR | EP BP SH SP AA OR CH DS
cmd:next               | cmd | /agent-kit:next | cold-start orientation: read state, name one next command, start nothing | FAN BP SP AA CH DS
cmd:accept             | cmd | /agent-kit:accept [pr#] | read a finished run's PR and run files, say mergeable-or-not and what needs hands | FAN BP SP AA CH DS
cmd:audit              | cmd | /agent-kit:audit [lens] [area] | read code against docs/knowledge/, write a work list; change nothing | AA EP FAN CH
cmd:advise             | cmd | /agent-kit:advise [lens] | propose where product/code/money is weak; owner decides in one round; write what they accept | AA BP RU CH DS
inv:blueprint:bare     | invocation | `blueprint` (bare or with words) | the one door — words after the command are the telling already done | BP
inv:blueprint:recall   | invocation | `blueprint --recall [part]` | reads the project back out loud; changes nothing until asked | BP
inv:blueprint:check    | invocation | `blueprint --check` | mechanical audit in seconds; runs check.py . --status --sync | BP
inv:ship:run           | invocation | `/agent-kit:ship --run <dir>` | the driver's default child prompt; also a resume | SH SP OR CH
inv:sprint:frame       | invocation | `/agent-kit:sprint --frame <dir>` | the frame child; only ever typed by the driver | SP OR
inv:sprint:close       | invocation | `/agent-kit:sprint --close <dir>` | the batch closing session; only ever typed by the driver | SP EP OR
inv:sprint:window      | invocation | `/agent-kit:sprint --window <dir>` | a fresh session standing beside a running batch | SP RU
inv:sprint:resume      | invocation | `/agent-kit:sprint --resume <dir>` | restart the driver over the same run directory | SP FAN
inv:epic:advance       | invocation | `/agent-kit:epic --advance <dir>` | started by the driver's hand-back: decide what follows, start it, stop | EP OR
inv:epic:resume        | invocation | `/agent-kit:epic --resume <dir>` | started by hand when a run stalled | EP FAN
inv:audit:run          | invocation | `/agent-kit:audit <lens> --run <dir>` | one lens as a batch child, no owner present | AA EP
```

### (b) Phases, gates and lenses inside commands — 105

**blueprint (23)**
```
phase:blueprint:preflight     | phase | Always-run check | check.py . --status, first, unconditionally | BP
phase:blueprint:talk          | phase | The owner talks | open question, not a menu | BP
phase:blueprint:read          | phase | Read what is written | only the entries the telling reaches | BP
phase:blueprint:compare       | phase | Put the reading up | new / refines / contradicts / unchanged | BP
phase:blueprint:debt-split    | phase | Description vs debt | 3-way test routes to entry or ledger | BP
phase:blueprint:write         | phase | Write it | into slots per knowledge-writing, commit per slot | BP
phase:blueprint:gaps          | phase | Then the gaps, and only then | tier 1/2 asked, tier 3 assumed | BP
gate:blueprint:contradiction  | gate | Contradiction fork | description wrong vs product wrong | BP
gate:blueprint:gap-tier1      | gate | MVP-blocking gaps | bounds, scenarios, endings — asked as choices | BP
gate:blueprint:gap-tier2      | gate | Expensive-to-get-wrong gaps | stored shapes, permissions, money, contracts | BP
gate:blueprint:gap-tier3      | gate | Everything else | never asked; recorded as [assumed …] | BP
gate:blueprint:verification-walk | gate | Walk verification.yml with the owner | a command, or `no <date> <reason>` | BP
gate:blueprint:e2e            | gate | What runs the scenarios end to end | never derived; written into commands.e2e | BP
gate:blueprint:scenario-endings | gate | Every ending read back as a choice | never prose-with-a-yes-or-no | BP
gate:blueprint:assumed-block  | gate | Resolve [assumed …] | yes/no, write into entry, delete block | BP
gate:blueprint:found-block    | gate | Resolve [found …] | confirm library, add to stack.md map, delete | BP
gate:blueprint:accepted-block | gate | Resolve [accepted …] | never re-asked; interview only declared fields | BP
gate:blueprint:frame-block    | gate | Resolve [frame …] | only once the batch's PR merged | BP
gate:blueprint:older-kit      | gate | Knowledge written by an older kit | pair the field lists with the owner | BP
gate:blueprint:recall-followup| gate | After --recall, one round | right / change this / rework the part | BP
gate:blueprint:used-it-fork   | gate | After the owner has used the product | description vs product | BP
gate:blueprint:branch-check   | gate | Look at the branch before first commit | spent feature branch → branch from default | BP
gate:blueprint:in-flight-source | gate | Which branch to read knowledge from | always the default branch | BP
```

**ship (5)**
```
gate:ship:owner-present   | gate | gate: owner vs gate: none | wait on a question, or record an assumption | SH
gate:ship:expensive-fork  | gate | "is this fork expensive" | asked with owner, recorded headless | SH
gate:ship:entry-vs-code   | gate | entry promises X, code does Y | unmet-marked test always; ask only with owner | SH
gate:ship:deliver-mode    | gate | deliver: "pr" vs "branch" | branch mode stops after Deliver step 3 | SH
gate:ship:touched-product | gate | git diff --name-only before Review | tests/fixtures/lock/docs-only skips the reviewer | SH
```

**sprint (11)**
```
phase:sprint:brief-knowledge  | phase | Knowledge check | check.py --status before asking anything | SP
phase:sprint:brief-compose    | phase | Compose the batch | ask only forking questions, one screen | SP
phase:sprint:brief-no-theme   | phase | With no theme | owed-vs-missing piles, then candidates | SP
phase:sprint:brief-write-runs | phase | Write run files | batch, frame, feature run.jsons; check each | SP
phase:sprint:brief-start-driver | phase | Start the driver | nohup orchestrate.py <dir>/ >> driver.out | SP
phase:sprint:brief-become-window| phase | Then stay, as the window | one line, then stop and wait | SP
gate:sprint:tmux-check        | gate | tmux installed? | `command -v tmux`; missing → offer ship per feature | SP
gate:sprint:pile-first        | gate | Which pile first | owed vs missing; skipped if one is empty | SP
gate:sprint:candidates        | gate | Which candidates | screen of candidates with cost | SP
gate:sprint:composition-qs    | gate | Composition/order/fork/assumption/reachability | up to 5 forking questions | SP
gate:sprint:promise-side      | gate | Which side is wrong | product or entry, per unkept promise | SP
```

**epic (17)**
```
phase:epic:gate      | phase | Gate phase | step:"gate" — the only owner conversation of the run | EP
phase:epic:building  | phase | Building phase | step:"building" — batches run one after another | EP
phase:epic:auditing  | phase | Auditing phase | step:"auditing" — up to 3 waves of lens audits + fix batches | EP
phase:epic:proving   | phase | Proving phase | step:"proving" — scenario e2e coverage, epic verification kinds, fresh-worktree boot | EP
phase:epic:done      | phase | Done | step:"done" written last, after the PR summary | EP
gate:epic:tmux-check | gate | tmux precondition | without it the driver cannot give a feature a session | EP
gate:epic:epic-check | gate | check.py --epic | fatal-or-silent: bounds, scenarios, run/test, verification | EP
gate:epic:status-state | gate | check.py --status --state | preflight counts, scenarios, audits | EP
gate:epic:derive-inlist | gate | Derive the in-list | scope choice → entry keys not yet built | EP
gate:epic:entries-settle | gate | Settle open blocks | check.py --entries; owner settles the expensive ones | EP
gate:epic:order-batches | gate | Order and batch | ~5-entry batches, one topic; assign each scenario's e2e test | EP
gate:epic:price      | gate | Price in hours | from docs/runs/*.json spent, else ~1h/feature | EP
gate:epic:harness    | gate | Say what proves it | name the e2e harness, or say none exists and what it costs | EP
gate:epic:parts-seen | gate | Parts seen by owner | N recorded, M walked, K derived; walk unread parts live | EP
gate:epic:invented-record | gate | Record what the conversation invents | assumption or new planned entry, before the run | EP
gate:epic:rank-questions | gate | Rank questions and blocks | ~5 most consequential up as choices | EP
gate:epic:screen     | gate | The one screen | scope, batches, price, audit cost, unread parts, this-or-narrower | EP
```

**fix (12)**
```
phase:fix-invoke  | phase | Invocation | owner's words / red output / --pr <n> | FAN
phase:fix-branch  | phase | Branch and run file setup | clean tree, branch, run.json created | FAN
phase:fix-cause   | phase | Find the cause | read to "this line, this condition"; name the missing test | FAN
phase:fix-prove   | phase | Prove it, then change it | failing test first, at an existing seam | FAN
phase:fix-change  | phase | Minimal change | fix only the cause; neighbours go to the ledger | FAN
phase:fix-verify  | phase | Verify | suite, mutation/manual-undo, --owed kinds, app exercise | FAN
phase:fix-deliver | phase | Deliver | review, PR, close run file, check --run, closing | FAN
gate:fix:not-a-fix | gate | "When this is not a fix" | new behaviour / product decision / rewrite ends the run | FAN
gate:fix:entry-contradiction | gate | entry vs code | the expensive fork shared with ship | FAN
gate:fix:cause-not-found | gate | cause won't come out | stop ~1h in; report ruled-out, suspicion, next step | FAN
gate:fix:flake-exception | gate | failure a test cannot hold | say so in the run file, name the alternative proof | FAN
gate:fix:no-refactor | gate | "What this command does not do" | no refactor, no entry rewrite, no merge | FAN
```

**accept (8)**
```
phase:accept-verdict   | phase | Block 1: verdict | mergeable now / after N steps / not mergeable | FAN
phase:accept-manual    | phase | Block 2: manual actions | numbered, ordered, proofs run first | FAN
phase:accept-waiting   | phase | Block 3: waiting on a decision | every timed-out waiting_on, each with a recommendation | FAN
phase:accept-decisions | phase | Block 4: decisions taken without them | expensive named, rest counted; offer to settle now | FAN
phase:accept-unproven  | phase | Block 5: what is not proven | unmet, no-e2e, never-exercised, stand-in seams | FAN
phase:accept-worktree  | phase | Block 6: how to look at it | worktree command, free port, first scenario | FAN
gate:accept:no-diff-read | gate | "You do not read the diff" | reviewer and audit already covered it | FAN
gate:accept:no-write   | gate | "does not fix, merge, answer, open" | two permitted writes only | FAN
```

**next (8)**
```
phase:next-bookkeeping | phase | Four bookkeeping writes | manual-done, audit box, --sync, delivered-branch delete | FAN
phase:next-ladder      | phase | The ladder | 11 ranked rungs, first that fires wins | FAN
phase:next-report      | phase | What you say | Where it stands / What is in the way / Next | FAN
gate:next:run-in-flight| gate | A run of this kit in flight here | next must not start; the four writes still allowed | FAN
gate:next:no-offline   | gate | never --offline | it would blind rungs 3-5 | FAN
gate:next:override-no-knowledge | gate | override: no docs/knowledge/ at all | forces blueprint | FAN
gate:next:override-empty-repo   | gate | override: empty repository | forces blueprint then epic | FAN
gate:next:override-mvp-unfinished | gate | override: MVP bounds not reached | swaps rungs 9/10 | FAN
```

**audit and advise (10 phases/gates)**
```
phase:audit.dispatch  | phase | invocation dispatch | typed args → lens+area, or stop and ask | AA
phase:audit.baseline  | phase | baseline check | two comparisons, once per full run; writes docs/audits/baseline.md | AA
phase:audit.lens      | phase | one lens's walk | the 7-step shape every lens follows | AA
gate:audit.clarify    | gate | clarify before starting | first word not a lens → print lenses, ask the area | AA
phase:advise.preflight| phase | preflight check | check.py --status once; findings are not a reason to stop | AA
phase:advise.dispatch | phase | invocation dispatch | typed args → lens (+area), or clarify | AA
phase:advise.closehalf| phase | close half | complete list, every row covered/gaps/unjudged, "from the files" | AA
phase:advise.widehalf | phase | wide half | domain judgement + research; ends in "considered and rejected" | AA
phase:advise.closing  | phase | closing round | rows put to the owner per asking.md; three answers per row | AA
gate:advise.clarify   | gate | clarify before starting | print the three lenses, ask the one clarification | AA
```

**shared gates from the rules (2)**
```
gate:run-in-flight | gate | run already in flight | preflight's hard stop when another session holds the checkout | RU FAN SH SP EP
gate:piled-up      | gate | say what has piled up | once-per-run pile-of-decisions gate, person-typed commands only | RU
```

**lenses (9)**
```
lens:tests       | lens | audit tests | walks every entry in scope; per-line coverage citations | AA
lens:deps        | lens | audit deps | direct dependencies via ecosystem tooling | AA
lens:scenarios   | lens | audit scenarios | every scenario in scenarios.md, chaining + tracing | AA
lens:security    | lens | audit security | risky actions: the product's "must never" + generic classes | AA
lens:performance | lens | audit performance | every action against a stack-derived anti-pattern catalogue | AA
lens:conventions | lens | audit conventions | every rule in stack.md | AA
lens:product     | lens | advise product | scenarios+actions failure walk; domain, adjacent audience, what to remove | AA
lens:code        | lens | advise code | actions at volume vs stack.md+product.md numbers; data-loss paths | AA
lens:money       | lens | advise money | what costs without reason, what could charge; market pricing | AA
```

### (c) Sessions, agents and the driver — 16

```
session:driver          | session | the driver process | orchestrate.py, detached, drives one batch's children serially | SP EP RU OR HR
session:brief           | session | brief session | composes the batch with the owner, then becomes the window | SP
session:window          | session | control window | answers the owner, relays [driver] news, writes control | SP RU OR EP
session:frame           | session | frame child session | first child of a batch of ≥3, started with --frame | SP EP
session:feature-child   | session | a ship/fix child session | one claude session building one feature | SH SP OR HR
session:batch-close     | session | batch-closing session | writes the batch branch, the one PR, docs/runs record | SP EP OR
session:epic-gate       | session | the epic gate session | runs bare /agent-kit:epic; ends after starting batch 1 | EP
session:advance         | session | <epic>-advance session | decides what follows a closed batch, starts it, ends | EP OR
session:epic-resume     | session | --resume session | started by hand when a run stalled | EP
session:audit-run       | session | a running audit invocation | person-typed (full or single lens) or a batch child | AA EP
session:advise-round    | session | the advise closing-round session | branches docs/advise-<date>, one commit per item, one PR | AA
session:owner           | session | the owner's own terminal | never matched by either hook, by construction | HR
session:blueprint-worktree | session | blueprint's own worktree session | ../<project>-knowledge while a run is in flight | BP
session:registered-epic | session | an epic's registered session | gate or hand-back; stop.py never blocks it mid-step, closes it once terminal | HR EP
agent:reviewer          | agent | agent-kit:reviewer | read-only diff review against the entry, run file, craft.md, stack.md | SH BP FAN RU
agent:advise-lens-subagent | agent | per-lens subagent for advise | inferred by analogy with audit; not stated anywhere | AA
```

### (d) Programs — 32

```
script:check            | script | scripts/check.py | the mechanical rule engine: one program, 13 flag modes, human text on stdout | CH all
mode:check:bare         | mode | check.py . | the full report; 19 checks; exit 1 on any blocking finding | CH SH FAN
mode:check:status       | mode | --status | standing, planned, parts, audits, sight, outside, where | CH BP SP AA
mode:check:state        | mode | --state | the Work block: git, gh, open runs, branches, scenarios, audits | CH EP FAN
mode:check:sync         | mode | --sync | move an entry's state line where a merged PR already decided it | CH BP FAN
mode:check:record       | mode | --record | rewrite every source and dependency hash in place | CH BP RU
mode:check:epic         | mode | --epic | the one blocking gate: bounds, scenarios, run/test, verification answers | CH EP
mode:check:entries      | mode | --entries KEY… | every open block under the named entries, in full | CH EP
mode:check:owed         | mode | --owed | the verification kinds a feature of this project owes | CH SH FAN
mode:check:tests        | mode | --tests | this project's testing on one screen, all derived | CH
mode:check:brief        | mode | --brief KEY | everything a run reads before it designs, in one call | CH SH SP
mode:check:run          | mode | --run DIR | judge one run file as it closes, plus entry drift | CH SH SP EP FAN
mode:check:manual       | mode | --manual | run every proof in docs/manual.md and delete what has happened | CH FAN
mode:check:pr-base      | mode | --pr-base BASE | what a PR from HEAD into that base will carry | CH RU
mode:check:pr-body      | mode | --pr-body FILE | measure a PR body against three character budgets | CH RU
mode:check:offline      | mode | --offline (hidden) | replace the Github object with one that can answer nothing | CH
script:runfile          | script | scripts/runfile.py | the shared "what a run is" module: constants, read/runs/in_flight/kind/resume_command | HR CH OR EP
script:orchestrate      | script | scripts/orchestrate.py | the driver program: serial loop, one session per child | OR SP EP SH HR RU AA DS
fn:orchestrate:main     | fn | main() | args, self-detach, tmux check, single-driver check, then go() | OR
fn:orchestrate:go       | fn | Driver.go() | the batch loop: control, skip cascade, chain, build, frame, close | OR
fn:orchestrate:build    | fn | Driver.build() | one child: watch, then judge built/blocked by run file, PR or pushed branch | OR
fn:orchestrate:watch    | fn | Driver.watch() | the poll loop: terminal, handoff, health, limit, overload, nudge, restart | OR
fn:orchestrate:close    | fn | Driver.close() | start the closing session, judge whether the batch closed | OR
fn:orchestrate:hand_back| fn | Driver.hand_back() | start the epic's advance session and exit without waiting | OR
fn:orchestrate:apply_frame | fn | Driver.apply_frame() | frame map → needs on siblings and a reordered queue | OR
fn:orchestrate:launcher | fn | Launcher | the only thing that knows how a visible session is made and closed | OR
script:orchestrate-detached | script | the systemd copy of the driver | same program re-executed as a transient user unit | OR
hook:guard              | hook | hooks/guard.py (PreToolUse/Bash) | refuses merge, force-push, push-to-default, held-tree switch, whole-product walk | HR SH BP EP RU
hook:stop               | hook | hooks/stop.py (Stop, all) | blocks turn-end while this session's run is mid-step; closes a finished epic's session | HR BP EP OR
script:validate         | script | scripts/validate.sh | the kit's own guard: 20 mechanical checks over its own repo; what CI runs | DS RU CH
script:measure          | script | scripts/measure.py | dev-only cost/turns analyser over Claude Code transcripts; does not ship | DS BP
script:release          | script | scripts/release.sh | version bump, validate, commit, tag | DS
```

### (e) Durable files and records in a project — 33

```
file:project-yml     | file | .agent-kit/project.yml | language, stage, commands, knowledge verdicts, verification answers | all
file:run-json        | file | .agent-kit/runs/<slug>/run.json | one run's memory and hand-off; git-ignored | SH FAN HR OR CH DS AA RU
file:run-json:batch  | file | a batch's run.json | children, step, base, window, model, parent, blockers, spent | SP EP OR
file:run-json:child  | file | a feature child's run.json | command:ship, entries/task, gate, branch, base/parent, needs, deliver | SP OR
file:run-json:frame  | file | the frame child's run.json | gate:none, deliver:branch, needs:[], prompt, the frame map | SP EP
file:run-json:epic   | file | the epic's own run.json | command:"epic", step, entries, children (batch slugs), window, finish, model | EP OR
file:run-log         | file | .agent-kit/runs/<…>/run.log | the driver's own event trace; no agent writes it | SP SH RU OR
file:control         | file | .agent-kit/runs/<batch>/control | one line: `skip <slug>` or `stop`; read and deleted by the driver | SP RU EP OR
file:driver-out      | file | .agent-kit/runs/<batch>/driver.out | the driver's stdout/stderr, via shell redirect; the program never names it | SP OR
file:knowledge       | file | docs/knowledge/*.md | the entries: key, state, fields, notes, source lines | all
file:product-md      | file | docs/knowledge/product.md | narrative, Parts, non-goals, MVP bounds section | EP CH DS AA
file:scenarios-md    | file | docs/knowledge/scenarios.md | scenario headings, read by check_epic and by scenarios() | EP CH DS AA
file:stack-md        | file | docs/knowledge/stack.md | library map, decisions per area; hosts [found …] and [frame …] | SH SP AA DS
file:actions-md      | file | docs/knowledge/actions.md | the actor.verb_object entries; carries the `state:` line | DS AA (edge-only, see DANGLING)
file:actors-md       | file | docs/knowledge/actors.md | who/what initiates actions | DS AA (edge-only)
file:screens-md      | file | docs/knowledge/screens.md | UI surfaces and their transitions | DS (edge-only)
file:entities-md     | file | docs/knowledge/entities.md | what persists, its states and invariants | DS
file:integrations-md | file | docs/knowledge/integrations.md | external systems the product depends on | DS
file:technical-debt  | file | docs/technical_debt.md | the ledger of understood-and-not-done work | BP SH SP FAN AA CH DS RU EP
file:manual-md       | file | docs/manual.md | what only the owner can do, each with a proof command | SH SP FAN CH DS RU
file:audits-lens     | file | docs/audits/<lens>.md | one lens's work list, rewritten whole each run | AA EP FAN RU CH DS
file:audits-baseline | file | docs/audits/baseline.md | the baseline check's output; belongs to no lens | AA
file:advice-lens     | file | docs/advice/<lens>.md | one advise-lens's report, rewritten whole each run | AA CH DS
file:batch-record    | file | docs/runs/<slug>.json | the durable batch record: pr, branches, spent, counts | SP EP CH DS
file:deployment-md   | file | docs/deployment.md | release-only manual actions while stage: development | RU DS
file:claude-md-block | file | CLAUDE.md <!-- agent-kit:where --> block | the map of where the project keeps its knowledge | BP DS
file:gitignore       | file | .gitignore | ship adds .agent-kit/runs/ if missing | SH SP
file:workflow-yml    | file | .github/workflows/<name>.yml | the project's own CI pipeline | CH DS
file:transcript      | file | ~/.claude/projects/<slug>/*.jsonl | the session heartbeat, context size and API-error record | OR DS
file:cgroup          | file | /proc/self/cgroup | read once to decide whether the driver would die with its pane | OR
file:pr-body         | file | the composed pull request body | What did not happen, Manual actions, Assumptions, Proven, per-feature, Review | SP RU
rec:block-accepted   | record | [accepted …] block under a slot | written by advise, raised by next, finished by blueprint | AA BP RU DS
artifact:fix-branch  | artifact | claude/fix-<slug>, or the --pr's own branch | fix's delivered artifact | FAN
```

### (f) Rules — 9

```
rule:asking            | rule | rules/asking.md | choices not prose, 2-4 options, recommendation first, gate:none → assumption | RU BP SH SP EP AA
rule:audit-boxes       | rule | rules/audit-boxes.md | who may tick a box in docs/audits/<lens>.md and what a tick must rest on | RU AA FAN SP
rule:channels          | rule | rules/channels.md | writer/reader/closer/durability for every durable record in the kit | RU BP SH DS
rule:closing           | rule | rules/closing.md | identity line, "say what's thin" report, next-command line | RU BP SH SP EP FAN AA
rule:craft             | rule | rules/craft.md | four coding standards shared by ship, fix and the reviewer | RU SH FAN
rule:knowledge-writing | rule | rules/knowledge-writing.md | shared discipline for blueprint and advise writing docs/knowledge/ | RU BP AA DS
rule:preflight         | rule | rules/preflight.md | the reaction table every build command follows after the knowledge check | RU BP SH SP EP FAN AA
rule:pull-requests     | rule | rules/pull-requests.md | PR body shape, three size ceilings, who opens and who reviews | RU SH SP EP FAN AA
rule:window            | rule | rules/window.md | what a standing-by session does and does not do during a driven batch | RU SP EP
```

### (g) Templates and kit-level data — 9

```
tpl:project-yml      | tpl | templates/project.yml | source for .agent-kit/project.yml; also check_shape's comparison | BP DS CH
tpl:run-json         | tpl | templates/run.json | the shape every run file follows; check_runs' authority | SH SP DS CH HR
tpl:batch-json       | tpl | templates/batch.json | the shape of docs/runs/<slug>.json; check_batches' authority | SP EP DS CH
tpl:workflow         | tpl | templates/workflow.yml | CI workflow a task-only ship may generate | SH DS
tpl:manual           | tpl | templates/manual.md | copied to docs/manual.md on first manual action | SH DS
tpl:technical-debt   | tpl | templates/technical_debt.md | copied to docs/technical_debt.md on first debt line | SH BP DS
tpl:where-things-are | tpl | templates/where-things-are.md | source for the CLAUDE.md block | BP DS
tpl:knowledge-slot   | tpl | templates/knowledge/*.md (×8) | one per slot; each declares its own fields: and section shape | BP RU DS CH
file:verification-yml| data | plugins/agent-kit/verification.yml | the kit's catalogue of 12 verification kinds | BP EP CH DS
```

### (h) External tools and refused command patterns — 26

```
ext:git             | ext | git CLI | clean-tree check, branches, commits, diff, push, rev-parse, ls-remote, grep | SH FAN OR CH HR AA DS
ext:gh              | ext | gh CLI | pr create, pr checks, pr list, pr view; never pr merge | SH SP EP FAN CH
ext:tmux            | ext | tmux | session identity and the session mechanism for every child | SP EP HR OR CH
ext:git-worktree    | ext | git worktree add | blueprint's own tree; epic's fresh-boot preview; accept's look-at-it command | BP EP FAN RU
ext:git-diff        | ext | git diff <default>...<run-branch> | read-only look at an in-flight run's knowledge writes | BP
ext:git-commit-push | ext | git commit/push | one commit per slot, pushed when there is a remote | BP
ext:claude-new      | ext | claude-new | optional host helper that registers and names a session | OR
ext:claude-close    | ext | claude-close | optional host helper that unregisters then kills a session | OR HR
ext:claude-binary   | ext | claude --dangerously-skip-permissions --remote-control | the portable fallback session inside a tmux pane | OR
ext:systemd-run     | ext | systemd-run --user --collect | moves the driver out of the pane's control group | OR
ext:security-review | ext | /security-review | run on trigger surfaces; also by the security lens | SH AA
ext:AskUserQuestion | ext | AskUserQuestion tool | the interactive tool every owner-facing fork goes through | RU
ext:web-research    | ext | web search | the "from research" tag in each advise lens's wide half | AA
ext:dep-tooling     | ext | composer/npm/pip outdated+audit | the deps lens never reasons about versions itself | AA
ext:project-suite   | ext | commands.test/lint/types | the declared suite, run once at Verify | SH FAN AA
ext:project-mutate  | ext | commands.mutate | mutation testing over the changed files | SH FAN AA
ext:project-run     | ext | commands.run | starts the app for manual exercise | SH EP
ext:e2e-suite       | ext | the project's end-to-end tests | run first by the scenarios lens if present | AA
ext:proof           | ext | a docs/manual.md `proof:` command | the one thing check.py executes that a run wrote | CH
ext:github-actions  | ext | GitHub Actions | runs the project's workflow, and the kit's own ci.yml | DS
ext:pull-request    | ext | the GitHub pull request | the report surface the owner reads and merges | RU SH SP EP FAN
cmd:gh-pr-merge     | refused | `gh pr merge` | refused unconditionally while a run is in flight | HR SH
cmd:git-push-force  | refused | `git push --force|-f|--force-with-lease|+refspec` | refused unconditionally while a run is in flight | HR SH
cmd:git-push-default| refused | `git push` to the default branch | refused while a run is in flight | HR SH
cmd:git-checkout-switch | refused | `git checkout`/`git switch` (not `-- path`) | refused when another session's run holds this checkout | HR SH BP RU
cmd:e2e-walk        | refused | the project's declared commands.e2e | refused inside a ship/fix session mid-flight | HR SH
```

---

## ALIASES FOLDED

```
cmd:blueprint  <- cmd:blueprint (BP AA CH DS) ; ext:blueprint (FAN next ladder) ; ext:hand-off-blueprint (FAN fix) ; ext:blueprint-narrowed (FAN accept)
cmd:ship       <- cmd:ship (SH CH DS) ; agent:ship (SP) ; ext:ship (FAN) ; cmd:ship = the /agent-kit:ship --run prompt (OR)
cmd:fix        <- cmd:fix (FAN BP SH) ; ext:fix (FAN next rung 4) ; cmd:fix (CH DS)
cmd:sprint     <- cmd:sprint (SP BP SH CH DS) ; ext:sprint (FAN) ; cmd:sprint-close's owner (OR)
cmd:epic       <- cmd:epic (EP BP SH AA DS) ; agent:epic (SP) ; ext:epic (FAN) ; cmd:epic-caller (CH)
cmd:next       <- cmd:next (FAN SP CH DS) ; cmd:next (AA)
cmd:accept     <- cmd:accept (FAN CH DS) ; cmd:accept (SP, declared from the task brief, no source line) ; bare `accept` used as an edge id (FAN, 3 edges)
cmd:audit      <- cmd:audit (AA CH) ; ext:audit (FAN rung 8)
cmd:advise     <- cmd:advise (AA CH) ; cmd:advise (DS, sourced from rules/knowledge-writing.md)
inv:ship:run   <- cmd:ship (OR, the literal prompt) ; ship's `--run <dir>` resume form (SH)
inv:sprint:close <- cmd:sprint-close (OR) ; session:close's invocation (SP) ; session:batch-close's prompt (EP)
inv:epic:advance <- cmd:epic-advance (OR) ; session:advance-session's invocation (EP)
gate:run-in-flight <- gate:run-in-flight (RU) ; gate:run-in-flight-next → kept separate as gate:next:run-in-flight (FAN) because next alone keeps four writes
script:check   <- script:check.py (BP AA EP) ; script:check (SH HR RU) ; script:check-py (DS) ; script:check (CH)
mode:check:bare    <- script:check-bare (FAN)
mode:check:status  <- script:check-status (SP) ; the `--status` half of `--status --state` (FAN EP)
mode:check:state   <- script:check-status-state (FAN accept) ; script:check-status-state-next (FAN next) ; gate:status-state's target (EP)
mode:check:sync    <- script:check-sync (FAN accept) ; script:check-sync-next (FAN next)
mode:check:manual  <- script:check-manual (FAN accept) ; script:check-manual-next (FAN next)
mode:check:owed    <- script:check-owed (FAN)
mode:check:run     <- script:check-run (FAN SP)
mode:check:brief   <- script:check-brief (SP)
mode:check:epic    <- the target of gate:epic-check's invoke (EP)
script:runfile <- script:runfile (HR) ; script:runfile.py (EP) ; script:check.runfile (CH) ; runfile (OR)
script:orchestrate <- script:orchestrate (SP SH HR CH OR) ; script:orchestrate.py (EP AA RU) ; script:orchestrate-py (DS) ; session:driver-process's program (EP)
hook:guard     <- hook:guard (BP SH HR) ; hook:guard.py (EP) ; script:guard.py (RU)
hook:stop      <- hook:stop (BP HR) ; hook:stop.py (EP) ; ext:stop-hook (OR) ; hook:stop as an undeclared edge source (SH)
script:validate<- script:validate.sh (RU) ; script:validate (CH) ; script:validate-sh (DS)
script:measure <- script:measure.py (BP) ; script:measure-py (DS)
session:feature-child <- session:ship-run (SH) ; session:feature-N (SP) ; session:child (OR) ; session:feature (HR)
session:batch-close   <- session:close (SP OR) ; session:batch-close (EP)
session:advance       <- session:advance-session (EP) ; session:advance (OR)
session:driver        <- session:driver (SP RU) ; session:driver-process (EP) ; the running orchestrate.py process (OR HR)
session:audit-run     <- session:audit.run (AA) ; session:audit-child (EP)
session:registered-epic <- session:epic (HR) ; overlaps session:epic-gate + session:advance (EP)
agent:reviewer <- agent:reviewer (SH BP FAN) ; agent-kit:reviewer as an edge target (RU)
file:run-json  <- file:run-file (SH) ; file:run-json (FAN DS) ; file:run.json (RU AA HR) ; file:runfiles (CH) ; file:run-json-live (FAN accept)
file:run-json:batch <- file:batch-run (SP OR)
file:run-json:child <- file:feature-run (SP) ; file:child-run (OR)
file:run-json:frame <- file:frame-run (SP) ; file:frame-child (EP)
file:run-json:epic  <- file:run.json-epic (EP) ; file:parent-run (OR)
file:knowledge <- file:docs/knowledge/* (BP) ; file:knowledge (SH CH) ; file:docs-knowledge (RU) ; file:knowledge-slot (DS) ; file:knowledge.entry (AA) ; file:knowledge-entry (FAN edge)
file:product-md   <- file:product-md (EP) ; file:knowledge.product (AA) ; file:knowledge.product-nongoals (AA) ; tpl-side product (DS)
file:scenarios-md <- file:scenarios-md (EP) ; file:knowledge.scenarios (AA) ; file:knowledge-scenarios (DS)
file:stack-md     <- file:stack-md (SH SP) ; file:knowledge.stack (AA)
file:actions-md   <- file:knowledge.actions (AA) ; file:knowledge-actions (DS) — never declared as a node by any sector
file:actors-md    <- file:knowledge.actors (AA) ; file:knowledge-actors (DS) — never declared as a node by any sector
file:screens-md   <- file:knowledge-screens (DS) — never declared as a node by any sector
file:technical-debt <- file:technical_debt (BP AA) ; file:technical-debt-md (SH DS) ; file:docs-technical-debt (RU EP) ; file:technical-debt (SP FAN) ; file:debt (CH)
file:manual-md   <- file:manual-md (SH SP DS) ; file:docs-manual (RU) ; file:manual (CH)
file:audits-lens <- file:audits.lens (AA) ; file:docs-audits (RU FAN) ; file:audits (CH) ; file:audits-lens (DS) ; file:audits.any (AA edge)
file:advice-lens <- file:advice.lens (AA) ; file:advice (CH) ; file:advice-lens (DS)
file:batch-record<- file:docs-runs-json (SP EP) ; file:batch-json (FAN DS) ; file:batchrecords (CH)
file:project-yml <- file:project.yml (HR) ; file:project-yml (SH FAN DS) ; file:manifest (CH) ; file:project-yml (SP EP)
file:verification-yml <- file:verification.yml (BP) ; file:verification-yml (EP DS) ; file:catalogue (CH)
file:transcript  <- file:transcript (OR) ; ext:claude-transcripts (DS edge target)
tpl:run-json     <- tpl:run-json (SH SP) ; file:run-template (CH) ; tpl:run-json (DS)
tpl:batch-json   <- tpl:batch-json (SP) ; file:batch-template (CH) ; tpl:batch-json (DS)
tpl:knowledge-slot <- tpl:knowledge-slot (BP) ; file:knowledge-templates (CH) ; the 8 individually-named tpl:knowledge-* nodes (DS), none of which carries an edge
tpl:project-yml  <- tpl:project.yml (BP) ; file:project-template (CH) ; tpl:project-yml (DS)
tpl:technical-debt <- tpl:technical_debt (BP) ; tpl:technical-debt (SH) ; tpl:technical-debt-md (DS)
rule:closing     <- rule:closing (RU BP SH SP EP) ; rule:closing-accept (FAN) ; rule:closing-shared (AA)
rule:preflight   <- rule:preflight (RU BP SH SP EP FAN) ; rule:preflight-next (FAN)
rule:audit-boxes <- rule:audit-boxes (RU AA SP FAN) ; rule:audit-boxes-next (FAN)
ext:git          <- ext:git (SH HR OR) ; ext:git-gh's git half (SP) ; bare `git` as an edge target (AA, 2 edges) ; script:git-branch-delete (FAN)
ext:gh           <- ext:gh (SH EP CH) ; ext:git-gh's gh half (SP) ; ext:gh-pr (FAN) ; script:gh-pr-view (FAN)
ext:project-mutate <- ext:project-mutate (SH) ; ext:project.mutate (AA) ; commands.mutate reads (FAN)
ext:project-suite  <- ext:project-suite (SH) ; ext:project.test-suite (AA)
```

**Two id collisions that are NOT the same thing and were kept apart:**
- `gate:tmux-check` is used by SP (inside the brief, before writing run files) and by EP (the epic
  gate's first precondition). Kept as `gate:sprint:tmux-check` and `gate:epic:tmux-check`.
- `file:pr-body` (SP: the composed PR body text) vs `cmd:pr-body`/`mode:check:pr-body` (CH: the
  check.py flag that measures it). Kept apart.

---

## EDGES

### From commands and invocations

```
inv:blueprint:bare -> phase:blueprint:preflight | invokes | always, before anything else | BP
inv:blueprint:recall -> file:knowledge | reads | retells a part out loud, never shows the file | BP
inv:blueprint:recall -> gate:blueprint:recall-followup | hands-off | after the retelling | BP
inv:blueprint:check -> script:check | invokes | mechanical only, exit 1 when findings | BP
cmd:blueprint -> script:check | invokes | --check runs check.py . --status --sync | BP
cmd:blueprint -> mode:check:status | invokes | before any of it, always | BP CH
cmd:blueprint -> mode:check:sync | invokes | the --check invocation | BP CH
cmd:blueprint -> mode:check:record | invokes | after writing a source: line | BP CH RU
cmd:blueprint -> file:project-yml | writes | the manifest; no build command may edit it | BP DS
cmd:blueprint -> file:knowledge | writes | copies the slot template, then interviews | BP DS
cmd:blueprint -> file:claude-md-block | writes | between the agent-kit:where markers only | BP DS
cmd:blueprint -> file:technical-debt | writes | debt from the 3-way fork and the used-it fork | BP DS
cmd:blueprint -> file:verification-yml | reads | walked top to bottom with the owner | BP
cmd:blueprint -> tpl:project-yml | reads | template for .agent-kit/project.yml | BP
cmd:blueprint -> tpl:where-things-are | reads | template for the CLAUDE.md block | BP
cmd:blueprint -> tpl:technical-debt | reads | copied only if the project has no ledger yet | BP
cmd:blueprint -> tpl:knowledge-slot | reads | write from the template, never from memory | BP RU
cmd:blueprint -> rule:knowledge-writing | delegates | shape, language, state, hashing, commits | BP RU
cmd:blueprint -> rule:asking | delegates | every question format | BP RU
cmd:blueprint -> rule:channels | delegates | who may close which block | BP
cmd:blueprint -> rule:closing | delegates | opening and closing lines | BP RU
cmd:blueprint -> ext:git-worktree | invokes | takes its own tree while a run is in flight | BP
cmd:blueprint -> ext:git-diff | invokes | reads an in-flight run's branch for knowledge changes | BP
cmd:fix -> cmd:blueprint | hands-off | a "fix" that turns out to be an undescribed feature | BP FAN
cmd:fix -> phase:fix-invoke | invokes | any of the three argument forms | FAN
cmd:fix -> rule:craft | reads | shares craft, asking and unmet-marking with ship | SH FAN
cmd:ship -> cmd:blueprint | hands-off | [assumed]/[stale]/[found] blocks left for blueprint | BP SH
cmd:sprint -> cmd:blueprint | hands-off | on a test/entry contradiction, the "entry is wrong" branch | BP
cmd:sprint -> file:knowledge | writes | closing session applies [stale …] within two named limits | BP
cmd:sprint -> phase:sprint:brief-knowledge | invokes | bare invocation with no --frame/--close/--window/--resume | SP
cmd:sprint -> phase:sprint:brief-no-theme | invokes | called with no theme | SP
cmd:sprint -> inv:sprint:frame | invokes | only ever typed by the driver | SP
cmd:sprint -> inv:sprint:close | invokes | only ever typed by the driver | SP
cmd:sprint -> inv:sprint:window | invokes | a fresh session standing beside a run | SP
cmd:sprint -> inv:sprint:resume | invokes | restarts the driver over the same run dir | SP
cmd:sprint -> mode:check:status | invokes | before you ask anything | SP CH
cmd:sprint -> mode:check:run | invokes | per queued child; and at close over the batch dir | SP CH
cmd:sprint -> mode:check:brief | invokes | frame child, per feature entry | SP CH
cmd:sprint -> file:batch-record | writes | closing session fills templates/batch.json | SP DS
cmd:sprint -> file:manual-md | writes | closing session copies the template and merges children's manual[] | SP DS
cmd:sprint -> session:feature-child | delegates | composes children with command:"ship", entries/task, optional approach/tasks | SH SP
cmd:epic -> cmd:blueprint | hands-off | refuses to start on missing bounds/scenarios/commands; offers blueprint | BP EP
cmd:epic -> file:knowledge | reads | branches from the branch a blueprint run left knowledge on | BP EP
cmd:epic -> gate:epic:tmux-check | invokes | bare invocation, before anything else | EP
cmd:epic -> gate:epic:epic-check | invokes | after the tmux check | EP
cmd:epic -> gate:epic:status-state | invokes | check.py . --status --state | EP
cmd:epic -> mode:check:epic | invokes | the gate, first thing; exit 1 blocks | EP CH
cmd:epic -> mode:check:state | invokes | the gate, second; and again in the proving phase | EP CH
cmd:epic -> mode:check:entries | invokes | scope: every key, built and planned alike | EP CH
cmd:epic -> mode:check:run | invokes | --advance, after a batch closed | EP CH
cmd:epic -> script:orchestrate | invokes | runs ship per feature and the closing session per batch | SH EP
cmd:epic -> session:audit-run | spawns | an audit lens as a batch child, not a ship | AA EP
cmd:epic -> file:batch-record | reads | a later gate prices the next scope from `spent` | SP EP DS
cmd:next -> cmd:blueprint | hands-off | rungs 6, 7, 9, 10 and the three overrides | BP FAN
cmd:next -> cmd:ship | hands-off | one missing entry, or a task-only ship for CI/skeleton work | SH FAN
cmd:next -> file:batch-record | reads | `branches`/`parked`, to know which branches to delete | SP FAN DS
cmd:next -> mode:check:manual | invokes | first of all, before anything else is read | FAN CH
cmd:next -> mode:check:sync | invokes | an entry `building` whose PR merged | FAN CH
cmd:next -> mode:check:state | invokes | the one mechanical read, after --manual | FAN CH
cmd:next -> gate:next:run-in-flight | blocks | the check prints the in-flight run first | FAN
cmd:next -> phase:next-bookkeeping | invokes | the four writes allowed even mid-flight | FAN
cmd:next -> phase:next-ladder | invokes | rank findings top-down | FAN
cmd:next -> rule:audit-boxes | delegates | tick a box, only if tree clean and branch already merged | FAN RU
cmd:next -> ext:git | invokes | git branch -D … && git push origin --delete …, only named-delivered branches | FAN
cmd:accept -> cmd:blueprint | hands-off | unanswered blocks handed over, narrowed to this run | BP FAN
cmd:accept -> ext:gh | invokes | gh pr view <n> --json title,body,mergeable,statusCheckRollup | FAN
cmd:accept -> mode:check:state | invokes | read exactly this, and stop | FAN CH
cmd:accept -> mode:check:manual | invokes | run the proofs before listing | FAN CH
cmd:accept -> mode:check:sync | invokes | an entry still building whose PR merged, on a clean tree | FAN
cmd:accept -> file:batch-record | reads | answers, unmet, manual, blockers, deviations, notes | FAN
cmd:accept -> file:run-json | reads | the same fields, while still on this machine | FAN
cmd:accept -> phase:accept-verdict | invokes | after reading gh + check.py + run files | FAN
cmd:accept -> rule:audit-boxes | delegates | tick a box it itself verified done | FAN RU
cmd:accept -> rule:closing | delegates | ends per closing.md | FAN
cmd:advise -> cmd:blueprint | hands-off | [accepted …] blocks finished by blueprint | BP AA
cmd:advise -> file:knowledge | writes | [accepted …] blocks and full entries, via knowledge-writing | BP AA
cmd:advise -> phase:advise.preflight | invokes | always, once | AA
cmd:advise -> gate:advise.clarify | invokes | first word not a recognised lens | AA
cmd:advise -> lens:product | delegates | full run (product first) or `advise product` | AA
cmd:advise -> lens:code | delegates | full run or `advise code` | AA
cmd:advise -> lens:money | delegates | full run or `advise money` | AA
cmd:advise -> phase:advise.closing | invokes | after all requested lenses' reports are written | AA
cmd:advise -> rule:closing | invokes | ending: what's thin, then the next-command line | AA
cmd:advise -> mode:check:status | invokes | preflight | AA CH
cmd:audit -> rule:closing | invokes | what is thin, then one line naming what to run next | AA
inv:audit:run -> file:run-json | reads | `entries` = the area, `task` = the wave context | AA EP
```
*(85 edges)*

### From phases, gates and lenses

```
phase:blueprint:preflight -> script:check | invokes | python3 check.py . --status | BP
phase:blueprint:preflight -> phase:blueprint:talk | returns-to | unconditionally, after the check prints | BP
phase:blueprint:talk -> phase:blueprint:read | hands-off | the telling is captured and narrowed | BP
phase:blueprint:read -> phase:blueprint:compare | hands-off | reading complete | BP
phase:blueprint:compare -> gate:blueprint:contradiction | blocks | only when a row is "contradicts" | BP
phase:blueprint:compare -> phase:blueprint:debt-split | hands-off | non-contradiction rows are stated, not asked | BP
phase:blueprint:debt-split -> file:technical-debt | writes | "does it badly" or "does not work at all" | BP
phase:blueprint:debt-split -> phase:blueprint:write | hands-off | "changes what the product must do" rows | BP
phase:blueprint:write -> file:knowledge | writes | one commit per slot as settled | BP
phase:blueprint:write -> phase:blueprint:gaps | hands-off | after writing, "then the gaps, and only then" | BP
phase:blueprint:write -> ext:git-commit-push | invokes | commits land on the checked-out branch, no PR | BP
phase:blueprint:write -> gate:blueprint:branch-check | blocks | fallback to branch+PR if default protected or a run in flight | BP
phase:blueprint:gaps -> gate:blueprint:gap-tier1 | blocks | MVP bounds/scenarios/endings missing | BP
phase:blueprint:gaps -> gate:blueprint:gap-tier2 | blocks | stored shapes/permissions/money/contracts missing | BP
phase:blueprint:gaps -> gate:blueprint:gap-tier3 | refuses | refuses to ask; everything else becomes an assumption | BP
phase:blueprint:gaps -> gate:blueprint:verification-walk | blocks | during the stack/application-type part | BP
phase:blueprint:gaps -> gate:blueprint:scenario-endings | blocks | the across-parts scenarios step | BP
gate:blueprint:contradiction -> phase:blueprint:write | returns-to | owner picks "description wrong" | BP
gate:blueprint:contradiction -> file:technical-debt | writes | owner picks "product wrong" | BP
gate:blueprint:verification-walk -> file:project-yml | writes | one line per kind under verification: | BP
gate:blueprint:verification-walk -> gate:blueprint:e2e | hands-off | asked in the same breath, never derived | BP
gate:blueprint:e2e -> file:project-yml | writes | the commands.e2e field | BP
gate:blueprint:assumed-block -> file:knowledge | writes | answer written into the entry, block deleted | BP
gate:blueprint:found-block -> file:stack-md | writes | stack.md library map updated, block deleted | BP
gate:blueprint:accepted-block -> file:knowledge | writes | remaining declared fields interviewed, block deleted | BP
gate:blueprint:frame-block -> file:stack-md | writes | folded into decisions per area — only once the batch's PR merged | BP
gate:blueprint:older-kit -> file:knowledge | writes | fills the fields that matter now, [assumed …] where filled unasked | BP
gate:blueprint:recall-followup -> phase:blueprint:talk | hands-off | "change this"/"rework the part" | BP
gate:blueprint:used-it-fork -> phase:blueprint:write | returns-to | description-wrong branch | BP
gate:blueprint:used-it-fork -> file:technical-debt | writes | product-wrong branch, marked `owner` | BP
gate:blueprint:branch-check -> ext:git-commit-push | invokes | decides which branch to commit onto | BP
gate:ship:deliver-mode -> session:feature-child | blocks | deliver:"branch" stops the run after Deliver step 3 | SH
gate:ship:touched-product -> agent:reviewer | refuses | a tests/fixtures/lock/docs-only diff skips the reviewer | SH
gate:ship:touched-product -> ext:security-review | refuses | the same diff-touch test decides the security pass | SH
phase:sprint:brief-knowledge -> mode:check:status | invokes | the first action of the brief | SP
phase:sprint:brief-knowledge -> rule:preflight | delegates | "react per rules/preflight.md" | SP
phase:sprint:brief-compose -> gate:sprint:composition-qs | invokes | when different answers fork the road | SP
phase:sprint:brief-compose -> rule:asking | delegates | question shape and order | SP
phase:sprint:brief-compose -> phase:sprint:brief-write-runs | hands-off | batch and order agreed | SP
phase:sprint:brief-no-theme -> gate:sprint:pile-first | invokes | unless one pile is empty | SP
phase:sprint:brief-no-theme -> gate:sprint:promise-side | invokes | a batch composed of unkept promises | SP
gate:sprint:pile-first -> gate:sprint:candidates | loops-to | after the pile is chosen | SP
phase:sprint:brief-write-runs -> gate:sprint:tmux-check | invokes | before writing anything | SP
gate:sprint:tmux-check -> phase:sprint:brief-write-runs | refuses | tmux missing → offer ship per feature, batch not composed | SP
phase:sprint:brief-write-runs -> file:run-json:batch | writes | the batch run.json per templates/run.json | SP
phase:sprint:brief-write-runs -> file:run-json:frame | writes | when the batch has ≥3 features | SP
phase:sprint:brief-write-runs -> file:run-json:child | writes | one per feature | SP
phase:sprint:brief-write-runs -> mode:check:run | invokes | on every queued child, before the driver starts | SP
phase:sprint:brief-write-runs -> phase:sprint:brief-start-driver | hands-off | once the run files pass the check | SP
phase:sprint:brief-start-driver -> script:orchestrate | spawns | nohup python3 orchestrate.py <batch dir>/ >> driver.out 2>&1 & | SP
phase:sprint:brief-start-driver -> phase:sprint:brief-become-window | hands-off | driver started | SP
phase:sprint:brief-become-window -> session:window | becomes | the brief session stays, follows rules/window.md | SP
gate:epic:epic-check -> script:check | invokes | check.py . --epic | EP
gate:epic:epic-check -> cmd:epic | blocks | a fatal finding: the run does not start, offer blueprint | EP
gate:epic:status-state -> script:check | invokes | scenarios described/covered, tests-mutation, audits history | EP
gate:epic:derive-inlist -> file:product-md | reads | owner's prose scope → entry keys via MVP bounds | EP
gate:epic:derive-inlist -> file:technical-debt | reads | for the "what is owed" scope | EP
gate:epic:entries-settle -> script:check | invokes | check.py . --entries <keys> | EP
gate:epic:entries-settle -> file:knowledge | writes | transcribed answers, block deleted, docs(knowledge): commit before batch 1 | EP
gate:epic:order-batches -> gate:epic:invented-record | hands-off | ordering also decides which feature writes which scenario's e2e test | EP
gate:epic:price -> file:batch-record | reads | rate from docs/runs/*.json `spent`, else ~1h/feature | EP
gate:epic:harness -> file:project-yml | reads | names the harness that will prove the finish line | EP
gate:epic:screen -> cmd:epic | blocks | the one owner round; nothing proceeds until answered | EP
gate:epic:screen -> phase:epic:gate | returns-to | the answer settles scope, batches, model, price into `finish` | EP
phase:epic:gate -> file:run-json:epic | writes | step:"gate", then entries, children, window, finish, model; step:"building" before the driver | EP
phase:epic:gate -> file:run-json:batch | writes | only the next/first batch's run file, never batches ahead | EP
phase:epic:gate -> file:run-json:frame | writes | for a batch of ≥3, exactly as sprint writes one | EP
phase:epic:gate -> ext:git-worktree | hands-off | branch epic/<slug> off the session's current branch, not default | EP
phase:epic:gate -> session:driver | spawns | nohup orchestrate.py <first batch>/ >> driver.out 2>&1 & | EP
phase:epic:auditing -> file:run-json:epic | writes | finish.lenses chosen and written here, not at the gate | EP
phase:epic:auditing -> file:run-json:batch | writes | one batch per wave, one child per lens-unit-of-work | EP
phase:epic:auditing -> session:audit-run | spawns | the child's whole prompt is /agent-kit:audit <lens> --run <its dir> | EP
phase:epic:auditing -> phase:epic:auditing | loops-to | a lens still returning real gaps, up to finish.waves (3) | EP
phase:epic:auditing -> phase:epic:proving | hands-off | waves exhausted or all lenses quiet | EP
phase:epic:proving -> script:check | invokes | check.py . --state, scenarios described vs covered | EP
phase:epic:proving -> file:verification-yml | reads | the kinds this project answered whose runs: epic | EP
phase:epic:proving -> ext:git-worktree | invokes | git worktree add /tmp/<slug>-preview epic/<slug>, boot via commands.run | EP
phase:epic:proving -> phase:epic:auditing | loops-to | a scenario with no e2e test becomes a scenarios-lens sprint | EP
phase:epic:done -> file:batch-record | reads | the run never flips entries to built; that is check.py --sync | EP
phase:epic:done -> ext:gh | hands-off | the closing summary written into the one pull request | EP
phase:epic:done -> file:run-json:epic | writes | step:"done" written last, after the summary | EP
phase:fix-invoke -> gate:fix:not-a-fix | blocks | cause is a missing feature, a product decision, or a rewrite | FAN
phase:fix-invoke -> mode:check:bare | invokes | "Before you start", mechanical, seconds | FAN
phase:fix-invoke -> rule:craft | reads | the four craft rules, before cause-finding | FAN
phase:fix-invoke -> file:run-json | reads | [label says "the entry covering the broken behaviour" — see disagreement 12] | FAN
gate:fix:not-a-fix -> cmd:blueprint | hands-off | "this was never built" | FAN
gate:fix:not-a-fix -> file:technical-debt | writes | the fix would be a rewrite: one line, cause named | FAN
phase:fix-branch -> ext:git | invokes | checkout the --pr branch, or branch claude/fix-<slug> off default | FAN
phase:fix-branch -> file:run-json | writes | task, cause, suite+proved_at, review, manual, notes | FAN
phase:fix-cause -> gate:fix:entry-contradiction | blocks | the cause is an entry-vs-code contradiction | FAN
phase:fix-cause -> gate:fix:cause-not-found | refuses | ~1h in, the cause will not surface | FAN
phase:fix-cause -> phase:fix-prove | loops-to | cause named at line/condition granularity | FAN
phase:fix-prove -> gate:fix:flake-exception | blocks | a failure a test cannot hold | FAN
phase:fix-prove -> phase:fix-change | loops-to | the test fails for the found reason | FAN
phase:fix-change -> file:technical-debt | writes | tidy-ups and neighbouring defects, one line each | FAN
phase:fix-change -> phase:fix-verify | loops-to | change made | FAN
phase:fix-verify -> file:project-yml | reads | commands: tests/types/lint, and commands.mutate | FAN
phase:fix-verify -> file:run-json | writes | mutation, verified[], suite | FAN
phase:fix-verify -> mode:check:owed | invokes | the list of verification kinds owed | FAN
phase:fix-verify -> phase:fix-deliver | loops-to | verification complete | FAN
phase:fix-deliver -> agent:reviewer | spawns | the change touched the product (a test-only fix skips) | FAN
phase:fix-deliver -> rule:pull-requests | reads | the shape of the PR body | FAN
phase:fix-deliver -> ext:gh | invokes | a new PR, or commit+push onto the --pr's branch | FAN
phase:fix-deliver -> file:run-json | writes | step: done, suite, pr, deferred items | FAN
phase:fix-deliver -> mode:check:run | invokes | silent unless a finished run overreaches | FAN
phase:fix-deliver -> rule:closing | delegates | thin spots, where they live, next command | FAN
gate:fix:no-refactor -> file:technical-debt | writes | refactor/tidy/second-defect ideas, never applied here | FAN
gate:fix:no-refactor -> cmd:blueprint | hands-off | an entry rewrite is never fix's to do | FAN
gate:accept:no-diff-read -> cmd:accept | blocks | the diff itself is never opened | FAN
phase:accept-manual -> mode:check:manual | invokes | run the proofs first, before listing | FAN
phase:accept-manual -> file:manual-md | reads | docs/manual.md merged with the run files' manual records | FAN
phase:accept-decisions -> mode:check:state | reads | check.py names the entries carrying expensive decisions | FAN
phase:accept-decisions -> cmd:blueprint | hands-off | offer to settle now, before merge, while the branch is open | FAN
phase:accept-unproven -> file:run-json | reads | suite, proved_at, seams proved against stand-ins | FAN
phase:accept-worktree -> ext:git-worktree | hands-off | the worktree command for the branch | FAN
gate:accept:no-write -> ext:pull-request | refuses | accept never merges | FAN
phase:next-bookkeeping -> file:knowledge | writes | an entry's state: line, its own docs(knowledge): commit | FAN
phase:next-bookkeeping -> file:audits-lens | writes | a ticked box, its own docs(audits): commit | FAN
phase:next-bookkeeping -> file:manual-md | writes | its own docs(manual): commit | FAN
phase:next-ladder -> gate:next:override-no-knowledge | blocks | no docs/knowledge/ | FAN
phase:next-ladder -> gate:next:override-empty-repo | blocks | empty repository | FAN
phase:next-ladder -> gate:next:override-mvp-unfinished | blocks | MVP bounds not reached | FAN
phase:next-ladder -> cmd:fix | hands-off | rung 4: CI failing | FAN
phase:next-ladder -> cmd:blueprint | hands-off | rung 6 waiting_on/assumed, rung 7 thin knowledge, rung 9 debt/promises | FAN
phase:next-ladder -> cmd:audit | hands-off | rung 8: a blind spot (lens never ran / stale / no-e2e scenarios) | FAN AA
phase:next-ladder -> cmd:sprint | hands-off | rung 9 debt-as-batch, rung 10 ~5 planned entries | FAN
phase:next-ladder -> cmd:epic | hands-off | rung 9/10 whole list, empty-repo override | FAN
phase:next-ladder -> cmd:ship | hands-off | rung 10 single entry; rung 8's "nothing runs the suite" | FAN
phase:next-ladder -> phase:next-report | loops-to | the first firing rung becomes the "Next" line | FAN
gate:next:run-in-flight -> rule:preflight | delegates | the rule and the offer are defined there | FAN
gate:next:run-in-flight -> phase:next-bookkeeping | hands-off | four facts stay writable even mid-flight | FAN
phase:audit.baseline -> file:audits-baseline | writes | once per invocation | AA
phase:audit.lens -> script:check | reads | the agent-kit:audit tally comment the check later verifies | AA
lens:tests -> ext:project-suite | invokes | once, before the per-entry walk | AA
lens:tests -> file:audits-lens | writes | docs/audits/tests.md, area by area | AA
lens:deps -> ext:dep-tooling | invokes | composer/npm/pip outdated and audit | AA
lens:deps -> file:audits-lens | writes | docs/audits/deps.md | AA
lens:scenarios -> ext:e2e-suite | invokes | if the project has end-to-end tests | AA
lens:scenarios -> file:scenarios-md | reads | every scenario, section at a time | AA
lens:scenarios -> file:technical-debt | writes | a step that cannot honestly live in a test | AA
lens:security -> file:actions-md | reads | every entry, marking in/out with a reason | AA
lens:security -> ext:security-review | invokes | pointed at the files the risky actions live in | AA
lens:security -> file:audits-lens | writes | docs/audits/security.md | AA
lens:performance -> file:stack-md | reads | to derive the anti-pattern catalogue | AA
lens:conventions -> file:stack-md | reads | walks every rule there | AA
lens:product -> file:scenarios-md | reads | close half | AA
lens:product -> file:actions-md | reads | close half | AA
lens:product -> file:product-md | reads | wide half, and the non-goals exclusion list | AA
lens:product -> file:actors-md | reads | wide half | AA
lens:code -> file:stack-md | reads | homegrown mechanisms vs the library map | AA
lens:code -> file:product-md | reads | the volumes stated there | AA
lens:money -> file:product-md | reads | usually finds nothing written — itself a finding | AA
phase:advise.preflight -> script:check | invokes | python3 check.py . --status | AA
phase:advise.preflight -> gate:advise.clarify | blocks | nothing written at all → name blueprint instead of running | AA
phase:advise.closehalf -> phase:advise.widehalf | loops-to | sequencing within a lens | AA
phase:advise.widehalf -> ext:web-research | invokes | briefed only after the domain reading is written | AA
phase:advise.closing -> rule:asking | invokes | rows to the owner: options, recommendation first, batched | AA
phase:advise.closing -> file:knowledge | writes | "accepted, changes the product/code" → full entry, state: planned | AA
phase:advise.closing -> file:technical-debt | writes | "accepted, work under rules that already hold" → one line | AA
phase:advise.closing -> file:advice-lens | writes | "declined, or not now" → a line, never a block | AA
phase:advise.closing -> rec:block-accepted | writes | owner said yes but the fields were left for later | AA
phase:advise.closing -> session:advise-round | hands-off | branch docs/advise-<date> off default, one commit per item | AA
gate:audit.clarify -> [owner] | blocks | stops before doing anything, asks which lens and area | AA — DANGLING
gate:run-in-flight -> hook:guard | refuses | the SWITCH regex refuses a checkout move in the held tree | RU
gate:run-in-flight -> file:run-json | reads | check.py reads `step` across .agent-kit/runs/ to print in-flight lines | RU
```
*(163 edges)*

### From sessions, agents and the driver

```
session:feature-child -> rule:closing | reads | the first line of every step | SH
session:feature-child -> rule:preflight | reads | react to check.py's findings, plus ship's two extra rows | SH
session:feature-child -> rule:craft | hands-off | pulled in by the --brief read, same call | SH
session:feature-child -> rule:asking | invokes | how the go/no-go and expensive-fork questions are put | SH
session:feature-child -> rule:pull-requests | reads | the shape rule for the PR body | SH
session:feature-child -> mode:check:bare | invokes | check.py . before anything else | SH
session:feature-child -> mode:check:brief | invokes | one call: project corner, entry, named entries, library map, craft.md | SH
session:feature-child -> mode:check:owed | invokes | design step, what will prove this | SH
session:feature-child -> mode:check:run | invokes | at handover and at step 7, closing the run file | SH
session:feature-child -> mode:check:pr-body | invokes | before opening or editing the PR | SH RU
session:feature-child -> mode:check:pr-base | invokes | in the same breath | SH RU
session:feature-child -> file:project-yml | reads | when building from a task, read project.yml + stack.md together | SH
session:feature-child -> file:run-json | writes | created at Design; step, handoff, approach, seams, verified, tasks, assumptions, deviations, unmet, notes, manual, review, suite, pr, blocker | SH
session:feature-child -> file:run-json | reads | --run means resume from `step`; a handoff note; a `parent`'s run file | SH
session:feature-child -> file:knowledge | writes | state: building (pr: n) — only when NOT inside a batch; [assumed]/[stale] blocks; agent-kit:unmet test marks | SH
session:feature-child -> file:stack-md | writes | a [found …] block for a ready-made answer the library map lacks | SH
session:feature-child -> file:technical-debt | writes | a line for work understood and not done; deletes it when finished | SH
session:feature-child -> tpl:technical-debt | reads | copies the template if the project has none | SH
session:feature-child -> file:manual-md | writes | manual records copied when this run opens its own PR | SH
session:feature-child -> file:gitignore | writes | adds .agent-kit/runs/ if absent | SH
session:feature-child -> ext:git | invokes | clean-tree check, branch claude/<slug>, commit, push | SH
session:feature-child -> ext:gh | invokes | gh pr create, gh pr checks; never merges | SH
session:feature-child -> ext:project-suite | invokes | declared test/lint/types once; rerun after fixes | SH
session:feature-child -> ext:project-mutate | invokes | commands.mutate over the changed files | SH
session:feature-child -> ext:project-run | invokes | starts the app and exercises the changed surface | SH
session:feature-child -> ext:security-review | invokes | on trigger surfaces only | SH
session:feature-child -> agent:reviewer | spawns | base branch, run file path, entries, expanded craft.md path | SH
session:feature-child -> gate:ship:owner-present | invokes | Design's "wait for go only if expensive" decision | SH
session:feature-child -> hook:guard | blocks | PreToolUse fires before every Bash call in that session | HR
agent:reviewer -> ext:git | invokes | git diff <base>...HEAD; git show <sha> --stat per closed task | SH
agent:reviewer -> file:knowledge | reads | the entries named in the run file, plus stack.md | SH BP
agent:reviewer -> file:run-json | reads | approach, task list, assumptions, deviations | SH
agent:reviewer -> rule:craft | reads | at the path ship gives it; one of its five questions | SH RU
agent:reviewer -> session:feature-child | returns-to | ordered findings plus a merge-without-reading verdict | SH
session:driver -> session:frame | spawns | the first child if ≥3 features, /agent-kit:sprint --frame <dir> | SP
session:driver -> session:feature-child | spawns | in queue order; prompt = the child's `prompt` or /agent-kit:ship --run <dir> | SP SH OR
session:driver -> session:batch-close | spawns | after all children terminal, /agent-kit:sprint --close <dir> | SP EP OR
session:driver -> session:advance | spawns | hand_back(): /agent-kit:epic --advance <dir>, only if the parent is epic/mvp | SP EP OR
session:driver -> session:audit-run | spawns | when a batch child's prompt names /agent-kit:audit <lens> --run <dir> | EP AA
session:driver -> session:window | invokes | tell() types [driver] … lines, WINDOW_RULE first | SP RU OR
session:driver -> file:run-json:child | writes | session, needs, step, spent, blockers | SP OR
session:driver -> file:run-json:child | reads | polls transcript mtime, step, handoff, assumptions, blockers | SP OR
session:driver -> file:run-json:batch | writes | step, children reorder, spent, blockers, window event | SP OR
session:driver -> file:run-json:frame | reads | polls step; on terminal, apply_frame() reads the `frame` field | SP OR
session:driver -> file:run-json:epic | writes | the hand-back session's name into `session`, read later by the stop hook | EP OR
session:driver -> file:control | reads | take_control() between features, then deletes the file | SP RU OR
session:driver -> file:driver-out | writes | stdout/stderr, by shell redirect only | SP OR
session:driver -> file:run-log | writes | one line per event, mirrored to stdout | SP OR
session:driver -> session:feature-child | blocks | idle > --hang → nudge, then one restart, then step:"blocked" | SP OR
session:driver -> session:feature-child | refuses | control=stop → remaining children step:"skipped" | SP OR
session:driver -> script:check | imports | from check import run_defects; called on every closing child | OR CH AA
session:driver -> script:runfile | imports | TERMINAL and kind() | OR HR
session:driver -> cmd:epic | hands-off | hand_back() if the parent's command is epic/mvp | SP
session:frame -> file:stack-md | writes | commits a [frame …] block on its own branch, pushes | SP
session:frame -> mode:check:brief | invokes | one call per entry; the first call unbriefed to read the map | SP
session:frame -> file:batch-record | reads | per_feature off the newest 1-2 batch records | SP
session:frame -> file:run-json:frame | writes | the `frame` map, then step:"done", notes | SP
session:batch-close -> file:run-json:batch | reads | run.json plus every child's run.json | SP
session:batch-close -> file:project-yml | reads | for the project's language | SP
session:batch-close -> ext:git | invokes | git fetch; git branch -f sprint/<slug> <tip>; git push -u origin | SP
session:batch-close -> ext:gh | invokes | gh pr create per feature (offered, not run); gh pr checks after the batch PR | SP
session:batch-close -> file:pr-body | writes | one PR for the batch, composed per pull-requests.md | SP
session:batch-close -> rule:pull-requests | delegates | section order and shape | SP
session:batch-close -> file:technical-debt | writes | delete closed_debt lines, add deferred lines | SP
session:batch-close -> file:manual-md | writes | merge the children's manual records | SP
session:batch-close -> rule:audit-boxes | delegates | ticking audit work-list boxes | SP
session:batch-close -> file:knowledge | writes | entries → state: building (pr: <n>); apply [stale …] within limits | SP [SP wrote the target as file:stack-md — see disagreement 5]
session:batch-close -> file:stack-md | writes | fill the frame block's `pr: ?` with the real number | SP
session:batch-close -> mode:check:run | invokes | "which records moved while the batch ran", over the batch dir | SP
session:batch-close -> file:batch-record | writes | from templates/batch.json, same commit as the ledger | SP EP
session:batch-close -> file:run-json:batch | writes | pr, branch, suite, blockers, step:"done" | SP
session:window -> file:control | writes | exactly `skip <slug>` or `stop`, one line | SP RU
session:epic-gate -> rule:closing | invokes | close per rules/closing.md | EP
session:epic-gate -> rule:window | delegates | stays as the control window after closing | EP
session:advance -> mode:check:run | invokes | "did it really close" gate before doing anything else | EP
session:advance -> file:run-json:batch | writes | the next batch's run file (+ frame child if ≥3) | EP
session:advance -> session:driver | spawns | starts the driver on the next batch | EP
session:advance -> phase:epic:auditing | invokes | the in-list is fully built → step:"auditing" | EP
session:advance -> phase:epic:proving | invokes | the audit is done → step:"proving" | EP
session:advance -> phase:epic:done | invokes | scenarios pass → write the PR finish, then step:"done" | EP
session:advance -> file:run-json:epic | writes | may reorder/drop/add batches; sets a dropped batch's step:"skipped" | EP
session:advance -> file:control | writes | can stop the run by writing `stop` into the current batch's control file | EP
session:advance -> script:orchestrate | spawns | a new driver for the next batch | OR
session:epic-resume -> file:run-json:epic | reads | rebuilds which batches are terminal, current, unfinished | EP
session:epic-resume -> session:driver | spawns | the driver on the current batch, or --advance if that batch is done | EP
session:epic-resume -> session:driver | refuses | never starts a second driver over a live one | EP
session:audit-run -> gate:audit.clarify | invokes | the first word is not a recognised lens | AA
session:audit-run -> phase:audit.baseline | invokes | a full run with no lens argument | AA
session:audit-run -> lens:tests | delegates | full run or `audit tests` | AA
session:audit-run -> lens:deps | delegates | full run or `audit deps` | AA
session:audit-run -> lens:scenarios | delegates | full run or `audit scenarios` | AA
session:audit-run -> lens:security | delegates | full run or `audit security` | AA
session:audit-run -> lens:performance | delegates | full run or `audit performance` | AA
session:audit-run -> lens:conventions | delegates | full run or `audit conventions` | AA
session:audit-run -> [agent:lens-subagent] | spawns | full run only — each lens gets its own subagent | AA — DANGLING
session:audit-run -> file:run-json | writes | step:"done", one line in notes, a commit on the run's branch | AA
session:audit-run -> session:driver | returns-to | the driver watches notes and the terminal step, nothing else | AA
session:advise-round -> rule:pull-requests | invokes | one PR for the round, opened after it | AA
session:advise-round -> ext:git | writes | branch docs/advise-<date>, one commit per item, PR sections | AA
session:owner -> hook:guard | reads | PreToolUse fires but never refuses — no run is keyed on this session | HR
session:owner -> hook:stop | reads | Stop fires but no-ops — no `session` match, `window` is ignored | HR
session:registered-epic -> hook:stop | reads | Stop fires but stands aside on the epic's own in-flight steps | HR EP
```
*(107 edges)*

### From programs

```
script:check -> file:knowledge | writes | --sync rewrites the state: line only | CH BP
script:check -> file:knowledge | reads | every Doc, on every mode behind the knowledge gate | CH
script:check -> file:project-yml | reads | read_manifest, brief, run_defects, print_state | CH
script:check -> file:project-yml | writes | --record rewrites dependency hashes (unconditionally) | CH
script:check -> file:verification-yml | reads | as a dict and as raw text (catalogue + catalogue_defects) | CH DS
script:check -> file:run-json | reads | check_runs, open_runs, print_flight, --run | CH HR DS
script:check -> file:batch-record | reads | delivered_branches, check_batches, --run for a sprint | CH
script:check -> file:manual-md | writes | --manual deletes the closed actions' line ranges | CH DS
script:check -> file:technical-debt | reads | collect_debt | CH DS
script:check -> file:audits-lens | reads | check_channels, check_audits, audit_lenses | CH AA RU
script:check -> file:advice-lens | reads | check_advice — the name only | CH
script:check -> file:workflow-yml | reads | --tests, and the outside line under --status/--state | CH DS
script:check -> file:claude-md-block | reads | the where line, under --status/--state | CH
script:check -> tpl:run-json | reads | check_runs' authority | CH
script:check -> tpl:batch-json | reads | check_batches' authority | CH
script:check -> tpl:knowledge-slot | reads | check_shape, older-kit detection | CH
script:check -> tpl:project-yml | reads | check_shape, key by key | CH
script:check -> ext:git | invokes | via ran(), 30s: grep, branches, ancestry, drift, pr-base | CH
script:check -> ext:gh | invokes | via ran(), gated on which(gh): pr list, pr view | CH
script:check -> ext:tmux | invokes | only when $TMUX is set, in print_flight | CH
script:check -> ext:proof | invokes | subprocess shell=True, 60s — --manual only | CH
script:check -> script:runfile | imports | always | CH HR
script:check -> session:advance | blocks | non-silent --run output means the batch closed badly | EP
hook:guard -> file:run-json | reads | runfile.runs/in_flight, on every Bash call | HR
hook:guard -> file:project-yml | reads | declared_e2e/declared_verification, only while building a feature | HR
hook:guard -> ext:git | invokes | rev-parse, symbolic-ref, for the current and default branch | HR
hook:guard -> ext:tmux | invokes | display-message, for session identity | HR
hook:guard -> cmd:gh-pr-merge | refuses | the MERGE regex, while any run is in flight | HR SH
hook:guard -> cmd:git-push-force | refuses | the FORCE regex, while any run is in flight | HR SH
hook:guard -> cmd:git-push-default | refuses | PUSH + pushes_default, while any run is in flight | HR SH
hook:guard -> cmd:git-checkout-switch | refuses | SWITCH + holds_tree(root) | HR SH BP
hook:guard -> cmd:e2e-walk | refuses | building_a_feature + the e2e substring + no own_checks match | HR SH
hook:guard -> cmd:blueprint | refuses | refuses a branch-switch by an unregistered session, forcing the worktree path | BP
hook:guard -> script:runfile | imports | module load, sys.path insert | HR
hook:guard -> phase:epic:proving | blocks | (context only) the proving phase's real merges are left alone | EP
hook:stop -> file:run-json | reads | runfile.runs and run.json mtime, on every Stop in a tmux session | HR
hook:stop -> ext:tmux | invokes | display-message; kill-session as the fallback closer | HR
hook:stop -> ext:claude-close | invokes | close_myself(), when the helper is present | HR
hook:stop -> session:feature-child | blocks | this session's own run is mid-step, not epic, no handoff | HR SH
hook:stop -> session:registered-epic | closes | this session's epic is terminal and fresh, no other unfinished run | HR EP
hook:stop -> cmd:blueprint | hands-off | matches only registered driver-child sessions, so blueprint is untouched | BP
hook:stop -> script:runfile | imports | module load, sys.path insert | HR
script:orchestrate -> file:run-json | writes | session, window, step, spent, frame, needs | HR SH
script:orchestrate -> script:runfile | imports | TERMINAL and kind() | HR OR
script:runfile -> file:project-yml | reads | the MANIFEST constant only — defined, never used | HR
fn:orchestrate:main -> file:run-json:batch | reads | existence check before anything else | OR
fn:orchestrate:main -> file:cgroup | reads | unless AGENT_KIT_DRIVER_DETACHED=1 | OR
fn:orchestrate:main -> ext:systemd-run | invokes | the cgroup contains tmux-spawn + .scope | OR
fn:orchestrate:main -> file:run-log | writes | `detached` or `detach-failed` | OR
fn:orchestrate:main -> ext:tmux | invokes | shutil.which("tmux"); absent → refuse, exit 1 | OR
fn:orchestrate:main -> ext:tmux | refuses | any non-terminal child's session is alive → "another driver is already on this run" | OR
fn:orchestrate:main -> fn:orchestrate:go | invokes | all checks passed | OR
fn:orchestrate:main -> [—] | returns-to | exit 0 after a successful detach | OR — DANGLING (empty target)
ext:systemd-run -> script:orchestrate-detached | spawns | success | OR
fn:orchestrate:go -> session:advance | refuses | kills <parent>-advance at the top; it never closes itself | OR
fn:orchestrate:go -> file:run-json:batch | writes | step=building, later closing; children reorder; spent; blockers | OR
fn:orchestrate:go -> file:control | reads | once per child iteration; deleted whatever it says | OR
fn:orchestrate:go -> session:window | invokes | tell() for start, control, defects, expensive decisions, finish | OR
fn:orchestrate:go -> file:run-json:child | writes | step=skipped on stop or on a skipped dependency | OR
fn:orchestrate:go -> fn:orchestrate:build | invokes | the child has a run file, is not terminal, is not skipped | OR
fn:orchestrate:go -> fn:orchestrate:apply_frame | invokes | a child came back built, or was already done | OR
fn:orchestrate:go -> fn:orchestrate:close | invokes | the child queue drained | OR
fn:orchestrate:go -> fn:orchestrate:hand_back | invokes | children was empty → hand back and exit 1 | OR
fn:orchestrate:apply_frame -> file:run-json:child | writes | a sibling with a run file and no authored `needs` list | OR
fn:orchestrate:apply_frame -> file:run-json:batch | writes | reorders children to [frame-child] + topological order | OR
fn:orchestrate:apply_frame -> fn:orchestrate:go | returns-to | always | OR
fn:orchestrate:build -> fn:orchestrate:watch | invokes | prompt = the child's own, else /agent-kit:ship --run <dir> | OR
fn:orchestrate:build -> inv:ship:run | invokes | prompt_for()'s default | OR
fn:orchestrate:build -> ext:git | invokes | git ls-remote --heads origin <branch>, when the run file is behind | OR
fn:orchestrate:build -> script:check | invokes | run_defects(state, cwd) on every child that closes | OR
fn:orchestrate:build -> file:run-json:child | writes | spent.sessions, blockers, step=done/blocked | OR
fn:orchestrate:watch -> fn:orchestrate:launcher | spawns | the first session, and one per handoff/restart | OR
fn:orchestrate:watch -> file:transcript | reads | every poll: head, tail, mtime | OR
fn:orchestrate:watch -> file:run-json:child | writes | session=<tmux name> on every start | OR
fn:orchestrate:watch -> file:run-json:child | reads | terminal() every poll; `handoff` every poll | OR
fn:orchestrate:watch -> session:feature-child | invokes | types HANDOFF_LINE, "continue", /model <name> | OR
fn:orchestrate:watch -> fn:orchestrate:watch | loops-to | continue after every non-terminal branch | OR
fn:orchestrate:watch -> fn:orchestrate:watch | blocks | sleep(poll); sleep(wait+60) on a 429; sleep(120) on a 529 | OR
fn:orchestrate:launcher -> ext:claude-new | invokes | claude-new on PATH | OR
fn:orchestrate:launcher -> ext:tmux | spawns | no helper: tmux new-session -d -s agent-kit-<name> … | OR
fn:orchestrate:launcher -> ext:claude-close | invokes | stop() with a closer present; its refusal is final, no kill follows | OR
fn:orchestrate:launcher -> ext:tmux | invokes | stop() with no closer: kill-session | OR
fn:orchestrate:launcher -> session:feature-child | spawns | — | OR
fn:orchestrate:close -> fn:orchestrate:watch | invokes | /agent-kit:sprint --close <run-dir>, hand_over=False | OR
fn:orchestrate:close -> inv:sprint:close | invokes | the exact command line | OR
fn:orchestrate:close -> session:batch-close | spawns | via the launcher | OR
fn:orchestrate:close -> file:run-json:batch | writes | step=done or step=blocked | OR
fn:orchestrate:close -> fn:orchestrate:hand_back | invokes | both branches, always | OR
fn:orchestrate:hand_back -> file:run-json:epic | reads | `command` must be epic or mvp | OR
fn:orchestrate:hand_back -> file:run-json:epic | writes | session=<tmux name>, only when the start succeeded | OR
fn:orchestrate:hand_back -> session:advance | spawns | /agent-kit:epic --advance <parent dir>; does not wait | OR
fn:orchestrate:hand_back -> inv:epic:advance | invokes | the exact command line | OR
script:validate -> script:check | reads | reads check.py as text; asserts format constants and lens tuples are covered | CH DS
script:validate -> script:orchestrate | reads | every add_argument("--…") must appear in backticks in sprint/epic SKILL.md | OR DS
script:validate -> rule:channels | reads | parses the table's declared path families; every payload path must have a row | RU DS
script:validate -> tpl:run-json | reads | every non-underscore field must be named in ≥2 payload files | DS
script:validate -> tpl:batch-json | reads | same | DS
script:validate -> hook:guard | invokes | must not error on a harmless Bash command, and must fail open on a broken install | DS
script:validate -> hook:stop | invokes | same | DS
script:validate -> file:verification-yml | invokes | catalogue_defects() plus ≥5 kinds must parse | DS
script:release -> script:validate | invokes | full validate before tagging | DS
script:measure -> file:transcript | reads | ~/.claude/projects/<slug>/*.jsonl and subagents/*.jsonl | DS
script:measure -> cmd:blueprint | reads | the regex that recognizes /agent-kit:blueprint invocations | BP
script:runfile -> cmd:blueprint | reads | classifies it as command-type `errand` | BP
```
*(105 edges)*

### From durable files and records

```
file:run-json:epic -> hook:stop | reads | the hook reads the epic's own `session` and `step` | EP
file:batch-record -> cmd:next | reads | branches[] tells next which to delete after a merge | SP DS
file:batch-record -> cmd:epic | reads | a later gate prices the next scope from `spent`; --advance checks closedness | SP EP DS
file:project-yml -> script:check | reads | commands, knowledge verdicts, verification answers | DS
file:project-yml -> file:workflow-yml | reads | commands.* fill the CI template's placeholders | DS
file:project-yml -> cmd:ship | reads | ship opens verified records at design time from the verification answers | DS
file:run-json -> script:check | reads | --run validates proved_at, verified, mutation, prompt shape | DS
file:manual-md -> script:check | reads | --manual runs each proof and deletes closed lines | DS
file:technical-debt -> script:check | reads | read and counted on every status read | DS
file:workflow-yml -> script:check | reads | --tests inspects .github/workflows/ | DS
file:verification-yml -> script:check | reads | catalogue()/catalogue_defects() | DS
file:verification-yml -> file:project-yml | writes | blueprint walks the catalogue and writes the verification: answers | DS
file:actions-md -> file:actors-md | reads | the actor part of actor.verb_object must resolve | DS
file:screens-md -> file:actions-md | reads | "Leads to" transitions name action keys | DS
file:scenarios-md -> file:actions-md | reads | steps name action keys | DS
file:knowledge -> script:check | reads | KEY_RE/REF_RE/SOURCE_RE parse every entry | DS
rec:block-accepted -> cmd:blueprint | hands-off | the block is finished by blueprint later | AA BP
rec:block-accepted -> cmd:next | reads | next raises the [accepted …] block, per channels.md | AA RU
```
*(18 edges)*

### From rules

```
rule:asking -> ext:AskUserQuestion | invokes | 2-4 options, recommendation first, every owner-facing fork | RU
rule:preflight -> rule:asking | delegates | "put it up as a choice" at the piled-up gate | RU
rule:preflight -> gate:run-in-flight | blocks | a run of this kit holds the checkout | RU FAN
rule:preflight -> file:knowledge | writes | transcribes a settled [assumed …]/[stale …] answer, docs(knowledge): commit | RU
rule:audit-boxes -> file:audits-lens | writes | `- [x] закрыто PR #<n>`, in its own docs(audits): commit | RU AA
rule:channels -> script:validate | reads | validate.sh parses the table's declared path families | RU
rule:closing -> ext:pull-request | hands-off | the only thing asked of the owner belongs under Manual actions | RU
rule:closing -> cmd:next | hands-off | when nothing follows from this run's own work, name /agent-kit:next | RU FAN
rule:craft -> agent:reviewer | reads | "the kit's craft rules, at the path the run gives you" — the reviewer's 5th question | RU
rule:craft -> script:check | reads | the mutation field's presence is checked when commands.mutate is declared | RU
rule:knowledge-writing -> script:check | invokes | --record computes hashes; --status verifies fields and keys | RU
rule:pull-requests -> script:check | invokes | --pr-body counts brief/open/table sizes; --pr-base checks carried branches | RU
rule:pull-requests -> file:deployment-md | writes | stage=development moves "before it ships" items here | RU
rule:pull-requests -> [skills/sprint/references/close.md] | delegates | the actual PR-composition mechanics for a batch/epic | RU — DANGLING
rule:window -> rule:closing | reads | the window's own report follows closing.md's "name where it lives" shape | RU
```
*(15 edges)*

### From templates and external tools

```
ext:github-actions -> script:validate | invokes | ci.yml runs it on push, PR and tag | DS
ext:github-actions -> file:workflow-yml | invokes | the downstream project's own workflow, on every push | DS
```
*(2 edges — every other template and external node is a pure sink)*

---

## DANGLING EDGES

### A. Globally dangling — the endpoint is defined by no sector

| # | edge | sector that wrote it | what it probably meant |
|---|---|---|---|
| 1 | `hook:guard -> ext:project-run/e2e \| blocks` | SH | a compound id; the graph has `ext:project-run` (SH) and `cmd:e2e-walk` (HR), never both at once |
| 2 | `gate:not-a-fix -> ext:hand-off-blueprint \| hands-off` | FAN | `cmd:blueprint`; the sector itself annotates "(see cross-command)" |
| 3 | `script:check-run -> gate:owed-unfinished \| blocks` | FAN | a gate that exists only as this edge's target; the real mechanism is `mode:check:run`'s exit 1 |
| 4 | `gate:review-open-finding -> phase:fix-deliver \| blocks` | FAN | **source** undefined; the real mechanism is `run_defects`' open critical/major rule |
| 5 | `phase:accept-verdict -> gate:not-mergeable \| blocks` | FAN | a gate defined nowhere |
| 6 | `phase:accept-waiting -> ext:owner \| hands-off` | FAN | the human owner — no sector declares an owner node |
| 7 | `gate:accept-no-write -> ext:merge \| refuses` | FAN | `cmd:gh-pr-merge` (HR) or `ext:pull-request` |
| 8 | `gate:accept-no-write -> ext:diff-fix \| refuses` | FAN | nothing; "accept does not fix" has no target |
| 9 | `phase:next-ladder -> ext:resume-commands \| hands-off` | FAN | the set {inv:epic:resume, inv:sprint:resume, inv:ship:run}, produced by `runfile.resume_command` |
| 10 | `gate:audit.clarify -> owner \| blocks` | AA | the human owner |
| 11 | `owner -> phase:advise.closing \| returns-to` | AA | **source** is the human owner |
| 12 | `rule:closing-shared -> owner \| hands-off` | AA | the human owner |
| 13 | `owner -> cmd:manual \| bash, by hand` | CH | the human owner, told to run `check.py --manual` by templates/manual.md |
| 14 | `any-command -> cmd:pr-body \| bash, exit 1 blocks` | CH | **source** is a wildcard: every command that opens a PR |
| 15 | `any-command -> cmd:pr-base \| bash, exit 1 blocks` | CH | same |
| 16 | `session:audit.run -> agent:lens-subagent \| spawns` | AA | a subagent node AA declared for *advise* (`agent:advise-lens-subagent`) but not for audit — the reverse of where the evidence is: audit's SKILL.md states it explicitly, advise's does not |
| 17 | `script:orchestrate.py -> orchestrate.audit() \| invokes` | AA | a function, not a node; = the `audit()` helper inside `fn:orchestrate:build` |
| 18 | `hook:stop.py -> session:gate-session/advance-session \| blocks` | EP | a compound id naming two sessions at once |
| 19 | `cmd:main -> — \| returns-to \| exit 0 after a successful detach` | OR | the target is literally an em-dash: process exit, which the graph has no node for |
| 20 | `rule:pull-requests -> skills/sprint/references/close.md \| delegates` | RU | a file path, not an id; SP models that file's behaviour as `session:batch-close` and never as a node |
| 21 | `lens:* -> …` (10 edges) | AA | `lens:*` is a wildcard, not an id: `session:audit.run -> lens:*`, `lens:* -> file:audits.lens(old)`, `lens:* -> git`, `lens:* -> rule:audit-boxes`, and six advise `lens:* -> file:knowledge.*` reads |
| 22 | `lens:widehalf -> ext:web-research \| invokes` | AA | **source** undefined; the declared node is `phase:advise.widehalf` |
| 23 | `lens:* -> file:knowledge.planned-entries \| reads` | AA | not a file: a *view* over docs/knowledge (entries whose state is `planned`) |
| 24 | `lens:* -> file:audits.any \| reads` | AA | = `file:audits-lens`, all of them at once |
| 25 | `file:knowledge-actions -> file:knowledge-actors`, `file:knowledge-screens -> file:knowledge-actions`, `file:knowledge-scenarios -> file:knowledge-actions` (3 edges) | DS | **three of the eight knowledge slots — actions.md, actors.md, screens.md — exist in the merged graph only as edge endpoints.** No sector declares them as nodes, although `actions.md` is where every `state:` line lives and is the single most-written file in the kit |

### B. Dangling only inside their own sector — another sector supplies the node

These are the "one sector believes something exists" cases, and every one of them resolves:

- SH: `hook:stop -> session:ship-run` — ship never declares `hook:stop` (HR, EP, BP do). Ship's whole
  handoff-and-blocking story depends on a hook ship's own map does not contain.
- SH: `cmd:next`, `cmd:sprint`, `cmd:epic`, `cmd:fix` used as edge endpoints, declared by SH as nodes
  only for `cmd:ship` — the four callers of ship are outside ship's own node list.
- FAN: `rule:preflight -> gate:run-in-flight` (RU declares it); `phase:fix-branch -> ext:git`,
  `phase:accept-manual -> file:manual-md`, `phase:accept-worktree -> ext:git-worktree`,
  `phase:next-bookkeeping -> file:knowledge-entry / file:docs-audits / file:manual-md`,
  `phase:next-ladder -> ext:{fix,blueprint,audit,sprint,epic,ship}` — nine endpoints FAN uses but
  never declares.
- AA: `phase:advise.preflight -> script:check.py`, `lens:scenarios -> file:knowledge.scenarios`,
  `lens:security -> file:knowledge.actions`, `lens:performance/-conventions/-code -> file:knowledge.stack`,
  `lens:*/product -> file:knowledge.product`, `lens:product -> file:knowledge.actors`,
  `lens:scenarios -> file:technical_debt`, `lens:* -> git`.
- DS: `script:measure-py -> ext:claude-transcripts` — = OR's `file:transcript`.
- Three sectors use a bare command word as an edge id where their own node list spells it fully:
  FAN writes `accept -> rule:audit-boxes`, `accept -> script:check-sync`, `accept -> rule:closing-accept`.

---

## ORPHAN NODES

### Nodes with NO INBOUND edge (nothing in the whole kit reaches them)

**Commands — the finding:**
- `cmd:accept` — **nothing hands off to accept anywhere in the merged graph.** SP declared the node
  from the task brief alone ("source: task instructions") and stated it found no contract; FAN's
  accept edges are all outbound; `rule:closing`'s next-command line is the only plausible route and
  no sector drew it.
- `cmd:advise` — same: no command, rule, gate or ladder rung names advise as what to run next.

**Invocations:** `inv:blueprint:bare`, `inv:blueprint:recall`, `inv:blueprint:check` (the owner types
them), `inv:epic:resume` (started by hand; the only would-be edge is dangling #9).

**Gates and phases:**
`gate:blueprint:assumed-block`, `gate:blueprint:found-block`, `gate:blueprint:accepted-block`,
`gate:blueprint:frame-block`, `gate:blueprint:older-kit`, `gate:blueprint:used-it-fork`,
`gate:blueprint:in-flight-source`, `gate:ship:expensive-fork`, `gate:ship:entry-vs-code`,
`gate:ship:deliver-mode`, `gate:ship:touched-product`, `gate:epic:tmux-check`, `gate:epic:derive-inlist`,
`gate:epic:entries-settle`, `gate:epic:order-batches`, `gate:epic:price`, `gate:epic:harness`,
`gate:epic:parts-seen`, `gate:epic:rank-questions`, `gate:epic:screen`, `phase:epic:building`,
`gate:fix:no-refactor`, `phase:accept-manual`, `phase:accept-waiting`, `phase:accept-decisions`,
`phase:accept-unproven`, `phase:accept-worktree`, `gate:accept:no-diff-read`, `gate:accept:no-write`,
`phase:audit.dispatch`, `phase:audit.lens`, `phase:advise.dispatch`, `phase:advise.closehalf`,
`gate:piled-up`.

**Sessions and agents:** `session:brief`, `session:epic-gate`, `session:epic-resume`, `session:owner`,
`session:blueprint-worktree`, `agent:advise-lens-subagent`.

**Programs:** `fn:orchestrate:main`, `mode:check:tests`, `mode:check:offline`, `script:measure`,
`script:release`.

**Files/templates/externals:** `file:entities-md`, `file:integrations-md`, `file:screens-md`,
`artifact:fix-branch`, `tpl:workflow`, `tpl:manual`, `ext:claude-binary`, `ext:github-actions`.

*(66 nodes with no inbound edge.)*

### Nodes with NO OUTBOUND edge (pure sinks)

Every layer-(e) file except the eleven that read something back
(`file:run-json:epic`, `file:batch-record`, `file:project-yml`, `file:run-json`, `file:manual-md`,
`file:technical-debt`, `file:workflow-yml`, `file:actions-md`, `file:screens-md`, `file:scenarios-md`,
`file:knowledge`, `rec:block-accepted`); every layer-(g) template except `file:verification-yml`;
every layer-(h) external except `ext:github-actions` and `ext:systemd-run`.

Named in full, the sinks that are *not* files, templates or tools — i.e. where a sink is surprising:

- `gate:blueprint:gap-tier1`, `gate:blueprint:gap-tier2`, `gate:blueprint:gap-tier3`,
  `gate:blueprint:scenario-endings` — four gates that block a run and then lead nowhere in the map.
- `gate:ship:owner-present`, `gate:ship:expensive-fork`, `gate:ship:entry-vs-code` — the three ship
  gates whose whole content is a decision, with no recorded consequence edge.
- `gate:sprint:candidates`, `gate:sprint:composition-qs`, `gate:sprint:promise-side`.
- `gate:epic:parts-seen`, `gate:epic:invented-record`, `gate:epic:rank-questions`,
  `gate:epic:tmux-check`, `phase:epic:building`.
- `gate:fix:entry-contradiction`, `gate:fix:cause-not-found`, `gate:fix:flake-exception`.
- `phase:accept-verdict`, `phase:next-report`, `phase:audit.dispatch`, `phase:advise.dispatch`.
- `gate:piled-up`, `session:brief`, `session:blueprint-worktree`, `agent:advise-lens-subagent`,
  `mode:check:tests`, `mode:check:offline`, `artifact:fix-branch`, `session:advise-round`'s
  downstream (it has outbound, listed above).
- All 15 `mode:check:*` nodes except none — every mode is a sink; `script:check` carries all the IO.

### Nodes with NEITHER inbound NOR outbound (18 — declared and never wired)

```
gate:blueprint:in-flight-source   BP    which branch to knowledge-read from while a run is in flight
gate:ship:expensive-fork          SH    "is this fork expensive"
gate:ship:entry-vs-code           SH    entry promises X, code does Y
phase:epic:building               EP    step:"building" — the phase the whole driver runs inside
gate:piled-up                     RU    preflight's once-per-run pile-of-decisions gate
phase:audit.dispatch              AA    audit's invocation dispatch
phase:advise.dispatch             AA    advise's invocation dispatch
session:brief                     SP    the brief session (all its edges were written with phase: ids)
session:blueprint-worktree        BP    blueprint's own worktree session
agent:advise-lens-subagent        AA    inferred, "not explicitly stated" by the sector itself
mode:check:tests                  CH    --tests — no payload caller exists anywhere
mode:check:offline                CH    --offline — hidden, no payload caller, tests only
file:entities-md                  DS    docs/knowledge/entities.md
file:integrations-md              DS    docs/knowledge/integrations.md
artifact:fix-branch               FAN   claude/fix-<slug>
tpl:workflow                      SH DS templates/workflow.yml
tpl:manual                        SH DS templates/manual.md
ext:claude-binary                 OR    claude --dangerously-skip-permissions --remote-control
```

---

## CROSS-SECTOR DISAGREEMENTS

**1. Does `check.py --epic` actually gate anything on a project with no blueprint?**

- EP: *"**Gate refuses to start**: `check.py --epic` fatal (no MVP bounds/marker, <2 filled
  bound-lists, no scenarios, missing/non-functional `commands.run`/`commands.test` …) → says what's
  missing, offers `/agent-kit:blueprint`, run never begins."* (epic.md, REFUSALS; epic/SKILL.md:44-46,
  check.py:849-921)
- CH: *"`--epic` on a project with no `docs/knowledge/` returns 0 in complete silence … **The one gate
  with teeth in this program opens for a project that has no blueprint at all.**"* (check.md, SILENCE
  AUDIT #1; check.py:3709-3714 vs 3729)

**Source checked.** `main()` at `scripts/check.py:3709-3714` is:
`knowledge = root / KNOWLEDGE; if not knowledge.is_dir(): … return 0` — and the `--epic` branch is at
3729, *after* it. The `--status`/`--state` message inside that early return does not print either,
because the epic gate's first line passes neither flag. CH is right; EP's refusal is real only once
`docs/knowledge/` exists. `--brief` (3720) and `--entries` (3840) sit behind the same return, which
also makes ship's `--brief` read and epic's `--entries` scope read silent on a fresh project.

**2. Does `check.py --sync` write `project.yml` or the knowledge files?**

- BP: `script:check.py -> file:project.yml | writes | `--sync` moves an entry's state once its PR has
  merged — the one thing `--check` writes` (blueprint.md EDGES)
- CH: *"`--sync` → rewrites `docs/knowledge/<slot>.md` in place, the `state:` line only … `--record`
  → rewrites `docs/knowledge/*.md` `@hash` values **and** `.agent-kit/project.yml` dependency
  hashes."* (check.md, IO/Writes)

**Source checked.** `sync_states()` (check.py:1440-1499) ends with
`if text != doc.text: doc.path.write_text(text …)` — `doc.path` is a `docs/knowledge/*.md` file.
`project.yml` is written only by `record()` (1637-1643). BP's edge points at the wrong file; the
merged graph carries CH's version.

**3. Is the whole-product e2e refusal bound to `ship`, or to `ship` and `fix`?**

- SH: hook:guard *"refuses the declared e2e/scenarios command … specifically inside a registered
  `ship` session"* and again in REFUSALS: *"Inside a session registered as a `ship` specifically."*
- HR: *"`building = building_a_feature(root)` — is *this* session a `ship`/`fix` (`kind == "feature"`)
  run of its own, not yet terminal."*

**Source checked.** `hooks/guard.py:128-138`: `return runfile.kind(state) == "feature" and …`, and
`runfile.BY_COMMAND` maps both `ship` and `fix` to `feature`. HR is right: a `fix` run is refused the
e2e walk too. (Guard's own docstring on that function says "This session is a `ship` mid-flight",
which is where SH's narrower reading comes from — the code and its own comment disagree.)

**4. `driver.out` lives in a run directory that `check.py` declares may hold only three files.**

- SP: *"`file:driver-out | .agent-kit/runs/<batch>/driver.out | Driver's stdout/stderr, redirected
  explicitly (never /dev/null)"* — and the launch line writes it there
  (sprint/SKILL.md:236, epic/SKILL.md:276).
- CH: *"`.agent-kit/runs/*/` directory listings — `check_channels` (2225-2230), which allows only
  `run.json`, `run.log`, `control`."*
- HR: *"Within this sector's reading, a run directory appears to contain exactly one file, `run.json`,
  and nothing else — worth the full map confirming whether any other sector's code writes additional
  files into a run directory."* (HR uncertainty #8 — it asked this question exactly.)

**Source checked.** `check_channels` (check.py:2214-2223) appends every file whose name is not in
`("run.json", "run.log", "control")` to `strays` and reports *"a mechanism nothing declared and
nothing tracks"*. `driver.out` is created by the shell redirect in both launch lines, in the batch's
own run directory. So the kit's own channel check flags a file the kit's own launch line creates.
(It lands in `report.drift`, which is advisory, so nothing breaks — but the answer to HR's open
question is: yes, a fourth file is written, and it is already being reported as drift.)

**5. Where the batch's closing session writes `state: building (pr: n)`.**

- SP: `session:close -> file:stack-md | writes | entries → state: building (pr: <n>); apply [stale …]
  blocks within limits; fill frame block's pr: ?` — one edge, target `stack.md`.
- DS: *"`docs/knowledge/actions.md` … Carries `state:` line: `planned | building (pr: N) | built` —
  **the only place implementation progress is recorded**."*

**Source checked.** `sprint/references/close.md:184-219` has three separate moves under `## Knowledge`:
the state line "for every entry a finished feature built", the `[stale …]` blocks under entries, and
(elsewhere, close.md:50-53) the frame block's `pr: ?` in `stack.md`. Only the third is `stack.md`.
SP collapsed three targets into one and picked the wrong one for two of them. The merged graph splits
the edge.

**6. Does `stop` skip only queued children, or also overwrite finished ones?**

- SP: *"**`stop`** — remaining queued children marked `step:"skipped"`, loop proceeds straight to
  closing."* (sprint.md, REFUSALS)
- OR: *"**`stop` overwrites a finished child's `done` with `skipped`.** The `self.stopping` branch
  (l.1070-1072) sits **before** the `child.terminal()` branch (l.1074) … On `--resume` that is silent
  data loss … Confirmed by reading the source; no test covers it."*

Not settled here (would need the driver's own loop re-read), but the two sectors describe the same
five lines and disagree on whether an already-`done` child survives a `stop`. OR read the ordering;
SP read the prose.

**7. Is the closing session started during a weekly limit?**

- SP: *"Account limit (429) … if wait exceeds `--max-wait` hours (default 6), treats it as a weekly
  limit and stops the whole run, telling the window."*
- OR: *"**The `stopping` flag from a weekly limit is set inside `watch()` but `build()` still judges
  the child** … Then `go()` reaches `close()` (l.1123) and **starts a closing session anyway** —
  during a weekly limit, when no session can do anything. Nothing checks `self.stopping` before
  `close()`."*

SP's "stops the whole run" and OR's "starts a closing session anyway" cannot both be the whole story.

**8. Who may close an `[assumed …]`/`[stale …]` block.**

- BP: *"`blocks.md` says 'ask it as yes-or-no… write the answer… delete the block' (implying
  blueprint), while `channels.md`'s table row says closer is '`blueprint`; **or a build command with
  the owner present**' — i.e. `channels.md` is more permissive than `blocks.md`'s own text reads in
  isolation."*
- RU (preflight table): *"`[assumed …]` blocks on in-scope entries | with `gate: owner`: show + offer
  to settle now, **write answer into entry + delete block in its own `docs(knowledge):` commit**."*
- DS: closed by *"`blueprint`, or a build command with the owner present"*.

Two of three sectors have the permissive reading and one command file has the narrow one. The
merged graph carries the permissive edge (`rule:preflight -> file:knowledge | writes`) and keeps
blueprint's gates alongside it.

**9. Whether a full `advise` run isolates each lens in a subagent — and whether `audit` does.**

- AA (nodes): declares `agent:advise-lens-subagent` for *advise*, marked "Implied … not explicitly
  stated (see UNCERTAIN)".
- AA (edges): draws `session:audit.run -> agent:lens-subagent | spawns | **full run only** — each
  lens gets its own subagent … audit/SKILL.md:161-164`.

The sector declared the node for the command that does *not* document the behaviour and drew the edge
for the command that does — leaving audit's documented subagent with no node (dangling #16) and
advise's undocumented one with no edge (a full orphan).

**10. `--ceiling` for a 200k-window model: 130k or 150k?**

- OR: *"`orchestrate.py:477-479` says a project on a 200k-window model 'must lower this to about
  130k'; `docs/design/2026-08-14-what-one-night-measured.md:49` says 'must set `--ceiling 150`'.
  Neither cites the other."*

One sector, two payload files. Kept because the graph has one `script:orchestrate` node and two
contradictory instructions hanging off it.

**11. Is `accept` subject to the in-flight refusal?**

- FAN: *"`rules/preflight.md:35` lists exactly '`ship`, `fix`, `sprint`, `epic` and `next`' … and
  explicitly says `blueprint` and `advise` are exempted 'and never stop'. `accept` is named in neither
  list … this is a gap, not a stated rule."*
- AA: *"`rules/preflight.md`'s table … lists only `ship`, `fix`, `sprint`, `epic`, `next` as commands
  that must not start over an in-flight run — `audit` and `blueprint`/`advise` are explicitly *not* on
  that stop-list."*
- RU: reproduces the same two lists and adds nothing about `accept` or `audit`.

Three sectors agree on the lists and all three notice the same hole: `accept` and `audit` are on
neither side of a binary rule. Combined with orphan finding above (`cmd:accept` has no inbound edge
at all), `accept` is the least-connected command in the kit.

**12. `fix` reading "the entry covering the broken behaviour" from the run file.**

- FAN (edge): `phase:fix-invoke -> file:run-json | reads | entry covering the broken behaviour, "as
  its own section" | skills/fix/SKILL.md:45-46`

The label describes a *knowledge* entry read as a section; the target is the run file. No other
sector routes an entry read through `run.json`. Recorded here rather than silently retargeted,
because fix/SKILL.md:45-46 was not re-read.

**13. What the driver's own docstring claims versus what it does.**

- OR: *"Module docstring (l.2-14) claims: 'It reads run files, watches a transcript's modification
  time, knows one HTTP status, and calls git and gh.' **Three of those four are wrong today**"* —
  transcript record timestamps not mtime, two HTTP statuses (429 and 529), and no `gh` call at all.
- EP: declares `ext:gh` for its own sector *"on inference (every PR-opening action must go through
  `gh`) … treat this node as low-confidence / likely belongs entirely to the sprint-close sector."*

SP settles EP's doubt in the right direction: `gh pr create` and `gh pr checks` are invoked by
`session:batch-close` (close.md:139-141, 181), not by the driver and not by epic. The merged graph
gives `ext:gh` edges to ship, batch-close and accept, and none to `script:orchestrate`.

**14. An unreadable run file: in flight, or not this session's run?**

- HR: *"`guard.py`'s `in_flight()` treats a run file nothing can parse as *in flight* … `stop.py`'s
  `my_runs()` does the opposite: it filters with `state is not None` … the two hooks read the
  identical signal in opposite directions."*
- CH: *"`open_runs` silently skips a run file it cannot parse … Mitigated: `check_runs` reports it as
  a `Runs` finding and `print_flight` prints `'<slug> · unreadable, and counted as in flight'`."*

Three programs, three stances on one signal: guard counts it, stop discounts it, check.py counts it
loudly in one place and skips it silently in another.

**15. Does `audit` ever run the check?**

- AA: *"I could not confirm audit runs `--status` at all, mechanically or as prose instruction."*
- CH: the CALLERS table lists **no** `audit` invocation; `audit/references/scenarios.md:62` appears
  only under "Prose-only mentions (no invocation)".

The two sectors agree, which settles it: `cmd:audit` is the only command in the kit that never
invokes `script:check`, while being the command whose output (`docs/audits/*.md` tallies) check.py
verifies arithmetically.

---

## COUNTS

### Nodes per layer

| layer | count |
|---|---|
| (a) commands and invocations | 20 (9 commands, 11 invocations) |
| (b) phases, gates and lenses | 105 (41 phases, 55 gates, 9 lenses) |
| (c) sessions, agents and the driver | 16 (14 sessions, 2 agents) |
| (d) programs | 32 (check.py + 15 modes, runfile, orchestrate + 8 fns + the detached copy, 2 hooks, validate, measure, release) |
| (e) durable files and records in a project | 33 |
| (f) rules | 9 |
| (g) templates and kit-level data | 9 |
| (h) external tools and refused command patterns | 26 (21 tools, 5 refused patterns) |
| **total** | **250** |

### Edges per source layer

| source layer | count |
|---|---|
| (a) commands and invocations | 85 |
| (b) phases, gates and lenses | 163 |
| (c) sessions, agents, driver | 107 |
| (d) programs | 105 |
| (e) files and records | 18 |
| (f) rules | 15 |
| (g)+(h) templates and externals | 2 |
| **total merged edges** | **495** |

### Edges per mechanism

| mechanism | count |
|---|---|
| reads | 148 |
| writes | 122 |
| invokes | 116 |
| spawns | 27 |
| blocks | 22 |
| hands-off | 21 |
| delegates | 18 |
| refuses | 17 |
| returns-to | 8 |
| loops-to | 8 |
| imports | 7 |
| becomes | 1 |
| closes | 1 |

### Dangling and orphans

| finding | count |
|---|---|
| globally dangling edges (endpoint defined by no sector) | 25 findings covering 33 edges |
| sector-local dangles that another sector resolves | 6 clusters, ~25 edges |
| nodes with no inbound edge | 66 |
| nodes with neither inbound nor outbound | 18 |
| cross-sector disagreements | 15 (5 settled against the source) |
