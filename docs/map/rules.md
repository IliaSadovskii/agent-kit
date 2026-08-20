# Sector: rules

All nine files live in `plugins/agent-kit/rules/`.

## Rule: asking.md
### WHAT IT GOVERNS
How any command puts a question to the owner. One rule: ask with the `AskUserQuestion` tool and
choices, not prose; do the fact-finding first; ask only what is genuinely a fork. (rules/asking.md:1-8)

### MECHANICS
- Use the interactive tool `AskUserQuestion` with written-out options, the recommended one marked
  first, never a prose question. (asking.md:6-10)
- **2 to 4 options**, batch every independent question into one call; but a question whose answer
  would change another may not travel with it — ask the fork first, then follow up. (asking.md:20-28)
- Exception: a "telling" (open interview move, e.g. "take me through a lesson") is not a fork —
  there the open question *is* the move, and choices come after, built from what was said.
  (asking.md:34-47)
- Test before asking: "name the fact that would settle this, and say why you cannot get it" — a
  fact in a file/repo/program output/the web must be fetched first; only a genuine preference
  (cheaper vs fuller, sooner vs safer, owner's own business) is worth a round. (asking.md:49-64)
- The recommended option carries one line on why it's expensive to get wrong (stored data, an
  outside contract, a permission boundary, money). (asking.md:69-74)
- Things that need no answer go in prose (report text), never dressed as a question. "Never ask a
  question nobody can act on" — if nothing will change from the answer, record it instead and let
  it reach the owner through the pull request. (asking.md:76-84)
- `gate: none` in the run file = nobody to ask: the fork becomes a recorded assumption, run carries
  on; never ask anyway, never wait. (asking.md:86-91)

### READERS (command -> at which step)
- `sprint/SKILL.md:77` — asking the batch composition question, "with options, the recommendation
  first"
- `sprint/SKILL.md:105` — a case where two questions can't travel together per this rule
- `ship/SKILL.md:61` — design-step question to the owner
- `blueprint/SKILL.md:37` — "every question you put to the owner follows" this, interview-wide
- `blueprint/SKILL.md:370` — batching several questions on one screen
- `epic/SKILL.md:191` — the scope-or-narrower gate question, "options with counts"
- `advise/SKILL.md:171` — putting proposal rows to the owner
- `rules/preflight.md:73` — the "say the count, put it up as a choice" step at a build command's
  gate references this rule for format

### IO
Reads: nothing of its own (each caller supplies the facts already gathered). Writes: nothing
directly — the answer lands wherever the calling command directs (an entry, `run.json` → `answers`,
etc., per rules/channels.md row for `waiting_on`).

### COMMANDS RUN
None — this is a UI/interaction rule, not a script-driving one.

### REFUSALS IT CAUSES
Not a refusal rule per se; it forbids a *behavior* (asking with prose, asking without having done
the legwork, asking two dependent questions at once, asking a question nobody can act on) rather
than stopping a command outright.

### ENFORCED BY A PROGRAM?
Prose only. No hook or check.py logic validates that a command used `AskUserQuestion` with 2-4
options, or that the fact-finding happened first.

---

## Rule: audit-boxes.md
### WHAT IT GOVERNS
Who may tick a checkbox in an audit lens's own work list, `docs/audits/<lens>.md`, and what a tick
must rest on. (rules/audit-boxes.md:1-6)

### MECHANICS
- The file belongs to the lens that wrote it; the lens rewrites it whole on its next run. Between
  runs, **only a box** may change, and only three sessions may change one: the session that closes
  a batch, `next`, and `accept`. (audit-boxes.md:1-6)
- A tick must rest on one read (never inferred) fact: (a) the item's own work is in a merged pull
  request — that number goes in the line; or (b) the entry it names is `built` and the change is in
  that PR's diff. (audit-boxes.md:12-19)
- Asymmetric risk: an item left open costs the next reader 10 seconds; a guessed tick removes the
  item from every future list until the lens's next run (months out) — `next`/`sprint` won't see it
  again. Unsettleable items are left alone and reported instead. (audit-boxes.md:20-26)
- **The literal form**: `` - [x] закрыто PR #<n> `` — sentence in the project's language, box and
  number stay literal/English. (audit-boxes.md:27-33)
- A refusal is written by the lens itself as `` - [x] `declined`: … `` — never a PR-closed tick.
  (audit-boxes.md:34-35)
- **Commit rule**: its own `docs(audits): …` commit with nothing else in it. (audit-boxes.md:37-41)
- **Untouched items stay untouched** — no rewording, reordering, or dropping stale-looking items;
  that is the lens's job on its next run. (audit-boxes.md:43-45)

### READERS (command -> at which step)
- `sprint/references/close.md:132` — closing session ticking items its features finished
- `accept/SKILL.md:113` — accept verifying and ticking items whose work it verified
- `next/SKILL.md:46` — `next` raising/ticking, "where the evidence, the form and the commit rule"
  live

### IO
Reads/writes: `docs/audits/<lens>.md` (tick the box, in its own `docs(audits): …` commit).

### COMMANDS RUN
None directly; the mechanism is a git commit convention, not a script invocation.

### REFUSALS IT CAUSES
Not a hard refusal — a norm that only three named sessions may edit a box, and any tick without a
verified fact must instead be left alone (with the miss reported).

### ENFORCED BY A PROGRAM?
**Yes, partially.** `check.py`'s `check_channels()` scans every `docs/audits/*.md` file for a
checked box (`- [x]` / `- [X]`) that names neither a `#<PR number>` nor carries `` `declined` `` —
flagged as drift: "audit items are ticked without naming the pull request that closed them"
(plugins/agent-kit/scripts/check.py:2226-2248). It does **not** verify who made the edit or that the
underlying fact (merged PR / entry `built`) is true — only that the number is present.

---

## Rule: channels.md
### WHAT IT GOVERNS
The full inventory of every durable communication channel in the kit — for each: who writes it, who
reads it, who may close it, what becomes impossible without it, and how durable it is (four kinds of
storage). (rules/channels.md:1-11)

### MECHANICS
A 40-row table (channels.md:14-50) covering, among others:
- `run.json` and each of its fields (`children`, `handoff`, `manual`, `needs`, `frame`, `mutation`,
  `proved_at`, `prompt`, `spent`, `waiting_on`) — machine-only, lives in `.agent-kit/runs/` which is
  git-ignored.
