# Sector: audit, advise

Sources: `plugins/agent-kit/skills/audit/SKILL.md`, `plugins/agent-kit/skills/audit/references/{tests,deps,performance,scenarios,security,conventions}.md`, `plugins/agent-kit/skills/advise/SKILL.md`, `plugins/agent-kit/skills/advise/references/{code,money,product}.md`, `plugins/agent-kit/rules/audit-boxes.md`, plus cross-refs found by grep across `plugins/` and `scripts/`.

## Command: audit

### NODES

| id | kind | label | description | source |
|---|---|---|---|---|
| cmd:audit | cmd | audit | Reads code, compares to `docs/knowledge/`, writes a work list; never changes code or knowledge. | audit/SKILL.md:8-16 |
| phase:audit.dispatch | phase | invocation dispatch | Parses the typed args into lens+area, or stops to ask. | audit/SKILL.md:21-36 |
| phase:audit.baseline | phase | baseline check | Two comparisons run once per full invocation, not per lens; writes `docs/audits/baseline.md`. | audit/SKILL.md:70-86 |
| phase:audit.lens | phase | one lens's walk | The 7-step shape every lens follows (mechanical pass → citation → per-line search → interpret → area-by-area write → batch into units of work → commit). | audit/SKILL.md:87-113 |
| gate:audit.clarify | gate | clarify before starting | If first word is not a lens/clearly about one, stop, print lenses + one clarifying question (area). | audit/SKILL.md:31-33 |
| file:audits.lens | file | `docs/audits/<lens>.md` | The lens's work list — one file per lens, rewritten whole on each run of that lens. | audit/SKILL.md:186-230 |
| file:audits.baseline | file | `docs/audits/baseline.md` | Output of the baseline check (surfaces missing from entries, entries naming gone surfaces). | audit/SKILL.md:74-86 |
| lens:tests | lens | tests | Walks every entry in scope; per-line coverage citations. | audit/references/tests.md:1-77 |
| lens:deps | lens | deps | Walks direct dependencies via ecosystem tooling. | audit/references/deps.md:1-42 |
| lens:performance | lens | performance | Walks every action against a stack-derived anti-pattern catalogue. | audit/references/performance.md:1-48 |
| lens:scenarios | lens | scenarios | Walks every scenario in `docs/knowledge/scenarios.md`, chaining + tracing steps. | audit/references/scenarios.md:1-95 |
| lens:security | lens | security | Walks risky actions: product's own "must never" rules + generic classes via `/security-review`. | audit/references/security.md:1-54 |
| lens:conventions | lens | conventions | Walks every rule in `docs/knowledge/stack.md`. | audit/references/conventions.md:1-35 |
| script:check.py | script | check.py | `python3 scripts/check.py . --status` etc — mechanical checks, tallies `agent-kit:audit` counters, ticks-with-PR rule. | audit/SKILL.md (implicit); check.py:2252-2338,3187-3196,3388-3392 |
| ext:project.test-suite | ext | `commands.test` | The project's declared test command, run once by the `tests` lens. | audit/references/tests.md:5-6 |
| ext:project.mutate | ext | `commands.mutate` (mutation test) | Referenced elsewhere (check.py) but not by audit lenses directly. | check.py (context) |
| ext:dep-tooling | ext | ecosystem dependency tools | `composer outdated`, `composer audit`, `npm outdated`, `npm audit`, `pip list --outdated`. | audit/references/deps.md:5-6 |
| ext:security-review | ext | `/security-review` command | Invoked by the security lens over the files risky actions live in. | audit/references/security.md:29-32 |
| ext:e2e-suite | ext | project's end-to-end tests | Run first by the scenarios lens if present. | audit/references/scenarios.md:17-19 |
| rule:audit-boxes | rule | audit-boxes.md | Governs who may tick a box in `docs/audits/<lens>.md` and how. | rules/audit-boxes.md:1-46 |
| rule:closing | rule | closing.md | Shared closing-report shape audit follows at the end. | audit/SKILL.md:240-244 |
| session:audit.run | session | a running audit invocation | Either a person-typed run (full or single-lens) or a batch child (`--run <dir>`). | audit/SKILL.md:21-60 |
| file:run.json | file | `.agent-kit/runs/<slug>/run.json` | When run `--run <dir>`, carries `entries` (area), `task` (context), `branch`, and is closed by the lens itself (`step: "done"`, one line in `notes`). | audit/SKILL.md:38-60 |
| cmd:epic | cmd | epic (external) | Spawns `audit <lens> --run <dir>` as a batch child during its `auditing` phase. | epic/references/finish.md:12-68 |
| script:orchestrate.py | script | orchestrate.py (driver) | Starts the audit child's session via `prompt_for`, reads its terminal `step`. | orchestrate.py:832-836 |

### EDGES

