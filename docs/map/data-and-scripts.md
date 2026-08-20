# Sector: data layer and repo scripts

Source repo root: `/projects/agent-kit`. Plugin root: `plugins/agent-kit` (referenced in payload as `${CLAUDE_PLUGIN_ROOT}`).

## TEMPLATE -> ARTIFACT TABLE

| template | destination in a project | created by | written by afterwards | read by | evidence |
|---|---|---|---|---|---|
| `templates/project.yml` | `.agent-kit/project.yml` | `/agent-kit:blueprint`, with the owner | `blueprint` only — "no build command may edit it" | every command; `check.py` (reads commands + verdicts) | `plugins/agent-kit/skills/blueprint/SKILL.md:188`; `rules/channels.md:48`; header comment `templates/project.yml:1-3` |
| `templates/run.json` | `.agent-kit/runs/<slug>/run.json` | the run itself (`ship`/`fix`/`sprint`/`epic` child), via `scripts/runfile.py` / driver `Run` class | every session working that run, the driver (`scripts/orchestrate.py`), the reviewer | the session resuming it, the closing session, the reviewer, the driver, `check.py --run` | `skills/ship/SKILL.md:105`; `rules/channels.md:15`; `scripts/orchestrate.py:74` (`self.file = directory / "run.json"`) |
| `templates/batch.json` | `docs/runs/<batch-slug>.json` | the closing session of a batch, filled from this template | nobody after write — "closed by nobody, it is history" | a later gate pricing a scope from `spent`; a batch's frame child (`per_feature`); `/agent-kit:next` (reads `branches` to retire delivered branches); a person | `skills/sprint/references/close.md:229`; `rules/channels.md:41`; `templates/batch.json:1-2` |
| `templates/workflow.yml` | `.github/workflows/<name>.yml` | a `ship` run given the task "build the CI that runs this project's declared commands" — never generated automatically | any run that changes what the project declares (rewrites it) | GitHub (on every push); `check.py --tests` (says whether anything outside a session runs each declared command) | `templates/workflow.yml:1-13`; `rules/channels.md:49`; `skills/next/SKILL.md:209` |
| `templates/manual.md` | `docs/manual.md` | the closing session of a batch (copies template if absent), or a run delivering its own PR | runs append `manual` entries at the same point | the closing session composing the PR's Manual actions section; `check.py --manual` (runs proofs, deletes closed lines); `/agent-kit:accept` | `skills/ship/SKILL.md:267`; `skills/sprint/references/close.md:124`; `rules/channels.md:39` |
| `templates/technical_debt.md` | `docs/technical_debt.md` | `ship`'s closing session (copies template if absent), or `blueprint` for owner-reported debt | `ship`, closing sessions, `blueprint` append; whoever does the work deletes the line | `check.py`, `sprint`, `next` | `skills/ship/SKILL.md:298`; `skills/blueprint/SKILL.md:122`; `rules/channels.md:38` |
| `templates/where-things-are.md` | block `<!-- agent-kit:where --> ... <!-- /agent-kit:where -->` inside the project's own `CLAUDE.md` | `/agent-kit:blueprint`, written between markers and nowhere else | `blueprint` only (rewrites between markers) | people / outside agents / plain conversations in the project directory (Claude Code auto-loads `CLAUDE.md`) | `skills/blueprint/SKILL.md:192`; `templates/where-things-are.md:1-25` |
| `templates/knowledge/*.md` (8 files) | `docs/knowledge/<slot>.md`, one file per slot: product, actors, entities, actions, screens, integrations, scenarios, stack | copied from `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/` on first use, by `blueprint`/`advise` | `blueprint` and `advise` with the owner present write prose; a build command (no owner) may move only the `state:` line and leave a block | every command; `check.py` | `rules/knowledge-writing.md:15`; `rules/channels.md:44` |

Note on `.agent-kit/project.yml` vs `docs/`: `.agent-kit/` is **not** in git (`rules/channels.md:43`, `where-things-are.md:43`); `docs/*` is committed.

## RECORD SHAPES

### `docs/knowledge/product.md`
Not a keyed record list — one narrative file with fixed sections: "How the owner describes it" (verbatim, lightly cleaned), "Parts" (one line each: name, coverage, mark), "What it is for", "What it deliberately does not do", "Application type", "Environment and constraints", and a fenced block `<!-- agent-kit:mvp-bounds -->` / `## MVP bounds` with explicit **In:** / **Out:** lists.
- Each Part line carries a mark: `walked: <date>` (owner confirmed) or `derived` (read out of code, unconfirmed) — English literal, counted by `check.py` (`rules/channels.md:36`).
- Application type decides which surface slots (screens/endpoints/commands) apply — referenced by name in `screens.md`/others (`templates/knowledge/product.md:19-20`).

