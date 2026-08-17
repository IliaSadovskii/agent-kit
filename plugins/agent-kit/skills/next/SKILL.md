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

**With a run of this kit in flight here, you do not run either.** The check prints it first; say
which run holds the checkout and what step it is on, and stop. The four bookkeeping writes below
are exactly the ones a live run cannot survive — `--sync` writes into knowledge and leaves the tree
dirty under a session mid-build, and a branch this command deletes as delivered may be the base the
next feature in the chain is about to fork from. The rule and what to offer instead are in
`${CLAUDE_PLUGIN_ROOT}/rules/preflight.md`, under *A run is already in flight here*.

The single exception is bookkeeping that has already happened somewhere else. **Four facts, and only
these four, you may write down where they belong:**

- **a manual action the owner has already done.** Every line in `docs/manual.md` carries a command
  that exits 0 once its work has happened, so this is the one of the four you do not have to judge
  at all — run them and let the lines that pass go:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --manual
  ```

  **First, before you read anything else**, because the answer changes what you are about to say: an
  action that is done is not something to put in front of them again. You are the reason this list
  is ever refreshed — the closing session writes it and never comes back, `accept` runs at delivery
  and not afterwards, and you are the command somebody types after a week away. Left to nobody, a
  line the owner cleared on Monday is still being printed by every command on Friday. Say the count
  you removed and nothing more; what is left belongs in *What is in the way* only when its `when`
  has arrived.

- **an audit's box whose work is done** — tick it right then, per
  `${CLAUDE_PLUGIN_ROOT}/rules/audit-boxes.md`, which is where the evidence, the form and the commit
  are. You are one of the three allowed to.
- **an entry still marked `building` whose pull request has merged.** The check names these on
  every run; moving the line is one command, and until somebody runs it the knowledge says a
  finished feature is still in flight:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --sync
  ```

- **a branch its pull request already delivered.** The check names them and how many, and you are
  the only command allowed to remove one:

  ```bash
  git branch -D <branch>… && git push origin --delete <branch>…
  ```

  Only what the check calls delivered, by name, and never a branch it could not judge — it says
  which those are and why, and one left standing costs a line in a listing while one deleted on a
  guess costs work nobody can get back. Say the count in your answer. This is the fourth answer
  every mechanism of this kit owes and branches never had: a run makes one, a batch delivers it,
  **and you are where it ends.** Measured on one project, nobody had that answer and it reached 99
  branches — 51 of them unanswerable by any git question, because the run's pull request was
  squashed and their commits are nowhere in the base branch.

You are the one holding the evidence in all four cases, and if you leave them the next run repeats
the same comparison and the lists keep lying.

All four go straight to the default branch, with no pull request: none is a decision anybody needs
to approve, each is a fact catching up with itself. Which is exactly why they are fenced:

- **only those four things** — the boxes in `docs/audits/*`, an entry's `state:` line, a delivered
  branch, and a manual action whose own proof says it happened. Not a line
  of anything else in that commit, or the next run will fix "just one more thing" in the same
  breath. The prose of an entry is never yours: `blueprint` owns it, and a state line that is right
  beside stale prose is still worth moving;
- **its own commit** — `docs(audits): …`, `docs(knowledge): …` or `docs(manual): …`, so it reads as
  bookkeeping in the history rather than hiding inside work;
- **switch branches only when it costs nothing**: a clean tree and a current branch already merged.
  Otherwise leave the boxes alone and say it — *ten of eleven are closed, I will tick them when the
  tree is free* — because moving somebody off their branch is a bigger intrusion than a stale list;
- **a rejected push is an answer.** If the branch is protected, keep the commit local, say so, and
  do not go looking for a way around it. A command that changes nothing does not argue with branch
  protection.