| from | to | mechanism | trigger/condition | source |
|---|---|---|---|---|
| session:audit.run -> gate:audit.clarify | invokes | first word not a recognised lens or clearly about one | audit/SKILL.md:31-33 |
| session:audit.run -> phase:audit.baseline | invokes | full run (`audit` with no lens argument) | audit/SKILL.md:70-77 |
| phase:audit.baseline -> file:audits.baseline | writes | once per invocation | audit/SKILL.md:74-77 |
| session:audit.run -> lens:tests | delegates | full run or `audit tests` | audit/SKILL.md:23-30,62-68 |
| session:audit.run -> lens:deps | delegates | full run or `audit deps` | same |
| session:audit.run -> lens:scenarios | delegates | full run or `audit scenarios` | same |
| session:audit.run -> lens:security | delegates | full run or `audit security` | same |
| session:audit.run -> lens:performance | delegates | full run or `audit performance` | same |
| session:audit.run -> lens:conventions | delegates | full run or `audit conventions` | same |
| session:audit.run -> agent:lens-subagent | spawns | **full run only** — each lens gets its own subagent for isolation | audit/SKILL.md:161-164 |
| session:audit.run -> lens:* | invokes (inline) | **single-lens run** — done inline, no subagent (context already oriented) | audit/SKILL.md:163-164 |
| lens:tests -> ext:project.test-suite | reads/runs | once, before per-entry walk | audit/references/tests.md:5-6 |
| lens:tests -> file:audits.lens | writes | `docs/audits/tests.md`, area by area | audit/SKILL.md:104,186-188 |
| lens:deps -> ext:dep-tooling | invokes | `composer outdated/audit`, `npm outdated/audit`, `pip list --outdated` | audit/references/deps.md:5-6 |
| lens:deps -> file:audits.lens | writes | `docs/audits/deps.md` | audit/references/deps.md |
| lens:scenarios -> ext:e2e-suite | reads/runs | if project has end-to-end tests | audit/references/scenarios.md:17-19 |
| lens:scenarios -> file:knowledge.scenarios | reads | `docs/knowledge/scenarios.md`, section at a time | audit/references/scenarios.md:3; audit/SKILL.md:171-175 |
| lens:scenarios -> file:technical_debt | writes | records exception when a step "cannot honestly live in a test" (paid third-party call etc.) | audit/references/scenarios.md:70-73 |
| lens:security -> file:knowledge.actions | reads | every entry, marking in/out with reason | audit/references/security.md:5-9 |
| lens:security -> ext:security-review | invokes | pointed at files the risky actions live in, not the whole repo | audit/references/security.md:29-32 |
| lens:security -> file:audits.lens | writes | `docs/audits/security.md` | audit/references/security.md |
| lens:performance -> file:knowledge.stack | reads | to derive the anti-pattern catalogue | audit/references/performance.md:9-16 |
| lens:conventions -> file:knowledge.stack | reads | walks every rule there | audit/references/conventions.md:3,9-13 |
| lens:* -> file:audits.lens(old) | reads | "Read the previous file before writing the new one" — every lens, before rewriting | audit/SKILL.md:219-221,58-60 |
| lens:* -> git | writes (commit) | one commit per lens file, `docs(audits): …` | audit/SKILL.md:112-113; audit-boxes.md:37-41 |
| phase:audit.lens -> script:check.py | reads (implicit contract) | `agent-kit:audit lens=... walked=... ...` tally comment the check later verifies | audit/SKILL.md:142-156; check.py:2252-2311 |
| gate:audit.clarify -> owner | blocks | stops before doing anything, asks which lens/area | audit/SKILL.md:31-33 |
| cmd:epic -> session:audit.run | spawns | `/agent-kit:audit <lens> --run <its own run directory>` as a batch child, not a `ship` | epic/references/finish.md:12,23-27 |
| script:orchestrate.py -> session:audit.run | invokes | `prompt_for(child)` returns the child's own `prompt` field verbatim (an audit invocation) rather than the default `/agent-kit:ship --run ...` | orchestrate.py:832-836 |
| session:audit.run -> file:run.json | reads | `entries` = area, `task` = wave context (which wave, what moved, what is settled) | audit/SKILL.md:42-49; epic/references/finish.md:29-35 |
| session:audit.run -> file:run.json | writes | sets `step: "done"`, one line in `notes`; leaves a commit on the run's `branch` | audit/SKILL.md:50-56 |
| session:audit.run -> script:orchestrate.py | returns-to | driver watches `notes`/terminal step; if absent, waits until the time limit | audit/SKILL.md:55-56 |
| script:orchestrate.py -> orchestrate.audit() | invokes | after any child (incl. an audit child) finishes, checks `run_defects(state)` and appends to `blockers` if the child closed with something it should not have | orchestrate.py:848-858 |
| lens:* -> rule:audit-boxes | hands-off | governs how a ticked box in the lens's own file must look; enforced later by 3 sessions (batch-closer, next, accept) | rules/audit-boxes.md:5-20 |
| cmd:audit -> rule:closing | invokes | at the end: what is thin, then one line naming what to run next (usually the next lens or `sprint`) | audit/SKILL.md:240-244 |

### LENSES (audit)

Six lenses, cheapest-first order in a full run (order not explicitly ranked by cost in the text beyond "cheapest first" — audit/SKILL.md:25); the six named are tests, deps, scenarios, security, performance, conventions (audit/SKILL.md:64,179-180).

