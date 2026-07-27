# Ship workflow

One command owns an entire feature: choose → ideate → design → plan → build → test → review →
review security → open PR → reflect docs.

## Arguments

- `--rebootstrap` reruns the project interview.
- `--no-ideate` skips feature ideation.
- `--manual` keeps the user in the loop after design approval — `.agent-kit/rules/interactive-mode.md`
  instead of the autonomous contract.
- Remaining free text is the chosen task and skips roadmap task selection.

The interaction contract and the design gate are defined in `.agent-kit/engine.md`. Either mode
records autonomous decisions in the PR's Assumptions and owner-only work in Manual actions.

## Pipeline — single source of truth

- **Gate** — read `.agent-kit/project/manifest.yml`.
  - Missing manifest, `bootstrapped: false`, or `--rebootstrap`: run `idea-interview`. It surveys
    the owner, records or generates core docs, provisions shared scaffolding, updates the manifest,
    and opens a separate bootstrap PR. Stop there and ask the owner to merge it before a feature.
  - `bootstrapped: true`: load source paths from the manifest. Repair a stale path in place rather
    than duplicating the document it points at.
- **Task** — use the free-text task when supplied. Otherwise read the idea and roadmap sources,
  inspect current code and recent history, propose 2–3 next coherent chunks, and let the user choose.
- **Ideate** — unless `--no-ideate`, run `feature-ideation`: challenge the chosen feature at the
  product level, agree what is in and out, and optionally append deferred ideas to the roadmap. The
  user may decline and build the roadmap version unchanged.
- **Design** — run `brainstorming`: clarify behavior, compare approaches, present a design, and get
  explicit approval. No implementation code before approval. After approval, write the feature spec
  and enter autonomous mode.
- **Plan** — run `writing-plans` for an executable implementation plan. No approval gate.
- **Build** — implement the approved design task by task using the project's conventions. Keep
  commits coherent and verification close to the changed behavior.
- **Test** — delegate to `tester` for uncovered paths and edge cases, then run the project's full
  declared test and lint suite. Fix product defects; never weaken a valid test for green output.
- **Review** — delegate an independent, read-only diff review to `reviewer`. Fix critical and major
  findings, then rerun the affected verification.
- **Security** — run a distinct security pass with the strongest capability available: injection,
  authentication and authorization, secrets and data exposure, unsafe deserialization, file and
  process handling, dependency and configuration risk. Fix every critical and high finding;
  document consciously deferred ones.
- **PR** — push the branch and open a pull request following `.github/pull_request_template.md` and
  `.agent-kit/rules/pull-requests.md`. Never merge. If no PR mechanism exists after every safe
  fallback, report that as the terminal blocker once the branch is pushed.
- **Docs** — run `docs-reflection`. No-op by default. If living docs genuinely diverged, open a
  separate docs-only PR from the default branch; otherwise mark docs as current in the feature PR.

The pipeline is complete when the feature PR exists and docs reflection is resolved — or when an
insurmountable blocker has been reported with the branch left in a recoverable state.
