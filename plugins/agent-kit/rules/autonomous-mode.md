# Autonomous mode (flow rule)

Applies during `ship` after the design is approved. The user is away: work through to a reviewed
pull request without them — or, under `--stage`, through to the end of this stage's steps and no
further. The next stage is another session's work, and running into it is not diligence. These rules outrank any "wait for approval" instruction inside a skill.

- **Don't stop to ask.** On ambiguity, pick a reasonable default consistent with the approved
  design, the always-on governance, `.agent-kit/project/instructions.md`, and the project's
  coding standards. Append what you assumed and why to the plan's Run log at the moment you decide;
  the PR's Assumptions are assembled from it. Where the design's *left to the build* list already
  named a default for this decision, that default is the answer — the owner saw it and did not pull
  it back. Departing from one is a deviation, and logged as such.
- **When something contradicts the approved design** — an approach fails, a decision conflicts with
  the codebase — pick the best option in your judgment and continue. Describe the deviation and its
  cause in the Run log, marked as a deviation.
- **Track manual actions.** When something needs the owner's hands and you cannot do it yourself —
  set a real secret, grant an access, create a third-party account, test on a physical device,
  change CI configuration, run a production migration — append it to the Run log with what, where,
  why, and when; the PR's Manual actions section is assembled from it. Do not silently skip it, and
  do not stop for it either. A thing the *owner* must do later is logged; only a thing that stops
  *you* from finishing the PR is a blocker.
- **Recover rather than abandon.** When a command, test, or tool fails, read the error, try safe
  in-scope alternatives, and continue. A recoverable tool difference is not a question.
- **Stop only on an insurmountable blocker**: a missing secret or access that prevents finishing
  the PR itself, a required irreversible destructive action, or no reasonable path at all.
- **Stay resumable.** Keep the plan and its Run log current, commit coherent completed work, and
  leave clear diagnostics if you do hit a terminal blocker, so another session can pick it up
  safely.
