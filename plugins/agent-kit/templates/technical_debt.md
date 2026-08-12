# Debt

Work that is understood and not done. Written by the runs and by `blueprint` when the owner brings
something back from using the product, read before every command, closed by whoever does the work.

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

**A line the owner brought carries `owner` where the run slug goes, and `—` for the pull request.**
They were using the product, not reading a diff, so there is no run and no number — and the word is
not bookkeeping: it says a person saw this happen. Whoever composes the next batch is choosing
between work a run decided to skip and work the owner watched go wrong, and those are not worth the
same. Without the word the line reads as neither.

Closed by deleting the line, in the commit that does the work, so the diff shows the debt going down
beside the code that paid it. **Never a ticked box** — a ticked box is a line nobody deletes
afterwards, and a ledger of them stops being read within a month; git holds every line that was ever
here, and the pull request holds the reasoning. The ticked boxes in this kit are in the audits' work
lists, which is a different file and a different rule.

If the work turns out bigger than its line said, the line stays and gains what was learned. **Half
an item deleted is worse than an item untouched**: the next run reads the shorter list and believes
it.

Nothing else edits this file: a run appends, a run that finishes an item removes it.

Keep it in the project's language, like everything else the owner reads.

```markdown
- [ ] pin the invariant the session fix rests on — a new path to an unverified account reopens the
      hole silently · guest.login_via_provider · 2026-08-05-security-and-deps · PR #21
- [ ] the two buttons under the answer sit together and get mistapped — the wrong one ends the
      lesson · student.answer_task · owner · —
```

Delete this file's own prose once the first real item is in it, or keep it — the check counts only
open boxes outside a fenced block, so the example above is not one.
