# What the check found, and what you do about it

Every build command runs the knowledge check before it starts, and every one of them meets the same
findings. This is that reaction, in one place: it was written twice, in `ship` and in `sprint`, in
different words — and when a third kind of block was added, one of the two did not learn about it
and its runs met a record they had no instruction for.

The command line itself stays in each command, because what they ask for differs.

| What it found | What you do |
|---|---|
| **a run of this kit is in flight here** — printed first, a line per run | **do not start** — see the section below, which is the whole of it |
| a slot in scope unsettled, or an entry incomplete | stop, name what is missing, offer `/agent-kit:blueprint` — the owner is here and closes it in a minute |
| no `docs/knowledge/` at all | **carry on.** Work from the task as written, and say once that without an entry the tests can only aim at what the task says done means. A project's first command should not be an hour of interview |
| `[assumed …]` blocks on the entries in scope | with `gate: owner`, show them and offer to settle them now — this is the last moment anyone is here. **When they answer, write it into the entry and delete the block**, in its own `docs(knowledge):` commit before you start: you are transcribing their answer, not deciding, and a block left open is a question asked twice. With `gate: none`, follow them as written |
| `[stale …]` blocks on those entries | an earlier feature outdated a sentence and could not correct it. The block says what the entry claims and what is true now, so with `gate: owner` apply it — same commit, same rule: transcribe, never decide. With `gate: none` leave it, and read the entry as the block corrects it |
| an entry's state line behind its merged pull request | not yours. `/agent-kit:next` and `blueprint --check` move it, and a build command that started by writing to knowledge would fail its own clean-tree rule |
| a declared command that starts nothing — `commands.test: make test` with no makefile | **stop and name it.** A run cannot prove itself with a suite that does not run, and the fix is one line in `project.yml`, which only `/agent-kit:blueprint` may write. Offer it; the owner closes this in a minute |
| **kinds of verification nobody has answered for**, or answers over six months old — printed under `--status` and `--state`, so it reaches the gates a person typed and not a feature's bare check | **say it in one line and offer `/agent-kit:blueprint`**, which walks `${CLAUDE_PLUGIN_ROOT}/verification.yml` with the owner. **Never ask it yourself**: `project.yml` is `blueprint`'s to write (`rules/channels.md`), so a question asked here would have nowhere to put the answer and would be asked again on every run for ever. Not a reason to stop, and never a reason to install anything mid-run — build with what this project answered for, and say in the report which kind would have caught this change and was not there. **An `epic` is the exception and refuses to start**: it runs dozens of features against these answers with nobody watching |
| a run file at a step no reader knows, or fields the template does not have | history from an earlier run, and not a reason to stop. It is said so the drift is visible while it is still happening |
| **knowledge written by an older kit** — a record declaring fewer fields than the template, a file with fewer sections | **not a reason to stop, and not yours.** Say it in one line with the count, so the owner learns it exists, and carry on: the entries you are about to build are answerable as they stand, they were written that way on purpose, and only `/agent-kit:blueprint` may change what a record requires. Never fill the missing field yourself — that is deciding what the product must describe, which is the one thing no build command may do |
| nothing | continue without a word about it |

## A run is already in flight here

The check prints it before anything else: a line per run, with its slug, its command and the step it
is on. It is a statement and never an exit code — what to do with it is here.

**Ignore it entirely if you are that run.** A session the driver started was given a run directory —
`--run`, `--frame`, `--close`, `--advance`, `--resume` — and is inside the thing the line describes.
The check marks the line `this session` where it can tell, and where it cannot, the flag you were
invoked with is the answer. A child that refused to build because its own batch was in flight would
be the funniest way yet to lose a night.

**Otherwise, if a person typed this command, do not start.** Say which run holds the checkout and
what step it is on, and stop. That is `ship`, `fix`, `sprint`, `epic` and `next` — everything that
writes code or moves a branch. `blueprint` and `advise` are not on that list and never stop: they
write no code, and knowledge dictated at midnight is worth more than the wait.

**One checkout, one writer, and that is the whole reason.** The driver starts every child in the
project's own directory, so a second build there moves the branch under a session that is mid-task.
Measured on 17 August 2026: a second session took the tree forty seconds after a feature's session
had it, and that feature spent the next twelve minutes rebuilding itself in a worktree it invented
on the spot. Nothing was lost, and nothing about that was work. `next` is on the list for a
different reason — it deletes delivered branches, and a chain's branch counts as delivered only
after the batch's own pull request merges.

**What to offer instead**, in this order: wait for the run — the check said what step it is on;
or, if the work touches no code, take a tree of its own, which is what `blueprint` does
(`git worktree add ../<name> <branch>`). The guard hook refuses to move this checkout's branch from
a session the driver did not register, so the offer is also the only way through.

**The owner overrules this in one sentence.** If they say build anyway, say what it costs and then
work in a worktree rather than in the run's tree.

## Before you start, say what has piled up

The row above settles the blocks **on the entries in scope**, which is right and is not enough: a
decision under an entry nobody is going to build in again is settled by nobody, ever. The check
counts those separately — *of those, 47 in 19 entries already `built`* — and that number is the one
an owner has no other way of seeing.

**Only where a person just typed the command.** That is the gate of a run they started themselves —
`epic`, `sprint`, a `ship` by hand — and nowhere else. A session the driver raised is not the
moment, whatever `gate` says in the file it reads: an `--advance` deciding what follows, a `--resume`
picking up a dead run and a closing session all run with nobody watching, and a question put there
stops the run until morning. If you did not receive this command from a person, this section is not
for you.

So at that gate, **once per run and before any work starts**:

- **say the count in one line**, both numbers, whatever else is on the screen;
- **and put it up as a choice**, per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`: settle the blocks on
  this run's own entries now (minutes, and the recommendation), hand the lot to
  `/agent-kit:blueprint` first, or go and build as it stands. Whatever they pick, it is asked once —
  a command that raises this again per feature is the alarm nobody hears by the third batch.

With `gate: none`, and in every session the driver started, this section does not exist: there is nobody to ask, the blocks are followed as
written, and the run leaves its own for the owner to meet in `accept`.

**Why insist here of all places.** A build command is the last cheap moment: what was decided
without the owner is about to be built on, and after that a *no* costs a new run instead of an
answer. The same insistence in `next` would be noise — advice between tasks is easy to scroll past —
which is why that ladder deliberately does not fire on open blocks alone.

**Promises the product does not keep are read differently by each command**, so that row lives in the
command rather than here: `ship` reads the marked test for the entry it is about to touch; `sprint`
counts them, and with no theme offers them as a batch of their own.

Two things this table never does. It never turns a finding into a reason to stop, except the first
row — everything else is a statement about the project, and a command that halted on one would be
halting over its own memory. And it never rewrites what an entry *requires*: settling a block means
writing down an answer the owner has just given, and nothing else.