- `run.log`, `control` — driver-only / window-only files beside `run.json`.
- In-entry marker blocks: `[assumed …]`, `[found …]`, `[frame …]`, `[stale …]`, `[accepted …]`, an
  entry's `state:` line, `agent-kit:unmet <key>`, `agent-kit:scenario <heading>` — each with its own
  writer/reader/closer (git-durable).
- Project-level files: `docs/technical_debt.md`, `docs/manual.md`, `docs/audits/<lens>.md`,
  `docs/runs/<slug>.json`, `docs/deployment.md`, `docs/advice/<lens>.md`, `docs/knowledge/<slot>.md`.
- Kit/project manifests: `verification.yml` (in the plugin), `project.yml` → `verification`,
  `run.json` → `verified`, `.agent-kit/project.yml`, `.github/workflows/<name>.yml`.
- The pull request body and comments — written by the closing session, read by the owner, closed by
  the merge, lives on GitHub. (channels.md:50)
- "**What is in it is what a program checks**" — a row whose rule can't be checked mechanically is
  prose in the owning command instead. (channels.md:8-11)
- "**Why there is no single bus**" — different readers need different transports: `agent-kit:unmet`
  works because it's a grep-able source comment; `docs/technical_debt.md` because a person reads it;
  `run.json` because a program does. (channels.md:89-96)

### READERS (command -> at which step)
- `templates/where-things-are.md:23` — distinguishes this file (for the kit's own sessions) from
  the project-facing map
- `skills/blueprint/references/blocks.md:5` — "who may delete which is ... in `rules/channels.md`"
  for the marker blocks blueprint manages
- `skills/blueprint/SKILL.md:551` — blueprint is "the only closer of" several rows, cross-referenced
  at its closing step
- `rules/preflight.md:19` — `project.yml` is "blueprint's to write (`rules/channels.md`)" — cited
  when preflight explains why a build command may not ask about missing verification kinds itself
- `scripts/check.py:2203` (`check_channels` docstring) — the table is the authority the mechanical
  check is built from

### IO
Reads: itself, to build a `declared` set of channel families. Writes: nothing itself; it is
descriptive of every other file's IO in the kit.

### COMMANDS RUN
None directly.

### REFUSALS IT CAUSES
None directly (it's a reference table), but it underlies refusals elsewhere (e.g. preflight's
"never ask yourself" about verification kinds, because `project.yml` belongs only to `blueprint`).

### ENFORCED BY A PROGRAM?
**Yes, strongly — this is the most heavily enforced rule file in the sector.**
`scripts/validate.sh` step "every durable file the payload names has a row in the channel table"
(scripts/validate.sh:293-347): it parses `rules/channels.md`'s table cells for path-like patterns,
builds a `declared` set of path "families" (e.g. `docs/audits`), then scans every `.md/.py/.json/.yml`
file under the plugin for path-like strings; any family found in the payload but not declared in the
table (and not in the small `NOT_CHANNELS` exception set) fails validation. This is also cross-
referenced by `check.py`'s `check_channels()` (scripts/check.py:2198-2249), which enforces two of the
table's specific promises: no stray files in a run directory, and no audit tick without a PR number
(see audit-boxes.md above).

---

## Rule: closing.md
### WHAT IT GOVERNS
How every command in the kit opens (first line) and closes (last two things): the identity line, the
"say what's thin" report, and the "name the next command" line. (rules/closing.md:1-3)

### MECHANICS
- **Opening**: before the preflight check and before reading anything, one line in the project's
  language: which run this is, what it's building in the owner's words (not entry keys), and where
  it lands. Max two lines, no plan, no restated task. Example given:
  ```
  2026-08-13-corpus-a-02-cards-a1 · пишу карточки свода уровня A1 из перечня CEFR-J
  → ветка claude/2026-08-13-corpus-a-02-cards-a1, дальше карточки A2
  ```
  A handoff session says the same plus which session-in-sequence it is. (closing.md:11-24)
- **Language rule**: everything the owner reads is in the project's language; the kit's own field
  names (`suite`, `handoff`, `frame`, `deliver`, entry keys) stay English because the payload is
  English — the two must never mix by transliteration (example given: "Гоню всю суиту" is wrong;
  say "прогоняю все тесты"). Untranslatable kit terms are used in English, in backticks.
  (closing.md:26-37)
- **Closing report**: say where it is thin, not what was done — what could not be settled, what was
  assumed, what was left alone, where the result is weaker than it looks. Never hand a finding to
  the owner as "your call" / "this is on you" / "needs your decision" — instead say **where it now
  lives**: an assumption under its entry, an unmet promise on its test, undone work as a line in
  `docs/technical_debt.md`. The only thing that may be asked of the owner is what genuinely needs
  their hands/access, and that belongs in the pull request's Manual actions section, not a closing
  line. (closing.md:38-56)
- **Next-command line**: one line, last, with the command already filled in and a reason clause.
  Examples:
  ```
  дальше: /agent-kit:audit тесты — 50 записей помечены built, ни одна не проверена
  дальше: смержи #42, потом /agent-kit:ship guest.report_post — следующее непостроенное в границах MVP
  ```
  One recommendation, never a menu. Name only what follows from *this run's own work*; when nothing
  does, name `/agent-kit:next` explicitly (which reads and ranks the whole project state).
  (closing.md:57-83)

### READERS (command -> at which step)
- `ship/SKILL.md:18` — "before anything else, say who you are in one line", its identity-line rule
- `ship/SKILL.md:418` — its final closing-report step
- `fix/SKILL.md:140` — closing step
- `sprint/references/frame.md:9` — frame child's own identity line
- `sprint/SKILL.md:267` — "close per ... before you go quiet"
- `sprint/references/close.md:3` — batch closing session identity line
- `sprint/references/close.md:270` — batch's final report
- `audit/SKILL.md:242` — a lens's closing report
- `blueprint/SKILL.md:469` — blueprint's closing, "naming the things the owner cannot..."
- `epic/SKILL.md:283` — "close per ..., then stay as the window"
- `advise/SKILL.md:275` — advise's closing report
- `accept/SKILL.md:122` — accept's closing report
- `rules/window.md:79` — the window's own report to the owner about a recorded finding follows
  closing.md's "name where it now lives" shape

### IO
Reads: nothing of its own. Writes: nothing directly — it shapes what a session *says*, not a file
(though its "say where it now lives" step points to `docs/technical_debt.md`, entry blocks, and the
pull request, which are governed elsewhere).

### COMMANDS RUN
None.

### REFUSALS IT CAUSES
None (a shaping/formatting rule for speech, not a gate).

### ENFORCED BY A PROGRAM?
Prose only — no hook or check.py validates the identity line, the closing shape, or the "дальше:"
line's presence/format.

---

## Rule: craft.md
### WHAT IT GOVERNS
The shared coding standard for the three sessions that write or judge product code: `ship`, `fix`,
and the reviewer. Four rules, deliberately capped at four because instruction-following degrades
with instruction count. (rules/craft.md:1-14)

### MECHANICS
Four rules:
1. **Make the product true, never the check quiet** — never edit a test to fit the code, branch on
   the test's own input, hard-code a value for the test's case, bend an equality/serializer, or make
   state answer differently the second time. Where the check itself is wrong, stop and say so (a
   `blocker` if it stops the feature, a line in `notes` if not, a question if somebody is present)
   rather than deciding alone. Cites a benchmark: frontier models cheat 46-93% of the time on
   dishonest-test tasks; a single sentence telling them to stop cut one model to 1% where the
   conflict was visible. The neighboring, allowed case: an entry that contradicts standing code is
   recorded via a test marked `agent-kit:unmet` (per `ship`). (craft.md:15-39)
2. **A stand-in proves the stand-in** — mocks/fakes/fixed clocks/stubbed sign-in only where the real
   thing is unreachable from a test; the reason goes beside it in the test, and the seam is named in
   the run file's `suite` field. Cites: coding agents mock in 36% of commits vs 26% for humans.
   (craft.md:41-53)
3. **Nothing the entry did not ask for** — no extra abstraction, config switches, defensive
   branches, or duplicate implementations of something `stack.md`'s library map already names. Cites
   a 623M-change study: duplicated blocks +81%, copy-paste-in-commit +41%, refactoring moves -70%,
   cross-file calls -35% as agent authorship grew. (craft.md:55-65)
4. **The door out is marked** — not being able to do something is a legitimate result: `unmet` for a
   broken promise, `blockers` for what stopped the run, a `docs/technical_debt.md` line for
   understood-and-set-aside work, a parked feature. Cites: given a legitimate "impossible" declaration,
   one model's cheating fell from 54% to 9%; another's didn't move — "necessary and not sufficient".
   (craft.md:67-76)

### READERS (command -> at which step)
- `ship/SKILL.md:82` — design step, read alongside `stack.md` and the library map
- `ship/SKILL.md:425` — closing step, re-read "expanded" for the `mutation` field
- `fix/SKILL.md:47` — "the four rules about how code is written here"
- `fix/SKILL.md:120` — "expanded — one of its five questions is asked out of that" (reviewer step)
- `agents/reviewer.md:19` — "Read exactly this" item 5: "The kit's craft rules, at the path the run
  gives you" — the reviewer's 5th review question ("is there more here than was asked for?") is
  drawn directly from craft.md's rule 3. Reviewer must say explicitly if given no path
  (reviewer.md:19-22).

### IO
Reads: nothing of its own. Writes: nothing directly, but drives writes to: a `blocker` in the run
file, a `notes` line, `suite` (naming a seam/stand-in), `agent-kit:unmet` test marks, `blockers`,
`docs/technical_debt.md`, a parked-feature record.

### COMMANDS RUN
None directly (the "make the check agree" prohibition is about test-editing behavior, not a script).

### REFUSALS IT CAUSES
Not a hard stop by itself; it prescribes "stop and say so" when a check is legitimately wrong,
routed as a blocker/note/question depending on context, rather than silently forcing the check to
pass.

### ENFORCED BY A PROGRAM?
**Partially.** `check.py` enforces the `mutation` field's presence/shape (rule 2's "the stand-in"
companion metric) — a finished `ship`/`fix` that left `mutation` empty where the project declares
`commands.mutate` is drift (scripts/check.py:2643-2651), and the reviewer (an agent, not a program)
is the mechanism that checks rules 1/3 against a diff. Rules 1 and 4 (honesty, marking the door out)
are prose-only / benchmark-justified, not mechanically checked.

