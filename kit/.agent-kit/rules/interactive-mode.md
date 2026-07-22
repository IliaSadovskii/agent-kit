# Interactive mode (flow rule)

Applies during `ship --manual` **after the design is approved**, in place of
`.agent-kit/rules/autonomous-mode.md`. The user wants to co-develop: stay in dialogue through the
build instead of running silently to the PR. Referenced by the `ship` steps when `--manual` is set.

Where autonomous mode front-loads all interaction at the design gate, interactive mode keeps the
user in the loop:

- **Checkpoints — pause and confirm at these four points:**
  1. After `writing-plans` — present the plan and wait for the user's go-ahead (autonomous mode has
     no plan gate; here there is one).
  2. After `plan-review` — surface the critical/major findings and how you intend to resolve them.
  3. After `build` + `test` — show what changed and the test results before the independent review.
  4. Before opening the PR — a final confirmation.
- **Consultative posture throughout — not only at the checkpoints.** On any real ambiguity, prefer a
  concise question over silently picking a default. On a fork with genuine trade-offs, present the
  alternatives with your recommendation rather than deciding alone. Voice your intent before
  nontrivial or hard-to-reverse steps.
- **Still record, don't lose context.** Keep filling the PR's `## Assumptions` and `## Ручные
  действия` as in autonomous mode; checkpoints add dialogue, they do not replace the written record.
- **The design gate is unchanged.** `--manual` changes only what happens *after* approval; the
  earlier steps (task, optional ideate, design) are identical.
- **The user may hand back to autonomous.** At any checkpoint the user can say "just finish it" —
  from there, follow `.agent-kit/rules/autonomous-mode.md` to the PR.