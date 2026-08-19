# What the entries do not say, and what was actually done about it

Written 2026-08-19, from the run `2026-08-17-epic-next-version` on a live project. Two drafts of
this note proposed more than survived review, and the record of what was cut is the more useful
half — it is at the end.

## What one run measured

Thirty-one children. Between them, **73 assumptions** recorded in run files. **Thirty-seven** name
the entry they were taken against; the rest name none. Their words:

> «Запись называет цену поиска, но не называет этих чисел.»
> «Запись говорит „что считается долей, а что нет“, но самой доли не называет — ни числа, ни правила.»
> «Запись велит отвечать отказом, а не пустым списком, но кода не называет.»

Those are not decisions about how code is written in this codebase, which is what `ship` is for.
They are facts about the product that its description does not carry — and two of those three
reached the knowledge as blocks, which is the mechanism working.

**Fourteen of the 73 did.** That is this run's count of `[assumed …]` blocks under entries; the
knowledge holds fifteen open blocks in all, and fourteen are this run's. The rest stayed in run
files, and `.agent-kit/runs/` is gitignored by the kit's own instruction — it is working state, and
is meant to be.

## What already works, and had to be checked before proposing anything

The mechanism is nearly complete, and the first draft of this note proposed several things it
already does:

- `check.py --brief <entry>` prints the blocks with the entry, so every later run reads them without
  being told to — four under the most-decided entry on this project;
- `check.py --entries` prints every open block in full, and **`epic`'s gate already runs it** across
  the whole scope and settles them with the owner before the first batch starts. That section exists
  because a live run once left «fifty-one decisions taken without an owner shut in twenty-one built
  entries while the owner sat there»;
- `ship`'s preflight does the same for the entries it is about to touch, with `gate: owner`;
- the closers are `blueprint` — **or a build command with the owner present**, transcribing the
  answer they just gave. Both are in `rules/channels.md`;
- and when a feature closes, the driver reads `expensive` off its run file and tells the owner's
  window which decisions it took with nobody to ask — while the batch is still running, which is
  the only stretch in which they can act on it.

So the question is not *how does a gap get recorded* — it is recorded — but which gaps the rule
sends to the knowledge, and whether the field that rule runs on is answered at all.

## The defect that is certain

**The field the whole thing runs on is unanswered a third of the time.** `assumptions[].expensive`
is absent from **28 of the 73**, including every one of the seventeen in the `own-key` batch, four
of which say «дорого ошибиться» in their own prose. Two of those 28 answer it under a name nothing
reads — `cheap_to_reverse`.

That is not bookkeeping, and the defect is worse than an empty field looks. `Driver.costly` reads
the field when a child closes and tells the owner's window what it decided with nobody to ask — and
it **tests the field for truth**, so an absent one is indistinguishable there from `false`. A third
of that run's decisions were therefore declared cheap by nobody in particular, including four whose
own prose says they are expensive. The channel that reaches a phone on its own, while the night can
still be acted on, was silent for all of them.

The template asked for the field by example, and now documents it. No program ever asked. Now
`check.py` names each record that leaves it unanswered, by what the record says, whenever the run
file is judged — and says so when `assumptions` is not a list it can read at all, which it used to
pass over in silence.

