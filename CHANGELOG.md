# Changelog

All notable changes to the kit. Versions follow semver from the perspective of a project that
installed it — see [docs/developing.md](docs/developing.md#versioning).

## 1.2.0

- **`advise` — the first command that doubts the description instead of building from it.** Until now
  `blueprint` wrote down what the owner meant and everything else treated that as true: `audit`'s six
  lenses measure code against the knowledge, which makes the knowledge their reference by
  construction. So a mediocre description was built carefully, tested against itself, and audited as
  correct. Three lenses: `product` (what a scenario is missing to finish, what nothing touches,
  what this audience expects and does not find, who is standing next to it unserved), `code` (where
  an approach stops holding at a named volume, and what would make the thing simpler, more reliable
  or faster to change), `money` (what is given away that costs per use, which limits exist on paper
  and nowhere in the code, what somebody would pay for).

  Each lens walks the files and cites them, then steps away and reads the domain — research delegated
  after that reading, never before it, so the reading is something the search can be checked against
  rather than a summary of the first page of results. Every row carries what it rests on: the files,
  the domain, or research with a link and a date. Nothing already `planned`, already in an audit,
  already in the ledger or already refused is raised twice, and what `product.md` says the product
  deliberately does not do may be reopened only by naming what changed.

  The owner decides in one round, and **what they accept is written while they are there** — the
  entry with its fields answered, a stance in `stack.md`, or a line in the ledger when it is work
  rather than a rule. The alternative, a marker for a later `blueprint` session, was rejected: it
  spends the owner's context at the moment it has already evaporated, and leaves a record whose
  closer is a command somebody has to remember to run. Two questions are asked that are not the
  entry's own fields — which scenario covers it, and whether it is inside the MVP bounds — because
  without them `mvp` builds the feature and proves nothing about it.

  Design, with the alternatives rejected on the way: [docs/design/advise.md](docs/design/advise.md).

- **A fourth block kind, `[accepted …]`,** for a proposal the owner agreed to whose fields were left
  for later. Counted and listed by the check like the other three, resolved only by `blueprint`,
  closed by deletion. It is a statement rather than a finding — the decision is made, only the
  interview is outstanding — so it does not turn the check red. `next` treats an open one as work
  rather than noise: unlike the other three it sits under no entry, so no later run arrives to settle
  it in passing.

- **`rules/knowledge-writing.md`**, extracted from `blueprint` rather than written twice, now that
  two commands write into `docs/knowledge/`. The rule underneath both is stated where it can be read:
  what separates them from every other command is the owner's presence, not the command's name — a
  run with nobody to ask moves a state line and leaves a block, and never writes prose.

## 1.1.2

- **Where the kit runs is a note beside the requirements, not a section of its own.** Five commands
  need `git` and `python3` and nothing else; `sprint` and `mvp` need `tmux` and a machine that does
  not sleep, because they wait out account limits by sleeping until the reset.
  [agent-vps](https://github.com/IliaSadovskii/agent-vps) is named as a server already arranged for
  that — any other will do, and the kit knows nothing about either.

## 1.1.1

- **A missing `tmux` says so.** The driver raised a traceback on a machine that simply had not
  installed one; `sprint` and `mvp` now check before composing anything, and the driver refuses with
  a sentence instead of a stack. Five of the seven commands are one session each and need no
  multiplexer at all — the plugin README now says which is which.

## 1.1.0

- **A run says which model its sessions start on.** `model` in the run file, typed into each session
  as `/model <alias>` before its task — rather than passed as a flag, because the launcher this
  server uses takes none and losing it would cost the session its registration and its name in the
  app. `sprint` and `mvp` write the model they are themselves running on unless the owner names
  another, so children inherit the choice made when the session was opened instead of the install's
  default. `orchestrate.py --model` is the whole run's fallback.

  Why it is worth having: measured on a real feature, the kit's own prose is 9.3k tokens of a 139k
  median context — two per cent. The model is the only setting that moves the price of a run rather
  than trimming its edges.

## 1.0.0

The rewrite is complete. Seven commands, one knowledge layer they all build from, and no stubs.

What version 1 is, against the line that ended at 0.17.0: **a feature costs about 15M tokens instead
of 27M**, and a night of five features about 73M. `ship`'s reading set is 9.3k tokens against 13.6k.
The machinery that insured the kit against its own autonomy is gone — what replaced it is a
description the code is held to, a reviewer that reads the entry rather than only the diff, and one
guard outside the model's context.

- **know** — `blueprint` writes what the project is, and `--check` audits it mechanically.
- **build** — `fix` for a defect, `ship` for a feature, `sprint` for a batch built while nobody
  watches, `mvp` for everything inside the MVP bounds.
- **check** — `audit`, six lenses, every verdict carrying a citation.
- **orient** — `next`, for the session opened a week later.

**What this version does not claim.** `fix` and `mvp` are written and have not met a live run. Five
of the seven have, on one real project, and every correction the kit carries came from those runs
rather than from re-reading the text. The number says the shape is finished; the README says which
parts are proven, because a version that waits for proof stops telling anyone what is in the box.

From here semver means what it says: a command removed or renamed is `2.0.0`.

## 0.50.0

**`mvp` is written.** The last stub, and the smallest command in the kit: it owns no build, test or
pull-request logic at all. It composes batches and the driver, `ship` and the closing session do
everything else — which is what the design predicted when it made a sprint's brief optional.

- **One question, at the gate.** The MVP bounds are the owner's prose, so `mvp` derives which
  entries fall inside them, orders them from what the scenarios and preconditions require, chooses
  the audit lenses from what the product is, prices the run — and asks only *this scope, or
  narrower*. Whether the owner is reachable is not asked: a run that lasts a day cannot wait on a
  phone, so every child gets `gate: none` and every fork becomes a recorded assumption.
- **`check.py --mvp` is what it may not start without**: two real MVP bounds, at least one scenario,
  and the commands that start the application and run its suite. Fatal, mechanical, in the project's
  own language — it finds `## Границы MVP` as readily as `## MVP bounds`.
- **Phases live on the run file**, and between them the driver runs rather than a session: gate →
  building → auditing → proving → done. `orchestrate.py` hands back to `/agent-kit:mvp --advance`
  when a batch's parent is an mvp, and that session decides one thing, starts it, and ends. Nothing
  sits watching for hours.
- **The audit goes in waves**: a lens, the sprints that fix what it found, then that lens again over
  the changed code — never twice over the same. It stops when a lens returns only minors, and a cap
  in `finish.waves` stops it regardless, because an audit is never *clean*.
- **`--resume` asks nothing.** Everything the gate settled is in `finish`, so a run that lost its
  driver to a restart or a weekly limit picks up where it stood. The driver now refuses to start
  when a child's session is alive: two drivers over one working tree is how a night ends with
  commits on the wrong branch.
- **The pull request prints `git worktree add`**, so the owner can open a batch without a `git
  checkout` that would pull the tree out from under the children still building in it.

The version stays `0.x`: every command is written now, but `1.0.0` is for the release where every
command has met a live run, and `fix` and `mvp` have not.

## 0.49.0

Two merges, in the two halves of the kit that do not touch each other.

- **`rules/preflight.md`: what the check found, and what you do about it.** `ship` and `sprint` each
  carried their own version of that table, written in different words, and when a third kind of
  block was added one of them did not learn about it — its runs met a record they had no instruction
  for. It is one rule now, shared, and `fix` reacts to the check for the first time: it ran it and
  was told nothing about what to do with what came back.
- **The two developer-facing maps became one.** `docs/developing.md` held *per file, who may write
  it* and `docs/design/the-loop.md` held *per record, who may close it* — the same graph, the same
  reader, the same moment, two places to disagree. The graph holds both views now; `developing.md`
  points at it. Neither is shipped: no run has ever read either, and the page says so.

## 0.48.0

**The first hook.** Never merging a pull request, never force-pushing and never pushing to the
default branch are the kit's oldest rules and were held by instruction alone — which is what a long
autonomous run loses. Two merge accidents happened before this.

- `hooks/guard.py`, a `PreToolUse` hook on Bash. It refuses those three, outside the model's
  context, where nothing can talk it round.
- **It has an opinion only while a run of the kit is at a non-terminal step.** The signal is the
  kit's own state, not a branch name — the hook that keyed on branch names treated every
  conversation held on a feature branch as that feature's pipeline and blocked a live session. With
  no run in flight it exits silently, so the owner's own sessions, `blueprint` and `next` never meet
  it.
- It fails open and says so. A guard that breaks must not stop the work, and it must not go quiet
  either.
- Fourteen tests of its own, and `validate.sh` refuses a release where the hook is unregistered or
  cannot answer. A hook that is not wired up is exactly the thing the audit refused to ship: a rule
  the payload believes in and nothing enforces.

Also: a `CLAUDE.md` at the root of the repository, so the rules for changing the kit — where a new
rule belongs, the four answers a mechanism owes, why a check may never go quiet — are loaded into
every session that works here rather than waiting in a file nobody opens.

## 0.47.0

Found by running 0.46.0 overnight on a live project: five runs wrote their review findings as
sentences — `"major — assertMissing cannot fail. Closed by reordering the fixtures."` — where the
template draws a record. The rule that a run may not finish with an open critical or major finding
was therefore never applied once all night: the check reads `severity` and `closed`, saw neither,
and skipped what it could not read without a word.

- **A finding written as a sentence is now a defect the run must fix before it closes.** Not parsed
  out of the prose: a severity this program guesses at is one it cannot hold anyone to, and
  salvaging it would teach the next run that the field's shape is a suggestion.
- **The check names any field of records filled with sentences**, derived from the template rather
  than from a list — `tasks`, `assumptions`, `answers`, `review.findings`. On the project that
  prompted this, `assumptions` and `tasks` turned out to be prose in seven and five run files, so
  the pull request's Assumptions table and its `expensive` flag were prose too.
- The template says it in one line of its own, and `ship` and `fix` say it where they write the
  field. Only the top-level key names were ever checked before; nothing looked at a shape one level
  down.

## 0.46.0

- **A closing line names what follows from its own work, or it names `/agent-kit:next`.** Every
  command ends by recommending a next step, and the rule asked for one every time — so a command
  that had nothing to say invented something, blind to the rest of the project: it has not looked at
  the branches, the pipeline or the audits since it started, and *build the next entry* while the
  default branch is red is worse than silence. What it does know is its own consequence — a pull
  request to merge, a blocker, the next feature of the batch. Beyond that it hands over to the
  command that reads the whole state and ranks it.

## 0.45.0

- **Questions go up in one round.** The rule said one question per call, and `blueprint` said the
  opposite two files away — batch the independent ones. The owner reads from a phone, where the
  expensive part is the return trip, not the number of taps, so everything that does not depend on
  another answer travels together. What still may not: a question whose answer would change or
  remove another. Ask the one that decides the road first, then put up whatever still stands.

## 0.44.0

A record that can only be closed by a command the owner has to start for that purpose makes every
batch end owing them a command — and `next` recommended exactly that after every sprint, because an
open block made the check unclean and the ladder read unclean knowledge as *not ready*. The block
was the right idea in the wrong place: it had a closer and nowhere to be closed.

- **A block is settled inside work that was happening anyway.** `ship` and `sprint` show the blocks
  on the entries in scope in their first minute, as they always did — and now, when the owner
  answers, they write it into the entry and delete the block in their own `docs(knowledge):` commit.
  Transcribing an answer, never deciding: what an entry *requires* is still `blueprint`'s alone.
- **The session that closes a batch applies the `[stale …]` blocks its children left.** Such a block
  states both halves — what the entry claims, what became true — so putting the second in place of
  the first needs no judgement and no owner. It rides in the pull request they are about to read,
  with every changed sentence named in the report. So a batch no longer ends by leaving stale prose
  behind at all.
- **`[stale …]` is a statement, not a finding.** It sits under the prose it corrects, so no run is
  misled while it stands, and it no longer changes the check's exit code. `[assumed …]` stays a
  finding: it is a question nobody has answered.
- **`next` does not recommend `blueprint` for open blocks.** It reports the count and goes on down
  the ladder — unless the entry it was about to recommend building is the one carrying the block.
- The graph in `docs/design/the-loop.md` gains the column it was missing: **where** a record is
  closed, not only who may close it. Every defect of this release lived in that column.

## 0.43.1

- **`blueprint` deletes a ledger line whose work it has just done.** The rule was already the
  ledger's own — closed by whoever does the work, in the same commit — but `blueprint` was never
  told it may touch that file, and a line asking for prose to be rewritten has no other closer.
  Projects that recorded prose work in the ledger before `[stale …]` existed are cleared by the next
  `blueprint` run rather than by hand.

## 0.43.0

The whole payload read against one graph of who records, who reminds and who resolves — written
down as [docs/design/the-loop.md](docs/design/the-loop.md), because the kit had four partial maps of
this and no complete one. Seven places where the loop did not close.

- **A third kind of block: `[stale …]`.** Prose an entry carries that the feature just shipped has
  made false. It went into the ledger yesterday, which was wrong twice over: `blueprint` is the only
  one who may rewrite the prose and the only one who never deletes ledger lines, so the line would
  have outlived its own answer; and a block under the entry is read by the next run that opens it,
  which a line in a ledger is not.
- **`blueprint` carries one table for all three block kinds**, each with its own ending. Only
  `[assumed …]` had a written procedure; what a `[found …]` becomes in the library map was nowhere.
- **A parked feature built from a `task` no longer disappears.** Its entry would have stayed
  `planned` and raised it again — but a task has no entry, and `check.py` does not list runs at a
  terminal step. The closing session writes it a ledger line.
- **The scenarios lens no longer instructs a reader it does not have.** It told whoever was reading
  to record an untestable step in the ledger; the only reader is `audit`, which may write nothing
  but its own work list.
- **The actions template stopped claiming nobody else writes the state line.** Five files state that
  rule and this was the one left behind when `next` gained the right to move it.
- **The screens template nested one HTML comment inside another**, so the inner `-->` closed the
  outer block and two lines of its example rendered as text. `validate.sh` now refuses a nested or
  unclosed comment anywhere in the payload, beside the code-fence check added yesterday.
- **Every record now names who may close it** — in the plugin README's table, and as the fourth
  question every new mechanism has to answer in `docs/developing.md`. Half of the 5 August defects
  were records with no writer or no reader; the ones found the day after were records nobody was
  allowed to remove.

## 0.42.0

Found by running 0.41.0 on a live project: a merged feature sat at `state: building` and nothing
anywhere said so. Two of these come straight out of yesterday's own changes.

- **The check says when a line is behind, whether or not it may move it.** Making writing explicit
  in 0.41.0 also made the fact invisible: a preflight that no longer syncs also stopped comparing.
  Looking is free now and happens on every run — `--sync` still decides whether anything is
  rewritten, and `--offline` still asks GitHub nothing at all.
- **`next` may move a state line**, under the fence it already had for an audit's boxes: only that
  line, its own `docs(knowledge):` commit, only on a clean tree. It is the command for coming back
  after a break, and this is a fact catching up with itself rather than a decision. Prose stays
  `blueprint`'s alone — a state line beside stale prose is still worth moving.
- **`ship` names the destination for prose its own feature made false.** The row existed in the
  pull-request rules and did not survive 0.41.0's table: a run that changes what is true has nowhere
  to say the entry now lies, and rewriting it is never the run's own right. It is a line in the
  ledger naming that entry, and `blueprint` executes it.

## 0.41.0

A review of the whole kit for contradictions — one command promising what another does differently,
a rule describing machinery that behaves otherwise. Nine were found; eight are fixed here.

- **The check no longer writes to a project unless it is asked to.** It moved an entry whose pull
  request had merged by default, and `ship`, `fix` and `sprint` all ran it as their preflight — so a
  command that meant only to read could leave the working tree dirty, which those same commands call
  a blocker, and which contradicts the rule that only `blueprint` rewrites knowledge. `--sync` now
  asks for it, and `blueprint --check` is the only caller that does.
- **`next` can see pull requests again.** It was given `--offline` in 0.39.0 to stop it writing, but
  that flag also cuts off `gh` — and rungs 3, 4 and 5 of its ladder are entirely about open pull
  requests and their CI. It ran blind past the most urgent thing it exists to find. With writing now
  behind `--sync`, it needs neither flag.
- **`blueprint` had an unclosed code fence**, so everything below it — how a session ends, what runs
  leave behind, what the check does — read as a listing rather than as instructions. `validate.sh`
  now counts fences in every file of the payload.
- **The run file's `step` had two vocabularies.** The template called its list closed while the
  driver wrote `building` and `closing`, which are not in it. Both are declared now, and the check
  names a step no reader knows.
- **The control window offered `pause` and `stop` as different things**; the driver treats them
  identically. `pause` is gone rather than invented: a stop that delivered nothing would leave a
  batch as branches with no pull request, and `--resume` already covers coming back.
- **`audit` said it writes nothing into the project** and then told itself to write and commit the
  lens's work list. It changes nothing *but its own work list*, which is what it meant.
- **The reviewer's four questions** were introduced as three.
- `docs/developing.md` gains a table of who may write which file in a project — the rule "only
  `blueprint` rewrites knowledge" was true when written and had grown four writers since — and its
  release note now describes the order `release.sh` actually enforces.
- `mvp` stays a stub, and now says what it will be: a layer that composes the entries inside the MVP
  bounds into batches and runs them the way `sprint` does. Nothing about how a feature is built.

## 0.40.0

The 5 August audit left five proposals unbuilt and asked that each be checked against the files
before it was executed. It was, and three of the five turned out to have a cheaper answer: the text
they wanted moved into new reference files was already in files that exist. No new file was written.

- **One route for an unmet mark, not two.** `ship` said in its opening that a contradiction between
  an entry and the code goes into `deviations`, "that field is where the batch's pull request gets
  it from", and said in its Build step that it goes into `deviations` **and** `unmet`. The closing
  session composes the batch's list of unkept promises from `unmet` alone — so a run that followed
  the opening left that list empty while the marks stood in the code. `unmet` is now the only route;
  `deviations` keeps what it is for, a departure from the approved approach.
- **`ship` records through one table.** Eight destinations — what you found, where it goes, who
  reads it — in place of six rules spread across three sections. The table in
  `rules/pull-requests.md` was not copied but reduced to its other half: what raises the record
  again.
- **The form of the `unmet` mark leaves `ship`.** The argument for a form that runs and fails over
  one that skips is in `templates/project.yml`, where `blueprint` settles `tests.unmet`; the answer
  for a project is in its own `project.yml`, which `ship` reads every run. The rule stays: the mark
  is the kit's constant plus the entry key, and it is only ever for code that was there before you.
- **The debt mechanics leave `ship`.** `templates/technical_debt.md` is the ledger's own header and
  already carried the format, the boundary against assumptions and marks, and delete-don't-tick. It
  gains the one rule it was missing — half an item deleted is worse than an item untouched — and
  says plainly that the ticked boxes in this kit belong to the audits' work lists.
- **The agent no longer writes `run.log`.** The driver already records a child's sessions starting,
  stalling, waiting out a limit and finishing, which is what the control window reads it for. The
  design has said since the rewrite that the log is written by the driver and never by the agent.
- **`check.py --run <dir>` judges one run file as it closes.** An open critical or major review
  finding, or an empty `suite`, at `step: done`. It is asked by `ship` and `fix` as they close and
  by the driver before it calls a feature built — a finished run's file is history, so a finding
  raised later reaches nobody. The driver does not park the feature over it: the branch is pushed
  and reviewed either way, so the defect goes to `blockers` and the pull request names it.
- **`validate.sh` checks that every field of the run file has a writer and a reader.** Half the
  defects of the audit were records with one side; this fails on a field fewer than two of the
  plugin's files name. Confirmed to fail on `waiting_since` before it was kept.
- **The `[assumed …]` block had two homes** and only one writer. `blueprint` describes it now
  instead of restating its shape.
- `docs/developing.md` records which of the three levels a piece of text belongs at — chosen by how
  often it is needed, never by how long it is — and its repository map covers the whole payload
  again.

## 0.39.0

An audit of the whole kit — the first since the rewrite reached six working commands — found one
crash, three records with a reader and no writer, and several places where a rule described a
mechanism that had since changed underneath it.

- **The check crashed on the day a feature landed.** Moving an entry to `built` rewrote the file
  while the parsed entries still pointed at the old text, and the next check died with
  `ValueError: substring not found` — taking the preflight of every command with it. Reproduced,
  fixed, and covered by a test; none of the 53 before it touched that branch.
- **`next` was writing to the knowledge it says it never touches.** It ran the check without
  `--offline`, which asks GitHub about entries marked `building` and rewrites their state lines —
  leaving uncommitted changes, which is its own ladder's most urgent finding.
- **The unmet list is no longer cut to ten.** `ship` is told to read the marked test for the entry
  it is about to touch, and a trimmed list could hide exactly that one.
- **`waiting_on` had three readers and no writer** — the field a driver, the window and `next` all
  use to know a run is stopped and on what, and the only route by which a night's question reaches
  a phone. `ship` now puts the fork's text there. `waiting_since`, which had the reverse problem,
  is gone.
- **Nothing produced `agent-kit:scenario`**, so "no scenario has an end-to-end test" was true by
  construction. `ship` writes it when the task is a scenario.
- **`commands.types` did not exist and `commands.run` had no reader**, while `ship` was told to run
  types and to start the app. Both are in the template now, and both are named where they are used.
- **The debt template seeded a phantom item** — its own example was an open box outside a fence, so
  every fresh project began one item in debt.
- **`blueprint` promised a guard that does not exist**, described a `--hash` path that contradicts
  `--record`, and claimed the check verifies a status against its entity, which the program's own
  closing line denies. All three corrected.
- **`run.log` stops duplicating the run file.** Assumptions, answers and review findings have had
  fields of their own since 0.36.0; logging them again bought shell calls and nothing else.
- A screen the entry calls an `entry_point` is no longer an orphan, and `close.md` no longer claims
  to be the only thing that ticks an audit box.

## 0.38.0

**`fix` is written.** It was a stub from the day the rewrite started, which meant every small repair
happened by hand, outside the kit, recorded nowhere.

- **Three ways in, one pipeline**: the owner's description when the cause is unknown, whatever is
  already red when it is not, and `--pr <n>` for a review round — that one commits onto the pull
  request's own branch and opens nothing new.
- **The spine is a failing test written before the change**, asserting the behaviour that should
  have held, at a seam the project already tests at. Then the fix is undone once to watch it fail
  again: the only cheap proof that the test guards the fix rather than passing beside it.
- **It says why nobody noticed** — which test should have caught this and does not exist, or exists
  and asserts the wrong thing. That is what keeps the defect from returning by another route.
- **It stops early rather than late.** A cause that is *this was never built* is `ship`'s; a cause
  that is somebody's decision belongs to the entry; a repair that touches a layer rather than a
  place goes to the ledger with the cause named. A run that grows a feature under the name of a fix
  delivers something nobody described.
- **It changes the least that makes the test pass.** The tidy-up next to it, the rename, the second
  defect found on the way are lines in `docs/technical_debt.md` — a fix that also refactors cannot
  be reviewed as one, or reverted without taking the refactor along.
- An hour with no cause ends in a report, not a hopeful change: what was ruled out, what is
  suspected, where to look next.

## 0.37.1

`next` gained the right to tick a box it had verified and, on its third run, exercised it by
switching to the default branch, committing and pushing — all reasonable, none of it written down.
The fence now is: only `docs/audits/*` and only boxes, its own `docs(audits):` commit, branches
switched only when the tree is clean and the current branch already merged, and a rejected push
accepted rather than worked around.

## 0.37.0

A second run of `next` on a real project did better than the rule it was following, and worse in one
way the rule had not thought to forbid.

- **It may settle a stale list, and tick what it settles.** Warning that an audit's boxes might be
  closed is homework; *eight of these eleven are finished, three are left* is an answer. The licence
  to check is now explicit — the entry's state, the diff of a pull request that landed since — and
  so is the one write it may make: tick the box, in the project's language, only for what it
  verified. Otherwise every later run redoes the same comparison and the list goes on lying.
- **Everything else stays shut**, and now says so: no walking the code, no reading entries for their
  own sake. A defect in the product belongs to a lens; a command meant to cost seconds turns into an
  afternoon the moment it goes looking.
- **A citation comes from an open file.** The run named a contradiction correctly and put it in the
  wrong file — the word it searched for appears in five places, and the sentence that mattered was
  in one. Cite from what you opened, or say the finding without the citation.

## 0.36.1

Field drift is printed beside the debt rather than filed as a defect. A finished run's file is
history — nobody edits it to add a key the template has since gained — so as a finding it would
have sat there forever, unclosable, holding the exit code at 1 on a project whose knowledge is
otherwise clean.

## 0.36.0

Runs were inventing fields. `review`, `fork_resolved`, `notes`, `commits` — none of them in the
template, each written in whatever shape that run felt like, and read by nobody, because every
reader knows only the template. The kit's most expensive output after the code itself — what the
reviewer found — was living in a chat window.

- **`review` in the run file**, with a severity per finding, whether it was closed and how, and
  whether the security pass ran. Written as the findings come back, before they are fixed; a
  critical or major one left open is not `step: done`. The batch's pull request composes its Review
  section from these rather than from a child's summary of them.
- **`answers`** — what the owner was asked and what they said, verbatim. A resumed run reads it
  instead of asking twice, and the pull request quotes it instead of recalling it.
- **The app check leaves a trace.** `suite` now carries what was opened in the running application
  and what was seen, or that there was nothing to open. Otherwise "checked by hand" and "wrote that
  it was checked" are the same sentence.
- **The reviewer reads the run file.** It could judge whether the code was good and whether the
  entry was covered, but not whether this was the feature that was designed — nothing in the kit
  compared the diff to the approach the run committed to.
- **Invented keys are said, not filed as a defect, and `notes` is where prose goes.** The field list is closed because
  readers are fixed; free context now has a home, so nothing has to mint a key to keep it. `check`
  names run files carrying unknown fields — on the project this was built against it found
  `commits` in seven of them.

## 0.35.0

Looking for other places with the same shape as the hash problem — a value one party records and
another trusts — turned up two, both silent by construction.

- **A dependency manifest nobody recorded is now a finding.** `checks.deps` was only ever walked
  over what it already contained, so a project that grew a second ecosystem — a `package.json`
  beside a `composer.json`, a `requirements.txt`, a `go.mod` — had those dependencies under no
  watch at all, and the check reported clean. It now looks for the manifest names it knows among
  the tracked files and names the ones the manifest does not carry.
- **A scenario mark pointing at nothing says so.** `agent-kit:scenario <heading>` matched by
  heading, so renaming a scenario silently unhooked its test: the scenario went back to "no
  end-to-end test" and the mark itself was never mentioned again. Same fix as for entry keys —
  the mark is checked against what exists, and an orphan is reported.

## 0.34.0

Running `next` on a real project surfaced two things it could not see and one it saw wrongly.

- **Hashes are written by the program now.** `check.py --record` rewrites every `source:` and every
  dependency hash in place, so no run transcribes one. Until 4 August the rule said the hash "is
  that section as you read it" — an algorithm left to the reader, which means every value written
  before then was invented. They are recognisable by length, and the check now says so in one line
  — *predate this program, re-record, no document changed* — instead of eleven false "changed"
  findings that crowded out the real ones.
- **Scenarios count their end-to-end tests.** A test claims one by carrying
  `agent-kit:scenario <the scenario's heading>`; `--state` reports how many scenarios have one and
  names those that do not. On the project this was built against: eleven described, zero covered —
  a blind spot `next` had reported as "none".
- **A batch ticks the audit boxes it closed.** `- [x] closed by PR #<n>` in `docs/audits/<lens>.md`,
  in the same commit that writes the ledger. Nothing else ever ticks them: the lens rewrites that
  file only on its next run, so until then every command reads finished work as still waiting.

## 0.33.0

Every command names a next step as it finishes, and that only helps while its session is open. A
week later there is nothing: a new session, no context, and no memory of where the last one stopped.

- **`/agent-kit:next`** answers exactly that, and nothing else. It reads the state, ranks it, and
  names **one** command with the reason in a clause, plus two or three alternatives so it is visible
  what was weighed. It starts nothing and changes nothing.
- **The ladder is the cost of leaving something alone**, not what is most interesting: work that
  exists on one machine only, then a run abandoned at a non-terminal step, then a green pull request
  nobody merged, then a red pipeline, then conflicts and unreviewed work, then anyone waiting on an
  answer, then knowledge too thin to build from, then a lens that never ran, then debt, then unbuilt
  entries. Three overrides on top: no knowledge at all means `blueprint`, an empty repository means
  `mvp`, and while the MVP bounds are unmet, unbuilt entries come before debt.
- **`check.py --state`** is the mechanical half, and three of its sources had no reader in the kit
  until now: runs left mid-flight, branches with their drift from `origin/main` and whether they
  were ever pushed, and the date each audit lens last ran. Pull requests come with their CI verdict
  and conflict state.
- **It degrades in pieces**: audits and runs need no git, branches do, pull requests need `gh`. A
  repository with no commits says so rather than reporting nothing.
- The ladder carries its own warning about stale lists — a run thirty commits behind is "start
  again", not "carry on", and an audit box may already be closed by a batch that never ticked it.

## 0.32.0

A pull request should end without a to-do list. Two rules were letting one form anyway: nothing said
that a leftover must name the file it now lives in, and nothing forbade handing it over in words.

- **Nothing is left on the owner.** *Your call*, *this is on you*, *needs your decision* are banned
  from pull requests and from closing lines alike. Every leftover instead names **where it is now**
  and **what will raise it again** — an `[assumed …]` block under its entry, a test marked
  `agent-kit:unmet`, a line in `docs/technical_debt.md` — each of which the check prints before the
  next command and `sprint` with no theme offers as work. A table in the rule maps every kind of
  leftover to its place; a leftover with no place in it is not recorded at all, and saying it in
  prose does not make it so.
- **Manual actions stays the one exception**, because secrets, migrations and third-party accounts
  genuinely need hands — and even there the line says what to do, not whose fault it is undone.
- **What was hard** — a new section, three to five lines, never collapsed: the approach that looked
  right and was not, the library that did not behave as documented, the test that passed for the
  wrong reason. It is the only part of a run that exists nowhere else, since the code shows the
  answer and never the two answers before it.

## 0.31.0

The ledger could be written to and never emptied: 0.30.0 said "closed by deleting the line" in the
template and nowhere a command would read it. A list that only grows is read once.

- **A finished item is deleted, in the commit that does the work** — so the debt going down shows up
  in the same diff as the code that paid it. Never a ticked box: a ticked box is a line nobody
  deletes afterwards, and git already holds every line that ever existed.
- **`closed_debt` in the run file** names what a run closed, the way `deferred` names what it added.
  The closing session deletes those lines, writes the new ones, commits both together, and reports
  the movement — nine items, three closed, two added — instead of leaving the owner to diff a file.
- **A batch taken off the ledger carries the line into the child verbatim**, so a run knows which of
  nine it was sent to close; a paraphrase leaves it guessing.
- **Half-finished is not finished**: the line stays and gains what was learned. And a child that
  claims an item whose line is still there gets carried over untouched — the ledger is not shortened
  on a run's word.

## 0.30.0

- **The ledger is `docs/technical_debt.md`.** `debt.md` sat one letter from `deps.md` in the same
  documentation folder and read like it — a name nobody should have to disambiguate. Renamed with
  the template; 0.29.0's `docs/debt.md` was a day old and is not migrated for anyone.
- **Its line carries the entry key**: `<what> — <why> · <entry key or —> · <run> · PR #<n>`. That is
  what lets a batch be composed around one area of the product rather than around whatever was
  written last.
- **`sprint` with no theme asks which pile first.** Everything it finds sorts into *owed on what
  exists* — the ledger, the audits' work lists, open notes, unkept promises — and *not built yet* —
  entries still `planned`. One question with the two counts, then a second naming the candidates of
  the chosen pile. Skipped when a pile is empty. No separate command and no flag for debt: it is not
  a mode, it is the half of the list that has been waiting longer.
- **The scenarios lens now demands an end-to-end test per scenario**, reported as its own verdict
  beside the walk. Tracing proves a path exists in the code today and says nothing about tomorrow,
  and this lens only runs when somebody remembers to run it. A step that cannot honestly live in a
  test — a paid third-party call, something only a person can judge — goes to the ledger by name.

## 0.29.0

A batch closed with two leftovers: an invariant the security fix rested on and nothing checked, and
two entries whose prose now described the old behaviour. Both were written down — one as an
`[assumed …]` block, which every command sees, and one in a free-form field of a run file, which
nothing reads. After the merge the second would have existed only in a pull request nobody reopens.

- **`docs/debt.md`** — the ledger for work a run decided not to do. It is the one thing the kit had
  nowhere to put: not a decision about the product (`[assumed …]`), not a promise the product does
  not keep (a marked test), not an unbuilt feature (`state: planned`), not an audit's finding (its
  own work list). What is left is the leftover a run creates and does not finish.
- **Written by the runs, not by hand.** `ship` writes the line as it defers the work; inside a batch
  it also lands in the run file's `deferred`, and the closing session carries every child's into the
  ledger and commits it on the batch's branch before opening the pull request.
- **Read before every command.** `check.py` lists the open items and changes no exit code — a
  project's own memory is not a defect. `sprint` with no theme offers them as a fifth source of
  candidates, beside planned entries, audits, open notes and unmet promises.
- **Closed by deleting the line**, in the commit that does the work: a ticked box is a line nobody
  ever deletes.

## 0.28.0

0.27.0 shipped the mark with a hand-written file walk behind it, and a review of that release found
what the walk cost. Every finding below was reproduced before it was fixed, and the tests now run
against a real git repository — the six written in 0.27.0 all took the fallback path, which is why
none of this was caught there.

- **The check no longer crashes on the form its own template asks for.** Several suites in one
  project means a nested map under `tests.unmet`, and the reader called a string method on it —
  taking the preflight of `ship`, `sprint` and `blueprint` down with it.
- **Files whose names are not ASCII are read again.** `git ls-files` quotes them, so a marked test
  in a file named in the project's own language was silently invisible.
- **The search is `git grep`** — binaries skipped, symlinks not counted twice, `docs/` excluded
  because reports and entries quote the mark in prose and a quotation is not a promise. On a
  50,000-file repository this is 0.2s against 2.3s and 142MB.
- **Entry keys without a dot** — entities and actors — are keys too, and **a key no entry defines
  is now said out loud**, so a renamed entry cannot leave a mark pointing at nothing.
- **A missing `tests.unmet` no longer fails the check.** It printed a finding in a group no skill's
  table mentions, and a run that met it would most likely have stopped.
- **The list is cut to ten and counted** — it is read before every feature and acted on by none.
- **`--status` names the planned entries** instead of counting them, which is what `sprint` with no
  theme needs to offer them as a batch.
- **The mark now has somewhere to live**: `unmet` in the run file, read by the closing session into
  the batch's pull request under Proven, uncollapsed. Before this it reached the owner only if a
  child happened to write it into `deviations`.
- **`reviewer` knows the mark** — not coverage, legitimate only when the run file records the
  contradiction, and a serious finding when it sits on what the diff itself was to build.
- **The example is `xfail(strict=True)`**, not Pest `todo`: a skipped test proves nothing today and
  stays quiet the day the product keeps the promise.
- **`ship` may not rewrite an entry** — `blueprint` owns the prose, so the mark stays until it does.
- `sprint` with no theme is told that audit work lists go stale, because nothing ticks their boxes
  when a batch closes them, and how to spot that from an entry's state.

## 0.27.0

The first live sprint — the tests lens over a real project, seven batches, 43 tests, all green —
froze three product defects as expected behavior. Not from laziness: a test for a line the code
contradicts could only be left red, which stops the branch, the batch behind it and CI, or written
over what the code does, which makes the suite guard the bug. This release adds the third road.

- **A promise the product does not keep gets a test and a mark.** The test says what the entry
  promises, and carries `// agent-kit:unmet <entry key>` beside whatever this project uses to keep
  it off the red. The dispute is recorded instead of settled: the proof is in the repository, the
  suite stays green, and whoever settles it later finds the test already written.
- **The mark is a constant of the kit, not a framework's syntax** — one project can hold three
  suites in two languages. `check.py` looks for that comment in every tracked file and reports the
  entry key rather than a fragment of code; `project.yml` → `tests.unmet` records only what keeps
  such a test green here, so runs do not each pick their own form.
- **The check prints them on every command and changes no exit code.** These tests are green by
  design, so nothing else in a run would mention them again; this is the one place that does, and a
  reminder is not a failure. It asks for `tests.unmet` only once a mark exists, so nothing nags a
  project that has none.
- **The mark is never for code the same run writes** — otherwise a feature could declare itself
  done by marking what it could not make pass.
- **`ship`** treats *the entry promises one thing, the code already does another* as an expensive
  fork of its own: unattended it marks and records both readings in `deviations`; with the owner
  present it marks and asks which side is wrong.
- **`sprint` with no theme** offers what the project already owes, from four places: entries still
  `planned`, the audits' work lists, open `[assumed …]` notes, and marked promises. There is no
  separate command for debt — debt is the part of that list nobody has chosen yet.
- **The tests lens** scores a marked line `unmet`: neither coverage nor a gap, since the work it
  asks for is a product change, and those lines are reported as their own list.
- **The window may not ask** — *your call now*, *either the entry is wrong or the code is* are
  questions with the mark filed off, landing on a phone as work owed and answered into a session
  that builds nothing. The ban is now on the shape, with a report to copy instead.
- **One question means one question in the call**, not one topic per screen.

Existing projects need nothing: the mark works without `tests.unmet`, and the key is asked for the
first time a marked test exists.

## 0.26.0

`sprint` — a batch of features built one after another while nobody watches. Its design was written
first, then reviewed against itself and cut by about a third; what survived is in
[docs/design/sprint.md](docs/design/sprint.md), and the *Rejected* section there is the more useful
half.

- **A driver, not an orchestrating agent.** `scripts/orchestrate.py` is a loop with no model behind
  it: it reads run files, watches a transcript's modification time, knows one HTTP status, and asks
  git whether a branch exists. 0.17.0's agent-held queue died of its own context and hid the run
  behind a third headless level; a loop does neither.
- **One visible session per feature.** It can be watched from the app, typed into when it goes
  wrong, and can ask its own question — none of which a headless child could do.
- **One chain, one pull request.** Every feature branches off the last successful one, so the last
  branch already holds the batch: integration stops being a step. No per-feature pull requests, no
  drafts, no integration branch — each branch is pushed, and a single feature's pull request is one
  printed command away on the day it is wanted.
- **The account limit costs the wait and nothing else.** The 429 record carries its own reset time,
  and the process survives it with its context intact, so one typed line resumes the session. A
  reset more than a few hours out is a weekly limit: the run stops instead of sleeping through a day.
- **No clock on a question.** Someone present, a child asks and waits; nobody present, it records
  the assumption and carries on. A failed feature takes its descendants with it and the rest of the
  batch runs.
- **The window is the owner's own session**, not one the kit raises: the brief writes its tmux name
  into the run file and stays to answer *how is it going*, to speak the driver's news, and to relay
  *pause*, *skip* and *stop* between features. A batch without one simply runs unnarrated.
- `ship` learns `--run <dir>` to continue a run file somebody else wrote, `parent` to inherit the
  decisions its base branch cannot explain, and `deliver: "branch"` to push reviewed code and stop.
- **The kit has tests.** `tests/test_orchestrate.py`, run by the validator; they found two defects
  before any live run — an unbounded wait on a closing session that never returns, and a dead
  session waited out as though it were merely quiet.

Nothing here has run against a real project yet, and neither has `ship`. The first batch's first
feature is `ship`'s first live run and belongs in daylight.

## 0.25.1

With six lenses written, `audit` had grown to 466 lines of which 301 described lenses — and a
single-lens run carried all six, paying for five it would never use on every step it took
afterwards. That is the kit's own rule about reading only what you need, broken by the kit.

- **Each lens is its own file** under `skills/audit/references/`, read when that lens runs. The
  command keeps the shared mechanics and drops to 180 lines.

## 0.25.0

The conventions lens, and with it all six. The other five check what the product does; this one
checks how it is built, against the project's own words in `stack.md` — the stances per area, the
library map, the testing rules, the list of what this project does not do.

- **The rules are the list.** Each is walked and gets a row, including the ones nothing violates and
  the ones that could not be checked. Three violations reported out of eighteen rules says nothing
  about the other fifteen.
- **Hand-rolled where the library map names a package** is the most valuable of the four kinds, and
  cites both the code and the map line it ignores.
- **It owns the half of "is this test any good" the tests lens cannot answer** — brittle, slow,
  duplicated, asserting the implementation, sitting below the seam the project's rules ask for.
- **A rule the project never wrote is not a finding.** An opinion about layering or naming smuggled
  in as a violation is how a lens becomes an argument; it goes in "also noticed" and is a candidate
  for `blueprint` to record.
- **The lens is worth what `stack.md` is worth**, and says which of the two it was working with
  before the findings — derived and confirmed stances, or three vague lines.

Six lenses, six written.

## 0.24.1

Nine of the ten corrections earned by the earlier lenses already applied to performance — it was
written after they were paid for. The tenth did not: the omission lesson, applied to the second
citation.

- **Name every consumer, not the first one.** An action's data can reach a list, a detail page, a
  notification and an export; reading one template and citing it leaves a row that looks checked
  while two consumers were never opened. Where they cannot be enumerated, `unjudged` is worth more
  than a clean row nobody can trust.

## 0.24.0

The performance lens — not "will it hold ten thousand requests", which needs numbers no project has
written down, but the code that is slow for a reason anyone would recognise, found early while it is
cheap to change.

- **The catalogue is derived, not shipped.** What is an anti-pattern in one stack is the idiom of
  another, so it comes from `stack.md` and the framework's own documented pitfalls — and it is
  written into the report before it is used, because a finding-free report against three patterns is
  a different thing from one against nine.
- **Two citations per action: where the data is fetched and where it is consumed.** An action can
  build a perfectly bounded query while the extra round trips happen in the template it feeds, in a
  serializer, in an accessor touched during rendering. Eager loading that covers what the action uses
  and misses what the view uses is the normal shape of this defect.
- **Every action in scope gets a row** — clean, a finding, or unjudged with the reason. A report
  listing only problems cannot be told from one that stopped looking.
- **Profiler output is an input, not a verdict**, and the kit adds no tooling and runs no benchmark.
  Measuring is somebody's work; this lens is reading.

Six lenses, five written. Conventions remains.

## 0.23.1

Eleven corrections were earned by the first three lenses over eight live runs. Eight of them already
covered the security lens, through the shared rules or by being written into it. Three did not, and
are now closed before its first run rather than after three.

- **Two citations per rule, not one: where the check is written and where it is invoked** on the path
  the actor takes. A policy method can be correct and never called; a middleware can be defined and
  missing from the route group. That is the scenarios lesson — exists is not reachable — applied to
  permissions.
- **Every *must never* line appears in the report**, with a citation or `none`. Omitting the ones
  that could not be placed is how a dense report stays silent about its gap.
- **A name is not a check.** `PostPolicy::report` existing, or `auth` appearing in a route file, is
  the code's claim about itself — the same substitution as crediting a test for its name.

## 0.23.0

The security lens. Two references, and only one of them is generic.

- **Choosing what to look at is the first finding.** Every entry is marked in or out with its reason
  — untrusted input, permissions, money, files or processes, an outbound call, a migration — and the
  whole table is written, excluded ones included. A lens that quietly narrows its own scope produces
  a clean report about five actions and says nothing about the thirty it never opened, and nothing
  in the output distinguishes the two.
- **Half of it is rules no scanner can know.** The *must never* lines of the entries and their
  actors are this product's own authorization rules: for each, the code enforcing it is cited, and
  nothing enforcing it is a finding — usually a more serious one than a generic pass returns, because
  it is specific and nobody else is looking for it.
- **The other half delegates.** `/security-review` runs over the files the risky actions live in,
  rather than reasoning about injection from scratch. Its silence is not a verdict: it knows its own
  catalogue and nothing about this product, and the report keeps the two halves separate.
- Credentials in tracked files, a committed `.env`, keys in fixtures — the one part of production
  readiness a repository can actually show, which is why the readiness lens left it here.
- No exploitation. The citation is the evidence, and a lens that changes state to prove a point has
  stopped being a lens.

Six lenses, four written.

## 0.22.4

The scenarios lens ran on a real project — 11 scenarios, 38 steps, two citations each, 5.4M — and
found a break no test at the level of one action could see: a story held for human review shows the
moderator the verdict fields but never the engine's raw response, so the next step of the scenario
is a decision made blind. It also declined to inflate a known defect into a break, because the
scenario it appears in walks past it, and reported it separately instead.

- **`debt` is renamed `conventions`** — two letters from `deps`, and the owner tripped over it. Its
  reference is what the project wrote down about itself, and the name now says so.
- **`readiness` is removed.** "Is this ready" splits into whether the MVP bounds are built with their
  scenarios passing — already answered by the `built` markers and the scenarios lens — and whether
  the thing survives production. The second is real, and half of it cannot be seen from a repository
  at all: backups, monitoring actually receiving events, a restore ever tested. A lens that checks
  half its checklist and guesses the rest is worse than none, because its output reads as a checklist.
  The observable remainder, secrets in the repository, belongs to the security lens.
- **A lens is legitimate on three counts, not two:** a finite list, a reference, and observability.
  The third was added here and cost a lens.

Six lenses, three written.

## 0.22.3

Two defects the deps run surfaced, both about the command's own bookkeeping rather than its findings.

- **The command now names the lenses that exist** — `tests`, `deps`, `scenarios` — because it
  mentioned four unwritten ones while explaining where a question belongs, and then recommended one
  as the next step. Typing it would have been refused by the unrecognised-argument rule: recommend,
  then decline.
- **The baseline check runs once per invocation, not once per lens**, into `docs/audits/baseline.md`.
  It had been repeated in every lens file — the same work twice, and two places for one fact to
  disagree with itself.

## 0.22.2

The deps lens ran on a real project for 1.0M and three minutes, with every finding carrying its call
sites, its reachability judged against this codebase, and its upgrade path — including one the
advisory could not state, that an unreachable host-check bypass still leaks an API key because the
calls carrying it follow redirects. Two claims of "used nowhere" checked out exactly.

- **Every lens groups its findings into units of work**, not only the tests lens. What a batch is
  differs — two security patches are one run, dropping three unused packages another, a framework
  major a project of its own — and the shape does not. A `sprint` reads that list instead of
  composing a batch itself, so a lens reporting findings without units of work has not finished.

## 0.22.1

The four cheap paths the tests lens revealed over four runs, extrapolated to the scenarios lens
before its first — the first time the corrections arrive ahead of the evidence rather than after it.

- **Two citations per step**: what implements it, and what gets the actor to it from the previous
  step. An action can exist, be correct, be tested and be unreachable, which is the class of defect
  this lens exists for and the one a single citation misses.
- **Citations come from the code, never from the entries.** An entry claiming a step is reachable is
  the claim under test; quoting it back is crediting a test for its name.
- **Walk past a break.** Assume it fixed and keep going, or the remaining breaks are discovered one
  per fix over the following weeks.
- **Where end-to-end tests exist, name which covers which scenario and check it walks the same
  steps.** Green is not evidence that the covered path is this one.
- **Three verdicts, no fourth invented**, and every scenario and step in the map — the file's own
  numbering makes a short trace countable.

## 0.22.0

The scenarios lens — the only one that answers whether the application works end to end, which is
the question `built` markers cannot answer. Tests prove the parts; scenarios prove the joins, and a
path where every action works and the step between two of them does not is invisible to any test
written at the level of one action.

- **Two passes, the first needing no code.** Chain the steps against the entries — step N sets a
  status, step N+1 lists its preconditions, and a mismatch is a finding without opening anything —
  then trace the path through the code.
- **It traces when there is nothing to run.** End-to-end tests are run first where they exist; where
  they do not, the scenario is walked through the code rather than reported as unrunnable, which on
  most projects would mean an empty audit and a defect left in place.
- **Each step cites the code that carries it**, and the break is named at the step where it happens.
  A scenario is `walks`, `breaks at step N`, or `unfollowable` — never a verdict with no trace behind
  it, which is this lens's cheap path.
- **It does not write the end-to-end tests.** Tracing says what is broken now; the tests say whether
  it breaks again, and building them is an owner's decision and a `ship` run. The work list opens
  with the harness when there is none.

## 0.21.3

The fourth run of the tests lens landed: 392 citations across 841 lines, exact to the line where
spot-checked, the entry that once produced a false covering demoted to the gaps by a single `none`,
and cost flat against the previous run. Four runs of measurement are recorded in
`docs/design/audit.md`.

- **`n/a` is allowed only where the entry's own line states that nothing happens.** The fourth run
  invented the marker and used it honestly, but a marker needing neither a citation nor an admission
  is the next cheap path, and it reads as a verdict.
- **The deps lens gets the same discipline.** Its cheap path is relaying what `composer audit`
  printed, so each finding now carries where the package is used in this codebase, whether the
  vulnerable path is reachable here, and what the upgrade costs or what blocks it — three fields that
  cannot be filled without looking. Ordered by what the owner acts on first; patch drift ignored.

Bringing a second lens to full rigour cost a paragraph and no special handling, which is what
shipping two lenses before the other five was meant to find out.

## 0.21.2

The citation format held on its first live run — cost 2.0M to 5.1M, file reads 3 to 34, coverings 19
to 12, and 155 real citations with line numbers. It also opened the next cheap path, one level down:
cite what can be cited and quietly omit the rest. The disputed line — a report count hidden from an
author — simply was not in the map, and the entry stayed covered.

- **The map carries every line of the entry**, and a line with nothing to cite is written `none`.
  Each distinct claim inside a line is its own row.
- **A single `none` moves the entry out of covered.** Covered means covered whole; anything else is a
  partial dressed as a verdict.
- **Completeness is arithmetic, not trust:** the entry's file declares its `fields:`, so a map with
  fewer rows than the entry has lines is a defect in the report, countable without reading it.

The rule as it now stands, which took three runs to state: where a cheaper path exists and produces
plausible output, demand an artefact that path cannot produce — and demand that the artefact be
complete, or the omission becomes the new cheap path.

## 0.21.1

The second live run of the tests lens produced a false covering, and finding it took one grep: the
entry's line was about hiding the report *count* from an author, the assertion was about hiding the
report *button*, and the entry was listed as covered without remarks.

Two earlier corrections had been written as instructions — read the file, do not stop at a grep hit
— and both were followed in letter. The run indexed every test *name* in the suite and judged from
those, which costs almost nothing and reads plausibly, because a test's name is its claim about
itself rather than its content.

- **A line is covered only when the file names the test and the line number proving it.** No
  citation, no coverage. A citation cannot be written without opening the file, so the cheap path
  stops being available instead of being discouraged.
- **The covered section is now the longest part of the file**, and that is correct: it is the only
  half a reader can check. Previously it was a list of bare entry names with no way to see which
  line each was credited by.

The general rule, recorded in `docs/design/audit.md`: where a cheaper path exists and produces
plausible output, demand an artefact that path cannot produce.

## 0.21.0

The first live `audit` run cost 1.7M and three minutes — and was too cheap. Sixteen gaps were facts,
because the absence of any match is a fact. The seventeen "covered" were guesses: they rested on grep
hits, and two test files out of thirty-five entries were ever opened. That was a defect in the text,
which said both "judge over the files the mechanical pass pointed at" and "stop at the first match",
and the cheaper reading won.

**Audit is the rarest command in the kit and its output has the longest life** — it decides whether
fifty `built` markers can be believed. Cheapness is not its virtue. The list bounds the breadth;
depth per item is not economised.

- **A verdict rests on something read, never on a search hit.** A match can be fixture data, a
  variable name, or an assertion about the neighbouring behavior. A false "covered" is the worst
  thing an audit can produce, because nobody looks for it again.
- **The tests lens asks four questions per line**, stopping at the first no: is there a test, is it
  about this line, is the assertion strong enough to observe what the line claims, does it cover the
  conditions the line names. Partial coverage is worth more than absence — it is what looks covered.
- **It does not judge how a test is built** — brittle, slow, duplicated, wrong seam. That has a
  different reference, `stack.md`'s testing rules, and belongs to the debt lens, which moves up the
  queue as a result. Nor does it invent conditions the entry never named: that is a hole in the
  description and `blueprint` closes it.
- **Findings are interpreted for this project, not relayed from a tool.** Whether an advisory matters
  depends on whether the vulnerable path is reachable here.
- **The scenarios lens walks the code when there is nothing to run**, rather than reporting "no
  harness" and stopping — the trace finds what is broken today, and the work list still orders the
  end-to-end tests, opening with the harness as the owner's decision.
- **The security lens will check the "must never" lines of the entries**, not only generic
  vulnerability classes: no scanner knows this product's own authorization rules.

Cost of the tests lens moves from ~1.7M to ~3–5M, which is what separates a report you act on from
one you re-check.

## 0.20.1

What `audit` guarantees, made explicit — and the three ways it could have ballooned, forbidden.

- **A row per entry**, including covered and unjudged ones, so completeness is something the owner
  counts rather than something the run claims.
- **Uncertainty resolves to a gap, never to "covered".** A spurious finding costs ten seconds of
  reading; a gap recorded as covered hides a bug nobody looks for again.
- **Area by area, writing as each finishes**, so the last entry of a long run is judged on as small a
  working set as the first.
- **Each file states its blind spot**: complete against the description, and the baseline check finds
  surfaces rather than logic that has none.
- **One subagent per lens in a full run, inline for a single lens, never per area** — a subagent's
  floor is 0.3–0.7M, so eight areas would spend more on orientation than the lens costs. Over forty
  entries the area split earns its keep.
- **No verification pass.** A second agent re-checking the first doubles the price against a
  ten-second mistake, which is the stacking that once produced thirty findings and then twenty more.

## 0.20.0

`/agent-kit:audit` — the third role the kit was missing. It could describe a project and build from
the description; nothing looked at code that already exists and said what was missing. The hole
showed twice before it was named: `blueprint` answered a doubt about readiness by building a
screenshot harness and spending 19.5M tokens, and there was nowhere to put "cover this inherited
codebase with tests".

Audit reads code, compares it to `docs/knowledge/`, and writes a work list that `ship` and `sprint`
execute. **It changes nothing** — the moment an audit starts fixing what it finds it loses its
stopping condition.

- **A lens is a comparison plus a reference, and it is legitimate only with a finite list to walk** —
  the entries, the dependency manifest, the scenarios. That list is the stopping condition, and its
  absence is what turned a bounded question into an afternoon of screenshots.
- **Two lenses to start: tests and deps.** Five more are designed with a verdict each in
  `docs/design/audit.md`; the point of shipping two is to find out whether adding the third costs a
  page or a redesign.
- **A baseline check on every run:** a surface the code has and no entry describes, and an entry
  naming a surface that is gone.
- **Naming a lens does not require remembering one.** No argument runs every lens cheapest first,
  committing each file as it finishes; free text is mapped to a lens and the mapping is said out
  loud before any work starts; an unrecognised argument stops the run rather than guessing, because
  guessing costs a full audit.
- **One file per lens**, `docs/audits/<lens>.md`, rewritten each run — git holds the history.
  Findings are grouped into batches of one `ship` run, and an item marked declined is never raised
  again.

## 0.19.5

- **Tests are written before the code by default**, not only for the lines that look risky — leaving
  the agent to judge what counts as risky meant almost nothing did. The one exception is a line whose
  shape is not decided until the code exists, mostly presentation: asserting on markup you have not
  chosen yet is writing the test twice. Those are written after and run once against the unfixed
  code, so the proof that a test can fail holds either way.
- The README opens on what the kit is rather than on who it is for.

## 0.19.4

The README is a reference now, not a story: what each command is for, its forms and arguments, the
loop, and where the kit writes. No rationale — that lives in `docs/design/`.

- **Two languages, two files.** `README.md` in English, `README.ru.md` in Russian, each linking to
  the other. The validator fails when they document different commands, since a stale translation is
  worse than none.
- `/agent-kit:audit` is listed as designed-but-unwritten, so the shape of the kit is visible from
  the front page.

## 0.19.3

Three gaps in how the kit meets its user, found by walking the whole lifecycle rather than one
command: a developer had to hold the order of commands in their head, had no way to ask where the
project stood, and was stopped at the door of a project that has no knowledge yet.

- **`rules/closing.md`** — every command ends by naming what is thin rather than summarising what it
  did, then one line with the next command already filled in and its reason. A summary sounds
  equally confident whether the work was thorough or shallow, which is the one thing the owner is
  trying to judge.
- **`blueprint --check` is the status view.** Run as another command's preflight it stays silent
  when clean; run by hand it always prints where the project stands — what is built, what inside the
  MVP bounds is not, open questions, assumptions waiting. No command of its own for that.
- **`ship` no longer stops on a project with no knowledge at all.** It works from the task as
  written, in the entry-less mode it already had, and says once what that costs: tests can only aim
  at what the task says done means. An unsettled entry in a project that *does* have knowledge still
  stops it — the owner is right there and closes it in a minute.

The rule behind the last one: every command works with knowledge missing except `mvp`, which refuses
because it has no stopping condition without the MVP bounds and the scenarios. The kit should be
learnable from one command, not from an hour of interview.

## 0.19.2

The second run of `blueprint` on the same project cost **2.0M tokens over 30 steps** against the
first run's 24M: no re-interview, no application started, four questions, all of them about real
holes — including that the only `planned` integration is mail, so email confirmation does not work in
production. A functional problem found from the knowledge, with nothing run.

That is what `state` is for, and this release says out loud what it can and cannot carry.

- **`built` means the code exists — not that it works.** Written into the actions template, because
  three commands and the owner read that marker.
- **The close-out says what fifty `built` markers rest on**: the scenarios are the check that a
  feature works, they run against a live application, and on an adopted project nobody has ever run
  them.
- **The declared test command is run once before the close.** Narrowly: blueprint recorded that
  command and every later command depends on it, so a wrong one is found here instead of in the
  middle of a build. The result is reported, never fixed.

## 0.19.1

The first live run of `blueprint`, on a real Laravel project: eight slots, 35 actions, 13 entities,
12 screens, 11 scenarios — **5.6M tokens and about an hour**. Then a further **19.5M** went into a
visual audit of the running application that this command was never meant to do. It was not the
agent inventing work: the owner voiced a doubt about whether the product was ready, and blueprint had
neither a way to answer it nor a boundary saying it should not go and find out.

- **`blueprint <what you want to add or reconsider>`** — the way into a blueprint that is already
  settled: a feature the owner has thought through, a part they want reworked, a doubt about
  coverage. Without it the thought has nowhere to go and turns into work nobody asked for.
- **A boundary section.** It writes knowledge: it does not build, start or instrument the
  application, write scripts, install dependencies, produce audit reports, or decide what gets
  worked on first. Gaps it reports are gaps in the knowledge — a screen nothing leads to, an actor
  with no actions — not defects in the product.
- **Screens are derived from the code, never from a running app.** When the code will not say, the
  slot is `open_question` and the run moves on: an honest gap costs a line.
- **A defined close-out** instead of a summary of the product. Where each slot came from, where it is
  thin, what is still unbuilt inside the MVP bounds, and what was left alone — because a retelling
  sounds equally confident whether the understanding under it is deep or shallow.
- **`--check` reads a field to the next field or heading.** Checking only the label's own line
  reported all eleven of that project's scenarios as empty, since their steps are a list below.
- **`ship` pulls an entry's own section rather than opening the file.** Measured on that project:
  1.6 KB against 44 KB, carried on every remaining step of the run.

## 0.19.0

`ship` is written: one feature from a blueprint entry to a pull request that can be merged without
reading the diff. Four steps — Design, Build, Verify, Deliver — where 0.17.0 had eleven, and no
generated spec or plan document: the entry is the spec and the task list lives in the run file.

- **Design is a precondition, not a flag.** Whoever writes the approach into the run file designed
  the feature, so a run launched by something else skips the step. `gate: owner | none` in that file
  says whether anyone is present, which replaces `--brief` and the two modes that had to be kept in
  agreement with each other.
- **One rule decides every question.** An expensive fork — stored data, a contract outside the
  codebase, permission boundaries, money — is asked when someone is present and recorded as an
  assumption when nobody is. Everything else is decided silently either way, so a feature with no
  such fork never waits for approval.
- **Review is one pass that reads the entry, plus a security pass on a diff trigger.** The
  `code-review` plugin's fan measured 6.7M tokens for 2 findings against the in-house reviewer's
  0.66M for 12, so it is not run per feature. `agent-kit:reviewer` returns; it also checks that every
  line of the entry has a test, which is how a feature that looks proven and is not gets caught.
- **Tests come from the entry, not from an agent's imagination** — one per line of what changes,
  what is seen, and what can go wrong, at the highest seam that can see it. The risky ones are
  written before the code, which is the proof they can fail; the separate pass that used to
  establish that is gone, along with the `tester` agent.
- **The pull request is opened after the review**, so it holds reviewed code from its first minute.
- **`run.json` and `run.log`** — the run's state and a one-line-per-event trace of when things
  happened, never read back, so a run that took an afternoon can be diagnosed afterwards.

Also: `rules/pull-requests.md` returns as a file rather than as prose repeated per command, and the
repository gains `scripts/measure.py`, which reports what a run cost per session or per branch.

## 0.18.0

The kit is being rebuilt from an empty command set. A measured run of 0.17.0 put a feature at ~27M
tokens, of which the review wave was 13M — the `code-review` fan costing 6.7M for 2 findings against
`agent-kit:reviewer`'s 0.66M for 12 — and verification at ~70%. The diagnosis was not any one of
those numbers: nearly every expensive mechanism existed to insure the kit against its own autonomy,
and four separate rules in the old text existed only to serve other rules. Autonomy stays; the
insurance goes.

This release is the first step of that rewrite and is **not a working kit**: only `blueprint` is
implemented. Install `v0.17.0` if you need the complete previous version.

- **Nine commands become five** — `blueprint`, `fix`, `ship`, `sprint`, `mvp`. `debug` and `address`
  fold into `fix`; `riff` and `ideate` are dropped outright, because product thinking with nothing
  to build is a conversation, not a command; `idea-interview`, `stack-playbook`, `docs`,
  `docs-reflection` and `screens-riff` fold into `blueprint`; `brainstorming` and `writing-plans`
  collapse into a step inside `ship`. `screens` is deferred until its format is simpler.
- **`blueprint` — the knowledge layer.** One command owns what the project knows, and it is the only
  writer: an interview that resumes where it stopped, and `blueprint --check`, mechanical enough to
  run ahead of every other command and silent when clean. Knowledge lives in `docs/knowledge/`, one
  file per slot, seeded from templates that carry the shape of a record — so the format and its
  description cannot drift apart, and each file declares its own required fields.
- **Feedback from runs, without a bookkeeping layer.** A run that has to assume something leaves a
  marked block under the entry it stood in for, and that assumption is the decision of record until
  the owner changes it. Resolving one is rewriting the entry and deleting the block; there is no
  `resolved` field anywhere.
- **Removed:** the `Stop` hook, which checked that a step had *a line* the agent wrote itself and
  blocked unrelated conversations that happened to be on a feature branch; the sprint watchdog,
  whose three headless levels made progress unobservable and which never once recovered correctly;
  `--manual` and the interactive-mode rule; three of the four passes that re-derived whether the
  documentation was still true; and the review levels stacked on top of the first one, which is what
  produced thirty findings and then twenty more.
- The plugin no longer declares `code-review` and `pr-review-toolkit` as dependencies. Whether a
  review wave pulls them back in is decided when `ship` is written.

## 0.17.0

A run costs its context multiplied by its steps. Measured over four headless `ship` runs — 207M
tokens of context re-reading for four features, 40% of it inside the subagents they spawned — and cut
where the measurement pointed. The measurement also corrected two assumptions: verification is 70% of
a feature's cost rather than construction, and `tester` alone is a fifth of it.

- **A feature is carried by four short sessions, not one long one.** `ship --stage
  <design|build|review|deliver>` runs one stage and stops; `sprint` launches them in turn. The
  handoff is the spec, the plan, its Run log and the commits, which the pipeline already kept on
  disk for exactly this. Splitting divides the part of the cost that grows with a session's length
  while the handoff each stage re-reads at its start stays — which is why the saving lands near half
  rather than the quarter the growth term alone would suggest.
- **One review wave over a frozen diff.** `reviewer`, the `code-review` plugin's fan and the
  security pass ran serially, each with its own fix-and-reverify round over a diff that barely
  changed between them. They now run together, findings are deduplicated across passes, and there
  is one round of fixes and one verification. Security stops being a separate step and becomes the
  wave's third question.
- **The pull request opens before the review, ready rather than draft.** The `code-review` plugin
  needs a pull request and declines drafts, so a stacked feature's PR — drafted the moment it opened
  — silently lost the strongest review in the pipeline, and children were rebuilding that fan by
  hand out of generic agents. The `deliver` stage converts it to a draft as the last thing it does,
  including when the run ends on a blocker; `sprint` checks that it did.
- **The wave is scaled to the diff.** A change with no executable surface earns the conformance
  question and a named skip, not a dozen agents proving that markdown has no injection flaws.
- **Stages name a model tier.** Design and review on the strong model at high effort, build and
  deliver on the mid tier at lower effort. What makes a cheaper build safe is the review wave
  immediately after it, on the strong model over the same diff.
- **`ship --brief` stops rewriting the sketch.** It is copied to `docs/specs/` as the feature's spec
  and gains only what exploration changed; the plan becomes a task list whose lasting job is hosting the
  Run log. Children had been producing two to three times the sketch's volume restating it.
- **`sprint` writes `orientation.md` once per batch** instead of every child working out the
  repository for itself, delegates each `upstream.md` to a subagent so a finished feature's Run log
  never enters the orchestrator's context, asks for at most one heavy verification layer per
  sketch and says why slow is not free, and waits for the named reset hour after a rate-limit exit instead of polling a
  closed window.
- **Stages hand off through a file, not an assumption.** `handoff.yml` beside the spec carries the
  branch, the base the reviewer must diff against, the plan's path, the last finished stage and the
  suite result. It is a record, not a gate — nothing in it proves a stage did what it claims — but a
  later session is never left deriving facts it cannot see.
- **A sprint survives losing the session that drives it.** Every recovery path in the kit — resume
  the stage, wait for the reset hour, retry once — assumed an orchestrator was alive to run it, and
  the one failure none of them covered was that orchestrator dying. `sprint` now starts a detached
  watchdog at preflight that resumes the run when no child is producing output and the heartbeat has
  gone stale, and exits when the queue says `done`. Liveness is measured by work rather than by
  process existence: a rate-limited `claude -p` can sit in the process table indefinitely, and a
  watchdog that matches it concludes a run is in flight and skips every tick — in silence, if it only
  logs when it acts. It logs every tick now.
- **The proof loop is ranked, not exhaustive.** `tester` proved every assertion could fail by
  editing, running, checking and reverting — a fifth of a feature's whole cost, and it rebuilt a
  throwaway mutation harness in `/tmp` on every run. It now proves the behaviours that carry real
  risk, says which it did not, and is told to commit a mutation script once rather than write one
  each time.
- **The review wave reconciles findings before fixing them.** Deduplication removes findings that say
  the same thing; a structural finding makes line-level findings inside the code it condemns
  pointless, and the fix round used to pay for both.
- **`engine.md` gains the arithmetic**: read the part you need, cap long command output, batch
  edits. It applies to every session the kit governs, not only to pipelines.

## 0.16.0

A pipeline can no longer end its turn with steps left, and a run that stopped early is resumed
instead of rebuilt.

- **The Run log carries the run's position, not just its surprises.** It opens with the branch and
  the ordered steps ahead, and each step is settled by its own line as it ends — `done`, or
  `skipped: why`, or `blocked: why`. Every outcome settles a step; only silence does not.
- **A `Stop` hook holds the run to that list.** Step order is prose, and prose loses to whatever
  instruction is freshest in a long context: a review prompt read inline can reassign the role, and
  the turn ends with a report where a pull request was due. The hook reads the plan on the current
  branch and hands the turn back with the steps that have no line. It nudges once, so it cannot loop,
  and it is silent unless a plan on this branch declares both header lines — an ordinary
  conversation, a repository that never ran a pipeline, and every plan written before this version
  are all untouched.
- **`sprint` stops trusting exit code 0.** A child that ended is not a child that finished: before
  marking a feature `done` it reads the Run log for unsettled steps, and resumes the child's own
  session rather than relaunching the feature or finishing the steps by hand from the orchestrator,
  which holds none of the feature's context.
- **Each child runs under a recorded session id.** `sprint` launches with `--session-id` and keeps
  the uuid in `queue.yml`, which is what makes that resume a `--resume` rather than a guess about
  which transcript belonged to the run.

## 0.15.1

A pipeline's named delegations stop being negotiable.

- **`reviewer` and `tester` are steps, not judgment calls.** The baseline's advice on subagents was
  written entirely as restraint — they cost context, don't spawn one for small work, keep the count
  low — and never said that a delegation a pipeline names by name is that step rather than an option.
  Two of three headless `ship --brief` runs in one sprint skipped Review and Test on that reading
  while a third ran them; nothing in the kit's text made the third one right.
- **A host instruction against spawning agents is about initiative, not about a requested step.** A
  session may arrive carrying one. Typing the command is the request, so it does not reach the
  pipeline's own delegations — and doing the review inline instead is not a substitute, since the
  point is that the reviewer did not write the code.
- **A delegation that cannot run is said out loud** — named, with the reason, in the run log and the
  PR. Skipping one in silence produces a feature that looks reviewed and is not.

## 0.15.0

The always-on governance gains the one rule it was missing: keep the diff surgical.

- **Only what the request needs changes.** No reformatting, no reworded comments, no improving the
  code you happened to open on the way, and the surrounding style is matched even where you would
  have written it differently — style drift is what makes a diff unreadable for whoever reviews it.
- **Orphans are split from dead code.** An import, variable, or function that nothing calls *because
  of this change* is cleaned up; code that was already dead is named and left for the owner. Until
  now the baseline said only that the best change often removes code, which pulled the other way.
- **A finished diff has a test.** Every changed line traces back to the request — the author-side
  counterpart to the `reviewer` agent's scope check, which until now was the only place this was
  looked for, and only after the code was written.

Adapted from the Karpathy-Inspired Claude Code Guidelines; see the plugin's `NOTICE.md` for what was
taken and what was deliberately not.

## 0.14.0

The playbook stops interviewing the owner about architecture and starts showing them what it
concluded.

- **Nothing about architecture is asked any more.** Each area's stance is derived from two sources
  the skill already had: what the code does, and what the stack is understood to do well, researched
  from the framework's own documentation and the ecosystem's catalogues rather than recalled. The
  research step now runs before the stances that depend on it.
- **The skill closes by putting its conclusions up.** One screen — stack profile, the stance table,
  the library map's picks, the testing idioms, and any place the code and the stack's practice
  disagreed, each with what was done about it — followed by an invitation to add what only the owner
  knows. An owner reacting to a finished playbook remembers what they care about; the same person
  facing a blank architecture question at bootstrap does not, which is what the old interview asked
  them to do.
- **Silence is consent.** No answer leaves the playbook as written, so an owner who does not care
  pays one screen and nothing else. What they do add is written in as their rule, in their words,
  and preserved by later refreshes. Headless runs ask nothing and send the summary to the run record.
- **The refresh asks nothing either.** A stance the code has parted from, and a new area with no row
  yet, are reported in its one-line note instead of interrupting a feature with a question.
- **`idea-interview` stops asking the same thing in other words.** "Which conventions are real, and
  which are legacy you would rather not spread" is the playbook's close-out question, asked once,
  where there is something concrete on screen to answer against.

## 0.13.0

The architecture stance stops being one question with one answer.

- **A project gets a stance per area, not a stance.** The domain, the HTTP surface, background work,
  the client, how data is reached — a project answers the architecture question separately wherever
  its answer actually differs, and asking for a single global one forced everything after it through
  a wrong frame. A CRUD app still has one line; a layered product has three or four. The areas are
  derived from the application type and from what the codebase already separates, never from a
  checklist — inventing areas a project does not have is the failure mode, because each line becomes
  a rule someone obeys forever.
- **The question is where to deviate, not what to choose.** The framework's own idiom holds
  everywhere the owner does not depart from it, so the round asks about departures and their cost.
  Nobody answers "choose an architecture" well at bootstrap, before the code that would inform the
  answer exists; everyone can answer "here is where I would leave the framework's path, and why".
  Areas where the default is plainly right are declared rather than asked.
- **The playbook records a table, looked up by area.** `brainstorming` names the stance for the area
  its feature changes and designs inside that row; `reviewer` checks against the same row. A feature
  touching the HTTP surface no longer reads a paragraph about the whole product to find its rule.
- **A refresh may ask exactly one question**: the project grew an area the table has no row for. It
  still never changes a recorded stance, and it still reports, by area, where the code has parted
  from what the table says.

## 0.12.0

0.11.0 fixed the presenting rule, and two skills that ask the owner questions did not notice: they
carried a hand-copied fragment of the rule instead of pointing at it.

- **`stack-playbook` and `idea-interview` now defer to the rule** rather than restating a piece of
  it, so they pick up the counterweight, the codebase-grounded questions, and the three decision
  groups — and the next fix to the rule as well.
- **The architecture stance is asked with its consequences attached.** It is the most expensive
  decision the kit ever records and every later feature inherits it, yet it was one question
  answerable in one word, leaving the agent to invent where boundaries sit and what a module is.
  The concrete reading of the stance for this repo now goes up together with the question. Derived
  without the owner, it is marked `derived` and surfaced where the run's decisions are read — the
  PR's Assumptions, the sprint report — instead of only in a log.
- **A refresh reports a stance the code stopped following.** It still never changes the stance, but
  where the boundaries in the document are no longer the boundaries in the code it says so in one
  line. Which of the two is wrong is the owner's call, and they cannot make it while nobody tells
  them the two parted.
- **`ideate` checks the roadmap against the code** before generating, for the claims the riff leans
  on. Ideas argued against a product that was last written down six months ago are the ones that
  feel beside the point.
- **Depth reaches the product layer.** `ideate`'s proportionality off-ramp is taken readily on a
  `light` feature and not at all on a `deep` one — the owner asked for the discussion, and the
  product layer is where its cheapest version happens.

## 0.11.0

Design conversations stop being thin. Every rule in the kit pushed one way — spend less of the
owner's attention — and with no counterweight the pipelines settled into asking two shallow
questions and calling the design agreed.

- **The sweep before the cut.** `brainstorming` now enumerates candidate questions across fixed axes
  — states and transitions, unhappy paths, data over time, permissions and boundaries, altered
  behavior, neighbours, the edge of the feature, scale, reversibility — and only then applies the
  filter. Too few questions was never a strict filter; it was an enumeration that never happened, and
  a question picked off the top of the head is exactly the one that reads as random.
- **Silence has a price too.** A decision expensive to reverse — a migration, a public interface,
  visible behavior, a boundary the next feature builds on — is now put to the owner even when the
  design holds a confident default, because after the gate it is settled alone. The pruning rule
  stays; it stops doubling as an excuse to arrive with nothing.
- **Questions name this codebase.** A question that would read the same in any project is treated as
  evidence the exploration has not happened yet, not as a question.
- **Documents are checked against the code.** Only the claims a feature leans on, and a divergence is
  put up as a fact — *the spec says X, the code does Y* — rather than resolved silently. Stale
  documents are the main reason sound reasoning produces odd questions.
- **Neighbours are found before anything is proposed.** Callers, subscribers, and stored data of
  every surface being altered, and whether what they see changes. An unattended run moving a
  neighbour's behavior is the most expensive thing it can do.
- **A third decision group: *left to the build*.** What stays open past the gate, each line with the
  default that will be taken, so the owner can pull any of it back while it is still cheap instead of
  meeting it as an assumption in a pull request. Autonomous mode treats those defaults as answers.
- **Depth is chosen, not guessed.** `light` / `normal` / `deep` per feature — `sprint` agrees it when
  the batch is composed and records it in `queue.yml`, `ship` takes `--deep` and `--quick`, and with
  neither the level is judged and stated in one line so it can be moved. A `deep` feature gets two
  rounds, shape then mechanics, and its internal mechanics become fair game for questions.
- **The sprint brief loses its clock.** The hour of attention and the ten minutes per feature are
  gone; the brief ends when nothing expensive to reverse is still open. A batch of small features
  takes minutes, one turning on a migration takes as long as that decision takes.

## 0.10.0

A sprint stops being a stack of pull requests the owner has to merge in the right order, and becomes
one pull request that either lands the batch or does not.

- **The batch is delivered by an integration PR.** Stacked feature PRs target their parent's branch,
  so their merge button moves code sideways rather than into the default branch — merge them in the
  wrong order, or with a squash, and the sprint quietly fails to land. The run now ends by branching
  `sprint/<slug>-integration` off a freshly pulled `main`, merging the feature tips into it,
  resolving conflicts between features there, and running the project's full suite on that tree —
  the only tree that matches what `main` will contain, and one no feature PR had ever been checked
  in. That branch's pull request is the sprint's single mergeable one. It asks to be merged with a
  merge commit rather than a squash, and the run checks once that the repository allows it.
- **Feature PRs become drafts.** They keep doing what they were good at — a narrow diff to read,
  a place for review comments, its own CI — and stop pretending to be a way to land code. The rule
  is conditional on the base branch, so it applies to any pull request opened against another
  feature's branch, and `sprint` verifies it as a backstop when a headless child does not.
- **`--integrate <feature ids>` takes the batch in parts**, for an owner who wants two features in
  production before committing to the rest. A batch must be closed under dependencies — a feature
  ships with its ancestors, whose branches carry its commits — and a later batch needs nothing done
  to the feature branches: it is built from the new `main` the same way. The same rebuild covers a
  review round through `/agent-kit:address` and a `main` that moved underneath an open batch.
- **Branches are swept, not remembered.** A branch whose `git diff origin/main...<branch>` is empty
  adds nothing to `main` and is deleted locally and on the remote, its pull request closed with a
  line naming the integration PR that carried it. The test errs one way only: a branch still holding
  unlanded code never reads as empty. It runs at the end of a run and in the next sprint's preflight.

## 0.9.0

The kit learns to draw the app. A project's screens stop being a thing you hold in your head and
become a picture the agent keeps true.

- **New skill: `screens`** — every screen of the app as a wireframe card, every transition as a
  labelled arrow, in one self-contained HTML file that opens with no server and no network. Built
  from the project's own documents and code: what the code has is `implemented` and points at the
  file that implements it, what only the documents promise is `planned`. Later runs **reconcile
  rather than regenerate** — ids are never reused, so a screen number stays a stable address for
  as long as the project lives. The viewer ranks screens by their transitions, left to right:
  a screen's column is the longest path to it, so entry screens stand at the left, every step
  forward points right, and a back edge is routed under the ranks it spans. `flow` groups screens
  where that costs no crossings; it does not place them. A project with no screens — a library, a
  CLI — gets one sentence and no map.
- **New skill: `screens-riff`** — the map shows what the app is; this asks what it should become,
  and answers in the same picture. Ideas arrive as one structured round; taken ones land as `idea`
  cards next to what already exists, turned-down ones stay as `rejected` memory so the same
  proposal never costs the owner attention twice, and "not now" is a third verdict that writes
  nothing. Improvements that are not screen-shaped go in the written review, never on the map.
- **A screen id is a unit of work.** `/agent-kit:ship S7` resolves against the map — the card's
  title, purpose, layout, and transitions seed the task. And `docs-reflection` treats the map as a
  living document: a feature that changed what the app shows flips statuses and adds what it
  introduced, in the feature's own PR, because an `implemented` card points at code that exists
  only there.
- **One file crosses the ownership line on purpose.** The viewer is plugin code that lives in the
  project's `docs/`, and later runs replace it — otherwise viewer improvements would never reach a
  project that already generated a map. The rule and its single exception are written down in
  `docs/developing.md`, the file says so in its own header, and the validator fails if that marker
  disappears. The map beside it, `screens.data.js`, belongs to the project.
- **`sprint` no longer talks about the night.** The command was written as an evening brief, a
  night of building, and a morning report; nothing in the design needs the hour, only that the run
  is unattended. Same steps, time-neutral wording — start a sprint over a working afternoon if
  that is when you have the hour.
- **The validator grew teeth for the payload's JavaScript**: it is parsed, the demo map is loaded
  the way the viewer loads it, a page's `<script src>` must ship beside it, any `sources.<key>` the
  payload reads must exist in the manifest template, and the demo map must obey the counter and
  code-path rules it teaches.

## 0.8.0

The kit learns to run a night shift: one evening hour of the owner's attention becomes a batch of
features built while they sleep.

- **New skill: `sprint`** — an evening brief, a night of ship runs, a morning report. The brief
  composes a coherent batch of 3–6 features with an explicit dependency order, scopes them in one
  pass, and sketches each design in about ten minutes of owner attention; approved specs land in
  `.agent-kit/sprint/`. The run executes each feature as `ship --brief` in its own fresh headless
  session, one at a time so dependent features can stack — each builds on its parent's *branch*,
  and nothing is ever merged without the owner. The night closes with an integration check over
  every stack tip and a one-screen report led by the decisions taken without the owner.
- **`ship --brief <spec>`** — a ship run with no interactive gates, for a design sketch the owner
  already approved. Deviations follow a ladder: implementation mechanics are the run's to choose, a
  settled approach that cannot work as written is replaced and recorded, and product scope is never
  changed silently. A sibling `upstream.md` tells the run what actually happened to the features it
  builds on, as opposed to what the sketch imagined.
- **New skill: `stack-playbook`** — the agent knows where it is and asks the ecosystem first. It
  detects the stack from dependency manifests and lockfiles, mines the codebase for the house
  conventions, records the owner's architecture stance, and researches the installed framework's
  idioms and library map from the ecosystem's own sources — training-data knowledge of an ecosystem
  is stale by definition. The result is short justified rules written into the registered
  coding-standards document, ending with a fingerprint of the manifests it was generated from.
  `ship` checks that fingerprint at the head of every run: current is silent, missing triggers a
  full generation, stale refreshes only what drifted — never the stance, which changes only on the
  owner's word.
- **The presenting rule** (`rules/presenting.md`) now governs everything put in front of the owner:
  one screen per subject, structure before prose, decisions split into *your call* and *taken as
  given*, questions batched with a marked recommendation each.
- **PR descriptions are scannable** — verdict first, evidence collapsed.

## 0.7.1

Found while running the kit on a real project: with the `code-review` plugin installed, a feature was
reviewing its own diff in three waves — `agent-kit:reviewer`, up to three `pr-review-toolkit`
specialists, and then the plugin's own dozen agents in the PR step. 0.7.0 added the third wave without
reconciling it against the first two.

The Review step now branches on whether the plugin is reachable, splitting by responsibility rather
than piling on depth:

- **Plugin available** — `agent-kit:reviewer` covers only what nothing else can, whether the diff is
  the feature that was approved. The bug hunt belongs to the PR step, where the plugin's five
  independent reviewers and its confidence-scoring pass do it better. The `pr-review-toolkit`
  specialists stop being a default and become an escalation for a change that earns a specific lens.
- **Plugin absent** — unchanged from 0.7.0: the reviewer carries correctness too, and the specialists
  are worth spawning, because nothing downstream will look again.

One wave either way. The step also states the agent budget out loud — roughly one reviewer here, a
dozen in the PR step — so the next person to add a tier has to notice the total first.

## 0.7.0

One install gets everything. 0.6.1 and 0.6.2 taught the kit to *use* Anthropic's `code-review` and
`pr-review-toolkit`; this makes them arrive on their own.

- **The kit declares both as dependencies.** `/plugin install agent-kit@agent-kit` now resolves and
  installs them too, and Claude Code lists what it added at the end of the install. Nothing to
  install by hand, and no per-project step.
- Cross-marketplace dependencies are blocked by default, and the allowlist that unblocks them belongs
  to the marketplace the user installs *from* — this one. `marketplace.json` now carries
  `allowCrossMarketplaceDependenciesOn: ["claude-plugins-official"]`. Without it the install fails
  outright, so the validator refuses to ship a cross-marketplace dependency whose source is not
  allowlisted.
- No version constraints on either dependency: those resolve against git tags in someone else's
  repository, so pinning would break the moment their tagging convention differed.
- If the dependencies cannot be reached at all — an organization policy blocking the official
  marketplace, or a Claude Code old enough not to ship it — they are left unresolved and the kit
  still runs. Every step that uses them is written "when enabled", and the `reviewer` agent covers
  correctness alone. You lose depth, not the pipeline.

## 0.6.2

Follow-up audit of the same class of bug as 0.6.1: an instruction the agent cannot act on.

- **Plugin agents and commands carry their plugin's name**, and 0.6.1 wrote them bare. Delegating to
  `silent-failure-hunter` resolves to nothing; `pr-review-toolkit:silent-failure-hunter` is the real
  name. Same for the review pass on the open PR, now spelled `/code-review:code-review`.
- The README gives the two install commands and says the official marketplace is already configured,
  so nobody has to work out where these plugins come from.

Audited and found sound, no change needed: the kit's own five pipelines are user-invoked and its five
internal skills are not, so pipelines can call them; `/security-review`, `/simplify`, and `/run` are
model-invocable, unlike `/code-review` and `/verify`; the `gh` and CI steps already degrade when the
session cannot reach them; and the guard hook asks on `git push origin main`, `git push --force`, and
`gh pr merge` while staying silent on `git status`, `echo "git push --force"`, and a push of
`claude/main-fix`.

## 0.6.1

The kit's main review path never ran. Found in real use, not by the validator.

Claude Code's bundled `/code-review` and `/verify` are marked `disable-model-invocation` — a property
of those skills, not a session setting, so no agent in any session can start them. The kit wrote both
into pipelines as the primary path, which meant:

- `ship`'s Review step fell through to its fallback line every time; the real reviewer was the
  fallback and the documented path was decoration.
- `ship`'s Test step nominally confirmed the running app through `/verify`.
- **`fix`'s Review step did nothing at all** — `/code-review` was its only reviewer, with no
  fallback beneath it. `debug` inherited that through "continue through the tail of `fix`".
- Worst of it: the `reviewer` agent was instructed *not* to hunt for bugs because "`/code-review`
  already does that". Nothing did.

Fixed by making every path something an agent can actually reach:

- **`agent-kit:reviewer` is the primary reviewer** in `ship` and `fix`, and covers correctness as
  well as design conformance. It gained a Correctness lens, and two lenses borrowed from what the
  bundled review does and the kit had no answer for: **History** (`git blame`/`git log -L` over the
  replaced lines, so a "cleanup" does not delete a guard added on purpose) and **Settled elsewhere**
  (review comments on the PRs that last touched these files — conventions the project agreed to
  without writing down).
- **Plugin commands and agents *are* model-invocable**, unlike their bundled equivalents. So the
  Review step now escalates through `pr-review-toolkit`'s specialists when a project has that plugin
  enabled, and the PR step runs the official `code-review` plugin's command on the open pull request
  — same multi-agent, confidence-scored architecture as the bundled version, reachable by an agent.
  Both optional; the kit works without them.
- **The Test step drives the app with the project's own commands.**
- **The bundled pair is offered, not invoked.** The PR description's Review section ends with
  `/code-review` and `/verify` as commands the owner can copy — the only way they get offered at all,
  and the owner is reading it at the moment a keystroke is cheap. `ship` explicitly must not stop and
  wait for them: after design approval the owner may be asleep, and a pipeline that waits for a human
  never finishes.

## 0.6.0

Two carriers for guarantees the kit could previously only phrase as prose: the project's CI, and a
permission gate in front of the commands the governance forbids. Nothing for an installed project
to migrate; the CI bullet applies at the next bootstrap or `--rebootstrap`.

### CI, detect-first

CI is the only verifier that outlives a session — everything the run proves locally dies with it,
and 0.5.0 taught `ship` to watch `gh pr checks` without ensuring there was anything to watch. CI
now gets the same treatment as the author's docs:

- Bootstrap detects an existing workflow and registers it in the manifest (`sources.ci`) instead
  of generating a second one. Where the declared Verification layers and the workflow disagree,
  that is a finding for the owner, never an edit.
- On a repository with no CI, it proposes a workflow running the Verification commands from the
  project instructions verbatim, written only on an explicit yes.
- When `ship`'s Test step installs new tooling, it extends a workflow the kit generated or the
  owner approved; a CI the project brought with it is not the kit's to edit — that gap goes to the
  Run log as a manual action.

### The guard hook

The rules the governance states as "never" — merge a pull request, push the default branch,
force-push — were promises. A new PreToolUse hook turns them into a confirmation: a matching
command comes back as an explicit permission question instead of running. The decision is "ask",
never "deny" — interactively the owner confirms in one click; in an unattended autonomous run
nobody answers, so the command does not run, which is exactly what the rules promised. Parsing
lives in `guard.py` and judges each pipeline segment on its own words, so `echo "git push"` or a
push of `claude/main-fix` does not cry wolf — a guard that does teaches everyone to click through
it. Everything that is judgment rather than invariant stays prose.

## 0.5.0

The run survives its own length, and the pipeline no longer ends the moment the PR opens. Nothing
for an installed project to migrate.

### The run log

Assumptions and manual actions used to exist only "in the PR" — which is written at the end of a
run long enough to outlive its own context, so a decision taken in hour three could be gone before
the PR step came to record it.

- The plan now ends with a `## Run log` section, appended to and committed as decisions happen:
  assumptions, deviations from the approved design, skipped verification layers, owner-only work,
  the tester's skipped-layer report.
- The PR's Assumptions and Manual actions are assembled from it rather than from memory, and a
  resumed or compacted session picks the run's state up from disk instead of losing it.

### After the PR

- **`ship`'s PR step now includes CI.** A red pipeline is part of the step, not the owner's
  problem: check `gh pr checks` after opening, fix in-scope failures, rerun the verification the
  fix put at risk, push again.
- **New command `/agent-kit:address`** closes a review round on an open PR: collect the owner's
  comments and the CI status, sort them out loud — in scope, design change, out of scope — fix,
  rerun what the fixes put at risk, push, and answer every thread. An owner comment that asks for
  a design change counts as the new approval; only contradicting comments are a question.

### Fixed

- The marketplace description still advertised `review`, `test`, and infrastructure provisioning,
  all removed in 0.4.0. It now mirrors `plugin.json`, and the validator keeps the two identical.
- `riff` and `docs` did not say what to do on a project with no manifest; both now handle it
  instead of reading null sources.
- `ship`'s `/verify` step gained the fallback the other delegated tools already had: no `/verify`
  in the session means starting the app with the project's own commands, not skipping the check.
- The `reviewer` agent no longer assumes the default branch is named `main`.
- `fix` states its interaction contract: no design gate, user presumed nearby, ask only when a
  real ambiguity changes what gets built.

### Smaller

- `idea-interview` batches independent facts into one message of up to four questions and keeps
  one-at-a-time only for decisions that depend on each other.
- `scripts/cloud-setup.sh` is now required to check before installing and no-op in seconds when
  everything is present — it runs at every session start, local ones included — and the hook
  carries an explicit 600-second timeout for the first, slow run.
- `docs-reflection` closes the learning loop: a review finding that traced back to an unwritten
  rule is a missing line in the coding standards, and a gap in the project instructions is
  proposed in the PR description rather than silently repeated next feature.
- The internal skills describe themselves as invoked by the pipelines rather than as "use when…"
  triggers, so plain conversation no longer competes with the engine's rule that free text is
  never routed into a pipeline.

## 0.4.1

Housekeeping on the payload. No new behavior, nothing for an installed project to do.

- **`/simplify` moved from the Test step to Review.** It is a quality pass, not a test; it sat
  between running the suite and checking the suite, and it edits the diff after the suite has run.
  It is now gated on a diff large enough to be worth reading through, and framed as what it does —
  readability, not a third opinion on correctness. Running it made the Review step's own "do not add
  a third opinion" line false, which is fixed.
- **Dropped `ship`'s restatement of "prove each test can fail".** The `tester` agent performs it and
  documents it; restating a subagent's job in the caller is the scaffolding that causes
  over-verification. The flake rule, which was genuinely new, folded into the suite step.
- **The two review passes are stated as independent** and may run concurrently.
- **Removed history and design commentary from the payload.** Provenance comments recording which
  sub-skill references were localized, that a browser companion was dropped, that a spec-review gate
  was removed, and that a code-per-step format was replaced — eleven lines telling the model what
  the kit used to be. `NOTICE.md` carries the MIT attribution and remains intact. Also gone: the
  kit explaining its own economics mid-instruction, `engine.md` describing itself, and
  `idea-interview` referencing its own steps by number, which breaks the moment they are renumbered.

## 0.4.0

The kit is a Claude Code plugin, it delegates the steps Claude Code now does better than a
hand-written prompt, and it is cut back to what it was actually for. See
[migrations/0.4.0.md](migrations/0.4.0.md) for what an installed project has to do.

### Reuse over reinvention

The kit said "prefer framework primitives and existing dependencies" and left it there. That is a
statement of preference; it never asked anyone to go and look, which is why hand-rolled helpers get
written — by someone who did not check.

- **New always-on section, "Reaching for what already exists"**: search for the behavior before
  writing it, search by behavior rather than by the name you would have chosen, and prefer in order
  the language, the framework, an installed dependency, a maintained library, and only then your own
  code. It states when a new dependency is the right call (well-defined, long-solved problems — dates,
  money, parsing, retries, crypto) and when it is not, and asks for the reasoning out loud rather
  than a silent `package.json` edit. Being always-on, it applies to `fix`, `debug`, and plain
  terminal work too, not only to `ship`.
- `ship`'s Build step points at it and at language-server tooling, since find-references is what
  makes the search actually succeed.
- **The `reviewer` agent gained two lenses**: *silent failure* — swallowed errors, over-broad catch
  blocks, and fallbacks the user never learns about, which survive both the suite and a bug hunt
  because nothing is red — and *reinvention*, which names the existing helper when it finds one.
- The plugin README now points at language servers and at `pr-review-toolkit` as worthwhile
  companions, and says plainly why writing tests is not delegated the way review and security are:
  everything the kit hands off inspects finished work, and authoring tests means writing code inside
  one project's conventions and seams.

### Verification

The target moved from "the tests pass" to "someone can merge this without reading the diff".

- **How a feature will be proven is now decided at design time**, as part of the design the owner
  approves, rather than improvised after the build. The new verification plan in `brainstorming`
  fixes three things while the owner is still present: the **seams** the feature is tested at
  (prefer existing ones, take the highest that still sees the behavior, keep the count near one),
  the **layers** it needs, and the **tooling gap** — what has to be installed to run those layers.
- **Missing test tooling gets installed** during the build when the session can do it, added to
  `scripts/cloud-setup.sh` so later sessions and CI inherit it, and recorded in the project
  instructions. Nothing is installed that the owner did not see in the approved plan. What the
  session cannot install becomes a manual action stating what stays unproven without it.
- **The `tester` agent gained a layer catalogue** — static, unit, integration, contract, end-to-end,
  regression, property-based, snapshot, accessibility, concurrency and idempotency, performance —
  and must report which layers it deliberately skipped. Contract tests are called out specifically:
  they are where "works on the backend, broken on the frontend" lives, and they were the layer most
  often missing entirely.
- **Every new test must be proven able to fail.** Invert the condition, watch the test go red, put
  the code back. A test that passes against broken code buys confidence it has not earned, and this
  is what separates a suite you can rely on from one that merely runs. Where the project has a
  mutation-testing tool, a surviving mutant counts as an uncovered behavior.
- **A flaky test is a defect, not an annoyance.** One known flake teaches everyone to ignore red,
  and then nothing in the suite means anything. `ship` now fails its own bar on a flake instead of
  noting it.
- **`/simplify` runs in the Test step** — four parallel agents covering reuse, simplification,
  efficiency, and level of abstraction. `/code-review` finds bugs at the next step; this is the pass
  that keeps the diff worth reading.
- Static analysis is stated as a test layer rather than a formality: a type error is a failing test.
- The project instructions template gained a Verification section with one line per layer, and
  `<none yet>` as a deliberate signal for the design step to propose adding a missing one.

### Bootstrap

- **`bootstrapped` was one flag doing two jobs**, so "I know exactly what I want built" waited behind
  "first write a roadmap" — even though a free-text task already skips the only step that needs one.
  The two concerns are now separate. Technical setup (manifest, project instructions, coding
  standards, cloud-setup script) is part of any run and needs no gate; it is cheap and mostly
  detection. Product bootstrap (idea and roadmap) gates only what it actually protects: task
  selection and product scoping.
- **`ship <task>` on a project with no product docs now builds the task**, skipping Task and Ideate,
  saying out loud what it is working without, and repeating that in the pull request. It is
  deliberately not blocked and deliberately not silent — the owner sees the notice on every review
  and runs `--rebootstrap` when they have had enough. `ship` with no task is unchanged: it still
  runs the full interview and stops at a bootstrap PR.
- **`idea-interview` splits into a setup half and a product half**, so `ship` can ask for the first
  alone.
- **`idea-interview` branches on whether code already exists.** A fresh repository is interviewed
  for everything. A repository with a real codebase gets the flow inverted — read the code, README,
  and history first, bring a draft, ask the owner to correct it — and spends their attention only on
  what code cannot tell you: intent, what is deliberately out of scope, what comes next, and which
  conventions are real rather than legacy. The roadmap stays required, but covers only what is
  ahead instead of reconstructing a phasing of what already shipped.

### Scope

Nine commands became five. The kit exists for autonomous feature development, and everything that
was not that has gone.

- **Removed `/infra`, and the `infra-local` and `infra-cloud` skills** with their hosting catalog
  and mobile-env references — 333 lines, a quarter of the payload. Provisioning is interactive by
  nature, was the most stack-opinionated material in the kit (validated only on Laravel plus Expo),
  and had nothing to do with shipping a feature autonomously. It was a second product living inside
  the first.
- **Removed `/review` and `/test`.** Both had become one-line wrappers: `/code-review` is a built-in
  command you can simply type, and "cover this with tests" works as a plain request. Nothing is lost
  inside `ship`, which still runs the `reviewer` and `tester` agents at their own steps.
- **Removed `/go`.** A router over nine commands stops paying for itself at five, and it put a menu
  between the user and the work. Bootstrap is reached through `ship`, which already detects a
  missing manifest and runs the interview first.
- `manifest.yml` drops the `infrastructure` block and `sources.deployment`, and instead invites
  project-specific `sources` keys of your own.

### Distribution

- **The kit installs as a plugin**: `/plugin marketplace add IliaSadovskii/agent-kit` and
  `/plugin install agent-kit@agent-kit`. The repository is its own marketplace.
- **Removed `install.sh`, `kit-update.sh`, `kit.lock`, and the whole conflict/checksum machinery.**
  Versioning, updating, and per-file replacement are what the plugin system already does; the kit
  had rebuilt all of it by hand.
- **Removed the adapter layer.** `catalog.tsv`, `generate-adapters.py`, and the 19 generated
  wrappers under `.claude/` existed because the payload had to serve two providers. With one
  provider a wrapper that points at a canonical file is pure indirection, so each skill now *is*
  the canonical file. 88 payload files became 30.
- **Commands are namespaced**: `/ship` is now `/agent-kit:ship`, and so on for every command.
- **`engine.md` arrives through the plugin's SessionStart hook** instead of a managed block in the
  project's `CLAUDE.md`. The kit no longer writes to `CLAUDE.md` or `.claude/settings.json` at all.
- `.agent-kit/project/manifest.yml` and `instructions.md` are unchanged and stay in the project.

### Delegating to Claude Code

- **`ship`'s Review step splits in two.** `/code-review` covers correctness — a multi-agent pass
  that scores its own findings for confidence and reports only what survives, which is the
  filtering pass the kit was missing. The `reviewer` agent is rewritten around the one question
  `/code-review` cannot answer: does the diff match the design that was approved for it.
- **`ship`'s Security step names its tools** — `/security-review` first, the `claude-security`
  plugin when a project has it enabled, and an adversarial subagent only as the fallback.
- **`ship` and `test` confirm the change against the running app** with `/verify`, instead of
  treating a green suite as proof.
- **`fix` and `debug` use `/code-review` and `/security-review`** rather than their own review pass.
- **`brainstorming` explores before it proposes**, and generates competing architectures in
  parallel — the approach of Anthropic's `feature-dev` plugin, built on the `Explore` and `Plan`
  agents Claude Code already ships rather than on copies of them.
- Effort levels are now part of the instructions: reviews name the level that matches what is at
  stake instead of inheriting whatever the session had.

### Governance

- **`engine.md` is trimmed to what is genuinely always-on** — communication, working style,
  delegation, and the core rules — and stays under the 10,000-character hook output cap, which the
  validator enforces. The workflow-scoped material moved into the skills that use it.
- The always-on guidance for narration, verbosity, scope, delegation, and self-correction follows
  Anthropic's [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
  guidance, including its warning against stacking extra self-verification on a model that already
  verifies its own work.
- Long autonomous runs point at auto mode instead of describing a hand-rolled equivalent.

### Tooling

- `scripts/validate.sh` is rewritten for the plugin: manifest and version agreement, skill and agent
  frontmatter, dangling `${CLAUDE_PLUGIN_ROOT}` references, the engine size cap, and
  `claude plugin validate --strict` when the CLI is present. It also fails a skill whose body is
  only a pointer at another file.
- `scripts/release.sh` bumps `plugin.json` and `marketplace.json` alongside `VERSION`.

## 0.3.0

The kit targets Claude Code only. Codex support is removed rather than left to rot: it doubled
every surface — two adapter trees, two root instruction files, two description columns per catalog
row, a provider switch through the installer and both validators — while only one of them was
actually used. See [migrations/0.3.0.md](migrations/0.3.0.md) for the manual cleanup an installed
project needs.

### Removed

- The Codex payload: `.agents/skills/`, `.codex/agents/`, `AGENTS.md` and its managed block, and
  the `.codex/hooks.json` template.
- `install.sh --providers`, the `providers:` key in `kit.lock`, and the providers line in
  `install.sh status`.
- `.agent-kit/platforms/`. The provider abstraction had one implementation left; its three
  Claude-specific rules moved into `.agent-kit/engine.md`.

### Changed

- `catalog.tsv` drops the per-provider columns: `claude_desc`/`codex_desc` collapse to `desc`,
  `claude_note`/`codex_note` to `note`, and the Codex-only `sandbox` column is gone.
- `scripts/generate-adapters.py` emits only `.claude/` wrappers; the payload is 22 generated files
  instead of 41.
- Both validators check a single adapter surface. The repository validator additionally asserts
  that no Codex artefact reappears in the payload or in a fresh install.

### Changed — prompts rewritten for the Claude 5 generation

Anthropic's guidance for Claude 5 models is that prompting is mostly subtraction: rules written to
protect against older models' failure modes now cost quality, and repeating an instruction across
several files creates conflicting signals rather than reinforcement. The prompt payload shrinks
from 1671 to 929 lines — 44% — with no capability removed. What survives is mostly a sequence of
steps per command plus the domain facts each step needs, rather than instruction scaffolding.

- Every fact now lives in exactly one file. The design gate was previously restated six times
  across the engine, `ship`, `brainstorming`, `writing-plans`, and `autonomous-mode`; "never merge"
  appeared in seven. The engine owns the shared rules and the workflows stop paraphrasing them.
- Dropped the pseudo-XML guardrails (`<HARD-GATE>`, `<SINGLE-GATE>`, `<SCOPE>`,
  `<NEVER-MOVE-USER-DOCS>`, …), the caps-lock imperatives, and the "this is too simple to need a
  design" anti-pattern essay. The gate itself is unchanged — it is now stated once, plainly.
- Removed the duplicated `LANGUAGE:` preamble from six skills; the engine's communication section
  is the only place it is defined.
- **Removed the `plan-reviewer` role and the `Plan review` step**, along with the spec self-review
  and plan self-review. Claude 5 verifies its own work; instructing it to verify — and especially
  delegating verification to a subagent — produces over-verification without a capability gain.
  Verification of the finished diff still happens: `tester` and `reviewer` are unchanged in spirit,
  and `reviewer` now explicitly reports everything with a confidence level rather than
  self-filtering by severity, which was suppressing real findings.
- `writing-plans` no longer asks for the full implementation code and a five-step
  test-run-implement-run-commit ritual per task. A plan is now the task specification handed over
  up front — goal, constraints, file map, task boundaries with interfaces, and how each is verified.
- The engine gained what the guidance says to add rather than assume: how to write for a user who
  cannot see your thinking, the length of generated files, scope discipline, when a correction is
  worth making, and an explicit cap on subagent delegation (Claude 5 reaches for subagents more
  readily than its predecessors).
- Dropped the per-skill "Key principles" sections, which restated their own body in bullet form,
  and the "create a task per item" preambles, which describe what the harness already does.
- Skill descriptions are now trigger-oriented ("Use when…") rather than descriptive. That is the
  text Claude reads to decide whether a skill is relevant, and a stated trigger measurably beats a
  statement of what the skill is.

### Removed — two commands that duplicated existing steps

- **`/plan-next`** is gone. "Read the roadmap, propose 2–3 next options, stop" was already the
  `Task` step of `ship` and a row in the `/go` menu.
- **`riff` and `feature-ideation` are merged into one `ideate` skill** with a broad scope and a
  feature scope. They were two halves of the same job — 206 lines that each carried a section
  explaining how not to overlap with the other, a section that only existed because they were
  split. `/riff` still exists and now runs `ideate` in its broad scope.

### Fixed

- The PR section names `## Ручные действия` were hardcoded in Russian inside English canonical
  files. The canonical name is now "Manual actions", with translation driven by the project
  language like the rest of the PR.

## 0.2.0

First release as a standalone repository. The kit previously lived inside the project it was
developed in; the behavior is unchanged, the distribution is new.

### Added

- `install.sh` — install, update, status, diff, and uninstall, with `--dry-run`, `--ref`,
  `--from`, `--providers`, and `--force`.
- `.agent-kit/kit.lock` — records the installed version, source ref, and two checksums per file, so
  an update can tell an untouched file from one the project customized.
- `.agent-kit/scripts/kit-update.sh` — in-project update shim; no URL to remember.
- `catalog.tsv` + `scripts/generate-adapters.py` — every provider wrapper is generated from one
  authoring source, and CI fails if the payload drifts from it.
- `scripts/validate.sh` — validates the payload, performs a real install into a scratch repository,
  and asserts the update semantics (idempotent re-run, preserved local edits, untouched user files).
- Clean `templates/` for the user-owned corner: an unbootstrapped manifest, neutral project
  instructions, and root instruction files with the managed-block markers.

### Changed

- Role wrappers now also read the provider platform adapter, and every wrapper body is generated,
  so the four adapter surfaces stay consistent.
- `.claude/settings.json` and `.codex/hooks.json` are treated as shared project files: the installer
  adds its SessionStart hook once and never rewrites them.
- The in-project validator resolves the project root from its own location instead of the caller's
  working directory.
