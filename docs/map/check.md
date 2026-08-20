# Sector: check.py

`plugins/agent-kit/scripts/check.py`, 3901 lines. Python 3.9+, standard library only.
Imports one sibling module: `runfile` (via `sys.path.insert` at check.py:48-49) for
`TERMINAL`, `BRANCH_PREFIXES`, `STEPS`, `KINDS`, `kind()`, `read()`, `runs()`,
`in_flight()`, `resume_command()`.

**It is not a subcommand CLI.** `argparse` defines one positional (`root`) and 13
boolean/valued **flags**; `main()` (check.py:3599-3897) dispatches them as a priority
chain of early returns. There are no `add_parser` calls anywhere in the file. Throughout
this document "subcommand" = "flag mode".

## CLI REFERENCE

Parser: check.py:3600-3648. Dispatch: check.py:3650-3897.

| mode | flags/args | reads | emits | exit codes | file:line |
|---|---|---|---|---|---|
| positional | `root` (nargs="?", default `"."`, type `Path`, resolved) | — | — | — | 3601, 3650 |
| `--status` | store_true | — | forces the standing/planned/parts/audits/sight/outside/where block on both clean and dirty paths | does not change code | 3602; used 3828-3839, 3846-3853 |
| `--offline` | store_true, `help=argparse.SUPPRESS` (hidden) | — | makes `gh` object `Offline` (every GitHub answer = "could not ask") | — | 3607, 3653 |
| `--sync` | store_true | knowledge + `gh pr` | rewrites `state:` lines in `docs/knowledge/*.md` for merged/closed PRs | as bare mode (0/1) | 3608, 3737 |
| `--record` | store_true | knowledge + `.agent-kit/project.yml` | rewrites `@hash` in `source:` lines and dep hashes; prints what it wrote or `"  every hash was already current"` | **always 0** | 3611, 3723-3727 |
| `--state` | store_true | git, gh, run files, audits, manifest | appends the "Work:" block | does not change code | 3614, 3842-3843 / 3892-3893 |
| `--epic` | store_true | product.md, scenarios.md, project.yml, verification.yml | `"This project cannot start an epic as it stands:"` + fatal lines | 1 if fatal, else 0 | 3617, 3729-3735 |
| `--entries` | `nargs="+"`, metavar KEY | knowledge | `"Open blocks under the N entries this command named:"` + full blocks; names keys matching nothing | does not change code (printed on both paths) | 3620, 3840-3841 / 3889-3890 |
| `--owed` | store_true | verification.yml + project.yml | the kinds a feature owes / kinds refused | **always 0** | 3624, 3664-3665 |
| `--tests` | store_true | project.yml, run files, `.github/workflows/`, verification.yml, scenarios.md | one screen about testing | **always 0** | 3627, 3667-3668 |
| `--brief` | `metavar KEY` | project.yml, knowledge, stack.md | the entry + everything it names, `====` banners | 0, or **2** if the key matches no entry (3810→`brief` 1811) | 3631, 3720-3721 |
| `--run` | `metavar DIR` (dir or `.json` path) | that run file, knowledge, git, project.yml, `docs/runs/<slug>.json`, verification.yml | `"This run cannot close as it stands (N):"` + defects; then `"Records that moved under this run (N) …"` | **2** no such file / unparseable; 1 if defects; 0 otherwise. Drift never changes it | 3634, 3670-3700 |
| `--manual` | store_true | `docs/manual.md` | runs each `proof`, **deletes** closed lines, prints Done/Still waiting/broken | **always 0** | 3637, 3661-3662 (`prove_manual` 1164-1219) |
| `--pr-base` | `metavar BASE` | git only | `"  <branch> into <base>: N commit(s), M file(s)"` + carried epic/sprint warnings | **2** not on a branch / no such base; 1 if it carries an epic/sprint; else 0 | 3641, 3655-3656 (`pr_base_defects` 3470-3528) |
| `--pr-body` | `metavar FILE` | that file | one measurement line + up to 3 budget defects | **2** missing/unreadable file; 1 if defects; else 0 | 3645, 3658-3659 (`pr_body_defects` 3531-3596) |
| bare (no mode flag) | | everything below | the full report | **0** clean, **1** any finding | 3737-3897 |

Output format is **human text on stdout, always**. There is no JSON output anywhere.
stderr is used only for the hard errors that return 2 (3674, 3679, 3487, 3496, 3556,
3561, 1811-1813, 1866).

### Dispatch order (first match wins, check.py:3655-3735)

`--pr-base` → `--pr-body` → `--manual` → `--owed` → `--tests` → `--run` →
`print_flight` (unless `--brief`/`--record`) → **early return 0 if `docs/knowledge/` is
missing** → `--brief` → `--record` → `--epic` → the full bare pipeline.

Consequences of the order:
- `--pr-base`/`--pr-body`/`--manual`/`--owed`/`--tests`/`--run` never print the
  in-flight banner (they return before check.py:3705).
- **`--epic`, `--brief` and `--entries` all sit *behind* the missing-knowledge early
  return at 3709-3714** — see SILENCE AUDIT.
- Flags of different modes do not combine: `--epic --status` runs only the epic gate.

### The bare pipeline (check.py:3737-3897)

`sync_states` → `check_fields` → `check_references` → `check_orphans` → `check_sources`
→ `check_stack` → `check_verification` → `check_commands` → `check_verdicts` →
`check_runs` → `check_batches` → `check_channels` → `check_audits` → `check_advice` →
`check_shape` → `collect_unmet` → `collect_debt` → `collect_manual` → `collect_notes`.

Then printing, in this order: `states` (3757), `unmet` (3762), `manual` (3776), `stale`
(3784), `accepted` (3792), `frame` (3800), `drift` (3808), `debt` (3811, cut at
`UNMET_SHOWN`=10), `shape` (3821). Then the clean/dirty fork at 3827.

`Report.clean` is `not self.groups` (check.py:306-308) — i.e. **only `report.add(group,
line)` findings decide the exit code**, plus `report.notes` and `report.assumed`
(3827). Everything in `states/unmet/manual/stale/accepted/frame/drift/debt/shape/sight/audits`
is advisory.

## PER-SUBCOMMAND DETAIL

### bare / `--status` / `--state` / `--sync` / `--entries` — the report

Report buckets (class `Report`, check.py:284-308):

| bucket | blocking? | printed where |
|---|---|---|
| `groups` (`add()`) | **BLOCKING** — sets exit 1 | 3855-3858, grouped by name |
| `notes` (`[found …]` and any unknown note kind) | **BLOCKING** (3827) | 3884-3887 |
| `assumed` (`[assumed …]`) | **BLOCKING** (3827) | 3864-3882, names entries only |
| `states` | advisory | 3757 |
| `unmet` | advisory, **never truncated** (3762-3771) | 3762 |
| `manual` | advisory | 3776 |
| `stale`, `accepted`, `frame` | advisory statements | 3784/3792/3800 |
| `drift` | advisory | 3808 |
| `debt` | advisory, cut to 10 | 3811 |
| `shape` | advisory | 3821 |
| `sight` | advisory, **only under `--status`/`--state`** | `sight_lines` 3090-3104, called 3834/3852 |
| `audits` | advisory, **only under `--status`** | `print_audits` 3388-3393, called 3832/3849 |

