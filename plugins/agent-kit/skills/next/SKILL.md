---
name: next
description: Where the project stands and what to do next — reads the state of the work and the knowledge, and names one command with the reason. Decides nothing and runs nothing. Use after a break, at the start of a session, or whenever the next step is not obvious.
argument-hint: ""
disable-model-invocation: true
---

# Next

The owner has been away and does not remember where they stopped. You read what happened while they
were gone and answer one question: **what is the next command, and why that one.**

Every other command in the kit ends by naming a next step, and that works while the session is still
open. This one exists for the cold start — a week later, in a new session, with nothing in context.

**You change nothing and start nothing.** Not a branch, not a file, not another command. You read,
you rank, you say one line. The owner runs it.

The single exception is the bookkeeping you just did: when you establish that an audit's box is
closed — the entry is built, the pull request that closed it is merged — **tick it**, right then:
`- [x]` with the pull request that closed it, in `docs/audits/<lens>.md`, in the project's
language. You are the one holding the evidence, and if you
leave it unticked every later run repeats the same comparison and the list keeps lying. Tick only
what you verified; a box ticked on a guess costs more than one left open.

## Read this much and no more

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --state
```

That is the whole mechanical half: the knowledge findings, what is `planned`, the debt, unkept
promises, open notes — and then branches with their drift, pull requests with their CI, runs left
mid-flight, and when each lens last ran.

Two things it does not carry, and you read them yourself only when the ladder below reaches them:

- the newest audit work list, when its lens is what you are about to recommend — the unticked boxes
  only, to say how much work it is;
- `docs/technical_debt.md`, when the debt is what you are about to recommend — the first few lines,
  to name one.

**And one narrow licence beyond that: settling whether a list is stale.** An audit's box may have
been closed by a batch that never ticked it, so for the items you are about to offer as work, check
whether they are already done — the entry's state line, or the diff of the pull request that landed
since the list was written. That is the difference between warning the owner that a list might lie
and telling them which eight of eleven items are finished, and it is worth the minute it costs.

**Everything else stays shut: no walking the code, no reading entries for their own sake, no
transcripts, no run logs.** A defect in the product is the audit's find, not yours; going looking
turns seconds into an afternoon and this into a command nobody runs before deciding.

**Whatever you do name, name it from an open file.** Searching for a word and citing the first file
it appears in is how a finding lands on the wrong line — the word is in five places and the sentence
that matters is in one. If you have not opened it, say the thing without the citation.

## The ladder

Top down, and the first rung that fires is the recommendation. The order is the cost of leaving it
alone, not what is most interesting.

| # | What you see | Why it comes first | What you name |
|---|---|---|---|
| 1 | uncommitted changes, or a branch never pushed | that work exists on one machine only, and everything else will bury it | commit it or throw it away, by hand |
| 2 | a run left at a non-terminal step | its branch is alive and nobody is on it; a new batch would fork past it | `/agent-kit:sprint --resume <dir>` or `/agent-kit:ship --run <dir>` |
| 3 | an open pull request, CI green, no conflicts | everything started from now on forks from a stale base | merge it |
| 4 | CI failing — on a pull request or on the default branch | it breaks whatever starts next | `/agent-kit:fix` |
| 5 | a pull request with conflicts, or one never reviewed | it looks finished and is not | resolve, or review it |
| 6 | somebody is waiting: a run's `waiting_on`, open `[assumed …]` on entries about to be built | the answer is cheapest while the context is warm | answer it, or `/agent-kit:blueprint` |
| 7 | knowledge not ready: a slot `open_question`, empty fields, a stale `source:` | a run over that entry invents the missing half | `/agent-kit:blueprint` |
| 8 | a blind spot: a lens that never ran, or ran long ago; scenarios with no end-to-end test | not knowing what is broken is not the same as nothing being broken | `/agent-kit:audit <lens>` |
| 9 | debt, unkept promises, unticked audit boxes | it only gets more expensive | `/agent-kit:sprint` with no theme |
| 10 | entries still `planned` | the product is unfinished | `/agent-kit:sprint` or `/agent-kit:ship <key>` |
| 11 | none of the above | say so | nothing |

Three overrides, because a ladder read literally lies:

- **No `docs/knowledge/` at all** — the ladder collapses: the answer is `/agent-kit:blueprint`,
  whatever else is true.
- **An empty repository** — the answer is `/agent-kit:mvp`, not a single feature.
- **MVP bounds not reached** — rungs 9 and 10 swap: unbuilt entries inside the bounds come before
  debt. Paying down debt in a product that does not exist yet is optimising a thing nobody has run.

Rungs 2, 3 and 9 all have a trap, and it is the same one: **a list can be stale.** A run left at
`step: build` whose branch is thirty commits behind is not "carry on", it is "start again". An audit
box may already be closed by a batch that never ticked it — so settle it rather than suspecting it:
check the entry, tick what is done, and offer the owner the remainder. "Eight of these eleven are
finished, three are left" is an answer; "some of this may be stale" is homework.

## What you say

Three blocks, always in this order, in the project's language.

**Where it stands** — five or six lines of fact, no adjectives: the branch and the tree, the open
pull request and its CI, runs left mid-flight, the counts of debt, unkept promises and `planned`,
and when each lens last ran.

**What is in the way** — up to five findings, ladder order, one line each. Nothing beyond five: this
is a starting point, not an audit.

**Next** — one line, the command filled in, the reason in a clause:

```
дальше: смержи #21 — пока он висит, каждый следующий прогон ветвится от устаревшего main
```

Then two or three alternatives, one line each, so it is visible what was weighed and passed over.
Never a menu of equals: a list of options hands back the decision along with the work of making it.

If the honest answer is that nothing needs doing, say that in one line and stop. A recommendation
invented to fill the slot is worse than silence — it is the one thing the owner cannot check.
