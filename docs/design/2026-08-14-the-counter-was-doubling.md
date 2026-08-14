# The counter was doubling, and what that hid

Every number in [2026-08-14-what-one-night-measured.md](2026-08-14-what-one-night-measured.md) that
came from the driver is twice the truth. The mechanism it tuned was running at half of what its own
command line said, all night, and the tuning was done against the wrong axis. This note carries the
proof, the corrected figures, and the thing the corrected figures say that the old ones hid.

## The defect

`context_size` and `opening_size` found their numbers by scanning each transcript line for three
field names and summing every match. A usage record carries those three fields twice — once in
`usage`, once again inside `usage.iterations[]`, which repeats them per API iteration:

```json
"input_tokens": 2, "cache_creation_input_tokens": 1406, "cache_read_input_tokens": 166691,
"iterations": [{ "input_tokens": 2, "cache_creation_input_tokens": 1406,
                 "cache_read_input_tokens": 166691, ... }]
```

Six numbers matched where three were meant: 336k reported against 168k of real context.

Measured across the whole run: **20,249 of 20,260 usage records carry exactly one `iterations`
entry, and the ratio of reported to real is 2.00 on every one of them.** The eleven that are not
doubled are the records with no `iterations` at all. There is no partial case and no drift — it is a
clean factor of two.

## What the real numbers are

| | as the driver read it | measured |
|---|---|---|
| a session's floor | 90.8k | **45.5k** (median of 104 sessions, quartiles 45.3k and 45.8k) |
| context growth per turn | 2.25k | **0.97k** |
| `--ceiling 300` fires at | 300k | **~150k** |
| `--ceiling 120` fired at | 120k | **~60k**, and with `--room 80`, really at 85.5k |

That last line explains the failure the ceiling was raised to fix. A floor of 45.5k plus the 40k of
growth `room` demanded put the trigger at 85.5k — which is 40 turns, which is exactly what a session
spends before its first edit. **Sessions were handing over the moment they finished orienting**,
eleven times in an hour on one feature. Not a modelling error: an arithmetic one.

## The curve, refitted

Session cost fitted over 170 sessions of both runs, in tokens priced against a plain input token
(cache read ×0.1, cache write ×1.25, output ×5):

```
cost(n) = 0.48M  +  5.3k·n  +  75.6·n²        context(n) = 45.5k + 0.97k·n
          restart   floor      growth
```

The square is 57% of a session's cost at 150 turns and 77% at 300. Dividing by the turns that were
not re-orientation gives the bottom:

| turns | context | o=25 | o=40 | o=55 |
|---|---|---|---|---|
| 100 | 142k | 23.5k | 29.4k | 39.2k |
| 150 | 191k | 23.8k | **27.1k** | 31.3k |
| 200 | 240k | 26.1k | 28.5k | **31.5k** |
| 300 | 336k | 32.3k | 34.1k | 36.2k |
| 400 | 434k | 39.2k | 40.8k | 42.6k |

Measured re-orientation is 40 turns, so the bottom is ~150 turns and 191k, and the floor of the
curve is flat from 160k to 250k. **The ceiling is now 280k** — the flat end of the bottom, because
the expensive error is cutting early and because the tail after the ask lands ~20k further on.

Three independent routes agree on that band. The fit above. The compaction practice, which puts the
threshold at [70–75% of the window](https://zylos.ai/research/2026-04-21-agent-context-compaction-long-running-sessions/)
rather than the 95–98% most harnesses use. And the quality argument, which puts the working limit of
[a 200k model near 130k](https://www.morphllm.com/context-rot) — 30–40% below its advertised size.
Money, engineering practice and accuracy land on the same number from different directions.

## What the corrected numbers say that the old ones hid

**The mechanism is worth almost nothing, and that is the finding.** On the run it was measured
against — 22 children, 41 handoffs — the children divide like this:

| sessions per child | children | cutting, against not cutting |
|---|---|---|
| 1 | 19 | — |
| 2 | 12 | **+5.0M worse** |
| 3 | 4 | **+1.8M worse** |
| 4 | 3 | +0.2M |
| 5 | 3 | −2.0M better |

Cutting cost about **5M tokens more than never cutting at all**, on a run of 183M. It loses on two-
and three-session features, which are 16 of the 22, and only pays from five sessions up.

A ceiling is a guard against a session growing without bound. It is not a saving, and the night of
2026-08-13 was spent tuning a parameter worth ±3% while believing it was the lever.

Where the money actually is, on the same run: **41% of every token burned before the first edit of a
session** (26.5% on the earlier `mvp` run), 103 sessions against 23 features, and 14 sessions that
never edited a file at all. That is 75M and 10M respectively. Neither is reachable from the ceiling.

## What this changes in the kit

- `record_size` parses the record and reads the three fields by name. A field that appears twice is
  not a number to add up, and no regular expression over a line can tell the copy from the original.
- `--ceiling` 300 → **280**, `--room` 80 → **40**. Together with the fix these leave the run's real
  behaviour close to where it already was — the point is that the numbers now mean what they say.
- `handoff_due` carries the refitted curve and, more importantly, carries what the mechanism is
  worth, so the next person to come looking for a saving here is told at once to go elsewhere.

## The method note

The earlier note's closing line was *don't argue about numbers, measure them on a live run*. That
was right and it was not enough. Every number in it was measured — off an instrument nobody had
checked. **A measurement inherits the defects of what took it**, and the check that would have
caught this is two minutes long: read one raw record by hand and see whether the instrument agrees.
