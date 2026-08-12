# agent-kit

A development kit for building software with long-running Claude Code sessions. Version 1 is a
rewrite from scratch, complete as of 1.0.0: the line before it ended at 0.17.0, where one feature
cost 27M tokens and most of that went on machinery insuring the kit against its own autonomy. What
the rewrite concluded, and what it deleted, is in
`docs/design/kit-v1.md`.

Measured against that line: a feature now costs about 15M tokens, and a night of five features
about 73M.

## Commands

Eight commands in four roles: **knowing** what the project is, **building** from that, **checking**
the result back against it, and **orienting** when you have lost the thread.

| Command | Role | What it does |
|---|---|---|
| `/agent-kit:blueprint` | know | the project's knowledge layer: an interview that writes what the project knows, and `--check` that audits it mechanically |
| `/agent-kit:advise` | know | where the project is weak and where it could grow — the product, the code, the money — and what you accept is written down |
| `/agent-kit:fix` | build | something is wrong and it is small: find the cause, prove it with a failing test, change the least that works |
| `/agent-kit:ship` | build | one feature end to end: design against the blueprint, build, verify, review, pull request |
| `/agent-kit:sprint` | build | a batch of features: brief them in one sitting, then a driver builds each unattended |
| `/agent-kit:epic` | build | a whole scope built, audited and proved, as one pull request: the MVP bounds first, then whatever is still planned or still owed |
| `/agent-kit:audit` | check | compare existing code to the description and write a work list |
| `/agent-kit:accept` | check | take delivery of a finished run: can this be merged, and what needs your hands, in what order |
| `/agent-kit:next` | orient | where the project stands and which command to run — for the cold start |

## Blueprint

Everything the project knows about itself, written before anything is built: what the product is
and deliberately is not, the stack and the rules the build follows, the actors, the entities and
their states, the actions, the screens, the integrations, the scenarios that have to pass, and the
MVP bounds.

It writes into `docs/knowledge/`, one file per slot, copied from `templates/knowledge/` — the
templates carry the shape of a record, so the format and its description cannot drift apart. The
project's language, its commands, and one verdict per slot live in `.agent-kit/project.yml`.

One door, and two flags:

- `blueprint` — **say whatever you came to say**, in any order and at any length: an idea, one part
  in detail, the whole product again, or a list of what did not match when you used it. It reads
  what is already written on what you touched, shows you the comparison — new, refines this,
  contradicts that — writes it, and only then asks about what is still missing. Say nothing and it
  tells you where the description is thin and asks from there.
- `blueprint --recall [part]` — tells you what the project already says, out loud, so you never
  open a file to find out. Changes nothing until you ask it to.
- `blueprint --check` — mechanical audit: fields, key references, orphans, stale sources, the state
  of the pull requests behind entries being built, and the promises the product does not keep.
  Seconds, asks nothing, quiet when there is nothing open.

**One decider, one trigger.** Only blueprint decides what an entry requires, and only you start
blueprint. A build command leaves a marked block where it had to assume something, or where its own
feature outdated a sentence — and when you are sitting there, the next command settles the block with
you and writes your answer in rather than sending you off to run another command. Nothing revises
what the product must do on its own.

## Advise

A look over the whole project: **where it is weak, and where it could grow.** Every other command
takes your description as true — blueprint writes down what you mean, audit measures the code against
it, the build commands make it real — so a mediocre idea gets built carefully and audited as correct.
This is the one that doubts it.

Three lenses, one reference file each:

- **`product`** — the idea and the people using it. What a user cannot finish because a step is
  missing. What is built and nobody needs. What people like these expect from a product like this and
  do not find here. Who is one field away from being served. And who to stop serving, because a
  narrower product is often the better one.
- **`code`** — how it is built. Where the present approach quietly stops working as the project
  grows, and at what number. What would make it simpler, harder to break and faster to change,
  including how long you wait on the tests and on the environment coming up — the thing that actually
  slows a developer down and that nobody measures.
- **`money`** — what it costs to run and what it could earn. What is given away that costs you per
  use, limits that exist in the plan and nowhere in the code, and what people would pay for that
  there is no way to pay for.

Each lens looks twice: **close up**, walking your files and citing them, and **from a step back**,
thinking about the product the way an outsider would — with research on the live web delegated after
that reading rather than before it, so the reading is something the search can be checked against
instead of a summary of the first page of results. Every row is tagged with what it rests on: the
files, the domain, or research with a link and a date. Judgement is never mixed silently into
evidence.

