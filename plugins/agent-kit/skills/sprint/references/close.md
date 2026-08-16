# Closing a batch

**Before anything else, say who you are in one line** — `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`, its first section, which carries the shape and the example.

You were started by the driver, with a run directory. Every feature in it has finished — with a
pushed branch, or parked. Your job is the one part of a batch that is judgement rather than
bookkeeping: turn it into a pull request somebody can merge without reading the diff, then write the
report.

You build nothing and fix nothing. If a feature is broken, it is parked and said so.

## Read first

`run.json` in the batch directory, then each child's `run.json` — approach, assumptions, deviations,
`review`, `answers`, `unmet`, `manual`, `deferred`, `closed_debt`, suite, blockers, branch, step,
and whatever a child left in `notes`. Then `.agent-kit/project.yml` for the language.

That is your whole source. Do not re-read the code of features you are describing: their run files
and their commits are the record, and re-deriving it costs more than the batch's own delivery.

## The branch

The children are one chain, so the last child that reached `step: done` already carries the batch.

```bash
git fetch origin
git branch -f sprint/<batch-slug> <last successful child's branch>
git push -u origin sprint/<batch-slug>
```

**Inside an `epic` the branch already exists and moves forward instead**: fast-forward `epic/<slug>`
to the last successful tip and push it. There is one pull request for that whole run, so the first
batch opens it and every batch after **rewrites its body and adds a comment with its own digest** —
what this batch built, what it proved, what it decided without the owner. They read one place and
see what is new since they last looked.

Say once, in the body, how to look at it without breaking the run:

```bash
git worktree add /tmp/<slug>-preview epic/<slug>
```

A `git checkout` in the project's own directory pulls the working tree out from under the children
still building in it. This line is what stops that at three in the morning; name a free port too if
the project already has an instance running.

**The frame child is not a feature and gets no row anywhere it would look like one** — no entry, no
tests, no diff of its own beyond one block. What it owes the reader is one line near the top: what
this batch agreed to build alike, quoted from the `[frame …]` block, because that block is in this
pull request's diff and nothing else in the body accounts for it. Fill its `pr: ?` in with this
pull request's number, in the commit that moves the ledger — `blueprint` closes the block months
later, when the run directory is long gone, and the number in it is the only way anybody can then
tell whether the batch behind it ever merged.

A child that was parked mid-feature keeps its branch pushed, out of the chain, and is named in the
report as unfinished work rather than merged silently.

**A parked child built from a `task` rather than an entry also gets a line in the ledger** — what it
was for, how far it got, and its branch. An entry that was not built stays `planned` and the next
command sees it; a task has no such line anywhere, so without this the only work in the kit with no
home in the knowledge is also the only work that disappears the day this pull request merges.

## The pull request

**One for the batch**, based on the default branch, covering every feature in it. The features chain
off each other, so the last branch already holds the batch and there is nothing to merge together
first. Sections and their order are `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`; everything below
is how they are composed across features, which is yours alone — you are the only session that ever
writes one of these, which is why it is here rather than in a file every feature reads.

Composed across features and **organised by what could have gone wrong**, not by what was done. With
the entries written in advance, a batch can only have gone wrong in three places, and all three stay
uncollapsed at the top:

1. **What did not happen** — every parked or skipped feature, and why. A hole in a batch is more
   dangerous than any line of code in it, and it is the first thing a reader must not miss.
2. **Manual actions** — the children's `manual` records, merged into one ordered list by `when`.
   Three migrations are three numbered steps, not three sections the owner assembles in their head.
   **From the field, never re-derived from a child's prose**: the list is what the owner will
   actually go and do, and a paraphrase of it drops the `proof` line that says how they will know
   it worked. Measured on one run, nineteen actions were listed and six needed a person — the
   other thirteen were things a script should have done or settings that already worked, and they
   were what made the six unfindable.
3. **Assumptions** — one table for the batch: decision, why, which feature, which entry. Expensive
   first, and the children's `deviations` belong in it too: a deviation is an assumption the code
   forced. This is the single place a well-specified batch diverges from what the owner wanted.

