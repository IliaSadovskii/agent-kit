---
name: ship
description: Build one feature end to end — design it against the project's blueprint, build it, verify it against what the entry promises, review it, and open a pull request that can be merged without reading the diff.
argument-hint: "[action key, or what to build]"
disable-model-invocation: true
---

# Ship

One feature: an action from `docs/knowledge/actions.md`, or a small coherent group of actions and
screens, delivered as one pull request.

Some work has no entry and never will — the skeleton that makes an empty project start, a build
step, a dependency bump. Then `entries` is empty, `task` in the run file describes what is being
built, and everything below reads "the entry's lines" as "what that task says done means". Nothing
else changes.

Blueprint already says **what** this feature does and **why**. Your job is **how, in this codebase,
now** — which files, which layer, which existing helper, which seam the tests sit at. Do not
re-decide what blueprint settled, and do not put product decisions into the code that the entry does
not carry.

**One rule governs every question you might want to ask:**

> An expensive fork — the shape of stored data, a contract outside this codebase, a permission
> boundary, money — is asked when someone is present, and becomes a recorded assumption when nobody
> is. Everything else you decide silently, either way.

`gate` in the run file says whether anyone is present. A question whose answers all lead to the same
work is never asked at all.

## Before you start

Run `blueprint --check`. It is mechanical and silent when clean. Then:

| What it found | What you do |
|---|---|
| a slot in scope unsettled, or the entry incomplete | stop, name what is missing, offer `/agent-kit:blueprint` — the owner is here and closes it in a minute |
| no `docs/knowledge/` at all | **carry on.** Work from the task as written, with `entries` empty and `task` describing it, and say once that without an entry the tests can only aim at what the task says done means. A project's first command should not be an hour of interview |
| `[assumed …]` blocks on the entries you will touch | with `gate: owner`, show them and offer to close them now — this is the last moment anyone is here; with `gate: none`, follow them as written |
| the entry is already `built` | say so and ask whether this is a change to it |
| nothing | continue without a word about it |

Then read, in one message: `.agent-kit/project.yml`, the entry and the entities it names,
`docs/knowledge/stack.md`. **Read nothing else yet.** Everything you read is re-read on every
remaining step, so a file costs its size times the steps left.

**Pull the entry's own section, do not open the file it lives in.** A real project's `actions.md`
runs to tens of thousands of characters, and opening it to read one of forty entries carries the
other thirty-nine through the whole run:

```bash
awk -v RS='\n### ' '/`key: developer\.create_offer`/{print "### " $0}' docs/knowledge/actions.md
```

Measured on a real project that is one entry out of thirty-five: 1.6 KB against 44 KB. The same
goes for every entity and screen you need — a section each, not the file.

The working tree must be clean — a dirty tree is a blocker to report, not to work around. Create
`claude/<slug>` from a freshly pulled default branch, unless the run file already names a branch and
a base.

## The run file

`.agent-kit/runs/<slug>/run.json`, shaped like `${CLAUDE_PLUGIN_ROOT}/templates/run.json`. It is
this run's memory and the handoff to anything that resumes it: create it at Design and update it as
each thing happens, never in a batch at the end. A run outlives its own context — what is not in
that file or in the code did not survive.

**`--run <dir>` means the file is already there**: a batch wrote it, or an earlier session of this
feature did. Read it and continue from its `step` rather than starting over — that is also how a run
comes back after the account limit killed its session. Set `step` as you enter each step, and one of
`done` / `blocked` when you stop, because whatever launched this is watching that field to know you
are finished.

Beside it, `run.log` records **when** things happened, which the state file cannot: one line per
event, appended and never read back, so it costs nothing in context.

```bash
printf '%s step=%s event=%s detail=%s\n' "$(date -u +%FT%TZ)" build suite "make test → 1 failed" \
  >> .agent-kit/runs/<slug>/run.log
```

Log a line when a step starts, when a command that matters returns, when you ask something and when
it is answered, when you take an assumption or hit a blocker, and when the review comes back — with
its counts. One event per line and nothing resembling prose: this is what someone reads to find out
where a run spent its afternoon, not a narrative of it.

Both files are working state, not repository content. Add `.agent-kit/runs/` to the project's
`.gitignore` if it is not there yet.

## Design

Skip this step when the run file already carries an approach and tasks: whoever wrote them designed
this feature, and redesigning it discards a decision the owner may already have approved.

**When `parent` names another run, read its run file first** — approach, assumptions, deviations.
You are building on its branch, so its code is already under you; what the code cannot tell you is
why. A field it renamed, a library it chose, a constraint it hit are decisions you inherit, not
decisions you get to take again. Read the immediate parent only: the whole chain would cost every
later feature the history of all the earlier ones.

Otherwise read the code the entry touches — including the callers and the stored data of everything
you will alter, because a feature that quietly moves a neighbour's behavior is the most expensive
thing an unattended run can produce. Then settle the approach. Reach for the library map in
`stack.md` before writing anything yourself, and stay inside the stances it records. Name the seams
the tests will sit at: prefer seams the project already has, take the highest one that can still see
the behavior, and keep the count as low as the feature allows.

Put it up as **one screen**: the goal, the approach, a diagram only if the change alters a flow,
what you are taking as given, and what you will settle during the build with the default you expect
to take.

