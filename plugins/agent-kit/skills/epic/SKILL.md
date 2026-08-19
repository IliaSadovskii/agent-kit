---
name: epic
description: From the blueprint to a running prototype — build a whole scope autonomously, audit it, and prove it, delivered as one pull request. The MVP bounds the first time; run again once they are built and it offers what is still planned or still owed.
argument-hint: "[--advance <run dir> | --resume <run dir>]"
disable-model-invocation: true
---

# Epic

A whole scope — built, audited and proved, as one pull request the owner can open and click through.
`sprint` is a batch of about five features; this is the whole of what is left, in batches. The MVP
bounds are the scope it takes when nothing is said; run it again after those are built and it offers
what is still planned, or what the project owes.

**It owns no build, test or pull-request logic.** It composes batches and hands each to the driver;
the driver runs `ship` per feature and the closing session per batch. Everything those already do
holds unchanged. What is this command's own is three things: the gate, the order of the phases, and
knowing when it is finished.

| Invocation | You are |
|---|---|
| `/agent-kit:epic` | the gate — the one conversation this run has. Then start the first batch and stop. Run again once the bounds are built and it offers what is left instead: see *Derive the in-list* |
| `/agent-kit:epic --advance <run dir>` | started by the driver when a batch finished: decide what follows, start it, stop |
| `/agent-kit:epic --resume <run dir>` | the run stalled and nobody restarted it. Work out where it is and carry on — see *Coming back* |

Each of these **ends**. Nothing sits watching for hours: between phases the driver runs, and a phase
that is waiting is a phase that has already lost the night to an account limit.

## The gate

The only moment an owner is present, and its whole job is to make the finish line real. A sprint
with a thin blueprint still delivers five features; an epic with a thin blueprint has no stopping
condition at all.

**Check `tmux` is installed before anything else** — `command -v tmux`. Without it the driver cannot
give a feature its own session, and an epic is nothing but batches of those. Say so now rather than
after the owner has answered a screen about a run that cannot start.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --epic
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --state
```

The first is fatal or silent: no MVP bounds, no scenarios, or no `commands.run` / `commands.test`
and this run does not start — say what is missing and offer `/agent-kit:blueprint`. The second is
the usual preflight, per `${CLAUDE_PLUGIN_ROOT}/rules/preflight.md`. It gives you counts and entry
names; the blocks themselves are read once the in-list exists, below, because until then you do not
know which entries this run is about.

**`--state` is here for two lines of its output.** The first is the most consequential fact the gate
can learn: *scenarios: N described, M with an end-to-end test*. That number decides how this run ends,
and until now nothing read it before the finish phase — which is the worst possible moment, because
a harness is infrastructure that shapes how features get built and by then they are built. On a
project where **M is zero**, no harness exists yet, and the run is heading for a finish it cannot
reach mechanically. Say so at the gate, in the finish line below.

The second is the `tests:` line. When it says nothing measures whether this project's tests can fail,
that goes on the screen beside the price as a fact about what the run can promise — every feature
will report the mutant step as not run, so *green* will mean the word of whoever wrote the tests, all
night. Only `blueprint` can answer it, and the offer is one line: before this run, or not at all.

**Derive the in-list, from the scope this run is for.** Typed with nothing, the scope is the MVP
bounds — which is what this command is named after and what it is for the first time. **Once nothing
inside the bounds is left to build, that is not an error and not a finished conversation**: the same
machinery runs any list, and the gate says so rather than stopping. Offer, with the count of each:

| scope | the in-list | and its finish line |
|---|---|---|
| the MVP bounds | entries inside them not yet `built` | every scenario inside the bounds passes against the running application |
| what is planned | every entry still `state: planned` | all of them built, the lenses quiet, and no scenario test that passed before has gone red |
| what is owed | the debt, the audits' open items, the promises the product does not keep | the list empty, or what is left named one by one |
| a list the owner names | what they name | as for *planned* |

The finish line changes with the scope and is not negotiable afterwards, because the gate's whole
job is to make it real. *Planned* has no scenarios of its own to prove — the ones that exist were
proved by the run that built them — so what it must not do is break them, and that is what its
finish says.

The bounds are written in the owner's own prose — *"registration and sign-in, email confirmation,
the composer, moderation with a fallback"* — not as entry keys. Read the bounds section and the
entry headings, and map one to the other. For every scope, take only what is not already `built`.

**Then write down what this run changes, which is more than what it builds.** The in-list is the
entries with no code yet; beside it stands every **built** entry this scope moves — a debt line that
rewrites a button's behaviour, an owner's remark that changes a prompt, a field that stops meaning
what it meant. Those are the entries a run touches without creating, and they are where the answers
already taken without an owner are sitting. Take both lists to the program:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --entries <every key, built and planned alike>
```

