# agent-kit

A development kit for building software with long-running Claude Code sessions. Version 1 is a
rewrite from scratch, complete as of 1.0.0: the line before it ended at 0.17.0, where one feature
cost 27M tokens and most of that went on machinery insuring the kit against its own autonomy. What
the rewrite concluded, and what it deleted, is in
[docs/design/kit-v1.md](../../docs/design/kit-v1.md).

Measured against that line: a feature now costs about 15M tokens, and a night of five features
about 73M.

## Commands

Seven commands in four roles: **knowing** what the project is, **building** from that, **checking**
the result back against it, and **orienting** when you have lost the thread.

| Command | Role | What it does |
|---|---|---|
| `/agent-kit:blueprint` | know | the project's knowledge layer: an interview that writes what the project knows, and `--check` that audits it mechanically |
| `/agent-kit:fix` | build | something is wrong and it is small: find the cause, prove it with a failing test, change the least that works |
| `/agent-kit:ship` | build | one feature end to end: design against the blueprint, build, verify, review, pull request |
| `/agent-kit:sprint` | build | a batch of features: brief them in one sitting, then a driver builds each unattended |
| `/agent-kit:mvp` | build | from the blueprint to a running prototype: the MVP bounds built, audited and proved by the scenarios |
| `/agent-kit:audit` | check | compare existing code to the description and write a work list |
| `/agent-kit:next` | orient | where the project stands and which command to run — for the cold start |

## Blueprint

Everything the project knows about itself, written before anything is built: what the product is
and deliberately is not, the stack and the rules the build follows, the actors, the entities and
their states, the actions, the screens, the integrations, the scenarios that have to pass, and the
MVP bounds.

It writes into `docs/knowledge/`, one file per slot, copied from `templates/knowledge/` — the
templates carry the shape of a record, so the format and its description cannot drift apart. The
project's language, its commands, and one verdict per slot live in `.agent-kit/project.yml`.

Three ways in:

- `blueprint` — the interview, resuming wherever the last session stopped. It works only on what is
  empty, stale, or marked by an earlier run, so a second run costs minutes rather than hours.
- `blueprint <what you want to add or reconsider>` — the way in once everything is settled: a
  feature you have thought through, a part you want reworked, a doubt about whether something is
  covered.
- `blueprint --check` — mechanical audit: fields, key references, orphans, stale sources, the state
  of the pull requests behind entries being built, and the promises the product does not keep.
  Seconds, asks nothing, quiet when there is nothing open.

**One decider, one trigger.** Only blueprint decides what an entry requires, and only you start
blueprint. A build command leaves a marked block where it had to assume something, or where its own
feature outdated a sentence — and when you are sitting there, the next command settles the block with
you and writes your answer in rather than sending you off to run another command. Nothing revises
what the product must do on its own.

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

Why it is shaped this way, and what was rejected: [docs/design/ship.md](../../docs/design/ship.md).

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
[docs/design/sprint.md](../../docs/design/sprint.md).

## MVP

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
[docs/design/audit.md](../../docs/design/audit.md).

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
| `docs/knowledge/` | what the product is, one file per slot; each entry's state — `planned`, `building (pr: n)`, `built` | `blueprint` writes the prose; a build command sets `building`, and the line moves on from there once its pull request merges | the state line is bookkeeping; the prose is `blueprint`'s alone |
| `[assumed …]`, `[found …]`, `[stale …]` blocks | what a run had to decide without you, a library it found, or prose its own feature has made false | any build command, under the entry or under `stack.md` | `blueprint` — or the next command that builds in that entry, which settles it with you in its first minute |
| `agent-kit:unmet` on a test | a promise the entry makes and the product does not keep — the test is written and marked so the suite stays green | `ship`, when the entry and the code contradict each other | you choose the side; then the product changes or the entry does |
| `docs/technical_debt.md` | work a run understood and did not do | `ship`, `fix`, and the session that closes a batch | whoever does the work, deleting the line in the same commit |
| `docs/audits/*.md` | a lens's work list, boxes ticked as they are closed | `audit` writes; a batch and `next` tick | that lens's next run, which rewrites the file |
| `.agent-kit/runs/*/run.json` | one run's memory: approach, tasks, assumptions, review, answers, what it left behind | the run itself, and the driver | nobody — it is history, and everything meant to outlive the branch is in one of the records above |

The rule underneath all six: **anything a run leaves undone names the record it now lives in, and
nothing is left as a message to a person.** A leftover described only in a pull request is forgotten
the day it merges. The whole graph — who records, who reminds, who resolves —
is [docs/design/the-loop.md](../../docs/design/the-loop.md).

## What it needs

`git` and `python3` for everything, `gh` to open a pull request. `sprint` and `mvp` also need
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
