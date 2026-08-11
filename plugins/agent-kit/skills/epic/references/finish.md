# The finish line

Read when the in-list is built and `--advance` has to decide what follows. Three things, in this
order, and the order is the point: the audit finds the holes, the scenarios judge the final state.

1. the in-list is built
2. the audit's lenses find nothing above minor
3. every scenario inside the bounds passes against the running application

Until then the run is not finished, however green the suite looks.

## The audit, in waves

A wave is **audit → the sprints that fix what it found → audit again**. Never twice over unchanged
code: between two runs of a lens there is always work that answered the first one.

**One batch per wave, not one per lens.** The lens already groups its findings into units of work,
so a batch takes the units of every lens in the wave, in the order the lenses themselves imply — one
unit, one child. Measured: six lens-shaped batches on one run cost six closing sessions and six
hand-backs on top of the work, for batches of two and three children. Split a wave only where one
lens's findings genuinely have to land before another's can be built, and say which and why.

**The audit itself is a child of the batch**, with `prompt` in its run file naming the lens and
telling it to close that file when it is done. It is not a `ship`, which is why the driver reads
that field — before it did, a live run wrote itself a shell script to launch the audit and another
to hand control back, neither of them tracked, neither of them knowing anything about limits or
stalls.

**The lenses are chosen here, not at the gate.** You have read what was built; the gate had only the
owner's prose. Take them from what this product is made of — `tests` and `scenarios` always, `deps`
always, `security` wherever there are people, permissions or money, `performance` only once there
are users to be slow for, `conventions` only if nothing else already holds the diff to a standard.
Write them into `finish.lenses`, with the one line of why, and do not take the full set: measured on
a real run, the lenses and the batches that fixed what they found cost as much as building the
product did.

**On the second wave, only the lenses that found something.** A lens that came back clean has
nothing to re-check — the code moved for the sake of another lens, not for it.

**When a lens stops.** It returns only minors and *also noticed* — it has done its job, and it is
not run again. It returns real gaps of the same class — the wave did not close them, so go round
once more. `finish.waves` is the cap, three by default; what is left when it runs out goes into the
pull request as work for the next run, named, not quietly dropped.

That cap is what makes this terminate. An audit is never *clean* — the conventions lens finds
something on any project ever written — so a rule of "until nothing is found" either never stops or
stops on a coincidence.

## The scenarios

The last phase, and the only one that judges the product rather than the code.

Every scenario inside the bounds must have an end-to-end test carrying `agent-kit:scenario <its
heading>`, and the suite must be green. That is mechanical — `check.py --state` counts described
against covered — and it is what keeps this phase from being an opinion:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --state
```

A scenario with no such test is work: one more sprint, composed from the scenarios lens, which
already knows how to say which harness is missing before the tests themselves. A scenario whose test
fails is a `fix`, and its cause is the most valuable thing this run will produce — it is a break at
a join, which no test written at the level of one feature can see.

**Start the application once, with `commands.run`, and walk what the scenarios walk.** A green suite
over an application that does not boot is exactly what this step exists to catch, and it is the last
moment anyone checks before the owner does.

**Start it in a worktree of the branch, never in the tree the run built in**, and this is the whole
point of the step rather than a detail of it:

```bash
git worktree add /tmp/<slug>-preview epic/<slug>
```

The tree the run built in has everything already done to it — dependencies installed, migrations
applied, `.env` filled in, files owned by the right user, images built. Starting there proves that
an application already running still runs. A fresh checkout is what the owner will have after the
merge, and it is the only place the question *does one command bring this up* has an answer.

**Then everything you had to do by hand to get it up belongs in one of two places, and there is no
third.** Either it goes **into `commands.run`** — a migration, a build argument, a port, a file
mode: anything a script can do, a script does — or it is named in Manual actions with the reason a
script cannot. Measured on one run, five mechanical steps ended up in a list of nineteen for the
owner to carry out: applying the migrations, rebuilding through the right target, a port into
`.env`, a `chown`, and running the browser suite. None of the five needed a person; they were
merely done by hand once and written down.

Nothing here writes deployment. A server, a domain, a production environment stay the owner's, and
say so. What this settles is narrower and is the thing they will do first: clone, one command, click
through it.

## Finishing

**`building (pr: <n>)` on every entry this run built is the finish, not a defect in it.** An entry
becomes `built` when its pull request merges, and `check.py --sync` is what moves it — nothing in a
run may, because the merge has not happened. A live run read `--status` saying *building: 21* as
work its finish still owed, carried that through four sessions of `--advance`, and there was never
anything to do.

Set `step: "done"` on the run file, and write the pull request's closing summary: what the product
now does, which scenarios are proved and by which tests, what the audit left, every assumption taken
without the owner, and what did not happen.

**Do not offer a fresh review of the whole diff** — `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`
settles that, and for a run the answer is no: this diff has been read twice with context nothing
else has, by the reviewer against each entry and by the audit's lenses over the whole branch.

**Name what no reviewer of any kind reached.** That is the finish's own job, and it is where the
real unknown is:

- **the suite on a machine other than the one that wrote it.** A project with no CI has never had
  its tests run anywhere else, so *green* means green where it was written. Say so, and say that the
  worktree below is where it is settled.
- **everything proved against a stand-in.** A run whose every proof went through a fake gateway, a
  fake sign-in or a fake clock has proved the fake. Name each seam by name — measured on one run,
  the real model was never called once in thirty hours, and that was known at the gate and true at
  the finish.

Then the line that makes the whole run usable — how to open it without touching the working tree the
children share:

```bash
git worktree add /tmp/<slug>-preview epic/<slug>
```

A `git checkout` in the project's own directory would pull the tree out from under a live run, and
this is the sentence that stops the owner doing it at three in the morning. Say which port to start
it on if the project's own instance is already using one.
