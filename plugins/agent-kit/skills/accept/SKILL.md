---
name: accept
description: Take delivery of a finished run — read its pull request and its run files, and say in one line whether it can be merged, then what needs hands and in what order. For the moment a long autonomous run has ended and its pull request is too big to read.
argument-hint: "[pull request number]"
disable-model-invocation: true
---

# Accept

A run that lasted a day ends with a pull request its owner cannot read. Measured on one: 157 000
characters, 40 000 lines of diff, seventy decisions taken without them, two questions waiting, one
test deliberately red. Every one of those was recorded honestly and none of them was findable.

This command is the reader those records never had. **It changes nothing and it decides nothing** —
it says what is there, in the order a person has to act on it.

Run it before merging, and again afterwards: the first time it answers *can this be merged*, the
second it is the list of what to go and do.

## You do not read the diff

That is the boundary, and it is what keeps this from being a second review. The diff was reviewed
per feature against the entry it was built from, and reviewed again as a batch. Forty thousand lines
would cost what another batch cost, to repeat a pass that already happened.

Read exactly this, and stop:

```bash
gh pr view <n> --json title,body,mergeable,statusCheckRollup
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --state
```

Then the run's own record — `docs/runs/*.json` for the batches, and `.agent-kit/runs/*/run.json`
while they are still on this machine, for `answers`, `unmet`, `manual`, `blockers`, `deviations` and
whatever a child left in `notes`. The pull request is prose; those are records, and where the two
disagree the record is what happened.

**Never guess a value out of the prose.** If the body says a suite was green and no run file says
what it returned, that is a thing you report as unproven, not a thing you round up.

## What you say

Six blocks, in this order, in the project's language. The order is what a person has to do, not
what the run found interesting.

**1. The verdict, one line.** *Mergeable now* — nothing blocks it and the manual actions can follow.
*Mergeable after N steps* — name them by number. *Not mergeable* — one reason, the first one. CI
that is red or a branch with conflicts makes this line, whatever else is in the body.

**2. Manual actions, numbered, in the order they must be done.** Each: what to do, where, and **how
to tell it worked**. A secret goes somewhere and something starts working; say which. These come
from the runs' own `manual` records — what, where, `proof`, `when` — merged and ordered, never
re-derived from the pull request's prose. Where a run file is gone from this machine and only the
body is left, say that the list is the body's and could not be checked against a record.

**3. What is waiting on a decision.** Every `waiting_on` that timed out, every fork the run took as
an assumption *because* nobody was there, and anything the body names as the owner's to settle. Each
with the two sides and which you would take, because a question handed over without a recommendation
is work handed over.

**4. Decisions taken without them.** Not seventy lines. The expensive ones by name — stored data,
permissions, money, a public contract — because those are the ones that cost something to reverse
later, and the rest as a count with where they live. `check.py` names the entries carrying them.

Then **offer to settle them, here, before the merge** — not as a report, as the question this
command exists to make cheap. It is the run's own blocks, not the project's pile: nine, not fifty.
Two things make this the right moment and no other. The owner is holding the run's output and has
just read what it decided; and **the branch is still open**, so a *no* is a fix in this pull request
rather than an entry put back to `planned` and a run of its own.

You do not write it. **`accept` changes nothing** — that is the boundary that keeps it cheap, and it
has not read the diff, so it cannot tell what an answer breaks. The offer hands over to
`/agent-kit:blueprint`, narrowed to this run's blocks, which owns the prose and may put an entry
back to `planned` when the answer says the build was wrong. Stopping halfway costs nothing: what is
not answered stays a block.

**5. What is not proven.** Tests marked `agent-kit:unmet` and what each waits for; scenarios inside
the bounds with no end-to-end test and why; and — the one nobody writes down — **what was never
exercised at all**. A run whose every proof went through a stand-in has proved the stand-in. Say
which parts of the product have never run against the real thing.

Two things belong in this block by name, because both are the owner's to settle and both are
routinely absent from a run that reports itself green:

- **the suite on a machine other than the one that wrote it.** A project with no CI has never had
  its tests run anywhere else, and *green* then means green where it was written. Name it as
  unproven, and the worktree in block 6 is where it is settled.
- **every seam that was proved against a stand-in.** Name them one by one: the gateway, the sign-in,
  the clock, the delivery. Measured on one run, the real model was never called once in thirty hours.

**Do not send them to review the diff.** It was read by `agent-kit:reviewer` against the entry each
feature was built from, and by the audit's lenses over the whole branch with the knowledge in hand.
A third pass, cold, over tens of thousands of lines returns a list nobody can act on before merging.
Where a run's diff really is small — one batch, one topic — its own pull request already offered
that, and this is not the place to offer it again.

**6. How to look at it.** The worktree command, so the tree the run shares is not pulled out from
under it, a free port if the project already has an instance, and the first scenario to click
through. One walk, not a tour.

Then stop. No summary of what was built — the pull request has that, and repeating it is how this
becomes a second document nobody reads.

## What you may write down

The same two facts `next` may, and nothing else, each in its own `docs(...)` commit: an audit's box
whose work you verified is done, naming the pull request; and an entry still `building` whose pull
request has merged — `check.py --sync`. Both only on a clean tree.

Everything else you found is a sentence in your report. **This command does not fix, does not
merge, does not answer its own questions, and does not open anything.**

## Closing

Per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is thin rather than what was done, then the one
line naming what to run next — usually the merge, or `/agent-kit:blueprint` for the prose a run was
not allowed to write.