---

## Rule: knowledge-writing.md
### WHAT IT GOVERNS
The shared half of how `blueprint` and `advise` — the only two commands that write
`docs/knowledge/` — write into it: template shape, language, entry state, hashing, and the
commit/check discipline. (rules/knowledge-writing.md:1-6)

### MECHANICS
- **The line that separates them from every other command is the owner's presence, not the command's
  name.** A run with nobody present may move an entry's `state:` line and leave a block — never
  write prose (a decision needs someone to make it). With the owner present, their answer is
  transcribed as given — "transcribing, not deciding". (knowledge-writing.md:8-11)
- **Shape lives in the template**, `docs/knowledge/`, one file per slot, copied from
  `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/` on first use; each template header declares `fields:`
  and the done-bar. Read the template for the slot being written — never write from memory.
  (knowledge-writing.md:13-21)
- **Language**: prose in the project's language (from `.agent-kit/project.yml`); headings/labels/
  `fields:` line translated together; keys/statuses/state names stay English.
  (knowledge-writing.md:23-27)
- **New entry = `state: planned`, nothing else** — `building (pr: N)` and `built` belong to other
  commands. (knowledge-writing.md:29-33)
- **Every key an entry names must exist** — actor, then entity, then action, then screen, then
  scenario (the interview order). Cascades must be written whole or not at all; where the owner
  won't settle the rest, leave the whole item as a block. (knowledge-writing.md:35-44)
- **Never write a hash by hand** — a `source: docs/DEVELOPER.md#offers @a3f1c9d1`-style hash is
  computed only by:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --record
  ```
  (knowledge-writing.md:46-57)
- **Write it, commit it, then check it**: one commit per slot as it's settled (a dying session then
  costs one slot, not the sitting); push when there's a remote. Where the commits land (branch, PR
  or not) differs by command and is not shared here. Never assume the checked-out branch is right —
  cites an incident of six commits pushed to a dead post-sprint branch, caught only by the owner
  asking. Then run:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
  ```
  and read it before closing — verifies every declared field has content and every key resolves.
  (knowledge-writing.md:59-85)

### READERS (command -> at which step)
- `blueprint/SKILL.md:13` — "the half both of you share", named at the top of the interview
- `blueprint/SKILL.md:141` — writing a slot mid-interview
- `blueprint/SKILL.md:201` — "which `advise` follows too" cross-reference
- `blueprint/SKILL.md:492` — the commit step, "one commit per slot as it is..."
- `advise/SKILL.md:179` — "read the slot's template and write from" it, when advise writes an
  accepted proposal into knowledge