Then **Proven**: a row per feature naming which of the entry's lines have a test, what the suite
returned, its `mutation` — how many changes to the product's logic the tests caught, how many they
slept through, or that the step did not run — and what is *not* proven, plus the batch-level fact
about the product's end-to-end scenarios: **which of the three it is.** They ran in CI on this
branch and what they returned; or this project declares no `commands.e2e`, so nothing can walk them
and the finish is somebody's hands; or the command exists and no pipeline runs it, which is the one
of the three worth a line of its own — the batch chained every feature onto the last precisely so
that the joins could be judged, and nothing judged them. You never run them yourself: a walk in the
tree the children built in proves that an application already running still runs, and the artefacts
it leaves make that tree dirty for the next batch.

Inside it, uncollapsed, **the promises this batch did not keep**: every line of every child's
`unmet`, with the entry, what the code does instead, and which feature met it. A batch that ends
green while the product contradicts three entries is only honest if that list is in plain sight —
and it is the list the next `sprint` composes a batch from.

**The ledger moves both ways in one commit.** Delete the lines the children finished — their
`closed_debt` — and write in the batch's leftovers, every child's `deferred`, one line each, newest
first, copying `${CLAUDE_PLUGIN_ROOT}/templates/technical_debt.md` if it is not there yet. Commit
it on the batch's branch, before the pull request, and say the movement in one line of the report:
nine items, three closed, two added. This is the only step of yours that leaves something behind in
the repository, and it is the difference between work the project remembers and work that lived in a
pull request until it was merged.

A child that says it closed an item whose line is still there did not finish it — carry the line
over untouched and name the feature in the report, rather than deleting on its word.

**Tick what the batch closed in the audits' work lists too**, when it was composed from one:
`- [x] закрыто PR #<n>` on each item its features finished, in `docs/audits/<lens>.md`, in the same
commit. Only three things ever tick them — this step, `next` and `accept`, each
only when it has verified an item is done — and the lens itself rewrites that file only on its next run, which may be months out. Until
then every command reads the list as though the work were still waiting.
Untouched items stay untouched: a box ticked on a guess costs more than one left open.

Then a collapsed block per feature, about eight lines: what it does now in the product's terms, the
approach in one sentence, where the tests sit, its branch, and the command that opens it as its own
pull request:

```bash
gh pr create --base <its base branch> --head <its branch>
```

That line is why per-feature pull requests are not opened up front: the capability costs one command
on the day it is wanted, and opening them in advance cost two merge accidents.

The **Review** section is composed from the children's `review` fields, not from their prose: the
verdict, then the findings that were closed and how, then any that were not — a finding a child
carried to the end without closing is the batch's most important line, and paraphrase is how it gets
lost. The same for **Assumptions**, whose owner-answered forks come from `answers` word for word.

### Inside an `epic`: one pull request, rewritten by every batch

An `epic` has one pull request and eleven batches rewrite its body, so **every rule applies to the
run, not to the batch that happens to be writing.** Written per batch and appended, the body grows
with the number of batches instead of with the size of the product. Measured on one real run:
157 000 characters, of which a quarter was a list of every sentence the run changed in the
knowledge, a fifth was seventy assumptions in one uncollapsed table, and *What was hard* — three to
five lines by the rule — was a hundred and eighty-seven.

So a batch inside a run **replaces** the body rather than adding to it, and four sections are held
to a size that does not depend on how many batches there have been:

- **What & why** — one line per batch, naming what the product can now do. Not the batch's report:
  that is its digest comment, which is where a reader goes for *what is new since I last looked*.
- **What was hard** — the five hardest things in the whole run, chosen again each time. Five per
  batch is the same rule applied eleven times, which is not the same rule.
- **Assumptions** — the expensive ones uncollapsed, by name: stored data, permissions, money, a
  public contract. The rest as one collapsed table with its count. Seventy uncollapsed rows defeat
  the reason the section is uncollapsed at all.
- **Knowledge this run corrected** — one line per entry: which entry, what it now says. What it said
  before goes in the collapsed half. A pull request that edits the description it is judged against
  must make *that it did* the easiest thing to see, which a six-hundred-line list does not.

Everything a batch knows that does not fit those is already written down twice — in its digest
comment and in `docs/runs/<slug>.json` — so nothing is lost by keeping it out of the body.

