# S6 — the knowledge, through the program

Written before building it, 22 August 2026, so that the next session starts from decisions
rather than from a blank page. S0–S5 are done: the package, the state, the step contract,
Claude Code at level B, one feature end to end, and a bench of fifteen traps that all fire.

The plan's own words: *The model returns fields, the driver writes the file and the mark.
The join the second version never made — an expensive assumption owes a block — becomes an
impossible state rather than an oversight. Done when a feature cannot be closed while an
expensive assumption has no block, and the bench has a trap proving it.*

The owner's answer, at the tail of the S5 note, settles the one thing that blocked this
step: **the second version's format, unchanged**, and **a new block carries an identifier**.
What the identifier looks like was left to this note. So is everything below it.

---

## 1 · What the format actually is, read rather than remembered

Measured again over `/projects/beeplish/docs/knowledge`, which is read-only to this session
and is the only real knowledge there is:

| | |
|---|---|
| files, lines | 8, 7 380 |
| blocks | 193 — 96 `frame`, 95 `assumed`, 1 `stale`, 1 `found` |
| blocks that are a markdown blockquote | 193 of 193 |
| distinct header shapes | **2** |
| `### …` records | 122, of which 102 carry a `` `key: …` `` line |
| files whose blocks hang off a heading instead | 3 — `product`, `scenarios`, `stack` |
| duplicate headings inside one file | 0 |
| block lines: median, p90, max width | 96, 101, 154 |

The two header shapes:

```
> **[assumed 2026-08-18 · claude/2026-08-17-own-key-01-key-storage]** …
> **[frame 2026-08-19 · 2026-08-19-teardown · pr: 29]** …
```

**Segments after the kind and the date are `·`-separated, and one of them already carries a
`key: value`.** That is the single most useful thing in the measurement, and it decides
section 2: the identifier does not need a new syntax, because the format already has one for
exactly this.

---

## 2 · The identifier

```
> **[assumed 2026-08-22 · kit/add-vat · id: k7f3q2]** …
```

**One more `·` segment, of a kind the format already writes.** A parser that reads today's
blocks reads tomorrow's; a reader who has never heard of the third version loses nothing.
Old blocks are not rewritten, `init` migrates nothing, and a block with no `id:` is simply
one the kit cannot address — which is what it already is.

**It is derived, not random.** `id = base32(sha256(slug · what))[:6]` over the alphabet
`23456789bcdfghjkmnpqrstvwxz` — digits and consonants, so six characters cannot spell
anything unfortunate. Three reasons, in order of weight:

1. **A bench case can name it.** A random identifier makes every judge assert whatever the
   kit happened to produce, which is a judge that cannot fail — the exact defect three
   reviewers found in S5 and the one this step must not reproduce.
2. **Writing twice is writing once.** An attempt that dies after editing the file and before
   recording it produces the same identifier next time, so the writer replaces its own block
   rather than laying a second one beside it. With a random identifier that recovery is a
   duplicate.
3. It is short enough to type into a commit message or say out loud.

Derived from the assumption's own words rather than its position, because the position in a
list is the thing most likely to move between attempts. Two assumptions of one run with
identical wording collide; the writer bumps the last character until the identifier is free
in that project's whole knowledge, and 27⁶ makes that rare enough not to design around.

**Only `assumed` is written by S6.** `frame` belongs to a batch and there is no batch until
S8; `found` belongs to a reviewer whose findings do not yet reach the knowledge; `stale`
belongs to whoever notices. Writing a kind with no writer is the mirror of writing a field
with no reader, and the kit refuses both. **`accepted` is dropped**, as the owner's answer
says: a template, a block and a closing rule, and no writer in the whole life of a project.

---

## 3 · The address: where a block goes

```
at = "entities.md#account"          a record with a key
at = "stack.md#Вызовы модели"       a prose file, addressed by its heading
```

`file#anchor`. The anchor is the record's `` `key:` `` where it has one, and the heading's
own text where it has not. The measurement above is what makes the second half safe: no file
in the real knowledge holds two headings of the same text.

**The address is resolved against the file, never trusted.** No such file, no such anchor,
or two anchors that match — the step is refused by name (`no-such-record`,
`ambiguous-record`). An address nobody resolved is a block that lands wherever the writer
guessed, and the point of an address is that somebody can find it again.