Group names used with `report.add` (these are the blocking findings):

- **`Fields`** — `check_fields` 309-319: `"<file>:<line> <key> — <field>, <field>"` for
  fields declared by the file's own `fields:` line and left empty.
- **`References`** — `check_references` 326-346: `"… <key> — no actor 'x'"`;
  `"… <key> → <ref> is not defined anywhere"` (only when `ref`'s first segment is a
  declared actor or it starts with `screen.`).
- **`Orphans`** — `check_orphans` 349-373: `"actors.md:<line> <key> — no action belongs
  to this actor"`; `"<file>:<line> <key> — named nowhere else"` (entities/screens,
  suppressed by `` `entry_point` `` 112).
- **`Sources`** — `check_sources` 393-442: `"→ <path> does not exist"`; `"→ <path>#<h>
  — no such heading"`; `"→ <path>#<h> changed (<old> → <new>)"`; `"N source hashes
  predate this program and mean nothing …"`; `"→ \`source:…\` is not a source line this
  program can read …"`. A `source:` pointing at http(s) goes to `report.drift` instead
  (438-442). Main adds a hint at 3860-3863 when >2 sources all say "changed".
- **`Stack`** — `check_stack` 815-840: `"<manifest> is recorded but missing"`;
  `"<manifest> changed since the library map was written"`; `"researched <date> — over
  six months ago"`; `"stack_researched is not a date: …"`; `"<name> is a dependency
  manifest that project.yml does not record"`.
- **`Commands`** — `check_commands` 1005-1016: ``"`commands.<name>: <cmd>` — <defect>"``
  where `<defect>` comes from `command_defect` (971-1003): `"nothing is at <tool>"`,
  ``"`<tool>` is not on the PATH here"``, ``"`make` has no makefile in this project"``.
- **`Verdicts`** — `check_verdicts` 1018-1026: for each of `SLOTS` (137):
  `"<slot> — no verdict in project.yml"` or `"<slot> — open question"`.
- **`Runs`** — `check_runs` 1915-1978: `"run file(s) nothing can parse (N): … — the run
  they belong to has lost its memory …"`. (The stray-key and prose-field results from
  the same function go to `drift`, not `groups`.)
- **`Audits`** — `check_audits` 2252-2315: `"<file> counts nothing as \`walked\`"`;
  `"<file> says it walked N and accounts for M (…)"`.
- **`MVP`** — `check_epic` 924. **Dead**: see UNCERTAIN.

Advisory statement producers:

- `sync_states` 1440-1499 → `report.states` and (on unreadable PR) group `States`
  (blocking, 1462). Lines: `"<key>: pull request N has merged/closed, and the line still
  says building"`; after `--sync`: `"<key>: building (pr: N) → built|planned"`, or the
  "was not moved — nothing in <file> matched it as a state line" line at 1485-1489.
- `collect_unmet` 1028-1060 → `report.unmet`: `"<path>:<n> <key>"`, `"<path>:<n> — no
  entry named beside the mark"`, `"<path>:<n> <key> — no such entry"`, plus
  `"project.yml has no tests.unmet — what keeps such a test green here"`.
- `collect_debt` 1062-1079 → `report.debt`: `"docs/technical_debt.md:<n> <text[:96]>"`
  for `- [ ]` lines outside fences.
- `collect_manual` 1132-1162 → `report.manual`: `"docs/manual.md:<n> <what[:96]>"`, cut
  at 10, plus `"(N more wait for a release this project has not reached)"` and the
  `"N of M carry no command that would prove them done"` line.
- `collect_notes` 1255-1290 → routes `[assumed]`→`assumed`, `[stale]`→`stale`,
  `[accepted]`→`accepted`, `[frame]`→`frame`, `[found]`/anything else→`notes`. Shape:
  `"[<kind><tail>] <where>: <text[:90]>"`.
- `check_runs`/`check_batches`/`check_channels`/`check_audits`/`check_advice`/
  `check_sources`/`check_shape` also fill `drift` and `shape` — see IO.
- `check_verification` 676-776 + `check_reviewed` 778-813 → **all into `report.sight`**,
  which prints only under `--status`/`--state`.

`--entries` (`print_entry_blocks` 3426-3467) prints the full quoted body of every
`assumed`/`notes`/`stale` block under each named key, `"  <key>: none"` when there are
none, and a loud `"Not an entry in this project's knowledge (N): …"` trailer.

Trailer on the exit-1 path (3894-3896): `"Not checked here: whether an answer is any
good, whether a status an action sets is one the entity declares, and anything that
needs the code read."`

### `--epic` (gate) — `check_epic` 849-928

**The one place the program blocks a command.** Fatal list:

1. `"product.md has no MVP bounds section, and no <!-- agent-kit:mvp-bounds --> marker
   above one …"` (871-875) — via `bounds_section` 1537-1550 (marker first, then a
   heading containing "MVP", then literal "MVP bounds").
2. `"the MVP bounds are not two lists …"` when fewer than two `**Label:**` lines carry
   >3 characters (877-881).
3. `"no scenarios are described …"` when `scenarios.md` has no `###` heading outside
   HTML comments (883-887).
4. `"project.yml has no \`commands.run|test\` …"` and ``"`commands.<n>: <cmd>` says how
   to <what>, and <defect>"`` (889-901).
5. `"<verification.yml> could not be read …"` when `catalogue()` is empty (908-911).
6. `"nobody has answered what this project checks itself for: …"` from `unanswered`
   (641-674) — a kind with no answer, an undated or unreasoned refusal, a refusal of a
   `skip_when: never` kind, a `NOT_A_COMMAND` word (633), or a command that cannot start.

Exit 1 if any, else 0, printed under `"This project cannot start an epic as it stands:"`.

### `--run` — `run_defects` 2338-2752 + `entry_drift` 2754-2821

Reads `<dir>/run.json` (or the `.json` path given). Non-dict JSON is coerced to `{}`
(3682). `run_defects(state, root)` findings, in file order:

- **kind unknown, only at `step == "queued"`** (2379-2387): `"nothing here can tell what
  kind of run this is — …"`. Kind comes from `runfile.kind`, never from `bool(prompt)`.
- **`prompt`, only at `queued`** (2395-2412): not starting with `/`; longer than
  `PROMPT_MAX`=400; matching `PINNED_PLUGIN` (a versioned plugin path).
- **`handoff`** (2414-2428): over `HANDOFF_MAX`=2000; empty `approach`; empty `tasks`.
- **`entries`** (2443-2464): no `docs/knowledge/`; keys matching no entry, with
  `difflib` near-misses at cutoff 0.8.
- **`branch`/`base`** (2477-2500, only inside a git repo): a `branch` that resolves to
  nothing and has no `/` (a slug); an in-flight `branch`/`base` that does not exist.
- **`tasks`/`assumptions`/`manual` written as sentences** (2508-2514).
- **`assumptions` not a list** (2528-2533); **`expensive` unanswered** (2537-2552);
  **`expensive` neither true nor false** (2553-2557).
