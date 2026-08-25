# S8 — parallelism

Written before building it, 26 August 2026, the way S5, S6, S7 and S7a were written before
them, so the next session starts from decisions rather than from a blank page. S0–S7a are
done: the package, the state, the step contract, Claude Code at level B, one feature end to
end, a bench of forty-five traps, the knowledge written by the program, a machine that counts
its own sessions, and a question that reaches a phone and changes what gets built.

The plan's own words, from the build order:

> **S8 · Parallelism.** A worktree per child, waves from the `needs` graph, several branches
> merged in an order the program decides. *Done when* a batch of three features that depend on
> nothing builds at once and all three land.
>
> Two things earlier steps deliberately left for this one, because neither has a unit until
> batches exist:
>
> - **Skip** (open question 9). S7 built stop and refused to build skip beside it: *its unit is
>   a feature inside a batch, and there are no batches until S8.*
> - **The machine's own ceiling is not queued.** S7's queue orders waiters per account. Two
>   runs waiting on *different* accounts, both held back by `machine.max_sessions`, are ordered
>   by whoever polls first rather than by who asked first.

Three things, then: the batch, the tree, and the two debts. Everything below is in service of
the sentence the step is done by.

---

## 1 · What is actually missing today, read rather than remembered

**Two runs in one project destroy each other's work.** `deliver` checks the branch out in the
project itself — S4 wrote that down as correct for one child and a collision for two. Today a
second `run go` in the same repository is not refused by anything: the ledger refuses a second
driver on *the same run*, and two different runs share one working copy, one HEAD and one index.
The first one to reach `deliver` moves the branch under a session that is still editing files
for another feature. Nothing in the kit notices, and the record of both runs says everything
went well.

**A night is one feature long.** `run go` walks one run's steps and stops. There is no shape at
all for *the work of one evening* — several features, some of which build on others. The second
version had one (an epic, a batch record, `needs`), and the third has read its measurements and
built none of it, because until now there was one child.

**A feature that depends on another has no way to say so.** A run knows its slug, its brief and
its branch. Two features where the second builds on the first can only be run one after the
other by a person who remembers the order, and the second one's sessions are never shown what
the first built — so they design it again, from the trunk, as if it were not there.

**Skip has nothing to skip and the queue has nothing to be fair about.** Both were named by S7
and refused on the same ground: no batches, so no unit. That ground goes away here.

---

## 2 · The central decision: a batch is a graph of runs, and a run is what it already was

The temptation is a new kind of thing — a batch with its own steps, its own contract, its own
state machine. Refused, for the reason the whole version is built on: **a run is already the
unit that works, and it has been proved by every step since S4.** A batch adds exactly two
facts to it — *what it may not start before*, and *what it builds on top of* — and one process
that reads them.

So:

**A batch is a file that names features and the edges between them. Each feature is an ordinary
run. The batch driver starts one driver per run — a process, exactly as the plan draws it — and
decides only which of them may start now.**

Four consequences, and each of them is why this shape rather than another:

1. **Nothing in a step, a contract, an adapter or the ledger learns what a batch is.** A run
   inside a batch and a run started by hand go through the same code. The mechanisms S4 to S7a
   proved keep being the ones that run.
2. **The ceiling is already enforced.** S7's ledger counts live sessions across processes and
   projects. Ten children asking for slots at once is the case it was built for and measured
   on; the batch driver counts nothing.
3. **One writer per run, kept.** Each child driver is the only writer of its own `run.json`;
   the batch driver writes only the batch's own file and never a run's.
4. **A batch that dies is a batch that is resumed by reading files.** Every fact is on disk in
   the shape it already had — the run files say where each feature got to — so `batch go` on a
   half-done batch carries on rather than starting again.

The four questions, answered where the mechanism is written:

| | |
|---|---|
| Can this be a program instead? | It is one, entirely. Nothing about ordering, basing or merging is prose in a role's file, and no session is told which feature comes first. |
| What trace does it leave? | `batches/<name>/batch.json` — every feature, its state, its tree, the hour it started and ended; the run files themselves; a `batch` lease in the ledger while it runs; and one message to the owner when it is over. |
| What composes its input? | The batch driver encloses what a feature's dependencies already designed and built. A session is never sent to go and look at another feature's branch. |
| Who reads what it writes? | The batch driver (the ready set), `deliver` (the base of the pull request), the page and `machine` (what is running), the owner (the news and the merge check). |