Nothing is proposed that was already decided: what is `planned`, what the audits found, what the
ledger holds, what you refused last time — and what `product.md` says the product deliberately does
not do, which may be reopened only by naming what changed since.

You decide in one round at the end. **What you accept is written down while you are still there** —
an entry with its fields answered, a stance in `stack.md`, or a line in the ledger when it is work
rather than a rule — so the next `ship` or `sprint` can build it like anything else. What you refuse
is recorded with your reason and never raised again; a refusal that rested on a number keeps the
number, so the next run can see whether it has moved.

The reasoning, and the alternatives rejected on the way:
`docs/design/advise.md`.

## Fix

The product does something it should not, and putting it right is smaller than a feature. Three ways
in, one pipeline: the owner's description when the cause is unknown, whatever is already red when it
is not, and `--pr <n>` for a review round on an open pull request, which commits onto that request's
own branch.

The spine is a failing test written **before** the change: without it "fixed" is a claim, and a
month later nobody can tell whether the defect was real. After the change the fix is undone once to
watch the test fail again — the only proof that it guards the fix rather than passing beside it.

It stops early rather than late. A cause that turns out to be *this was never built* is `ship`'s
work; a cause that is somebody's decision belongs to the entry; a repair that touches a layer rather
than a place goes to the ledger with the cause named. And it changes the least that makes the test
pass: the tidy-up next to it, the rename, the second defect found on the way are lines in
`docs/technical_debt.md`, because a fix that also refactors cannot be reviewed as a fix.

## Ship

One feature — an action from the blueprint, or a small group of actions and screens — to a pull
request that can be merged without reading the diff.

Blueprint says what the feature does; ship decides how, here: which files, which layer, which
existing helper, which seam the tests sit at. It asks only where a fork is expensive to reverse and
someone is present; everything else is decided and recorded. The tests are the entry's own lines —
what changes, what the initiator sees, what others see, what can go wrong — written before the code
where the risk is, so a test that cannot fail cannot pass unnoticed. One review pass reads the diff
against the entry that was approved, a security pass runs on a diff trigger, and the pull request is
opened after the fixes rather than before.

Where the entry promises something the code standing there does not do, ship settles nothing: it
writes the test for the promise, marks it `agent-kit:unmet` so the suite stays green, and records
the contradiction. That is the one green a kit should not want — a test written over the code's side
turns the day somebody fixes the product into a regression.

Why it is shaped this way, and what was rejected: `docs/design/ship.md`.

## Sprint

A batch of features around one theme, built one at a time while nobody watches. You compose the
batch in one sitting — that is the only part needing a person — and a script driver then runs each
feature as its own visible session, chaining every branch off the last, so the batch arrives as one
pull request rather than as five to reconcile.

Called with no theme it does not ask you to think one up: the project has already written down what
it owes, in `planned` entries, the audits' work lists, open notes, unkept promises and the debt
ledger. It asks which pile first — close what is owed, or build what is missing — and then which
items, and composes from that.

Why a script driver and not an orchestrating agent, and what a review deleted from the first design:
`docs/design/sprint.md`.

## Epic

Everything inside the MVP bounds, autonomously, as one pull request. It owns no build, test or
pull-request logic — it composes batches and the driver, `ship` and the closing session do the rest,
which is why it is the smallest command in the kit rather than the largest.

One question at the gate: the scope it derived from your bounds, or narrower, with the price of
each. Then batches of about five features, each a real sprint; after each one the pull request says
what now works, and you can open the branch in a `git worktree` without touching the run. When the
in-list is built it audits with the lenses this product needs, fixes what they find in wave after
wave until they stop finding it, and finishes only when every scenario inside the bounds passes
against the running application.

## Audit

Reads existing code, compares it to `docs/knowledge/`, and writes a work list a `sprint` can be
composed from. It changes nothing — not code, not tests, not the description.

Six lenses, each with its own reference and its own way of being cheap to fake: `tests` (does an
assertion exist for every line of every entry), `scenarios` (do the joins between actions hold),
`security`, `performance`, `conventions`, `deps`. Every verdict of "covered" carries a citation to
the file and line that proves it, because a verdict without one can only be believed.

The reasoning for each lens, and the two that were rejected:
`docs/design/audit.md`.

## Accept

For the moment a long run has ended and its pull request is too big to read. Measured on one: 157 000
characters of description over 40 000 lines of diff, seventy decisions taken without the owner, two
questions still waiting, one test deliberately red. All of it recorded honestly, none of it findable.

