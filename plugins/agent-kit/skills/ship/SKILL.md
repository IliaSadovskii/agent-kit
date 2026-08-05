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
option either, so **write the test on what the entry promises and mark it unmet**. Two things make
the mark, and both are needed:

```python
# agent-kit:unmet author.request_validation_now
@pytest.mark.xfail(strict=True, reason="the entry promises the window closes; it stays open")
def test_the_edit_window_closes_once_the_check_is_asked_for(): ...
```

The comment is the kit's constant, followed by the entry key — it is what every command finds, in
any language, and the key is checked against the knowledge. The rest is whatever keeps the test off
the red here, recorded once in `project.yml` → `tests.unmet` so that runs do not each pick their
own. **Prefer a form that runs the test and expects it to fail** — `xfail(strict=True)`, Jest
`test.failing` — over one that skips it, like Pest `todo`: a skipped test proves nothing today and
stays quiet on the day the product does keep the promise.

That records the dispute instead of resolving it. The proof lives in the repository rather than in a
sentence of a report, the suite stays green, and whoever settles it later finds the test already
written. With `gate: none` that is the whole of your move, plus the contradiction written into
`deviations` with both readings named — that field is where the batch's pull request gets it from.
With someone present, mark it the same way and ask which side is wrong: the answer either turns into
product work now, or goes to `blueprint` through the pull request. Rewriting the entry is never
yours — `blueprint` owns the prose, so the mark stays until it does.

**The mark is only ever for code that was there before you** — including code a sibling run put on
the branch you are building from. A test for what this feature itself builds is never marked: that
is the feature failing to be built, and calling it a recorded promise would let any run declare
itself done by marking what it could not make pass. When the project records no form at all, the
line stays uncovered rather than covered by the code's side, and the run file says so.

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

Then:

| What it found | What you do |
|---|---|
| a slot in scope unsettled, or the entry incomplete | stop, name what is missing, offer `/agent-kit:blueprint` — the owner is here and closes it in a minute |
| promises the product does not keep, on an entry you are about to touch | read that test before you design: it is the shape the promise will take when it is kept, and building over it is how a feature and a marked test end up contradicting each other. On any other entry, ignore the list — it belongs to whoever composes the next batch. It is never a reason to stop, whatever else it says about a missing `tests.unmet` or an entry that no longer exists |
| no `docs/knowledge/` at all | **carry on.** Work from the task as written, with `entries` empty and `task` describing it, and say once that without an entry the tests can only aim at what the task says done means. A project's first command should not be an hour of interview |
| `[assumed …]` blocks on the entries you will touch | with `gate: owner`, show them and offer to close them now — this is the last moment anyone is here; with `gate: none`, follow them as written |
| the entry is already `built` | say so and ask whether this is a change to it |
| nothing | continue without a word about it |

Then read, in one message: `.agent-kit/project.yml`, the entry and the entities it names,
`docs/knowledge/stack.md`. **Read nothing else yet.** Everything you read is re-read on every
remaining step, so a file costs its size times the steps left.

**Pull the entry's own section, do not open the file it lives in.** A real project's `actions.md`
runs to tens of thousands of characters, and opening it to read one of forty entries carries the
other thirty-nine through the whole run:

```bash
awk -v RS='\n### ' '/`key: developer\.create_offer`/{print "### " $0}' docs/knowledge/actions.md
```

Measured on a real project that is one entry out of thirty-five: 1.6 KB against 44 KB. The same
goes for every entity and screen you need — a section each, not the file.

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

Beside it, `run.log` records **when** things happened, which the state file cannot: one line per
event, appended and never read back, so it costs nothing in context.

```bash
printf '%s step=%s event=%s detail=%s\n' "$(date -u +%FT%TZ)" build suite "make test → 1 failed" \
  >> .agent-kit/runs/<slug>/run.log
```

Log a line when a step starts and when a command that matters returns — that is all. What was
assumed, what was asked and answered, what the review found already have fields of their own in the
state file, and writing them twice buys nothing but shell calls. One event per line and nothing
resembling prose: this is what someone reads to find out where a run spent its afternoon, not a
narrative of it.

Both files are working state, not repository content. Add `.agent-kit/runs/` to the project's
`.gitignore` if it is not there yet.

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

Record as you go, not at the end. Cheap decisions go to the run file's `assumptions`. A decision
that is expensive to reverse goes there **and** into `docs/knowledge/`, as a block under the entry
it stood in for:

```markdown
> **[assumed 2026-08-02 · claude/<branch>]** <what the knowledge does not say>. Took: <what you did>.
> Expensive to get wrong — <data model | permissions | money | public contract>.
```

That block is the decision of record for every later run, which is what keeps features consistent
with each other. Anything contradicting the approved approach goes to `deviations` instead, with its
cause — and so does every contradiction you marked unmet, one line in `unmet` as well: the closing
session reads run files and nothing else, so a mark left out of them never reaches the pull request.

When you find a ready-made answer the library map in `stack.md` does not name — a package that
covers what you were about to write — leave a `[found …]` block under that file the same way. It is
the only route by which the map learns anything, since nothing else goes looking on its own.

**Work you decided not to do goes in `docs/technical_debt.md`**, one line, copied from
`${CLAUDE_PLUGIN_ROOT}/templates/technical_debt.md` when the file is not there yet. Not the
decisions — those are `[assumed …]` blocks — and not the promises the product does not keep, which
are marks on tests. This is the leftover: a fix resting on an invariant nothing checks, a review's
minor that belonged to another command, a rename you applied in one place of three. Delivering a
batch, write it into the run file's `deferred` as well: the closing session reads run files, not
your diff. An item recorded nowhere survives in a pull request nobody reopens, which is the same as
forgotten.

**And the way back out: an item you finished, you delete** — the line, in the commit that does the
work, so the diff shows the debt going down beside the code that paid it. Never a ticked box. A
ticked box is a line nobody deletes afterwards, and a ledger of them stops being read within a
month; git holds every line that was ever there, and the pull request holds the reasoning. The run
file names what you closed in `closed_debt`, one line each, which is what lets the batch's report
say the debt went from nine to six rather than leaving the owner to diff a file.

If the work turns out bigger than its line said, the line stays and gains what you learned. Half an
item deleted is worse than an item untouched: the next run reads the shorter list and believes it.

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
   come back**, before you fix any of them, with a severity each; then mark what you closed and how.
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
7. Close the run file: `step: "done"`, `suite`, `pr`, and any blocker.

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

**Always: the `agent-kit:reviewer` agent.** Give it the base branch to diff against, the run file's
path, and the entries. It answers what nothing else can — whether this is the feature that was
approved — because it is the only pass that reads the entry.

**On a trigger: `/security-review`.** Run it when the diff touches authentication or permissions,
parsing of untrusted input, money, files or processes, a data migration, or an outbound call.
Otherwise skip it, and say in the pull request that you did and why.

Never run the `code-review` plugin's fan here: measured on one feature it cost 6.7M tokens for two
findings against the reviewer's 0.66M for twelve. Its place is once over a whole batch, which is not
this command's business. Claude Code's own `/code-review` is stronger than either and can only be
started by a person typing it, so it is not part of this pipeline.

Then **one round of fixes**: everything critical or major, everything that departs from the entry,
and every security finding. Record the rest as deliberately deferred rather than building
scaffolding around it. Send the fix diff back through `agent-kit:reviewer` only when the fixes
changed structure rather than lines.

## What this command does not do

It does not choose the next feature, integrate anything, merge anything, run the product's
scenarios, or decide what becomes of the pull request once it is open — those belong to whatever
launched it. And it never rewrites knowledge prose: blueprint owns that.
