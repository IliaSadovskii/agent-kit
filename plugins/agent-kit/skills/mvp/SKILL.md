---
name: mvp
description: From the blueprint to a running prototype — build everything inside the MVP bounds autonomously, audit it, and prove it with the scenarios against the running application, delivered as one pull request.
argument-hint: "[--advance <run dir> | --resume <run dir>]"
disable-model-invocation: true
---

# MVP

Everything inside the MVP bounds, built, audited and proved, as one pull request the owner can open
and click through.

**It owns no build, test or pull-request logic.** It composes batches and hands each to the driver;
the driver runs `ship` per feature and the closing session per batch. Everything those already do
holds unchanged. What is this command's own is three things: the gate, the order of the phases, and
knowing when it is finished.

| Invocation | You are |
|---|---|
| `/agent-kit:mvp` | the gate — the one conversation this run has. Then start the first batch and stop |
| `/agent-kit:mvp --advance <run dir>` | started by the driver when a batch finished: decide what follows, start it, stop |
| `/agent-kit:mvp --resume <run dir>` | the run stalled and nobody restarted it. Work out where it is and carry on — see *Coming back* |

Each of these **ends**. Nothing sits watching for hours: between phases the driver runs, and a phase
that is waiting is a phase that has already lost the night to an account limit.

## The gate

The only moment an owner is present, and its whole job is to make the finish line real. A sprint
with a thin blueprint still delivers five features; an mvp with a thin blueprint has no stopping
condition at all.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --mvp
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

**Derive the in-list.** The bounds are written in the owner's own prose — *"registration and sign-in,
email confirmation, the composer, moderation with a fallback"* — not as entry keys. Read the bounds
section and the entry headings, and map one to the other. Take only what is not already `built`.

**Order it.** Scenario steps name action keys and entries carry their preconditions, so the order is
derived, not chosen: what must exist before what. Group the result into batches of about five, each
batch one topic, and put the batch that makes a whole scenario walkable first — that is what the
owner can click after the first few hours.

**Choose the lenses.** From the product, not from a menu: tests and scenarios always; `deps` always;
`security` where there are people, permissions or money; `performance` is premature here and
`conventions` optional. Say which you took and why in one line.

**Price it.** A feature costs roughly 15M tokens on a real project, so nineteen entries is about
280M and the better part of a day. Say the number.

**Say what will prove it.** The finish line is *every scenario inside the bounds passes against the
running application*, and something has to run them. Name it from `stack.md` and from the count
above: the harness that exists, or — when nothing claims a scenario yet — that there is none, what
building one would cost as a batch of its own, and that without it the finish is the owner's hands
on a phone rather than a green suite. **Never leave that to be discovered later.** It is one line
here and a rebuilt plan later, and the owner is standing right there.

Then **one screen, one question**: the finish line said back in words — including what proves it —
the batches in order, the lenses, the price, and *this scope, or narrower?* Two or three options
with counts, per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`. That is the only question this run ever
asks, so a harness that has to be decided is decided as part of the scope rather than in a question
of its own.

**Nothing else is asked, deliberately.** Whether the owner is reachable is not worth asking of a run
that lasts a day — every child gets `gate: "none"`, so an expensive fork becomes a recorded
assumption instead of a night spent waiting on a phone, and they read them all at once in the pull
request.

## The run files

**Check `tmux` is installed before the gate's screen** — `command -v tmux`. Without it the driver
cannot give a feature its own session, and an mvp is nothing but batches of those. Say so at the
gate rather than after the owner has answered.

`.agent-kit/runs/<date>-mvp-<slug>/run.json`, shaped like
`${CLAUDE_PLUGIN_ROOT}/templates/run.json`: `command: "mvp"`, `entries` holding the keys the owner
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

The branch is `mvp/<slug>`, created once from the default branch. Every batch chains onto it and the
closing session moves it forward, so there is one branch and one pull request for the whole run.

Then start the driver on the first batch and end:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" .agent-kit/runs/<first batch>/ >/dev/null 2>&1 &
```

Close per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`, then stay as the window —
`${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/window.md`, unchanged. The owner steers with the
same two words, and closing you costs the run nothing but its narrator.

## `--advance`: what follows a batch

The driver starts you when a batch has closed. Read this run's file and the batch's, and do one
thing:

| Where the run is | What you do |
|---|---|
| batches left in `children` | write the next one and start the driver on it |
| the in-list is built | move to the audit, per `${CLAUDE_PLUGIN_ROOT}/skills/mvp/references/finish.md` |
| the audit is done | move to the scenarios, same file |
| the scenarios pass | set `step: "done"` and say so in the pull request |

Then end. You are one decision and its consequence, not a supervisor.

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
the first failure would lose everything behind it — but say it plainly, because a hole in an mvp is
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