### `docs/knowledge/stack.md`
Sections: Versions, Principles, Decisions per area, Library map, Testing, "What we do not do". No `key:`/entries — derived from manifests/code, corrected by the owner. Also hosts three cross-run inline markers that live *under this file*, per `rules/channels.md`:
- `[found …]` — written by `ship`, read/folded by `blueprint`.
- `[frame …]` — written by a batch's frame child, read by every later `ship` of the batch and by `agent-kit:reviewer`, folded into "Decisions per area" by `blueprint` once the batch merges.
(These markers are not defined inside `templates/knowledge/stack.md` itself, only referenced from `run.json`'s `_frame` comment and `channels.md`.)

### `docs/knowledge/actors.md`
Fields: **Comes to exist, Can do, Must never**.
Key: `key: <slug>` — short lowercase slug, e.g. `developer`, `buyer`, `scheduler`, `payment_gateway`.
Done when every actor named in product.md has an entry and at least one action attributed to it in actions.md (cross-checked by `check.py:check_orphans`, which flags an actor no action belongs to).

### `docs/knowledge/entities.md`
Fields: **What it is, States, Transitions, Relations, Invariants**.
Key: singular lowercase noun, e.g. `offer`, `request`, `lot`.
States/Transitions are the point — an action setting a status the entity does not list is a defect (cross-checked, not automatically — this is a design intent, no dedicated check found for entity-state-vs-action-state matching beyond generic reference resolution).

### `docs/knowledge/actions.md`
Fields: **Who, Trigger, Preconditions, What happens, What changes, Initiator sees, Others see, Can go wrong, Reached from**.
Key: `actor.verb_object`, e.g. `developer.create_offer`, `scheduler.expire_offers` — actor part must resolve against `actors.md` (checked in `check.py:check_references`, `plugins/agent-kit/scripts/check.py:323-338`, flags "no actor {actor!r}" when the prefix before `.` isn't a declared actor).
Carries `state:` line: `planned | building (pr: N) | built` — the only place implementation progress is recorded. Written by: build command sets `building (pr: N)` on opening the PR, or the batch's closing session for the whole batch; moved to `built` by bookkeeping (`blueprint --check`, `/agent-kit:next`) once merged (`templates/knowledge/actions.md:13-16`; `rules/channels.md:34`).
Prose above the state line is written only with the owner present (`blueprint`, or `advise`); a run with nobody to ask moves only the state line.

### `docs/knowledge/screens.md`
Fields: **For whom, Purpose, On the screen, Arrived from, Leads to**.
Key: `screen.<slug>`.
A screen the product opens on has no "Arrived from": write `entry_point` (matched by `ENTRY_POINT_RE`, `check.py:112`) so `check_orphans` stops counting it as unreached.
Not applicable when the product has no UI — declared via `project.yml` verdict + reason, not by inventing empty entries.
"Leads to" transitions name action keys, cross-checked to exist in `actions.md`.

### `docs/knowledge/integrations.md`
Fields: **What it is, We send, We receive, When it is down, Credentials**.
Key: `integration.<slug>`.
Rule: never record credential *values*, only the names of environment variables.

### `docs/knowledge/scenarios.md`
Fields: **Who, Starting point, Steps, Ends with**. No `key:` line shown in the template example — scenarios are addressed by heading text via the marker `agent-kit:scenario <heading>` placed beside an end-to-end test (matched via `section_after()` in check.py, language-independent because the mark itself, not the heading, is matched).
Steps name action keys — a scenario mentioning an action nobody wrote is a finding.
8-10 scenarios expected, walked end-to-end on real names/numbers; these are what `epic`'s proving phase runs against the live application — every scenario inside MVP bounds must pass.

### Cross-reference / key syntax (global, enforced by `check.py`)
- `KEY_RE = ^`key:\s*([^`·]+?)\s*`(?:\s*·\s*`state:\s*([^`]+?)\s*`)?` (`check.py:89`) — a record's key line, optionally followed by `· `state: ...``.
- `REF_RE = `([a-z][a-z0-9_]*\.[a-z0-9_]+)`` (`check.py:104`) — any backticked `a.b` token is treated as a knowledge-key reference only when `a` is a declared actor or the ref starts with `screen.`; otherwise ignored as prose (config path, class name, filename) to avoid false positives (`check.py:333-338`).
- `HEADING_RE = ^###\s+(.+)$` — record boundaries are level-3 headings.
- `ENTRY_POINT_RE` — literal backticked `entry_point`.
- `SOURCE_RE = `source:\s*([^#`]+)#([^@`]+?)\s*@([0-9a-f]+)`` — links a knowledge entry to a heading section of the owner's own document (e.g. `docs/DEVELOPER.md`) with an 8-char content hash (`DIGEST_LEN = 8`), recomputed by `check.py --record` and never typed by hand (`rules/knowledge-writing.md:46-57`).
- `SOURCE_LOOSE_RE` catches malformed `source:` lines the strict pattern missed, distinguishing a URL (allowed, unverifiable) from a broken local reference (flagged).
- Orphan check (`check_orphans`, `check.py:344-361`): an actor with no action, or an entity/screen named nowhere else in the whole knowledge corpus (outside its own body) and not marked `entry_point`, is reported.

## PROJECT DATA LAYER MAP

Everything the kit creates in a project that uses it, from `rules/channels.md` (the kit's own authoritative "four answers" table) cross-checked against templates and skills:

| Path | Written by | Read by | Closed by | Storage |
|---|---|---|---|---|
| `.agent-kit/project.yml` | `blueprint` only | every command; `check.py` | `blueprint`, with the owner | git |
| `.agent-kit/runs/<slug>/run.json` | every session, about its own run | resuming session, closing session, reviewer, driver, `check.py --run` | the run itself, reaching a terminal `step` | machine-only, `.agent-kit/runs/` is git-ignored |
| `.agent-kit/runs/<slug>/run.log` | the driver only | a person | never (history) | machine-only |
| `.agent-kit/runs/<slug>/control` | the owner's window | the driver, between children | the driver, deletes on read | machine-only |
| `docs/knowledge/<slot>.md` (×8) | `blueprint`/`advise` (owner present) for prose; build commands for `state:` line only | every command; `check.py` | nobody — entries are rewritten, never removed | git |
| `docs/technical_debt.md` | `ship`, closing sessions, `blueprint` (owner-reported) | `check.py`, `sprint`, `next` | the commit that does the work, deleting the line | git |
| `docs/manual.md` | closing session (copies from `templates/manual.md`); a self-delivering run | `check.py` (gated by `stage`), `next`, `accept` | the program: `check.py --manual` runs each `proof` and deletes closed lines; the owner for `proof: none` lines | git |
| `docs/audits/<lens>.md` | that lens | `sprint`, `epic`, `next`, `accept` | closing session / `next` / `accept` ticking a box with its PR number; the lens itself rewriting the file next run | git |
| `docs/runs/<slug>.json` | closing session, from `templates/batch.json` | later gate (pricing from `spent`), frame child (`per_feature`), `next` (`branches`), a person | never — durable history | git |
| `docs/deployment.md` | any run finding a release-only concern while `stage: development` | the owner (on first release), the next run that finds another item | the owner only | git |
| `docs/advice/<lens>.md` | that lens of `advise` | the next run of the same lens | that same lens, rewriting the file | git |
| `.github/workflows/<name>.yml` | a `ship` given the CI-building task, from `templates/workflow.yml` | GitHub on every push; `check.py --tests` | the owner (stops using GitHub); any declaration-changing run rewrites it | git |
| project's own `CLAUDE.md`, block between `<!-- agent-kit:where -->` markers | `blueprint`, from `templates/where-things-are.md` | people, outside agents, fresh sessions (Claude Code auto-loads CLAUDE.md) | `blueprint` (rewrites between markers, never touches outside them) | git |
| in-source markers: `agent-kit:unmet <key>` beside a test | `ship` | `check.py`, `sprint` with no theme | the `ship` run that fulfills the promise, deleting the mark in the same commit | git (source file) |
| in-source marker: `agent-kit:scenario <heading>` beside an e2e test | `ship` | `check.py --state`, an epic's finish | never — it is the proof itself | git (source file) |
| `docs/knowledge/*.md` inline markers `[assumed …]`, `[stale …]` under an entry | `ship` | later runs building in that entry; `blueprint` | `blueprint`, or a build command with the owner present | git |
| `docs/knowledge/stack.md` inline markers `[found …]`, `[frame …]` | `ship` / a batch's frame child | `blueprint`; every `ship` of that batch + `agent-kit:reviewer` | `blueprint` folding it in once merged | git |
| `docs/advice/<lens>.md` marker `[accepted …]` | `advise` | `next`, which raises it | `blueprint`, writing up the record | git |

Verified with grep that `docs/audits`, `docs/runs` and `.github/workflows` paths are actually referenced by `check.py` (lines 51, 2738-2748, 2863-2915) confirming these are live, checked channels, not just documented aspiration.

## verification.yml

Read by `scripts/check.py` (function `catalogue()`, `check.py:499-517`) and by `/agent-kit:blueprint` (walks it with the owner). Also by `ship`/an epic's proving phase, which use it to decide which kinds a change touches.

`catalogue()` returns only entries whose `body["runs"]` is `"feature"` or `"epic"` — malformed entries (no `runs`) are silently dropped from the usable set, but `catalogue_defects()` (`check.py:520+`) is a separate, stricter line-level parser that flags: file empty/unreadable, a kind defined twice (last-wins silently loses the first), a wrapped/unreadable value line, and a `#` inside a value truncating it (an editor line-wrap already broke `runs: featrue` once in production, silently dropping `suite`).

Twelve kinds (confirmed by `grep -c "^[a-z_]*:$" verification.yml` = 12), each with `catches` (the defect it finds), `runs` (`feature` or `epic`), `skip_when` (interview guidance only, never auto-applied), and optionally `command` (only for the five kinds that already have a home in `project.yml → commands`: test/suite, e2e/end_to_end, mutate/mutation, types, lint):

| kind | command key | runs | catches (summary) |
|---|---|---|---|
| suite | test | feature | wrong-answer logic bugs |
| end_to_end | e2e | epic | parts work individually but the product doesn't |
| mutation | mutate | feature | a test that asserts nothing (never seen red) |
| types | types | feature | value not the shape assumed |
| lint | lint | feature | code that reads wrongly later |
| static_analysis | — | feature | what types can't see (null 3 calls away, unreachable branch, injectable query) |
| architecture | — | feature | work correct but in the wrong place |
| visual | — | feature | a screen rendering wrongly with the same underlying values |
| contract | — | epic | an outside service or published API that drifted |
| performance | — | epic | correct but too slow |
| accessibility | — | feature | unusable by keyboard/screen-reader/contrast |
| security | — | epic | known-hole dependency, committed secret, unenforced permission |

(12 rows confirmed by reading the raw file, `verification.yml:28-91`.)

A project's answer lives only in `.agent-kit/project.yml → verification`, one line per kind: either the command that runs it, or `no <date> <reason>` — never bare `yes`. `project.yml → checks.verification_reviewed` records when these answers were last confirmed with the owner; `check.py` flags it stale past six months or sooner if a dependency manifest changed.

## validate.sh

Ordered list of every check `bash scripts/validate.sh` performs (also what CI runs, `.github/workflows/ci.yml:20-21`):

1. **Repository layout** (`validate.sh:19-25`) — `VERSION`, `CHANGELOG.md`, `README.md`, `README.ru.md`, `.claude-plugin/marketplace.json`, `plugins/agent-kit/.claude-plugin/plugin.json`, `plugins/agent-kit/README.md`, `plugins/agent-kit/templates/project.yml`, `plugins/agent-kit/templates/knowledge` must all exist. Fails with `missing: <path>`.
2. **VERSION is semver** (`:28`) — regex `^[0-9]+\.[0-9]+\.[0-9]+$`. Fails `VERSION is not semver: <val>`.
3. **CHANGELOG has an entry for VERSION** (`:29`) — `grep -q "## $VERSION" CHANGELOG.md`. Fails if missing.
4. **No project-owned dir shipped inside the plugin** (`:32`) — `$PLUGIN/.agent-kit` must not exist, because an update would overwrite a project's own corner.
5. **Every knowledge template has a header comment** (`:36-39`) — first line must start with `<!--`; enforces that templates, not commands, define shape.
6. **Manifests, frontmatter, and versions** (python block, `:44-154`): marketplace.json has `name`/`owner`/`plugins`, contains a plugin entry `source: ./plugins/agent-kit`; plugin.json's `name` is exactly `"agent-kit"` and its `version` matches `VERSION`; marketplace metadata.version agrees with VERSION; marketplace plugin `description` matches plugin.json's `description` (storefront drift, cost a real release once); any cross-marketplace dependency must be in `marketplace.json`'s `allowCrossMarketplaceDependenciesOn`; every `skills/*/SKILL.md` has valid YAML frontmatter with `name` matching its directory, a `description` between 40 and 1024 chars, and a body that is either the literal "Not written yet." (a declared stub) or at least 400 chars (real behavior) — anything shorter is neither; every `/agent-kit:<cmd>` mentioned in the plugin README must exist as a skill and vice versa; every stub must be marked as such in the README.
7. **The two READMEs (en/ru) agree** (`:161-190`) — same set of `### \`name`-headed commands; same count of `## ` section lines and `| ` table rows (a table-row drift once slipped past the heading-only check); every skill directory is documented in README.md; every documented command has a matching skill directory; a stub's README heading must say "not written"/"не написана" in *both* files, a shipped command must say so in *neither*.
8. **Internal `${CLAUDE_PLUGIN_ROOT}/...` references resolve** (`:196-199`) — every such path mentioned anywhere in the plugin must exist as a file under it. Fails `dangling reference: ...`.
9. **Bare (non-variable) references also resolve** (`:205-209`) — same idea for paths like `skills/…`, `rules/…`, `agents/…`, `templates/…`, `scripts/…`, `hooks/…` ending in `.md/.py/.json/.yml`, written without the `${CLAUDE_PLUGIN_ROOT}` prefix.
10. **Both hooks are registered and run** (`:217-256`): `hooks/hooks.json` must register both a `PreToolUse` and a `Stop` event; every `.py` file under `hooks/` must appear in `hooks.json`; the guard hook (`guard.py`) must not error on a harmless Bash command; the stop hook (`stop.py`) must not error outside a project; simulating a broken install (plugin copied with `scripts/` deleted) — neither hook may `exit 2` (which denies the tool call) and each must print a `systemMessage` saying it failed open rather than staying silent.
11. **Markdown is not malformed** (`:264-292`): every `.md` file under the plugin has an even number of ``` ` ``` fences (odd = unclosed fence swallows the rest of the file); no HTML comment nests inside another (`<!--` inside `<!--` is silently closed by the first `-->`, hiding everything meant to stay hidden — this shipped once in `screens.md`).
12. **Every durable file the payload names has a row in the channel table** (`:295-357`) — extracts every `docs/...` or `.agent-kit/...`-shaped path mentioned anywhere in the plugin payload, reduces to its "family" (first two path segments), and requires each family to appear either in `rules/channels.md`'s table (first cell of each row) or in an explicit `NOT_CHANNELS` allowlist (`docs/design`, `docs/DEVELOPER.md`, `docs/advise-<date>`). Fails per undeclared family with the reason "a file with no writer, reader and closer named is not a mechanism yet".
13. **Every format `check.py` parses has a documented example** (`:368-384`) — every `*_RE`/`*_MARK` constant declared in `check.py` must be named in `tests/test_formats.py`; otherwise `check.py declares X and tests/test_formats.py neither covers it...`.
14. **Every driver flag is named where a person reads it** (`:394-409`) — every `add_argument("--...")` in `orchestrate.py` must appear in backticks in `skills/sprint/SKILL.md` or `skills/epic/SKILL.md`; else "a flag named nowhere the owner reads is a flag they do not have".
15. **Command/lens name agreement** (`:419-455`) — for `audit`/`LENSES` and `advise`/`ADVICE_LENSES` in `check.py`: the constant's declared lens names must exactly match the `.md` filenames under `skills/<command>/references/`, and every lens name must appear in backticks in that command's own `SKILL.md`.
16. **Every field of `run.json`/`batch.json` has a writer and a reader** (`:468-501`) — for each non-underscore-prefixed top-level field in both templates, at least 2 distinct payload files (excluding the templates themselves, and excluding each other so they can't vouch for each other) must mention that exact word; otherwise "a record with one side is written by nobody or read by nobody".
17. **No project-specific leakage** (`:506-510`) — greps the whole plugin case-insensitively for `beeplish` or `english push tutor` (names of real projects the kit was developed against); any hit fails.
18. **Every verification kind is usable** (`:520-533`) — runs `check.catalogue_defects()` from `check.py` against `verification.yml`, and separately requires at least 5 kinds to parse successfully via `catalogue()`.
19. **The driver's own tests** (`:539-543`) — if a `tests/` directory exists: `python3 -m compileall` over `scripts/` and `hooks/` must succeed; `python3 -m unittest discover -s tests` must pass.
20. **Shell syntax** (`:546-560`) — every `*.sh` under the plugin and top-level `scripts/` gets `bash -n` (syntax check); if `shellcheck` is installed, also `shellcheck -S warning`; if not installed, prints a NOTE that CI checks it but this run did not.

Exit: prints error count and `exit 1` if `errors > 0`, else prints `OK — <plugin> <version> validates` and `exit 0` (`:562-569`).

## measure.py / release.sh / CI

**`scripts/measure.py`** — a development tool for the kit's own maintainers; explicitly does **not** ship with the plugin (`measure.py:2`). Run by hand: `scripts/measure.py <project-dir> [--by-role|--by-branch|--curve|--since DATE]`.
- Input: Claude Code's own session transcripts at `~/.claude/projects/-<slugified-project-path>/*.jsonl`, plus `<session>/subagents/*.jsonl` for spawned agents.
- What it measures: cost in *weighted tokens* (input×1, cache-write×1.25, cache-read×0.1, output×5 — the four raw token kinds price fifty-fold apart, so a raw total is unusable) per session, deduplicated by `message.id`; turns counted as one model reply (not one transcript record, which overcounts ~1.9×); each session's "role" inferred from the slash-command found in its opening records (`ship`, `epic`, `sprint`, etc., narrowed by flags like `--advance`/`--resume`/`--close`); context floor/peak per session.
- `--curve` additionally least-squares-fits `cost = a + b·turns + c·turns²` over feature-child (`ship`) sessions, derives a context floor/growth rate, and prices several candidate "handoff ceiling" values (110k–340k tokens) against the actual distribution of feature lengths observed in the project, to find the cheapest ceiling.
- Nobody in the automated pipeline runs it — it's a manual diagnostic used to produce the design notes under `docs/design/` (e.g. `docs/design/2026-08-14-where-the-tokens-burn.md`, referenced at `measure.py:24`).

**`scripts/release.sh <version>`** — run by hand by a maintainer before publishing a release:
1. Validates `$1` is given and is semver.
2. Refuses if the git working tree is dirty.
3. Refuses if tag `v<version>` already exists.
4. Refuses if `CHANGELOG.md` has no `## <version>` section.
5. Writes `<version>` into `VERSION`.
6. Via inline Python, bumps `plugins/agent-kit/.claude-plugin/plugin.json`'s `version` field and `.claude-plugin/marketplace.json`'s `metadata.version` to match, writing both back as pretty JSON.
7. Runs `bash scripts/validate.sh` (any failure aborts, `set -euo pipefail`).
8. `git add`s the four bumped files; commits `release: v<version>` (skipped if nothing changed — e.g. VERSION already had this value from an advance-prepared release).
9. Creates annotated tag `v<version>`.
10. Prints a reminder to `git push && git push --tags` — it does **not** push itself.

**CI** — `.github/workflows/ci.yml`, one workflow `validate`, one job `validate`, triggers: push to `main`, push of tags matching `v*`, and every pull request.
Steps: checkout; `apt-get install shellcheck` (so `validate.sh`'s shellcheck branch always actually runs in CI, even though it's optional locally); run `bash scripts/validate.sh`; and, only on a tag push (`startsWith(github.ref, 'refs/tags/v')`), assert the tag's version suffix equals the content of `VERSION` — this is the one check `validate.sh` itself does not perform, since `release.sh` writes `VERSION` and the tag from the same run and they can't drift *there*, but a tag pushed by hand independently could.
This is the kit's *only* CI file — there is no separate lint/test/deploy workflow; `scripts/validate.sh` is the entire gate, run identically locally and in CI (`validate.sh:5`).

## NODES

`tpl:project-yml | template | project.yml template | shape of a project's own corner of the kit (language, stage, commands, knowledge verdicts, verification answers, check dates) | plugins/agent-kit/templates/project.yml:1`
`tpl:run-json | template | run.json template | shape of one run of any kit command (feature/errand/batch/epic), with 30+ documented fields | plugins/agent-kit/templates/run.json:1`
`tpl:batch-json | template | batch.json template | what one delivered batch leaves behind permanently: counts, PR, branches, spend | plugins/agent-kit/templates/batch.json:1`
`tpl:workflow-yml | template | workflow.yml template | shape of the project's own CI pipeline built from its declared commands | plugins/agent-kit/templates/workflow.yml:1`
`tpl:manual-md | template | manual.md template | ledger of actions only the owner can do, each closed by a proof command | plugins/agent-kit/templates/manual.md:1`
`tpl:technical-debt-md | template | technical_debt.md template | ledger of work understood and deliberately not done | plugins/agent-kit/templates/technical_debt.md:1`
`tpl:where-things-are-md | template | where-things-are.md template | the block blueprint writes into the project's own CLAUDE.md | plugins/agent-kit/templates/where-things-are.md:1`
`tpl:knowledge-product | template | product.md template | narrative product description + parts + MVP bounds | plugins/agent-kit/templates/knowledge/product.md:1`
`tpl:knowledge-stack | template | stack.md template | versions, principles, per-area decisions, library map, testing bar | plugins/agent-kit/templates/knowledge/stack.md:1`
`tpl:knowledge-actors | template | actors.md template | who/what initiates actions | plugins/agent-kit/templates/knowledge/actors.md:1`
`tpl:knowledge-entities | template | entities.md template | what persists, its states and invariants | plugins/agent-kit/templates/knowledge/entities.md:1`
`tpl:knowledge-actions | template | actions.md template | the unit of work an actor performs, carries build state | plugins/agent-kit/templates/knowledge/actions.md:1`
`tpl:knowledge-screens | template | screens.md template | UI surfaces and their transitions | plugins/agent-kit/templates/knowledge/screens.md:1`
`tpl:knowledge-integrations | template | integrations.md template | external systems the product depends on | plugins/agent-kit/templates/knowledge/integrations.md:1`
`tpl:knowledge-scenarios | template | scenarios.md template | end-to-end walks used to prove completeness and correctness | plugins/agent-kit/templates/knowledge/scenarios.md:1`
`file:project-yml | file | .agent-kit/project.yml | a project's filled-in corner; git-tracked, not machine-only | plugins/agent-kit/rules/channels.md:48`
`file:run-json | file | .agent-kit/runs/<slug>/run.json | live working state of one run; git-ignored, dies with the machine | plugins/agent-kit/rules/channels.md:15`
`file:batch-json | file | docs/runs/<slug>.json | permanent record of a delivered batch | plugins/agent-kit/rules/channels.md:41`
`file:workflow-yml | file | .github/workflows/<name>.yml | this project's actual CI pipeline | plugins/agent-kit/rules/channels.md:49`
`file:manual-md | file | docs/manual.md | durable manual-actions ledger surviving past the PR | plugins/agent-kit/rules/channels.md:39`
`file:technical-debt-md | file | docs/technical_debt.md | durable debt ledger | plugins/agent-kit/rules/channels.md:38`
`file:knowledge-slot | file | docs/knowledge/<slot>.md (×8) | the product description every build works from | plugins/agent-kit/rules/channels.md:44`
`file:audits-lens | file | docs/audits/<lens>.md | one lens's findings and work list | plugins/agent-kit/rules/channels.md:40`
`file:advice-lens | file | docs/advice/<lens>.md | one advise-lens's proposal record | plugins/agent-kit/rules/channels.md:43`
`file:deployment-md | file | docs/deployment.md | release-only concerns deferred while stage: development | plugins/agent-kit/rules/channels.md:42`
`file:claude-md-block | file | project's own CLAUDE.md, agent-kit:where block | address list of where the kit's data lives, for non-command readers | plugins/agent-kit/templates/where-things-are.md:27`
`file:verification-yml | file | plugins/agent-kit/verification.yml | the kit-wide catalogue of verification kinds | plugins/agent-kit/verification.yml:1`
`script:validate-sh | script | scripts/validate.sh | the kit's own guard: 20 mechanical checks over its own repo, run before release and by CI | plugins/agent-kit/../scripts/validate.sh:1`
`script:measure-py | script | scripts/measure.py | dev-only cost/turns analyzer over Claude Code session transcripts | scripts/measure.py:1`
`script:release-py | script | scripts/release.sh | version bump + validate + commit + tag | scripts/release.sh:1`
`script:check-py | script | plugins/agent-kit/scripts/check.py | the runtime check every kit command runs against a project's own data layer | plugins/agent-kit/scripts/check.py (3901 lines)`
`script:orchestrate-py | script | plugins/agent-kit/scripts/orchestrate.py | the driver: starts/monitors/hands-off sessions building a batch's or epic's children, reads/writes run.json | plugins/agent-kit/scripts/orchestrate.py:72`
`cmd:blueprint | cmd | /agent-kit:blueprint | interviews the owner, writes .agent-kit/project.yml, docs/knowledge/*, the CLAUDE.md block | plugins/agent-kit/skills/blueprint/SKILL.md`
`cmd:ship | cmd | /agent-kit:ship | builds one feature; writes run.json, may open its own PR, copies manual.md/technical_debt.md templates | plugins/agent-kit/skills/ship/SKILL.md`
`cmd:sprint | cmd | /agent-kit:sprint | runs a batch of features via the driver; closes with docs/runs/<slug>.json | plugins/agent-kit/skills/sprint/SKILL.md`
`cmd:epic | cmd | /agent-kit:epic | runs a queue of batches through gate/build/audit/prove phases | plugins/agent-kit/skills/epic/SKILL.md`
`cmd:next | cmd | /agent-kit:next | bookkeeping: retires delivered branches from docs/runs, advances action state lines | plugins/agent-kit/skills/next/SKILL.md`
`cmd:advise | cmd | /agent-kit:advise | writes docs/advice/<lens>.md and knowledge prose for accepted proposals | plugins/agent-kit/rules/knowledge-writing.md:3`
`cmd:accept | cmd | /agent-kit:accept | reads run.json → manual, docs/manual.md | plugins/agent-kit/rules/channels.md:18,39`
`cmd:fix | cmd | /agent-kit:fix | small unplanned run, still shaped by run.json | plugins/agent-kit/skills/fix/SKILL.md:55`
`ext:github-actions | ext | GitHub Actions | runs .github/workflows/checks.yml on every push, and the kit's own ci.yml | plugins/agent-kit/templates/workflow.yml:9`
`ext:git | ext | git | storage medium for every "git"-durability channel in the table | plugins/agent-kit/rules/channels.md (Lives column)`

## EDGES

`cmd:blueprint -> file:project-yml | copies+fills tpl:project-yml | first run of blueprint, owner present | plugins/agent-kit/skills/blueprint/SKILL.md:188`
`cmd:blueprint -> file:knowledge-slot | copies tpl:knowledge-* then interviews | first touch of each slot, owner present | plugins/agent-kit/rules/knowledge-writing.md:15`
`cmd:blueprint -> file:claude-md-block | writes tpl:where-things-are-md between markers | any time the map is stale | plugins/agent-kit/skills/blueprint/SKILL.md:192`
`cmd:blueprint -> file:technical-debt-md | appends debt owner brought back from using the product | owner reports something wrong while using the app | plugins/agent-kit/skills/blueprint/SKILL.md:122`
`file:project-yml -> script:check-py | read: commands, knowledge verdicts, verification answers | every command's pre-flight | plugins/agent-kit/scripts/check.py (catalogue reads verification via project answers)`
`file:project-yml -> file:workflow-yml | commands.* values fill the CI template's placeholders | ship builds CI | plugins/agent-kit/templates/workflow.yml:7`
`cmd:ship -> file:run-json | creates+writes .agent-kit/runs/<slug>/run.json from tpl:run-json | every feature/errand build | plugins/agent-kit/skills/ship/SKILL.md:105`
`script:orchestrate-py -> file:run-json | Run class reads/writes state, children, spent, session | driving a batch/epic's children | plugins/agent-kit/scripts/orchestrate.py:72-101`
`file:run-json -> script:check-py | check.py --run validates proved_at, verified, mutation, prompt shape | before a run is considered finished | plugins/agent-kit/scripts/check.py (check_runs, :1915)`
`cmd:sprint -> file:batch-json | closing session fills tpl:batch-json into docs/runs/<slug>.json | batch closes | plugins/agent-kit/skills/sprint/references/close.md:229`
`file:batch-json -> cmd:next | next reads branches[] to know which to delete after merge | after a batch's PR merges | plugins/agent-kit/rules/channels.md:41`
`file:batch-json -> cmd:epic | a later gate prices the next scope from spent | epic gate, pricing next batch | plugins/agent-kit/templates/batch.json:18`
`cmd:ship -> file:manual-md | copies tpl:manual-md if absent, appends manual actions | run finds an owner-only action and delivers its own PR | plugins/agent-kit/skills/ship/SKILL.md:267`
`cmd:sprint -> file:manual-md | closing session copies tpl:manual-md, copies every child's manual[] in | batch close | plugins/agent-kit/skills/sprint/references/close.md:124`
`file:manual-md -> script:check-py | check.py --manual runs each proof, deletes closed lines | run explicitly, e.g. before a command | plugins/agent-kit/scripts/check.py:1165`
`cmd:ship -> file:technical-debt-md | copies tpl:technical-debt-md if absent, appends deferred work | run leaves work undone | plugins/agent-kit/skills/ship/SKILL.md:298`
`file:technical-debt-md -> script:check-py | check.py reads/counts open items | every command's status read | plugins/agent-kit/rules/channels.md:38`
`file:verification-yml -> script:check-py | catalogue()/catalogue_defects() parse the kit-wide kind list | every command's pre-flight, blueprint's interview | plugins/agent-kit/scripts/check.py:499-533`
`file:verification-yml -> file:project-yml | blueprint walks the catalogue with the owner and writes verification: answers | blueprint interview, and every 6 months / on manifest change | plugins/agent-kit/templates/project.yml:79-98`
`file:project-yml (verification) -> cmd:ship | ship decides which kinds this change touches, opens run.json → verified records at design time | design step of a feature | plugins/agent-kit/templates/run.json:79`
`file:knowledge-actions -> file:knowledge-actors | actor.verb_object key's actor part must resolve | check_references | plugins/agent-kit/scripts/check.py:333-336`
`file:knowledge-screens -> file:knowledge-actions | "Leads to" transitions name action keys | check_references via REF_RE | plugins/agent-kit/scripts/check.py:104,339`
`file:knowledge-scenarios -> file:knowledge-actions | steps name action keys | check_references via REF_RE | plugins/agent-kit/scripts/check.py:339`
`file:knowledge-slot -> script:check-py | KEY_RE/REF_RE/SOURCE_RE parse every entry for fields, keys, cross-refs, sources | every command's pre-flight status check | plugins/agent-kit/scripts/check.py:89-112`
`script:release-py -> script:validate-sh | runs full validate before tagging | every release cut | scripts/release.sh:49`
`ext:github-actions -> script:validate-sh | ci.yml runs it on push/PR/tag | every push to main, tag push, every PR | .github/workflows/ci.yml:20-21`
`ext:github-actions -> file:workflow-yml | the project's own workflow (built from tpl:workflow-yml) runs on every push, once installed in a downstream project | downstream project pushes | plugins/agent-kit/templates/workflow.yml:28-30`
`file:workflow-yml -> script:check-py | check.py --tests inspects .github/workflows/ to say whether declared commands run outside a session | project status check | plugins/agent-kit/scripts/check.py:2863-2915`
`script:measure-py -> ext:claude-transcripts | reads ~/.claude/projects/<slug>/*.jsonl and subagents/*.jsonl | run by hand by a maintainer | scripts/measure.py:49-54`

## UNCERTAIN / CONTRADICTORY

1. **`entities.md` state/transition cross-check is a stated design intent, not a proven mechanical check.** The template header says "An action that sets a status the entity does not list is a defect, and that cross-check only works if the states are written down" (`templates/knowledge/entities.md:4-5`), but I found no dedicated function in `check.py` that parses an entity's `**States:**` line and cross-validates it against the specific status string an action's "What changes" field sets. `check_references`/`REF_RE` only catch backticked `a.b` cross-file key references, not free-text status names inside a field. This looks like an aspiration recorded in the template that the checker does not yet enforce mechanically — worth flagging as a gap between stated design and implemented check, though I did not exhaustively search all 3901 lines of check.py for a status-specific parser, so this is a moderate- rather than high-confidence claim.

2. Resolved during writing: `verification.yml` has exactly 12 kind entries (`grep -c "^[a-z_]*:$" verification.yml` = 12: suite, end_to_end, mutation, types, lint, static_analysis, architecture, visual, contract, performance, accessibility, security). Table above reflects this.

3. **`stack.md`'s `[found …]` and `[frame …]` markers have no worked example anywhere in `templates/knowledge/stack.md` itself** — the template's own file (`templates/knowledge/stack.md`) never shows their syntax; the only descriptions live in `rules/channels.md:30-31` and in `run.json`'s `_frame` comment (`templates/run.json:84`). This is a template whose full shape is split across two other files rather than self-contained — consistent with the kit's own stated rule that "the shape is in the template, never in the command" (`rules/knowledge-writing.md:13`), yet here part of the shape (these two markers) is documented only in `rules/channels.md` and `run.json`, not in `stack.md`'s own header comment. Possible drift between principle and practice, though minor since `channels.md` is itself a shared kit-level rule file, not a command.

4. **No template file define exists for `docs/deployment.md` or `docs/advice/<lens>.md`** among the files I was asked to read — both are real, checked channels (`rules/channels.md:42-43`, confirmed live via `check.py` path constants) but have no corresponding file under `plugins/agent-kit/templates/`. This is expected/by-design (their shape is prose composed at write time, not a fixed record template) but is worth naming explicitly since every *other* durable file in the data layer does trace to a template in this sector.

5. **`templates/where-things-are.md`'s own doc-map text is slightly out of sync with `rules/channels.md`'s fuller table**: the where-things-are block (read by non-kit sessions) does not mention `docs/deployment.md`, `docs/advice/`, or the in-source markers (`agent-kit:unmet`, `agent-kit:scenario`, `[assumed …]` etc.) at all — which is explicitly intentional per its own header ("An address list, not documentation... only the lines that are true today" — `templates/where-things-are.md:20-21`, and it is meant to be a *short form* of `rules/channels.md`, `where-things-are.md:22-24`), so this is confirmed-by-design rather than a defect, but any diagram of the full kit should not treat `where-things-are.md`'s list as the complete channel set — it is deliberately partial.

6. **Every field-writer/reader pairing above is only as strong as `validate.sh`'s own check #16 (run.json/batch.json field coverage)** — that check only proves a field's *name* appears as a word in ≥2 payload files, not that one file actually writes it and the other actually reads it semantically. So while `validate.sh` passing is evidence no field is completely orphaned, it is not proof of correct writer/reader direction for every one of run.json's ~35 top-level fields; I traced the important ones (manual, verified, mutation, proved_at, frame, needs, prompt, spent, handoff, waiting_on, review) explicitly via `rules/channels.md`'s per-field rows, which is the stronger source.
