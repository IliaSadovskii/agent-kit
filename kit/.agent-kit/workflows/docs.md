# Docs workflow

A standalone reconciliation of the living documentation against what the code actually does,
outside the `ship` pipeline.

Run the `docs-reflection` skill; its scope and per-document judgment live there. If nothing
genuinely diverged, say so. If something did, apply a docs-only update on its own branch and PR,
touching no product code.
