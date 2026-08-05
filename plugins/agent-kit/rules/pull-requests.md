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

Everything else the run did not finish is not a message to a person, it is **a record in a file**,
and the sentence that names it says where it now lives and what will raise it again:

| What was left | Where it is now | What raises it |
|---|---|---|
| a decision taken without the owner | `[assumed …]` under the entry, in `docs/knowledge/` | the check prints it before every command; `blueprint` closes it |
| a promise the entry makes and the product does not keep | a test marked `agent-kit:unmet` | the check lists it; `sprint` with no theme offers it as a batch |
| work understood and not done | a line in `docs/technical_debt.md` | the check counts it; `sprint` with no theme offers it |
| a defect found but out of scope | a line in `docs/technical_debt.md`, or an audit's work list if a lens covers it | the same |
| an entry whose prose is now wrong | `[assumed …]` block plus a line in the ledger | `blueprint`, on the next run |

So the sentence reads *recorded in `docs/technical_debt.md`, offered by the next sprint* — a
statement about where the project keeps it, not a task handed over. If a leftover has no place in
that table, it does not go in the pull request as a request either: find its file, or it is not
recorded at all.

The reader should finish the description without a to-do list — knowing what changed, what was hard,
what is thin, and that nothing they just read depends on them remembering it.

## Sections, in order

- **What & why** — five lines or fewer. Which blueprint entry this builds, what it now does, and
  anything unusual about how.
- **Manual actions** — everything the owner must do by hand: new secrets and where they go, access
  grants, third-party accounts, a migration to run, a CI change. One line each — what, where, why,
  when. Never collapsed; this is the section they act on. "None." when there is nothing.
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

A batch — a sprint, or one of an `mvp`'s — opens **one** pull request, based on the default branch,
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
