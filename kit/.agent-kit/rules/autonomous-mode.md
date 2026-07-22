# Autonomous mode (flow rule)

Applies during `ship` **after the design is approved**: work FULLY autonomously up to opening
the PR — the user may be unavailable (asleep, away). Referenced by the `ship` steps and by the
`brainstorming` and `writing-plans` skills. These rules OUTRANK any "wait for user approval"
instruction inside a skill.

- **Do NOT stop with clarifying questions.** On any ambiguity pick a reasonable default,
  consistent with `.agent-kit/engine.md`, `.agent-kit/project/instructions.md`, the approved design, and the
  project's coding standards.
- **Record every such decision** in the PR's `## Assumptions` section (what you assumed and why).
- **If, mid-work, something contradicts the approved design/brainstorm** or makes it unworkable
  (approach failed, decision conflicts with the codebase/tests) — do NOT wait for the user. Pick
  the best option in your judgment, continue, and describe the deviation and its cause in the PR's
  `## Assumptions` (mark it "deviation from design").
- **Track manual actions.** Throughout the feature, whenever something needs the owner's hands
  and you cannot do it yourself (set a real secret / env var, grant an access, create a
  third-party account, build/test on a real device, change CI/GitLab config, run a prod
  migration), do NOT silently skip it and — if it doesn't block your own progress — do NOT stop
  either. Record it in the PR's `## Ручные действия` section (what/where/why/when) and keep going.
  The difference from a blocker: a thing the *owner* must do later is logged; only a thing that
  stops *you* from finishing the PR is a real blocker.
- **Stop and ask ONLY on an insurmountable blocker** with no way forward: a missing secret/access
  that blocks you from finishing the PR itself (not merely something the owner must do afterwards
  — that goes to `## Ручные действия`); a required irreversible destructive action; no reasonable
  path at all.
- **Recover, don't abandon.** When a command/test/tool fails, inspect the error, try safe in-scope
  alternatives, and continue. Do not turn a recoverable provider/tool difference into a question.
- **Preserve resumability.** Keep the plan current, commit coherent completed work, and leave clear
  diagnostics if a real terminal blocker occurs, so another cloud session can resume safely.
- **See it through:** after design approval, run every remaining `ship` step autonomously —
  through to the PR and the docs-reflection step (a second docs PR if needed — also autonomous,
  no gate). The step sequence is defined in `../workflows/ship.md`.
- **Interactivity is front-loaded.** The user is present only for the early steps — the task
  choice, the optional product brainstorm, and the design approval. **Design approval is the
  final gate;** after it there is NO spec approval and NO plan approval, and everything onward
  runs autonomously.
