# S8e — what proves a feature, and what a project checks itself for

Written after building it, 28 August 2026. The plan calls this the largest of the recovered
steps and the one the third version **regressed** rather than merely omitted: the catalogue of
kinds of verification shipped in the second version on 20 August at 01:23, and this plan was
written on the 22nd at 01:46 — measured over runs made before it, which is why the plan's own
inventory files `verified` under *checked at the end only*, true until two days before the plan
and false after.

## 1 · The cut, and the argument for it

The plan asks for twelve kinds plus `screen`, both levels, answers proposed from the repository,
staleness on evidence, and the review's check against the diff. That is several nights. The cut
taken:

**Built: three kinds, the project's answers, the feature's level entire, nine traps.**
**Not built: the other nine kinds, proposing answers from the repository, staleness on evidence,
`runs: epic`, a refusal at the batch's gate.**

The argument is the *done when*, which asks that a project be asked about **every kind the kit
knows** — and the kit will know three. Three carry every mechanism: one that can never be excused
(`suite`), two that can, with different shapes of excuse. The other nine are three lines of data
each and no new place to break. Better the feature's level complete with three kinds than twelve
kinds and a feature level held together by prose.

## 2 · Where the answers live, and what it cost to put them there

A new table beside the old one, and not a replacement:

```toml
[commands]
test = "make test"

[verification.suite]
command = "make test"

[verification.types]
why = "в этом стеке типов нет: код нетипизирован по решению"
since = "2026-08-28"
```

`[commands]` answers *what to run over this project and in what order*; `[verification]` answers
*what class of defect this project catches, and with what*. Replacing the first would have meant
rewriting the declared order, S8b's gate, `no-commands`, `no-such-command` and 121 bench worlds
for a rename. A pointer (`command = "test"`) was refused too: a dangling reference is a new
refusal code and a new place to break, bought for one saved line.

**A project that has answered nothing owes nothing.** No table, no owed kinds, and `design`'s
contract is exactly what it was. That is what keeps 121 standing cases green, 107 planted replies
untouched, and the sandbox frozen at `0e54eef` working as it worked. **The bench's baseline world
was not extended** — the temptation was to put three answers there, and it would have made every
one of the 121 cases owe `proves`. Each new case plants its own table through `plant.sh`, which
also buys every one of them an honest disarm: take the plant away and nothing is owed.

## 3 · The two levels

**The project's.** `verification/kinds.py` is the one home: `suite` (code that worked and stopped;
never excusable), `types` (a value used as something it is not, without running the code), and
`end-to-end` (the parts pass separately and the product does not work whole). Nothing outside that
file enumerates kinds — not a role's prose, not a template, not `project.toml`, which only ever
holds what a project answered. `runs: feature|epic` was **not** built: nothing runs an epic level,
so the column would have one value and no reader.

**The feature's, which is what was missing from the code.** `design.proves` returns one record per
kind the project owes — the command this change will be proved by, or the `why` it does not apply.
It is required, and non-empty, exactly where the project answered a kind with a command: the same
mechanism `knowledge_requires` already uses, so the contract is stricter for the project that said
more, never for the one that said nothing.

`verify` walks that list rather than deciding again, and writes `verify.kinds`. `passed` now means
*both the project's commands and the kinds' commands were green*.

`review.proofs` says, per kind, whether the excuse stands or the diff contradicts it.

## 4 · Two things the reviews caught that reading would not have

