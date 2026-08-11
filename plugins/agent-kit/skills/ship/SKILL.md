---
name: ship
description: Build one feature end to end — design it against the project's blueprint, build it, verify it against what the entry promises, review it, and open a pull request that can be merged without reading the diff.
argument-hint: "[action key, or what to build]"
disable-model-invocation: true
---

# Ship

One feature: an action from `docs/knowledge/actions.md`, or a small coherent group of actions and
screens, delivered as one pull request.

Some work has no entry and never will — the skeleton that makes an empty project start, a build
step, a dependency bump. Then `entries` is empty, `task` in the run file describes what is being
built, and everything below reads "the entry's lines" as "what that task says done means". Nothing
else changes.

Blueprint already says **what** this feature does and **why**. Your job is **how, in this codebase,
now** — which files, which layer, which existing helper, which seam the tests sit at. Do not
re-decide what blueprint settled, and do not put product decisions into the code that the entry does
not carry.

**One rule governs every question you might want to ask:**

> An expensive fork — the shape of stored data, a contract outside this codebase, a permission
> boundary, money — is asked when someone is present, and becomes a recorded assumption when nobody
> is. Everything else you decide silently, either way.

One more fork is always expensive, whatever it touches: **an entry promises one thing and the code
standing there already does another.** Whichever side you take, you are deciding what this project
treats as true. Take the entry and the feature changes the product; take the code and a test freezes
the contradiction, so the day someone makes the entry come true, the suite calls it a regression.

Which side is right is not yours to settle — but leaving the contradiction unwritten is not an
option either, so **write the test on what the entry promises and mark it unmet**. The mark is the
comment `agent-kit:unmet <entry key>` beside the test: the kit's own constant, which every command
finds in any language, and the key is checked against the knowledge. What keeps such a test off the
red belongs to the project and is recorded once in `project.yml` → `tests.unmet`, whose own comment
says which forms are worth having. Where nothing is recorded there, the line stays uncovered rather
than covered by the code's side, and the run file says so.

That records the dispute instead of resolving it. The proof lives in the repository rather than in a
sentence of a report, the suite stays green, and whoever settles it later finds the test already
written. Then **one line in the run file's `unmet`**: the entry, what the code does instead, and
what it is waiting for. That field is the only route by which a mark reaches a batch's pull request,
because the closing session reads run files and never the code. With `gate: none` the mark and that
line are the whole of your move. With someone present, mark it the same way and ask which side is
wrong: the answer either turns into product work now, or goes to `blueprint` through the pull
request. Rewriting the entry is never yours — `blueprint` owns the prose, so the mark stays until it
does.

**The mark is only ever for code that was there before you** — including code a sibling run put on
the branch you are building from. A test for what this feature itself builds is never marked: that
is the feature failing to be built, and calling it a recorded promise would let any run declare
itself done by marking what it could not make pass.

`gate` in the run file says whether anyone is present. A question whose answers all lead to the same
work is never asked at all. How to put one — with options, not prose — is
`${CLAUDE_PLUGIN_ROOT}/rules/asking.md`.

## Before you start

Run the knowledge check. It is mechanical, takes seconds, and says nothing when there is nothing to
say — bar the standing list of promises the product does not keep, which is a statement, not a
finding, and leaves the exit code alone:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" .
```

Then react to it per `${CLAUDE_PLUGIN_ROOT}/rules/preflight.md`, which every build command shares —
plus the two findings that mean something particular here:

| What it found | What you do |
|---|---|
| promises the product does not keep, on an entry you are about to touch | read that test before you design: it is the shape the promise will take when it is kept, and building over it is how a feature and a marked test end up contradicting each other. On any other entry, ignore the list — it belongs to whoever composes the next batch. It is never a reason to stop, whatever else it says about a missing `tests.unmet` or an entry that no longer exists |
| the entry is already `built` | say so and ask whether this is a change to it |

Then read what this feature is, in **one** call — the project's corner, the entry, every entry it
names, and the library map:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --brief developer.create_offer
```

It pulls sections, never whole files: a real project's `actions.md` runs to tens of thousands of
characters, and opening it to read one of forty entries carries the other thirty-nine through the
whole run — measured, 1.6 KB against 44 KB. And it is one turn rather than five, which is the same
saving again, because a turn costs the entire context a second time.

**Read nothing else yet.** Everything you read is re-read on every remaining step, so a file costs
its size times the steps left. Building from a `task` rather than an entry, there is no key to pass:
read `.agent-kit/project.yml` and `docs/knowledge/stack.md` together, in one message.

