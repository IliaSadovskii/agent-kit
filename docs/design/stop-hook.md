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

## What it does not do

It does not judge the work, read the diff, or check the suite. `check.py --run` already judges a
closing run file and is called by `ship` at its last step. The hook's whole question is whether the
run believes it is finished.

## What becomes impossible without it

A run file left mid-step by a session that thought it was done — the defect that costs a driver
thirty minutes and a restart, and costs an unattended night that same amount per occurrence.