**The block goes at the end of the section it addresses** — after the last non-blank line
before the next heading of the same or a higher level, or the end of the file. Blank line
above it, `> ` on every line, wrapped at 100 characters, which is where the real knowledge
already sits.

---

## 4 · Who writes it: a step called `record`

A run becomes six steps: `design`, `build`, `verify`, `review`, **`record`**, `deliver`.

Not a part of `deliver`, and the reason is the plan's second question — *if an agent must do
it, what trace does it leave?* — turned on the kit itself. A step leaves an `output.json`
naming every block it wrote and every one it removed, and a run that never had the step is
visible in its own record. Folded into delivery, the same work leaves a line in a log.

**It is a program, not a role.** The model returns fields; the program writes the file. That
is the whole sentence the plan wrote for S6, and it is also what makes the join checkable:
an agent that writes the file itself can always claim it did.

**What it returns**, and every field has its reader:

| field | who reads it |
|---|---|
| `blocks` — `{id, at, what}` for each block written | `deliver`, to check the join; a person, to find the block |
| `closed` — the identifiers removed | the pull request's record half |
| `files` — the knowledge files it changed | `deliver`, which commits them beside the code |

**It runs before `deliver` and it asks the deliverable question first.** A blocking finding,
a red suite or an unfinished build must stop the run *before* anything is written into the
owner's knowledge, not after. So the three refusals that were `deliver`'s move into
`programs/deliverable.py` and both programs call it, with the same codes they already have.
One bench case changes owner because of this, and it is named in section 8.

---

## 5 · The join, and where exactly it refuses

*A feature cannot be closed while an expensive assumption has no block.* Two halves, and
they are not redundant:

**The contract half, at the design step.** An assumption record gains `block` — the prose
that goes into the knowledge — and `at` — where. They are **required when `expensive` is
true, and only in a project that keeps knowledge.** So the contract is not fixed for all
time: the driver asks the definition for the contract *this project* imposes, and renders
that same contract into the step's input. The agent is told in the form the program checks,
which is the only form the measurement says is obeyed.

Refused by name: `output-missing-field: assumptions[0].block`. The step gets its remaining
attempts with the reason enclosed, which is what the kit does everywhere else and costs one
session rather than one run.

**The program half, at `record`.** The project keeps knowledge, an expensive assumption
carries no block, and the run stops: `assumption-with-no-block`. It cannot fire while the
contract half stands, and that is the point — it is what survives a run assembled from
different steps, or a contract someone loosens later without noticing what it held.

**A project that keeps no knowledge owes nothing.** The join binds a project that has a
`docs/knowledge/`; it does not make one invent it, and it does not make the kit write into a
directory nobody asked for. The expensive assumptions still reach the owner: `deliver`
already prints them in the open half of the pull request, which is the channel that exists.

---

## 6 · Reading, which is not an instruction

`design` is the step that decides both halves of an address, so it is the step that must
know what the knowledge holds. It cannot be told to go and look — that is the prescribed
step with no trace the whole plan is written against.

**The driver encloses an index.** Every file with the first line of its own header comment;
every record as `file#anchor · its heading`; every block as `id · kind · date · run` with
its first line cut at 120 characters. For beeplish that is 8 files, 122 records and 193
blocks — the real size is measured after it is built and written down in the section this
note grows when the work lands.

Not the knowledge itself: 7 380 lines is a window, not an enclosure. The files are on disk
where the session is standing, exactly like the code, and the role's prose says so in the
one sentence it already spends on the code.

**The index is also what makes reading leave a trace.** An address is resolved against the
same files the index was built from, so a design that never looked cannot produce one that
resolves. That is the measured defect from the plan — *nothing noticed* — answered by a
program rather than by a reminder.

---

## 7 · Closing a block, and why the identifier has to pay for itself

The owner's answer gives two reasons for the identifier, and the second is closing: *closing
is deletion, and deletion needs an address.* An identifier built for a reason nothing
exercises is a field with no reader.

So `design` returns `closes` — a list of identifiers this feature makes untrue — and
`record` removes those blocks. Required, and an empty list is a real answer, like the four
lists S4 already writes. An identifier that is not in the knowledge is refused by name
(`no-such-block`) rather than passed over: the second version deleted 47 blocks across
thirty commits with nothing checking what was deleted.