**What becomes impossible:** two runs editing one working copy; a feature built on a
dependency it was never shown; and an evening's work whose order lives only in a person's head.

---

## 3 · The worktree, and it is the core of the step

`git worktree add` gives a run its own checkout of the same repository — its own HEAD, its own
index, its own files — sharing one object store. That is the whole mechanism, and it is what the
plan means by *a worktree per child, in the core*.

**Where it lives: `<project>/.agent-kit/v3/trees/<slug>`, ignored by git.** Three candidates
were weighed. A sibling of the project would put a checkout wherever the kit was standing when
it was created, which is a path nobody can find again. The machine's state directory would make
one project's code live under `~/.local/state`, and the plan's own table says that directory
holds what is true right now and dies with the machine — a half-built feature is neither.
`.agent-kit/v3/` is already the project's own kit directory, already ignored one level down for
`runs/`, and `git worktree list` prints these relative to the repository they belong to. The
ignore is written by the same call that writes the one over `runs/`, and it is written *before*
the first tree is made — a checkout inside an un-ignored directory is a repository that stages
itself.

**A tree belongs to a run and is addressed by its slug**, so a second driver on the same run
cannot get a second tree — and it is already refused a step earlier, by the run lease S7 built.

**A tree that git already holds for somebody else is a refusal, never a takeover.**
`git worktree add` fails when the branch is checked out elsewhere, and that failure is read and
named — `tree-held` — rather than worked around. The one case that is not somebody else's is our
own: a tree left by a driver that died, on the same branch, at the same path. That is
reclaimed, because a run that is being carried on is the run whose tree it is.

**A tree is removed when its run is `done`, and kept otherwise.** A finished feature's work is
committed and pushed, so the checkout is a copy of what the branch already holds. A run that
failed, stopped or was skipped mid-build has files nobody has read yet, and deleting them would
be the kit throwing away the only evidence of what went wrong. Where it is kept, the batch's
report says the path. `agent-kit tree list` prints what stands and `agent-kit tree remove <slug>`
takes one away, both of them thin over `git worktree`.

**What runs where.** The run's paperwork stays in the project: `run.json`, the step directories,
`asks.json`, `pull-request.md`. The *work* happens in the tree: the session's cwd, the commands
`verify` runs, the commit and push `deliver` makes, the knowledge `record` writes. Two places,
two owners, and the code says which is which by carrying both — `StepRequest` gains `tree`
beside `project`, and every executor that touches code reads `tree`.

---

## 4 · What a run learns, and the schema goes to 4

Three fields, each with a reader named before it is written — rule 5, and the only reason these
are not four.

| Field | What it is | Who reads it |
|---|---|---|
| `base` | the branch this run builds on and opens its pull request against | the tree (what it is checked out from), `deliver` (the `--base` of the pull request, and what "this branch holds somebody else's work" is measured against) |
| `tree` | the working copy this run builds in | the driver (the cwd of every session and every program), `run show`, the batch's report |
| `needs` | the slugs this run may not start before, and whose work it is shown | the batch driver (the ready set), `driver/compose.py` (the enclosure) |

`base` defaults to the project's default branch, which is what every run since S4 has had
implicitly. `tree` is empty for a run started by hand in the project itself — that is exactly
what a run is today and it must keep working, because `run go` with no batch around it is how
half the bench and every live check is done.

This is rule 4 of the build order — *a frozen shape is never quietly changed* — obeyed rather
than mentioned: **schema 3 → 4 goes in first, with its migration and its tests, in its own
commit, before anything else in this step is written.** A run file that names a tree must not be
readable by a kit that does not know what a tree is: `schema-too-new` is what says so.

**`deliver` gets the one fix this makes necessary.** It asks `git rev-list --count <base>..<branch>`
to find out whether a branch holds somebody else's work. With a feature stacked on another, the
project's default branch is the wrong `base` for that question — the dependency's commits are
"work that is not main's", and delivery would refuse its own stack by name. The run's own `base`
is the answer, and it is the same field the pull request opens against.

---

## 5 · The batch: a file the owner writes, a file the program writes