| lens | reference | reads | runs (tools) | writes | verdicts (own vocabulary) |
|---|---|---|---|---|---|
| tests | tests.md | `docs/knowledge/actions.md` entries, section at a time (awk pattern, audit/SKILL.md:173-175); existing test files | `commands.test` from `project.yml` once | `docs/audits/tests.md` | `covered`, `gaps`, `unjudged`, `deferred`, `declined` (SKILL.md generic 5) + own markers `unmet`, `n/a`, `(stand-in: …)` (tests.md:21-61) |
| deps | deps.md | manifests (`composer.json`/`package.json`/etc, implied) | `composer outdated`, `composer audit`, `npm outdated`, `npm audit`, `pip list --outdated`, "whatever the stack has" | `docs/audits/deps.md` | generic 5 (`covered` etc.); findings ordered reachable-vuln → unreachable-vuln → EOL → major-behind |
| scenarios | scenarios.md | `docs/knowledge/scenarios.md` every scenario; code (routes, templates, controllers) for citations | project's own end-to-end suite, if any | `docs/audits/scenarios.md`; also a note in `docs/technical_debt.md` when a step cannot live in a test | own 3: `walks`, `breaks at step N`, `unfollowable` |
| security | security.md | every entry in `docs/knowledge/actions.md` (in/out table with reason); each entry's "must never" lines | `/security-review` on risky-action files; manual check of tracked files for committed secrets | `docs/audits/security.md` | generic 5 |
| performance | performance.md | `docs/knowledge/stack.md` + framework docs (to build catalogue); code (fetch site + every consumer) | no external tool named; optional: quotes existing profiler/query-counter/debug-bar/tracer output if the project has one | `docs/audits/performance.md` | generic 5 |
| conventions | conventions.md | `docs/knowledge/stack.md`, every rule | none named; direct code reading | `docs/audits/conventions.md` | generic 5 |

Order within a lens (all lenses): mechanical pass → per-line search with citation → interpret for this project → area by area, writing as each area finishes → group findings into batches (units of work for `ship`) → write+commit before moving to next lens. (audit/SKILL.md:87-113)

Cross-lens ordering: full run does baseline once, then each lens in turn, each writing+committing its own file before the next starts (audit/SKILL.md:70-77,112-113,183-184).

### IO TABLE (audit)

| Path / command | Read by | Written by | Format/notes |
|---|---|---|---|
| `docs/audits/<lens>.md` | `sprint`, `epic`, `next`, `accept`, and the lens itself (next run) | that lens | rewritten whole each run; header `<!-- agent-kit:audit lens=X walked=N ...=N ... -->`; sections by area, "Covered", "Also noticed"; boxes `- [ ]`/`- [x]` | audit/SKILL.md:144-230; rules/channels.md:40 |
| `docs/audits/baseline.md` | implied same readers | the baseline check (belongs to no lens) | audit/SKILL.md:74-86 |
| `docs/knowledge/actions.md`, `scenarios.md`, `stack.md` | audit lenses (read-only) | never by audit | audit/SKILL.md:10-16 |
| `project.yml` → `commands.test` | tests lens | never | audit/references/tests.md:5-6 |
| `docs/technical_debt.md` | scenarios lens writes an item (harness/exception); other lenses reference it via `next`/`sprint` downstream | scenarios lens (append only) | audit/references/scenarios.md:70-73 |
| `.agent-kit/runs/<slug>/run.json` (`--run` mode) | audit session | audit session (`step:"done"`, `notes`) | audit/SKILL.md:38-60 |
| `docs(audits): …` git commit | git history | the lens, per file | audit/SKILL.md:112-113 |
| `check.py --status` output | audit session isn't shown reading this directly in SKILL.md, but `check_audits`/`print_audits` (check.py) consume `docs/audits/*.md` tallies for other commands | n/a | check.py:2252-2311,3388-3392 |

### OWNER GATES (audit)

- **Clarify gate**: if the typed argument is not clearly a lens/area, audit stops before doing anything and asks (via prose, per SKILL.md — not explicitly routed through `rules/asking.md`), printing the lens list plus the one worth clarifying (area). audit/SKILL.md:31-33.
- **Free-text mapping**: `audit "why is X slow"` — must state in one line what was understood, then start (no owner round-trip required beyond that statement). audit/SKILL.md:29.
- No decision round exists otherwise — audit is described as "Reads and reports; never changes code," (SKILL.md:3) with no owner interview at the end (contrast with `advise`).

### REFUSALS AND EXITS (audit)

