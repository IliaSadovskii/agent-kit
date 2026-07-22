# Ship workflow

One command owns an entire feature: choose → ideate → design → plan → review plan → build → test →
review code → review security → open PR → reflect docs. Follow `.agent-kit/engine.md`, the active
provider adapter, and `.agent-kit/rules/`.

## Arguments

- `--rebootstrap` reruns the project interview.
- `--no-ideate` skips feature ideation.
- `--manual` keeps the user in the loop after design approval — interactive mode (checkpoints + a
  consultative posture) instead of the autonomous contract. See `.agent-kit/rules/interactive-mode.md`.
- Remaining free text is the chosen task and skips roadmap task selection.

## Interaction contract

Interaction is front-loaded during Gate/Task, optional Ideate, and Design; design approval is the
final gate. Immediately after approval:

- **Default (autonomous):** read `.agent-kit/rules/autonomous-mode.md` and finish every remaining
  step without routine questions.
- **With `--manual`:** read `.agent-kit/rules/interactive-mode.md` instead — stay in the loop through
  the four checkpoints and a consultative posture.

Either way, record autonomous/assumed decisions in the PR's Assumptions and owner-only work in
Manual actions.

## Pipeline — single source of truth

- **Gate** — read `.agent-kit/project/manifest.yml`.
  - Missing manifest, `bootstrapped: false`, or `--rebootstrap`: run canonical skill
    `idea-interview`. It surveys the owner, records or generates core docs, provisions shared
    project scaffolding, updates the manifest, and opens a separate bootstrap PR. Stop after that PR
    and ask the owner to merge it before starting a feature.
  - `bootstrapped: true`: load source paths from the manifest. If a path is stale, locate the
    intended document and repair the manifest without duplicating user docs.
- **Task** — use the free-text task when supplied. Otherwise read the idea and roadmap sources,
  inspect current code/recent history, propose 2–3 next coherent chunks, and let the user choose.
- **Ideate** — unless `--no-ideate`, run `feature-ideation`: challenge the chosen feature at the
  product/business layer, agree scope IN/OUT, and optionally append liked deferred ideas to the
  roadmap with the user's permission. The user may decline and build the roadmap version unchanged.
- **Design** — run `brainstorming`: clarify technical behavior, compare 2–3 approaches, present a
  design, and obtain explicit approval. Do not write implementation code before approval. After
  approval, write and self-review the feature spec, then enter autonomous mode.
- **Plan** — run `writing-plans`: create a detailed executable plan and self-review it. There is no
  plan approval gate.
- **Plan review** — delegate an independent, read-only adversarial review to `plan-reviewer`.
  Resolve all critical/major findings before implementation. If a necessary spec correction changes
  approved behavior, continue and record the deviation in Assumptions.
- **Build** — implement the approved design task-by-task using the project conventions. Keep commits
  coherent and verification close to the changed behavior.
- **Test** — delegate to `tester` for uncovered paths and edge cases, then run the project's full
  declared test/lint suite. Fix product defects; never weaken a valid test to obtain green output.
- **Review** — delegate an independent, read-only diff review to `reviewer`. Fix critical/major
  correctness and maintainability findings and rerun affected verification.
- **Security** — run a distinct independent security pass using the strongest capability available
  on the active provider. Check injection, authentication/authorization, secrets/data exposure,
  unsafe deserialization/files/processes, dependency and configuration risks. Fix every
  critical/high issue; document consciously deferred lower-severity findings.
- **PR** — ensure commits are on a non-main branch, push it, and open a pull request with available
  GitHub tooling. Follow `.github/pull_request_template.md` and
  `.agent-kit/rules/pull-requests.md`. Never merge. If no PR mechanism is available after every
  safe fallback, report that only as the terminal blocker after the branch is ready/pushed.
- **Docs** — run `docs-reflection` in the main agent context. No-op by default. If living docs
  genuinely diverged, open a separate docs-only PR from the default branch; otherwise mark docs as
  reviewed/current in the feature PR.

The pipeline is complete only when the feature PR exists and docs reflection is resolved, or an
insurmountable terminal blocker has been reported with the branch left in a recoverable state.