Two files, and confusing them is the defect this section exists to avoid.

**What the owner writes** is a declaration: features, briefs, edges. A batch of five features
with a brief each does not fit on a command line, and the evening it is composed in is the one
hour the owner spends on the kit. So it is a file, in the project, and `agent-kit batch new
<file>` reads it:

```toml
name = "2026-08-26-vat"

[features.rates]
brief = "A table of VAT rates, one row per country, read from config"

[features.quote]
brief = "Money quotes a price with VAT on it"
needs = ["rates"]

[features.receipt]
brief = "A receipt line naming the VAT that was charged"
needs = ["quote"]
```

One door, not two: there is no `--feature` flag beside this. Nine doors with nine checks is the
defect the plan measured, and a second spelling of one act is how it starts.

**What the program writes** is `.agent-kit/v3/batches/<name>/batch.json`: every feature, the run
it became, its state, its tree, when it started and ended, and why it did not. No agent edits
it, and neither does a person — same rule as `run.json`, and the same store behind it.

A feature's state is one of `pending`, `running`, `done`, `failed`, `stopped`, `skipped`. The
first five are the run's own, read back rather than kept twice; `skipped` is the batch's, because
a skipped feature may have no run at all.

**What is refused at `batch new`, before anything is created:** a `needs` naming a feature that
is not in the batch (`no-such-feature`), a cycle (`needs-a-cycle`, and it names the loop), a
feature whose slug is already a run in this project (`run-exists`), and a batch name already
taken. Nothing is written until all of it passes: a half-created batch is a graph somebody has
to repair by hand.

---

## 6 · Waves without a wave: the ready set

The plan says *waves from the `needs` graph*. Built literally — start a wave, wait for all of
it, start the next — that is a barrier, and a barrier makes the whole batch as slow as its
slowest member at every level. What is built instead:

**A feature may start when every feature it needs is `done`. The batch driver starts whatever is
ready, up to the machine's ceiling, and starts more as children finish.** With edges, that is a
wave; with none, all of them at once; and nothing has to decide which of the two this is.

**How many at once: `machine.max_sessions`, and not one more.** Not because the batch enforces a
ceiling — the ledger does that, and it is the only thing that may, since it is what other
projects share — but because a child that cannot possibly get a slot is a python process idling
in a poll loop. The ledger stays the authority; this is arithmetic about how many processes are
worth raising.

**A feature whose dependency did not end `done` never starts.** Its state is `stopped` with
`needed-<slug>`, said in those words, because *failed* would say the kit tried and could not.
Whatever needed *that* goes the same way, down the graph.

**The batch ends when nothing is running and nothing is ready.** Its exit code is 0 when every
feature is `done`, and otherwise the code of the first feature, in the order they were declared,
that is not — with the meanings those codes already have. A batch does not invent a code for
"some of it worked": that is what the report is for.

---

## 7 · Stacked, not merged — and a merge check that never merges

The plan says *several branches merged in an order the program decides*. There are two readings
and only one of them survives contact with what the kit already is.

**A feature is based on what it needs.** `quote` needs `rates`, so `quote`'s tree is created
from `kit/rates` and its pull request opens against `kit/rates`. That is the order the program
decides, and it is decided once — when the tree is made — rather than negotiated later. The
owner reviews and merges a stack, which is the shape they already work in, and each pull request
stays what S7a made it: a report about one feature.

**The kit does not merge anything into anything.** An integration branch the kit pushes is a
fourth thing for the owner to review and the first place the kit would be writing code nobody
wrote. Every branch reaches the owner as a pull request, and the merge button stays theirs.

**What the program does do is find out, at the end, whether they will merge at all.** Two
independent features that touched the same file conflict on GitHub in the morning, and the kit
is the only thing awake at 03:00 that could have said so. So: when the batch is over, in a
throwaway tree off the default branch, it merges each delivered branch in the order the graph
gives, `--no-commit`, and throws the tree away. What it reports is which pair conflicts and in
which files. It pushes nothing, opens nothing, and changes no branch. A conflict is not a
failure of the batch — both features are built and both are deliverable — it is a line in the
report and in the message the owner gets.

---

## 8 · Skip, and what it costs the things that needed it

Open question 9, and its unit exists now.

