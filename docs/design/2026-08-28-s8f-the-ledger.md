# S8f — the ledger, and the two kinds of block that stay unwritten

Written after building it, 28 August 2026. The sixth of the seven recovered steps, and the one
where a measurement changed the shape of the answer twice.

The plan's words:

> **S8f · The kinds of block that have no writer, and the ledger.** S6 wrote that the kit writes
> `assumed` alone and named who the others were waiting for. Two are still waiting: **`found`** —
> a review's findings reach the knowledge not at all; **`stale`** — nobody marks a sentence of the
> description untrue when a feature makes it so; and **the ledger**, without which the three
> destinations of S8a are two.
>
> *Done when* a review's finding reaches the knowledge with an identifier, a feature that outdates
> a sentence marks it where it stands, the ledger has a writer and a reader, and each of the three
> has a trap.

## 1 · The cut: the ledger entire, and neither kind of block

**Built:** the ledger with all three ends — a reader, a second writer, a closer, and its traps.
**Not built:** the `found` kind, the `stale` kind, a rung on the door, a sitting that closes lines.

The first argument offered for this was a snapshot — *one `found` block against 110 ledger lines* —
and the review measured it properly and found it wrong. Over the second version's whole life
`found` was written **12 times and removed 11**, `stale` **46 and 44**. Both kinds had a writer and
a closer, and both worked. A note built on a misquoted measurement is an assertion instead of a
trace, and the argument had to be replaced rather than patched.

The real argument is stronger. **Eleven of the twelve `found` blocks were written by lens runs**,
and their content is a complaint about a *record of the knowledge* — which has an address. A
feature review's finding has `where`: a path and a line in the code, which the knowledge does not
hold, so an address would have to be invented. And the lens's output already goes somewhere on
purpose: S8c writes it into a report and a candidate list. So `found`'s content reaches the owner
as a ledger line, which is a form with a key and a closer, and that is where the second version
sent it too — 110 lines against 12 blocks.

**`stale` is not built because its closer was never a program.** All 44 removals were human commits
closing a batch by hand. The kit's rule after S8b is that a kind with a writer and no closer grows
the knowledge index by a line per block for ever, and that index is enclosed in every `design`.
The shape is named for whoever takes it up: the writer is `design.outdates`, the address is a
part's key from the enclosed index (a white list, and `no-such-part` already exists), and **the
first half of the block — what the part says today — is printed by the program from the line it
already holds**, so the session can only supply the second half. That removes inventing *which
sentence*; it does not remove inventing *that it is untrue*, and nothing can.

## 2 · The measurement that decided the writer

The proposal made `record` the ledger's second writer: each feature appends its findings. I refused
to let that be built before it was measured, because every feature of a batch would be writing into
the same insertion point.

**200 conflicts out of 200.** Two siblings branching from one base, each appending a line after the
same last line: `MERGED kit/rates`, then `CONFLICT kit/quote — docs/knowledge/debt.md`. Three
features: one merges, two conflict. The night is green throughout, and the owner meets the conflict
only at the end of the batch, in a file no feature was about.

Moving the insertion point does not help. Appending at the top of the section: 200/200. Inserting in
key order into a sorted section: 65% at one standing line, 24% at six, 7% at forty, 2% at a hundred
and ten. **That is worse than the deterministic conflict** — it turns "always" into "sometimes",
which is a flickering night nobody can reproduce or explain, and it also means rewriting lines the
owner wrote by hand.

So the writer changed: **the batch lays the ledger, not the feature.** The precedent is the kit's
own — `_close_the_frames` already writes into the owner's checkout once, at the point where there
is nothing left to build, and never fails a night. The child records its lines in its own
`output.json`; the batch collects them in one move, at the same two points where it closes the
frames. The cause is removed rather than softened, which is the owner's measure.

Nothing below the batch learned the word *batch*: `write_debt` has exactly two callers, the sitting
and the batch driver, and the child only ever names keys.

**The cost, stated plainly rather than buried:** a run started by hand never writes to the ledger.
Its findings stay in the pull request, as they do today. The plan's bullet is therefore paid for
the night the kit was written for, and not for the run a person starts and reads themselves. The
report says so in both halves, in the kit's own words.

## 3 · The divergence a review caught, and why it mattered only after variant C

`record` measured the ledger against **the run's own worktree** while the index `design` reads is
built from **the owner's checkout**. Before the writer changed, the two agreed: blocks were written
into the tree and `deliver` committed them. **Nobody commits the ledger** — the kit prints the paths
and the owner reads the diff — so under variant C the divergence became permanent.

The move that breaks: a night lays a line into the owner's checkout, uncommitted; the owner does not
commit; the next night's `design` sees the line in its enclosed index and legitimately names it in
`fixes` — and the run dies at `record` with `no-such-debt`, after `design`, `build`, `verify` and
`review` have all been paid for. The ledger's authority is the owner's checkout, and it is asked
there now. The case that proves it plants the line *after* the world's first commit and proves, in
two checks, that no commit anywhere holds it — otherwise the trap would be measuring nothing.

