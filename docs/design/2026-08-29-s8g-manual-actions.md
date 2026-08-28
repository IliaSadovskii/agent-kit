# S8g — manual actions, with a proof that runs

Written after building it, 29 August 2026. The last of the seven recovered steps, and the one the
plan describes as having no home in the third version at all: before tonight, `manual` appeared
nowhere in `src/` or in `method/`.

> **S8g · Manual actions, with a proof that runs.** The one class of work an autonomous night
> cannot do for itself — place a secret, apply a migration, create an account, point a domain.
>
> *Done when* a run that needs a human action records it where it survives the machine; a proof
> that passes deletes its own line; a line with no possible proof says so in its own words; and the
> door of S8d names what is due rather than leaving it to be found.

## 1 · Where the file lives, and why not beside the ledger

`.agent-kit/v3/manual.md`, committed to git. Its shape is the ledger's — a list item with segments,
one parser now shared by both — and its *place* is the one deliberate difference.

The knowledge directory is **declared**: `knowledge = ""` is a legitimate answer, and a night never
creates the directory. A ledger line can be lost that way honestly — *works, but badly* is talk
about a product the kit was told nothing about. **A chore cannot.** *Put the key in the
environment* is exactly as binding for a project the kit knows nothing about, and that is most
projects at first meeting; a line lost precisely at the least-described project is the same defect
this layer exists against, entered a second time.

The second reason is mechanical: `described()` would have had to exclude a second file by name.
S8f already pays that exclusion for `debt.md`, because otherwise an hour spent on complaints makes a
project "described". A night that wrote down a chore must not make a project described either, and
not having the relation is cheaper than defusing it.

`.agent-kit/v3/` is repository content: the `*` ignores live only in `runs/`, `batches/`, `audits/`,
`sittings/` and `trees/`, and `project.toml` rides along in a clone. I verified that by hand before
the step was built.

**And the one case where it is not true has a refusal of its own.** The kit of S0–S3 wrote
`.agent-kit/v3/.gitignore` = `*`, and only `agent-kit init` removes it. A project raised by that kit
and never re-initialised would have swallowed `manual.md` silently, and no trap would have noticed —
every bench world is fresh. So the writer asks `git check-ignore` and refuses `manual-ignored`
without writing anything, and a case plants the old ignore.

## 2 · The writer, decided by S8f's measurement rather than repeated

The feature names the chore; **the evening lays the line**. No second measurement was made, and
none was needed: it is the same file, the same insertion point and the same 200-of-200 that S8f
measured, where two siblings of one batch appending after the same last line stop merging.

So `design.manual` returns records, `record` derives the key **against the owner's checkout** — S8f's
lesson, since nobody commits this file and a run's worktree is frozen at its branch's base — and the
batch lays the lines where it lays the ledger and closes the frames: once, at the end, only for
features that landed, remembered in `batch.json` so a second `batch go` cannot resurrect a line a
proof has already taken away.

Nothing below the batch learned the word *batch*. The run only ever names.

**The cost, said in the report and not only here:** a run started by hand lays no lines. Its chores
go into the pull request, as they do today.

One placement detail is worth recording because it is where the mechanism would have vanished
silently: `record` returns early when the knowledge does not exist, and manual actions are named
*before* that return. They do not depend on the knowledge — which is the whole reason the file lives
outside it.

## 3 · Who runs the proofs

Only `agent-kit manual check`, typed by a person.

**Not the door**, whose own rule is that it does nothing — and `next` is typed constantly. **Not the
night**, because the proof is a command in the owner's checkout, which the batch does not hold, and
because a hanging proof would lengthen a night and a red one would redden it for work that is not
the kit's. **Not `verify`**, which answers whether a *feature* is proved.

The walk covers every line and a red one does not stop it — this is a report, not a `verify`. It has
a proof timeout of its own (thirty seconds) rather than the project's `command_timeout`, which is
sized for a suite in a container while a person is standing at the terminal. A hang, a missing file
(exit 127) and a red exit all leave the line standing. The command as a whole always exits zero.

A proof that cannot fail — `true`, `:`, `yes` — is caught at both layers by S8e's own
`proves_nothing`: at the design's contract, and again in the walk, because a line can also be
written by hand.

## 4 · The bug the last review found, and why it is the step in miniature

The walk branched on `by_hand` rather than on `proof`. Two consequences, one root:

- **A line with neither answer was silently deleted.** Its `proof` is empty, `proves_nothing("")` is
  empty, and `subprocess.run("", shell=True)` returns zero — so the kit removed it having run
  nothing. And the file's own header invites the owner to write lines by hand. An owner writing
  *reissue the certificate* would have had it erased. That is *done* as somebody's own word about
  their own work, which is the sentence this step exists to make impossible.
- **A line carrying both answers occupied a rung nothing could remove**, because the door ranks by
  the proof and the walk skipped by the reason.

One change fixes both: the walk branches on the same field the door ranks by. A line with both is
run; a line with neither is named `manual-nobody-can-close` and left exactly where it stands. The
writer refuses `action-with-no-answer` as well, because an empty segment does not read back and the
line would have become invisible to the reader while its key had already reached `batch.json`.