## Read this much and no more

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --state
```

**Read first, without `--sync`.** This run tells you everything, including which entries are behind
their merged pull requests — `--sync` comes after, as the fenced bookkeeping above, and only when
the tree is clean. A command whose first rung is *uncommitted changes* does not start by making
some.

**`--manual` is the exception and runs before this**, for the reason above: what it removes changes
what this reading prints. It writes only to `docs/manual.md`, and only lines whose own command says
the work is done — so on a tree that is not clean, keep the change and say you did rather than
leaving a list you have already proved wrong.

**And never `--offline`** — rungs 3, 4 and 5 are entirely about open pull requests and their CI,
and a run that cannot see them walks past the most urgent thing on the list. It is a test seam, not
a setting, and no longer appears in `--help`.

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
| 2 | a run left at a non-terminal step | its branch is alive and nobody is on it; a new batch would fork past it | **the command the check printed beside it** — see below |
| 3 | an open pull request, CI green, no conflicts | everything started from now on forks from a stale base | merge it |
| 4 | CI failing — on a pull request or on the default branch | it breaks whatever starts next | `/agent-kit:fix` |
| 5 | a pull request with conflicts, or one never reviewed | it looks finished and is not | resolve, or review it |
| 6 | somebody is waiting: a run's `waiting_on`, open `[assumed …]` on entries about to be built | the answer is cheapest while the context is warm | answer it, or `/agent-kit:blueprint` |
| 7 | knowledge not ready **for the work you are about to name**: a slot `open_question`, empty fields, a stale `source:`, an open block on the very entry you would recommend building | a run over that entry invents the missing half | `/agent-kit:blueprint` |
| 8 | a blind spot: a lens that never ran, or ran long ago; scenarios with no end-to-end test | not knowing what is broken is not the same as nothing being broken | `/agent-kit:audit <lens>` — **unless the work below runs that lens itself**, see under the table |
| 9 | debt, unkept promises, unticked audit boxes, decisions nothing will reach | it only gets more expensive | `/agent-kit:sprint` with no theme — or `/agent-kit:epic` when there is a lot of it |
| 10 | entries still `planned` | the product is unfinished | by how much is left: one `/agent-kit:ship <key>`, a `/agent-kit:sprint` of about five, or `/agent-kit:epic` for the rest of them |
| 11 | none of the above | say so | nothing |

**Rungs 9 and 10 are one judgement in two rows, and it is about size.** One entry is a `ship`; about
five on one topic is a `sprint`; a whole list is an `epic`, which takes it, audits what it built and
proves it, as one pull request. Say which of the three you mean and why, with the count: *seven
entries left — `/agent-kit:epic`, it asks one question and runs the rest unattended*. Naming the
command without the count leaves the owner to guess at a day's work.

**And `planned` is never one number.** The check prints the split — the owner's own lists out of
`product.md`, with their own labels and the keys on each: what is waiting inside the MVP bounds, what
was deliberately deferred to a later version, what was put outside. Read that line before you name
anything, because the three are answered differently:

- **inside the bounds** — offer it, whatever its size;
- **a later version** — offer it when the bounds are closed, and say the bounds are closed, since
  that is the owner's own condition for starting it. It is the ordinary next thing on a finished MVP
  and not a request to jump ahead;
- **outside** — never offer it. The owner ruled it out and a command that puts it back on the list is
  arguing with them from a count.

Two things this closes, both measured on a live project on 17 August 2026. An epic offered *every
`planned` entry* would have taken three the owner had put outside — its gate takes a named list for
exactly this reason, so name one rather than accepting the default. And one entry still inside the
bounds was read as *the MVP is not finished*, which is what stopped an epic being offered at all: the
bounds are one entry from closed, and the whole next version was described and waiting.

**An open block is not by itself a reason to recommend `blueprint`.** Every batch leaves some, and a
ladder that fires on them recommends the same command after every sprint until the owner learns to
ignore the recommendation. A `[stale …]` carries its own correction under the entry, so no run is
misled; an `[assumed …]` is a decision already taken and already in a merged pull request. Both are
settled by the next command that builds in that entry, with the owner present, and the check names
them there. Report the count in *Where it stands* and go on down the ladder — unless the entry you
were about to recommend is the one carrying the block, which is rung 7.

**The exception is the block nothing will ever reach**, and there are two kinds of it.

The first is `[assumed …]` under an entry already `built`. The reasoning above — *the next command
that builds in that entry settles it* — is a promise about a run that is coming; under a built entry
with nothing planned in it, no run is coming. The check counts them apart from the rest for exactly
this: *of those, 47 in 19 entries already `built`*. That count is rung 9 work, named with the number
and `/agent-kit:blueprint`. It cannot become noise, because it only grows when work **finishes** and
it goes to zero after one pass — a fresh batch's blocks sit under entries the run will return to,
and those do not count.

**And `[accepted …]`, because nothing else will ever reach it either.** The other
three sit under an entry, so a run that returns there settles them in passing — where one is coming. This one is
waiting *for* an entry: the owner agreed to something and its fields were left for later, so there is
nothing to build in and no command that arrives by accident. Left alone it stays for ever, and the
work it stands for is invisible to `sprint`, to `epic` and to rung 10. Treat any open one as rung 9
work and name `/agent-kit:blueprint`, saying how many and from which lens.

**Rung 8's other half: nothing outside a session runs the suite at all.** The check says it in one
line under `--status`, and `check.py --tests` says which command is in which state. That is the
purest blind spot there is — every proof the project has was made by the session that wrote the code,
on the machine that wrote it, and nothing re-checks it after the session is gone or when the owner
pushes by hand. What you name is **an ordinary `ship` with a task**: *build the CI that runs this
project's declared commands*, from `${CLAUDE_PLUGIN_ROOT}/templates/workflow.yml`. Not a command of
its own — the kit builds a project's infrastructure the same way it builds its skeleton, a build step
or a dependency bump: one `ship`, no entry, the task says what done means. It proves itself on the
spot: the run pushes its branch, the pipeline fires on that very branch, and step 6 of `ship`
already reads `gh pr checks`.

**Say it once and then let it go.** Like every rung, it fires until it is answered — so name it, and
if the owner passes over it, do not raise it again ahead of the work on the next run. A rung that
repeats itself nightly is the alarm nobody hears by the third batch.

**Rung 8 is about nobody looking, not about coverage being incomplete.** An `epic` runs the lenses
itself — `deps`, `security` and `conventions` over the whole codebase, `tests` and `scenarios`
narrowed to its own entries — so where rung 10 would name an epic, that lens is *being looked at* and
rung 8 does not fire on it. What the epic will not reach is real and is not the recommendation: it
goes in *What is in the way* as one line, and into the recommendation as a clause — *catch it after,
with `/agent-kit:audit scenarios`*. Naming an audit that the next command performs anyway costs a
night twice, and the lens then walks unchanged code, which is the thing every rule about waves
forbids.

Measured on a live project on 17 August 2026: four scenarios of thirteen had no end-to-end test, so
this rung fired and named `/agent-kit:audit scenarios` — while seven entries the owner had dictated
the day before sat at rung 10 and an epic was about to audit most of them on its way. The owner had
to say so twice. Only one of those four scenarios was outside what the epic would walk.

**Rung 2 is four kinds of run, and the check names which command each one takes.** `--state` prints
it beside the run: `/agent-kit:epic --resume <dir>` for a whole scope, `/agent-kit:sprint --resume
<dir>` for a batch, `/agent-kit:ship --run <dir>` for a feature, and for an errand the prompt it was
started with — which carries what nothing else can know, an audit's lens being the case. Read it
rather than deriving it: this row used to name two of the four and left the epic out entirely, so a
run at `auditing` or `proving` — an epic mid-flight, in a phase no other command has — was offered
the command that drives a batch. Where the check says nothing can say which, say that: a run whose
kind is unreadable is a thing to look at by hand, not a command to run.

Three overrides, because a ladder read literally lies:

- **No `docs/knowledge/` at all** — the ladder collapses: the answer is `/agent-kit:blueprint`,
  whatever else is true.
- **An empty repository** — the answer is `/agent-kit:blueprint`, then `/agent-kit:epic`, which
  builds the MVP bounds it just wrote. Its gate is one screen and one question, so recommending it
  costs the owner a conversation, not a night.
- **MVP bounds not reached** — rungs 9 and 10 swap: unbuilt entries inside the bounds come before
  debt. Paying down debt in a product that does not exist yet is optimising a thing nobody has run.
  **It is about a product that does not run yet, not about a count above zero.** One entry left
  inside the bounds is a finished MVP with a correction outstanding, and this override does not fire
  on it — a live project had exactly that, and reading it as *the MVP is unfinished* is what kept the
  next version from being offered at all.

Rungs 2, 3 and 9 all have a trap, and it is the same one: **a list can be stale.** A run left at
`step: build` whose branch is thirty commits behind is not "carry on", it is "start again". An audit
box may already be closed by a batch that never ticked it — so settle it rather than suspecting it:
check the entry, tick what is done, and offer the owner the remainder. "Eight of these eleven are
finished, three are left" is an answer; "some of this may be stale" is homework.

## What you say

Three blocks, always in this order, in the project's language.

**Where it stands** — five or six lines of fact, no adjectives: the branch and the tree, the open
pull request and its CI, runs left mid-flight, the counts of debt, unkept promises and `planned`,
and when each lens last ran. Manual actions belong in this block and not below it — how many are
still waiting, and how many you cleared as already done. They are a fact about the project, not
something in the way of the work: what is in the way is one at `before_run`, because nothing starts
without it.

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
