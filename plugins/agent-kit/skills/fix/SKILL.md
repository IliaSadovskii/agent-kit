---
name: fix
description: Something is wrong — your words, a PR review, or an observed failure. The light path from a small change to a PR, with the review round and root-cause debugging reached through the same command. Understand, change, test, review, PR.
argument-hint: "[task] [--pr <n>]"
disable-model-invocation: true
---

# Fix

Something is wrong: your words, a PR review, or an observed failure. This is the light path — no
design gate, no written plan. Choosing `fix` over `ship` is the user's call; there is no automatic
heuristic.

There is no mode switch here either: the user who typed the task is presumed nearby. Ask when a real
ambiguity would change what you build; don't pause for routine choices.

Task: `$ARGUMENTS`

**A pull request came back.** `--pr <n>`, or a PR URL in the task, is a review round rather than a
new change: run the `address` skill, which owns that run end to end — collect the threads and CI,
sort them into in-scope, design changes, and out of scope, fix, verify, push, and answer every
thread. The steps below do not apply; `address` has its own.

**The cause is not known yet.** A task that names only a symptom — what someone saw, not what to
change — runs the `debug` skill first: reproduce, isolate, and root-cause it before touching
anything. Judge that from the task text; there is no flag for it. `debug` either stops with a
diagnosis the owner has to decide on, or fixes the root cause with a regression test and continues
through the tail below from **Test**. A task that already names the change is this path's own, and
starts at step 1.

1. **Understand** — read the request and the surrounding code until the change is clear, and confirm
   the scope really is small and local.
2. **Change** — make it on a branch, following the project's conventions. Keep the blast radius
   small.
3. **Test** — cover the changed behavior, and make each new test fail once against the unfixed code
   before you trust it. Run the relevant tests, the type checker, and lint. This is the whole
   verification budget on this path, so spend it on proving the change rather than on breadth.
4. **Review** — delegate to the `agent-kit:reviewer` agent, briefed narrowly: this change, this
   request, no spec to check against. One fresh pair of eyes on a small diff is cheap, and it is the
   only review this path gets — `/code-review` is stronger but can only be started by a person
   typing it, never by an agent, so it belongs in the PR description as the owner's one-command
   second opinion. Then run `/security-review`, which an agent *can* invoke, if the change touches
   input handling, authentication, secrets, or file and process use — otherwise skip it and say so.
5. **PR** — push the branch and open a pull request per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`.

Relative to `ship` this skips ideation, the design gate, the written plan, the `tester` agent, and
the deep security pass. Everything else holds.

If the task turns out to need a design, a new domain model, or contract changes, stop and offer to
switch to `ship` rather than forcing it through the light path. The user decides.
