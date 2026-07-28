---
name: docs-reflection
description: Check whether the living documentation still matches what the code does. Invoked by ship's Docs step after the feature PR is open, and by the docs command. Updates only where you can name the divergence in one sentence.
---

# Docs Reflection

Keep the project's living documentation from going stale, as the final step of a feature after the
PR is open. Do not delegate this to a subagent: the whole value is knowing what actually diverged
while you were implementing, which a fresh context cannot see.

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
   - **Screen map** — when the project has one, at `manifest.sources.screens` or, since the manifest
     ships that key empty, at `docs/screens/screens.data.js`. It is a living document like any
     other, and this is where a feature pays its debt to it: a screen this feature built flips
     `planned` → `implemented` with its `code` path filled in, and a screen this feature introduced
     is added as `implemented` with the same path — no card claims to be built without one. New
     screens and transitions take ids from `meta.nextScreenId` / `meta.nextTransitionId` with the
     counter raised, and both ends of a new transition must be on the map, or the viewer reports it
     as dangling in front of whoever opens it. Nothing else on the map is touched: the format and
     the id rules belong to `/agent-kit:screens`
     (`${CLAUDE_PLUGIN_ROOT}/skills/screens/references/format.md`), reflection never renumbers, and
     a card this feature did not affect is that command's drift to find, not this step's. Only
     `screens.data.js` — never the viewer beside it.
   - **Open questions** — did this feature answer one, or raise a new one?
   - **Coding standards** — only when the feature established a durable new convention, not per
     routine feature. One more trigger: a review or security finding that traced back to a rule
     nobody had written down. A finding that will repeat is a missing rule.
4. **Update only where you can name the divergence in one sentence.** No speculative rewrites of
   stable sections.

Out of scope: `.agent-kit/`, `.claude/`, and root `CLAUDE.md`, which change only in meta mode with
the user; and `docs/specs/` and `docs/plans/`, which are the immutable record of what was decided
at the time. If the gap you found lives in `.agent-kit/project/instructions.md` — a command the run
had to rediscover, a convention it had to infer — propose the exact line in the PR description
instead of editing the file; that file changes with the user.

## Outcome

- **Nothing changed** — add `## Docs: reviewed, current` to the feature PR description. Done.
- **Something changed** — a separate branch off the default branch, one commit
  `docs: sync after <feature>`, and a PR touching only the affected docs, saying which changed and
  why and linking the feature PR. Autonomous, no gate. Docs stay out of the code PR.
- **The screen map changed** — the one exception: it rides in the feature PR. A card flipped to
  `implemented` points at code that exists only on the feature branch, so the same card on a branch
  cut from the default branch would point at nothing. Run `node --check` on the data file first if
  the project has Node — the map is loaded as a script, so a syntax error is a blank page and no
  message at all. Then commit it there, push it to the open PR, and say which cards moved and what
  drifted; if nothing else diverged, that note carries the `## Docs: reviewed, current` line too.
  Run from `/agent-kit:docs`, where there is no feature branch, the map goes in the docs PR like
  every other document.