It reads the pull request, the run files and the mechanical state — **never the diff**, which was
already reviewed per feature and again per batch — and answers in six blocks, in the order a person
acts on them: can this be merged, what needs hands and how to tell each step worked, what is waiting
on a decision and which side to take, the expensive assumptions by name and the rest by count, what
is not proven or was never exercised at all, and how to open it without disturbing the run.

It changes nothing but the two facts of bookkeeping `next` may also write.

## Next

For the cold start: a session opened after a break, with nothing in context and no memory of where
the last one stopped. Every other command names a next step as it finishes, which works while that
session is still open; this one answers the same question a week later.

It reads the mechanical state — knowledge findings, debt, unkept promises, branches and their drift,
open pull requests and their CI, runs left at a non-terminal step, when each lens last ran — and
ranks what it finds by the cost of leaving it alone: work that exists on one machine only, then a
run abandoned mid-flight, then a green pull request nobody merged, then a red pipeline, and so on
down to unbuilt entries.

The answer is one command with the reason in a clause, plus two or three alternatives so it is
visible what was weighed. It changes nothing and starts nothing.

## What the kit remembers between runs

A command finishes, its session closes, and everything it knew is gone. Six records survive that,
and every command reads them before it starts. Each names who may close it, because a record nobody
is allowed to remove is a record that grows for ever:

| Record | Holds | Written by | Closed by |
|---|---|---|---|
| `docs/knowledge/` | what the product is, one file per slot; each entry's state — `planned`, `building (pr: n)`, `built` | `blueprint` writes the prose, and `advise` writes what you answered in front of it; a build command sets `building`, and the line moves on from there once its pull request merges | the state line is bookkeeping; the prose is written only with you in the room |
| `[assumed …]`, `[found …]`, `[stale …]`, `[accepted …]` blocks | what a run had to decide without you, a library it found, prose its own feature has made false, or a proposal you accepted whose fields are still outstanding | any build command, under the entry or under `stack.md`; the last by `advise` | `blueprint` — or the next command that builds in that entry, which settles it with you in its first minute |
| `[frame …]` under `stack.md` | how one batch's features agreed to build alike, settled by the batch itself with nobody present | the frame child a batch opens with | `blueprint`, folding it into the stack once that batch has merged |
| `agent-kit:unmet` on a test | a promise the entry makes and the product does not keep — the test is written and marked so the suite stays green | `ship`, when the entry and the code contradict each other | you choose the side; then the product changes or the entry does |
| `docs/technical_debt.md` | work a run understood and did not do | `ship`, `fix`, and the session that closes a batch | whoever does the work, deleting the line in the same commit |
| `docs/audits/*.md` | a lens's work list, boxes ticked as they are closed | `audit` writes; a batch and `next` tick | that lens's next run, which rewrites the file |
| `.agent-kit/runs/*/run.json` | one run's memory: approach, tasks, assumptions, review, answers, what it left behind | the run itself, and the driver | nobody — it is history, and everything meant to outlive the branch is in one of the records above |

The rule underneath all six: **anything a run leaves undone names the record it now lives in, and
nothing is left as a message to a person.** A leftover described only in a pull request is forgotten
the day it merges. The whole graph — who records, who reminds, who resolves —
is `docs/design/the-loop.md`.

## What it needs

`git` and `python3` for everything, `gh` to open a pull request. `sprint` and `epic` also need
`tmux`: the driver gives each feature its own visible session through it, which is what makes a
stalled run rescuable by hand and an account limit recoverable by typing one line into a session
whose context is intact. Headless children were rejected for exactly that reason.

Those two run for a night or a day and wait out account limits by sleeping until the reset, so they
want a machine that does not sleep either. Nothing else is assumed: `claude-new` is used when it
happens to be on the PATH, plain `tmux` is the fallback, and the kit ships no dependency on any
particular machine.

## Working in a repository

The kit works on branches and never merges a pull request — that decision is the owner's, on every
command. Since 0.48.0 that is machinery rather than instruction: a `PreToolUse` guard refuses to
merge a pull request, to force-push and to push to the default branch, and it runs outside the
model, where nothing can talk it round. It has an opinion only while a run is at a non-terminal
step, so your own sessions never meet it.

Two kinds of write are the exception, and both are bookkeeping rather than change: an entry's state
line moves when the pull request behind it merges, and an audit's box is ticked once the work behind
it is verified done. `blueprint --check` and `next` are what do them. Neither touches code, neither
decides anything, and both go in their own commit.