The working tree must be clean — a dirty tree is a blocker to report, not to work around. Create
`claude/<slug>` from a freshly pulled default branch, unless the run file already names a branch and
a base.

## The run file

`.agent-kit/runs/<slug>/run.json`, shaped like `${CLAUDE_PLUGIN_ROOT}/templates/run.json`. It is
this run's memory and the handoff to anything that resumes it: create it at Design and update it as
each thing happens, never in a batch at the end. A run outlives its own context — what is not in
that file or in the code did not survive.

**`--run <dir>` means the file is already there**: a batch wrote it, or an earlier session of this
feature did. Read it and continue from its `step` rather than starting over — that is also how a run
comes back after the account limit killed its session. Set `step` as you enter each step, and one of
`done` / `blocked` when you stop, because whatever launched this is watching that field to know you
are finished.

**Its fields are a closed list.** Every reader — the run that resumes this one, the closing
session, `check.py` — knows only the shape in the template, so a key you invent is a key nothing
will ever read. Anything with no field of its own goes in `notes`, in prose: context for whoever
picks this up, a dead end worth not repeating, a suspicion you could not chase. And a field the
whole kit is missing is a finding about the kit — say it in the report, do not mint it here. The
check names run files that carry unknown keys.

Beside it there may be a `run.log` — **the driver's**, not yours. It records when a session started,
stalled, hit a limit or finished, which is the one thing a run cannot record about itself once it
has stopped. Never write to it: everything you would have logged has a field above, and writing it
twice buys nothing but shell calls.

The run directory is working state, not repository content. Add `.agent-kit/runs/` to the project's
`.gitignore` if it is not there yet.

## Handing over

A feature can outlast one session, and it costs more the longer it does: every turn re-sends the
whole context, so a session that grew to 340k over 340 turns spent 70M tokens on re-reading itself.
The driver measures that — a session cannot see its own size — and types one line when it is time to
hand over. **Nothing about this is yours to judge except how.**

Finish the task you are on, to its commit. Then close it in the run file, write `handoff`, and stop.

- **Do not start the next task.** Half a task is the one thing the next session cannot pick up: the
  commit is the boundary that carries its own verification.
- **Do not finish the run to get out of it.** `step: "done"` on an unbuilt feature buys a quiet
  night and delivers nothing; the driver would take it and move on.
