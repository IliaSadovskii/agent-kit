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

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --epic
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --state
```

The first is fatal or silent: no MVP bounds, no scenarios, or no `commands.run` / `commands.test`
and this run does not start — say what is missing and offer `/agent-kit:blueprint`. The second is
the usual preflight, per `${CLAUDE_PLUGIN_ROOT}/rules/preflight.md`; open blocks on entries you are
about to build are settled here, because this is the last moment anyone can answer.

**`--state` is here for one line of its output**, and it is the most consequential fact the gate can
learn: *scenarios: N described, M with an end-to-end test*. That number decides how this run ends,
and until now nothing read it before the finish phase — which is the worst possible moment, because
a harness is infrastructure that shapes how features get built and by then they are built. On a
project where **M is zero**, no harness exists yet, and the run is heading for a finish it cannot
reach mechanically. Say so at the gate, in the finish line below.

Then the work only this gate can do.

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

**Order it.** Scenario steps name action keys and entries carry their preconditions, so the order is
derived, not chosen: what must exist before what. Group the result into batches of about five, each
batch one topic, and put the batch that makes a whole scenario walkable first — that is what the
owner can click after the first few hours.

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

**And price the audit separately, because it is not small.** Measured on one real `epic`: the lenses
and the batches that fixed what they found came to as much as building the product did. It is a
choice, so it goes in the screen as one — two waves against one, with what each costs.

**Say what will prove it.** Whatever this scope's finish line is, something has to run it. Name it from `stack.md` and from the count
above: the harness that exists, or — when nothing claims a scenario yet — that there is none, what
building one would cost as a batch of its own, and that without it the finish is the owner's hands
on a phone rather than a green suite. **Never leave that to be discovered later.** It is one line
here and a rebuilt plan later, and the owner is standing right there.

**Say how much of the description the owner has actually seen.** `product.md` lists the product's
parts, each either walked in an interview on a date or derived from code and documents and never
confirmed. Count them and say it as a fact: *four parts of six you walked; two were derived*. You
cannot measure whether a description is detailed enough — there is no such signal, and claiming it
would be the most expensive sentence on this screen. You can say what nobody has read, and on a
measured run that was the whole failure: the scenarios were written in the same session as the gate,
nobody walked them, and six of their endings contradicted the product by the finish.

**Then spend your questions where being wrong is expensive.** Not evenly across the list: rank the
entries you are about to build by what they touch — stored data first, then permissions, money, a
contract outside this codebase — and put the top few up as choices. Measured, an entry's decisions
scale with how much it changes and not at all with how thinly it is written, so this is the one
ranking with evidence behind it. Typically five entries of twenty, and the rest you decide and
record as you go.

Then **one screen**: the scope and its finish line said back in words — including what proves it —
the batches in order, the price in hours, what the audit adds, what has never been read, and *this
scope, or narrower?* Options with counts, per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`, and the
expensive entries beside it — one round, a handful of taps. This is the only round this run ever
has, so a harness that has to be decided is decided here as part of the scope rather than in a
question of its own.

**Nothing else is asked, deliberately.** Whether the owner is reachable is not worth asking of a run
that lasts a day — every child gets `gate: "none"`, so an expensive fork becomes a recorded
assumption instead of a night spent waiting on a phone, and they read them all at once in the pull
request.

## The run files

**Check `tmux` is installed before the gate's screen** — `command -v tmux`. Without it the driver
cannot give a feature its own session, and an epic is nothing but batches of those. Say so at the
gate rather than after the owner has answered.

`.agent-kit/runs/<date>-epic-<slug>/run.json`, shaped like
`${CLAUDE_PLUGIN_ROOT}/templates/run.json`: `command: "epic"`, `entries` holding the keys the owner
took, `children` naming the batches in order, `window` your own tmux session, and `finish` carrying
what the gate settled — the lenses, the wave cap, the batches already delivered. **A resumed run
reads `finish` instead of asking again**, so anything the gate decided that is not in there is a
question the owner will be asked twice.

`model` is the one setting that moves the price of a run rather than trimming its edges, so say
which you took in the screen, beside the price. Default it to **the model you are running on**; a
session started without one takes the install's default, which may be neither what you are on nor
what they asked for.