**Wait for a go only if there is an expensive fork in it.** With one, ask it with a recommendation
and wait. With none, say what you are about to do and start — a gate that always waits teaches the
owner to approve without reading. Under `gate: none` you never wait, and the fork becomes an
assumption.

Before asking anything, write `waiting_since` and the fork into the run file, and clear them when it
is answered.

Design ends when the run file holds the approach, the seams, and a task list in which each task is
the smallest unit that carries its own verification.

## Build

Task by task, one commit each.

**Write the test before the code.** That is the default for every line of the entry, and it is what
makes the proof free: a test written first fails on its own, so nothing has to be run again to
establish that it can.

The one exception is a line whose shape is not decided until the code exists — presentation, mostly.
Asserting on markup you have not chosen yet is not test-first, it is writing the test twice. Write
those after, and **run each one once against the unfixed code**, so the guarantee holds where the
default does not apply.

Record as you go, not at the end. Cheap decisions go to the run file's `assumptions`. A decision
that is expensive to reverse goes there **and** into `docs/knowledge/`, as a block under the entry
it stood in for:

```markdown
> **[assumed 2026-08-02 · claude/<branch>]** <what the knowledge does not say>. Took: <what you did>.
> Expensive to get wrong — <data model | permissions | money | public contract>.
```

That block is the decision of record for every later run, which is what keeps features consistent
with each other. Anything contradicting the approved approach goes to `deviations` instead, with its
cause.

When you find a ready-made answer the library map in `stack.md` does not name — a package that
covers what you were about to write — leave a `[found …]` block under that file the same way. It is
the only route by which the map learns anything, since nothing else goes looking on its own.

Code, identifiers and commit messages in English; anything the owner reads in the project's
language.

## Verify

1. **Cover the entry.** Every one of its lines — what changes, what the initiator sees, what others
   see, what can go wrong — has a test naming it. A line with no test is not done.
2. **Run the project's declared suite once**, from `project.yml` → `commands`: tests, types, lint. A
   type error is a failing test. Fix the product; never weaken an assertion for green output.
3. **Start the app and exercise what changed**, when the feature has a surface a person can reach. A
   green suite on an app that does not start is exactly what this catches. Say so when there is no
   such surface.

Fix what fails, then run the suite once more at the end. Record in the run file what ran and what it
returned: the pull request is written from that, not from memory.

Do not run the product's end-to-end scenarios here. They prove the product rather than this feature,
and belong to whatever integrates a batch.

## Deliver

In this order, because it puts reviewed code in the pull request from its first minute:

1. Commit and push the branch.
2. **Review** — see below.
3. **One round of fixes**, then rerun what the fixes put at risk, plus the suite.
4. Open the pull request per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`. Never merge it.
5. **CI** — `gh pr checks`, or the closest this session has. Fix what is yours: formatting, lint, a
   flake, the workflow's own configuration. A failure that needs the feature's design changed is a
   blocker to report in the pull request. Bound the wait — a pipeline still pending after a
   reasonable window is reported as pending, rather than polled until something kills the session.
6. Set the entry's machine line to `state: building (pr: <n>)`. Besides an assumption block, that is
   the only thing you write into knowledge; `blueprint --check` moves it to `built` once the pull
   request merges.
7. Close the run file: `step: "done"`, `suite`, `pr`, and any blocker.

**`deliver: "branch"` stops you after step 3.** A feature inside a batch pushes reviewed code and
nothing else: the batch opens one pull request over the whole chain, runs CI there, and sets the
entries' machine lines from it. Push, close the run file with `step: "done"` and the branch name,
and stop — do not open a pull request, do not wait for a pipeline that has none, and do not report
as if you had. Everything before Deliver is unchanged, review included.

The run is finished when the pull request exists with CI green or its state reported — or, delivering
a branch, when that branch is pushed with its review done — or when a blocker has been reported and
the branch left in a recoverable state. Close it per
`${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is thin rather than what was done, then the one line
naming what to run next.

## Review

**Always: the `agent-kit:reviewer` agent.** Give it the base branch to diff against, the run file's
path, and the entries. It answers what nothing else can — whether this is the feature that was
approved — because it is the only pass that reads the entry.

**On a trigger: `/security-review`.** Run it when the diff touches authentication or permissions,
parsing of untrusted input, money, files or processes, a data migration, or an outbound call.
Otherwise skip it, and say in the pull request that you did and why.

Never run the `code-review` plugin's fan here: measured on one feature it cost 6.7M tokens for two
findings against the reviewer's 0.66M for twelve. Its place is once over a whole batch, which is not
this command's business. Claude Code's own `/code-review` is stronger than either and can only be
started by a person typing it, so it is not part of this pipeline.

Then **one round of fixes**: everything critical or major, everything that departs from the entry,
and every security finding. Record the rest as deliberately deferred rather than building
scaffolding around it. Send the fix diff back through `agent-kit:reviewer` only when the fixes
changed structure rather than lines.

## What this command does not do

It does not choose the next feature, integrate anything, merge anything, run the product's
scenarios, or decide what becomes of the pull request once it is open — those belong to whatever
launched it. And it never rewrites knowledge prose: blueprint owns that.