- **done tasks with no `commit`** (2568-2573) and **a `commit` this repo does not
  have** (2574-2581).

Everything below returns early unless `step == "done"` (2583):

- **review findings written as prose** (2585-2593); **an open critical/major finding**
  (2594-2600).
- **`suite` empty** (2602-2608) — features only.
- **`proved_at`** (2610-2643) — features only, and only when `command in ("ship","fix")`:
  missing; not a commit here; not an ancestor of `branch`.
- **`mutation`** (2645-2665) — only when `commands.mutate` is declared.
- **`verified`** (2667-2731) — `catalogue_defects()` echoed first (2670-2672), then: not
  a list; kinds silent; records with neither `result` nor `why`; a `skip_when: never`
  kind excused with `why`; a `result` with no `command`.
- **`pr` empty on `deliver == "pr"`** (2733-2737).
- **the batch's durable record** (2739-2751) — only `command == "sprint"`: file never
  written / unparseable / not a record, else `batch_defects` (1994-2096), which judges
  `slug/command/pr/branches/spent`, `pr` wholeness, `spent.{hours,features,sessions}`,
  the four string lists, `parked ⊄ branches`, `children/assumptions/unmet` numbers, and
  `debt/review/per_feature` numeric maps.

Then `entry_drift` (2754-2821) prints a separate, **non-blocking** section: entries
whose text moved on the default branch since the run branched, or an explicit statement
that the comparison could not run ("no default branch", "nothing common between X and
Y", "<file> is not on <base>").

Blocking: exit 1 on defects only. Drift is a statement (3695-3699 comment).

### `--manual` — `prove_manual` 1164-1219

The only place the program executes something a run wrote. `subprocess.run(proof,
shell=True, cwd=root, timeout=60)` (1189-1191) — deliberately not through `ran`.
Exit 0 = the proof's work has happened → its line range (`first..last`) is **deleted
from `docs/manual.md`** and the file is rewritten (1200-1207). Exit 127 = "no such
command on this machine" → reported, line kept. Any other non-zero = "not yet", silently
kept. Always returns 0.

### `--owed` — `print_owed` 2985-3025

Joins `verification.yml` (`runs: feature`) against `project.yml` answers. Prints the
owed kinds with their command (marking the five with a home in `commands` as "recorded
in its own field, not in `verified`") and the refused ones. Always 0.

### `--tests` — `print_tests` 2948-2983

One screen: each key of `WHO_RUNS` (2851-2860: test/lint/types/mutate/e2e/run) with its
declared command, who runs it and when, `last_ran` (2918-2946, from run files' `proved_at`
and `mutation`), and `outside_a_session` (2899-2916, four answers). Then scenarios,
`print_answers` (3059-3088), `print_outside` (3027-3057), and the "Not here: what each of
these costs" line. Always 0.

### `--brief KEY` — `brief` 1794-1866

Prints `.agent-kit/project.yml`, the entry's own body, each entry it names in backticks
that the knowledge defines, and `stack.md`; then a `== pulled in:` boundary line, a
`== named by this entry and defined nowhere …` line, and a stderr `not found, and read
nowhere else:` line for absent sections. Exit 2 with a "did you mean" list when the key
is unknown.

### `--record` — `record` 1590-1644

Rewrites `@hash` in every `SOURCE_RE` match whose target file and heading resolve, and
every 4-space-indented `name: hash` under `project.yml` (1637-1643). Prints one line per
rewrite or `"  every hash was already current"`. Always 0. **Writes `project.yml`
unconditionally at 1643**, even when nothing changed.

### `--pr-base BASE` — `pr_base_defects` 3470-3528

Prints `"  <branch> into <base>: N commit(s), M file(s)"`, then for any
`epic/*`/`sprint/*` ref that is an ancestor of HEAD and not of the base:
`"  it also carries <name> — N commit(s) the base does not have. …"`. Exit 1 if any.

### `--pr-body FILE` — `pr_body_defects` 3531-3596

Strips `<details>…</details>`, measures total / uncollapsed / brief (everything above the
first `##`) / longest table run minus 2. Budgets: `PR_BRIEF_MAX`=2500, `PR_OPEN_MAX`=4000,
`PR_TABLE_MAX`=15 (check.py:75-77). Exit 1 if any budget is over.

### Blocking vs advisory — how a caller tells

**Only by the exit code.** There is no marker in the text. Exit 1 modes: bare (`groups`
or `notes` or `assumed` non-empty), `--epic`, `--run`, `--pr-base`, `--pr-body`.
Always-0 modes: `--record`, `--manual`, `--owed`, `--tests`. Exit 2 = "this program could
not read what you pointed it at" and is always accompanied by a stderr line.

Advisory content is separated by *where it prints*: `sight`/`audits` need
`--status`/`--state`; `unmet`/`manual`/`drift`/`stale`/`accepted`/`frame`/`debt`/`shape`
print always but never change the code.

## CALLERS

Every `check.py` invocation in the payload. `$P` = `${CLAUDE_PLUGIN_ROOT}`.

| caller (command + step) | exact command line | call site |
|---|---|---|
| `blueprint` — `--check` invocation | `python3 "$P/scripts/check.py" . --status --sync` | plugins/agent-kit/skills/blueprint/SKILL.md:35 |
| `blueprint` — before any of it, always | `python3 "$P/scripts/check.py" . --status` | skills/blueprint/SKILL.md:53 |
| `blueprint` / knowledge writing — recording hashes | `python3 "$P/scripts/check.py" . --record` | rules/knowledge-writing.md:53 |
| `blueprint` / knowledge writing — before closing | `python3 "$P/scripts/check.py" . --status` | rules/knowledge-writing.md:80 |
| `ship` — "Before you start" preflight | `python3 "$P/scripts/check.py" .` | skills/ship/SKILL.md:70 |
| `ship` — read the feature in one call | `python3 "$P/scripts/check.py" . --brief developer.create_offer` | skills/ship/SKILL.md:87 |
| `ship` — handover, before stopping | `python3 "$P/scripts/check.py" . --run .agent-kit/runs/<slug>` | skills/ship/SKILL.md:148 |
| `ship` — design step, what will prove this | `python3 "$P/scripts/check.py" . --owed` | skills/ship/SKILL.md:216 |
| `ship` — step 7, closing the run file | `python3 "$P/scripts/check.py" . --run .agent-kit/runs/<slug>` | skills/ship/SKILL.md:400 |
| `fix` — "Before you start" preflight | `python3 "$P/scripts/check.py" .` | skills/fix/SKILL.md:41 |
| `fix` — closing the run file | `python3 "$P/scripts/check.py" . --run .agent-kit/runs/<slug>` | skills/fix/SKILL.md:137 |
| `fix` — what else this project checks for (prose ref) | `check.py . --owed` | skills/fix/SKILL.md:106 |
| `sprint` — before you ask anything | `python3 "$P/scripts/check.py" . --status` | skills/sprint/SKILL.md:43 |
| `sprint` — read the queued children back | `for run in .agent-kit/runs/<batch slug>-*/; do python3 "$P/scripts/check.py" . --run "$run"` | skills/sprint/SKILL.md:172-173 |
| `sprint` / frame child — per feature entry | `python3 "$P/scripts/check.py" . --brief <entry key>` | skills/sprint/references/frame.md:24 |
| `sprint` / close — which records moved | `python3 "$P/scripts/check.py" . --run .agent-kit/runs/<batch slug>` | skills/sprint/references/close.md:210 |
| `epic` — gate, first thing | `python3 "$P/scripts/check.py" . --epic` | skills/epic/SKILL.md:40 |
| `epic` — gate, second | `python3 "$P/scripts/check.py" . --status --state` | skills/epic/SKILL.md:41 |
| `epic` — scope, both key lists | `python3 "$P/scripts/check.py" . --entries <every key, built and planned alike>` | skills/epic/SKILL.md:90 |
| `epic` — `--advance`, after a batch closed | `python3 "$P/scripts/check.py" . --run .agent-kit/runs/<the batch that just closed>` | skills/epic/SKILL.md:298 |
| `epic` / finish — proving phase | `python3 "$P/scripts/check.py" . --state` | skills/epic/references/finish.md:83 |
| `next` — bookkeeping: manual actions | `python3 "$P/scripts/check.py" . --manual` | skills/next/SKILL.md:34 |
| `next` — bookkeeping: merged entries | `python3 "$P/scripts/check.py" . --sync` | skills/next/SKILL.md:53 |
| `next` — "Read this much and no more" | `python3 "$P/scripts/check.py" . --status --state` | skills/next/SKILL.md:94 |
| `accept` — read exactly this, and stop | `python3 "$P/scripts/check.py" . --status --state` | skills/accept/SKILL.md:30 |
| `accept` — run the proofs before listing | `python3 "$P/scripts/check.py" . --manual` | skills/accept/SKILL.md:56 |
| `advise` — preflight | `python3 "$P/scripts/check.py" . --status` | skills/advise/SKILL.md:47 |
| any command opening a PR (rules) | `python3 "$P/scripts/check.py" . --pr-body <that file>` | rules/pull-requests.md:35 |
| any command opening a PR (rules) | `python3 "$P/scripts/check.py" . --pr-base <the base you are about to open against>` | rules/pull-requests.md:42 |
| `docs/manual.md` template, to the owner | `python3 "$P/scripts/check.py" . --manual` | templates/manual.md:32 |
| **`orchestrate.py` (the driver) — `Driver.audit`, when a child closes** | **in-process**: `from check import run_defects` (line 38); `defects = run_defects(state, self.cwd)` | scripts/orchestrate.py:38, 859 |
| `scripts/validate.sh` — CI, reads the source as text | reads `check.py` text; asserts every `*_RE`/`*_MARK` constant is covered by `tests/test_formats.py`, and that `LENSES`/`ADVICE_LENSES` match the reference files of `audit`/`advise` | scripts/validate.sh:373-383, 424-436 |

Prose-only mentions (no invocation): `audit/references/scenarios.md:62`,
`next/SKILL.md:205`, `epic/references/finish.md:79,136`, `accept/SKILL.md:69,114`,
`hooks/guard.py:199`, `hooks/stop.py:78`, `rules/channels.md` (the whole channel table).

**No payload caller ever passes `--offline`.** Its only callers are
`tests/test_check.py` (`run_check`, tests/test_check.py:105) and the `Offline` tests.

## EXTERNAL PROCESSES

Every subprocess goes through `ran()` (check.py:155-171) except one. `ran` wraps
`subprocess.run(..., capture_output=True, text=True, timeout=READ_TIMEOUT)` where
`READ_TIMEOUT` = 30s (check.py:87), and returns **`None` on `OSError`/`SubprocessError`
— "could not ask", explicitly not "an empty answer"** (docstring 156-166).

| process | exact argv | caller | failure handling |
|---|---|---|---|
| `git ls-files` | `git -c core.quotePath=false ls-files` | `tracked_manifests` 842-847 | returns `[]` — **silent** |
| `git grep` | `git -c core.quotePath=false grep -n -I --no-color -F -e <needle> -- :!docs` | `grep` 1221-1253 | accepts rc 0 and 1; **anything else falls back to a Python filesystem walk** (1237-1253), skipping `.git docs node_modules vendor dist build .venv __pycache__` |
| `git symbolic-ref` / `rev-parse` | `symbolic-ref --quiet refs/remotes/origin/HEAD`, then `rev-parse --verify --quiet <origin/main|origin/master|main|master>` | `default_branch` 1652-1662 | returns `""`; `print_state` says "no git repository here" / "a repository with no commits yet" (3225-3229) |
| `git for-each-ref` | `for-each-ref --format=%(refname:short)\t%(upstream:short) refs/heads`; and `refs/remotes/origin`; and the four `refs/heads/epic refs/heads/sprint refs/remotes/origin/epic refs/remotes/origin/sprint` | `work_branches` 1664-1678, `delivered_branches` 1697-1701, `pr_base_defects` 3510-3512 | `git()` (1647-1650) returns `""` on any non-zero |
| `git rev-list --left-right --count` | `rev-list --left-right --count <base>...<name>` | `work_branches` 1673 | `""` → 0/0 |
| `git log -1 --format=%cs` | | `work_branches` 1677, `print_state` 3218 | `""` → `'?'` |
| `git merge-base --is-ancestor` | `merge-base --is-ancestor <name> <base>` | `delivered_branches.inside` 1768-1770, `run_defects` 2639, `pr_base_defects.ancestor` 3501-3503 | `bool(done) and rc == 0` — a `None` reads as **not an ancestor** |
| `git merge-base` | `merge-base <base> <branch>` | `entry_drift` 2794 | `""` → explicit "nothing common between X and Y" finding |
| `git show` | `show <ref>:<relpath>` | `entry_drift` 2802, 2807 | empty `now` → explicit "<file> is not on <base>" finding |
| `git rev-parse --verify --quiet` | on branch/base/commit names | `delivered_branches.merged_as` 1776, `run_defects` 2479/2634, `pr_base_defects` 3492/3515/3517 | `""` = does not resolve |
| `git cat-file -t <sha>` | | `run_defects` 2576, 2628 | anything ≠ `"commit"` → a finding |
| `git status --porcelain` / `rev-parse --abbrev-ref HEAD` / `rev-parse --git-dir` | | `print_state` 3216-3218, `run_defects` 2478/2575/2629 | `rev-parse --git-dir` empty = "no repository" → the rule is **skipped** rather than guessed |
| `git diff --name-only` | `diff --name-only <base>...<branch>` | `pr_base_defects` 3506 | `""` → 0 files |
| `gh pr list` (all) | `gh pr list --state all --limit 100 --json number,state,headRefName,headRefOid` | `Github.states` 1338-1355 | gated on `shutil.which("gh")`; `None` on failure/unparseable JSON, and `None` means "could not ask" — every caller distinguishes it |
| `gh pr view` | `gh pr view <n> --json state` | `Github.state` 1370-1391 | `None` on failure |
| `gh pr list` (open) | `gh pr list --state open --json number,title,headRefName,isDraft,mergeable,statusCheckRollup,updatedAt` | `Github.open_requests` 1402-1430 | **returns `[]` on every failure** — see SILENCE AUDIT |
| `tmux display-message -p '#S'` | | `this_session` 3315-3326 | only when `$TMUX` is set; `""` otherwise |
| **anything in `docs/manual.md`'s `proof:` field** | `subprocess.run(<proof>, shell=True, cwd=root, timeout=60)` — **not through `ran`** | `prove_manual` 1189-1191 | `OSError`/`SubprocessError` → "the proof … could not run"; rc 127 → "no such command on this machine"; **any other non-zero → treated as "not yet", silently** |
| project commands from `project.yml` | **never launched.** `command_defect` (971-1003) only does `shutil.which` / `Path.exists` on the first word of the first stage | | — |

## SILENCE AUDIT

The kit's own rule (CLAUDE.md, and check.py's docstring at 25-27): *a check that cannot
read its input says so*. What follows is every place the checker produces no finding
because it could not read, parse, or reach its input, and whether it says so.

### Violations — the checker stays quiet

1. **`--epic` on a project with no `docs/knowledge/` returns 0 in complete silence.**
   `main` hits the missing-knowledge early return at check.py:3709-3714 *before* the
   `--epic` branch at 3729. `--status`/`--state` are not passed by the epic gate's first
   line, so line 3711's message never prints either. Verified empirically: `check.py .
   --epic` on an empty directory prints nothing and exits 0. **The one gate with teeth in
   this program opens for a project that has no blueprint at all** — the opposite of what
   `check_epic`'s docstring (849-861) claims it prevents. Caller: skills/epic/SKILL.md:40.
2. **`--brief <key>` on a project with no `docs/knowledge/` prints nothing and returns
   0** (same early return, 3709-3714, vs the `--brief` branch at 3720). Inside `brief`
   an unknown key is a loud exit 2 (1811-1813); with no knowledge directory at all it is
   silence. Callers: skills/ship/SKILL.md:87, sprint/references/frame.md:24.
3. **`--entries <keys>` on a project with no `docs/knowledge/` prints nothing and
   returns 0** (3709-3714 vs 3840/3889). `print_entry_blocks`'s whole design (3426-3439)
   is that a filter matching nothing must be loud. Caller: skills/epic/SKILL.md:90.
4. **`sync_states` returns without a word when `gh` is not installed** (check.py:1452-1453).
   Every entry sitting at `building (pr: N)` is then unreported — indistinguishable from
   a project where no entry is mid-flight. Compare `delivered_branches` 1758-1766, which
   goes out of its way to say "nothing here could ask about pull request N". Same class of
   defect, ten lines of the same file apart.
5. **`Github.open_requests` returns `[]` on every failure** (check.py:1407-1411): `gh`
   absent, unauthenticated, rate-limited, no remote, or JSON it cannot parse. `print_state`
   (3266-3270) then prints no PR lines at all — identical to a repository with no open
   pull requests. This is the exact confusion the `Github` docstring (1304-1312) says the
   class exists to end, and `states()` handles correctly two methods above.
6. **`tracked_manifests` returns `[]` when `git ls-files` fails or git is missing**
   (check.py:845-847). The "a dependency manifest project.yml does not record" finding
   (check.py:836-840) then never fires, silently.
7. **`check_runs` returns immediately when `templates/run.json` is missing or
   unparseable** (`run_template` 1869-1876 swallows `OSError`/`ValueError`; `check_runs`
   1924-1926 `if not known: return`). A damaged install silently stops judging every run
   file in the project.
8. **`check_batches` returns immediately when `templates/batch.json` is missing or
   unparseable** (`batch_template` 1980-1987; `check_batches` 2114-2115). Same shape.
   Note both are *dependency-of-the-check* failures, precisely the case
   `check_epic`:905-911 and `check_verification`:700-705 were rewritten to announce for
   `verification.yml`.
9. **`check_shape` compares against `templates/project.yml` via `read_manifest`**
   (check.py:2185), which returns `{}` on a missing or wrongly-encoded file
   (check.py:194-202). The whole manifest half of the older-kit check then produces
   nothing, silently.
10. **`where_line` returns silently when `CLAUDE.md` cannot be read**
    (check.py:3126-3129, `except OSError: return`). It is loud when the file is absent
    (3121-3125) and mute when it is present and unreadable.
11. **`workflows` skips a workflow file it cannot read** (check.py:2891-2893,
    `except OSError: continue`). That file is then absent from `names`, from `blob`, and
    from the `fires` disjunction — so `outside_a_session` (2899-2916) and `outside_line`
    (3140-3162) can report "nothing runs it on a push" about a repository whose only
    push-triggered workflow is the file that was skipped.
12. **`read_manifest` returns `{}` on `OSError`/`UnicodeDecodeError`**
    (check.py:197-202). Deliberate and documented (the driver calls it all night), but
    nothing anywhere says "this manifest could not be read". Downstream it surfaces
    obliquely — `check_verdicts` reports every slot as having no verdict — never as the
    real cause.
13. **`check_commands` returns silently when `commands` is not a dict**
    (check.py:1006-1008), delegating the statement to `print_state` — which only runs
    under `--state`. `ship` and `fix` run the check **bare** (ship/SKILL.md:70,
    fix/SKILL.md:41), so on a project whose `commands:` is a scalar those two commands
    get no word about it from any surface.
14. **`report.sight` prints only under `--status`/`--state`** (`sight_lines` 3090-3104,
    called at 3834 and 3852). Everything `check_verification` and `check_reviewed`
    produce lives there — **including line 702-705, whose entire purpose is to say
    "`verification.yml` could not be read"**. Under a bare run (`ship`, `fix`) an
    unreadable catalogue is completely silent. The docstring at 3092-3097 argues the
    seam deliberately; it does not carve out the cannot-read line.
15. **`prove_manual` treats every non-zero, non-127 exit as "not yet"**
    (check.py:1195-1198). A `proof` script that exists and crashes (exit 1, 2, …) is
    indistinguishable from a proof correctly reporting the work is not done — despite the
    docstring at 1173-1175 promising the two are separated.
16. **`open_runs` silently skips a run file it cannot parse** (check.py:2829-2833).
    Mitigated: `check_runs` reports it as a `Runs` finding and `print_flight` prints
    `"<slug> · unreadable, and counted as in flight"` (3345-3348).
17. **The `grep` fallback silently drops undecodable files** (check.py:1245-1246), so an
    `agent-kit:unmet` or `agent-kit:scenario` mark in a non-UTF-8 file is invisible in the
    fallback path only.
18. **`--owed` on a project with no answers prints nothing and returns 0.**
    `print_owed` (2985-3025) only prints the `owed` and `refused` lists; a project that
    has never been asked yields both empty. Verified empirically: an empty directory
    prints nothing. "This feature owes nothing" and "nobody has ever been asked" are the
    same output. Caller: skills/ship/SKILL.md:216.

### Not violations — the checker says so

- `ran()` returning `None` vs an empty answer, documented and used correctly at
  check.py:155-171.
- `Github.states()` returning `None` and `delivered_branches`'s `unasked` flag
  (check.py:1755-1766): "nothing here could ask about pull request N".
- `catalogue_defects` (check.py:520-573) reads `verification.yml` as raw text precisely
  because `read_manifest` is last-wins and line-oriented; it names an empty/unreadable
  file, a duplicate kind, a wrapped line and a `#` inside a value.
- `check_verification` 700-705 and `check_epic` 908-911 both announce an unreadable
  catalogue (but see violation 14 for where the first one prints).
- `entry_drift` 2790-2806: every reason the comparison could not run is a printed line.
- `check_runs` 2050-2059 + 2075-2080: an unparseable run file is a `Runs` **finding**
  (changed from `continue`, per the comment).
- `check_batches` 2126-2133: an unparseable batch record is stated.
- `check_shape` 2160-2168: a knowledge file the kit ships no template for is stated
  rather than passed.
- `check_audits` 2296-2302 / `check_advice` 2331-2337: a report file outside the lens
  list is named rather than skipped.
- `outside_a_session` 2899-2916: the fourth answer, "cannot say".
- `check_sources` 428-431: a source hash of the wrong length is named as predating the
  program, not as a change.
- `brief` 1851-1866: absent sections are printed as `[not in this project — …]` and
  repeated on stderr.
- `check_epic` 866-875: a bounds heading it cannot find is reported as *cannot read*
  (marker missing) rather than as *no bounds*.
- `last_ran` 2918-2946 returning `None` → `'nothing in this kit records one'` (2978).
- `print_state` 3320-3327: `no git repository` / `no commits yet` / `no MANIFEST` /
  `commands is not a map` are three distinct sentences (3313-3322).

### Crash, not silence (worth naming)

`Doc.__init__` (check.py:236), `check_sources` (400), `collect_debt` (1073),
`read_manual` (1095), `check_channels` (2237, 2247), `check_audits` (2285) and
`check_batches`/`record`/`run_template` callers read with `read_text(encoding="utf-8")`
and **no** `errors=` and no `try`. A knowledge, debt, manual or audit file in another
encoding raises `UnicodeDecodeError` out of `main()` — a traceback and a non-zero shell
status, which callers reading only the exit code will read as "the check found
something". Contrast `where_line`/`workflows`/`scenarios`/`audit_lenses`, which do pass
`errors="replace"`.

## IO

### Reads (paths, relative to `root` unless noted)

- `docs/knowledge/*.md` — every `Doc` (3719); `docs/knowledge/stack.md` (1842);
  `docs/knowledge/scenarios.md` (3167); `docs/knowledge/product.md` (via `docs`).
- `.agent-kit/project.yml` (MANIFEST, 52) — `read_manifest`, `brief`, `run_defects`,
  `print_state`.
- `.agent-kit/runs/*/run.json` — `check_runs` (1929), `open_runs` (2828),
  `runfile.in_flight`/`runs` (3336, 2924), `entry_drift`'s children (2777), `--run`'s
  target (3672-3680).
- `.agent-kit/runs/*/` directory listings — `check_channels` (2225-2230), which allows
  only `run.json`, `run.log`, `control`.
- `docs/runs/*.json` — `delivered_branches` (1707), `check_batches` (2116),
  `run_defects`'s batch rule (2745).
- `docs/technical_debt.md` (53) — `collect_debt`.
- `docs/manual.md` (54) — `read_manual`, `collect_manual`, `prove_manual`.
- `docs/audits/*.md` (51) — `check_channels` (2246), `check_audits` (2280),
  `audit_lenses` (3193).
- `docs/advice/*.md` (55) — `check_advice` (2330), name only.
- `CLAUDE.md` — `where_line` (3120).
- `.github/workflows/*.yml|*.yaml` — `workflows` (2886).
- Dependency manifests by name (`MANIFEST_NAMES`, 150-153) — hashed by `check_stack`,
  listed by `tracked_manifests`.
- Any file a `source:` line points at (400, 1613).
- **Inside the plugin**: `../verification.yml` (`CATALOGUE`, 499), `../templates/run.json`
  (1871), `../templates/batch.json` (1982), `../templates/knowledge/<name>.md` (2156),
  `../templates/project.yml` (2185).
- Environment: `$TMUX` (3323). PATH, via `shutil.which` (1327, 993).

### Writes — three, each behind a flag (docstring 15-20)

1. **`--sync`** → rewrites `docs/knowledge/<slot>.md` in place, the `state:` line only
   (check.py:1491-1497). Also refreshes `doc.entries` afterwards.
2. **`--record`** → rewrites `docs/knowledge/*.md` `@hash` values (1632-1635) and
   `.agent-kit/project.yml` dependency hashes (1637-1643, and the file is written
   unconditionally at 1643).
3. **`--manual`** → deletes the closed actions' line ranges from `docs/manual.md` and
   rewrites the file (1200-1204).

**No caches, no generated files, no state directory.** `Github` memoises its listing
in-process only (`self._listed`, `self._asked`, `self._heads`, 1322-1325).

## NODES

```
script:check                  | script  | check.py                    | The kit's mechanical checker: one program, thirteen flag modes, human text on stdout. | plugins/agent-kit/scripts/check.py:1
script:check.main             | fn      | main()                      | Parses the flags and dispatches them as a priority chain of early returns. | check.py:3599
script:check.runfile          | module  | runfile.py                  | Supplies STEPS/TERMINAL/KINDS/BRANCH_PREFIXES and the run-file readers. | check.py:48-49
cmd:bare                      | mode    | check.py .                  | The full report: 19 checks, exit 1 on any blocking finding. | check.py:3737-3897
cmd:status                    | mode    | --status                    | Adds standing, planned, parts, audits, sight lines, outside line, where line. | check.py:3602
cmd:state                     | mode    | --state                     | Adds the Work block: git, gh, open runs, branches, scenarios, audits. | check.py:3614
cmd:sync                      | mode    | --sync                      | Moves an entry's state line where a merged PR already decided it. | check.py:3608
cmd:record                    | mode    | --record                    | Rewrites every source and dependency hash in place. | check.py:3611
cmd:epic                      | mode    | --epic                      | The one blocking gate: bounds, scenarios, run/test commands, verification answers. | check.py:3617
cmd:entries                   | mode    | --entries KEY…              | Prints every open block under the named entries, in full. | check.py:3620
cmd:owed                      | mode    | --owed                      | The kinds of verification a feature of this project owes. | check.py:3624
cmd:tests                     | mode    | --tests                     | This project's testing on one screen, all derived. | check.py:3627
cmd:brief                     | mode    | --brief KEY                 | Everything a run reads before it designs, in one call. | check.py:3631
cmd:run                       | mode    | --run DIR                   | Judges one run file as it closes, plus entry drift. | check.py:3634
cmd:manual                    | mode    | --manual                    | Runs every proof in docs/manual.md and deletes what has happened. | check.py:3637
cmd:pr-base                   | mode    | --pr-base BASE              | What a pull request from HEAD into that base will carry. | check.py:3641
cmd:pr-body                   | mode    | --pr-body FILE              | Measures a PR body against three character budgets. | check.py:3645
cmd:offline                   | mode    | --offline (hidden)          | Replaces the Github object with one that can answer nothing. | check.py:3607
file:knowledge                | file    | docs/knowledge/*.md         | The entries: key, state, fields, notes, source lines. | check.py:50
file:manifest                 | file    | .agent-kit/project.yml      | commands, knowledge verdicts, checks.deps, verification, stage. | check.py:52
file:catalogue                | file    | plugins/agent-kit/verification.yml | The kit's twelve kinds of verification; the list lives here, the answers in the project. | check.py:499
file:run-template             | file    | templates/run.json          | The shape a run file may have. | check.py:1871
file:batch-template           | file    | templates/batch.json        | The shape a batch record may have. | check.py:1982
file:knowledge-templates      | file    | templates/knowledge/*.md    | Compared structurally to detect a project written by an older kit. | check.py:2156
file:project-template         | file    | templates/project.yml       | Compared key-by-key against the project's own manifest. | check.py:2185
file:runfiles                 | file    | .agent-kit/runs/*/run.json  | One run's memory; git-ignored. | check.py:1929
file:batchrecords             | file    | docs/runs/*.json            | A batch's durable record: pr, branches, spent. | check.py:1707
file:debt                     | file    | docs/technical_debt.md      | Work earlier runs decided not to do. | check.py:53
file:manual                   | file    | docs/manual.md              | What only the owner can do, each with a proof command. | check.py:54
file:audits                   | file    | docs/audits/*.md            | One report per lens, with agent-kit:audit counters. | check.py:51
file:advice                   | file    | docs/advice/*.md            | One report per lens of advise; only the name is judged. | check.py:55
file:claudemd                 | file    | CLAUDE.md                   | Where a non-kit session learns the knowledge exists. | check.py:3120
file:workflows                | file    | .github/workflows/*.yml     | Whether anything outside a session runs a declared command. | check.py:2885
ext:git                       | ext     | git                         | ls-files, grep, for-each-ref, rev-list, merge-base, show, cat-file, status, log, rev-parse, diff. | check.py:155
ext:gh                        | ext     | gh                          | pr list (all and open), pr view. | check.py:1327
ext:tmux                      | ext     | tmux                        | display-message -p '#S', to know which session this is. | check.py:3324
ext:proof                     | ext     | docs/manual.md proof:       | The one thing this program executes that a run wrote, shell=True, 60s. | check.py:1189
cmd:blueprint                 | caller  | /agent-kit:blueprint        | Runs --status, --status --sync, --record. | skills/blueprint/SKILL.md:35,53
cmd:ship                      | caller  | /agent-kit:ship             | Runs bare, --brief, --owed, --run twice. | skills/ship/SKILL.md:70,87,148,216,400
cmd:fix                       | caller  | /agent-kit:fix              | Runs bare and --run. | skills/fix/SKILL.md:41,137
cmd:sprint                    | caller  | /agent-kit:sprint           | Runs --status, --run per queued child, --brief in the frame child, --run at close. | skills/sprint/SKILL.md:43,173
cmd:epic-caller               | caller  | /agent-kit:epic             | Runs --epic, --status --state, --entries, --run, --state. | skills/epic/SKILL.md:40,41,90,298
cmd:next                      | caller  | /agent-kit:next             | Runs --manual, --sync, --status --state. | skills/next/SKILL.md:34,53,94
cmd:accept                    | caller  | /agent-kit:accept           | Runs --status --state and --manual. | skills/accept/SKILL.md:30,56
cmd:advise                    | caller  | /agent-kit:advise           | Runs --status. | skills/advise/SKILL.md:47
script:orchestrate            | caller  | orchestrate.py Driver.audit | Imports run_defects and calls it in-process on every closing child. | scripts/orchestrate.py:38,859
script:validate               | caller  | scripts/validate.sh         | Reads check.py as text; asserts format constants and lens tuples are covered. | scripts/validate.sh:373,424
```

## EDGES

```
cmd:blueprint    -> cmd:status    | bash, exit code read | before any of it, always            | skills/blueprint/SKILL.md:53
cmd:blueprint    -> cmd:sync      | bash (--status --sync) | the --check invocation             | skills/blueprint/SKILL.md:35
cmd:blueprint    -> cmd:record    | bash                 | after writing a source: line        | rules/knowledge-writing.md:53
cmd:ship         -> cmd:bare      | bash, exit code read | "Before you start" preflight        | skills/ship/SKILL.md:70
cmd:ship         -> cmd:brief     | bash                 | reading the feature in one call     | skills/ship/SKILL.md:87
cmd:ship         -> cmd:owed      | bash                 | design step, before any code         | skills/ship/SKILL.md:216
cmd:ship         -> cmd:run       | bash                 | at handover and at step 7 (closing)  | skills/ship/SKILL.md:148,400
cmd:fix          -> cmd:bare      | bash                 | preflight                            | skills/fix/SKILL.md:41
cmd:fix          -> cmd:run       | bash                 | closing the run file                 | skills/fix/SKILL.md:137
cmd:sprint       -> cmd:status    | bash                 | before you ask anything              | skills/sprint/SKILL.md:43
cmd:sprint       -> cmd:run       | bash, loop over dirs | children written and still queued    | skills/sprint/SKILL.md:172-173
cmd:sprint       -> cmd:brief     | bash                 | frame child, per feature entry       | skills/sprint/references/frame.md:24
cmd:sprint       -> cmd:run       | bash                 | close.md, over the batch's own dir   | skills/sprint/references/close.md:210
cmd:epic-caller  -> cmd:epic      | bash, exit 1 blocks  | the gate, first thing                | skills/epic/SKILL.md:40
cmd:epic-caller  -> cmd:state     | bash (--status --state) | the gate, second                  | skills/epic/SKILL.md:41
cmd:epic-caller  -> cmd:entries   | bash                 | scope: every key, built and planned  | skills/epic/SKILL.md:90
cmd:epic-caller  -> cmd:run       | bash                 | --advance, after a batch closed      | skills/epic/SKILL.md:298
cmd:epic-caller  -> cmd:state     | bash                 | proving phase, scenario coverage     | skills/epic/references/finish.md:83
cmd:next         -> cmd:manual    | bash, writes manual.md | bookkeeping already done elsewhere | skills/next/SKILL.md:34
cmd:next         -> cmd:sync      | bash, writes knowledge | an entry building whose PR merged  | skills/next/SKILL.md:53
cmd:next         -> cmd:state     | bash (--status --state) | "read this much and no more"      | skills/next/SKILL.md:94
cmd:accept       -> cmd:state     | bash (--status --state) | read exactly this, and stop       | skills/accept/SKILL.md:30
cmd:accept       -> cmd:manual    | bash                 | run the proofs before listing        | skills/accept/SKILL.md:56
cmd:advise       -> cmd:status    | bash                 | preflight                            | skills/advise/SKILL.md:47
any-command      -> cmd:pr-body   | bash, exit 1 blocks  | before opening or editing a PR       | rules/pull-requests.md:35
any-command      -> cmd:pr-base   | bash, exit 1 blocks  | in the same breath                   | rules/pull-requests.md:42
owner            -> cmd:manual    | bash, by hand        | the template tells them to           | templates/manual.md:32
script:orchestrate -> script:check | python import       | every child that reaches a close     | scripts/orchestrate.py:38,859
script:validate  -> script:check  | reads the source text | CI, before every release            | scripts/validate.sh:373,424
script:check     -> file:knowledge | read, and write under --sync | always                      | check.py:3719,1491
script:check     -> file:manifest | read; written under --record  | always                      | check.py:192,1643
script:check     -> file:catalogue | read as dict and as raw text | check_verification, check_epic, --owed, --tests, --run | check.py:504,520
script:check     -> file:runfiles | read                 | check_runs, open_runs, print_flight, --run | check.py:1929
script:check     -> file:batchrecords | read             | delivered_branches, check_batches, --run for a sprint | check.py:1707,2116,2745
script:check     -> file:manual   | read; lines deleted under --manual | collect_manual, prove_manual | check.py:1085,1200
script:check     -> file:debt     | read                 | collect_debt                         | check.py:1073
script:check     -> file:audits   | read                 | check_channels, check_audits, audit_lenses | check.py:2246,2280,3193
script:check     -> file:advice   | name only            | check_advice                         | check.py:2330
script:check     -> file:workflows | read                | --tests, --status/--state outside_line | check.py:2885
script:check     -> file:claudemd | read                 | --status/--state where_line          | check.py:3120
script:check     -> file:run-template | read             | check_runs                           | check.py:1871
script:check     -> file:batch-template | read           | check_batches                        | check.py:1982
script:check     -> file:knowledge-templates | read      | check_shape                          | check.py:2156
script:check     -> file:project-template | read         | check_shape                          | check.py:2185
script:check     -> ext:git       | subprocess via ran(), 30s | grep, branches, ancestry, drift, pr-base | check.py:155,1221,1647
script:check     -> ext:gh        | subprocess via ran(), 30s, gated on which(gh) | sync_states, delivered_branches, print_state | check.py:1338,1379,1404
script:check     -> ext:tmux      | subprocess via ran() | only when $TMUX is set, in print_flight | check.py:3324
script:check     -> ext:proof     | subprocess shell=True, 60s | --manual only                  | check.py:1189
script:check     -> script:check.runfile | python import | always                              | check.py:48-49
```

## UNCERTAIN / CONTRADICTORY / DEAD

1. **`report.add("MVP", line)` is dead code** (check.py:924). `check_epic` is called from
   exactly one place, `main`:3730, which prints `fatal` directly and returns at 3735
   without touching `report.groups`. Nothing ever prints the `MVP` group. Proof:
   `check_epic(` appears twice in the file (definition 849, call 3730) and `"MVP"` twice
   (a comment at 869, the dead `add` at 924).
2. **`--offline` has no payload caller.** Declared with `argparse.SUPPRESS` (3607) and
   documented as a seam (3603-3606, 1310-1312). `grep -rn "check.py" plugins/ scripts/`
   finds no invocation passing it; the only users are `tests/test_check.py` (line 105 and
   the `Offline` cases at 925, 1149/3149, 2569).
3. **`--epic` is unreachable on a project without `docs/knowledge/`** — the gate is
   skipped, not failed. See SILENCE AUDIT #1, proven empirically. `--brief` and
   `--entries` share the defect. All three sit behind check.py:3709-3714.
4. **The `Sources` "every source looks changed" hint (check.py:3860-3863) can only fire
   on the exit-1 path.** It is placed after the `report.clean` early return at 3827, and
   `Sources` findings are `groups` entries, so this is consistent — but note it cannot
   fire under `--status` on an otherwise clean project, and the wording ("Re-record them
   with blueprint") names a command rather than the flag `--record` that actually does it.
5. **`check_verification`'s cannot-read announcement is invisible to the two commands
   most likely to hit it.** Line 700-705 explicitly exists so that an unreadable catalogue
   is not silence — but it goes into `report.sight`, which prints only under
   `--status`/`--state` (3090-3104, 3834, 3852). `ship` (skills/ship/SKILL.md:70) and
   `fix` (skills/fix/SKILL.md:41) run the check bare. The same line duplicated into the
   `--epic` gate (908-911) is reached — that gate prints `fatal` directly.
6. **Duplicated logic — three places compute the same catalogue join.** `answers()`
   (576-598) is called by `unanswered` (652), `check_verification` (707),
   `check_reviewed` (783, 787), `print_owed` (2999), `print_outside` (3040),
   `print_answers` (3071) and `run_defects` (2673). The `runs == "feature" and not
   body.get("command")` filter appears twice, at `print_owed` 3001-3008 and
   `run_defects` 2678-2680. `print_owed`'s docstring (2990-2996) names the duplication as
   intentional.
7. **Duplicated logic — `record_lists`/`stringly` (1883-1913, used by `check_runs`) and
   the per-field `isinstance` loop in `run_defects` (2508-2514) both judge "a field of
   records filled with sentences"**, from different sources (the template vs a hard-coded
   `("tasks", "assumptions", "manual")` tuple). A run file can be reported by both, in two
   different vocabularies, on one mistake.
8. **`prove_manual`'s `timeout` parameter (1164) is never overridden.** `main`:3662 calls
   `prove_manual(root)`. Same for `ran`'s `timeout` (155) — no caller passes it.
9. **`check_channels`'s allowed run-directory files (`run.json`, `run.log`, `control`,
   check.py:2229) are hard-coded here and nowhere else**, while `runfile.py` owns
   everything else about a run directory. A fourth file the kit starts writing would be
   reported as "a mechanism nothing declared" by this check alone.