It prints every open block under them in full, and names any key that matched no entry — so a key
you derived wrongly from prose comes back as a mistake instead of as silence. **Settle them on the
screen below**, per `${CLAUDE_PLUGIN_ROOT}/rules/preflight.md`: transcribe the answer into the entry,
delete the block, commit it as `docs(knowledge):` before the first batch starts.

This is the one thing at this gate that cannot be done later at any price, and a live run skipped it
by reading *the entries you are about to build* as *the entries with no code yet*: fifty-one
decisions taken without an owner stayed shut in twenty-one built entries while the owner sat there
answering other questions. The list of what is being built is not the list of what is being changed.

**Order it.** Scenario steps name action keys and entries carry their preconditions, so the order is
derived, not chosen: what must exist before what. Group the result into batches of about five, each
batch one topic, and put the batch that makes a whole scenario walkable first — that is what the
owner can click after the first few hours.

**And that same ordering says who writes each scenario's test.** The feature that closes a
scenario's last step is the one that writes its end-to-end test, marked
`agent-kit:scenario <the scenario's heading>`, and its `task` says so. Nothing else in this run is
allowed to leave a scenario for later: a test written at the finish is written by a session reading
the code it is meant to judge, which is the one way this run can quietly move its own goalposts.
Written with the feature, the join is proved the hour it becomes provable, the suite stays green
throughout, and the diff is under the reviewer like any other. A scenario whose last step falls
outside this scope keeps no test and is named as such on the screen.

**Do not choose the lenses.** They are chosen later, by the `--advance` that reaches the audit,
which has seen the product built and can say what it is made of — where a gate can only guess from
prose. What the gate settles is the ceiling: **three waves**, and that number is what makes the run
terminate, so it is not raised later by anything.

**Price it, in hours.** Not in tokens and not in money: an owner cannot forecast either, and a
number they cannot use is a number that gets approved without being read. Hours they can.

Take the rate from what this project has already measured — `docs/runs/*.json`, `spent`, written by
every batch that has closed here — and say which runs it came from. With none yet, the measured
figure elsewhere is **about an hour per feature end to end**, so twenty-one entries is a day and a
night; say that it is a figure from another project until this one has its own.

**The rate is a rate for features, and content is not a feature.** An entry that says *the reference
holds the grammar rules* is one line of description and an unbounded amount of writing — cards,
seed data, a table of copy, a migration full of text somebody composes by hand. Before the screen,
find the actual count: the list it comes from, the number of items, whether it exists anywhere
already. One entry of that kind grew from one work item to seven while the owner was mid-conversation,
because nobody counted first. Two things go on the screen beside it, and neither can be added later:
the count, and that **no test will say the content is right** — a test says the card exists, and only
a person says it is true.

**And price the audit separately, because it is not small.** Measured on one real `epic`: the lenses
and the batches that fixed what they found came to as much as building the product did. It is a
choice, so it goes in the screen as one — two waves against one, with what each costs.

**Say what will prove it.** Whatever this scope's finish line is, something has to run it. Name it from `stack.md` and from the count
above: the harness that exists, or — when nothing claims a scenario yet — that there is none, what
building one would cost as a batch of its own, and that without it the finish is the owner's hands
on a phone rather than a green suite. **Never leave that to be discovered later.** It is one line
here and a rebuilt plan later, and the owner is standing right there.

**Say how much of the description the owner has actually seen.** The check counts it — *Parts: 6
recorded, 4 walked with the owner, 2 derived* — and you say it as a fact on the screen. You cannot
measure whether a description is detailed enough; there is no such signal, and claiming it would be
the most expensive sentence here. You can say what nobody has read, and on a measured run that was
the whole failure: the scenarios were written in the same session as the gate, nobody walked them,
and six of their endings contradicted the product by the finish.

**When it says no parts are recorded, that is the fact to say**, not a thing to skip: the
description was written before the kit asked who had walked what, so nobody can tell which of it
the owner ever saw. Put it on the screen in one line beside the price, and offer
`/agent-kit:blueprint` as the way to close it — after this run, not before, unless they want it now.