- **Changes nothing but its own work list** — not code, not tests, not the knowledge. audit/SKILL.md:13-16.
- **No verification pass** — a second agent re-checking the first is explicitly forbidden as a shape (doubles cost). audit/SKILL.md:158-159.
- **Does not attempt an exploit** in the security lens — citation is the evidence; "a lens that changes state to prove a point has stopped being a lens." audit/references/security.md:53-54.
- **Does not write end-to-end tests** the scenarios lens wants — that's a `ship` run, not the lens's job; it only names the need in the work list. audit/references/scenarios.md:91-95.
- **tests lens never fixes a red suite** — reports the result, never fixes it. audit/references/tests.md:5-6.
- **deps lens never reasons about versions itself** — must use ecosystem tooling. audit/references/deps.md:5-6.
- **conventions lens may not invent a rule the project never wrote** — not a violation of something unwritten; goes to "also noticed" instead. audit/references/conventions.md:27-30.
- **A tick in `docs/audits/*` may only be made by 3 sessions** (the batch-closing session, `next`, `accept`), never by the audit itself re-ticking arbitrarily, and never on a guess. rules/audit-boxes.md:5,12-26.
- **Untouched items in the work list stay untouched** between runs — nothing but the lens itself may rewrite the file whole, and only a tick may be added by the three sessions above. rules/audit-boxes.md:43-46.
- **Never truncates** the work list / never caps scope silently — completeness is stated, sorted, not capped. audit/SKILL.md:229,235-238.
- **As a batch child, the audit does not ask anything** ("nobody is present, so nothing is asked") — doubtful items are written down as-is. audit/SKILL.md:42-43.

---

## Command: advise

### NODES

