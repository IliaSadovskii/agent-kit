# Measuring each thing once

Written 31 August 2026, after doing it. Not a step of the plan — maintenance, named three times in
these notes before anybody fixed it, which is itself the point of writing it down.

## What was wrong

`make test` took **26 minutes** for 1368 tests. Three of them accounted for eighteen of those
minutes, and every one of the three re-ran a measurement that already has a Makefile target:

| test | what it did |
|---|---|
| `test_every_shipped_case_fires` | ran the **whole bench** — 142 worlds |
| `test_the_bench_with_no_word_after_it_runs_the_cases` | ran the **whole bench again** |
| `test_every_shipped_case_is_armed_or_says_why_it_cannot_be` | ran the **whole disarm** |

So a routine `make test` measured 142 worlds three times, and then the owner and I ran `make bench`
and `make armed` separately on top: **five measurements of one thing per verification round.** Six
more tests genuinely slept — about 300 seconds between them — waiting for their own deadlines.

**It was not only slow; it was unsound.** The server has 11 GB shared between projects, and the
duplicated bench failed twice in my own verification runs, each time for want of a resource rather
than because a mechanism broke:

- `a-tree-in-the-way-of-one-feature` — the disarmed run did not come back within 300 seconds (S8e);
- `the-machine-frees-up` — `plant.sh exited with 137: Killed`, the out-of-memory killer (S9).

A suite that reddens for want of memory teaches everybody to re-run it rather than read it, which
is the opposite of what a suite is for. Both sightings are recorded in the notes for the steps they
interrupted; neither was fixed at the time, because fixing the instrument mid-step is how a step
stops being measured.

## What it is now

| | before | after |
|---|---|---|
| `make test` | 1368 tests, **26:35** | 1370 passed, 2 deselected, **3:19** |

Measured by me on a stable tree, after the work landed: `make bench` 142 of 142, `make armed` 137
disarm and 5 say in words why they cannot.

Four targets, and each answers one question:

- **`make test`** — is the kit's own code well? Minutes, not half an hour.
- **`make bench`** — do the mechanisms under the traps fire?
- **`make armed`** — are those traps traps at all?
- **`make round`** — all three, one word.

## The deselection says so out loud

A test whose whole measurement already runs under a target of its own carries
`measured_elsewhere("<target>")`. The routine suite deselects it and **prints the pair at the end
of its own output**:

```
not measured here: tests/test_bench.py::test_every_shipped_case_fires — `make bench` measures it
not measured here: tests/test_disarm.py::test_every_shipped_case_is_armed_or_says_why_it_cannot_be — `make armed` measures it
```

The line is derived from the same marks that do the deselecting. So a test cannot be dropped
quietly, and a line cannot name a test that carries no mark — one pass over one set of data, which
is the shape the door already uses for its answer and its view. `pytest --everything` runs them in
place, so they stay reachable and cannot rot.

That mechanism is itself covered: a new `tests/test_suite.py` runs the real collection of both bench
files in a subprocess and asks what was taken and what was said about what was not. Four branches
were broken by hand — the deselection, the printed line, `--everything`, one mark — and each
reddened what it should. **A bench trap for it cannot be planted**, and that is stated rather than
skipped: the bench drives the kit, not pytest.

## The third test was rewritten, not moved

`test_the_bench_with_no_word_after_it_runs_the_cases` is about the dispatch of a bare `bench` with
no subcommand, not about the cases. It now points `cases_root` at a directory holding one case and
measures exactly that. The only thing that stopped being checked by it — that the default directory
is `bench/cases` — is checked by a test that calls `cases_root()` directly and stays in the routine
suite.

## The six sleepers, all six changed

None of them was about waiting:

- three in `test_runner.py` waited on the attempt chain's real pause; the helper now hands them a
  pause of zero. The seconds themselves, and their doubling, are measured by three tests below them
  in the same file that pass their own pause and record how long they were asked to wait.
- `test_a_step_that_is_waiting_says_so_in_the_run` already had a fake clock for the owner's twenty
  minutes while the chain's pause stayed real.
- two in `test_cli.py` go through `main()`, where there is no seam in Python, so the pause is named
  where the machine names it: `[machine] backoff = 0` in the config — the same zero `bench/world.py`
  writes into every case's world.

What was left alone, and why: four tests take three to five seconds each because they **kill process
groups and then watch whether a file keeps growing**. There the waiting *is* the mechanism.

## What this cost, and what it did not

Nothing stopped being covered. The two deselected measurements run in `make bench` and `make armed`,
which I run in every verification round anyway — but that was true before, and it is written down
now rather than left to my memory.

Two things worth knowing, found on the way:

- **Under load the three heavy tests took 18 minutes, not the 11.5 recorded in S8e's note.** The
  spread is itself the symptom.
- `--collect-only -q` in pytest 8 changes its output format when `-q` arrives twice, and it already
  arrives once from `addopts`. A test that missed this would have been green for nothing; the trap
  is recorded as a comment where somebody will meet it.

The most expensive thing left in the routine suite is two bench tests that genuinely build worlds —
seven and six seconds — checking that a case stops firing when its trap is taken away. They are not
duplicates of `make bench`, but they are the next candidates if another minute is ever needed.