**Except where this run stands on one.** A part nobody walked that the scope merely mentions waits;
a part the scope **builds on** does not — an unconfirmed map of topics is a guess that every entry
hanging off it inherits. Walk that one part now, here, with the owner, and record it walked. It is
minutes, and the alternative is a batch built on prose derived from code that nobody ever confirmed.

**And a thing the conversation invents gets written down before the run starts.** An owner answering
a fork will describe something the description does not have — on a measured run, a table of
translations shared across everyone, which was neither an entity nor an entry anywhere. Recorded as
an assumption it builds fine and is reviewed against nothing: `${CLAUDE_PLUGIN_ROOT}/agents/reviewer.md`
holds a diff against the entry it was built from, and the finish line counts scenarios, so a feature
with no entry is outside both. So write the record — the owner is here, and their answer is the
material — in the same `docs(knowledge):` commit as the settled blocks. If it will not fit in a few
minutes, it does not enter the scope; it becomes a named `planned` entry and the next run builds it.

**Then spend your questions where being wrong is expensive.** Not evenly across the list: rank the
entries you are about to build by what they touch — stored data first, then permissions, money, a
contract outside this codebase — and put the top few up as choices. Measured, an entry's decisions
scale with how much it changes and not at all with how thinly it is written, so this is the one
ranking with evidence behind it. Typically five entries of twenty, and the rest you decide and
record as you go.

**The open blocks are ranked the same way and by the same rule**, because there can be fifty of them
and there is one screen. What a run took without an owner and cannot take back — where data is
stored, who may see it, what it costs, what an outside party was promised — goes up as choices. The
rest keep standing as written, which is what makes features consistent with each other, and the pull
request names them. What may never happen is the third thing: leaving a block unread because it sat
under an entry that already has code.

