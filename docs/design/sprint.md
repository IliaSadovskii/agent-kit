# Sprint — why it is shaped this way

The behavior will be `plugins/agent-kit/skills/sprint/SKILL.md` and `scripts/orchestrate.py`. This
file holds what neither should carry: the reasons, and what was rejected. Decided 2026-08-04,
against [kit-v1.md](kit-v1.md), [ship.md](ship.md) and the numbers in
[0.17.0-measurements.md](0.17.0-measurements.md).

## Three roles, and none of them is an orchestrating agent

A sprint is a batch of features built one after another. Three things happen, and keeping them
apart is the whole design:

| | Who | Talks to the owner |
|---|---|---|
| **Brief** | a session the owner is already sitting in | yes — this is the only place |
| **Driver** | `scripts/orchestrate.py`, a loop with no model behind it | never |
| **Child** | one `claude` session per feature, visible in the app | only on an expensive fork |

The brief ends before the driver starts. The driver does not raise an orchestrating session and
does not read what the children say — it reads their run files. A child is a normal `ship` run.

**Why no orchestrating agent.** 0.17.0 had one and it was the measured failure: an agent holding
the queue dies of context, costs tokens to do bookkeeping a loop does for free, and puts a third
headless level between the owner and the work, which is what made progress unobservable. A loop has
no context to lose and no opinion to have. Its price is that anything unusual becomes an honest
`blocked` rather than a clever recovery, and that price is acceptable.

**Why the children are visible rather than headless.** A visible session can be watched from the
app, can be typed into when it goes wrong, and can ask a question that reaches the owner's phone by
itself — no relay through an orchestrator that lacks the context to explain the fork. Headless
children were cheaper to launch and could do none of this.

## The brief is optional, and only some commands may ask

Each command asks about the thing only it can see. `ship` sees one feature and asks about it
concretely, at design time. `sprint` sees a batch and asks about composition and order, shallowly.
`mvp` sees the whole product and asks once, at launch, whether the blueprint can define a finish —
then goes quiet for the rest of the run.

So the brief is a way to produce a sprint's input, not the definition of it. The input **is** the
run file: a list of children, each with an approach and a task list. A person can fill it by talking
to the brief; `mvp` fills it directly. Nothing downstream can tell the difference. This is the same
shape `ship` already uses — whoever wrote the design is the designer, and the run file says whether
anyone was present.

Building the brief as the only entrance would mean rewriting sprint when `mvp` arrives.

### What the brief is worth

Two things, and they are the only two a child cannot supply.

**It sees the batch.** A child knows its own feature. It cannot notice that two features write to the
same table, that the fourth depends on the second rather than the first, or that an audit item was
fixed a month ago. That is visible only from above, and only before the run starts.

**The owner is present.** Overnight an expensive fork becomes an assumption, and a wrong assumption
is paid for in code already written. So the brief's real job is to **pre-answer the questions the
night will have nobody to ask.**

### What the brief does not do

It does not design the features. The old kit spent eight to ten minutes sketching each one, and the
sketch was written by a session that had read less of the code than the child later would. `ship`
already has a Design step that reads the code it touches, puts up one screen, and asks only on an
expensive fork.

A brief that designs either duplicates that step or replaces it with a worse-informed version of
itself. The consequence is deliberate and worth stating plainly: **the owner sees each feature's
design in its pull request, not before the night.** What they get up front is the forks, not the
shape.

### What it reads, in order

Cheapest and most decisive first. It rarely needs to go past the third.

1. **`blueprint --check`** — mechanical, silent when clean. It reports an incomplete entry, or an
   `[assumed …]` block left by an earlier run. Both turn into invention overnight.
2. **The batch's source** — an audit's work list, a roadmap, or the theme the owner named.
3. **The entries themselves**, a section each rather than the file, plus `stack.md`. This is where
   features touching the same ground become visible, and where an expensive fork is recognisable from
   the entry alone — stored data, an outside contract, a permission boundary, money.
4. **Code, narrowly.** Two questions only: *does this already exist?* and *who else touches these
   files?* A search or two per feature. The deep read belongs to the child.

### The questions that come out of it

One rule of selection: **ask only when different answers lead to different work and the rework is
expensive.** Answered by the blueprint — not asked. Cheap either way — the child decides.