10. **`brief`'s "did you mean" uses substring matching** (1809: `key.split(".")[-1] in k`)
    while `run_defects`'s `entries` rule uses `difflib.get_close_matches` at cutoff 0.8
    (2458-2460). The same question, two algorithms, in one file.
11. **`bounds_section` has three fallbacks** (1537-1550) and `check_epic`'s comment at
    866-874 says the hard-coded heading was removed — but the literal English string
    `"MVP bounds"` at 1549 is still one of them, which is the same kind of language
    assumption, in English rather than Russian.
12. **`--record` writes `project.yml` even when nothing changed** (check.py:1643,
    unconditional `manifest_path.write_text`). Harmless byte-wise, but it touches the
    mtime of a file the program's own docstring says it writes only when asked to change
    something.
13. **`--pr-body` counts `rows - 2` as "the biggest uncollapsed table"** (3568, 3590),
    assuming every table has a header row and a separator row. A block of consecutive
    `|`-leading lines that is not a table (a fenced example, say) is counted as one, and
    `<details>` stripping is regex-based (3565) so a nested or unclosed `<details>` skews
    every number on that screen.
14. **`WHO_RUNS` (2851-2860) is the kit's schedule and `verification.yml`'s `command:`
    keys are the same five names** (`test`, `e2e`, `mutate`, `types`, `lint`), plus `run`
    which has no catalogue kind. Nothing in `check.py` or `validate.sh` holds the two
    lists together; a kind renamed in `verification.yml` would silently drop out of
    `print_outside`'s exclusion at 3038.
