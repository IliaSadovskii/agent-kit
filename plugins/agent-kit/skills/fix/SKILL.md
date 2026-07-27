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
4. **Review** — run `/code-review` over the diff. At this size `low` or `medium` effort is the right
   trade: it reports only the findings it is most confident in, which is what you want on a change
   this small. Fix what it returns. Then run `/security-review` if the change touches input handling,
   authentication, secrets, or file and process use — otherwise skip it and say so.
5. **PR** — push the branch and open a pull request per `${CLAUDE_PLUGIN_ROOT}/rules/pull-requests.md`.

Relative to `ship` this skips ideation, the design gate, the written plan, the `tester` and
`reviewer` agents, and the deep security pass. Everything else holds.

If the task turns out to need a design, a new domain model, or contract changes, stop and offer to
switch to `ship` rather than forcing it through the light path. The user decides.
