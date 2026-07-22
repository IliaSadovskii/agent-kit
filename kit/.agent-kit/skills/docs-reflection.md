# Docs Reflection

> **LANGUAGE:** talk to the user in the language from `.agent-kit/project/manifest.yml` → `language`. These
> instructions are in English; doc edits are in each doc's own language (the user's product docs
> are usually the user's language). Commit messages in English.

Keep the project's living documentation from going stale. After a feature ships, the main agent —
which just did the work and knows what actually changed — reviews the docs and reconciles them
with reality. This runs on the **main agent's own context on purpose** (not a fresh-eyes subagent):
the value is knowing what diverged during implementation.

<WHEN>
The final step of a feature, after the PR is open (the `Docs` step of Ship). It is a mandatory *review*,
but the usual *outcome is no-op* — most features don't warrant a doc change.
</WHEN>

## Don't assume a fixed list — scan

Different projects have different docs (a fresh project may have 3; an existing one 30). Do NOT
hardcode doc names. **Scan the docs directory** (the folder holding `manifest.sources`, default
`docs/`) plus the root `README.md`, and judge each file. This picks up docs added after bootstrap.

## Scope

**In scope — the living product/design docs:** roadmap, architecture, product spec, domain docs,
open-questions, dev guide — whatever this project actually has.

**Excluded, never touched here:**
- The engine/meta: `.agent-kit/`, `.claude/`, `.agents/`, `.codex/`, root `CLAUDE.md`, and root
  `AGENTS.md`. Those
  change only in meta mode, with the user.
- The immutable record: `docs/specs/` and `docs/plans/` — the letter of what was decided/built
  then; never rewritten after the fact.

## Per-doc judgment

Read the PR's `## Assumptions` / deviations and the feature spec first — that's where divergence is
already recorded. Then, per doc:
- **Roadmap** (path from `manifest.sources.roadmap`) — is the next item still the logical step; did
  a prerequisite surface (add an intermediate item); did anything become redundant; did a later
  phase's premises shift?
- **Architecture / spec / domain docs** — did the implementation diverge from the draft (the spec/
  Assumptions say so)? Reconcile the summary with what was actually built. Don't duplicate spec
  detail into them — keep the summary accurate.
- **Open-questions** — did the feature answer an open question (resolve/remove it) or raise a new
  one (add it)?
- **Coding-standards** — update ONLY if the feature established a durable new convention worth
  codifying (e.g. a new folder/layer pattern), not per routine feature.

## No-op by default

Update a doc ONLY where the feature genuinely diverged from it or concretely resolved/added
something — a reason nameable in one sentence. No speculative rewrites of stable sections. If a doc
is still accurate, leave it. Churn is the failure mode; a settled doc stays settled.

## Output

- **Nothing to change** → add one line to the feature PR description: `## Docs: reviewed, current`.
  Done. An honest trace that reflection happened.
- **Something to change** → a separate branch off the default branch using the active provider's
  branch prefix, one commit
  `docs: sync after <feature>`, a separate PR touching only the affected docs. Body: which docs
  changed and why, linking the feature PR. This runs autonomously — no gate. Keep it separate from
  the feature code PR (docs ≠ code).