**`agent-kit batch skip <batch> <feature> <reason>`.** Two halves behind one door, the way
`run stop` has two:

- the feature has not started: it is marked `skipped` with the reason, and nothing is ever
  raised for it;
- a driver is running it: the stop is posted into the ledger exactly as `run stop` posts one,
  its own driver reads it at a step boundary and stops the run itself, and the batch marks the
  feature `skipped` when that child comes back.

**Whatever needed a skipped feature is skipped too, and the reason says so** — `needed-<slug>`.
This is the sharpest thing in the command and the one that has to be printed at the moment it is
typed: skipping `rates` skips `quote` and `receipt`. A person who wanted one feature dropped and
got three has been told before it happens, not afterwards in a report.

**Skip is a batch's word, not a run's.** There is no `run skip`: skipping means *do not build
this part of the night*, and outside a batch there is no night to take it out of. A run on its
own is stopped, which is a door that already exists and already works.

---

## 9 · Stop, news, and one phone

**`agent-kit batch stop <batch> <reason>`** posts one request. The batch driver reads it at the
same boundary it reads everything else — between starting children — stops every child that is
running by posting each a stop, starts nothing more, and leaves every unstarted feature
`pending`. Exit 130, which is what that code has meant since S0: the operator stopped it. A
batch that is stopped can be gone on with by `batch go` again, because nothing about it was
failed.

**One message, not five.** S7a made a run say so when it ends, and that was right when a night
was one run. A batch of five would wake the owner five times at 03:00. So a child driven by a
batch is silent about its own ending, and the batch sends one message when it is over: what
landed with its pull request, what did not with its reason, and what will not merge cleanly.

The silence is a flag with a reader and not an inference: `run go --silent` says *somebody else
is telling the owner about this run*, the batch driver is what passes it, and a run started by
hand keeps saying what it always said.

**A question is not news and is never held back.** A question has a deadline against a person's
twenty minutes; batching them would be inventing a second waiting mechanism on top of the one
S7a measured. Every child asks the owner directly, exactly as it does today.

---

## 10 · The machine's own ceiling, queued at last

S7's second debt. Its queue orders waiters per account: `_ahead_of` looks for an older waiter on
*the same account*. When what binds is `machine.max_sessions` rather than a provider's, two
waiters on different accounts are ordered by whichever polls at the right moment. With one
provider configured there was one account, and S7 refused to fix it on a guess. A batch across
two providers is what stops it being a guess.

**The rule: when the machine's own ceiling is what would refuse this request, the oldest waiter
of all goes first, whatever account it is on. When a provider's ceiling or a limit is what
refuses, the account's own queue decides, exactly as it does today.** One extra question asked
of the same table, in the same transaction, and the ordering stays *who asked first* in both
cases — which is the only ordering anything has measured a need for.

---

## 11 · Where the code goes, and which way the arrow points

```
batch/                what an evening's work is
  declaration.py      the file the owner writes, read and refused by name
  state.py            batch.json: the features, their states, one writer
  driver.py           the ready set, the children, the stop, the report
  merge.py            the check that never merges
driver/
  tree.py             a worktree per run: make it, reclaim it, take it away
```

`batch/` depends on `state/`, on `driver/` and on `machine/`. Nothing depends on `batch/` —
not the runner, not a step, not an adapter, not the ledger. That is the test of §2's claim that
a batch adds a layer above rather than a concept inside: if anything below has to import it, the
shape is wrong.

`driver/tree.py` sits beside the runner because a tree belongs to a run, not to a batch: a run
started by hand can be given one, and the batch is only the thing that always does.

---

## 12 · What changes in what already stands

