# Debt

Work a run decided not to do. Written by the runs, read before every command, closed by whoever
does the work.

This is the ledger for the one thing the rest of the kit has nowhere to put. A decision about the
product goes into `docs/knowledge/` as an `[assumed …]` block. A promise the product does not keep
goes on a test as `agent-kit:unmet`. A feature described and unbuilt is `state: planned`. An audit's
findings are its own work list. What is left over is work this run created and did not finish —
a fix resting on an invariant nothing checks, a rename half applied, a review's minor left open
because it belonged to another command. Unwritten, it survives only in a pull request nobody reopens.

One line per item, newest first, four fields separated by `·` so the line can be read without
opening anything:

```markdown
- [ ] <what to do> — <why it matters, in one clause> · <entry key, or `—`> · <run slug> · PR #<n>
```

The entry key ties the item to the part of the product it belongs to, which is what lets a batch be
composed around one area rather than around whatever was written last; `—` when the item belongs to
no entry, like a tidy-up in the test suite. The run slug and the pull request are where the reasoning
still lives when the line is too short to carry it.

Closed by deleting the line, in the commit that does the work — a ticked box is a line nobody will
delete later. Nothing else edits this file: a run appends, a run that finishes an item removes it.

Keep it in the project's language, like everything else the owner reads.

- [ ] example: pin the invariant the session fix rests on — a new path to an unverified account
      reopens the hole silently · guest.login_via_provider · 2026-08-05-security-and-deps · PR #21