A block with no `id:` — every block the second version ever wrote — cannot be closed by the
kit. That is stated in the index rather than hidden, and it is the honest cost of not
rewriting a line of anybody's knowledge.

---

## 8 · What changes in what already stands

| Where | What |
|---|---|
| `knowledge/` | new: read a project's knowledge, write a block, close one, build the index |
| `steps/contract.py` | a field may be required when a sibling is true; a contract can be asked for a stricter copy |
| `steps/registry.py` | `record`; `design` gains `block`, `at`, `closes`, and declares it needs the knowledge |
| `driver/runner.py` | the contract a project imposes; the knowledge index as an enclosure |
| `programs/deliverable.py` | new: the three refusals `deliver` held, now asked by `record` first |
| `programs/record.py` | new |
| `programs/deliver.py` | commits `record.files` beside `build.files`; refuses `assumption-with-no-block` |
| `project.py` | `knowledge = "docs/knowledge"`, with that default |
| `method/roles/design.md` | the two new fields, and what an address is |
| `bench/cases/` | four new cases; one existing case changes which step refuses it |

`a-review-that-disagrees-with-itself` expects `deliver = "failed"` today and will expect
`record = "failed"`: the disagreement is now caught before the knowledge is touched, which
is where it belongs. Nothing else about that case moves.

**Deliberately not built:** `docs/runs/<slug>.json`, which is the plan's durable batch
record and belongs to a step that has batches; a knowledge writer for `build` or `review`;
any migration of what the second version wrote, because the owner's answer says there is
nothing to migrate.

---

## 9 · Where this is proved

**On the bench, with knowledge of the real shape planted in the case's own overlay.** The
baseline stays what it is — a project with no knowledge — so the fifteen standing cases keep
measuring what they measure. Four new ones:

| Trap | The mechanism it must fire |
|---|---|
| an expensive assumption with no block, in a project that keeps knowledge | the design step is refused and the reason names the field |
| an address that resolves to no record | `record` refuses rather than writing where it guessed |
| `closes` naming an identifier the knowledge does not hold | `record` refuses rather than deleting nothing quietly |
| a run that goes green, in a project that keeps knowledge | the block is in the file, under the record it addressed, with its identifier, and in the commit |

Each judge proves its own trap sprang before it judges — the S5 lesson: the knowledge file
must be non-empty and must not already hold the block. Each mechanism is broken by hand
afterwards, and exactly one case must say so.

**And the sandbox baseline moves once, deliberately.** `kit-sandbox` holds no knowledge, so
it cannot answer for a step about knowledge, and the S5 rule that its `main` stays on its
first commit would freeze it out of every step from here on. It gains a `docs/knowledge/` of
the real shape, in one commit, and is frozen again there. Runs across that line are not
comparable with each other, and this sentence is the record of why.

`beeplish` is read for its format and never written to: the second version runs on it
nightly and is frozen.

---

## 10 · What S6 is done when

`agent-kit bench run` reports nineteen cases as fired; a design that gives an expensive
assumption no block cannot pass its step in a project that keeps knowledge; a block written
by the kit is in the owner's file, under the record it named, carrying an identifier that
the same run would produce again; and breaking any one of the four new mechanisms by hand
makes exactly one case say it did not.

---

# What was built, 22 August 2026

Six steps to a run now — `design`, `build`, `verify`, `review`, `record`, `deliver` —
nineteen bench cases all firing, and 434 tests. Everything decided above was built as
decided; what changed on the way is in the last section, and so is what was not built.

## The identifier, in the file

```
> **[assumed 2026-08-22 · kit/add-vat · id: k7f3q2]** Ничего не говорит, что ставка целая.
> Взял целую: дробная округлялась бы молча, а на эту ставку опирается расчёт цены.
```

Derived from the run's slug and the assumption's own words, over digits and consonants.
`identifier('add-vat', 'the rate is a whole percent')` is the same six characters on every
machine and in every attempt, which is what lets a bench judge ask the kit what the block's
name must be instead of accepting whatever it produced — the judge for
`a-block-that-reaches-the-knowledge` does exactly that.

An identifier that is already in the knowledge under a *different* run is stepped over
rather than overwritten. One under the same run is ours: the block is replaced, so an
attempt that died after editing the file writes the same block again instead of a second
one beside it.

## What the enclosure costs, measured