**What that costs on a project that already exists**, measured against all 165 run directories on
the one this note is written from: 26 of them would be named, and two are batches. That matters
because `epic` reads any output about a batch as *it closed badly* and says so in the pull request —
there are no levels of finding in this kit yet, which is item 6 of `docs/planned.md`. Both are
batches whose closing session wrote a summary of its children's decisions into its own `assumptions`
— a field `sprint`'s closing reference never asks it to fill, in a shape (`{count, expensive,
where}`) that is not a record at all. The finding is correct in both, and the consequence is
heavier than the mistake. Nothing here softens it: the fix is one line in the run file, and the
alternative — a check that goes quiet for batches — is the shape this kit has paid for three times.

## The defect that is real and whose fix is not

Fifty-nine assumptions did not reach the knowledge. Not all of them should have: reading them one
by one, a large share are about the code and the harness — dependency pins, a snapshot window,
which module a helper sits in — and those belong exactly where they are. What is left is a genuine
loss of product decisions, and the obvious fix is to change the axis: write a block for anything
that changes what a person sees or what is stored, whatever it cost to reverse.

**That was drafted, and then withdrawn, for a reason worth writing down.** `blueprint`'s own
reference says: «Blocks are only left where being wrong is expensive… Without that filter the
documents silt up after one sprint.» The filter is not an oversight, it is a decision with a cost on
the other side of it — and the cost is paid on the hottest path in the kit, because `--brief` prints
every open block under an entry before every `ship`. One entry on this project already carries four.
Roughly doubling that, on every entry, on every build, is a change nobody has measured, and the
sentence that would justify it is not in any file.

It is also more than a wording change: the block's own shape ends «Expensive to get wrong — data
model | permissions | money | public contract», which a cheap decision cannot honestly fill; and
three other files compose their reports from the same four categories.

So the axis stands, and the question goes to the owner with its price rather than into a command.

## What was done instead

**A program.** `check.py` names an assumption whose `expensive` is unanswered, and says when the
field cannot be read at all. One check, and it retires a judgement nobody could see.

**The reviewer.** An assumption the run itself called expensive, with no block under its entry, is
a finding — the reviewer holds the run file and the entries at once, and nothing else in the kit
does. It points at the entry, and where the assumption names no entry it says that instead, because
the reviewer may not go reading entries it was not given.

**A template slot.** The frame child's block gains `Costs:` — a state or a distinction the entries
ask for that this ruling makes impossible, or `nothing`. It is in the shape rather than in a rule
because the shape is what a frame child copies, and because a fifth rule in that file would be paid
for by the other four.

That last one comes from the `own-key` batch, and the story is worth its line. The frame allowed the
batch one migration. Work 03 then recorded — correctly, and as a block — that two states its entry
asks the product to show could no longer be told apart. Work 04 read that block, said so in its own
first assumption, drew one screen for both states, and wrote the difference into
`docs/technical_debt.md`, where it still is. Nothing was hidden and nothing was lost: the product
question had simply been settled by a technical budget before anyone asked it, and by then the
budget was spent. `epic`'s gate holds every entry too and holds them earlier, but it settles prose,
not budgets: nobody there rules on how many migrations a batch gets. The frame child does, holding
the entries beside the code they meet in — and it is the only session that can still widen its own
ruling, which is what the slot asks it to consider rather than merely to announce.

## What was proposed and is not

**A completeness pass before the build** — read the entry, list what it does not say, decide it
before writing code. Withdrawn. The measurement does not support it and one piece of evidence argues
against it: **eight frame children have run on this project and all eight recorded zero
assumptions.** The frame is already a pre-build pass over every entry of a batch, by a session with
no code to write. Nobody ever asked it for this list, so that is not proof it cannot produce one —
but it is the closest thing to an experiment here, and it says the list does not appear merely
because somebody reads the entries early.

The other half: much of what those 73 record could not have been found early at all. The `own-key`
batch's sharpest finding — that validating a key by fetching the model catalogue accepts any string,
because the catalogue is public — came from calling the real gateway by hand, and the frame's own
ruling on that point was simply wrong until then. Code produces those. Reading does not.

**Judging completeness at `epic`'s gate.** Withdrawn for a different reason: the gate already prints
every open block across the scope and settles them with the owner. What it does not do is invent
gaps nobody has hit yet, and that is the same unsupported proposal one level up.

## The four answers, for each rule added

| | who writes | who reads | who may close it, and where | impossible without it |
|---|---|---|---|---|
| the `expensive` check | `check.py`, on every judgement of a run file | the session being judged | delete the check and its tests in one commit, when `Driver.costly` no longer reads the field | a decision taken with nobody to ask, declared cheap by an empty field and never reaching the owner's window |
| the reviewer's finding | `agents/reviewer.md`, per diff | the run that gets the review, and whoever reads it | delete the paragraph, in the commit that gives blocks another writer | an expensive decision recorded only in a directory that is not in the repository |
| `Costs:` in the frame block | the frame child, per batch | every feature of that batch; the reviewer, judging against `stack.md` | drop the slot from the shape in `frame.md`, with a line here saying why | a technical budget settling a product question two features later, with nobody in a position to see it |

## Left open — also on `docs/planned.md`

- **The axis, with its price.** Whether a product decision that is cheap to reverse should reach the
  knowledge, against the silting `blueprint`'s reference warns about and the `--brief` cost on every
  build. The owner's call, and it needs a measurement nobody has: what `--brief` costs today per
  entry, and what it would cost at double.
- **`--advance` reads no blocks.** It composes the next batch from run files alone, so a decision
  taken in the batch that just closed reaches the next one only through entries it never opens.
- **Whether `[frame …]` and `[assumed …]` should ever be one writing.** Different closers today.
- **Whether `check.py` can say anything mechanical about a thin entry.** Probably not: the judgement
  is about prose, and this kit's checks stop where prose starts. Kept here and not on `planned.md`:
  it is a question answered, not work waiting for a turn.
