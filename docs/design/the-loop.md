# The loop: who records, who reminds, who resolves

Built by reading every file of the payload, not from memory; each row was checked against the lines
cited beside it. It exists because the kit had four partial maps of this and no complete one — the
plugin README lists what survives a run, `docs/developing.md` lists who may write which file,
`ship`'s Build table lists where a finding goes, and `rules/pull-requests.md` lists what raises one
again. None of the four names **who is allowed to close it**, which is the question that was missing
when a merged feature sat at `building` for a week.

## The actors

| Actor | What it is |
|---|---|
| the owner | the only one who decides what the product is, and the only one who merges |
| `blueprint` | the sole writer of knowledge prose; runs `--check` |
| `ship`, `fix` | the only two that change product code |
| `sprint` | three roles in one file: the **brief** that composes a batch, the **closing session** that delivers it, the **window** that narrates it |
| `orchestrate.py` | the driver: starts children, watches them, obeys `control`, never judges |
| `audit` | six lenses; writes one work list per lens and nothing else |
| `next` | reads everything, ranks it, recommends one command; changes nothing but two bookkeeping facts |
| `agent-kit:reviewer` | reads one diff against one entry; writes only into the run file, through its caller |
| `check.py` | the mechanical reader every command runs first; writes one thing, and only with `--sync` |

## The records

Six columns. A record with a blank in any of them is a defect, not a design — and the last one is
the column this page did not have when it was written. *Who* may close a record says nothing about
*where* that happens, and a record whose only closing place is a session the owner has to start by
hand is a record that makes them run a command after every batch. That is what an open block did
until 0.44.0.

| What was found | Who records it | Where it lives | What raises it again | Who may close it | Where that happens |
|---|---|---|---|---|---|
| a decision the knowledge did not settle, expensive to reverse | `ship`, `fix` | `[assumed …]` block under the entry | the check, before every command | `blueprint` — asks it as a yes-or-no, rewrites the entry, deletes the block | in a `blueprint` session, or in the preflight of the next command to touch that entry, when the owner answers there |
| a ready-made answer the library map does not name | `ship`, `fix` | `[found …]` block under `stack.md` | the check, before every command | `blueprint` — folds it into the map and deletes the block | in a `blueprint` session |
| the entry promises what the product does not do | `ship` | `agent-kit:unmet` on a test, plus `unmet` in the run file | the check lists it; `sprint` with no theme offers it as a batch | the owner picks the side; then `ship` makes it true and unmarks, or `blueprint` rewrites the entry and `ship` deletes the test | in a `sprint` composed of unkept promises |
| what a run built made the entry's prose false | `ship`, `fix` | `[stale …]` block under the entry | the check, before every command | `blueprint` — rewrites the prose and deletes the block | the batch's closing session applies it in the pull request; otherwise the preflight of the next command to touch that entry, or a `blueprint` session |
| work understood and not done | `ship`, `fix` | a line in `docs/technical_debt.md` | the check counts it; `sprint` with no theme offers it | whoever does that work — `ship`, `fix`, or `blueprint` where the work was prose — deleting the line in the same commit | in the commit that does the work |
| a gap between the code and the description | `audit` | a box in `docs/audits/<lens>.md` | `next`; `sprint` composes a batch from it | `ship`, `fix` do the work; the closing session or `next` tick the box | in the batch's own commit, or in `next`'s bookkeeping commit |
| a rule the project never wrote, where the code is plainly worse | `audit` | "also noticed" in the lens's file | that lens's next run | `blueprint`, by making it a rule — or nobody, deliberately | in a `blueprint` session |
| a scenario with no end-to-end test | nobody records it — it is computed | the absence of `agent-kit:scenario` in the suite | `check.py --state`, and `next` at rung 8 | `ship`, writing the test — via the scenarios lens and a batch | in a `sprint` composed from that lens |
| a feature delivered | `ship` or the closing session | `state: building (pr: n)` on the entry | the check compares against the pull request on every run | `next` or `blueprint --check`, with `--sync` | in their own `docs(knowledge):` commit |
| a fork nobody was there to answer | `ship` | `waiting_on` in the run file | the window, the driver, `next` | the run itself, when the answer lands in `answers` | in the run that asked |
| everything else a run learned | the run | `deviations`, `notes`, `blockers`, `review`, `suite`, `answers` | the closing session, into the pull request | **nobody — this is history by design**, and it dies with the branch | — |

## The cycles

**1. Knowledge → code → knowledge.** `blueprint` writes an entry → `ship` builds it and marks the
state line → the pull request merges → `next` or `blueprint --check` moves it to `built`. Closed.

**2. Code → knowledge.** A run meets a gap in the description and takes a decision → `[assumed …]`
→ the check prints it before every command → the next command to touch that entry shows it to the
owner in its preflight and writes their answer in, or a `blueprint` session does → the block goes.
Closed, and **without a command run for the purpose**: the settling happens inside work the owner
was doing anyway, which is the difference between a loop and a chore.

