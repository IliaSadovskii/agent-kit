---
name: fix
description: The light path for a genuinely small, local, low-risk change — a bug fix, a copy tweak, a small refactor, a dependency bump. Understand, change, test, review, PR.
argument-hint: "[task]"
disable-model-invocation: true
---

# Fix

The light path for a genuinely small, local, low-risk change. Choosing `fix` over `ship` is the
user's call; there is no automatic heuristic.

There is no design gate and no mode switch here: the user who typed the task is presumed nearby.
Ask when a real ambiguity would change what you build; don't pause for routine choices.

Task: `$ARGUMENTS`

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