Over the real knowledge of `beeplish`, read and not written:

| | |
|---|---|
| the knowledge | 8 files, 7 380 lines, 868 KB |
| the index the driver encloses | 377 lines, **47 KB** |
| addressable records | 155 |
| blocks listed, of which addressable | 193, of which 0 |

Five and a half per cent of the knowledge, and it does not grow when a record's body does:
a record reaches the index by its address and its heading, a block by its first 120
characters. Two things were cut after the first measurement, which was 50 KB: a block's
glimpse repeated the header the index already prints as columns, and a file's own `#`
title was an address — a block "under `# Сущности`" is a block anywhere in the file.

`0 of 193` addressable is the honest number and it is not a defect: every block standing in
`beeplish` today was written by the second version, and the identifier is additive. The
index says so in its own last line rather than leaving it to be discovered.

## Three things the code had to learn, and each is a defect found by reading it

1. **Fenced code is not prose.** A `### Пример` inside a ```` ``` ```` block became an
   address, and a quoted block inside one became a block. The real knowledge has neither
   today — which is exactly how this class of defect waits. Both readers and the section
   boundary ask `outside_fences` before believing a line.
2. **A file that cannot be read is a named refusal.** `unreadable-knowledge`, not a stack
   trace and an exit code of 70. The knowledge is the owner's and is edited by hand.
3. **Every address resolves before anything is written.** Two expensive assumptions with a
   bad address on the second used to leave the first block on disk under a run that failed.
   A half-written knowledge is worse than an unwritten one, and the same is true of closing.

## Breaking it by hand, as the rule says

Four mechanisms, one at a time, each reverted before the next:

| What was broken | What said so |
|---|---|
| the project no longer makes the design's contract stricter | `an-expensive-assumption-with-no-block` |
| an address that resolves to nothing lands on the first record instead | `an-address-that-names-no-record` |
| closing an identifier nobody holds passes quietly | `closing-a-block-that-is-not-there` |
| the knowledge is written and left out of the commit | `a-block-that-reaches-the-knowledge` |

Each pointed at one case and no others. And, as the S5 review taught, the judges were asked
whether they are armed rather than merely green: take the planted knowledge away and all
four must go quiet, and the green case's judge is asked while the run still goes green —
it answers *"no knowledge was planted at all"* rather than passing.

The bench was also run from `git archive HEAD` unpacked elsewhere, which is the check
nobody thinks to do and the one that caught S5's blocker. Nineteen of nineteen there too.

## What changed on the way, against the note above

**`closes` is required by the project, not by the kit.** The note said required with an
empty list as a real answer. It is — in a project that keeps knowledge. Making it
unconditional would have asked fifteen standing bench cases to answer a question about a
knowledge their projects do not have, which is a field with no reader wearing a convention's
clothes.

**Only one standing case changed owner, not three.** The deliverable question moving in
front of the knowledge touches `a-review-that-disagrees-with-itself`, whose `deliver`
becomes `record`. `a-blocking-finding`, `a-red-test-command` and `a-command-that-hangs`
declare no step, because a run that *stops* parks its step back to pending — so they were
already written in the only way that survives this.

**A design that omits both `block` and `at` is refused for the address.** The fields are
checked in the order the contract declares them, and the address is declared first. The
case that proves the join therefore supplies `at` and withholds `block`, which is the
sharper trap anyway: it isolates the field the rule is named for.

## What is still open

**The knowledge a failed run wrote stays in the working copy.** `record` writes, and a
later `deliver` refusal — a branch that is somebody else's, a file the build named and
never wrote — leaves those edits uncommitted beside the code the build wrote. It is no
worse than what the kit already does with code, and it is the same shape: there is no
rollback in the kit, and inventing one for the knowledge alone would be inventing it in the
wrong place.

**The sandbox baseline has not moved.** Section 9 decided it should, once and deliberately,
and it has not been done: `kit-sandbox` is another repository and moving its `main` is the
kind of act that is the owner's to approve rather than a side effect of this step. S6 is
proved on the bench, which is what its done-condition names. The move is the first thing to
do before the next live run.

**No `full` case, still.** Every one of the nineteen answers from `providers/fake/`. A case
that drives a real provider needs the runner to stop passing `--provider fake`
unconditionally, which S5 already wrote down and S9 still owns.