**2b. Code → knowledge, with nothing to ask.** A feature outdates a sentence of its own entry →
`[stale …]` under it, saying what it claims and what is true now → the batch's closing session
applies it in the pull request the owner is about to read, or the next command to touch that entry
does. Nothing is misled meanwhile: the correction sits under the prose it corrects. Closed.

**3. The contradiction.** An entry promises what the code does not do → the test is written and
marked, the run file names it → the check lists it for ever → `sprint` with no theme offers the pile
→ the owner says which side is wrong → the work makes it true or the entry changes. Closed.

**4. The leftover.** Work understood and not done → a line in the ledger → the check counts it →
`sprint` offers it → whoever does it deletes the line in the same commit. Closed.

**5. The blind spot.** Nobody has looked at an area → `audit <lens>` → a work list of boxes → `next`
sees the lens is stale or the list is long → `sprint` composes a batch → the work is done → the
closing session or `next` ticks the boxes → the next run of that lens rewrites the file. Closed.

**6. The night.** The brief writes the run files → the driver builds each child → each child records
into its own run file → the closing session reads every run file and writes one pull request → the
owner merges. Closed, and everything the children knew that did not reach the pull request is gone
by design.

## Where the loop did not close, and what was done

All seven were found by building this page and reading every file of the payload against it. All
seven are closed in 0.43.0.

**a. The prose-is-stale line had no one to delete it.** It was put in the ledger on 5 August, with
`blueprint` named as its resolver — but `blueprint` never deletes ledger lines, and the only two
commands that do are `ship` and `fix`, who may not touch prose. So the line would have survived the
rewrite that answered it, for ever. It is a `[stale …]` block under the entry now: same writer, same
resolver, and the resolver removes it with the same movement that answers it. It is also read by the
next run that opens that entry, which a line in a ledger never was.

**b. `[found …]` had a resolver and no procedure.** Only the `[assumed …]` path was written down.
`blueprint` now carries one table for all three block kinds, each with its own ending.

**c. A blocked run with no entry vanished.** A parked feature is named in the batch's pull request,
and its entry stays `planned`, which raises it again. A run built from a `task` has no such line,
and `check.py` does not list runs at a terminal step — `blocked` is terminal. The closing session
now writes a ledger line for a parked child that had no entry.

**d. The scenarios lens instructed a reader it does not have.** It said an untestable step "goes to
`docs/technical_debt.md`", addressed to whoever writes the end-to-end test — but the file is read
only by `audit`, which may write nothing but its own list. It now says which run records it, and
that the lens says so in its work list.

**e. Four maps, none complete, and one of them stale.** The plugin README's table of records,
`docs/developing.md`'s table of writers, `ship`'s table of destinations and `rules/pull-requests.md`'s
table of raisers are four views of this graph, read at four different moments. They stay — but the
README's now names who closes each record, and this page is what they are checked against.

**f. The actions template claimed nobody else writes the state line.** Five places state that rule;
this was the one that had not been updated when `next` gained the right to move it.

**g. The screens template nested one HTML comment inside another**, so the inner `-->` ended the
outer block and the last two lines of its example rendered as text. `validate.sh` now refuses both
that and an unclosed code fence anywhere in the payload — the second malformed-markup defect found
in two days, after `blueprint` shipped a release with half its rules inside a code block.

## The rule this graph produces

Every mechanism in the kit arrives with **four** answers, not three: who writes it, who reads it,
who may close it, and what becomes impossible without it. The third was never asked, and every
defect above is a mechanism missing exactly that one.

Two sentences say the whole loop:

> **Records are written by many. Reminding is always the check. Only three commands resolve
> anything: `ship` and `fix` change code, `blueprint` changes knowledge, `audit` writes its own
> list.** Everything else transcribes what one of them has already established.

> **A record is closed inside work that was happening anyway.** If the only place it can be closed
> is a session the owner has to start for that purpose, every batch ends by owing them a command,
> and the recommendation to run it stops being read by the third time.

> **Every record names who may close it and who removes it.** They may be different actors — but
> both must be named, and a record whose resolver cannot remove it needs a remover of its own.

That second sentence was written the other way round first — *whoever resolves is whoever removes* —
and the graph refuted it within the hour. Two records split the two roles deliberately and are fine:
an audit's box is ticked by the closing session or `next` and only disappears when that lens runs
again, months later; a child's ledger line is written by the child and carried into the file by the
closing session, because the ledger moves once, in the batch's own commit. Both name their remover.
The prose-is-stale line names neither.

Everything else that writes — the closing session ticking a box, `next` moving a state line, the
driver setting `step` — is recording a fact one of those three has already produced. None of them
decides anything, and that is why they are allowed to write without a pull request.