- **A run file that cannot stand on its own is not handed over.** Write the note, then run the
  check; what it names is what you put right before you stop, not what you leave for the note.

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --run .agent-kit/runs/<slug>
  ```

`handoff` answers four questions and nothing else, under 2000 characters — its shape is in the
template. Everything you would otherwise write there is already somewhere: the approach, the seams
and the tasks are fields, the code is in the commits, the decisions worth keeping are `assumptions`
and `deviations`. What is nowhere else is **what you tried that did not work** — the code shows the
answer and never the two answers before it — and what you settled silently on the way.

**Coming in on a handoff**: read it, move anything durable into the field that owns it, overwrite
`handoff` with your own when your turn comes, and carry on from `step`. You are continuing a run,
not reviewing one: do not re-read the diff behind you, do not revisit the approach, do not design
anything that is already designed. Design is skipped for exactly this reason when the file carries
an approach and tasks.

## Design

Skip this step when the run file already carries an approach and tasks: whoever wrote them designed
this feature, and redesigning it discards a decision the owner may already have approved.

**When `parent` names another run, read its run file first** — approach, assumptions, deviations.
You are building on its branch, so its code is already under you; what the code cannot tell you is
why. A field it renamed, a library it chose, a constraint it hit are decisions you inherit, not
decisions you get to take again. Read the immediate parent only: the whole chain would cost every
later feature the history of all the earlier ones.

Otherwise read the code the entry touches — including the callers and the stored data of everything
you will alter, because a feature that quietly moves a neighbour's behavior is the most expensive
thing an unattended run can produce. Then settle the approach. Reach for the library map in
`stack.md` before writing anything yourself, and stay inside the stances it records. Name the seams
the tests will sit at: prefer seams the project already has, take the highest one that can still see
the behavior, and keep the count as low as the feature allows.

Put it up as **one screen**: the goal, the approach, a diagram only if the change alters a flow,
what you are taking as given, and what you will settle during the build with the default you expect
to take.

**Wait for a go only if there is an expensive fork in it.** With one, ask it with a recommendation
and wait. With none, say what you are about to do and start — a gate that always waits teaches the
owner to approve without reading. Under `gate: none` you never wait, and the fork becomes an
assumption.

Before asking anything, put the fork's own text in `waiting_on` — that field is how a driver, the
window and `next` know a run is stopped and on what, and it is the only route by which a night's
question reaches a phone. Then when the answer comes, clear it and put the question and the
answer into `answers`, in the owner's own words. A run that
resumes reads that instead of asking a second time, and the pull request quotes it instead of
recalling it.

Design ends when the run file holds the approach, the seams, and a task list in which each task is
the smallest unit that carries its own verification.

## Build

Task by task, one commit each.

**Write the test before the code.** That is the default for every line of the entry, and it is what
makes the proof free: a test written first fails on its own, so nothing has to be run again to
establish that it can.

The one exception is a line whose shape is not decided until the code exists — presentation, mostly.
Asserting on markup you have not chosen yet is not test-first, it is writing the test twice. Write
those after, and **run each one once against the unfixed code**, so the guarantee holds where the
default does not apply.

Record as you go, not at the end. What you found decides where it goes, and every destination has a
reader that acts on it — a finding written anywhere else reaches nobody:

| What you found | Where it goes | Who reads it |
|---|---|---|
| a decision the entry did not settle, cheap to reverse | `assumptions` | the pull request |
| one expensive to reverse — stored data, permissions, money, a public contract | `assumptions` **and** an `[assumed …]` block under the entry | every later run follows it; the check prints it; `blueprint` closes it |
| the entry promises what the code does not | a test marked `agent-kit:unmet`, and a line in `unmet` | the check lists it; the pull request; `sprint` with no theme offers it as a batch |
| you departed from the approach that was approved | `deviations`, with its cause | the pull request, as an assumption the code forced |
| a ready-made answer the library map does not name | a `[found …]` block under `stack.md` | the check prints it; `blueprint` folds it into the map |
| what you built makes the entry's own prose false — it described the world before this feature | a `[stale …]` block under that entry | the check prints it; `blueprint` rewrites the entry and deletes the block, and nothing else may |
| work you understood and decided not to do | a line in `docs/technical_debt.md` — and in `deferred` when a batch delivers this | the check counts it; `sprint` with no theme offers it |
| an item of that ledger you finished | delete its line in the commit that does the work; name it in `closed_debt` | the batch's report, for the count |
| anything with no field of its own | `notes`, in prose | whoever resumes this run, and the closing session |

Two of those have a shape. The assumption block goes under the entry it stood in for, and is the
decision of record for every later run — which is what keeps features consistent with each other:

```markdown
> **[assumed 2026-08-02 · claude/<branch>]** <what the knowledge does not say>. Took: <what you did>.
> Expensive to get wrong — <data model | permissions | money | public contract>.
```

`[found …]` is written the same way under `stack.md`, and is the only route by which the library map
learns anything, since nothing else goes looking on its own. `[stale …]` is written the same way
under the entry whose prose your feature has just made false — what it still says, and what is true
now. Rewriting that prose is never yours, and a block under the entry is read by the next run that
opens it, which a line in a ledger is not.

The ledger is the third file you may write, and it carries its own format and its own rules in its
header: copy `${CLAUDE_PLUGIN_ROOT}/templates/technical_debt.md` to `docs/technical_debt.md` when
the project has none yet, and read it there before writing your first line.

Code, identifiers and commit messages in English; anything the owner reads in the project's
language.

## Verify

1. **Cover the entry.** Every one of its lines — what changes, what the initiator sees, what others
   see, what can go wrong — has a test naming it. A line with no test is not done. A line whose test
   is marked unmet is done **only if the design said so** — the contradiction was there before this
   run and the mark is what it decided. Marking a test this feature was supposed to make pass is not
   a result, it is an unbuilt feature with a label on it. Say how many marked tests the run leaves
   and what each is waiting for; that list is the most useful thing in the pull request.
2. **Run the project's declared suite once**, from `project.yml` → `commands` — whatever it
   declares there: `test`, `lint`, and `types` where the project has one. A type error is a failing
   test. Fix the product; never weaken an assertion for green output.
3. **Start the app** with `project.yml` → `commands.run` **and exercise what changed**, when the
   feature has a surface a person can reach. A
   green suite on an app that does not start is exactly what this catches. Say so when there is no
   such surface. Either way it goes into `suite` beside the test and lint results — what you opened
   and what you saw, or that there was nothing to open. Nobody can tell "checked by hand" from
   "wrote that it was checked" unless the run says which screens it went to.

Fix what fails, then run the suite once more at the end. Record in the run file what ran and what it
returned: the pull request is written from that, not from memory.

Do not run the product's end-to-end scenarios here. They prove the product rather than this feature,
and belong to whatever integrates a batch. When the task **is** a scenario — a run composed from the
scenarios lens — the test carries `agent-kit:scenario <the scenario's heading>` in a comment, which
is how anything afterwards knows that scenario is covered by something other than a reading of the
code.