### IO
Reads: `docs/knowledge/<slot>.md`, `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/*`,
`.agent-kit/project.yml` (for language). Writes: `docs/knowledge/<slot>.md` (per-slot commits).

### COMMANDS RUN
- `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --record` — computes/rewrites source and
  dependency hashes so none is typed by hand.
- `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status` — verifies every declared field has
  content and every key resolves; read before closing.

### REFUSALS IT CAUSES
Not itself an exit-with-refusal rule — its violations (writing prose with nobody present, writing a
half-cascade, hand-typing a hash, committing on the wrong branch) are prevented by discipline/process,
though `--status` will surface incomplete records mechanically for the *next* reader.

### ENFORCED BY A PROGRAM?
**Partially.** `check.py --status` mechanically verifies field completeness and key resolution
(the template-shape and "every key must exist" rules). `check.py --record` mechanically prevents
hand-typed hashes by being the only way hashes get written. The "owner's presence" / "transcribe not
decide" / "state: planned only" / "one commit per slot" rules are prose-only.

---

## Rule: preflight.md
### WHAT IT GOVERNS
The single reaction table every build command follows after running the knowledge check at start —
what each possible finding means and what to do about it — plus the special "a run is already in
flight" refusal and the "say what has piled up" gate. (rules/preflight.md:1-9)

