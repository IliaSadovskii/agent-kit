---
name: address
description: Close a review round on an open pull request — read the owner's comments and the CI status, fix what is in scope, rerun the verification the fixes put at risk, push, and answer every thread. Invoked by fix --pr <n> after ship or fix opened a PR and feedback came back; it owns that run end to end.
---

# Address

Close one round of pull-request feedback. `ship` ends at an open PR; this is the loop that runs
when the owner's review and the CI results come back.

PR: `$ARGUMENTS`, or the number or URL `fix --pr` handed you — otherwise the PR of the current
branch (`gh pr view`).

1. **Collect** — the PR's review threads and comments and its CI status (`gh pr view`,
   `gh pr checks`, `gh api` for inline threads). Read the diff alongside the spec and plan under
   `docs/specs/` and `docs/plans/` so each comment lands in context. Nothing is ignored: every
   thread ends this run with either a change or an answer.
2. **Sort** — three piles, stated out loud before anything changes:
   - **In scope** — defects, requested changes within the approved design, red CI. Fix these.
   - **Design changes** — the owner asking for something the approved design does not cover. Their
     comment *is* the new approval: restate in one sentence what you understood it to change, in
     your reply, then build it. Two comments that contradict each other are a genuine fork — ask.
   - **Out of scope** — ideas beyond this feature. Don't build them; answer in the thread and
     offer to put them on the roadmap.
3. **Fix** — work the in-scope pile on the PR branch, under the project's conventions and the
   always-on rules. Keep commits coherent, and say in each commit which thread it resolves.
4. **Verify** — rerun what the fixes put at risk, then the project's full declared suite. If CI
   was red, reproduce the failure locally first; that reproduction passing is the proof the fix
   is real, a green rerun in CI alone is not.
5. **Push and reply** — push, confirm CI comes back green (`gh pr checks --watch`, or the closest
   the session has), then answer every thread: what changed and where, or why nothing did. Update
   the PR description where the fixes moved it — Assumptions, Manual actions, Testing.

After the sorting is stated, the run is autonomous in the sense of
`${CLAUDE_PLUGIN_ROOT}/rules/autonomous-mode.md`: the user may have walked away, new assumptions go
to the plan's Run log and the PR, and only an insurmountable blocker or contradicting comments
stop the run.