Then **one screen**: the scope and its finish line said back in words — including what proves it —
the batches in order, the price in hours, what the audit adds, what has never been read, and *this
scope, or narrower?* Options with counts, per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`, and the
expensive entries and the expensive blocks beside it — one round, a handful of taps. This is the only
round this run ever has, so a harness that has to be decided is decided here as part of the scope
rather than in a question of its own.

**And it is one round because you did the reading first**, per that same file: every number on this
screen — the count of a list somebody has to write, what a published source already contains, how
long the base branch has been apart from the default — is yours to fetch before the screen goes up.
A gate that asks in order to find out spends the run's only round on its own ignorance, and the
price it quoted moves while the owner is still reading it.

**Nothing else is asked, deliberately.** Whether the owner is reachable is not worth asking of a run
that lasts a day — every child gets `gate: "none"`, so an expensive fork becomes a recorded
assumption instead of a night spent waiting on a phone, and they read them all at once in the pull
request.

## The run files

`.agent-kit/runs/<date>-epic-<slug>/run.json`, shaped like
`${CLAUDE_PLUGIN_ROOT}/templates/run.json`: `command: "epic"`, `step: "gate"` while this screen is
up, `entries` holding the keys the owner
took, `children` naming the batches in order, `window` your own tmux session, and `finish` carrying
what the gate settled — the scope, the wave cap, the batches already delivered. **A resumed run
reads `finish` instead of asking again**, so anything the gate decided that is not in there is a
question the owner will be asked twice.

`finish.lenses` is **not** the gate's and stays empty until the audit begins: the `--advance` that
reaches it writes them, having seen the product built. Empty there means not yet chosen, never
*nobody decided* — a resumed run before the audit reads it that way and asks nothing.

**`step` on this file is your own phase, and you move it**: `gate` while this screen is up,
`building` once the first batch is under way, `auditing` when the audit begins, `proving` at the
scenarios, `done` at the end. No driver watches this file — **the stop hook does**, and only for the
last of those: a terminal step here is what closes your session, since when nothing follows there is
no driver left to close it. Everything before it is a phase of a run that outlives any one session,
and the hook stands aside for all of them. A run left at a step nobody set is a run whose state has
to be reconstructed from its children, and `--resume` is not the only reader: the check lists a run
that never reached a terminal step, and a person looking at that list should see where this one
stands.

`model` is the one setting that moves the price of a run rather than trimming its edges, so say
which you took in the screen, beside the price. Default it to **the model you are running on**; a
session started without one takes the install's default, which may be neither what you are on nor
what they asked for.

**A cheaper model the owner names goes to the children and not to this run's own file.** The
children are effectively the whole cost — on a real night the closing session was 2M of 73M — while
this file's model is what your `--advance` sessions run on, and those decide what follows. Cheap
where the work is, unchanged where the judgement is.

**Each batch's own file gets a `model` too, and it is the one you are running on.** The driver
starts a batch's closing session on the model in *that batch's* file and looks nowhere else — not
here. Left empty it takes the install's default, so the session that writes the pull request would
run on something nobody chose.

Each batch is an ordinary sprint run file — `command: "sprint"`, `parent` naming this run, children
with `deliver: "branch"`, `gate: "none"`, chained off each other. Write **only the batch you are
about to start**: a batch composed three phases ahead would be composed against code that does not
exist yet.

**Every batch of three or more opens with a frame child**, written exactly as
`${CLAUDE_PLUGIN_ROOT}/skills/sprint/SKILL.md` writes one, under *Write the run files* — the JSON
is there and is not repeated here. It matters more here than it does in a sprint and for
both of its halves: nobody is present at any point of this run, so the questions two features would
each answer differently are answered once instead of twice; and an epic is long enough that a
session dying in the middle of one batch would otherwise take the rest of the batch with it.

The branch is `epic/<slug>`, created once **from the branch this session is standing on** — not from
the default branch. That is where the description you are building from lives: a `blueprint` run in
another session leaves its work on a branch of its own, and an epic based on `main` would build
against a description that is not there. Every batch chains onto it and the closing session moves it
forward, so there is one branch and one pull request for the whole run.

Two consequences, and both are said on the screen rather than discovered in the pull request:

- **anything uncommitted is committed here**, as `docs(knowledge):` — the batches cannot start on a
  dirty tree, and what is not committed is not in the base they build on. Say what you committed;
- **where the pull request points** is that base branch when it is pushed and still open — then the
  diff is this run's work and nothing else. Otherwise it points at the default branch and carries
  the description's commits too; say how many, so nobody opens it expecting only code.

Then set `step: "building"` on this file, start the driver on the first batch and end:

```bash
nohup python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" .agent-kit/runs/<first batch>/ >/dev/null 2>&1 &
```

Close per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`, then stay as the window —
`${CLAUDE_PLUGIN_ROOT}/rules/window.md`, unchanged. The owner steers with the
same two words, and closing you costs the run nothing but its narrator.

**Read that file before you close, not when the driver first pokes you.** By then hours have passed,
the context has been compacted at least once, and what remains of this instruction is a path — which
is how a live run came to review a finished batch on its own and put a question to the owner in the
middle of the night. The rule it never read is the one that says a window reports and never asks.

## `--advance`: what follows a batch

