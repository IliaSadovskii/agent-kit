# Where the tokens burn

A third measurement of the same two runs, taken because the second one
([the counter was doubling](2026-08-14-the-counter-was-doubling.md)) ended on *the kit has no
material saving left in it* — a conclusion large enough to be worth attacking. Two of its claims
survive. The one about the ceiling does not: the counter was fixed and the curve it feeds was not,
and the ceiling that came out of it is 14% off the bottom.

Everything below is priced in **weighted tokens** — a plain input token is 1, cache read 0.1, cache
write 1.25, output 5 — and read from `usage` in the transcripts, deduplicated by `message.id`.
Subagents live in `<session>/subagents/*.jsonl` since some version of the harness and are included;
the earlier notes did not include them, which is why their totals for the same run are smaller.

## The week

| Where | Weighted tokens | Share |
|---|---|---|
| `beeplish` — both runs | 265.5M | 71% |
| `agent-kit` — six conversations about the kit | 98.0M | 26% |
| everything else | 10.4M | 3% |

The earlier note's headline finding is confirmed and is the largest single number here: **six
sessions of talking about the kit cost two thirds of a whole `epic`.** Each ran 100-600 turns and
reached 400-780k of context — four to five times past the bottom of the very curve those
conversations were about. Modelled with the same fit as below, and charging each segment its cold
cache and its eight turns of re-orientation, cutting them at 170k would have cost 50.3M instead of
95.1M.

Nothing in the kit can reach that. It is a habit, and the habit is the one `ship` already has.

## Per feature, the second run was cheaper

| Run | Features | Sessions | Hours | Cost | Per feature |
|---|---|---|---|---|---|
| `mvp`, 9-11 Aug | 33 | 69 | 31.3 | 160.4M | 4.86M |
| `epic`, 13-14 Aug | 23 + 8 audit | 110 | ~15 | 104.6M | ~3.4M |

Which answers the question that started this: nothing got worse. The second run has more sessions
and each is shorter, and it was still running its audit when this was taken.

## Where a run's money goes

Second run, 107.9M over 112 sessions, from `scripts/measure.py /projects/beeplish --by-role`:

| | sessions | | |
|---|---|---|---|
| feature children (`ship`) | 86 | 81.8M | 76% |
| audit lenses | 4 | 10.1M | 9% |
| `sprint --close` | 7 | 5.0M | 5% |
| `epic --advance` | 7 | 3.3M | 3% |
| `blueprint` | 2 | 2.7M | 2% |
| `epic --resume` | 1 | 1.9M | 2% |
| the gate and its window | 5 | 3.1M | 3% |

**A first pass at this table said `--advance` was 10%, and it was wrong.** Sessions were classified
by the first kit command in their opening records, and the pattern matched the `/mvp-finish` inside
the run directory `2026-08-13-epic-mvp-finish` — which appears in the arguments of every `--advance`
of that run. Twelve sessions were filed under a command nobody typed, and the two roles they really
belonged to are the two that moved. The fix is in `measure.py`, in the pattern, with the case
written beside it; the lesson is the one this kit already has, which is that **a measurement
inherits the defects of what took it** — including when the instrument is three hours old.

And inside those, by what the tokens are carrying — 112 sessions, 5404 turns:

- **the floor, re-read on every turn: 23.6M, plus 6.3M writing it cold. 29% of the run.** The floor
  is 45.7k: ~33k of harness system prompt and tool definitions, ~9.4k of `ship/SKILL.md`, ~2.7k of
  three `CLAUDE.md` files. **The kit owns a fifth of it**, which is the arithmetic behind *trimming
  prose is not the lever*: a thousand tokens cut from `ship` is 0.5% of a run.
- **output at ×5: 18.0M, 17%.**
- everything the sessions read and wrote: ~48M. Of the bytes that enter a context from a tool,
  `Bash` results are 62% (`cat`/`sed` 44% of those, `grep` 19%), `Read` 35%. By file, the largest
  single named thing is **`run.json` — 2.14M characters over 567 reads, 16% of all tool-result
  bytes**, because run files reach 17-19k characters and are read whole.

Two things that were suspected and are not true: the cache is working (of 5233 turns, 6 rewrote it
outside a session start), and the hooks cost nothing in context.

## The curve, fitted a third time

The previous note refitted cost against turns and got `0.48M + 5.3k·n + 75.6·n²` with re-orientation
at 40 turns. Checked against the observed medians of the sessions it was fitted on, that curve is
out by **21% on average**, and not evenly — it reads ~20% low from 130 to 190 turns, which is the
only band where a ceiling is decided.

Refitted over 119 `ship` sessions of both runs, counting a turn as one reply of the model rather
than one transcript record:

```
cost(n) = 0.076M + 10.67k·n + 87·n²          context(n) = 45.7k + 1.64k·n
```

Mean error against the same observations: 4%.

