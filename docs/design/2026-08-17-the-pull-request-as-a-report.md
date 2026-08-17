# The pull request as a report, 17 August 2026

The owner read the first batch pull request written under the 2.15.0 rules — `beeplish` #21, five
features and a frame — and asked whether it counted as short. It did not, and the interesting part is
that its writer had followed every rule in the kit exactly.

Their framing, given twice before this and written down nowhere: **a pull request is a report to
somebody who has other work.** The essence of what was done, in bullets. Whether anything is needed
from them. Blockers, if there were any. Everything else omitted or behind a spoiler.

## What was measured

`check.py --pr-body` on the body of #21:

| | |
|---|---|
| whole body | 21 747 characters, 217 lines |
| uncollapsed | **11 972** against the budget of 12 000 |
| of that, the brief | 2 152 against the 2 500 the rule names |
| folded | 7 blocks, 9 775 characters — the review, five features one by one, the file map |
| biggest open table | 10 rows of 15 allowed |

Two things follow, and they point in opposite directions. The folding mechanism works: #15, the run
before the rules existed, was 81 KB. And the ceiling is not a ceiling on *short* — it was chosen
against a 45 000-character disaster, and the first body written to it came in 28 characters under.
A body that lands at 99.8% of a budget is a body written to a target.

Where the open 11 972 went: Proven 3 843, Assumptions 2 742, the brief 2 152, What was hard 1 443,
the rest 1 792. Two sections were more than half of it — and **both were pinned open by the rule**:
*Assumptions — never collapsed*, *Proven — never collapsed*, *What was hard — never collapsed*. So
was the batch's own list of unkept promises. The writer had no room to be shorter.

## Why those three could be folded, and why one line of them could not

Each *never collapsed* was written after something was lost, and each reason was about the pull
request being the **only** place the fact would reach the owner. That is no longer true, and the same
file says so three paragraphs earlier, in *Nothing is left on the owner*: an assumption is an
`[assumed …]` block under its entry, printed by `check.py` before every command and closed only by
`blueprint`; an unkept promise is a marked test the check lists and `sprint` offers as a batch;
undone work is a line in `docs/technical_debt.md`. Folding a section does not delete a fact that has
a file and a program behind it — it costs the fact its *first* sight, and the fact comes back through
its own channel.

So the test for what stays open is not *is this important*. It is **can the reader be misled by not
seeing it.** Exactly one thing on that list fails it: a suite reported green while the product
contradicts entries nobody has read. That is why the promises are named — one line each — up in
*what went wrong*, while the evidence for them stays folded. Everything else in a pull request
survives being folded, which is why everything else now is.

**This note is what closes those three prose rules**, per `CLAUDE.md`: a rule that lives in prose is
closed by a design note saying so, and not by whoever next finds it inconvenient.

## The numbers

- **the brief — 2 500 characters, and the program now counts them.** It has asked for that since
  2.15.0 and nothing measured it: the program counted the whole uncollapsed body against one number,
  so a short brief under ten thousand characters of open evidence passed. The brief is everything
  above the first `##` heading — the writer decides where that is, because matching the section names
  would make the program answer differently per project, and those names are translated.
- **uncollapsed in the whole body — 4 000**, down from 12 000. Derived from #21 rather than chosen:
  its brief (2 152), its manual actions (264), what did not happen (140), and the not-proven half of
  Proven trimmed to the three to five lines the rule already asks for (~900) come to about 3 450.
- **the biggest uncollapsed table — 15 rows**, unchanged. Under the new shape every long table is
  folded anyway, and folded tables are not counted.

## What is left

**One body is one data point.** These two numbers are derived from #21 and nothing else — #15 is
from before the rules and cannot be a second point. The next batch pull request is the measurement
that either confirms 4 000 or moves it, and the rule now says in as many words that moving it is
allowed and belongs in the changelog.

**Nothing counts sections against the shape.** The program counts characters, not whether Assumptions
is inside a `<details>`. A body that keeps everything open and simply writes less would pass. That is
the same trade the character budget already makes, and it is worth an eye rather than a check: the
cheap way to satisfy a length is to delete evidence, and this kit would rather have the evidence
folded than gone.
