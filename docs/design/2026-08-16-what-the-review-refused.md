# What the review refused

Six proposals came out of reading the kit as an architecture rather than as a set of commands — the
question being where a run of it decides something nobody checks. Each went to an independent pass
over the payload with one instruction: **attack it**, verify the claim it rests on, and name what
breaks.

**All six were refused as written.** Four were refused on a fact the proposal had wrong; two were
refused on a mechanism that already exists and does the same thing better. What shipped in 2.16.0 is
what the refusals left behind, and it is smaller and cheaper than what was proposed.

This page is the record of that, because the refusals are worth more than the proposals: five of
them are the kit catching a change that would have made it worse, and the sixth found a defect
nobody was looking for.

## 1. Freeze the acceptance tests — refused

**Proposed.** An `epic`'s first batch writes an end-to-end test for every scenario inside the
bounds, before any feature exists. They fail. From then on they are only run, never edited.

**Why it was refused.** Three reasons, each sufficient.

- **It blinds the only mechanical check the finish has.** `check.py --state` counts a scenario as
  covered when a comment `agent-kit:scenario <heading>` appears anywhere in the suite. It does not
  run anything. Batch zero would move the count to *10 of 10 covered* in the first hour with nothing
  working — and that number is what the gate reads, what `next` reads at rung 8, what the scenarios
  lens reports and what the finish phase is judged by. This kit has paid for exactly this shape
  before: a check that compared two empty lists and passed for months.
- **A deliberately red test has nowhere to live.** The one mechanism for it is `agent-kit:unmet`,
  and `ship` forbids marking anything the run itself was sent to build — otherwise any run declares
  itself done by marking what it could not make pass. The recommended form is stricter still
  (`xfail(strict=True)`, `test.failing`): it goes red the moment the product keeps the promise, so
  the test **must** be edited exactly when it starts passing. *Expected to fail* and *never edited*
  are incompatible at the level of the runner.
- **"Only the owner may edit it" is a record with no closer, in the one command where the owner does
  not exist.** `epic` waits for nobody by design. A test written by the session with the least
  information in the whole run — one guessing at routes before they exist — would be the hardest
  thing in the repository to correct.

**What shipped instead.** The gate already derives which feature closes which scenario, because it
orders the batches by preconditions. So the test rides with that feature. The join is proved the
hour it becomes provable, the suite stays green, the diff stays under the reviewer, and the count
means what it says.

## 2. Run the acceptance tests after every batch — refused in that shape

**Proposed.** The closing session of every batch runs the product's end-to-end tests.

**Why it was refused.**

- **There was no command to run.** `project.yml` declared `test`, `lint`, `types`, `run`, `mutate`
  and nothing that walks the product. The closing session would have had to guess one out of prose.
- **The driver would kill it.** `--hang` is 30 minutes of transcript silence; a blocking run longer
  than that reads as a stalled session, gets `continue` typed into it, then a restart — and the
  closing session is allowed one, after which the batch is `blocked`.
- **A walk in the tree the children built in proves the wrong thing.** That tree has dependencies
  installed, migrations applied and `.env` filled in. It proves that an application already running
  still runs, which the finish phase already says in as many words. Doing it honestly means a fresh
  worktree, and paying for its install per batch.
- **Nobody may close a red result.** The closing session does not fix, `--advance` is one decision
  and not a supervisor, nothing waits for the owner, and a blocked batch does not stop the run. On an
  MVP most scenarios are red *by construction* until the batch that closes them — which is the best
  available way to teach a run to stop looking at red.

**What shipped instead.** The command is declared (`commands.e2e`), its absence is said at the gate
where the run is priced, and the batch reports which of three states it is in — CI ran them, nothing
can run them, or the command exists and no pipeline runs it. CI is the right home: it survives a
dead session, runs on a clean checkout, and the closing session already waits for it.

## 3. Move the bookkeeping into the program — refused, and it was already there

**Proposed.** `check.py --sync` moves state lines, ticks audit boxes and deletes delivered branches;
the prose instructions shrink to *run --sync*.

**Why it was refused.**

- **The state line has been in the program since 0.41.0.** What is distributed in prose is the right
  to *run* it, and that is deliberate: nothing writes to a project as a side effect of reading it,
  and a preflight that wrote would break the clean-tree rule every build command enforces.
