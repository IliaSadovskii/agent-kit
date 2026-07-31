# Interactive mode (flow rule)

Applies during `ship --manual` after the design is approved, in place of
`${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md`. The user wants to co-develop: stay in dialogue
through the build instead of running silently to the PR. `--manual` changes nothing before approval.

- **Checkpoints — pause and confirm at three points:** after `writing-plans`, present the plan and
  wait for a go-ahead; after build and test, show what changed and the test results before opening
  the pull request; after the review wave, confirm what you are fixing from it.
- **Consultative throughout, not only at checkpoints.** On real ambiguity, prefer a concise
  question over silently defaulting. On a fork with genuine trade-offs, present the alternatives
  with your recommendation. Say what you intend to do before anything nontrivial or hard to
  reverse.
- **Keep the written record.** Append to the plan's Run log as in autonomous mode, and assemble the
  PR's Assumptions and Manual actions from it; checkpoints add dialogue, they do not replace the
  record.
- **The user may hand back.** At any checkpoint they can say "just finish it" — from there, follow
  `${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md` to the PR.
