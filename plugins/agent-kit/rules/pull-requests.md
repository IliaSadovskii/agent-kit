# Pull requests

Every command that opens one follows this. Never merge — the owner merges.

The owner decides in the first five lines whether this is mergeable without reading the diff. That
is the whole design goal: everything below either serves that decision or collapses out of the way.
Write it in the project's language (`.agent-kit/project.yml` → `language`); the section names below
are canonical, so translate them with the body.

## Sections, in order

- **What & why** — five lines or fewer. Which blueprint entry this builds, what it now does, and
  anything unusual about how.
- **Manual actions** — everything the owner must do by hand: new secrets and where they go, access
  grants, third-party accounts, a migration to run, a CI change. One line each — what, where, why,
  when. Never collapsed; this is the section they act on. "None." when there is nothing.
- **Assumptions** — every decision taken without them, from the run file, as a table of decision and
  why. Never collapsed: an assumption the owner does not see defeats the point of recording it.
  Mark the ones also written into blueprint as `[assumed …]` blocks, so they know where to answer.
- **Proven** — which of the entry's lines have a test, what the suite returned, and whether the app
  was started and exercised. Name what is *not* proven and why. A feature that says it is unproven
  in one line is fine; one that looks proven and is not is the failure this section exists against.
- **Review** — the reviewer's findings and how each was closed, and whether the security pass ran or
  was skipped and why. Collapsible, count in the summary line.
- **Changes** — the key files and their role, as a table. Collapsible.

A Mermaid diagram when the change alters a flow — GitHub renders it. Tables for anything
enumerable. `<details>` for supporting evidence, with the conclusion in the `<summary>` line, so the
collapsed view still tells the whole story.

## Stacked features

A pull request based on another feature's branch cannot land code: merging it moves the code
sideways. Open it as normal and say in the first line which batch it belongs to, what it is based
on, and that it reaches the default branch through that batch's integration pull request. Parking
it — draft, closing, whatever the batch decides — belongs to whoever launched the feature, not to
the run that opened it.
