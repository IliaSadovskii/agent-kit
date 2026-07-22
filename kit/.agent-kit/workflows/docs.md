# Docs workflow

`docs` surfaces the kit's documentation-reflection capability as a directly-invocable entry: a
standalone reconciliation of the living docs outside the `ship` pipeline. Follow
`.agent-kit/engine.md` and the active provider adapter.

## When to use

When you want to check whether the project's living documentation still matches reality and reconcile
it if it drifted — without shipping a feature.

## Behavior

Run the canonical `docs-reflection` skill; do not duplicate its scope or per-doc judgment here. It
scans the docs directory plus the root `README.md`, judges each living product/design doc against
what the code actually does, and leaves settled docs untouched. The engine/meta files and the
immutable `docs/specs/` and `docs/plans/` records are out of scope.

Outcome mirrors the skill: if nothing genuinely diverged, report that the docs are current. If a doc
concretely diverged, propose or apply a docs-only update on a separate branch and PR, touching only
the affected docs — never product code.