## 5 · The rung

`manual-due`, between *work not finished* and *a report is waiting*: unfinished work costs more than
a chore, and a chore costs more than a report about work that does not run without the key.

**Only lines with a proof stand on it.** A `by-hand` line never occupies a rung, because the kit
cannot remove it and a rung the kit cannot remove stops the ladder descending — the defect the S8d
review found in `run-failed`. Those lines are counted in the view instead. This is also what earns
the rung at all: S8d refused to read `debt.md` because its lines have no command, and a provable
chore has one — `agent-kit manual check`.

## 6 · The stage, not built

The plan wants a stage to decide what is shown. There is no stage on disk — the word does not occur
in `src/` — and a stage field would have a reader (the filter) and neither a writer nor a closer:
nobody moves a project from one stage to the next, so it would be set once or never and the filter
would be a constant. Each line would also need a second field, *when it is due*, which a session
would invent.

Decisively: **the plan's own *done when* does not ask for one.** Its four clauses are the record,
the proof, the line with no possible proof, and the door. The stage is the only bullet with no
check behind it, and the fear behind it — *a list teaches the owner to scroll past* — is answered by
what already exists: the door names one thing, and the list is printed by a command somebody types
when they intend to work.

## 7 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1226 | **1294** |
| `make bench` | 127 of 127 | **135 of 135** |
| `make armed` | 122 + 5 in words | **130 + 5 in words** |

Eight traps added. The bench also ran 135 of 135 from `git archive HEAD` unpacked outside the
repository, and every commit imports every module of the package.

## 8 · Breaking it by hand, and the break that reddened nothing

Thirteen breaks across two rounds, each of a branch; and the most useful one is the one that failed
to redden anything.

Breaking the evening's *memory* guard reddened no case, and the investigation is the finding: two
features naming one chore already collapse to one line without the guard, because the writer
replaces a line with the same key. The guard holds something else — that a night does not name a
chore to the owner twice, and does not lay it again after a proof has taken it away. The trap was
strengthened to ask `batch.json` as well as the file, and the round was started again.

**The same accident exposed a hole in S8f, accepted an hour earlier**: the ledger's memory guard had
no bench trap either — no case gave two features one debt line, and the test that stood was green
with the guard removed for the same reason the old judge was. It is closed in this step's round: a
second feature now finds the same thing, and the judge counts the key in `batch.json`.

| broken | what said so |
|---|---|
| the evening does not remember what it laid | `an-action-a-night-hands-over` |
| a proof removes a line whatever it exits with | `a-proof-that-comes-back-green` |
| the walk does not ask `proves_nothing` | `a-proof-that-cannot-fail` |
| a `by-hand` line is run like any other | `an-action-only-a-person-can-do` |
| every action reaches the rung, not only provable ones | `an-action-only-a-person-can-do` |
| there is no rung at all | `an-action-the-door-names` |
| the design is not asked about its actions | `an-action-proved-by-nothing` |
| the writer does not ask `git check-ignore` | `a-file-an-older-kit-hid` |
| the walk branches on the reason again | `a-line-the-kit-must-not-close` |
| a line with neither answer is run like any other | `a-line-the-kit-must-not-close` |
| the door runs proofs itself | `an-action-the-door-names` **and** `a-line-the-kit-must-not-close` |
| a red proof stops the walk | `a-proof-that-comes-back-green` |
| the ledger's evening forgets what it laid (S8f) | `a-finding-that-outlives-its-report` |

Three judges that *could not have failed* were found and repaired in the same round: one watched for
a file nothing in its world could create, one ordered its lines so that a walk stopping at the first
red would still pass, and one asserted only a negative.

## 9 · What is held by words, not by a trap

- **The join** (`action-with-no-line`) fires only when a *program* lies, and the fake provider
  answers for sessions. Tests, as in S8f.
- `action-unproved`, `action-proved-and-by-hand`, `action-that-cannot-be-written`,
  `action-with-no-answer`, `two-actions-one-key`, `unreadable-manual` — tests.
- **A broken proof stands for ever**: a command whose file is missing exits 127, and the line keeps
  its rung. The closer of last resort is the owner deleting the line by hand — which they can,
  because the file is in git and reads as prose. Without that sentence this would be `run-failed`,
  only slower.
- **The race**: `manual check` rewrites the file while an evening appends to it; the last writer
  wins, and the night writes again on the next `batch go` — while `batch.json` keeps a line a proof
  removed from coming back.
- **Nothing was driven by a live model**, as in every step of this layer.

## 10 · Where the plan was wrong

1. **"A run appends a line"** — the evening appends. Measured in S8f, and it is the same insertion
   point.
2. **"Whoever does the work deletes it in the same commit"** — half true. The proof removes the
   line; the kit commits nothing in the owner's checkout, so the deletion waits in the working copy
   for the owner. The kit will not promise a commit it does not make.
3. **"A file shaped like the ledger of S8f"** — in shape yes, in place no, for §1's reasons.
4. **The stage** — a field with no writer and no closer, and absent from the plan's own *done when*.
5. **"The door names what is due"** — only what the kit can remove. A `by-hand` line may not hold a
   rung, or the ladder stops descending.
