---
name: screens
description: Build and maintain the project's visual screen map — every screen of the app as a wireframe card, transitions as labelled arrows, statuses separating what is built from what is only planned. Generated from the project's own documents and code, reconciled rather than regenerated on later runs, and readable offline by opening one HTML file. Use when the owner asks for a screen map, a user-flow diagram, or an inventory of the app's screens.
disable-model-invocation: true
---

# Screens

A product that has screens is understood by looking at them, not by reading a list of them. This
command turns the project's own documents and code into that picture.

It writes exactly two files, at `manifest.sources.screens` when that is already registered and in
`docs/screens/` by default when it is not:

```text
docs/screens/screens.data.js   the map — the only file this command ever edits
docs/screens/screens.html      the viewer — copied from the plugin, opened with a double click
```

The map is a working document, not a diagram someone drew once. Its value is entirely in staying
true: a card marked `implemented` must point at code that exists, and a screen someone rejected
must still be there with the reason, or the same idea gets re-proposed every quarter.

## Before you start

Read `${CLAUDE_PLUGIN_ROOT}/skills/screens/references/format.md` — the whole format, including the
element vocabulary and the id rules. Do not invent fields; the viewer only draws what is there.

Then find the ground truth:

- `.agent-kit/project/manifest.yml` → the registered idea, roadmap, and documentation sources;
  `sources.coding_standards`, which is where the stack playbook recorded this project's stack and
  its house conventions; and `sources.screens` if a map already exists.
- No manifest — this still works. Read `docs/` and `README.md`, and say once that the map is built
  from those because the project has no registered sources.

**A project with no screens gets no map.** A library, a CLI, a backend service with only endpoints —
if neither the documents nor the code describe anything a person looks at, say that in one sentence
and stop. No files, no branch, no PR. An empty map is worse than none: it looks like an answer.

## First run

1. **Set the platform, once.** If `meta.platform` already has a value, leave it alone — it is the
   owner's. Otherwise derive it from the stack the playbook recorded, or from the code: mobile, web,
   or desktop. It only picks the card frame. Say which you chose.
2. **Read the product documents** for the screens that are *described* — the idea document, the
   roadmap, any flow or UX notes. These give you purposes and triggers, which code cannot.
3. **Scan the code** for the screens that *exist* — see below. A screen found in code is
   `implemented` and carries its `code` path; a screen described in the docs with no code behind it
   is `planned`.
4. **Compose the map.** Group screens into flows a person would recognize (onboarding, browse,
   checkout, account) — flows become the columns, so this grouping is what makes the map readable.
   Write the wireframe rows per the reference, from what the screen actually contains. Write
   transitions for the paths the docs or the code support, and give each one a trigger in the
   person's words.
5. **Copy the viewer** from `${CLAUDE_PLUGIN_ROOT}/templates/screens/screens.html` unchanged. Do
   not copy the demo `screens.data.js` next to it — that is the kit's example, and the project's map
   replaces it.
6. **Register it** when a manifest exists: `sources.screens: docs/screens/screens.data.js`. Without
   a manifest, skip this silently — the files work on their own.

## Later runs reconcile, they never regenerate

Regenerating throws away everything the map knows that the code does not: the rejected screens, the
ideas, the phrasing the owner corrected. So read the existing file first and change it in place.

- **Ids are stable.** Allocate new ones from `meta.nextScreenId` / `meta.nextTransitionId` and raise
  the counter; the reference explains why that rule has no exceptions.
- **`planned` → `implemented`** when the code appeared, with the `code` path filled in. That flip is
  the map's main job.
- **`implemented` → drift, not deletion,** when the code is gone: check whether it moved before
  concluding anything, and report a screen that truly vanished rather than quietly removing a card.
- **`idea` and `rejected` entries survive untouched** unless the owner said otherwise. A rejected
  screen that got built becomes `implemented`, and that is worth saying out loud in the PR.
- **New screens found in code or docs are added** to the flow they belong to, appended after their
  neighbours rather than reordered into place.
- **The viewer is refreshed** when it differs from the plugin's current copy — it is plugin-owned
  wherever it sits, which `docs/developing.md` records as the one exception to what a project owns.
  Copy it over and mention the refresh in the PR.

Report the drift you found either way: what flipped, what is new, what the docs promise and the
code does not have.

## The code scan

**Find the router first.** Whatever the stack calls it — a routes directory, a navigator, a URL
configuration, a list of destinations — it is a screen inventory somebody already wrote and kept
current, and reading it beats pattern-matching component names. The playbook in
`sources.coding_standards` names this project's framework and its conventions; a shipped list of
per-stack file patterns would be stale training data pretending to be knowledge.

**Then the screens the router does not reach** — modals, sheets, error and empty states. Take the
naming convention from the screen files the router did point at: one of them names the pattern for
the rest.

What the scan cannot resolve is reported as drift and never guessed at. A screen this command
cannot name is one the next run will find; a screen it invents is one the owner has to disprove.

## Boundaries

- **Nothing is invented here.** A screen appears only if the docs describe it or the code contains
  it. Proposing screens that should exist is product thinking, and it belongs to a separate pass so
  that the owner always knows whether they are reading the app or a proposal.
- **Only `screens.data.js` is edited.** Not the viewer, except for the version refresh above.
- **The map is not a spec.** One line of purpose per screen; the detail lives in `docs/specs/`.

## Output

A docs-only change, in the style of `docs`: its own branch off the default branch, one commit
`docs: screens map` (or `docs: screens map — <what drifted>` on a reconcile), and a PR touching
nothing but `docs/screens/` and the manifest line that registers it. Never merge.

Before opening it, re-read the diff, and if the project has Node available run
`node --check docs/screens/screens.data.js` — the map is loaded as a script, so a syntax error is a
blank page rather than an error message. Then say in the PR what changed and what drifted, and
that the map opens by double-clicking `docs/screens/screens.html`.

**Nothing diverged is the expected outcome most of the time**: no branch, no PR, one sentence
saying the map is current.
