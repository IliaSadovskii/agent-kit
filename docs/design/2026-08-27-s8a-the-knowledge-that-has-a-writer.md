# S8a — the knowledge that has a writer

Written after building it, 27 August 2026, unlike the notes for S5–S8: those were written the
evening before, from a plan that had a section for the step. S8a has no such section — it is
one of the seven steps the plan of 22 August discovered it was missing four days later, and
the section it does have is three hundred words of bullets. So the decisions were taken while
building, and this note is where they are written down rather than where they were made.

The plan's own words:

> **S8a · The knowledge that has a writer.** An interactive session, and the only shape that
> fits what it does: the owner talks, at any length and in any order, and nothing about that is
> sorted for them.
>
> *Done when* a repository with no `docs/knowledge/` ends one sitting with a description the
> design step can read; every record is traceable to a line the owner said or is marked
> `derived`; the same telling run twice rewrites rather than duplicates; and a bench trap proves
> that a project with no description is refused by name rather than passed in silence.

Until tonight the knowledge had a reader and half a writer. `design` is handed an index of it;
`record` appends `assumed` blocks to it. Nothing in the third version could put the product's
own description there, and the second version's answer to that — a session that interviewed the
owner and wrote the files itself — is the shape this kit exists against.

---

## 1 · Who holds the loop, and the three shapes that were refused

**The kit holds it.** `agent-kit knowledge tell` reads the telling from a file (or `$EDITOR`,
the way `git commit` does), numbers it, writes it down verbatim before anything else happens,
and then runs two ordinary headless turns through the same `providers/` every step of a run
uses. Between them the program prints the reading and asks the contradictions, reading the
answers from the terminal. The files are written by `sitting/write.py`.

**Not a provider CLI attached to a terminal.** Three reasons, and any one of them is enough.
The adapter contract is one input and one answer; an attached terminal is a new provider level,
which is S9. The owner's words would reach the model down a channel the kit cannot see — no
`raw.txt`, no contract, no way to check that a line was ever said. And the bench cannot drive an
attached terminal, so the shape would ship with no trap, which the project's rules forbid
outright.

**Not a sitting shaped like a run.** It has no branch, no worktree, no pull request and no
sequence of the method. Putting it in `run.json` would teach the word *sitting* to `deliver`,
to `tree`, to `pre-push` and to the batch. It reuses the parts — the contract, the composed
input, the provider registry, the workspace, the slot, `Knowledge` — and none of the shell.
This is the same test S8 applied to the shape of a batch: if something below had to learn the
word, the form is wrong.

**Not an interview.** The plan says the questions walk the parts of the product, and it also
says only contradictions are asked. On a project where nothing is written down there is nothing
to contradict, so a first sitting asks *nothing at all* and writes everything from what was
said. The parts of the product are the shape of the reading, not a route of questions. An
interview is a second, third and fourth round — a conversation, and every handover in this kit
is a file.

## 2 · What a program can check about an hour of somebody's speech

Three things, and they are the whole of S8a's honesty.

**Traceability is a removed possibility, not a check.** `said` is a range of lines — `L12-L14` —
in a telling the kit numbered and stored before it asked anything. The first form tried was the
verbatim slice: the row must quote the telling word for word. That is a check, and a fragile
one — a line break, «ёлочки» against straight quotes, a dash, a `ё`, or a part assembled from
two places forty minutes apart, and three honest attempts burn on punctuation. A range is
arithmetic. There is nothing to normalise and no way to point at words nobody said.

**The reading is complete, and the program counts it.** Every standing part gets a row,
including the ones that did not move. The cheap way to look thorough is to read a third of the
records and name three differences confidently; a row per part is what a third of the reading
cannot produce. `reading-misses-a-part` names the part that was missing.

**The denominator is printed.** The sitting reads parts, not every record: on the one live
knowledge there are fifteen parts and about a hundred and forty other records. `сверено частей:
N; записей вне частей не читалось: M` is one line, and without it the counters read as *your
whole knowledge*, which they are not.

## 3 · Three states, not two

`keeps_knowledge` used to sniff the filesystem: a directory exists, so the project keeps
knowledge. That sniffing *was* the silence. It is also what made the third version ask least of
the project it knows least about — `design`'s contract is stricter where knowledge exists, so a
project with none owed nothing and was never told.

- **Described** — at least one addressable record stands in the declared directory.
- **Not describing itself, said out loud** — `knowledge = ""`, typed by a person into a file
  that lives in git. `agent-kit init` never writes it: choosing silence on the owner's behalf is
  the defect, not the cure.
- **Silence** — refused. `no-description`, exit code 2, before the first session, and only for a
  run whose method includes `design`, its one reader. One code and three doors: `agent-kit
  init`, `agent-kit knowledge tell`, `knowledge = ""`.

The empty value is a state and not a path. `Path(root) / ""` is the working copy itself, so a
project that declares no knowledge would have had the kit reading its `README.md` as knowledge.

