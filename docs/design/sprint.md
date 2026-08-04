# Sprint — why it is shaped this way

The behavior will be `plugins/agent-kit/skills/sprint/SKILL.md` and `scripts/orchestrate.py`. This
file holds what neither should carry: the reasons, and what was rejected. Decided 2026-08-04 against
[kit-v1.md](kit-v1.md), [ship.md](ship.md) and [0.17.0-measurements.md](0.17.0-measurements.md),
then rewritten the same day after a review that removed about a third of it — the removals are in
**Rejected**, and they are the more useful half of this document.

A sprint is a batch of features built one after another while nobody watches. `mvp` is the same
engine with a different entrance, so its decisions are settled here too rather than rediscovered.

## The pieces

| | What it is | Talks to the owner |
|---|---|---|
| **Brief** | a session the owner is already sitting in | yes — this is where questions belong |
| **Driver** | `scripts/orchestrate.py`, a loop with no model behind it | never |
| **Child** | one visible `claude` session per feature, running `ship` | only on an expensive fork |
| **Window** | one control session, standing beside the run | on demand, and when poked |

The brief ends before the driver starts. The driver never reads what a child says — it reads run
files. The window decides nothing. There are two layers, not three: the driver leads, the children
build.

**Why no orchestrating agent.** 0.17.0 had one and it was the measured failure: an agent holding the
queue dies of context, pays tokens for bookkeeping a loop does for free, and puts a third headless
level between the owner and the work, which is what made progress unobservable. A loop has no
context to lose and no opinion to have. Its price is that anything unusual becomes an honest
`blocked` rather than a clever recovery.

**Why the children are visible rather than headless.** A visible session can be watched from the
app, typed into when it goes wrong, and can ask a question that reaches the owner's phone by itself.
Headless children were cheaper to launch and could do none of this.

## Who may ask what

Each command asks about the thing only it can see. `ship` sees one feature and asks about it
concretely, at design time. `sprint` sees a batch and asks about composition and order, shallowly.
`mvp` sees the whole product and asks once, at launch, whether the blueprint can define a finish —
then goes quiet for the rest of the run.

## The brief is optional

The brief is a way to produce a sprint's input, not the definition of it. The input **is** the run
file: a list of children, each with an approach and a task list. A person fills it by talking to the
brief; `mvp` fills it directly. Nothing downstream can tell the difference. Building the brief as
the only entrance would mean rewriting sprint when `mvp` arrives.

### What it is worth

Two things, and they are the only two a child cannot supply.

**It sees the batch.** A child knows its own feature. It cannot notice that two features write to
the same table, that the fourth depends on the second rather than the first, or that an audit item
was fixed a month ago.

**The owner is present.** Overnight an expensive fork becomes an assumption, and a wrong assumption
is paid for in code already written. So the brief's real job is to **pre-answer the questions the
night will have nobody to ask.**

### What it does not do

It does not design the features. The old kit spent eight to ten minutes sketching each one, and the
sketch was written by a session that had read less of the code than the child later would. `ship`
already has a Design step that reads the code it touches, puts up one screen, and asks only on an
expensive fork. A brief that designs either duplicates that step or replaces it with a
worse-informed version of itself.

The consequence is deliberate: **the owner sees each feature's design in the pull request, not
before the night.** What they get up front is the forks, not the shape.

### What it reads, in order

Cheapest and most decisive first; it rarely needs the fourth.

1. **`blueprint --check`** — mechanical, silent when clean. It reports an incomplete entry or an
   `[assumed …]` block left by an earlier run. Both turn into invention overnight.
2. **The batch's source** — an audit's work list, a roadmap, or the theme the owner named.
3. **The entries themselves**, a section each rather than the file, plus `stack.md`. This is where
   features touching the same ground become visible, and where an expensive fork is recognisable
   from the entry alone: stored data, an outside contract, a permission boundary, money.
4. **Code, narrowly and only in doubt** — *does this already exist?*, *who else touches these
   files?* The deep read belongs to the child.

### The questions that come out of it

One rule of selection: **ask only when different answers lead to different work and the rework is
expensive.** Answered by the blueprint — not asked. Cheap either way — the child decides.