In practice four kinds, plus one that is not about the work:

- **Composition** — "the audit lists twelve, I am taking these five; they are one topic and do not
  collide."
- **Order and collisions** — "three and five both alter the orders table, so five goes after three
  and branches from it."
- **A fork found early** — "the second feature stores something and the entry does not say where. I
  will decide it overnight and you will get a migration. Decide it now?"
- **An open assumption** — "an earlier run assumed this under that entry; this is the last moment to
  close it."
- **Whether the owner is reachable**, which sets the one timer.

Finding none of these is an honest outcome. Then the brief states the batch and the order and starts.

### When there is no blueprint, and when the source is an audit

An audit's items are the easiest input there is: each already carries its evidence — file, line, why
it is a defect — so there is nothing to invent and the brief is reduced to composition and order.

With no blueprint at all, the brief works from the owner's words and the code, and says once that
tests can only aim at what the task itself says done means. That is the rule `ship` already carries;
sprint does not vary it.

## Children run in sequence, and inherit two things

Sequential, never parallel: a shared VPS and one repository, and parallel children were never the
bottleneck — a night is long.

**Code passes by the branch.** A dependent feature branches from its parent's branch rather than
from the default branch. That is most of the transfer: everything the parent built is simply there.

**Decisions pass by the parent's run file.** Code shows what exists, not why. If the parent renamed
a field, chose a library, or hit a constraint, the child must inherit that instead of deciding it
differently. So a child with a parent reads the parent's run file first — its approach, assumptions
and deviations. Ten lines of JSON that are already being written; no new file and no new format.

**Only the immediate parent is read.** Otherwise the last child of the night carries the whole
history. This is the same reasoning that killed `upstream.md`: a file that grows with the run is a
context bill paid by every step after it.

Independent children inherit nothing, because they need nothing.

## A child may ask, and silence has a deadline

A child asks only on an expensive fork — stored data, a public contract, permission boundaries,
money — the rule `ship` already carries. Everything else it decides silently.

When it asks, it writes two things into its run file: **the question**, and **what it will do if no
answer comes** — either a named assumption, or "this cannot continue without an answer". The
decision belongs to whoever can see the fork; the driver is not asked to understand it.

The driver sees a run file waiting and starts a clock:

- an answer arrives — the child clears the wait and carries on;
- the clock runs out — the driver types one line into the session: *no answer, take your fallback.*
  A waiting agent runs no timer of its own, so somebody has to poke it, and that is all the poking
  the driver ever does.

Then the child's own fallback decides: build on with a recorded assumption, or stop. A stopped
feature is parked and the driver moves to the next independent one. If nothing independent is left,
the sprint stops and waits for the owner, with a notification.

**The clock is one number, set by the brief.** Reachable: thirty minutes. Nobody present: zero — the
fallback is taken immediately, and a night is not spent waiting for an answer that cannot come.

This is the one timer in the design. It exists because the alternative is a lost night, and its cost
is a single configurable number.

## Liveness, limits, and picking a run back up

The old answer to "is it still working?" was that the log stopped growing. That is wrong: a large
feature can work silently for half an hour, and a log line is written only when the agent chooses to
write one.

**Liveness comes from the session's own transcript** — `~/.claude/projects/<cwd-slug>/<id>.jsonl`,
which grows on every message and every tool call whether or not the agent cooperates. Its
modification time is the heartbeat. Because children are sequential, the driver identifies a child's
transcript as the one that appeared in that directory after it launched the session.

**A limit is a structured record, not prose.** When the account limit is hit, that same file gets a
line carrying `"isApiErrorMessage":true,"apiErrorStatus":429` and a text like
`You've hit your session limit · resets 2:20am (Asia/Tbilisi)`. So the driver sleeps until the
stated reset rather than guessing an interval, then raises the session again and resumes the same
child. `529` is the overloaded case — a short retry, not a wait.

**Resuming needs nothing new.** A child writes its state after each step, so a fresh session opens
the run file and continues from the step recorded there. This is the first thing to test on the
first live run: kill a child mid-feature and see it come back.

**Judge by the world, not by the exit.** A limit hit at the tail of a feature looks exactly like a
crash while the work is already done — this cost us a feature in the July run. Before calling a
feature failed, the driver checks whether the pull request actually exists.

