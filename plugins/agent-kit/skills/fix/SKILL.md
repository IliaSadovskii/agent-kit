---
name: fix
description: Something is wrong and it is small — a symptom the owner describes, a failure you can already see, or a review round on an open pull request. Find the cause, prove it with a failing test, change the least that makes it pass, deliver.
argument-hint: "[what is wrong] [--pr <n>]"
disable-model-invocation: true
---

# Fix

The product does something it should not, and putting it right is smaller than a feature. This is
the command for that, and it is deliberately the cheapest one in the kit: if it costs what `ship`
costs, nobody runs it and the fix happens by hand, unrecorded.

| Invocation | Where the input comes from |
|---|---|
| `/agent-kit:fix <what is wrong>` | the owner's words. The cause is unknown and finding it is the first half of the work |
| `/agent-kit:fix` | whatever is already red: a failing test, a failing pipeline. The symptom is in the output, so start from it |
| `/agent-kit:fix --pr <n>` | a review round on an open pull request. Same pipeline, different source — and the branch is that pull request's, so nothing new is opened |

## When this is not a fix

**A fix does not add behaviour the product never had.** That is the line, and it is not about how
many lines change. The moment the cause turns out to be *this was never built*, stop and say so:
`ship` builds it against an entry, and `blueprint` writes the entry when there is none. A run that
quietly grows a feature under the name of a fix delivers something nobody described, reviewed
against nothing, and covered by whatever tests it felt like.

Two more that end the run early rather than late:

- **The cause is a decision, not a defect.** The code does what somebody chose; you disagree, or the
  owner does. That is a product decision, and it belongs to the entry — record it and stop.
- **The fix is a rewrite.** Cause understood, repair touches a layer rather than a place. Say what
  you found, put it in `docs/technical_debt.md` with the cause named, and let the owner decide
  whether that is a feature.

## Before you start

The knowledge check, same as every command — mechanical, seconds:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" .
```

You need less of it than `ship` does. Read the entry that covers the broken behaviour, if there is
one, as its own section rather than by opening the file; read nothing else until the cause is found.
Without knowledge at all, carry on: the symptom is the specification.

The tree must be clean. `--pr <n>` starts by checking out that pull request's branch; otherwise
branch `claude/fix-<slug>` off a freshly pulled default branch.

Keep a run file — `.agent-kit/runs/<slug>/run.json`, the shape in
`${CLAUDE_PLUGIN_ROOT}/templates/run.json` — but keep it short: `task` in the owner's words, the
cause once you have it, `suite`, `review`, and whatever the fix left behind. Its fields are a closed
list; prose that fits none of them goes in `notes`. A fix that dies mid-session and left no file
starts again from nothing.

## Find the cause

**The symptom is not the cause, and the first plausible story is not the cause either.** Read the
code along the path the symptom names, and keep going until you can say *this line, this condition,
this missing branch*. Then say why nobody noticed: which test should have caught it and does not
exist, or exists and asserts the wrong thing. That answer is what stops the same defect returning
next month by a different route.

Where the cause is a contradiction between an entry and the code, that is the expensive fork every
build command shares — mark, ask or record it exactly as `ship` does. Do not resolve it here.

When the cause will not come out — an hour in, a flaky failure with no reproduction — stop and
report: what you ruled out, what you suspect, where you would look next. A named dead end is worth
more than a change made in hope, which is indistinguishable from a change that worked.

## Prove it, then change it

**Write the failing test first.** It is the whole point of running this as a command rather than
editing the file: without it, "fixed" is a claim, and a month later nobody can tell whether the
defect was real. The test asserts the behaviour that should have held, at the seam the project
already tests at — not a reproduction of your debugging session.

Run it. It must fail, and it must fail for the reason you found: a test that fails for a different
reason will go green on a change that fixes nothing.

The one exception is a failure a test cannot hold — a flake in the pipeline, something in the
environment, a race you cannot make deterministic. Then say so in the run file, name what you did
instead, and expect the reviewer to ask.

**Then change the least that makes it pass.** Not the tidy-up you noticed next to it, not the
rename, not the neighbouring defect — those go to `docs/technical_debt.md`, one line each, with the
cause you already understand. A fix that also refactors cannot be reviewed as a fix, and cannot be
reverted without taking the refactor with it.

## Verify

1. The new test passes, and the rest of the suite still does. `project.yml` → `commands`: tests,
   types, lint, once, at the end.
2. **Undo the fix and watch the test fail again.** Ten seconds, and it is the only thing that proves
   the test is guarding the fix rather than passing beside it.
3. Start the app and exercise the path, when the defect has a surface a person can reach. What you
   opened and what you saw goes in `suite` — "not exercised" is an answer, silence is not.

## Deliver

Review with `agent-kit:reviewer` when the change touched the product; a fix inside the tests does
not need a reviewer to tell it what it did. The verdict and the findings go into `review` as they
come back — a critical or major one left open is not `step: done`.

Then the pull request, per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`, with the cause in the
first lines: what broke, why, since when if you can tell, and which test now stands where nothing
stood. **What was hard** is usually the most useful part of a fix's description — the story that
looked right and was not is exactly what the next person needs.

`--pr <n>` ends differently: commit onto that pull request's branch, push, and say what changed in
its terms. No new pull request, no second branch — the round belongs to the one that is open.

Close the run file: `step: done`, `suite`, `pr`, anything deferred — then have the check read it
back, which is silent unless a finished run is saying something it may not:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --run .agent-kit/runs/<slug>
```

Then end per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md` — what is thin, where it now lives, and the
one command that comes next.

## What this command does not do

It does not refactor, tidy neighbouring code, or fix the second defect it found on the way — those
are lines in the ledger. It does not rewrite an entry: `blueprint` owns the prose. It does not
merge. And it does not take work with no observable symptom: "this looks wrong" without a failing
behaviour is a review comment, not a fix.
