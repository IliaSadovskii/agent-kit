# Pull requests

Every command that opens one follows this. Never merge — the owner merges.

The owner decides in the first five lines whether this is mergeable without reading the diff. That
is the whole design goal: everything below either serves that decision or collapses out of the way.
Write it in the project's language (`.agent-kit/project.yml` → `language`); the section names below
are canonical, so translate them with the body.

## The brief, and its ceiling

**Every pull request opens with four questions and answers nothing else in them.** They are the
whole of what the owner has to read; everything after is for whoever wants it.

1. **What works now that did not.** One line per feature, or per batch on a run of many. What the
   product does, in the owner's words — not what was built.
2. **What is needed from them to run it here.** From the `manual` records, and only those whose
   `when` this project has reached — see the stage rule under *Manual actions*. "Nothing" when there
   is nothing, and that is the common answer.
3. **What went wrong.** Composed from fields and never from judgement: parked or skipped features,
   `unmet` promises, red or unrun tests, `blockers`. Empty only when those fields are empty.
4. **What only they can decide.** At most five, each a question with the answer this run took as its
   default. The rest are recorded and raise themselves; see the table below.

**Two thousand five hundred characters, and the program counts them.** Before opening or editing a
pull request, write the body to a file and read it back:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --pr-body <that file>
```

The ceiling is on the brief and on the uncollapsed part below it, not on the whole body: a reader
who wants the detail should find it, and a reader who wants the decision should not have to walk
past it. It is a number rather than a paragraph asking for restraint because restraint was what the
rule asked for before, and one measured run answered with 45 000 characters — of which a table of
seventy assumptions was uncollapsed and *What was hard*, three to five lines by the rule below, was
a hundred and eighty-seven.

Length is also a property of the model rather than of this kit: the documents Claude writes to disk
run long unless a length is named, so naming one here is what makes the rest of this file work.

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

  **`stage` in `.agent-kit/project.yml` decides which of those groups is printed at all.** On a
  project at `development` there is no release, so `before it ships` is not a list of things for the
  owner: each of those lines goes into `docs/deployment.md` on this same branch and is named here in
  one line with a count. A push credential for an app nobody has published is not something anybody
  is going to do this week, and on one measured run that group was a third of nineteen items — which
  is what made the six that genuinely needed a person unfindable. Empty `stage` is not `development`:
  print everything and say the field is unanswered.

  **Each line carries its proof, and the proof is a command** — one that exits 0 once the action has
  been done. The same records go into `docs/manual.md` on this branch, where `check.py --manual`
  runs them later and deletes what has happened: this section is where the owner meets the list, and
  that file is what still holds it the day after the merge, when nobody opens this pull request
  again.

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
- **Proven** — which of the entry's lines have a test, what the suite returned **and the commit it
  returned it on**, from `proved_at`, and whether the app was started and exercised. Name what is *not* proven and why — **including every seam a proof went
  through a stand-in at**, by name, from the run files' `suite`: a fake gateway, a fake sign-in, a
  fixed clock. A feature proved entirely against doubles has proved the doubles, and on one measured
  run the real model was never called once in thirty hours. **And what `mutation` says**: how
  many changes to the product's own logic the suite caught and how many it slept through, or that
  the step did not run and why. Everything else in this section is a green tick reporting on
  itself; that pair of numbers is the only line in a pull request that says the tests would have
  noticed. A feature that says it is unproven
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

## Who may run a review over the whole diff

Settled here, once, because three files used to answer it and two of them disagreed — with the net
effect that nobody ran it at all.

- **A feature** never does. It was reviewed against its entry as it was built, and a second pass over
  the same diff is what the measurement above rules out.
- **A batch** offers `/code-review` on its pull request in its closing line, and never runs it: no
  agent can start that one. A few thousand lines on one topic is where it pays.
- **A run of many batches** does not offer it either. Its diff has been read twice with context
  nothing else has — by the reviewer against each entry, and by the audit's lenses over the whole
  branch — and a third pass, cold, over tens of thousands of lines returns a list nobody can act on
  before merging.

## A feature inside a batch opens none of its own

Its branch is pushed, so a pull request for it alone is one
`gh pr create --base <its base> --head <its branch>` away on the day it is wanted, and the batch's
own pull request prints that command per feature. Opening them in advance is what caused two merge
accidents — a feature merged into its parent branch instead of the default one, so nothing reached
it at all — and a review plugin that declines drafts silently skipping the pass.

**How a batch composes its own pull request out of its features, and how an `epic`'s eleven batches
share one, is in `${CLAUDE_PLUGIN_ROOT}/skills/sprint/references/close.md`** — the file the one
session that ever does it reads. It is not here because every feature reads this file on every run
and none of them will ever open a batch's pull request.