| Where | What |
|---|---|
| `state/schema.py` | `Run.base`, `Run.tree`, `Run.needs`; schema 4 |
| `state/migrations.py` | 3 → 4, so a run that names a tree is refused by an older kit rather than misread |
| `driver/tree.py` | new — `git worktree` add, reclaim, remove, list |
| `driver/runner.py` | the tree is where a session and a program work; a run that has one is not run in the project |
| `driver/compose.py` | what the features this one needs already designed and built, enclosed |
| `providers/base.py` | `StepRequest.tree` beside `project` |
| `providers/process.py`, `providers/fake/adapter.py` | the cwd of a session is the tree where there is one |
| `programs/verify.py` | the project's commands run in the tree |
| `programs/deliver.py` | commit and push from the tree; the pull request opens against `run.base`; "does this branch hold somebody else's work" is asked against `run.base` |
| `programs/record.py` | the knowledge is written in the tree, so it is committed on the branch |
| `batch/` | new — the declaration, the state, the driver, the merge check |
| `machine/ledger.py` | the machine's own ceiling is queued across accounts; a `batch` lease so two `batch go` on one batch is refused by name |
| `cli/main.py` | `batch new/list/show/go/stop/skip`; `tree list/remove`; `run go --silent`; `run show` names the tree and the base |
| `daemon/server.py` | the page shows a batch as one row with its features under it |
| `state/store.py` | the ignore that keeps `runs/` out of git covers `trees/` too, and is written before the first tree |
| `errors.py` | no new exit code — see below |
| `bench/cases.py`, `bench/runner.py` | a case may declare a batch, and the runner drives it as one |
| `bench/cases/` | twelve new cases |

**No new exit code.** A feature that did not land ends with the code its own run ended with. A
batch stopped by a person is 130. A conflict found by the merge check is not a failure at all —
both features are built and deliverable, and the owner is told. Adding a code that means what an
existing one already means is the same defect the plan measured, from the other side.

---

## 13 · What the last three rounds taught, applied here

S6's holes were a list S7 worked from, S7's review added more, and S7a's added more still. Each
has a place here:

| What it was | Where it lands here |
|---|---|
| a judge green where the trap was never planted | every judge proves what it plants stood: the tree existed, the branch was there before the run, the file the other feature wrote is in this one's input |
| a green case whose two causes were the same place | *at once* is proved by the sessions meeting — each waits for the other's mark and both time out if they never overlap — and not by comparing two timestamps a second apart, which is S7's `the-machine-frees-up` in a new costume |
| a case that measured a sentence | every case reads a code or a name: `needs-a-cycle`, `no-such-feature`, `needed-rates`, a branch, a path |
| a fixture that encodes a moment rather than a shape | no case writes an hour; where one waits, it waits against something the case itself planted |
| a mechanism with no trap shipped broken | twelve mechanisms, twelve cases, each broken by hand afterwards |
| a new trap that was green against a broken kit | each of the twelve is broken by hand *before* it is called a trap, and where one cannot be — the note says so in words rather than counting it covered |
| green in the working copy only | the bench is run from `git archive HEAD` unpacked elsewhere before this is called done |
| commit before breaking things on purpose | the break-by-hand round starts from a clean tree and does not touch it |
| source and tests in one commit | tests are their own commit, before the one that makes them pass — and the schema change of §4 is its own commit before either |
| the same identifier twice half-wrote a file | every batch act is one transaction over one file, and skipping or stopping twice is the same as once |
| a trap that reported as a broken bench | every case's wait is well inside the bench's own timeout, and what it waits for is planted rather than hoped for |

---

## 14 · Where this is proved

Twelve traps. The bench becomes fifty-seven cases, and every one of them still costs nothing:
`providers/fake/` answers the sessions and the file channel answers the phone.

The bench itself learns one thing, and only one: **a case may declare a batch instead of a run.**
`case.toml` gains a `[batch]` block naming features, briefs and edges; the runner writes the
declaration, runs `batch new` and `batch go` instead of `run new` and `run go`, and `[expect]`
may name a per-feature state. Everything else — the world, the fake provider, the judges, the
`gh` that is a script — is untouched.

| Trap | The mechanism it must fire |
|---|---|
| three features that need nothing | all three land, with three branches and three pull requests, **and their build sessions met**: each waits for the others' mark and none of them times out |
| a feature that needs another | it does not start until that one is `done`, and its own input encloses what that one designed and built |
| a dependant's base | its tree is checked out from the dependency's branch and holds the file that feature wrote, and its pull request opens against `kit/<dependency>` and not against `main` |
| `needs` that names nothing | `batch new` refuses `no-such-feature` and creates no batch, no run and no tree |
| a cycle | `batch new` refuses `needs-a-cycle` and names the loop |
| a feature that fails | what needed it is `stopped` with `needed-<slug>` and never started a session; what did not need it lands |
| a feature skipped while the batch runs | it never starts, what needed it is `skipped`, the rest land, and the reason names the feature that was dropped |
| a stop while a batch is running | every running child stops with `stopped-by-request`, unstarted features stay `pending`, exit 130 |
| two features that change one file | each builds in its own tree, neither sees the other's uncommitted work, and both commits hold only their own change |
| two branches that will not merge | the batch's report and the owner's message name the conflicting pair and the file, and nothing was pushed or merged |
| a batch of two features ending | the channel holds exactly one message, and it names both features |
| two runs on two accounts, one slot | the one that asked first gets it, whichever polls first |

