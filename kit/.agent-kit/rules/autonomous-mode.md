# Autonomous mode (flow rule)

Applies during `ship` after the design is approved. The user may be asleep or away: work through to
the PR without them. These rules outrank any "wait for approval" instruction inside a skill.

- **Don't stop to ask.** On ambiguity, pick a reasonable default consistent with the approved
  design, `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, and the project's coding
  standards. Record what you assumed and why in the PR's Assumptions.
- **When something contradicts the approved design** — an approach fails, a decision conflicts with
  the codebase — pick the best option in your judgment and continue. Describe the deviation and its
  cause in Assumptions, marked as a deviation.
- **Track manual actions.** When something needs the owner's hands and you cannot do it yourself —
  set a real secret, grant an access, create a third-party account, test on a physical device,
  change CI configuration, run a production migration — record it in the PR's Manual actions with
  what, where, why, and when. Do not silently skip it, and do not stop for it either. A thing the
  *owner* must do later is logged; only a thing that stops *you* from finishing the PR is a blocker.
- **Recover rather than abandon.** When a command, test, or tool fails, read the error, try safe
  in-scope alternatives, and continue. A recoverable tool difference is not a question.
- **Stop only on an insurmountable blocker**: a missing secret or access that prevents finishing
  the PR itself, a required irreversible destructive action, or no reasonable path at all.
- **Stay resumable.** Keep the plan current, commit coherent completed work, and leave clear
  diagnostics if you do hit a terminal blocker, so another session can pick it up safely.
