# Review workflow

`review` surfaces the kit's independent review capability as a directly-invocable entry. It runs an
adversarial, read-only review of the current changes without going through `ship`. Follow
`.agent-kit/engine.md` and the active provider adapter. Never merge PRs.

## When to use

When you want a fresh-eyes review of work already in progress — the current working-tree changes or
the branch diff against the default branch — outside the full feature pipeline.

## Behavior

Delegate the review to the canonical `reviewer` role; do not duplicate its checklist here. The role
inspects the working changes (`git diff`) or the branch diff (`git diff main...HEAD`) with a fresh,
picky perspective. It has read and check-running access only — it never edits code.

Report the returned findings to the user by severity (critical / major / minor), each with a
`file:line` and a brief "why". The user decides what to act on; `review` itself changes nothing.