**One thing is proved by tests and not by a trap, and this is the record of that rather than a
claim it is covered:** a tree left behind by a driver that died and reclaimed by the next one.
Reaching it on the bench needs a run that outlives its own death, and the bench runs a batch
once. It is the same shape S7a had to write down about sweeping a question out from under a live
driver, and it is written down here for the same reason.

---

## 15 · What S8 is done when

`agent-kit bench run` reports all fifty-seven cases as fired; three features that depend on
nothing are built at once by three sessions that were alive together, and all three land as
three pull requests; a feature that needs another is shown what it built and opens against its
branch; a feature dropped from the night takes what needed it with it, and says so as it is
typed; two runs never touch each other's files; the owner is woken once for a batch and not once
per feature; and breaking any one of the twelve new mechanisms by hand makes exactly one case
say it did not fire.

**Deliberately not built:**

- **An integration branch the kit pushes.** The merge check reports; the merge button is the
  owner's. Nothing has measured that anybody wants the kit to write a merge commit.
- **A batch that reorders by anything but its graph.** No priorities, no estimated cost, no
  "cheap ones first" — the same refusal S7 made about its queue, for the same reason: nothing has
  measured that it matters.
- **A batch across projects.** A batch is one repository's evening. Two projects at once already
  work — that is what the ledger has counted since S7 — and they are two batches.
- **A feature added to a batch that is already running.** It is a second door onto the graph, and
  the first one costs one command to run again.
- **Retrying a failed feature inside the same batch.** The run's own three attempts and its
  fallback are the retry policy, settled with the plan; a second layer of retrying on top of it
  would be a mechanism nobody measured a need for.
- **S9.** The adapters are the next step and none of them is touched here.

---

# What was built, 26 August 2026

Everything above was built as decided, with two departures the note did not foresee and one trap
that was green against a broken kit until it was broken by hand. Fifty-nine bench cases all firing,
745 tests, and three features built at once by three sessions that were alive together.

## The sentence the step is done by, measured

`three-features-at-once` is the case, and what makes it a measurement rather than a hope is that
every build session waits for the other two before it may answer:

```sh
printf 'here\n' > "$BENCH/rates.here"
while ...; do
  if [ -f "$BENCH/rates.here" ] && [ -f "$BENCH/quote.here" ] && [ -f "$BENCH/receipt.here" ]; then
    printf 'met\n' > "$BENCH/rates.met"; exit 0
  fi
done
```

A kit that builds them one after another never gets past that line: the first session waits for two
that have not started, times out, and the run fails. Three branches, three pull requests, and three
`met` files is the whole of the plan's *done when*.

The same rendezvous is what makes `two-features-in-one-repository` mean anything: both sessions
append to `money.py` at the same moment, each checks that the other's line is **not** in its own
copy, and each commit holds only its own change. With one working copy that case cannot pass; with
a tree per run it cannot fail.

## The two departures

**A feature waits for one thing, not several.** The note says a feature is based on the branch of
what it needs and opens its pull request against it — and a pull request has one base. Two needs
would mean merging two branches into a third before the work starts, which is the kit writing a
merge nobody reviewed. So `needs-more-than-one` is refused at `batch new`, by name, with the reason
in the message. It is a real limitation and it is written down here rather than picked silently
from the list.

**A skipped feature takes what needed it *skipped*, not stopped, and a batch of skipped features
exits 0.** The first cut cascaded everything the same way and gave a skipped feature the exit code
of a failure. Both were wrong for the same reason: nobody tried to build these and nothing failed —
a person said not to. A night that did everything it was allowed to do exits 0, and the report says
which features the owner dropped.

## The trap that was green against a broken kit

