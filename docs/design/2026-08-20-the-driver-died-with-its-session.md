# The driver died with the session that started it, 20 August 2026

An `epic` on a live project stopped at its third batch. The batch's run log holds two lines and
nothing else:

```
2026-08-19T21:49:31Z step=driver event=start detail=4 features
2026-08-19T21:49:31Z step=driver event=window detail=ccp-beeplish
```

Four features stayed `queued` for eight hours. No child was started, no session died visibly, and
no message was written anywhere. This is what happened, why it had not happened before, and why the
release that came the day before made it certain rather than fixing it.

## What the machine recorded

The driver is started by the session that composed the batch, as a background process of that
session's shell. One second after those two lines, the systemd journal has:

```
Aug 20 01:49:32  tmux-spawn-79c91a45-…scope: Consumed 27.998s CPU time
```

That is the pane of the session that started the driver, closing.

Three things close it, and at the time all three were live:

1. **The driver itself.** `go()` begins by closing the session it was started from —
   `self.launcher.stop(f"{parent}-advance")`.
2. **An instruction in prose**, in `skills/epic/SKILL.md` up to 2.25.0: *So close yourself as the
   last thing you do, once the batch is under way*, with `tmux kill-session` on the session's own
   name.
3. **The stop hook**, from 2.26.0, which took that job over from the prose.

## Why `nohup` did not save it

The comment above the line in `go()` read:

> Safe because the driver is started under `nohup` and ignores the SIGHUP that killing a session
> sends — `setsid` would do the same and does not exist on macOS.

Both halves are wrong on any machine with systemd. tmux 3.4 puts every pane in a scope of its own;
`KillMode` for a scope is `control-group`; closing the pane tears down the scope and everything in
it. `nohup` ignores one signal, and this is not that signal.

Measured on the machine that lost the night:

```
the shell itself:        …/app.slice/tmux-spawn-e8b65465-….scope
nohup child:             …/app.slice/tmux-spawn-e8b65465-….scope
setsid nohup child:      …/app.slice/tmux-spawn-e8b65465-….scope
```

A new session id is not a new control group. `setsid` was offered as the portable equivalent and is
not equivalent to anything.

## Why it had never happened

Because the sessions **usually forgot to close themselves**.

The instruction sat at the end of the command, after the closing report — a step after the last
step. On the same machine, the session of an `epic` from 17 August was still standing on 20 August,
having never run it. In the batch that failed, the two batches before it had run on the same
version, from the same kind of session, and both survived: their sessions did not close, so their
drivers lived.

So the kit's most load-bearing property that week was a session forgetting an instruction. Nothing
recorded that, and nobody would have believed it if asked.

**2.26.0 made the closing reliable.** It removed the prose instruction and gave the job to the stop
hook, with a design note about a session that stood for eight hours doing nothing. That was the
right fix for the defect it named — and it armed this one: from that release, the thing that had
been forgotten happens every time.

The failure arrived a day later, on 2.25.0, when a session did it by itself.

## Why nobody could see it

The launch line ended in `>/dev/null 2>&1 &`. A driver that died in its first second and a driver
with nothing to say produce identical evidence: an empty log and a run that stopped moving. The
reconstruction above came out of the systemd journal, four hours after the fact, because that was
the only place that recorded anything.

This kit has a rule for exactly this — *a check that cannot read its input says so* — and the rule
was about checks. It applies to programs too: **a process whose output goes nowhere cannot report
its own death.**

## What was changed, in 2.28.1

- **The driver moves itself out of the pane's control group before it does anything else**, into a
  transient systemd service named for the batch, and prints which one. Everything after that is
  indifferent to what happens to the session that started it — the line in `go()` included, which
  is why that line stays.
- **Where there is no `systemd-run`, it says so and carries on in place.** A driver that a parent
  can kill beats no driver at all, and going quiet here would be the same defect wearing a new hat.
  The run log gets `detached` or `detach-failed` either way, so the state is readable afterwards.
- **The launch line writes to `.agent-kit/runs/<slug>/driver.out`.** Nothing in this kit should send
  a program's only voice to `/dev/null`.

## What this leaves open

**The transcript of a failure is only as good as the weakest silence in it.** Two mechanisms here
were unobservable — the driver's output and the fact of a session closing — and the run file, which
is the kit's own record, said only that the driver had started. A `driver-exit` line written on the
way out, whatever the reason, would have answered in one read what took four hours.

**And the deeper shape is worth naming.** A run's liveness depended on a process being a child of a
session that the run is designed to close. That is a dependency nobody declared, and it survived a
review, a design note about that very session, and a release. It was found only because it finally
fired. Where else does the kit depend on a parent it also kills? Nobody has looked.
