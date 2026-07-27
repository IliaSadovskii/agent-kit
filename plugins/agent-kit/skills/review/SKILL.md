---
name: review
description: Independent adversarial review of work in progress — the working-tree changes or the branch diff — outside the full feature pipeline. Read-only; it changes nothing itself.
argument-hint: "[target]"
disable-model-invocation: true
---

# Review

An adversarial, read-only review of work in progress: the current working-tree changes, or the
branch diff against the default branch. Target: `$ARGUMENTS` when given, otherwise the current
branch plus uncommitted work.

Run `/code-review` for correctness. It reviews the diff in its own context with a panel of agents,
scores every finding for confidence, and reports only what survives. Choose the effort level from
what is at stake, not from the size of the diff: `medium` by default, `high` or `xhigh` when the
change touches security, concurrency, data migration, or money. Pass the target through if the user
named one.

If the project has an approved spec or plan for this work, add a second pass that `/code-review`
cannot do: delegate to the `agent-kit:reviewer` agent to check the diff against what was agreed, and
report where the implementation drifted.

Report the findings by severity, each with `file:line` and a one-line reason. This skill changes
nothing — the user decides what to act on. Offer `/code-review --fix` if they want the correctness
findings applied.
