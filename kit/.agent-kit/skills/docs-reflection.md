# Docs Reflection

Keep the project's living documentation from going stale, as the final step of a feature after the
PR is open. It runs in the main agent's own context on purpose rather than in a fresh-eyes
subagent: the value here is knowing what actually diverged during implementation.

The review always happens; the outcome is usually nothing, because most features do not warrant a
doc change. Churn is the failure mode — a settled doc stays settled.

## Steps

1. **Read what already records the divergence** — the PR's Assumptions section and the feature
   spec. That is where deviations were logged during the run.
2. **Scan, don't assume a list** — the directory holding `manifest.sources` (default `docs/`) plus
   the root `README.md`. Projects differ, and docs get added after bootstrap.
3. **Judge each living document** against what the code now does:
   - **Roadmap** — is the next item still the logical step? Did a prerequisite surface, did
     something become redundant, did a later phase's premises shift?
   - **Architecture, product spec, domain docs** — did the implementation diverge from the draft?
     Reconcile the summary; don't copy spec detail into them.
   - **Open questions** — did this feature answer one, or raise a new one?
   - **Coding standards** — only when the feature established a durable new convention, not per
     routine feature.
4. **Update only where you can name the divergence in one sentence.** No speculative rewrites of
   stable sections.

Out of scope: `.agent-kit/`, `.claude/`, and root `CLAUDE.md`, which change only in meta mode with
the user; and `docs/specs/` and `docs/plans/`, which are the immutable record of what was decided
at the time.

## Outcome

- **Nothing changed** — add `## Docs: reviewed, current` to the feature PR description. Done.
- **Something changed** — a separate branch off the default branch, one commit
  `docs: sync after <feature>`, and a PR touching only the affected docs, saying which changed and
  why and linking the feature PR. Autonomous, no gate. Docs stay out of the code PR.