| id | kind | label | description | source |
|---|---|---|---|---|
| cmd:advise | cmd | advise | Proposes where the product/code/money is weak or could grow; owner decides in one round at the end; writes what they accept. | advise/SKILL.md:8-22 |
| phase:advise.preflight | phase | preflight check | Runs `check.py --status` once for the four exclusion lists and knowledge gaps; findings are *not* a reason to stop. | advise/SKILL.md:42-70 |
| phase:advise.dispatch | phase | invocation dispatch | Parses typed args into lens (+area), or stops to clarify. | advise/SKILL.md:24-40 |
| gate:advise.clarify | gate | clarify before starting | If first word isn't a lens/clearly about one, stop, print the three lenses, ask the one clarification (area). | advise/SKILL.md:37-38 |
| lens:product | lens | product | Close half: scenarios+actions failure walk. Wide half: domain reading, adjacent audience, what to remove. | advise/references/product.md |
| lens:code | lens | code | Close half: actions/mechanisms at volume vs `stack.md`+`product.md` numbers. Wide half: data-loss/lying paths, dev feedback loop. | advise/references/code.md |
| lens:money | lens | money | Close half: what costs money without reason / what could charge and doesn't. Wide half: market pricing, what to drop. | advise/references/money.md |
| phase:advise.closehalf | phase | close half | Walks files, complete list, every row gets `covered`/`gaps→proposal`/`unjudged`, tagged `from the files`. | advise/SKILL.md:73,89-90 |
| phase:advise.widehalf | phase | wide half | Domain judgement + optional research; ends in "considered and rejected"; tagged `from the domain`/`from research`. | advise/SKILL.md:73,91-93 |
| file:advice.lens | file | `docs/advice/<lens>.md` | The lens's report — one file per lens, rewritten whole each run. | advise/SKILL.md:130-158 |
| phase:advise.closing | phase | closing round | Puts rows to the owner per `rules/asking.md`; three possible answers per row. | advise/SKILL.md:169-271 |
| rule:asking | rule | asking.md | Governs how the closing round is asked (choices, recommendation first, batched). | rules/asking.md:1-90 |
| rule:knowledge-writing | rule | knowledge-writing.md | Governs how an accepted "changes the product" row is written into `docs/knowledge/`. | rules/knowledge-writing.md:1-86 |
| rule:pull-requests | rule | pull-requests.md | Governs the one PR opened after the round. | rules/pull-requests.md:1-120 |
| rule:closing-shared | rule | closing.md | Shared "say what's thin, name next command" ending. | advise/SKILL.md:273-281 |
| file:knowledge.entry | file | `docs/knowledge/<slot>.md` entry | Written for "accepted, changes the product/code" rows: `state: planned`, full fields. | advise/SKILL.md:174-201 |
| file:technical_debt | file | `docs/technical_debt.md` | Written for "accepted, work under rules that already hold" rows. | advise/SKILL.md:203-208 |
| file:advice.block | file | `[accepted …]` block | Written when owner said yes but the fields weren't finished in the round ("nobody in the room" fallback / tired partway). | advise/SKILL.md:262-271 |
| session:advise.round | session | the closing-round session | Branches `docs/advise-<date>` off default branch, one commit per item, opens one PR at the end. | advise/SKILL.md:230-260 |
| ext:web-research | ext | web search | Used for the "from research" tag in each lens's wide half — briefed only after the domain reading is written. | advise/SKILL.md:101-102; product.md/code.md/money.md "What research is for here" sections |
| agent:advise-lens-subagent | agent | per-lens subagent | Implied by "every lens, `product` first, each writing its file as it finishes" (analogous to audit's full-run isolation, not explicitly stated as subagent in advise/SKILL.md — see UNCERTAIN). | advise/SKILL.md:28 |
| cmd:blueprint | cmd | blueprint (external) | Reads `[accepted …]` blocks and finishes them into full entries; also the target named when advise finds nothing written at all. | advise/SKILL.md:60,269-271; blueprint/references/blocks.md:18 |
| cmd:next | cmd | next (external) | Raises `[accepted …]` blocks (per rules/channels.md); reads `docs/advice/*` implicitly? (see IO table). | rules/channels.md:33 |

### EDGES

| from | to | mechanism | trigger/condition | source |
|---|---|---|---|---|
| cmd:advise -> phase:advise.preflight | invokes | always, once | advise/SKILL.md:44-47 |
| phase:advise.preflight -> script:check.py | invokes | `python3 check.py . --status` | advise/SKILL.md:47 |
| phase:advise.preflight -> gate:advise.clarify | blocks | if nothing written at all in knowledge — says so, names `blueprint` instead of running | advise/SKILL.md:60 |
| cmd:advise -> gate:advise.clarify | invokes | first word not a recognised lens/clearly about one | advise/SKILL.md:37-38 |
| cmd:advise -> lens:product | delegates | full run (product first) or `advise product` | advise/SKILL.md:26-33 |
| cmd:advise -> lens:code | delegates | full run or `advise code` | same |
| cmd:advise -> lens:money | delegates | full run or `advise money` | same |
| lens:product -> file:knowledge.scenarios | reads | close half | advise/SKILL.md:56 |
| lens:product -> file:knowledge.actions | reads | close half | advise/SKILL.md:56 |
| lens:product -> file:knowledge.product | reads | wide half | advise/SKILL.md:57 |
| lens:product -> file:knowledge.actors | reads | wide half | advise/SKILL.md:57 |
| lens:code -> file:knowledge.stack | reads | advise/SKILL.md:57 |
| lens:code -> file:knowledge.product | reads | volumes stated there | code.md:5 |
| lens:money -> file:knowledge.product | reads | usually finds nothing written — that is itself a finding | advise/SKILL.md:57-58; money.md:7 |
| lens:* -> file:advice.lens(old) | reads | "the previous `docs/advice/<lens>.md` is read before anything is proposed" | advise/SKILL.md:98-99 |
| lens:* -> file:knowledge.planned-entries | reads | exclusion list 1: `planned` entries not re-proposed | advise/SKILL.md:110-111 |
| lens:* -> file:audits.any | reads | exclusion list 2: open boxes in `docs/audits/*` | advise/SKILL.md:112-113 |
| lens:* -> file:technical_debt | reads | exclusion list 3 | advise/SKILL.md:114 |
| lens:* -> file:advice.lens(old) | reads | exclusion list 4 (same as ordering rule) | advise/SKILL.md:114 |
| lens:* -> file:knowledge.product-nongoals | reads | exclusion list 5: "what it deliberately does not do" in `product.md` — read before the wide half, always | advise/SKILL.md:120-126 |
| lens:widehalf -> ext:web-research | invokes | briefed only after the domain reading is written down | advise/SKILL.md:100-102 |
| phase:advise.closehalf -> phase:advise.widehalf | loops-to | sequencing order within a lens (order not fully explicit but domain-reading-before-research is stated) | advise/SKILL.md:100-102 |
| lens:* -> file:advice.lens | writes | `docs/advice/<lens>.md`, rewritten whole | advise/SKILL.md:130-158 |
| cmd:advise -> phase:advise.closing | invokes | after all requested lenses' reports are written | advise/SKILL.md:169 |
| phase:advise.closing -> rule:asking | invokes | put rows to owner: options, recommendation first, everything independent batched | advise/SKILL.md:171 |
| owner -> phase:advise.closing | returns-to (answers) | 3 possible answers per row: accepted-changes-product/code, accepted-is-debt-work, declined/not-now | advise/SKILL.md:174-224 |
| phase:advise.closing -> file:knowledge.entry | writes | "accepted, changes what the product/code is held to" — full entry, `state: planned`, this round, via rule:knowledge-writing | advise/SKILL.md:174-201 |
| phase:advise.closing -> file:technical_debt | writes | "accepted, work under rules that already hold" — one line, that file's format | advise/SKILL.md:203-208 |
| phase:advise.closing -> file:advice.lens | writes | "declined, or not now" — a line, never a block; declined rows never raised again, not-now rows carried forward as open | advise/SKILL.md:212-224 |
| phase:advise.closing -> file:advice.block | writes | "[accepted …]" written only when owner said yes but fields left for later / round ended partway | advise/SKILL.md:262-271 |
| phase:advise.closing -> session:advise.round | hands-off | branch `docs/advise-<date>` off default branch (never the checked-out branch), one commit per item as settled | advise/SKILL.md:230-235 |
| session:advise.round -> rule:pull-requests | invokes | one PR for the round, opened after the round, per pull-requests.md | advise/SKILL.md:237-260 |
| session:advise.round -> git | writes | PR sections: What & why, Manual actions ("None."), Assumptions (every derived field), Changes (slot table) | advise/SKILL.md:243-251 |
| cmd:advise -> rule:closing-shared | invokes | ending: what's thin, then next-command line | advise/SKILL.md:273-281 |
| rule:closing-shared -> owner | hands-off | if the round wrote anything: "merge the pull request" (nothing downstream sees the entry until then); else next lens or `blueprint` if blocks left | advise/SKILL.md:279-281 |
| file:advice.block -> cmd:blueprint | hands-off | `[accepted …]` block is finished by `blueprint` later | advise/SKILL.md:271; blueprint/references/blocks.md:18,29-31 |
| file:advice.block -> cmd:next | reads | `next` raises the `[accepted …]` block per rules/channels.md:33 | rules/channels.md:33 |

### LENSES (advise)

Three lenses, `product` first in a full run (advise/SKILL.md:28).

| lens | reference | close half reads | wide half proposes from | writes | research target |
|---|---|---|---|---|---|
| product | product.md | every scenario, every action | domain reading (5-7 lines) written before proposals; adjacent audience; what to remove | `docs/advice/product.md` | live products in the space, what people dislike (reviews/forums), what changed this year, regulation/seasonality — link+date every row |
| code | code.md | every action that reads/writes at volume, every homegrown mechanism, vs `stack.md` + `product.md` volumes | data-loss/lying paths, dev feedback loop | `docs/advice/code.md` | current majors of the stack, known traps, ecosystem's standard answer for the homegrown piece — link+date |
| money | money.md | every action/integration that costs money to serve | market pricing/what audience would pay; what running cost dominates at stated volumes; what to drop | `docs/advice/money.md` | what products in this space charge/how packaged; current published prices of services this project runs on — link+date |

Each lens's own internal ordering:
1. Close half — every scenario/action/mechanism gets a row: proposal / `clean` / `unjudged` (with reason). Never truncated. (advise/SKILL.md:89-90)
2. Wide half — domain reading written first, then research briefed from it, then proposals; ends in "considered and rejected" section. (advise/SKILL.md:91-93,98-102)
3. Every row tagged `from the files` / `from the domain` / `from research`. (advise/SKILL.md:78-86)
4. Filtered against the 5 exclusion lists before reaching the report. (advise/SKILL.md:106-126)
5. Report written, **then** the closing round. (advise/SKILL.md:104)

Full-run cross-lens order: `product` first, each lens writing its own file as it finishes (advise/SKILL.md:28) — i.e. sequential, not explicitly stated as parallel/subagent-isolated (see UNCERTAIN).

### IO TABLE (advise)

| Path / command | Read by | Written by | Format/notes |
|---|---|---|---|
| `docs/advice/<lens>.md` | next run of same lens; `next` and `sprint`/etc are NOT listed as readers of this file directly in channels.md (only "the next run of the same lens") | that lens; the closing round (adds declined/not-now lines) | rewritten whole per run; sections: small-edits-first (product only), close-half findings, wide-half findings, "Рассмотрел и отклонил" (considered & rejected), "Отклонено раньше" (declined earlier), "Чего я не вижу" (blind spot: domain knowledge + 3 questions) | advise/SKILL.md:130-167; rules/channels.md:43 |
| `docs/knowledge/<slot>.md` entries | every command; `check.py` | `blueprint` and `advise` (with owner present) | full entry, `state: planned`, one commit per slot | advise/SKILL.md:179-201; rules/knowledge-writing.md |
| `docs/technical_debt.md` | `check.py`, `sprint`, `next`; closed by whoever does the work | `advise` closing round (and `ship`, closing session, `blueprint`) | one line, that file's own `·`-separated format | advise/SKILL.md:203-208; templates/technical_debt.md |
| `[accepted …]` block under a slot | `next` (raises it); finished by `blueprint` | `advise` | carries proposal, why accepted, date, source row | advise/SKILL.md:262-271; rules/channels.md:33; blueprint/references/blocks.md:18,29-31 |
| `docs/advise-<date>` branch | reviewer/owner via PR | the closing round | branched off default branch, never the checked-out one | advise/SKILL.md:230-235 |
| PR opened by the round | owner (merges) | closing round session | per rules/pull-requests.md; sections What&why / Manual actions / Assumptions / Changes | advise/SKILL.md:237-260 |
| `python3 check.py . --status` | advise (preflight) | n/a | prints the 4 lists + knowledge gaps | advise/SKILL.md:47 |

### OWNER GATES (advise)

- **Preflight is never a stop condition** for advise (unlike every build command) — thin knowledge is advise's subject matter; it names each gap, runs the halves that don't need it, never invents. advise/SKILL.md:50-54.
- **Clean-tree requirement before the closing round** — because that round commits into `docs/knowledge/`; checked at closing time, not at start. advise/SKILL.md:62-64.
- **Branch note** — advise notes (and reports) which branch it's on if not the default one; purely informational, changes nothing about where writing lands. advise/SKILL.md:66-69.
- **The closing round itself** — the central owner gate. Per row, three possible answers (rules/asking.md style: options, recommendation first, batched):
  1. **Accepted, changes product/code** → full entry written now, complete, `state: planned`, in `docs/knowledge/`, one commit/slot, via rule:knowledge-writing. Two extra required questions not part of the entry's own fields: (a) which scenario covers it (existing gains a step, or a new scenario written) — required because `epic` stops on "every scenario inside the bounds passes"; (b) inside or outside MVP bounds — required because `epic` reads those bounds to know where to stop. Both "fail silently if skipped." advise/SKILL.md:174-201.
  2. **Accepted, work under rules that already hold** → one line in `docs/technical_debt.md`. Fork test: "does this change a rule, or follow one?" advise/SKILL.md:203-210.
  3. **Declined, or not now** → a line in `docs/advice/<lens>.md` (never a block). Declined = never raised again by this lens; not-now = stays open, carried forward as open next run, not presented as new. advise/SKILL.md:212-224.
  - **"All or nothing, per item"** for the knowledge-entry case: a field with no answer means the item does not become an entry — it becomes an `[accepted …]` block instead. advise/SKILL.md:186-190.
  - **Nobody in the room** → write the list and stop; nothing accepted, nothing written; closing line says the round is outstanding. advise/SKILL.md:262-267.
  - **`[accepted …]` fallback** written only when owner said yes but round left fields for later / tired partway — carries proposal, reason accepted, date, source row; `blueprint` finishes it. advise/SKILL.md:269-271.
- **Considered-and-rejected section is mandatory in every wide half** — without it, 5 proposals can't be told apart from a walk that stopped after 5. advise/SKILL.md:91-93.
- **Blind-spot statement mandatory every run**: what is known about the domain and from where; 3 questions whose answers would change the list; unresearched rows marked as such if no network/no results. advise/SKILL.md:162-167.

### REFUSALS AND EXITS (advise)

- **Changes no code and no tests, and decides nothing about the product** — writes only its own list, plus (for accepted rows) what the owner answered. advise/SKILL.md:21-22.
- **Never fills a thin-knowledge gap by invention** — names it, runs the parts that don't need it. advise/SKILL.md:53-54.
- **Nothing raised that was already decided** — 5 exclusion lists (planned entries, open audit boxes, technical_debt.md, previous docs/advice/<lens>.md, product.md non-goals). A restatement of any of these is not raised as a proposal (may be raised once as a "priority remark", explicitly marked as different from a proposal). advise/SKILL.md:106-118.
- **Reopening a `product.md` exclusion requires quoting the recorded reason and saying what changed** — no answer to "what changed" and the exclusion stands. advise/SKILL.md:120-126.
- **A stance recorded in `stack.md` is not written by advise alone in the closing round** — actually it is written there too (money.md / code.md fork), but must be the "changes a rule" branch, going into `stack.md` "the same way" as an entry (two lines). advise/code.md:55-57; money.md:38-40.
- **A revenue/pricing proposal that makes the product "meaningfully worse to use" is not a proposal in money's wide half** — must say so in the row instead. advise/references/money.md:30.
- **A proposal without a number/amount is not a proposal** in code and money close halves — becomes an `unjudged` row carrying the question instead of a guess. advise/references/code.md:13; money.md:13.
- **A proposal that can't fill the "three lines" shape (who / what they do instead / what changes) in product's wide half goes to "considered and rejected."** advise/references/product.md:45.
- **A rewrite-shaped proposal (no migration path in pieces) must be plainly labelled "a rewrite."** advise/references/code.md:45.
- **Does not copy blueprint's commit rule** (onto checked-out branch, no PR) — explicitly told not to; advise's round always branches fresh and always opens a PR because the owner answered fast (one-line yes), unlike blueprint's slow dictation. advise/SKILL.md:257-260.
- **The entries in the round's PR are invisible to `ship`/`sprint` until it merges** — must be said in the closing line. advise/SKILL.md:253-255,279-281.

---

## CROSS-COMMAND

- **Both commands share `rules/closing.md`** for their final report shape (what's thin, one line naming what to run next). audit/SKILL.md:240-244; advise/SKILL.md:273-281.
- **Both are "errand" kind** in `runfile.py`'s `BY_COMMAND` map (`"audit": "errand", "advise": "errand"`) — distinct from `feature`/`batch`/`epic`, meaning no suite of its own from the driver's point of view. runfile.py:53-54.
- **`docs/audits/*` and `docs/advice/*` are structurally parallel channels**: one file per lens, rewritten whole by that lens on its next run, both defended by a "read the previous file before writing" rule, both excluded from re-proposing declined/settled items. audit/SKILL.md:219-221; advise/SKILL.md:98-99,114.
- **`docs/audits/*` boxes are machine-tallied** (`agent-kit:audit lens=… walked=…` comment, checked for arithmetic by `check_audits` in check.py:2252-2311) — **`docs/advice/*` is not tallied**, only checked for stray filenames (`check_advice`, check.py:2317-2333) since "advise proposes rather than counts."
- **`audit` feeds `epic`'s finish line directly**: `epic`'s `auditing` phase spawns lenses as batch children (`/agent-kit:audit <lens> --run <dir>`), narrowed to `entries` per-wave, capped at 3 waves, and `finish.lenses` is chosen by the `--advance` reaching the audit (not the gate). epic/references/finish.md:1-72; epic/SKILL.md:217-222,314-315,346.
- **`audit`'s output feeds `sprint`/`next`**: `sprint` with no theme offers the audits' unticked boxes as one of 4 debt sources; `next` rung 8/9 recommends `/agent-kit:audit <lens>` for a stale/never-run lens and rung 9 folds unticked audit boxes into "debt, unkept promises...". sprint/SKILL.md:91-116; next/SKILL.md:150-151.
- **`advise`'s output feeds `blueprint`** (finishing `[accepted …]` blocks into full entries) and **`next`** (raising the block). advise/SKILL.md:269-271; rules/channels.md:33; blueprint/references/blocks.md:18,29-31.
- **Ticking an audit box is restricted to exactly 3 sessions kit-wide**: the batch-closing session, `next`, `accept` — governed by `rules/audit-boxes.md`, cross-checked by `check.py`'s `check_channels` (blind ticks with no PR number flagged as drift). rules/audit-boxes.md:5-6; check.py:2225-2247.
- **`docs/technical_debt.md` is a shared sink** written by `ship`/closing sessions, `blueprint` (owner-reported), and `advise`'s closing round (the "follows a rule" fork) — one ledger format for all writers. templates/technical_debt.md:1-53; advise/SKILL.md:203-210.
- **check.py's `--status`** prints both `audits: <lens> <date> (<n> open)` per lens (from `audit_lenses()`) and is the one preflight command advise runs; audit itself does not appear to invoke `check.py --status` explicitly in its own SKILL.md (see UNCERTAIN below) though its work-list tallies are what that same script verifies downstream. check.py:3187-3196,3303-3309.
- **`epic`'s finish also separates lenses by scope-capability**: `tests`/`scenarios` take an area (the run's own entries); `deps`/`security`/`conventions` never take an area (project-wide properties). `performance` is not mentioned in that specific split (see UNCERTAIN). epic/references/finish.md:42-47.

## UNCERTAIN / CONTRADICTORY

1. **Does `audit`'s SKILL.md itself run `check.py --status` as a preflight?** Unlike `advise` (explicit `## Preflight` section calling `check.py . --status`, advise/SKILL.md:44-47) and unlike `sprint`/`next` (explicit calls), `audit/SKILL.md` never shows a `check.py` invocation in its own text — its only script mention is the awk-based section reader (audit/SKILL.md:173-175). The tally format it must produce (`<!-- agent-kit:audit lens=... -->`) is clearly meant to be read by `check.py`'s `check_audits`, but I found no line in `audit/SKILL.md` instructing the lens to *run* check.py before starting. This may be an intentional omission (audit doesn't touch `project.yml`-gated preflight the way build commands do, per `rules/preflight.md`'s table which lists only `ship`, `fix`, `sprint`, `epic`, `next` as commands that must not start over an in-flight run — `audit` and `blueprint`/`advise` are explicitly *not* on that stop-list, rules/preflight.md:37) — but I could not confirm audit runs `--status` at all, mechanically or as prose instruction.

2. **Is a full `advise` run's per-lens execution isolated in a subagent, the way a full `audit` run explicitly is?** `audit/SKILL.md:161-164` explicitly says "A full run gives each lens its own subagent... A single-lens run does the work inline." `advise/SKILL.md` has no equivalent sentence — it only says "every lens, `product` first, each writing its file as it finishes" (advise/SKILL.md:28). I did not find text confirming or denying subagent delegation for advise. Marked `agent:advise-lens-subagent` as inferred/uncertain in the NODES table above.

3. **performance lens's area-scoping in an epic's audit wave**: `epic/references/finish.md:42-47` explicitly splits the six lenses into "takes a scope" (`tests`, `scenarios`) and "takes no scope" (`deps`, `security`, `conventions`) but never places `performance` in either bucket. Whether `performance` is scoped by area during an epic's wave is not stated anywhere I found.

4. **Order of "cheapest first" in a full audit run** (audit/SKILL.md:25 says lenses run "cheapest first") is asserted but no explicit ordering of the six lenses by cost is given anywhere in the sector's files — I could not find which lens is considered cheapest.

5. **Whether `next` reads `docs/advice/*.md` directly.** `rules/channels.md:43` lists `docs/advice/<lens>.md`'s only reader as "the next run of the same lens." But `next/SKILL.md`'s ladder (rungs 1-11) never mentions `docs/advice/` at all — it only reads audits' work lists and technical_debt.md at rungs 8-9. So it appears advise's proposals are *not* surfaced by `next`, only the `[accepted …]` blocks that came out of a completed round are (via the entry/block mechanism, not the advice file itself). This is consistent, not contradictory, but worth flagging since it means `docs/advice/*.md` has exactly one reader in the whole kit: the same lens's own next run.

6. **Ordering guarantee "close half before wide half" is implicit, not explicit as a numbered sequence.** advise/SKILL.md's "Three orderings that are load-bearing" section (advise/SKILL.md:94-104) states three orderings (previous file read first; domain-reading before research; everything-passes-filters before report, report before closing round) but does not explicitly say "close half runs before wide half" — I inferred this from each lens reference file's own structure (## Close half then ## Wide half headings) rather than from an explicit sequencing rule in SKILL.md. Likely true but not a directly cited ordering rule.
