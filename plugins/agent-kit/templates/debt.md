# Debt

Work a run decided not to do. Written by the runs, read before every command, closed by whoever
does the work.

This is the ledger for the one thing the rest of the kit has nowhere to put. A decision about the
product goes into `docs/knowledge/` as an `[assumed …]` block. A promise the product does not keep
goes on a test as `agent-kit:unmet`. A feature described and unbuilt is `state: planned`. An audit's
findings are its own work list. What is left over is work this run created and did not finish —
a fix resting on an invariant nothing checks, a rename half applied, a review's minor left open
because it belonged to another command. Unwritten, it survives only in a pull request nobody reopens.

One line per item, newest first:

```markdown
- [ ] <what to do> — <why it matters, in one clause> · <run slug> · PR #<n>
```

Closed by deleting the line, in the commit that does the work — a ticked box is a line nobody will
delete later. Nothing else edits this file: a run appends, a run that finishes an item removes it.

Keep it in the project's language, like everything else the owner reads.

- [ ] example: pin the invariant the session fix rests on — a new path to an unverified account
      reopens the hole silently · 2026-08-05-security-and-deps · PR #21