## Deliver

In this order, because it puts reviewed code in the pull request from its first minute:

1. Commit and push the branch.
2. **Review** — see below. Its verdict and every finding go into the run file's `review` **as they
   come back**, before you fix any of them — one record each, `severity` and `what`, per the
   template; then set `closed` and `how` as you close them. A finding written as a sentence is a
   finding no program can read, and this field is the one thing standing between a run and finishing
   with a major one open.
   Written afterwards from memory it becomes a summary, and a summary is what a batch's pull request
   already has too much of. A critical or major finding left open is not `step: done`.
3. **One round of fixes**, then rerun what the fixes put at risk, plus the suite.
4. Open the pull request per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`. Never merge it.
5. **CI** — `gh pr checks`, or the closest this session has. Fix what is yours: formatting, lint, a
   flake, the workflow's own configuration. A failure that needs the feature's design changed is a
   blocker to report in the pull request. Bound the wait — a pipeline still pending after a
   reasonable window is reported as pending, rather than polled until something kills the session.
6. Set the entry's machine line to `state: building (pr: <n>)`. Besides an assumption block, that is
   the only thing you write into knowledge; `blueprint --check` moves it to `built` once the pull
   request merges.
7. Close the run file: `step: "done"`, `suite`, `pr`, and any blocker. Then have the check read it
   back — it is silent unless the file says something a finished run may not say, and what it names
   is fixed in the work rather than in the field that named it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --run .agent-kit/runs/<slug>
   ```

**`deliver: "branch"` stops you after step 3.** A feature inside a batch pushes reviewed code and
nothing else: the batch opens one pull request over the whole chain, runs CI there, and sets the
entries' machine lines from it. Push, close the run file with `step: "done"` and the branch name,
and stop — do not open a pull request, do not wait for a pipeline that has none, and do not report
as if you had. Everything before Deliver is unchanged, review included.

The run is finished when the pull request exists with CI green or its state reported — or, delivering
a branch, when that branch is pushed with its review done — or when a blocker has been reported and
the branch left in a recoverable state. Close it per
`${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is thin rather than what was done, then the one line
naming what to run next.

## Review

**The `agent-kit:reviewer` agent, whenever the diff touched the product.** Give it the base branch
to diff against, the run file's path, and the entries. It answers what nothing else can — whether
this is the feature that was approved — because it is the only pass that reads the entry.

Look at what you changed before you start it:

```bash
git diff --name-only <base>...HEAD
```

**A run that changed only tests, fixtures, lock files or documentation has no feature to judge**, so
the reviewer is asked to compare a product change that is not there. `fix` has said this since it
was written; it costs about as much as the whole of a one-line run, and audit batches are full of
them. Skip it, write in `review.verdict` that you did and what the diff touched — silence there
reads as a pass that happened. The same line decides the security pass: its triggers are all
product surfaces, so a diff with none of them meets none of them.

**On a trigger: `/security-review`.** Run it when the diff touches authentication or permissions,
parsing of untrusted input, money, files or processes, a data migration, or an outbound call.
Otherwise skip it, and say in the pull request that you did and why.

**Never a third pass over the same diff.** The `code-review` plugin's fan cost 6.7M tokens for two
findings on one feature, against this reviewer's 0.66M for twelve — and Claude Code's own
`/code-review` is stronger than either and can only be started by a person typing it. Neither is
part of this pipeline, and neither is offered from here: where a repository-wide pass belongs is
settled once, in `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, so that a batch and a run do not
answer it differently.

Then **one round of fixes**: everything critical or major, everything that departs from the entry,
and every security finding. Record the rest as deliberately deferred rather than building
scaffolding around it. Send the fix diff back through `agent-kit:reviewer` only when the fixes
changed structure rather than lines.

## What this command does not do

It does not choose the next feature, integrate anything, merge anything, run the product's
scenarios, or decide what becomes of the pull request once it is open — those belong to whatever
launched it. And it never rewrites knowledge prose: blueprint owns that.