**A command a session invented was being run unchecked.** `verify` took the strings straight out
of `design.proves` and ran them with `shell=True`. No filter stood between them: the owed-kinds
check returned early on every project that had answered nothing — which is every project today —
and `proves` was rendered into the design's input regardless. So `design.proves = [{kind: "suite",
command: "true"}]` gave `passed: true` and a green night. That is exactly the hole
`command-that-proves-nothing` exists for, entered from the side that decides whether the *feature*
is proved. The plan names it in as many words: *`yes` is a claim no program can test — and it is
also a real binary on every Unix, which is how the second version's own gate was once opened by
it.* The kit's rule — *the program runs what can be checked* — was being broken by the program
running an unverified string.

**The white list was skipped when the design excused nothing.** The recount returned before its
loop when nothing was owed, while `deliverable` read `contradicted` unconditionally. A review could
return a `contradicted` row naming a path nobody measured, on a run where nothing was owed, and
stop the night on an invented finding.

Both were found by reading the finished diff, and neither by writing it.

## 5 · Review is two events, not one

The first form made *the diff contradicts this excuse* a `ContractRefusal`. That would have meant
the kit re-asking the reviewer until it withdrew the finding, and ending in `fail_step` — *the
step could not answer* — instead of a blocker in the owner's report. Two rules at once: a refused
attempt and a failed step are different events, and a step that recorded the truth did its work.

So they are split:

- a `contradicted` row naming a **measured** path is a finding. It stops the run with its own code
  — `why-the-diff-contradicts: <kind>` — raised where `blocked-by-review` is raised, so `record`
  asks first and the owner's knowledge is never touched;
- a `contradicted` row naming an **unmeasured** path is a bad output: a contract refusal, enclosed
  in the next attempt, mended by the session.

**The measured diff is not measured twice.** `verify.proved_over` already holds every change the
tree carries over the commit, path and fingerprint, and it is already enclosed in the review as the
previous step's output — the same shape as S8c's audit: the program measures, the session sorts,
the program recounts against a white list. And the list is *wider* than the feature's diff, because
a working copy legitimately holds things the feature never touched; the prose of `proofs` says so,
rather than letting a path from it read as proof the feature wrote it.

A run with no `verify` in it is named rather than guessed: `nothing-was-measured`.

## 6 · The numbers, measured by hand

| | before | after |
|---|---|---|
| `make test` | 1116 | **1177** |
| `make bench` | 112 of 112 | **121 of 121** |
| `make armed` | 107 + 5 in words | **116 + 5 in words** |

Nine traps added, none carrying `no_disarm`. Twelve refusal codes, four of them the *done when*'s:
`bad-verification-answer`, `command-that-proves-nothing`, `kind-unproved`,
`why-the-diff-contradicts`. `design.verification` — the field the plan ends this step by deleting,
whose only reader was a printer — is gone, and none of the 107 planted replies broke, because a
contract drops what it did not ask for.

## 7 · The flake, caught with a name at last

The owner named an open tail at the start of this night: one bench run under load answered *the
bench could not answer* and named no case. It happened again in my verification of this step, and
this time it is pinned.

`tests/test_disarm.py::test_every_shipped_case_is_armed_or_says_why_it_cannot_be` failed with
`a-tree-in-the-way-of-one-feature` — **the disarmed run did not come back within 300 seconds**, so
the bench answered *could not be checked*. The same test passes alone, and `make armed` had passed
standalone fifteen minutes earlier: 116 + 5.

Two things are worth keeping. **The mechanism behaved correctly** — *could not be checked* never
read as *armed*, which is exactly what `bench disarm` was built to guarantee. And **the cause is a
timeout, not a defect in a trap**: a disarmed batch case, run inside the suite while the suite is
also running everything else, on a machine shared with other projects. The builder saw a
neighbouring shape in the same round — `three-features-at-once` returning *its driver exited 70 and
left the run running*, once in nine bench runs, green on the other eight.

Both are parallel-batch cases, both appear only under load, and a driver exiting 70 is by
definition *a defect in the kit* rather than a load artefact. That is not this step's mechanism and
was not chased here, but it is now recorded with a case name, a limit and a reproduction, which is
what the owner asked for.

## 8 · Breaking it by hand

The round was interrupted — the builder was stopped mid-round with a deliberate break uncommitted
in the tree (`proves_nothing` disabled), which I reverted before anything else. That is the rule
working: a deliberate break must never survive the round, and the tree is checked rather than
trusted.

| broken | reddened |
|---|---|
| the refusal for an excuse with no date | `an-answer-that-is-neither` |
| the list of words that prove nothing | `a-command-that-proves-nothing` |
| the branch for a kind that cannot be excused | `a-kind-that-cannot-be-excused` |
| the branch for a command and an excuse at once | `a-kind-answered-twice` |
| the walk's call in `verify` | `a-run-that-skips-the-design` |
| the refusal on a contradiction | `a-why-the-diff-contradicts` |
| the check that a path was measured | `a-contradiction-nobody-measured` |
| the contract the project makes stricter | `a-design-with-no-verification` |
| the command a feature names, held to what a command is | `a-command-the-feature-invented` |
| the branch for silence about a kind | **two**: `a-kind-this-feature-says-nothing-about` and `a-run-that-skips-the-design` |
| asking about an unanswered kind before paying for the suite | `a-run-that-skips-the-design` |

**Two reddening is right here, and the reason is worth the sentence.** One judgement has two
callers — `design`, so a build session is never paid for, and `verify`, because a run assembled
from other steps may carry no design at all — and the *done when* requires that `verify` be the one
that refuses. There is a trap per caller; breaking the shared branch reddens both, breaking either
caller reddens its own. That is the idiom `programs/deliverable.py` already uses.

And one break in the round was made wrongly and is recorded rather than hidden: breaking `_judge`
as a whole reddened three cases, which measures nothing. Broken branch by branch, each reddens
exactly one.

## 9 · What is held by words, not by a trap

Written at the code rather than only here, and each one broken by hand to prove it holds nothing:

- `no-such-command` on a command a **session** named — the existing trap is about a *declared*
  command;
- the white list in `proving` — a row for a kind the project does not owe never becomes a command;
- the recount running its loop on a feature that excused nothing;
- `kind-cannot-be-excused` and `kind-excused-and-commanded` reached through `verify` rather than
  through `design`;
- `kind-named-twice` and `excuse-unjudged`;
- `nothing-was-measured` — the bench has no world that reaches a run with no `verify` in it.

**`since` has only a printer for a reader, and that is a decision rather than an oversight.**
`answer-out-of-date` was designed and dropped: without a rung on the door it would have been
arithmetic against today's date, which the door does not do. `since` stays required at parse time —
an excuse with no date is refused — and nothing ages. The docstring says so, because this same step
deleted a field for having only a printer.

**Nothing was driven by a live model.** Everything answers from `providers/fake/`.

## 10 · Where the plan was wrong

1. **"`verify` refuses a result with no command behind it" describes an event this kit does not
   have.** That sentence assumes a `verify` that is *told* results; ours *runs* them, so there is
   nothing to invent. The nearest real shape is a row carrying a command and an excuse at once
   (`kind-excused-and-commanded`), and the plan's actual hole — `yes` — is
   `command-that-proves-nothing`, which is what the fourth *done when* refusal is counted as here.
2. **"The review step checks the claims against the diff" does not say where the diff comes from.**
   It already exists: `verify.proved_over`. A second measurement would be a second home for one
   truth.
3. **"Each kind says which session runs it"** — a field with no reader until something runs an epic
   level.
4. **"A kind added here starts being asked of every project on its next check" is true of a report,
   not of a refusal.** A refusal would redden every project in the world on the day a kind ships,
   including the frozen sandbox, and the first thing anybody would do is route around it. So the
   door reports, in its **view** and not on its ladder, and `batch/gate.py` was not touched by a
   single line. That is a deliberate narrowing of the plan, and the gate's own *done when* belongs
   to S8b, which paid it with `no-commands`.