In practice four kinds, plus one that is not about the work: composition ("the audit lists twelve, I
am taking these five"), order and collisions ("three and five both alter the orders table"), a fork
found early ("the second feature stores something and the entry does not say where — decide it now
or get a migration"), an open assumption from a previous run, and whether the owner is reachable.

Finding none of these is an honest outcome: the brief states the batch and the order, and starts.

An audit's items are the easiest input there is — each already carries file, line and why — so the
brief reduces to composition and order. With no blueprint at all, it works from the owner's words
and the code, and says once that tests can only aim at what the task itself says done means.

## Children run in sequence, in one chain

Sequential, never parallel: a shared VPS and one repository, and parallelism was never the
bottleneck — a night is long.

**Every child branches from the last successful child's tip**, whether or not it depends on it. The
chain is what removes the whole integration problem: the last tip already contains the batch, so
there is nothing to merge together at the end, and each child's suite run happens on code containing
everything before it. Integration stops being a step and becomes a property.

Its cost, stated plainly: unrelated features are entangled, so a feature cannot be dropped out of the
middle — it is amended or reverted by a commit. That is the price of deleting an entire stage, the
drafts, and both merge accidents the old shape caused.

**Code passes by the branch. Decisions pass by the parent's run file.** Code shows what exists, not
why; if the parent renamed a field, chose a library or hit a constraint, the child inherits that
instead of deciding differently. So a child reads its parent's approach, assumptions and deviations
first — ten lines of JSON that are already being written.

**Only the immediate parent is read.** Otherwise the last child of the night carries the whole
history. This is what killed `upstream.md`: a file that grows with the run is a context bill paid by
every step after it.

**A failed child skips its descendants**, and the rest of the list runs in order. The driver does not
re-plan, re-order, or look for the next independent feature — the parent field it already needs for
branching is the whole mechanism.

## A child may ask, and there is no clock

A child asks only on an expensive fork — stored data, a public contract, permission boundaries,
money — the rule `ship` already carries. Everything else it decides silently.

**Someone present: it asks and waits. Nobody present: it takes the assumption immediately.** That is
all. `ship` settled this already — *waiting costs nothing; a session stopped on a question burns no
tokens* — and the first draft of this document contradicted it by adding a thirty-minute clock, a
declared fallback, and a poke from the driver.

Walk the case that machinery was for: the owner said they were reachable and then stepped away, at
their own desk, in daylight. They come back and find the run standing on a question with the
question in front of them. Insuring against that cost four mechanisms, one of them the driver typing
into a working agent. That is exactly the class of spend this rewrite exists to delete.

So the driver never interrupts a child. If a child waits when nobody is present — a misbehaving run —
it stops making progress, and the liveness check below kills it like any other hang.

## Liveness, limits, and picking a run back up

The old answer to "is it still working?" was that the log stopped growing. That is wrong twice over:
a large feature can work silently for half an hour, and a log line is written only when the agent
chooses to write one.

**Liveness comes from the session's own transcript** — `~/.claude/projects/<cwd-slug>/<id>.jsonl`,
which grows on every message and every tool call whether the agent cooperates or not. Its
modification time is the heartbeat. Because children are sequential, the driver identifies a child's
transcript as the one that appeared in that directory after it launched the session.

**A limit is a structured record, not prose.** The account limit puts a line in that same file
carrying `"isApiErrorMessage":true,"apiErrorStatus":429` and a text like `You've hit your session
limit · resets 2:20am (Asia/Tbilisi)`. The reset time comes with it, so the driver sleeps until the
stated moment rather than guessing. `529` is the overloaded case — a short retry, not a wait. A
reset more than a few hours out is a weekly limit: stop the run and say so, do not sleep through a
day.

**Coming back is a ladder, cheapest first.** A limit does not kill the process: the session is alive
and its whole conversation is in memory.

1. **Process alive** — after the reset, type one line into the pane. The child continues with its
   context intact and re-reads nothing. This is the normal case.
2. **Process dead** — raise a session that resumes the old one; the conversation comes back from the
   transcript.
3. **Resume failed** — a fresh session runs `ship` again; it reads the run file and continues from
   the recorded step. Costs a re-orientation, always works.

Typing into a pane was rejected above as a way to interrupt a child and is accepted here, because the
conditions are opposite: a known-idle session at a known moment, not a working agent mid-step.

**Judge by the world, not by the exit.** A limit hit at the tail of a feature looks exactly like a
crash while the work is already done — this cost us a feature in the July run. Before calling a
feature failed, the driver checks whether the branch and the pull request actually exist.

So the driver's whole vocabulary is: the run file, a transcript's modification time, one error code,
`git`, and `gh`.

## The control window

One session raised beside the run, for the owner to talk to. It **decides nothing**, and the run does
not depend on it: kill it and the driver carries on. That invariant is what keeps it from becoming
0.17.0's orchestrator, which *led* the run and died of it.

It does three things.

**Answers when asked.** It reads run files and the tail of the log and says where the run is. The
value is the synthesis: children are individually visible in the app, but the finished ones are gone
and the whole picture exists nowhere else. It does not read children's transcripts — that is how it
would eat its own context.

**Speaks when poked.** The driver decides an event is worth words — a limit, a parked feature, a
finished batch — and types one line into the window. The window turns it into a sentence, and the app
turns that into a notification on the owner's phone. When the driver is silent, so is the window.

**Relays three instructions back.** This is the reader that a feedback channel needs: the driver runs
for the whole night, so it can be told things. The window writes the owner's instruction to a file
and the driver picks it up **at the boundary between features**, never mid-feature:

- **pause** — finish this feature and stop;
- **skip** — do not build that feature, carry on;
- **stop** — wind up, deliver what exists.

Its context grows only when the owner asks something, a little at a time. If it ever fills, it dies
without consequence and is raised again.

## Delivery

**No per-feature pull requests, no drafts, no integration branch.** Every child pushes its branch and
stops there; one pull request is opened for the run, based on the default branch. The old shape cost
two live merge accidents — children merged into their parent, nothing reaching `main` — plus a review
plugin that refuses drafts, and it bought a per-feature reading surface the owner never used, because
they merge the batch.

**A single feature can still be seen alone.** Its branch is pushed and its base is known, so its own
pull request is one command away, on the day it is wanted. The report prints that command per
feature. The capability stays; the machinery goes.

A last session — not the driver, because writing a pull request is judgement — opens or updates the
pull request and writes the report.

### What the pull request says

`rules/pull-requests.md` already fixes the sections and the goal: decide in the first five lines
whether this is mergeable without reading the diff. A batch fills the same sections, composed across
its features, and is **organised by what could have gone wrong, not by what was done**. With the
entries written in advance, a batch can only have gone wrong in three places, and all three stay
uncollapsed at the top:

- **What did not happen** — features parked and why. A hole in a batch is more dangerous than any
  line of code in it.
- **Manual actions** — merged across features into one ordered list. Three migrations are three
  numbered steps, not three sections the owner assembles in their head.
- **Assumptions** — one table for the batch: decision, why, which feature, which entry. Expensive
  first. This is the single place a well-specified batch diverges from what the owner wanted.

Then **Proven** — a row per feature naming which of the entry's lines have a test, what the suite
returned, and what is *not* proven, plus the batch-level fact that end-to-end scenarios were not run
here. **Review** and **Changes** collapse as usual.

Per feature, a collapsed block of about eight lines: what it does now in product terms, the approach
in one sentence — that line is where "you put it in the wrong layer" is visible in a second — where
the tests aim, its branch, and the command to open it as its own pull request.

## `mvp`

`mvp` composes batches and owns no build, test or pull-request logic — it calls `sprint`, which calls
`ship`. Everything above holds; four things are its own.

**One gate, at launch, and it is the heaviest of the three.** The moment `mvp` is started the owner
is present, and that is its only opportunity. A sprint with a thin blueprint still delivers five
features; an `mvp` with a thin blueprint has no stopping condition. The gate checks `blueprint
--check` over the slots it needs; that the MVP bounds are two real lists ("and so on" is not a
bound); that the scenarios cover the in-list — arithmetic, because scenario steps name action keys,
so an action in no scenario and a scenario naming an action nobody wrote both fall out; that the
in-list's entries are complete enough to aim tests at; any open assumptions, this being the last
chance to close them; and that `stack.md` says how to start the application and run its suite,
without which the finish line cannot be walked. It ends on one screen, with the finish line said back
in words. **Missing bounds or missing scenarios stop the run**; anything smaller becomes an
assumption rather than costing a whole run.

**The finish line is three things, in this order.** The in-list is built. Then `audit` runs over the
lenses declared at the gate, its findings are fixed, and the remainder is reported. Then the
scenarios pass against the running application. Audit before scenarios because audit finds the holes
and the scenarios judge the final state.

This is what closes the old open question of how `mvp` knows it is finished, and it closes the loop
the kit already claims — know, build, check, build — which until now stopped at *build*.

Three limits keep the audit from becoming a second MVP. **Not every lens**: tests, scenarios and
dependencies always; security when the product has users, permissions or money; performance is
premature at this stage and conventions are optional. **One wave, not a cycle**: audit, then sprints
over its findings, then done — a later audit may report but does not start another round. **One
sprint per lens**, because the audit already groups its findings into units of work and a batch
should be about one thing. The fixes go into the same chain and the same pull request.

A standalone sprint gets no audit: a batch of five features is small enough for the owner to read,
and the sweep would cost more than the batch.

**One pull request for the whole run, opened at the start and grown.** Batches append commits to the
`mvp` branch; each batch's closing session rewrites the summary and adds a comment with that batch's
digest. The owner reads one place, sees what is new since they last looked, and merges once. The
owner merges — `mvp` does not, and the reason autonomous merging was proposed (a pile of pull
requests nobody would read) no longer exists once there is one.

**Notification without a checkpoint.** After each batch the owner is told what now works and what was
decided without them. Nobody waits for an answer and no mechanism picks one up. `mvp` does not stop
between batches: that would put back in the middle exactly the waiting this design removes, and the
control window already exists for steering a live run.

## Rejected

From the first draft of this design, in the review that produced this version:

- **A thirty-minute clock on an unanswered question**, with a declared fallback and the driver typing
  into a working child. It contradicted a settled rule and insured against the owner walking away
  from their own desk.
- **Per-feature pull requests, drafts, and parking them.** Two live merge accidents, one review
  plugin that refuses drafts, and a reading surface the owner does not use.
- **The integration branch and its own suite run.** The chain integrates continuously; the last
  child's suite run already covers the batch.
- **Finding the next independent feature after a failure.** Replaced by skipping the failed child's
  descendants.
- **Reading code as a step of the brief.** Audit items carry their own evidence and `blueprint
  --check` already reports what is built.
- **Mid-run checkpoints where `mvp` waits for the owner**, and **pull request comments as the
  feedback channel** — a channel with no reader, since every session that could have read it has
  closed. The control window replaced both.

From earlier:

- **An agent orchestrator** (0.17.0): dies of context, pays tokens for bookkeeping, hides progress.
- **A watchdog above it**: a third headless level, and the reason the July run stopped.
- **Headless children**: cheaper to launch, but invisible, unaskable, impossible to rescue by hand.
- **`queue.yml` + `handoff.yml` + `upstream.md`**: three files saying what `children` and the
  children's own run files already say.
- **Timers anywhere except the limit ladder**: a run that is working is left alone, however long it
  takes.

## Still open

Both of the questions this section carried are closed. The launcher uses `claude-new` when it is on
the PATH and plain tmux otherwise, so the server's helper is an optimisation rather than a
dependency; `rules/pull-requests.md` now describes batches instead of stacked features.

What is left is not a design question but the only thing that settles one: **none of this has run.**
`ship` has never run either, so the first sprint's first child is `ship`'s first live run, and it
should be watched by hand rather than started at midnight. Measure it with `scripts/measure.py`,
check a sample of what it claims, and expect the corrections to be about the seams between the
pieces — a child that does not close its run file, a launcher that races its own session — rather
than about the shape above.

The driver's own tests cover what it decides: they already found an unbounded wait on a closing
session that never returns, and a dead session waited out as though it were merely quiet. What they
cannot cover is a real `claude` session on the other side of the launcher.