| turns | observed | old curve | refit |
|---|---|---|---|
| 28 | 0.39M | 0.69M (+76%) | 0.44M (+14%) |
| 49 | 0.81M | 0.92M (+14%) | 0.81M (−0%) |
| 70 | 1.21M | 1.22M (+1%) | 1.25M (+3%) |
| 108 | 2.33M | 1.93M (−17%) | 2.24M (−4%) |
| 131 | 3.11M | 2.47M (−21%) | 2.97M (−5%) |
| 172 | 4.51M | 3.63M (−20%) | 4.49M (−1%) |
| 186 | 5.19M | 4.08M (−21%) | 5.07M (−2%) |

**The turn axis was wrong by the same kind of defect as the context axis.** One reply of the model
carrying several content blocks is several records in the transcript — a factor of ~1.9 — so the
earlier fit's growth of 0.97k per turn is really 1.64k, and its re-orientation of 40 turns is 8.

Re-orientation measured directly, as the median turn of the first `Edit`: **18 turns in a session
starting from nothing, 8 in one that took a handoff.** A cut therefore costs about 0.17M — the
restart term plus those eight turns — which is a fifth of what the earlier number implied.

## What that makes the ceiling

Both corrections push the same way: a steeper tail makes a long session dearer, a cheaper cut makes
cutting easier. Priced over the real distribution of feature lengths in the second run — 36
features, median 114 turns in total, p90 243 — the whole cost of building them:

| ceiling | 130k | 150k | 170k | 190k | 210k | 240k | 280k | 340k |
|---|---|---|---|---|---|---|---|---|
| vs best | +0.4% | — | +1.0% | +2.7% | +4.9% | +7.4% | **+14.0%** | +18.6% |

The bottom is a plateau from 130k to 170k and the whole band up to 190k is inside 3%. **280k is 14%
off it** — and the second run never paid that, because the doubled counter had it cutting at
140-168k of real context, which is the plateau. The instrument was wrong and the behaviour was
right; fixing the instrument without refitting the curve would have made the next run the first one
to actually sit at 280k.

The ceiling is now **210k**. Not 160: 280 was never compared with anything a night could resolve —
300 → 280 is 0.8% — and 210 against 280 is a difference a single run can show. If it holds, 160 is
where to go next.

**What the mechanism is worth is still small.** The whole span from 130k to 280k is 14% of the
feature children, which is ~10% of a run. That part of the earlier note stands, and so does its
advice to look elsewhere.

## Three defects in the driver's own reading, and how far they go

Checked by replaying the driver's reader over the real transcripts.

- **The record parse is correct.** All 20,763 usage records: the outer `usage` equals the sum of
  `usage.iterations[]` on every record that has any, and `cache_creation_input_tokens` is an integer
  everywhere. The doubling is gone.
- **The delivery is sound.** 1459 polls simulated by truncating real transcripts at record
  boundaries and calling the driver's own `read_tail`/`context_size`: never blind, never low by more
  than 10%, and `opening_size` found the floor in all 186 sessions. One latent hole — the longest
  single transcript line is 273k characters against a 200k byte window, and a line longer than the
  window leaves nothing parseable. Window raised to 400k.
- **`--room` has been inert since the counter was fixed.** `size - floor >= room` with a floor of
  45.7k and a ceiling of 210k is `164k >= 40k`, always. It can only bind where the ceiling is under
  the floor plus `room`, which is a ceiling set by mistake — it used to bind because the broken
  counter doubled the floor. Its help text said otherwise and now says this.
- **A floor that could not be read lapsed silently.** With `floor` at 0 the `room` condition clears
  trivially and the ceiling decides alone. That is the deliberate behaviour and the tests hold it;
  what was missing is that nothing said so, and a guard that stopped applying looked exactly like a
  guard with nothing to complain about. The driver now writes `floor-unreadable` into the run log,
  once per session. It has never fired on real data.

## What was looked for and is not there

Confirming the earlier note where it was right, from an independent measurement:

- **The handoff mechanism is not a saving.** 42 of 83 feature sessions in the second run exist only
  because of it, and cost per feature barely moves with the session count: 4.86M at 2.1 sessions per
  feature, 3.4M at 2.6.
- **The reviewer is cheap.** 36 runs, 6.9M — 6.6% of the run, 0.19M against a feature costing 3.4M.
- **`--brief` is not being skipped**, for the reason that note gives.

And three that are new, small, and free:

- `code-review` and `pr-review-toolkit` are enabled globally on this machine and sit in the system
  prompt of every session of every project. The kit forbids itself from calling either.
- `ship` ran `make e2e` 144 times across 80 feature sessions, and its own Verify step says not to.
  Cheap in tokens, expensive in hours.
- **`epic --advance` re-does the closing session's work**, though it is 3% of a run and not the 10%
  the mistake above made it look. Of its seven sessions, five ran the suite, two wrote
  `docs/runs/<batch>.json` and one rewrote the pull request's body — all three of those belong to
  `references/close.md`. Traced through one of them: it ran `make test`, `make e2e` and the linter,
  re-derived the ledger's movement with `git diff | grep -c`, wrote the batch's durable record and
  edited the pull request. Its own instruction is *decide what follows, start it, stop.* The check
  worth having is mechanical — a batch whose `docs/runs` record, `spent` and `pr` are all present is
  closed, and a batch missing them is a defect to name rather than to quietly finish.

None of those is written yet. They are here so the next reading starts from them.
