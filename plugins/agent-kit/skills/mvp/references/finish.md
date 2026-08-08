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

**One sprint per lens.** The lens already groups its findings into units of work, and a batch should
be about one thing.

**Only the lenses `finish.lenses` names**, chosen at the gate from what this product is. Not the
full set: a sweep with every lens on every wave costs more than the features did.

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

## Finishing

Set `step: "done"` on the run file, and write the pull request's closing summary: what the product
now does, which scenarios are proved and by which tests, what the audit left, every assumption taken
without the owner, and what did not happen.

Then the line that makes the whole run usable — how to open it without touching the working tree the
children share:

```bash
git worktree add /tmp/<slug>-preview mvp/<slug>
```

A `git checkout` in the project's own directory would pull the tree out from under a live run, and
this is the sentence that stops the owner doing it at three in the morning. Say which port to start
it on if the project's own instance is already using one.