**What "described" counts, and what it deliberately does not.** The ledger — `debt.md` — is
made of headings, and a heading is an addressable record like any other. Counted, an hour spent
entirely on complaints would leave a project the gate calls described and nobody described. So
`described` counts records outside the ledger. Naming that file in the check is allowed because
`debt.md` is the kit's own name, not a word in the project's language.

## 4 · Where the plan was wrong, and where my own instruction was

**The ledger's path.** The plan puts it at `docs/technical_debt.md`, outside the knowledge
directory — where it has no index, no anchors, no parser and therefore no reader at all until
S8f builds one. It is at `<knowledge>/debt.md`, which puts it into the index for free: every
`design` from tonight sees the *works, but badly* lines. S8f can rename it in one line.

**"A line per record" is a line per part.** The reason behind the plan's bullet — a third of
the reading is the cheap way to look thorough — survives the narrowing, because completeness is
measured over the set the sitting actually writes. The rest of the knowledge is named in the
denominator rather than silently skipped.

**Three destinations are two files.** *Works badly* and *does not work at all* are one field,
`kind`, choosing a section. Three numbers are said out loud; two files are written.

**Mine, and it cost twenty-two tests.** I wrote that a project with no `project.toml` refuses
"as it does today". It did not: such a run worked. The preflight now reads the project rather
than requiring it, and all three shapes of silence — no declaration, no knowledge, an
undescribed directory — get the same code and the same three doors. That is better than what I
asked for, and it is a behaviour change outside S8a's section, recorded here rather than
discovered later.

## 5 · The form of a part, and why nothing is migrated

A part of the product stays what the second version made it: a list item under `## Части`,
with a mark at the end.

```
- вход — Google, Apple и почта — `key: sign-in` · `walked: 2026-08-27`
```

The key is one more `·` segment of a kind the line already carries — the same move S6 made when
it gave a block `id: k7f3q2`. The first form proposed was a `### heading` record per part, which
the parser already addresses; it was refused because the fifteen parts of the live knowledge are
list items, and writing records beside them means a second format standing next to the first
and a migration nobody asked for. The rule this project already keeps is that no old line is
rewritten.

A part is found **by its mark**, not by the heading above it: `## Части` is one project's word,
and a reader that looks at it goes blind the day somebody renames it.

The key is derived from the part's name, so a bench judge can ask the kit what it must be
instead of asserting whatever came out. It is written into the line when the kit writes the
part — deriving it afresh every time would read a renamed part as a new one, which is the
duplication S8a exists to prevent.

## 6 · What was built

| Where | What |
|---|---|
| `driver/session.py` | the attempt chain — the slot, the growing pause, the fallback provider, the last refusal enclosed in the next input, the attempt's papers — extracted whole, used by the run driver and the sitting alike |
| `sitting/` | the telling, the two turns, the questions, the writer |
| `knowledge/parts.py` | a part is a list item with a mark; a key that finds it again |
| `knowledge/store.py` | `parts`, `part`, `described`, `blocks_beside` |
| `project.py` | `knowledge = ""` as a state; `init` writes the default |
| `driver/runner.py` | the preflight refusal, beside the one for a command nothing can start |
| `method/roles/` | `reading.md`, `settling.md` |
| `bench/` | a case may drive a sitting; ten new traps |
| `errors.py` | what exit code 8 means in a sitting, in words, beside what it means at night |

The chain lives in one place, and that was the largest risk in the step: a second copy of the
mechanism the bench has a dozen traps for would have had none of them.

## 7 · The numbers, measured rather than reported

| | before | after |
|---|---|---|
| `make test` | 894 | **962** |
| `make bench` | 79 of 79 | **89 of 89** |
| `make armed` | 76 + 3 in words | **86 + 3 in words** |

All three were run by hand after the work landed, not read out of a report. The bench was also
run from `git archive HEAD` unpacked elsewhere — the check that caught S5's blocker, and the one
`.gitignore` has eaten trap files under before.

## 8 · Breaking it by hand

Ten mechanisms, one at a time, each reverted before the next. Exactly one case reddened each
time:

| broken | which case said so |
|---|---|
| the `no-description` gate always passes | `a-project-that-was-never-described` |
| `described` counts the ledger too | `a-telling-that-is-all-complaints` |
| the sitting's room gets no `.gitignore` | `a-room-that-does-not-reach-the-commit` |
| any range is accepted | `a-telling-that-invents-a-part` |
| completeness of the reading is not required | `a-reading-that-drops-a-record` |
| a contradiction with no answer takes an invented one | `a-contradiction-with-nobody-there` |
| `write_part` appends instead of replacing by key | `the-same-telling-told-twice` |
| the mark carries a fixed date | `a-description-from-nothing` |
| `settle` ignores the second turn | `an-answer-that-settles-a-contradiction` |
| the sitting writes where no knowledge is declared | `a-sitting-where-nothing-is-described` |

