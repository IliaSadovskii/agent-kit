---
name: docs
description: Reconcile the project's living documentation against what the code actually does, outside the ship pipeline. Updates only where docs genuinely diverged, and opens a docs-only PR.
disable-model-invocation: true
---

# Docs

A standalone reconciliation of the living documentation against what the code actually does. Inside
`ship`, `docs-reflection` runs with the feature fresh in context and the PR's Assumptions to read
from. Here there is no such record, so establish the ground truth first.

1. **Find the window.** Ask what should be covered, or infer it: the commits since the last
   `docs: sync` commit, or since the last release tag. Say which range you settled on before you
   start reading — the user can correct it in one word, and getting it wrong wastes the whole pass.
2. **Read what changed.** The diff over that window, and the specs under `docs/specs/` that were
   written for it. This is what `docs-reflection` normally gets for free from having just built the
   feature.
3. **Run `docs-reflection`** with that context. Its per-document judgment and its out-of-scope list
   live there and are unchanged.

If nothing genuinely diverged, say so and stop — no branch, no PR, no churn. A settled document
stays settled, and "the docs are current" is the expected outcome most of the time.

If something did diverge, apply a docs-only update on its own branch, one commit
`docs: sync <range or topic>`, and open a PR touching no product code. Say in the description which
documents changed and why.