So the driver's whole vocabulary is: the run file's state, the transcript's modification time, one
error code, and `gh pr list`.

## How a sprint ends

Every child is terminal — a pull request, or parked with a reason. Then integration: a branch from a
freshly pulled default branch, the children's tips merged into it, the suite run **once** there, and
one pull request for the batch. Feature pull requests exist for reading and review; the integration
one is what the owner merges.

End-to-end scenarios are not run here. They belong to `mvp`'s finish line, against a running
application — running them per batch pays for the whole product on every sprint.

The report is per feature: status, pull request, and the assumptions actually taken. Those
assumptions are where the questions the owner never got asked come back to them, in one place.

## What `mvp` needs from this, and why it is decided now

`mvp` composes batches and owns no build, test or pull-request logic — it calls `sprint`, which
calls `ship`. Three consequences, all cheap now and expensive later:

1. **The brief must be skippable**, because `mvp` composes its batches itself and there is nobody to
   brief with between them. Hence the input being a run file rather than a conversation.
2. **A sprint's result must be readable by a program** — built, parked, assumed — because `mvp`
   composes the next batch from it. The run file already is that.
3. **A sprint does not judge whether the product is done.** It finishes its batch. Whether the MVP is
   finished is measured against the blueprint's in-list and its scenarios, and that is `mvp`'s
   question.

### `mvp` has one gate, at launch, and it is the heaviest of the three

Recorded here so it is not rediscovered later; the full design goes in `mvp.md` when it is built.

The moment `mvp` is started, the owner is present — they typed the command. That is its only
opportunity, and it is not a courtesy. A sprint with a thin blueprint still delivers five features.
An `mvp` with a thin blueprint **has no stopping condition**: its finish is the in-list plus the
scenarios passing against a running application, so vague inputs mean it either stops early or never
stops at all.

The gate checks: `blueprint --check` across the slots it needs; that the MVP bounds are two real
lists ("and so on" is not a bound); that the scenarios cover the in-list — checkable by arithmetic,
since scenario steps name action keys, so an action in no scenario and a scenario naming an action
nobody wrote both fall out; that the in-list's entries are complete enough to aim tests at; any open
assumptions and open questions, this being the last chance to close them; and that `stack.md`
actually says how to start the application and run its suite, because without that the finish line
cannot be walked.

It ends on one screen, and the finish line is stated back in words — *"I stop when these fourteen
actions are built and these six scenarios pass against the running app."*

**Missing bounds or missing scenarios stop the run**; those are precisely what `mvp` cannot work
without. Anything smaller — a field, a stack detail — is taken as an assumption rather than costing a
whole run.

**No gate between batches.** Showing progress and asking "continue?" puts the waiting back in the
middle, which is what the design exists to remove. The checkpoint already exists: each batch has its
own integration pull request, and not merging it is how the owner stops. Children inside an `mvp`
can still ask — the same clock — because a child sees forks `mvp` could not foresee.

## Rejected

- **An agent orchestrator** (0.17.0): dies of context, pays tokens for bookkeeping, hides progress.
- **A watchdog above the orchestrator**: a third headless level, and the reason the July run stopped.
- **Children as headless `claude -p` runs**: cheaper to launch, but invisible, unaskable, and
  impossible to rescue by hand.
- **`queue.yml` + `handoff.yml` + `upstream.md`**: three files to say what `children` and the
  children's own run files already say. State lost between them is what this rewrite exists to fix.
- **A dependency graph with parking and re-planning**: the driver parks a feature and moves on; it
  does not re-order the batch. Anything cleverer is machinery for a case that has not happened yet.
- **Timers anywhere except the unanswered question**: a run that is working is left alone, however
  long it takes.

## Still open

- **Where the launcher lives.** On this server a visible session is `claude-new <name> <dir>` and the
  command typed into it; the kit cannot depend on that. The contract the driver needs is small — a
  session whose transcript is discoverable and which can be typed into — so this is one configurable
  line rather than a design question. Settle it while writing the script.
- **Whether the integration step is the driver's or a final child's.** Merging tips and running the
  suite is judgement the driver does not have, so it is probably a last session; that costs one more
  session per sprint and is decided on the first run.