**Review and CI.** Whether a repository-wide `/code-review` belongs on this pull request is settled
in `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, and nowhere else — a batch offers it in its
closing line and never runs it; a batch inside an `epic` does not offer it at all.

Wait for `gh pr checks` within a reasonable window; fix what is yours (formatting, lint, a flake, the workflow's own configuration)
and report anything that needs a feature's design changed. Never merge.

## Knowledge

For every entry a finished feature built, set its machine line to `state: building (pr: <n>)` with
the batch's number. `blueprint --check` moves an entry to `built` once the pull request merges.

**Then apply the `[stale …]` blocks the children left.** A block says two things — what the entry
still claims, and what became true when the feature shipped — so putting the second in place of the
first is transcription, not judgement, and you are the last session that knows this batch. Delete
the block in the same commit and **name every sentence you changed in the report**, one line each,
uncollapsed: a pull request that edits the description it is judged against has to make that the
easiest thing in it to see.

Two limits, and outside them the block stays and travels to `blueprint`:

- **only what the block itself states.** If applying it means deciding anything the block does not
  already say, it is not yours.
- **never what an entry requires.** A block claiming the product should do something else is a
  product decision wearing a correction's clothes. The owner settles those.

`[assumed …]` blocks are not touched. They are questions nobody has answered, they are already in
the Assumptions section of this pull request, and answering them is the owner's.

## The one thing this batch leaves in the repository

`.agent-kit/runs/` is working state and is in the project's `.gitignore`, so every run file, every
driver log and everything a child left in `notes` lives on one machine and dies with it. What
survives a batch today is the pull request's prose — which no program can read, and which nobody can
read either once it has been rewritten eleven times by an `epic`.

So write **`docs/runs/<batch slug>.json`**, in the same commit as the ledger, and write it **from
`${CLAUDE_PLUGIN_ROOT}/templates/batch.json`** — read that file and fill it, rather than from what
this page says a record looks like. The shape lives there, `check.py --run` judges it against there,
and a second description of it here is the one that would go out of date. Keep it small: a few
kilobytes, counts rather than sentences.

Two of its fields are the reason it is judged at all, and both are below. **`branches` is every
child's branch, copied from its run file** — including the frame child's and
any child that was parked, because a branch nobody can account for is one nobody will ever remove.
**And a parked child's branch is named a second time, in `parked`.** Both lists, not one: the first
is everything this batch made, the second is which of it the merge did not carry. `next` retires
every branch of a record whose pull request merged, so a parked branch left out of `parked` is
deleted as delivered — locally and on the remote, where a branch nobody ever had a local copy of has
no second one. Write the branch name and not the slug; they differ, which is why `blocked` cannot
stand in for this.
It is the only field here that is not a count, and it is not derivable from the others: a slug does
not give a branch name (the frame child's branch and its slug differ), and `.agent-kit/runs/` dies
with the machine. Without it, the day this pull request is **squash**-merged, git can no longer tell
those branches from unfinished work — measured on one project, 51 of 99 branches were unanswerable
by any git question, and the list grew until nobody could read it. `/agent-kit:next` reads this
field to know which branches a merged pull request already delivered, and deletes those; **the field
itself is never edited afterwards** — it is history, and a name still in it after the branch is gone
is the record of what this batch made.

Counts, not copies: what each of those *says* is already in the pull request and in the knowledge,
and duplicating it here would give one fact two places to disagree with itself. `per_feature` is `spent.sessions` off each child's own run file, by slug: the average hides the
shape, and the shape is the thing a later batch can act on. Measured — a batch reporting 1.67
sessions per feature was one feature at four and three at one, and the four was where a person's
action and a background job had been composed into a single child. The frame child of a later batch
reads this to decide what to split before anything is built; nothing else in the kit can tell it.
`spent` is copied
from the run file as the driver left it — the only measurement of what a run costs that outlives the
machine it ran on, and the only thing a later gate can price a scope from.

**Who may remove one:** nobody, and that is deliberate — it is history, one file per batch, and it
is the smallest durable record the kit has.

## Close the run file

Set `pr`, `branch`, `suite`, any `blockers`, and `step: "done"`. The driver is watching this file;
until `step` is terminal it believes you are still working.

Then the report, in the project's language, per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is
thin rather than what was done. For a batch that means the parked features, the assumptions that
would be expensive to have wrong, and anything a child could not verify — then one line naming what
to run next.