### MECHANICS
**The reaction table** (preflight.md:10-22), one row per finding `check.py` can produce:
| Finding | Action |
|---|---|
| a run of this kit is in flight here | do not start (see below) |
| a slot/entry unsettled | stop, name what's missing, offer `/agent-kit:blueprint` |
| no `docs/knowledge/` at all | carry on; say once that tests can only aim at what the task says |
| `[assumed …]` blocks on in-scope entries | with `gate: owner`: show + offer to settle now, write answer into entry + delete block in its own `docs(knowledge):` commit; with `gate: none`: follow as written |
| `[stale …]` blocks on those entries | same transcribe-not-decide handling as assumed blocks |
| entry's state line behind its merged PR | not yours — `next`/`blueprint --check` moves it |
| a declared command that starts nothing (e.g. `commands.test: make test` with no makefile) | stop and name it; fix is one `project.yml` line only `blueprint` may write |
| unanswered/stale (>6mo) verification kinds | say it in one line, offer `/agent-kit:blueprint`; **never ask it yourself** (project.yml is blueprint's, per channels.md); not a stop reason except for `epic`, which refuses to start |
| run file at unknown step/fields | history from an earlier run; not a stop reason, just say it |
| knowledge written by an older kit (fewer fields/sections than template) | not a stop reason, not yours to fix; say the count in one line, carry on; never fill the missing field yourself |
| nothing | continue silently |

- **"A run is already in flight here"**: printed first by the check, one line per run with slug,
  command, step. If it's *this* run's own directory (invoked with `--run`/`--frame`/`--close`/
  `--advance`/`--resume`), ignore it. Otherwise, if a person typed the command, **do not start** —
  applies to `ship`, `fix`, `sprint`, `epic`, `next` (anything that writes code or moves a branch);
  `blueprint`/`advise` never stop this way. Reason: one checkout, one writer — the driver runs every
  child in the project's own directory. Cites an incident (17 August 2026): a second session took
  the tree 40 seconds after a feature's session had it, costing that feature 12 minutes rebuilding
  in an improvised worktree. **What to offer instead**: wait for the run, or (if the work touches no
  code) take a worktree of its own — `git worktree add ../<name> <branch>` — which is what
  `blueprint` does. "The guard hook refuses to move this checkout's branch from a session the driver
  did not register" — this is the *only* way through besides the offers. The owner overrules in one
  sentence; then work happens in a worktree, not the run's tree. (preflight.md:24-54)
- **"Before you start, say what has piled up"**: only when a *person* typed the command (`epic`,
  `sprint`, a hand-typed `ship` — never a driver-raised or `--advance`/`--resume`/closing session).
  Once per run, before any work: say the count in one line (both numbers: blocks on this run's own
  entries + the wider pile), and put it up as a choice per `rules/asking.md` — settle now, hand to
  `/agent-kit:blueprint`, or build as-is. Asked once only. With `gate: none` this section is skipped
  entirely. (preflight.md:56-84)
- Promises-not-kept (`agent-kit:unmet`) are read *differently* by each command and so live in the
  command, not here: `ship` reads the marked test for the entry it's touching; `sprint` counts and
  offers them as a batch with no theme. (preflight.md:86-88)
- Two things this table never does: turn a finding into a stop reason except the in-flight row; and
  rewrite what an entry *requires* (settling a block only transcribes an already-given answer).
  (preflight.md:90-93)

### READERS (command -> at which step)
- `fix/SKILL.md:44` — "react to what it found per..." right after running the check
- `ship/SKILL.md:73` — "then react to it per..." after the preflight check
- `sprint/SKILL.md:46` — "react to what it says per..."
- `next/SKILL.md:24` — cites specifically "under *A run is already in flight here*"
- `epic/SKILL.md:46` — "the usual preflight, per..." — gives counts and entry names
- `epic/SKILL.md:95` — the settle-blocks screen, "transcribe the answer into the entry"
- `advise/SKILL.md:51` — "`rules/preflight.md` is written for the build commands, which must not
  build over an unsettled..." (advise explains why this rule doesn't fully bind it)
- `scripts/check.py:2849` (comment) — notes the answer used to be prose in four places including
  `rules/preflight.md`, now centralized
- `scripts/check.py:3336` (comment) — "the build commands do not start, `blueprint` takes a tree of
  its own" cross-referenced from the in-flight logic

### IO
Reads: whatever `check.py` printed (knowledge state, run-in-flight list, verification staleness,
entry blocks). Writes: `docs(knowledge):` commit when transcribing an owner's settled answer into an
entry (deleting the `[assumed …]`/`[stale …]` block).

### COMMANDS RUN
The knowledge/preflight check itself is invoked by each calling command (not specified with exact
flags inside preflight.md — the command line "stays in each command, because what they ask for
differs", preflight.md:8). The rule itself directs `git worktree add ../<name> <branch>` as the
alternative-to-waiting action.

### REFUSALS IT CAUSES
- **Hard stop**: a person-typed build/branch command refuses to start entirely when another run
  holds the checkout — told to wait, take a worktree, or (owner override) proceed anyway in a
  worktree.
- **Hard stop**: a slot/entry unsettled, or a declared test/build command that starts nothing —
  told to offer `/agent-kit:blueprint`.
- **Hard stop**: `epic` specifically refuses to start on unanswered/stale verification kinds (all
  other commands just note it and continue).

### ENFORCED BY A PROGRAM?
**Yes, for the in-flight detection.** The "run already in flight" line is printed by `check.py`
itself (mechanical), and the actual branch-move refusal is enforced by the `guard.py` PreToolUse
hook (`holds_tree()`/`SWITCH` regex in plugins/agent-kit/hooks/guard.py) — a session not registered
to the in-flight run is refused a `git checkout`/`git switch` in that tree. The reaction *table*
itself (what to say/offer for each finding) is prose that each command follows by hand; the
`--offline`/refusal branching around unanswered verification kinds is check.py-computed but the
"never ask yourself" instruction is prose.

---

## Rule: pull-requests.md
### WHAT IT GOVERNS
The shape and size of every pull request the kit opens, who may open one, and who runs a full-diff
review. "Never merge — the owner merges." (rules/pull-requests.md:1-3)

### MECHANICS
- **Framing**: a PR is "a report to somebody who has other work" — they read the top, decide, and
  go; everything else is for the day someone comes looking. (pull-requests.md:5-9)
- **Three answers stay open, above the fold, nothing else**:
  1. What works now that did not (one line per feature/batch, in the owner's words).
  2. What is needed from the owner to run it here (from `manual` records whose `when` this project's
     `stage` has reached — "Nothing" is the common answer).
  3. What went wrong (composed from fields, never judgement: parked/skipped features, `blockers`, a
     red/unrun suite, `unmet` promises, anything that looks proven and isn't).
  (pull-requests.md:11-23)
- **Everything else folds into `<details>`**, with conclusion + count in the `summary` line.
  (pull-requests.md:24-30)
- **Three size ceilings, and a program counts all three**:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --pr-body <file>
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --pr-base <base>
  ```
  - brief (everything above the first `##`): **2 500 characters**
  - whole uncollapsed body: **4 000 characters**
  - biggest uncollapsed table: **15 rows**
  These replaced a single 12 000-char ceiling in 2.22.0 after one run hit 45 000 characters.
  (pull-requests.md:31-64; constants at scripts/check.py:75-77 `PR_BRIEF_MAX=2500`,
  `PR_OPEN_MAX=4000`, `PR_TABLE_MAX=15`)
- `--pr-base` warns what the PR will actually carry (base...branch diff) before opening — cites an
  incident: a knowledge branch cut from a running `epic` showed 88 files / ~60 commits of someone
  else's work when opened against the default branch. (pull-requests.md:38-51; implemented in
  `pr_base_defects()`, scripts/check.py:3470-3524, which flags any `epic/…`/`sprint/…` integration
  branch "carried" by this one that the base doesn't already have)
- **"Nothing is left on the owner"**: never say "your call" / "this is on you" / a column named
  after them — except **Manual actions**, and even there the line says what to do, not whose fault
  it is. Every leftover is *already* recorded in a file; the PR's job is to say **what raises it
  again**:
  | Where it is | What raises it |
  |---|---|
  | `[assumed …]`/`[stale …]` block under an entry | the check prints it before every command; `blueprint` rewrites the entry and deletes the block |
  | a test marked `agent-kit:unmet` | the check lists it; `sprint` with no theme offers it as a batch |
  | a line in `docs/technical_debt.md` | the check counts it; `sprint` with no theme offers it |
  | an item in an audit's work list | that lens's next run; `next` when it comes due |
  (pull-requests.md:65-91)
- **Sections, in order**:
  - **What & why** — ≤5 lines: which entry, what it now does, anything unusual.
  - **Manual actions** — only what needs hands *and* access; one line each (what/where/why), grouped
    by *when* (before it runs at all / before this merges / before it ships); **never collapsed**.
    `stage` in `.agent-kit/project.yml` decides which group prints — at `development`, "before it
    ships" items go to `docs/deployment.md` instead and are named here only as a count (cites: on one
    run a third of 19 items were this, burying the 6 that mattered). Empty `stage` = print
    everything + say it's unanswered. Each line's proof is a command exiting 0; the same records go
    into `docs/manual.md` where `check.py --manual` runs them later and deletes what's done. Two
    false-positives named explicitly: scriptable actions belong in `commands.run`, not here; a
    working default setting is an Assumption, not an action.
  - **Assumptions** — every decision taken without the owner, table of decision+why, **collapsed**,
    summary carries both counts (how many, how many are expensive). Mark ones also written as
    `[assumed …]` blocks so the reader knows where to answer.
  - **What was hard** — 3-5 lines, collapsed, skipped when nothing fought back.
  - **Proven** — collapsed with one exception (see below): which entry lines have a test, what the
    suite returned and **the commit it returned it on** (from `proved_at`); every seam a proof went
    through a stand-in at, by name (from `suite`); what `verified` says per kind, including a `why`
    excuse; what `mutation` says (killed/survived counts, or why the step didn't run). **The
    exception**: what looks proven and isn't goes up into answer 3 instead — `unmet` promises and
    untested scenarios are named above the fold; the evidence stays in this block.
  - **Review** — reviewer's findings and how each was closed; whether the security pass ran/was
    skipped and why. Collapsible, count in summary.
  - **Changes** — key files/role as a table. Collapsible.
  - A Mermaid diagram when flow changes; tables for anything enumerable.
  (pull-requests.md:93-168)
- **Who may run a full-diff review**: a feature never does (already reviewed against its entry); a
  batch *offers* `/code-review` in its closing line but never runs it itself; a run of many batches
  (epic) doesn't offer it either — its diff was already read twice with unique context (reviewer per
  entry, audit lenses over the branch). (pull-requests.md:170-182)
- **A feature inside a batch opens none of its own** — its branch is pushed; a standalone PR is one
  `gh pr create --base <its base> --head <its branch>` away on demand, printed per-feature by the
  batch's own PR. Opening them in advance caused two merge accidents (a feature merged into its
  parent branch instead of default) and a review plugin silently skipping drafts. How a batch/epic
  composes its shared PR is delegated to
  `${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/close.md` — deliberately not duplicated here since
  only that one session ever does it. (pull-requests.md:184-196)

### READERS (command -> at which step)
- `fix/SKILL.md:125` — opening the PR, "with the cause in the..."
- `ship/SKILL.md:381` — step 4, "open the pull request per..."
- `ship/SKILL.md:450` — cross-reference on batch-vs-run PR distinction
- `sprint/references/close.md:67` — "sections and their order are..."
- `sprint/references/close.md:178` — "who may run a review... and nowhere else"
- `advise/SKILL.md:237` — "then one pull request for the round, per..."
- `epic/references/finish.md:148` — "do not offer a fresh review of the whole diff"

### IO
Reads: `run.json` fields (`manual`, `assumptions`, `suite`, `proved_at`, `verified`, `mutation`,
`blockers`), `.agent-kit/project.yml` → `stage`/`language`. Writes: the PR body/comments (GitHub);
`docs/deployment.md` (stage=development manual-action overflow); `docs/manual.md` (same manual
records, durable copy).

### COMMANDS RUN
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --pr-body <file>   # counts brief/open/table sizes
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --pr-base <base>   # what the PR diff will carry
gh pr create --base <its base> --head <its branch>                    # opening a feature's own PR on demand
```

### REFUSALS IT CAUSES
- `--pr-body` returns a defect (exit 1) when any of the three size ceilings is exceeded — the rule
  says to shrink/fold before opening/editing, not to open oversized.
- `--pr-base` returns a defect when the branch carries a whole `epic/…`/`sprint/…` integration
  branch the base lacks — told to rebase onto the base first and open there instead.
- The reviewer-run rule refuses a feature or an epic-level session from ever running a full-diff
  review itself — only a batch may *offer* it, never run it.

### ENFORCED BY A PROGRAM?
**Yes, mechanically, for size and composition** — `check.py --pr-body` (`pr_body_defects()`,
scripts/check.py:3531-3593) and `check.py --pr-base` (`pr_base_defects()`, scripts/check.py:
3470-3524) are run before every PR open/edit. The section shape, "nothing left on the owner"
wording, and who-may-review rule are prose-only, followed by the closing session/`sprint/references/
close.md` by convention.

---

## Rule: window.md
### WHAT IT GOVERNS
What the control-window session (the one that briefed a batch, or a later session the owner opens)
does while a driver runs a batch unattended: report state, relay driver news, and pass exactly two
steering instructions back — nothing else. (rules/window.md:1-16)

### MECHANICS
- **Role**: the driver builds features; the window answers the owner's questions, speaks when the
  driver has news, passes two instructions. Usually it's the session that briefed the batch, still
  standing after the driver took it; can also be a session the owner opened afterward, in which case
  it must say it wasn't there when the batch was composed. The driver types news at whatever session
  is named in `window` in the batch's run file; if that's now this session, it should self-register
  via `tmux display-message -p '#{session_name}'`. (window.md:1-11)
- **"You decide nothing, and the run does not depend on you"** — if closed, the batch loses only its
  narrator. Never take work on itself, never edit code, never touch a feature's run file, never
  start its own session. (window.md:13-16)
- **Where it looks**: `run.json` in the batch dir (`children` order, `step`); each child's `run.json`
  (`step`, `branch`, `pr`, `assumptions`, `blockers`, `waiting_on`); the tail of `run.log` in either
  (the driver's own trace, the only record of *when*). **Never open a child's transcript** (largest
  file, would spend context on an unasked-about feature). Read on demand, not on a schedule.
  (window.md:18-28)
- **Answering**: give state (which feature building/since when, which done and where their branches
  are, which parked and why, any expensive-if-wrong assumption), 3-4 lines, for a phone reader. If a
  child has `waiting_on`, say what it's asking and that answering means typing into that child's
  own session directly — the window never relays answers, because the child has the context.
  (window.md:30-42)
- **Driver pokes**: the driver types lines beginning with `[driver]`, only for things worth the
  owner's attention (feature started/parked, an account limit and wait length, batch finished). The
  window turns it into one plain sentence in the project's language — this becomes the owner's phone
  notification. No embellishment, no investigation, no asking if they want anything done.
  (window.md:44-52)
- **"You report; you do not ask"** — never put a question to the owner, about anything: only a child
  may ask (it has the context and the ability to act on the answer, and only while still building).
  An answer given to the window changes nothing. When a feature records something expensive
  (decision without the owner, code-vs-entry contradiction), **say it as a statement**: what was
  recorded, which feature, that it'll be in the batch's PR under Assumptions. If the owner thinks
  it's wrong, they have the lever: *stop*. The ban is on the shape, not the question mark — "your
  call now" / "this one is on you" / "either the entry is wrong or the code is" are banned exactly
  like a literal question, because a reply given to the window "dies in your window while the
  finding reaches the pull request anyway, unchanged". Ends with a 3-line worked example (window.md:
  81-84) closing per `rules/closing.md` — names where the thing lives and what raises it again.
  (window.md:54-86)
- **The two instructions**, written into `control` beside the batch's `run.json`:
  | Owner wants | Window writes |
  |---|---|
  | skip a feature | `skip <that feature's run slug>` |
  | finish this feature, then wind up and deliver what exists | `stop` |
  No third word — there is no "pause"; a pause delivering nothing would leave branches with no PR,
  the exact state a night is lost in. `stop` is resumable via `/agent-kit:sprint --resume`, which
  picks up anything with no PR yet.
  ```bash
  printf 'skip 2026-08-05-offers-03-decline\n' > .agent-kit/runs/<batch>/control
  ```
  The driver reads `control` at the boundary between features and deletes it — nothing interrupts
  mid-feature. Writing anything other than the two exact words still gets the file deleted (and the
  driver logs/reports "not recognised"). Anything the owner wants outside these two is not the
  window's to do — say plainly that stopping the run and doing it themselves is the way, and offer
  `stop`. (window.md:87-115)

### READERS (command -> at which step)
- `sprint/SKILL.md:23` — table entry for `/agent-kit:sprint --window <run dir>`, "stand beside a run
  somebody else started"
- `sprint/SKILL.md:261` — "from here on you follow..." — the point sprint's session becomes a window
- `epic/SKILL.md:284` — "unchanged. The owner steers with the..." — epic's closing session becomes a
  window the same way
- `scripts/orchestrate.py:591-600` — the driver's `WINDOW_RULE` string, sent once per driver as the
  first `[driver]` message to the registered window session: "you are this run's window: turn the
  lines below into one sentence for the owner, decide nothing, investigate nothing, and never put a
  question to them — the rule is rules/window.md, read it before you answer anything." Triggered by
  `Driver.tell()` on first call (orchestrate.py:598-610).

### IO
Reads: `.agent-kit/runs/<batch>/run.json` (`children`, `step`), each child's `run.json`
(`step`,`branch`,`pr`,`assumptions`,`blockers`,`waiting_on`), `.agent-kit/runs/<batch>/run.log`
(tail only). Writes: `.agent-kit/runs/<batch>/control` (one of two literal instructions).

### COMMANDS RUN
```bash
tmux display-message -p '#{session_name}'          # self-register as the window if it's a fresh session
printf 'skip <slug>\n' > .agent-kit/runs/<batch>/control
printf 'stop\n' > .agent-kit/runs/<batch>/control
```

### REFUSALS IT CAUSES
The rule itself is a set of behavioral prohibitions on the window session (never ask, never decide,
never edit code/run files, never relay a child's answer) rather than a program-enforced refusal. The
one exit-code-like refusal: an unrecognised `control` line is silently discarded by the driver
(orchestrate.py:1066-1068), and the driver reports it as not recognised.

### ENFORCED BY A PROGRAM?
**Mechanically for the `control` file mechanism** — `take_control()` (orchestrate.py:546-548) reads
and clears `control`; the driver's loop (orchestrate.py:1054-1068) interprets exactly `skip <slug>`
and `stop`, discards anything else. The **prohibition on asking questions / deciding / editing code**
is prose only, reinforced by the driver sending the `WINDOW_RULE` reminder text once per session
(orchestrate.py:589-600) — a nudge, not an enforcement (nothing stops the window session from typing
a question; it just isn't given tools or a consumer for the answer).

---

## NODES

`rule:asking` | rule | Asking the owner | when/how a command puts a fork to the owner via AskUserQuestion | rules/asking.md:1
`rule:audit-boxes` | rule | Ticking a box in an audit's work list | who may tick `docs/audits/<lens>.md` boxes and what a tick must rest on | rules/audit-boxes.md:1
`rule:channels` | rule | Every channel this kit has | the writer/reader/closer/durability table for every mechanism in the kit | rules/channels.md:1
`rule:closing` | rule | How a command speaks | identity line, closing report shape, next-command line | rules/closing.md:1
`rule:craft` | rule | Craft | four coding standards shared by ship/fix/reviewer | rules/craft.md:1
`rule:knowledge-writing` | rule | Writing into the knowledge | shared discipline for blueprint/advise writing docs/knowledge | rules/knowledge-writing.md:1
`rule:preflight` | rule | What the check found, and what you do about it | the reaction table every build command follows after the knowledge check | rules/preflight.md:1
`rule:pull-requests` | rule | Pull requests | PR body shape, size ceilings, who opens/reviews | rules/pull-requests.md:1
`rule:window` | rule | The control window | what a standing-by session does/does not do during a driver-run batch | rules/window.md:1
`gate:run-in-flight` | gate | run already in flight | preflight's hard-stop when another session holds the checkout | rules/preflight.md:24
`gate:piled-up` | gate | say what has piled up | preflight's once-per-run pile-of-decisions gate, person-typed commands only | rules/preflight.md:56
`file:run.json` | file | run.json | per-run machine state file, git-ignored | rules/channels.md:15
`file:control` | file | control | window's steering file for the driver | rules/window.md:87; rules/channels.md:27
`file:docs-audits` | file | docs/audits/<lens>.md | a lens's own audit work list with tick boxes | rules/audit-boxes.md:1
`file:docs-manual` | file | docs/manual.md | durable list of manual actions, closed by check.py --manual | rules/channels.md:39
`file:docs-technical-debt` | file | docs/technical_debt.md | undone-work ledger, raised by sprint | rules/channels.md:38
`file:docs-knowledge` | file | docs/knowledge/<slot>.md | product knowledge entries | rules/knowledge-writing.md:15
`file:docs-deployment` | file | docs/deployment.md | release-only manual actions, deferred while stage=development | rules/pull-requests.md:105
`script:check.py` | script | check.py | mechanical checker: --status, --sync, --record, --run, --pr-body, --pr-base, --manual | scripts/check.py
`script:validate.sh` | script | validate.sh | kit-level validator, includes the channels-table completeness check | scripts/validate.sh:293
`script:guard.py` | script | guard.py | PreToolUse hook refusing merge/force-push/default-push/branch-switch during a live run | plugins/agent-kit/hooks/guard.py
`script:orchestrate.py` | script | orchestrate.py | the driver: runs children, reads control, sends [driver] news to the window | scripts/orchestrate.py
`cmd:AskUserQuestion` | cmd | AskUserQuestion | interactive tool for owner-facing forks | rules/asking.md:8
`session:window` | session | window session | the standing-by narrator session for a batch | rules/window.md:1
`session:driver` | session | driver | orchestrate.py's process managing a batch's children | rules/window.md:3
`ext:pull-request` | ext | GitHub pull request | the report surface read by the owner, merged only by them | rules/pull-requests.md:1-3

## EDGES

`rule:asking -> cmd:AskUserQuestion | invoked with 2-4 options, recommendation first | every owner-facing fork | rules/asking.md:6-10`
`rule:preflight -> rule:asking | "put it up as a choice" | the piled-up gate, once per run | rules/preflight.md:73`
`gate:run-in-flight -> script:guard.py | SWITCH regex refuses git checkout/switch in the held tree | a non-registered session tries to move the branch | rules/preflight.md:50-51; hooks/guard.py holds_tree()`
`gate:run-in-flight -> file:run.json | check.py reads run.json step across .agent-kit/runs/ to print in-flight lines | before every command | rules/channels.md:15`
`rule:audit-boxes -> file:docs-audits | tick written as - [x] закрыто PR #<n> | batch-closing session / next / accept, each in own docs(audits): commit | rules/audit-boxes.md:27-41`
`script:check.py -> file:docs-audits | check_channels() flags a tick with no #<n> and no \`declined\` | every command's preflight | scripts/check.py:2226-2248`
`rule:channels -> script:validate.sh | validate.sh parses the table's declared path families | kit release validation | scripts/validate.sh:293-347`
`rule:closing -> ext:pull-request | "the only thing that may be asked of the owner ... belongs in the pull request under Manual actions" | every command's closing step | rules/closing.md:54-55`
`rule:craft -> agent-kit:reviewer | "the kit's craft rules, at the path the run gives you" feeds the reviewer's 5th question | reviewer's read-in step, given a run/entry to judge | agents/reviewer.md:19-22, 90`
`rule:craft -> script:check.py | mutation field presence checked when commands.mutate is declared | finished ship/fix | scripts/check.py:2643-2651`
`rule:knowledge-writing -> script:check.py | --record computes hashes; --status verifies fields/keys | blueprint/advise commit step | rules/knowledge-writing.md:52-85`
`rule:pull-requests -> script:check.py | --pr-body counts brief/open/table sizes; --pr-base checks carried branches | before opening/editing any PR | rules/pull-requests.md:31-43; scripts/check.py:3470,3531`
`rule:pull-requests -> file:docs-deployment | stage=development manual actions moved here instead of Manual actions section | closing session composing a PR | rules/pull-requests.md:103-109`
`rule:pull-requests -> skills/sprint/references/close.md | delegates the actual PR-composition mechanics for batch/epic | batch or epic closing | rules/pull-requests.md:192-195`
`session:window -> file:control | writes exactly "skip <slug>" or "stop" | owner gives a steering instruction | rules/window.md:87-103`
`session:driver -> file:control | take_control() reads and deletes it at a feature boundary | between children | scripts/orchestrate.py:546-548,1054-1068`
`session:driver -> session:window | sends "[driver] ..." lines, first one prefixed with WINDOW_RULE reminder | on news worth the owner's attention | scripts/orchestrate.py:589-610`
`rule:window -> rule:closing | the window's own report ("03-scheduler is done...") follows closing.md's "name where it lives" shape | reporting an expensive finding | rules/window.md:79-84`
`rule:preflight -> file:docs-knowledge | transcribes an owner's settled [assumed…]/[stale…] answer, docs(knowledge): commit | gate:owner, before build starts | rules/preflight.md:15-16`

## BLOCK / RECORD FORMATS

- **Audit tick** (rules/audit-boxes.md:29-31):
  ```
  - [x] закрыто PR #<n>
  ```
  Written by: the batch-closing session, `next`, or `accept` — each ticking only what it verified.
  Closed/rewritten wholesale by: the lens itself, on its next run (the tick just marks progress
  between runs). Refusal form written by the lens: `` - [x] `declined`: … ``.

- **Manual action record** (rules/pull-requests.md → Manual actions section, and rules/channels.md
  row `run.json → manual`): one line each — what, where, why — grouped by `when` (before it will run
  at all / before this merges / before it ships), each carrying a `proof` that is a command exiting
  0 once done. Written by: the run that found it needs the owner's hands and access. Copied into
  `docs/manual.md` by the closing session in the same commit as the ledger. Closed by: `check.py
  --manual`, which runs each proof and deletes lines whose work has happened; the owner for the few
  no command can answer.

- **`[driver] …` line** (rules/window.md:87-89, scripts/orchestrate.py:598-610): typed by the driver
  into the window's tmux session — pure speech, never persisted, no reader but the window session.
  First occurrence per driver is prefixed with the `WINDOW_RULE` reminder text.

- **`control` instruction** (rules/window.md:87-111): exactly one line, one of two words —
  `skip <run slug>` or `stop`. Written by: the window (on the owner's behalf), or nothing. Read and
  deleted by: the driver, at the boundary between features — regardless of whether the line was
  recognised.

- **PR body budgets** (rules/pull-requests.md:53-64, enforced in scripts/check.py:75-77): brief
  (before first `##`) ≤ 2500 chars; whole uncollapsed body ≤ 4000 chars; biggest uncollapsed table
  ≤ 15 rows. `<details>` content is excluded from all three counts.

- **Source hash** (rules/knowledge-writing.md:46-51): `source: docs/DEVELOPER.md#offers @a3f1c9d1`
  — written only by `check.py . --record`, never typed or copied by hand.

- **Entry state line** (rules/knowledge-writing.md:29-33): `state: planned` is the only value a
  knowledge-writing session may write for a new entry; `building (pr: N)` and `built` are written by
  other commands (per rules/channels.md's `state:` row).

## UNCERTAIN / CONTRADICTORY

- **No orphan rules found.** All nine rule files in this sector have at least one confirmed reader
  outside the rules directory (grep-confirmed pointer in a SKILL.md, an agent file, or a script).
  `window.md` is the rule with the fewest command-level pointers (only `sprint` and `epic`
  explicitly hand a session the window role) but it is additionally enforced/reinforced at the
  mechanism level by `orchestrate.py`'s `WINDOW_RULE` string and the `control`-file protocol, so it
  is well-anchored, not orphaned.

- **preflight.md's authority is partly borrowed, not owned.** The rule file states plainly that "the
  command line itself stays in each command, because what they ask for differs" (preflight.md:8) —
  meaning preflight.md documents *reactions* to findings but never shows the actual check invocation
  each command runs. This makes it impossible, from this sector alone, to enumerate the exact
  `check.py` flags each command passes; that detail lives in each SKILL.md, not here. Not a
  contradiction, but a documented gap by design.

- **advise.md is a partial exception to preflight.md**, per its own admission at
  `advise/SKILL.md:51`: "`rules/preflight.md` is written for the build commands, which must not
  build over an unsettled..." — i.e. advise reads preflight.md but doesn't fully bind to it since it
  writes no code. This is consistent with preflight.md's own text (`blueprint` and `advise` never
  stop on the in-flight row) but is worth flagging as a rule file partially opting a reader out of
  itself.

- **Overlap between closing.md and window.md's reporting shape.** window.md explicitly says the
  window's own report to the owner ("03-scheduler is done...") follows `rules/closing.md`
  (window.md:79), even though window.md is not itself a "command" in the sense closing.md defines
  ("every command in the kit opens/closes the same way") — the window is a standing session, not a
  command invocation. This is a deliberate, named cross-reference rather than a contradiction, but it
  means closing.md's scope is slightly broader than its own opening line ("every command...") states.

- **channels.md is the only rule file with a program (`validate.sh`) that treats it as ground truth
  for *every other file in the plugin*** — i.e. it's not just a rule some commands read, it's a
  constraint the entire payload is checked against at validate time. This makes it structurally
  different from the other eight rule files (which are read by specific commands at specific steps)
  and worth marking distinctly in the diagram — it is closer to a schema than a procedure.

- **audit-boxes.md and channels.md both govern the same tick mechanism** (rules/channels.md:40 has
  its own row for `docs/audits/<lens>.md` that restates who ticks/closes it) — this is intentional
  per audit-boxes.md's own opening ("it was a paragraph in each of the three... one said the commit
  rule, one said the form, none said both") consolidating what channels.md's table still references
  in summary form. Not a contradiction — channels.md's row and audit-boxes.md's full rule agree, and
  channels.md explicitly is the "table of four answers" while audit-boxes.md is the full mechanics
  (form + commit rule) — but a reader of only the channels.md row would miss the tick's literal
  syntax and the three-sessions-only restriction, both of which live only in audit-boxes.md.