## 4 · The join, which had to be asked for twice

`record.debt` and `record.fixed` were fields whose only reader was a printer — the exact defect the
plan spends a paragraph on when it ends S8e by deleting `design.verification`. The mirror of
`_refuse_a_naked_assumption` was decided in the first round and simply was not built; the review
found it by grep, and it is worth writing down that the round in which a decision is *accepted in
the report* is not the round in which it is *in the code*.

It is there now: every `worth-fixing` in a review owes a line (`finding-with-no-line`), every key in
`design.fixes` owes a record (`fix-with-no-line`), **counted rather than gathered into a set** —
which is what S6 spent a blocking finding on, when one block answered for two identically worded
assumptions.

Two findings worded alike therefore owe two lines, through the same walk of the salt that `free_id`
already does for blocks. Across two *features* of one evening the same words collapse to one line,
and that is deliberate and now said out loud to the owner: a reviewer who said it twice about one
feature said it twice; two features that each said it once said it once.

## 5 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1177 | **1226** |
| `make bench` | 121 of 121 | **127 of 127** |
| `make armed` | 116 + 5 in words | **122 + 5 in words** |

Six traps added. The bench also ran 127 of 127 from `git archive HEAD` unpacked elsewhere, and all
seventeen commits import every module of the package.

**And the flake from S8e's note is explained.** Two bench tests were given a ceiling of their own
(1800 seconds) because 127 worlds in one process no longer fit inside the shared 300. That is
exactly the cause pinned in S8e's note — `a-tree-in-the-way-of-one-feature` answering *could not be
checked* under load — found from the other end, by the suite growing rather than by chasing it.

## 6 · Breaking it by hand

Six breaks across two rounds, each of a **branch** rather than a function, each reverted before the
next; exactly one case reddened each time:

| broken | what said so |
|---|---|
| the evening lays no new line | `a-finding-that-outlives-its-report` |
| the index carries no ledger section | `the-debt-a-design-is-given` |
| the evening closes nothing it was told to | `a-debt-line-the-work-closes` |
| a key is not checked against the ledger | `a-debt-line-nobody-wrote` |
| `record` asks its own tree about the ledger | `a-line-the-owner-has-not-committed` |
| a feature that did not land still lays lines | `a-finding-of-a-feature-that-did-not-land` |

## 7 · What is held by words, not by a trap

- **The join has no trap and cannot have one.** It fires only when `record` names fewer lines than
  the review found — and `record` is a program. The bench's fake provider answers for sessions, not
  for programs, so there is no world in which a program lies. This is the same shape S6 left to
  tests for the program half of `_refuse_a_naked_assumption`. Four tests hold it.
- **Idempotence across a second `batch go`** — the bench drives one `batch go` per case.
- **`two-lines-one-key`** — a ledger broken by hand — and `no-free-identifier`, unreachable.
- **A known brittleness, not fixed:** the section is chosen by `kind` when a line is written;
  rename the heading by hand and the next write starts the section again. The reader does not read
  headings at all, so no line is lost.
- **Nothing was driven by a live model.**

## 8 · Found while measuring, and deliberately not fixed

**Two `assumed` blocks addressed to the same record conflict exactly as ledger lines would.**
Measured with the real writer: two features of one batch, both addressing `entities.md#tax` →
`MERGED kit/rates`, `CONFLICT kit/quote — docs/knowledge/entities.md`. The standing case
`two-blocks-each-on-its-own-branch` is silent about it because it deliberately addresses two
*different* records, and its judge only ever asserts that a branch does not carry the other's block
— true in both worlds.

This defect is older than S8f and outside its cut, so it was recorded rather than fixed, and no trap
was planted for it. What softens it: `check_merges` at the end of a batch names the pair and the
file, so the owner is told rather than handed a green night. What is missing is a trap that would
notice if that stopped being true.

## 9 · Where the plan was wrong

1. **`found` and the ledger are one destination, not two** — for the reason in §1, and the measured
   numbers are 12/11 and 46/44 rather than the snapshot first quoted.
2. **"The ledger has a writer and a reader" is one end short of the kit's own rules.** After S8b a
   kind needs a closer too, and the second version measured exactly that defect: a line whose named
   closer never deleted lines outlived the work that answered it.
3. **`stale` is described as a form, not as a proof.** The plan names neither a writer with evidence
   nor a closer; in the second version the closer was a human commit, which is what makes the kind
   look healthy in a count and unbuildable in a program.
4. **The feature cannot be the ledger's writer**, which the plan could not have known — it is a
   measurement, 200 out of 200. The honest form of its bullet is not *a finding reaches the
   knowledge* but *a finding reaches the knowledge on the night a batch composed it*.
5. **The ledger's path.** The plan puts it at `docs/technical_debt.md`, outside the knowledge
   directory; S8a had already moved it inside, and this step is what makes that move pay — the
   index now carries the ledger's **lines**, which is what the corrected sentence in S8a's note
   promised and what, until tonight, was not true.