The driver starts you when a batch has closed. **Ask the check whether it really closed, first,
before reading anything else:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --run .agent-kit/runs/<the batch that just closed>
```

**Silence means it is closed** — its `docs/runs/<slug>.json` record is there and carries `pr`,
`branches` and `spent` — and none of the closing session's work is yours to do again: not the suite,
not that record, not the pull request's body. **Output means it closed badly**, and it is named in
your report and in the pull request, like a blocked batch, rather than finished here: you did not
build this batch, and a session that quietly does the job again hides that it was skipped. Measured
on one run: of seven `--advance` sessions, five ran the suite, two wrote the batch record and one
rewrote the pull request body — 3% of the run, none of it asking first.

Then read this run's file and the batch's, and do one thing:

| Where the run is | What you do |
|---|---|
| batches left in `children` | write the next one and start the driver on it |
| the in-list is built | set `step: "auditing"` and move to the audit, per `${CLAUDE_PLUGIN_ROOT}/skills/epic/references/finish.md` |
| the audit is done | set `step: "proving"` and move to the scenarios, same file |
| the scenarios pass | write the finish into the pull request, and **then** set `step: "done"` |

Then end. You are one decision and its consequence, not a supervisor.

`done` is last on that row for a mechanical reason: the stop hook closes this session at the end of
the first turn that finds this run terminal, because when nothing follows, nothing else ever will.
Write the file first and the field after it, and the same holds for `blocked` — a run that stops for
hands says why, in the pull request, before it says that it stopped.

### What you may change about the run that is left

The gate settled the scope and the wave ceiling. Everything below that is yours, because you have
seen the product built and the gate had only prose to go on. **This run's `children` is the list of
batches, and you are its only reader** — the next `--advance` reads it and decides from it; no
driver ever looks at this file. A batch's own `children` is a different list, of features, and that
one the driver does re-read before every child. Keeping them apart matters: a feature slug put into
this list gets a driver started on it, which finds no children of its own. What has already run is
left alone.

| What you may do | How |
|---|---|
| reorder what is left | move the slugs in this run's `children` |
| drop a batch | take its slug out and set its own `step: "skipped"`; its entries stay `planned` and the pull request names them |
| add a batch — a round of fixes, a review | write its run file, with children of its own, and put its slug here |
| add work that is not a `ship` — an audit between two waves | it is **a child of a batch**, never a batch: write its run file with `prompt` in it and put its slug in that batch's `children`. This is why the driver reads that field, and `${CLAUDE_PLUGIN_ROOT}/skills/epic/references/finish.md` says the same. **The prompt is a command and that directory, and the child's context goes in `entries` and `task`** — the form and the night it cost are under `_prompt` in `${CLAUDE_PLUGIN_ROOT}/templates/run.json` |
| stop the run | write `stop` into the current batch's `control` file |

Two ceilings, and they are what keeps a run that can extend itself finite. Neither is a judgement
call:

- **three waves of audit**, from the gate. A lens that found nothing is not re-run at all;
- **an inserted child inserts nothing itself.** Work you added because a feature went badly is one
  level deep, never a chain that grows while it is being worked through.

**Nobody is waited for, and there is no exception.** An expensive fork becomes a recorded assumption
and the pull request carries it. A run that stood still for an answer had no way to receive one: the
window may not write into a run file, no child's session is alive between batches, and the deadline
always ran out — hours spent to reach the same place.

**Closing your own session is not yours and never was.** Ending a turn does not end a session, and
this file used to ask you to end it yourself with one shell line — placed, like every instruction of
its kind, after the work was finished, which is where instructions go to be forgotten. It was
forgotten on a measured run, and when it was finally obeyed the line was wrong anyway. Two programs
hold it now: the driver of the batch you start closes you before it builds anything, and the stop
hook closes you when this run has finished and no batch follows. Say your last line and stop.

**A batch that ended blocked does not stop the run.** Its features' entries stay `planned`, they are
named in the pull request as what did not happen, and the next batch starts. A run that stopped on
the first failure would lose everything behind it — but say it plainly, because a hole in an epic is
worth more attention than anything that did land.

**Before starting a batch, look at the working tree.** A dirty tree blocks every child in turn:
`ship` treats it as a blocker, and the batch would die one feature at a time against the same wall.
Report it and stop instead — `--resume` continues once it is clean.

**Tell the window** what now works and what was decided without the owner. One line, a statement:
nobody waits for an answer, and this run does not stop between batches.

## Coming back

`--resume` is for a run nobody is driving any more — the server restarted, the driver was killed, an
account limit outlasted the wait, or the session that was to decide the next batch died.

**Ask nothing.** Everything the gate settled is in `finish`; the owner has already answered.

Read this run's file and every batch's, and rebuild where it stands: which batches are terminal,
which is current, which of its children are not finished. Then start the driver on the current
batch — it leaves terminal children alone and builds the rest — or `--advance` if that batch is
done.

**A batch you write yourself is written by the gate's rules, not by this section's.** Normally there
is nothing to write — you continue batches that already exist, which is what this invocation is for.
When there is (the files were lost, or a batch was rolled back), everything under *The run files*
applies unchanged, and the one that gets forgotten is the frame child: a batch of three or more
opens with one. Measured — a resumed batch of three came out without it, and what it cost was not
the shared rules (its first feature wrote those itself) but `frame`, the record of what depends on
what, which is the only thing standing between one dead session and the rest of the batch.

**Never start a second driver over a live one.** The driver itself refuses when a child's session is
alive, and that is the check to trust rather than a guess: two drivers on one working tree is how a
night ends with commits on the wrong branch.

## What this command does not do

It does not design features, write code, run tests, or merge anything — those belong to `ship`, to
the driver, and to the owner. It opens exactly one pull request and never a second. It does not stop
to ask between batches: the gate was the conversation, and the control window is how a live run is
steered.