Two of those breaks reddened *two* cases at first, and both times the second judge was
measuring somebody else's mechanism: one checked that an old line was gone, which belongs to
`the-same-telling-told-twice`; one read the gate rather than asking the kit whether the project
is described. Both were narrowed. A judge that reddens for a neighbour's break is a judge that
cannot say what it measures.

## 9 · What is held by tests and not by a trap

The rule is that a new mechanism gets a trap immediately, and that where one cannot honestly be
planted it is written down in words rather than counted as proved. Nine:

| mechanism | held by | why not a trap |
|---|---|---|
| `nothing-was-told` — an empty telling | a test | a case cannot declare an empty telling: `sitting.telling` is checked as a non-empty string, and loosening that would let a case declare a question it never asks |
| `part-already-there` — a new part on a taken key | two tests | the same path through the program as `no-such-lines` and `reading-misses-a-part`, which is caught from both ends; a world of its own would measure the same lines |
| `part-named-twice` — one part read twice | a test | the same |
| `no-question-for-a-contradiction` | a test | the same |
| `part-nobody-asked-about` — the settling answers for what was not asked | a test | the same |
| `nothing-was-said` — a range of blank lines only | a test | the same |
| `two-parts-one-key` — two lines carrying one key | a test | it needs a knowledge the kit cannot write: two lines with one key are written by hand |
| `bad-mark` — a mark that is neither a date nor `derived` | a test | unreachable through a sitting: the program writes the mark, never the session |
| `checkout-held-elsewhere` from a sitting | three tests | not a new mechanism — a second caller of an old one, and the mechanism itself is watched by `two-runs-in-one-working-copy`; there is no way on the command surface to hold a working copy by hand |

## 10 · What no trap can catch, and this is the honest half of the step

**The bench measures the mechanism, never obedience.** Every case answers from
`providers/fake/`. That a real model returns a complete reading over fifteen parts, and a range
that points at the lines it means, is the one claim in this step that has not been measured. It
is the same shape as S6's `0 of 197`: named here rather than rounded up. The first live sitting
is where it gets measured, and it has not been run.

**`derived` has no writer.** The done-when says every record is traceable to a line the owner
said *or* is marked `derived`. S8a closes the first half completely and writes no `derived` at
all — its writer is the audit of S8c, which works the code out and never confirms it with
anybody. So after a first sitting every part is `walked`, and the half a machine wrote about a
product has nowhere to come from yet. That is a gap in the layer, not in this step, and S8c
closes it.

**The parts of the live knowledge carry no keys yet.** The kit reads a list item that has none
and derives one from its name; it writes the key only when it writes the line. So the first
sitting on `beeplish` will add keys to the parts it touches and leave the rest exactly as they
stand. Nothing is migrated and nothing is rewritten, which is the rule — but it means the
knowledge will hold both shapes for a while, and that is deliberate.

**A stale flake in the bench, still not caught.** Under load a case occasionally answers "could
not judge" or its child driver exits 70, and a rerun is green. Seen three times tonight, twice
on `two-features-in-one-repository`. It is not S8a's mechanism, but it is the bench telling the
truth about somebody else's trap only most of the time, and a full run can therefore lie. This
is the same tail the owner already knew about — exit code 7 with no case named — and it is
still open.

## 11 · The history was rewritten once, and why

The first attempt landed fifteen commits, and one of them — the extraction of the attempt
chain — did not build: it called `project.declares_knowledge` and `Knowledge.described` two and
four commits before either existed. Its message said *Behaviour is unchanged: 79 of 79 traps
still fire*, a measurement that could not have been taken on a commit where every run with a
`design` step raises `AttributeError`.

That is an assertion instead of a trace, standing in the project's own history, which is the
single defect this whole plan is written against. Nothing had been pushed, so the range was
rewritten into nine commits: each one imports, answers `--help`, and the extraction commit was
measured for real — the bench and the suite, from an unpacked archive, on that commit. Its
message now says what actually changed, which is one thing: after a split step continues, the
pause between attempts starts doubling from the beginning again.

The reviewer found this by reading the commit rather than the diff. It is worth writing down
that no test, no trap and no green suite would have found it: the tree was correct at HEAD the
whole time.

## 12 · What was deliberately not built

- **`sitting.json`** — a sitting does not resume, cannot be stopped from elsewhere and has no
  graph. State with no reader.
- **A second round of questions.** One round; a second is a conversation.
- **A template for the description.** There is none at all: the program writes the file, so
  there is no prose to promise a check nobody performs. That is the plan's bullet about
  templates, executed by removal rather than by review.
- **`agent-kit knowledge show`** — the files are markdown and the person is standing in the
  repository.
- **The slots of the kit as questions** — entities, integrations, scenarios, the MVP bounds.
  The bounds and the scenarios are S8b's, by the plan's own words.
- **A commit.** The kit prints the paths; the owner reads the diff and commits. A sitting on
  `main` that commits and pushes is the kit breaking its own `pre-push`.
