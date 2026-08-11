# Pull requests

Every command that opens one follows this. Never merge — the owner merges.

The owner decides in the first five lines whether this is mergeable without reading the diff. That
is the whole design goal: everything below either serves that decision or collapses out of the way.
Write it in the project's language (`.agent-kit/project.yml` → `language`); the section names below
are canonical, so translate them with the body.

## Nothing is left on the owner

**Never write that something is the owner's to do.** Not *your call*, not *this one is on you*, not
*remains for you to decide*, not a table column named after them. The one exception is **Manual
actions**, which exists because a few things genuinely need hands and access — a secret, a
migration, an account somewhere — and even there the line says what to do, not whose fault it is
that it is undone.

Everything else the run did not finish is not a message to a person, it is **a record in a file**.
By the time you write this, every such thing is already in one — the run put it there as it went,
and the run file's fields are where you find them again. Your job here is the second half of the
sentence: what will raise it again.

| Where it is | What raises it |
|---|---|
| an `[assumed …]` or `[stale …]` block under the entry | the check prints it before every command; `blueprint` rewrites the entry and deletes the block |
| a test marked `agent-kit:unmet` | the check lists it; `sprint` with no theme offers it as a batch |
| a line in `docs/technical_debt.md` | the check counts it; `sprint` with no theme offers it |
| an item in an audit's work list | that lens on its next run, and `next` when it comes due |

So the sentence reads *recorded in `docs/technical_debt.md`, offered by the next sprint* — a
statement about where the project keeps it, not a task handed over. A leftover that is in none of
those files is not recorded at all, and writing it here as a request does not record it: put it in
its file first.

The reader should finish the description without a to-do list — knowing what changed, what was hard,
what is thin, and that nothing they just read depends on them remembering it.

## Sections, in order

- **What & why** — five lines or fewer. Which blueprint entry this builds, what it now does, and
  anything unusual about how.
- **Manual actions** — **only what needs hands *and* access**: a secret and where it goes, an
  account somewhere, a store's requirement, a device to hold, a production environment to fill in.
  One line each — what, where, why — grouped by **when**: before it will run at all, before this
  merges, before it ships. Never collapsed; this is the section they act on. "None." when there is
  nothing.

  Two things that look like manual actions and are not, because a list that holds them stops being
  read. **Anything a script can do belongs in the script**: a migration to apply, a build argument,
  a port, a file mode. If you did it by hand, fold it into `commands.run` and say you did.
  **A setting that already works is an assumption, not an action** — a limit somebody chose a
  default for, a threshold in a config file: it belongs in the Assumptions table, where a decision
  taken without the owner is what the reader is looking for. Measured on one run, a list of nineteen
  actions held six that genuinely needed a person, five a script should have done, and four settings
  that were working fine — and the six that mattered were unfindable among them.
- **Assumptions** — every decision taken without them, from the run file, as a table of decision and
  why. Never collapsed: an assumption the owner does not see defeats the point of recording it.
  Mark the ones also written into blueprint as `[assumed …]` blocks, so they know where to answer.
- **What was hard** — three to five lines, never collapsed, and skipped honestly when the feature
  went straight through. Where the work fought back and what you did about it: the approach that
  looked right and was not, the library that behaved differently from its documentation, the test
  that passed for the wrong reason until it was rewritten, the second attempt at a fix after the
  first proved half a fix. This is the part of a run that exists nowhere else — the code shows the
  answer and never the two answers before it — and it is what tells the owner whether the ground
  here is solid or was made to hold by one careful decision.
- **Proven** — which of the entry's lines have a test, what the suite returned, and whether the app
  was started and exercised. Name what is *not* proven and why. A feature that says it is unproven
  in one line is fine; one that looks proven and is not is the failure this section exists against.
  Tests left marked unmet go here in their own short list — the promise, the test that proves it
  absent, and what would have to change in the product. Never collapsed: a green suite that carries
  unkept promises is exactly the thing a reader will otherwise take for a clean bill.
  Work left undone is written into `docs/technical_debt.md` on this same branch and named here in
  one line, with what will raise it again — a leftover described only in a pull request is forgotten
  the day it merges.
- **Review** — the reviewer's findings and how each was closed, and whether the security pass ran or
  was skipped and why. Collapsible, count in the summary line.
- **Changes** — the key files and their role, as a table. Collapsible.

A Mermaid diagram when the change alters a flow — GitHub renders it. Tables for anything
enumerable. `<details>` for supporting evidence, with the conclusion in the `<summary>` line, so the
collapsed view still tells the whole story.

## Batches

A batch — a sprint, or one of an `epic`'s — opens **one** pull request, based on the default branch,
covering every feature in it. Its features chain off each other, so the last branch already holds
the batch and there is nothing to merge together first.

A feature inside a batch does not open one of its own. Its branch is pushed, so a pull request for
it alone is one `gh pr create --base <its base> --head <its branch>` away on the day it is wanted,
and the batch's own pull request prints that command per feature. Opening them in advance is what
caused two merge accidents — a feature merged into its parent branch instead of the default one, so
nothing reached it at all — and a review plugin that declines drafts silently skipping the pass.

The sections above are then composed across features rather than written per feature: one **Manual
actions** list in the order they must be done, one **Assumptions** table with a column for which
feature took each, and a **What did not happen** section — parked features and why — before either.

## A run's pull request, rewritten by every batch

An `epic` has one pull request and eleven batches rewrite its body, so **every rule above applies to
the run, not to the batch that happens to be writing.** Written per batch and appended, the body
grows with the number of batches instead of with the size of the product. Measured on one real run:
157 000 characters, of which a quarter was a list of every sentence the run changed in the
knowledge, a fifth was seventy assumptions in one uncollapsed table, and *What was hard* — three to
five lines by the rule above — was a hundred and eighty-seven.

So a batch inside a run **replaces** the body rather than adding to it, and four sections are held
to a size that does not depend on how many batches there have been:

- **What & why** — one line per batch, naming what the product can now do. Not the batch's report:
  that is its digest comment, which is where a reader goes for *what is new since I last looked*.
- **What was hard** — the five hardest things in the whole run, chosen again each time. Five per
  batch is the same rule applied eleven times, which is not the same rule.
- **Assumptions** — the expensive ones uncollapsed, by name: stored data, permissions, money, a
  public contract. The rest as one collapsed table with its count. Seventy uncollapsed rows defeat
  the reason the section is uncollapsed at all.
- **Knowledge this run corrected** — one line per entry: which entry, what it now says. What it said
  before goes in the collapsed half. A pull request that edits the description it is judged against
  must make *that it did* the easiest thing to see, which a six-hundred-line list does not.

Everything a batch knows that does not fit those is already written down twice — in its digest
comment and in `docs/runs/<slug>.json` — so nothing is lost by keeping it out of the body.