**A model the owner names goes to the children and not to this run's own file.** The children are
effectively the whole cost — on a real night the closing session was 2M of 73M — while this file's
model is what your `--advance` sessions and each batch's closing session run on, and those are the
ones deciding what follows and what the pull request says. Cheap where the work is, unchanged where
the judgement is.

Each batch is an ordinary sprint run file — `command: "sprint"`, `parent` naming this run, children
with `deliver: "branch"`, `gate: "none"`, chained off each other. Write **only the batch you are
about to start**: a batch composed three phases ahead would be composed against code that does not
exist yet.

The branch is `epic/<slug>`, created once from the default branch. Every batch chains onto it and the
closing session moves it forward, so there is one branch and one pull request for the whole run.

Then start the driver on the first batch and end:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" .agent-kit/runs/<first batch>/ >/dev/null 2>&1 &
```

Close per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`, then stay as the window —
`${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/window.md`, unchanged. The owner steers with the
same two words, and closing you costs the run nothing but its narrator.

**Read that file before you close, not when the driver first pokes you.** By then hours have passed,
the context has been compacted at least once, and what remains of this instruction is a path — which
is how a live run came to review a finished batch on its own and put a question to the owner in the
middle of the night. The rule it never read is the one that says a window reports and never asks.

## `--advance`: what follows a batch

The driver starts you when a batch has closed. Read this run's file and the batch's, and do one
thing:

| Where the run is | What you do |
|---|---|
| batches left in `children` | write the next one and start the driver on it |
| the in-list is built | move to the audit, per `${CLAUDE_PLUGIN_ROOT}/skills/epic/references/finish.md` |
| the audit is done | move to the scenarios, same file |
| the scenarios pass | set `step: "done"` and say so in the pull request |

Then end. You are one decision and its consequence, not a supervisor.

### What you may change about the run that is left

The gate settled the scope and the wave ceiling. Everything below that is yours, because you have
seen the product built and the gate had only prose to go on. `children` **is** the queue — the
driver reads it again before every feature, so editing it is how all of this is done, and there is
no second file to disagree with it. What has already run is left alone.

| What you may do | How |
|---|---|
| reorder what is left | move the slugs in `children` |
| drop a feature | take its slug out and set its own `step: "skipped"`; its entry stays `planned` and the pull request names it |
| add a feature, a round of fixes, a review | write its run file and put its slug in `children` |
| add work that is not a `ship` — an audit between two waves | the same, with `prompt` in its run file. This is why the driver reads that field |
| stand still and ask the owner | write `wait <hours> <question>` into the batch's `control` file |
| stop the run | `stop` in the same file |

Three ceilings, and they are what keeps a run that can extend itself finite. None of them is a
judgement call:

- **three waves of audit**, from the gate. A lens that found nothing is not re-run at all;
- **an inserted child inserts nothing itself.** Work you added because a feature went badly is one
  level deep, never a chain that grows while it is being worked through;
- **one `wait` per batch.** A run that stops twice for one absent owner has lost the night the
  deadline was there to save.

`wait` is the one that undoes a rule this command otherwise keeps — that nobody is waited for. Use it
only where the answer changes everything after it, not merely something: a measured run never called
its real model once, because the key was a manual action and every feature after that point was
proved against a stand-in. That is what it is for. The deadline is what makes it safe: when it runs
out the question is already in `waiting_on`, the pull request carries it, and the run goes on.

**And ending your turn does not end your session** — that is the part which reads as obvious and is
not. Nothing else closes you: the driver that started you exits at the hand-back, and the driver you
just started is watching its own children. So close yourself as the last thing you do, once the
batch is under way:

```bash
tmux kill-session -t "$(tmux display-message -p '#S')" 2>/dev/null || true
```

Left standing, you idle until the next batch reclaims the name — the driver takes it back rather
than typing into you, so nothing breaks, but a session per batch sits on a machine that is usually
shared. Do it last: your session dies with the command, so anything after it never happens.

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

**Never start a second driver over a live one.** The driver itself refuses when a child's session is
alive, and that is the check to trust rather than a guess: two drivers on one working tree is how a
night ends with commits on the wrong branch.

## What this command does not do

It does not design features, write code, run tests, or merge anything — those belong to `ship`, to
the driver, and to the owner. It opens exactly one pull request and never a second. It does not stop
to ask between batches: the gate was the conversation, and the control window is how a live run is
steered.
