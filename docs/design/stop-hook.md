# The stop hook — a turn that ends is not a run that finished

Designed 2026-08-10, from a live `mvp`.

A child pushed its branch, took its review, ran its security pass — and ended its turn with
`step: "deliver"` still in its run file. The kit judges a child by that field: `done`, or a pull
request, or nothing happened. Nothing had. The branch was fine, the work was fine, and the run said
it was mid-flight, because **ending a turn and finishing a run are separate events and nothing in
the harness ties them together.**

The only thing that noticed was the driver's stall timer, thirty minutes later.

## What the hook does

On `Stop`, before the session is allowed to end its turn: find this session's own run. If its step is
terminal — `done`, `blocked`, `skipped` — say nothing. If it is anything else, refuse the stop and
return the one sentence that says where the run actually is.

The session then finishes the step or records a blocker, both of which it already knows how to do.
Thirty minutes of waiting and a restart that discards a warm context become one line, immediately.

## Whose run is it

This is the whole design. A hook that blocked on *any* run in flight would trap the owner's own
session the moment a child was mid-build, which is most of a night.

So the driver writes the child's session name into its run file when it starts it — it already
writes exactly this for a batch's control window — and the hook resolves its own session name and
matches on that field alone. Two consequences, both wanted:

- **A session nobody registered has no run**, so the hook has no opinion. The owner's sessions,
  `blueprint`, `next`, and every side conversation are untouched by construction rather than by a
  list of exceptions.
- **`window` is never matched.** That field holds the owner's session, and matching it would block
  the very session the design keeps free.

## The three ways it must not misfire

**A step it cannot read is not a step to block on.** No run file, no session field, unreadable JSON,
no way to resolve its own name: exit without an opinion. Blocking on ignorance would strand a
session with no way to satisfy the condition.

**It refuses once.** `stop_hook_active` arrives true on the second try; the hook then allows the
stop. A run that will not close after being told once is the stall the driver already handles, and
two mechanisms fighting over the same session is worse than either alone.

**It fails open, out loud.** A broken hook must not stop the work — and must not go quiet either,
because silence is indistinguishable from consent.

## The same match, the opposite question — added 2026-08-19

A session whose run is *finished* is the mirror of the one above, and one of them has nobody to
close it.

Everything the kit starts is closed by the driver that started it: each child it watched, and each
hand-back session before the next batch builds anything. The session an `epic` hands back to falls
through both. It decides what follows; when something follows it starts a driver, and that driver
closes it. When **nothing** follows — the run is finished — there is no next driver, and the driver
that started this session exited at the hand-back. Nothing is left that knows the session exists.

Measured on a live run of 18 August 2026: the session wrote `step: "done"`, reported to the window,
said its closing line, and stood for eight hours until the owner noticed it and asked it to close.

`epic/SKILL.md` did carry the instruction to close itself — one `tmux kill-session` line at the end
of a section, after the work was finished, which is where instructions go to be forgotten. Two
things were wrong with it and the second is the more interesting:

- it was placed after the closing report, and a report is the end of a turn. The instruction asked
  for a step after the last step;
- **the line was wrong anyway.** `tmux kill-session` kills the session and leaves it registered with
  whatever started it. On the machine this was measured on, a watchdog restored the session a minute
  later and typed *Continue from where you left off* into it. When the owner finally asked the
  session to close, that is exactly what happened — the kill worked, and the session came back.

So the rule left prose for a program, which is the move `CLAUDE.md` asks for. The hook already
resolves *this session's own run* and matches on `session`; a finished `epic` on that field is a
session with nothing left to do, and closing it is one call. `hand_back` now writes the name there,
which it did not before — nothing had ever needed it.

**Only an `epic`, and the reason is not a race.** The driver's watch loop asks `run.terminal()`
first on every pass and `alive()` after it, so a child that closed itself on a terminal step reads
as finished, not as dead. The reason is the fourth answer: every other session already has a closer
and they work — the driver closes each child it watched, and the driver of the next batch closes the
hand-back session before it builds anything. A second closer for those would make nothing possible
that is not already possible, and this file's own rule is that a mechanism with no such answer does
not get built.

**And the other half of the hook had to learn about `epic` too**, which was not obvious and cost a
defect in the first version of this change. Writing the session's name into the epic's run file arms
*both* halves at once — the closing half and the refusing one. An `epic`'s steps are `gate`,
`building`, `auditing`, `proving`: all of them non-terminal, all of them normal. That session
decides one batch, hands the building to a driver that outlives it, and ends its turn on purpose.
Refusing that stop would trap the one session with no way to satisfy the condition — its only exits
would be to mark a live run `blocked` or to declare it `done`, and the second one gets it closed
mid-run by the half above.

So `unfinished()` stands aside for an `epic` and for nothing else, while every other run of the same
session is still judged exactly as before.

Closing means asking the helper and **taking its answer**, and the driver's own `Launcher.stop` was
changed to do the same, because it had the same defect: it called the helper, ignored the exit code,
and killed the tmux session anyway. A non-zero exit means either that the helper guards that session
or that it stopped part way, and there is no way from outside to tell which — killing over the top
of the first overrides a guard, and over the second leaves a registration standing, which is the
whole defect. So a refusal is reported and nothing is killed. Where no helper exists at all, tmux is
the whole answer and its own failure is reported the same way. Where the helper made the session and
cannot close it — `claude-new` present, `claude-close` missing — the driver kills and says once that
it may have left the session registered, because there is nothing better to do and doing it quietly
is what made this take eight hours to notice.

**What a zero proves is that the job was accepted, and no more.** `claude-close` on this machine
writes `claude-registry del … || true`, so its own success does not depend on the unregistering
having worked, and nothing out here can check it. That is the floor of what a helper's reporting
allows; it is worth writing down rather than being described as a guarantee.

The hook's timeout in `hooks.json` is 30 seconds because of this call: closing a session can stop a
project's containers on the way out, and a budget smaller than the work it authorises is a silence
by another name. It is a floor, not a guarantee — containers that ignore a signal are stopped by
force after their own timeout, and past 20 seconds the helper's call is abandoned and reported.
Inside a hook, that is the end of what can be done about it.

**What this costs.** A session that has finished its run closes at the end of any turn, including
one where the owner typed into it. They get the answer and then the session goes. That is the
trade: the owner of the measured run was typing *«ну и ты закроешь или нет»* into a session whose
work had been over since morning.

It also makes the order of the last two actions load-bearing, so both files that carry the finish
now say it — `epic/SKILL.md`'s table and `epic/references/finish.md`, which is the one actually
being read at that moment: write the finish into the pull request, **then** set the step. A step set
first is a session closed before it has written anything, and that is true of `blocked` as much as
of `done`. `SKILL.md`'s description of the field said *nothing depends on it*, which had been true
since the field existed and stopped being true with this change; it now says what watches it.

**When it stops applying.** A hand-back session's name is derived from its run's slug, so the same
run picked up again produces the same name. A finished `epic` therefore has to stop speaking at some
point, or it would close whatever session next carried that name — `STALE_AFTER`, the kit's existing
answer to *this run file still speaks for the project*, is that point. Nothing clears the field
itself; the driver overwrites it on every session it starts.

## What it does not do

It does not judge the work, read the diff, or check the suite. `check.py --run` already judges a
closing run file and is called by `ship` at its last step. The hook's whole question is whether the
run believes it is finished.

## What becomes impossible without it

A run file left mid-step by a session that thought it was done — the defect that costs a driver
thirty minutes and a restart, and costs an unattended night that same amount per occurrence.
