# S8b — the evening composed with the owner

Written after building it, 27 August 2026, like the note for S8a and for the same reason: S8b
has no section in the plan of 22 August, only the bullets the missed-layer section added on the
26th. The decisions were taken while building; this is where they are written down.

The plan's own words:

> **S8b · An evening composed with the owner.** What `batch new <file>` does today, done in
> front of somebody. Two things a child cannot supply: the whole batch is visible at once, and
> the owner is here.
>
> *Done when* a batch can be composed without anybody writing TOML by hand; the graph it
> produces is the shape `batch new` already accepts; a `frame` block reaches the knowledge with
> a named writer; and a bench trap proves the gate refuses an unanswered kind rather than
> starting the night anyway.

## 1 · One shape, two sittings

`agent-kit batch compose <name>` is the sitting S8a built, reading something else and writing
something else. The owner tells what is being built tonight; the kit numbers the telling and
puts it on disk before anything is asked; one headless turn returns the graph of features, the
MVP bounds, the scenarios and the frames; the program runs the **gate** and puts to the person
standing here exactly what the gate did not get an answer to; a second turn settles what was
answered; the program writes the declaration and one `frame` block per frame.

What is genuinely shared moved to `sitting/room.py` and nothing more: the names of the room and
its files, where the papers go, the name of today's sitting, the lease of the working copy with
its reason (so the machine's page says `batch compose` when that is what is running), the
telling on disk before the first question, the attempt with its two refusals, the one round of
questions, and the answer that only ever comes from a terminal. What each sitting keeps for
itself: what it reads, what it prints, what it writes.

The heavy part — the slot, the growing pause, the fallback provider, the refusal enclosed in
the next input — was already extracted by S8a into `driver/session.py`. Parameterising the
whole of `Sitting` was proposed and refused: the ten traps of S8a hang off that path, and a
class that grows a stage for one caller and skips it for the other is two shapes wearing one
name.

## 2 · The gate, and what it may honestly stand on tonight

One function, `batch/gate.py`, with two callers. In `compose` each unanswered item becomes a
question for the person who is here — that is the whole point of the hour, since the night has
nobody to ask. In `batch new` the first unanswered item is a refusal. The round is one: the
gate runs before the questions and again after the second turn, and the second time it refuses
rather than asks.

It stands on three things:

- **the MVP bounds** — `bounds-unwritten`;
- **an ending for every scenario** — `scenario-with-no-ending`, and `no-scenarios` for none at
  all;
- **at least one declared command** — and here the important decision: **no new code was
  invented**. The proposal wanted `kind-unanswered: suite` over a catalogue of exactly one kind.
  That is `no-commands` — the code `verify` already raises — moved earlier in time, with a
  parameter that has one value. A refusal that duplicates a neighbour is a mechanism nobody
  needs, so the gate raises `no-commands` and `verification/kinds.py` was not written.

**The catalogue of kinds of verification is S8e's, and it is not here.** The plan's *done when*
says a trap proves the gate refuses an unanswered kind; tonight the kit knows one kind, and its
answer is `[commands]`. The trap measures the gate, not the length of the catalogue, which is
why it will survive S8e. This is the seam, written in words rather than half-built.

**The gate stands where the batch is created, not where it starts.** The plan says a batch does
not *start*; a refusal at `batch go` would leave a batch on disk that can never begin. Order
inside `batch new` is gate → batch → file, and a refusal creates no batch, no run, no tree and
no block.

## 3 · The frame, measured before it was designed

The plan says `frame` was S6's promise to S8 and that S8 did not keep it. What the live
knowledge actually holds, measured rather than remembered: **99 `frame` blocks in `beeplish`,
all in `stack.md`, all appended at the tail under whichever heading happened to be last, all
carrying `pr: 29`, stamped with fifteen different feature slugs.** So in the second version the
frame was written by a *feature*, had no address at all, and there were about seven of them per
feature. Above them, in the owner's own hand, a comment: twenty-three frames of two earlier
packs were folded into prose by hand after the merge — *what survives its pack stayed, the
choreography of particular work was thrown away*.

That measurement decided three things.

**The writer is the sitting, and only the sitting.** One evening sees the whole batch at once,
which is what a frame is *about*. A declaration written by hand still gets its frames into the
features' inputs and gets no block in the knowledge — the block has a writer or it has none.

**The address is real.** `file.md#record`, resolved against the file, refused by name when it
names nothing. Appending to the tail of a file is exactly what an address exists against, and
the measurement shows what the alternative produced.

**It has a closer, and that was the hardest call of the step.** The proposal wanted to leave
closing to S8d or S8f. I refused: the plan's own measurement gives the frame a median life of
one day, and a kind with a writer and no closer grows the knowledge index by a line per frame
for ever — and that index is enclosed in every `design`. So the batch closes the frames it
wrote, when there is nothing left to build, and only those whose header carries its own name. A
run still cannot close one: `record` refuses by kind, and `a-frame-a-run-tries-to-close` stayed
green through the whole step.

**How it reaches a feature.** Through `Run.frame`, enclosed by `driver/compose.py`. Not through
the knowledge: 99 standing frames of one batch would land in every later run, and a run started
by hand would read the choreography of work it has nothing to do with. The run learns the word
*frame*, the way it learned *base* and *needs*; it never learns the word *batch*.

## 4 · Four ways the frame could still end badly, found by review after it was built

All four were found by reading the finished diff, and all four are the reason this step took a
second round:

1. **Two codes for one error, one of them unreachable.** The contract made `frames.at` required
   *and* the judge refused `no-address`; the contract is checked first, so `no-address` could
   never fire. The test admitted it — `assert "output-missing-field" in ... or "no-address" in
   ...` — and a test that cannot say which mechanism fired measures neither. One enforcer left:
   the judge.
2. **An address that resolves at nothing killed the sitting after two paid turns**, because
   `resolve` was called by the writer, outside the attempt. It is resolved in the judge now and
   mends itself on the next attempt, like every other refusal in the kit.
3. **Orphans.** Composed a second time with different wording, a frame derives a different
   identifier; `write` replaces only its own, so the first block would stand for ever while the
   declaration already names the new one. The sitting now takes away the frames of its own
   evening that it has stopped naming.
4. **Closing had exactly one attempt.** It ran after the batch's `try/finally`, and `go` refuses
   `batch-finished` on the way in — so an exception, a killed process or an unreadable knowledge
   left the frames standing with no way back. It runs on the way *into* `go` as well now, and it
   is idempotent.

## 5 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 962 | **1019** |
| `make bench` | 89 of 89 | **93 of 93** |
| `make armed` | 86 + 3 in words | **89 + 4 in words** |

Run by me after the work landed, and the bench also from `git archive HEAD` unpacked elsewhere.
Every one of the nine commits was checked to import and answer `--help`, which is the check the
previous step had to rewrite its history for.

## 6 · Breaking it by hand

| broken | what said so |
|---|---|
| the gate reads the project's commands | `a-night-with-nothing-to-check-it-with` |
| the frame reaches the composed input of a step | `a-frame-every-feature-is-built-alike-on` |
| the batch hands frames to its children | `a-frame-every-feature-is-built-alike-on` |
| the sitting writes the frame's block | `a-frame-that-reaches-the-knowledge` |
| the evening closes the frames it wrote | `a-frame-the-evening-closes` |
| a run may close a frame | `a-frame-a-run-tries-to-close` (stood, stayed green) |

Two breaks redden the same case, and that is honest: who puts the frame into the input and who
hands it down are one mechanism from two sides.

One break — the block landing at the end of the record it names — reddens **six** cases, five of
them S6's. That is one mechanism seen from six sides, every one of them a writer of a block.
`a-frame-that-reaches-the-knowledge` only joined that six *after* the fix: until the bench's
baseline world gained a second heading, its check "under the record it named" was green for a
block anywhere in the file. A tautology that a review caught and a break confirmed.

## 7 · What is held by tests, not by a trap

Written down rather than counted as proved:

| mechanism | why not a trap |
|---|---|
| the sitting sweeping away the frames it no longer names | the bench drives one sitting per case; a second composing is a second command with its own replies, and a judge that plants its own `replies/` is a trap `disarm` cannot take away — which is to say, not a trap |
| `bounds-unwritten`, `scenario-with-no-ending` at `batch new` | the bench's declarations are written by its runner, and no third way of driving was added; a case declaring an evening with no bounds would declare what the composing contract makes impossible |
| the migrations of both schemas (run 4 → 5, batch 1 → 2) | the bench runs one version of the kit |
| `still-asking`, `not-its-block`, `claimed` for two frames worded alike | reachable only through states the bench cannot plant in one run |
| `checkout-held-elsewhere` from `batch compose` | not a new mechanism — a second caller of an old one |

`a-frame-every-feature-is-built-alike-on` carries `no_disarm` in words: the frame *is* the
case's own declaration, and an evening with no frame is a different case.

## 8 · What no trap catches

The same honest half as every step of this layer: everything answers from `providers/fake/`.
That a real model composes a graph whose edges are really edges, and bounds that are really
bounds, is measured by nothing. The first live composing is where that gets measured, and it
has not been run.

And one thing this step leaves standing on purpose: **until `batch new` is typed, nothing closes
a frame.** Compose an evening, never create the batch, and the blocks stay in the owner's
knowledge. The sitting sweeps its own evening's orphans; it cannot sweep an evening the owner
simply abandoned, because a batch that was never created has no record saying it is over.

## 9 · Where the plan was wrong

- **"The gate is the only place that stops anything" is already untrue.** The driver's preflight
  stops a run twice before the first session — a command that starts nothing, and a project with
  no description. Read as *the only place S8b adds*, and the gate calls the same `starts_nothing`
  rather than writing a second check.
- **"The bounds and the scenarios are filled here" does not say where.** They are filled into the
  declaration, which the plan itself calls the artefact. The kit does not write them into the
  knowledge: that would give the owner's description a second writer with no key and no closer.
  This is a narrowing of the plan's words, said out loud rather than worked around.
- **On `frame` the plan describes a step forward, not a restoration.** The measurement above is
  why: what the second version wrote was a feature's note with no address, seven per feature.
  What S8b writes is one evening's, addressed, closed by the batch that wrote it.

## 10 · What was deliberately not built

The catalogue of kinds of verification and a feature's record per kind (S8e); the bounds and the
scenarios written back into the knowledge; a frame per feature; a second round of questions;
a `batch compose` that also creates the batch — one door to the graph stays `batch new`; the
candidate list an audit would compose from (S8c, and the place for it is named, not filled).