- **A program cannot tick an audit box.** The item is free prose in the project's language; ticking
  it means comparing that sentence to a diff. A check that cannot read its input has to say so, not
  guess — and a ticked box removes the item from every future list for good.
- **Branch deletion is not safe yet, for a reason nobody had noticed.** `close.md` requires the batch
  record to list the branch of *every* child, parked ones included — and a parked child's work is not
  merged. When the batch's pull request merges, every branch in that list reads as delivered. A
  remote-only branch then loses its only copy. The guard cannot be written today: the record holds
  parked children as slugs and delivered branches as branch names, and there is no join between them.

**What shipped instead.** Nothing of the proposal — but the pass found a real defect while checking
it, and that is what shipped: `--sync` was announcing moves it had not made. The branch work is
listed below as blocked on a change to what a batch records.

## 4. Read `run.json` in parts — refused on the number

**Proposed.** Named views over the run file, the way `--brief` reads one entry out of `actions.md`.

**Why it was refused.** Measured on 113 real run files and 355 transcripts: the whole traffic of
`run.json` is 3.9% of a run, and views would take **0.5–0.9%** of it. The premise that the file is
mostly the template's inline documentation is false — no real run file carries a single `_` key.
Writing already costs more than the reads the proposal targeted, and it is already near optimal:
two thirds of writes are point patches.

**What is worth doing instead**, and is not done yet: three prose fields — `review`, `notes`, `task`
— are 51% of all run-file bytes. A ceiling on those would name 80 files of 113 and cut 42% of the
bytes on both sides, twice what views would save, as one finding in a program rather than a norm at
the hottest fork of a run.

## 5. A task must carry its own verification — refused, and replaced by a SHA

**Proposed.** `check.py --run` rejects a task list whose records do not say how each task is proved.

**Why it was refused.** A free-text field saying *how this is proved* is answered with "covered by
unit tests" for nothing. And the moment was wrong: the list is written at Design, and no command
calls the check between Design and Build — judging it at `done` reports a defect to a session that
can no longer act on it, in a pull request written at three in the morning.

**What shipped instead.** `tasks[].commit` — the SHA that closed the task. It either resolves in
this repository or it does not, which is the artefact the cheap path cannot produce; it is asked for
at the handoff, where it is fixed in a minute; and it has a reader besides the check, which is the
reviewer.

## 6. An asynchronous channel for questions — refused, and half of it already existed

**Proposed.** A child writes its question, takes its default, continues; the question is pushed
outside the terminal; an answer landing within N minutes is applied.

**Why it was refused.**

- **It was tried and cut.** `wait <hours> <question>` shipped in 1.4.0 with this exact argument and
  was removed in 2.5.0: every `wait` spent its hours and arrived where the run would have arrived
  without it.
- **"Applied" has no coherent meaning.** An expensive fork is by definition one whose cost is the
  cost of reversing it, and the answer arrives after the commits built on the default. The remaining
  readings — the next feature honours it, or it is merely recorded — are what `[assumed …]` blocks
  and `answers` already do, and under both the deadline distinguishes nothing.
- **The outgoing half already reaches a phone.** The driver types into the owner's window, the
  window turns it into a sentence, the app turns that into a notification. The terminal is needed to
  *answer*, not to hear.

**What shipped instead.** The outgoing half, for the one thing it was silent about:
`assumptions[].expensive` had a writer and no reader anywhere in the kit. The driver now says one
line per child as it closes, with no path back.

## What this leaves open

- **Retiring a branch** needs the batch record to name parked children's branches apart from
  delivered ones. Until then no program can tell the two lists apart, and the operation stays in
  prose with a person's eyes on it.
- **The size of a run file** is where the measured number actually is — `review`, `notes` and `task`
  are half of it.
- **`epic --advance` re-doing the closing session's work** is still open, and the check worth having
  is still the mechanical one named in
  [2026-08-14-where-the-tokens-burn.md](2026-08-14-where-the-tokens-burn.md): a batch whose record,
  `spent` and `pr` are all present is closed, and one missing them is a defect to name.

## The one that generalises

Five of the six proposals were arguments about what the kit *should* check. Each was answered by a
file that already said what happens, and in four cases the proposal's premise was simply wrong about
the current behaviour — written from a reading of the design rather than of the code.

The defect that shipped was found by none of the proposals. It was found by a pass sent to verify
one of them, reading the function the proposal was about.

> An argument about architecture is worth what the reading behind it is worth. Send it to be
> refuted, against the files, and keep what survives.