`one-message-for-a-whole-batch` counted the batch's name in the channel file. Breaking `--silent` —
so that every child speaks for itself, which is the defect the flag exists to prevent — left the
whole bench green: a child's own message names its *run*, and the batch's name appears exactly once
whether one message was sent or three. The judge counts sends now (`^--- `), and the same break
makes it say so.

That is the S7a lesson in a new costume, and it was found the only way this kind of thing is found:
by breaking the mechanism, not by reading the case.

## Breaking the twelve

Each mechanism was switched off with the smallest edit that switches off only it, and the whole
bench was run against the broken kit:

| What was broken | What said so |
|---|---|
| the base is the branch of what it needs | `a-feature-built-on-what-it-needs` |
| what a feature needs is enclosed for its sessions | `a-feature-that-waits-for-another` |
| a need that names no feature is refused | `a-need-that-names-nothing` |
| a cycle is refused | `a-batch-that-waits-for-itself` |
| a skip is read while the batch runs | `a-feature-skipped-mid-batch` |
| a stop is read while the batch runs | `a-stop-while-a-batch-is-running` |
| the merge check | `two-branches-that-will-not-merge` |
| one message for the whole batch | `one-message-for-a-whole-batch` |
| the queue across accounts | `the-oldest-waiter-goes-first` |
| a stalled feature's tree is kept | `a-feature-that-does-not-land` |

Ten of the twelve light exactly one case. Two light several, and both are one mechanism seen from
its sides rather than a case measuring the wrong thing:

- **children start together** (`one-at-a-time`) reddens `three-features-at-once`,
  `two-features-in-one-repository` and `a-feature-skipped-mid-batch`. All three are about what can
  only happen while two sessions are alive at once; a case that covered all of it could not say
  which side broke.
- **a feature waits for what it needs** (`needs-ignored`) reddens five, and **a tree per run**
  (`one-working-copy`) reddens eight. These two are the spine of a batch: without them a dependant
  designs against a branch that holds nothing, and two runs fight over one HEAD. Every case with an
  edge in its graph, or two features in it, is a case about them.
- **the cascade** (`no-cascade`) reddens the two cases that have a dependant to cascade to.

The bench was also run from `git archive HEAD` unpacked elsewhere — the check that caught S5's
blocker — before this was called done.

## What the bench had to learn, and what it cost

**One case declaration, two commands.** A `[batch]` block, `replies/<feature>/*.json`, and
`expect.features`. The runner writes the declaration and runs `batch new` and `batch go`; everything
else — the world, the fake provider, the judges, the `gh` that is a script — is untouched, which is
the claim S8 makes about a batch being several ordinary runs.

**The `gh` that is a script needed one flag per branch.** With one `gh-opened` for the whole world,
the second feature's `pr view` found the *first* one's pull request and delivered without ever
opening its own — and the case said three features had landed. Parallelism is what surfaced it; a
fixture that cannot tell two branches apart cannot judge two features.

**`REPO` reaches a session's own script.** With a tree per run the cwd is the worktree, so a reply
script that wanted to reach the project — to skip a feature from inside the night — was reaching
its own tree instead. Two of the twelve cases could not have been written without it.

**The declaration is written beside the world, not in the project.** A case about two runs not
dirtying one working copy must not be the thing that dirties it.

## What is open, said out loud

**A feature may wait for one thing.** Named above; the alternative is the kit merging branches
nobody reviewed. If a real evening wants a diamond in its graph, that is the measurement that would
justify building it, and not before.

**Autostart is still unproven, and so is a live Telegram.** Unchanged from S7 and S7a: this machine
runs the kit in a container with no systemd, and every bench case answers through the file channel.

**A tree reclaimed from a driver that died is proved by tests and not by a trap.** Reaching it on
the bench needs a run that outlives its own death, and the bench runs a batch once. The same shape
S7a had to write down about sweeping a question out from under a live driver.

**The merge check believes git.** It reports what git says will not merge; it does not say whether
the owner would have wanted those two features to touch one file at all.

**Nothing measures how much a batch actually parallelises.** Every case here is a handful of
scripted sessions. What three real features across two providers cost, and whether the machine's
ceiling or the graph is what binds a real night, is a measurement that needs S9 and a live evening.
