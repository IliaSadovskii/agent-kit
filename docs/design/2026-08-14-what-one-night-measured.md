# What one night measured

> **Every token figure below that came from the driver is twice the truth.** The instrument was
> double-counting: the floor is 45.5k and not 90.8k, growth is 0.97k a turn and not 2.25k, and the
> ceiling of 300k was firing at 150k. The conclusions about *where* the bottom sits survive in
> shape; the numbers do not. Corrected figures, the proof, and what the correction revealed — that
> the mechanism this note spent a night tuning is worth about ±3% — are in
> [2026-08-14-the-counter-was-doubling.md](2026-08-14-the-counter-was-doubling.md). Read that first.

Watching a live `epic` from the outside for fourteen hours — 2026-08-13 into 2026-08-14, on
`beeplish`, six batches and 23 features — and releasing against what it showed. Nine releases,
2.9.0 through 2.10.7. This is the evidence, so the next argument about any of it starts from numbers
rather than from the last person's intuition.

## The numbers, and how they were taken

All of these are from the run's own transcripts under `~/.claude/projects/`, and from
`docs/runs/*.json` in the project. None is an estimate.

| What | Value | How |
|---|---|---|
| a `ship` session's floor | **90.8k tokens** | first usage record of every child's transcript, identical across the run |
| context growth | **~2.25k per turn**, 8–31k per minute | (max − first) usage over turn count, sixteen sessions |
| what a session reads before its first edit | **33 turns / 140k chars** fresh, **21 / 65k** taking a handoff | first `Edit`/`Write` in each transcript |
| wrap-up after the ask | 3–8 minutes | `handoff-asked` → `handed-off` in the run logs |
| review findings per feature | 3–13, mean **6.4** | `review.findings` in each child's run file |

The floor breaks down roughly into a third harness (system prompt and tool definitions), a third kit
(`ship` at ~25k chars plus the rules at ~31k, so 18–20k tokens), and a third project (the knowledge
brief and three `CLAUDE.md` files). Trimming the kit's share would buy 5–7% of a session and cost
the rules that caught three defects in one night.

## The ceiling, and the parameter that was wrong

The handoff ceiling was 120k absolute. Against a 90k floor that left 30k of room — about five
minutes — and one feature was handed over eleven times in an hour without finishing. Worse than
never handing over at all.

The cost model: a turn re-sends the whole context and reads it from cache at a tenth of the price; a
handoff writes the floor into a cold cache at a quarter over and buys `o` turns of re-orientation.
Cost per useful turn is `(0.1·(n·F + g·n²/2) + 1.25·(F + g·n)) / (n − o)`.

`o` was **assumed at 7 and measured at 26**, which moved the cheapest segment from ~216k to **297k**.
The ceiling is 300k. Between 280k, 300k and 320k the money differs by half a percent; what settles
it is the tail after the ask, which lands ~20k past the ceiling — 320k rather than 340k, and further
from the 300–400k band where published long-context measurements put visible degradation.

Two ceilings sit above and neither binds: the harness compacts at ~83% of the window, and Claude
Opus 5's window is 1M by default. **A project on a 200k-window model must set `--ceiling 150`.**

Result on the run: handoffs went from eleven an hour to roughly one per 15–20 minutes, and review
findings did not get worse — the first feature built under the higher ceiling came back with 4
against the run's mean of 6.4.

## What the run refuted

- **Splitting a feature by the kind of its entries.** Shipped in 2.10.0, reverted in 2.10.2 an hour
  later: a feature of two homogeneous entries (an action and its screen) took three sessions,
  exactly as many as one of three mixed entries, while features with no entries at all took one or
  two. What correlates is the task count — 7 tasks → 4 sessions, 5 → 3, 4 → 2 — and tasks are
  written at Design, inside the session that then builds. There is no test worth keeping, and a
  split costs the new half a full 33-turn orientation.
- **Naming the worked-in files in the handoff note.** Shipped in 2.10.3 on the theory that part of a
  successor's 21 turns went to finding where the last one was. Measured after: 19 and 21 turns.
  Unchanged. The turns go to reading, not to searching. Kept because it is free; recorded here
  because it did not work.

## What the run confirmed

- **Sessions were reading their predecessor's raw transcript** — 38k characters of JSONL in one
  session, 23k in the next, the largest single read in each, to learn what the note says in two
  paragraphs. Forbidden in 2.10.4; three handoffs since with none.
- **A rule checked at the last moment is a rule that drifts.** `tasks` is shape-checked before every
  handoff and held all night; `assumptions`, checked only at `step: done`, drifted twice in two
  batches. Moved to every judgement of the file (2.10.6).
- **The hand-back session never closed itself.** The instruction sits at the end of a section, after
  the work is done. Moved into the driver, which knows the name from `parent` (2.10.0), with
  `nohup` making the kill safe — `setsid` was the first attempt and does not exist on macOS.
- **Recovery works.** An `API Error: 529 Overloaded` stopped a lens mid-run; the driver waited out
  its silence threshold, read the cause from the transcript's tail, typed one line, and the session
  finished four minutes later with its context intact.
- **A narrowed audit is honest if it says so.** `tests` and `scenarios` took the run's 24 entries as
  their area and reported arithmetic that adds up; `deps` and `security` took none, each writing its
  own reason. First run of 2.10.7's rule.

## What is still open

1. **A child with a `prompt` loads no skill, and so gets none of the shared rules.** The driver
   types the prompt verbatim; a feature child gets `/agent-kit:ship <dir>` and with it the skill and
   everything it references, while a compose or knowledge child gets prose. Observed: an English
   opening line where the rule asks for the project's language, and `suite` transliterated into
   Cyrillic. The narrow fix is in the driver, which types every prompt anyway: one appended line
   naming `rules/closing.md`. Not to invent a command per one-off shape, and not to trust the
   composing session to remember.
2. **`--brief` is called by two first-sessions in five.** The rest read `docs/knowledge/` piecemeal —
   one to five `Read`s plus greps. The risk is not turns but omission: the entry without the library
   map or the entries it names. Measure the piecemeal path's cost before spending a rule on it.
3. **Effort per child.** Thinking is 43–85k characters of a session, about a fifth, and it is `high`
   for everything. Writing 39 cards from a published list does not need what a scheduler change
   needs. `effort` would sit beside `model` in the run file — a quality trade, so the owner's to
   make.

## Where the evidence is

`docs/runs/2026-08-13-*.json` and `2026-08-14-*.json` in the project carry `spent` and, since
2.10.0, `per_feature` — the session count of each feature by slug, which is what an average hides:
a batch reporting 2.8 sessions per feature was one feature at five and two at two.
