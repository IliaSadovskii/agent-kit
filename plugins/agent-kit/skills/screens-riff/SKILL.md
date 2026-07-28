---
name: screens-riff
description: Product thinking about the screens themselves — study the existing screen map, the product documents, and the code, then propose the screens the app is missing. Taken proposals land on the map as idea cards next to what already exists; turned-down ones stay as rejected memory, so the same idea is not proposed twice. Use when the owner asks what the app should grow next, what a flow is missing, or what to do with the screen map now that it exists.
argument-hint: "[focus]"
disable-model-invocation: true
---

# Screens riff

The map shows what the app *is*. This pass asks what it should become, and answers in the same
picture — a proposed screen is read next to the screens it sits between, which is the only way to
tell whether it belongs there.

Three commands touch the map, and keeping them apart is what makes it trustworthy:

| Command | Asks | Writes |
|---|---|---|
| `/agent-kit:screens` | what is true today | every card kept true, including an idea that got built; invents nothing |
| `/agent-kit:screens-riff` | what is missing | `idea` and `rejected` cards, builds nothing |
| `/agent-kit:riff` | what the product should be | roadmap lines, draws nothing |

This one is visual and product-shaped; `riff` is strategy. If a proposal here turns out to be a
strategy question rather than a screen, say so in the review and point at `/agent-kit:riff` rather
than drawing a card for it.

## Before you start

Read `${CLAUDE_PLUGIN_ROOT}/skills/screens/references/format.md`. You write the same file
`/agent-kit:screens` writes, under the same rules — ids, statuses, the element vocabulary, and the
way the viewer reports what it cannot honour. Only what this pass adds on top of the format is
stated here.

Find the map at `.agent-kit/project/manifest.yml` → `sources.screens` when that is registered, and
at `docs/screens/screens.data.js` when it is not — a manifest that ships the key empty is the
common case, so look on disk before concluding there is no map.

**No map, no riff.** If there is none, say that in one sentence, offer `/agent-kit:screens`, and
stop. Never generate one here: a map whose first commit mixes what exists with what was imagined in
a brainstorm is worthless for the one thing a map is for. And if the project has no screens at all —
a library, a CLI, a service — `/agent-kit:screens` will say so too, so do not push the owner toward
generating an empty map to have something to riff on.

`$ARGUMENTS` is an optional focus: a flow, a screen id, an area of the product. Without one, the
whole map is the arena — unlike `riff`, this command does not have to ask what to think about,
because the map already bounds it.

## What you read before proposing anything

| Source | What it gives |
|---|---|
| The map | the flows as they stand, what is built against what is only agreed, and every rejected entry |
| The product documents — `sources.idea` and `sources.roadmap`, else `docs/` and `README.md` | what the product is for. A screen that serves nothing stated is ornament |
| The code behind `implemented` screens | what a screen actually does. Its card is one line of purpose, and the gap between the two is where missing screens hide |

A screen the roadmap already promises is agreed work, not an idea. If the map does not have it,
that is drift for `/agent-kit:screens` — report it, don't propose it as new.

## The rejected check comes first

Read every `status: 'rejected'` entry before generating, not after. Match by meaning: the same job
for the person, in the same place in the flow, for the same value is the same idea however
differently it is titled. Those entries are kept forever precisely so that nobody spends the
owner's attention on the same proposal twice.

If circumstances genuinely changed — a screen dropped for "no audience" in a product that now has
that audience — do not write a new card anyway. Name the rejected entry and what changed, as a
question in the written review, and let the owner reopen it. Reopening their own rejection is
theirs to do.

## Generating

Work these as prompts, not as a form: dead ends, where a flow gives a person no way onward or back;
the states nobody drew — empty, error, loading, offline, first run, permission refused; the step
someone currently has to take outside the app; screens that would be better as one; the moment the
product's value first lands, and whether any screen makes it visible; what a standout version of
this flow has that this one does not.

Hold judgment while generating and judge in the round below. Two mistakes are cheap to make here:
proposing a screen because an app "should have" one rather than because someone needs it, and
answering every unanswered question with a settings screen.

**Screen-shaped, or not.** A proposal earns a card only when it is a place a person goes. Copy,
ordering, a control that belongs on a screen that already exists, a default worth changing — these
are real improvements and they belong in the written review, never on the map. A card is a promise
that a place exists; making one out of a wording fix teaches the reader to distrust every other
card.

## One round with the owner

`${CLAUDE_PLUGIN_ROOT}/rules/presenting.md` governs, and this is one structured round — use
AskUserQuestion when the session has it:

- One line per idea, plus one line for what it buys, stated as what a person gets.
- Where it lands: the flow, and what it connects to.
- Your recommendation, marked. Get behind the ones that earn it.
- The non-screen improvements in the same round, so the owner judges the whole picture at once.
- The strongest few, not everything generated. A round the owner has to grind through gets skimmed,
  and the presenting rule also forbids batching a dependency chain — if two ideas are alternatives
  to each other, settle that fork first and let the answer moot the rest.

Nothing is written before the owner marks each idea. Take and reject both land on the map: the
rejections are worth as much as the proposals, because an idea turned down with no trace comes back
next quarter with a different title. **Parked is a third answer** — an idea the owner finds
interesting but not now goes in the written review and onto no card at all, because a `rejected`
entry is permanent and would suppress it forever.

Record the reason for a rejection in the owner's words. If they gave none, write the one they
implied and mark it as yours — "Dropped (inferred): …" — so the next run can tell the owner's
judgment from your reading of it.

This command is interactive by design. There is no autonomous variant of it — the round is the
feature.

## What lands on the map

`screens.data.js` and nothing else. Never `screens.html`: the viewer is plugin-owned wherever it
sits and a later `/agent-kit:screens` run refreshes it.

- **Taken** → `status: 'idea'`, an id drawn from `meta.nextScreenId` with the counter raised, one
  line of `purpose` saying what a person does there, no `code` field — nothing implements an idea —
  the flow it belongs to, a sketched layout of the three to six rows that make it recognizable, and
  the transitions that connect it, with ids from `meta.nextTransitionId`. Put it in an existing
  flow unless it genuinely opens a new part of the app; a new flow is a new column, appended after
  the others.
- **Rejected** → `status: 'rejected'`, the reason in `purpose` after what it was ("A weekly PDF of
  saved items. Dropped: no audience for it."), two or three layout rows so the card stays
  recognizable, and no transitions — a rejected card is memory, and an arrow into a card hidden
  behind its filter draws nothing.
- **Both ends of every transition must exist**, or the viewer names it in the legend as dangling in
  front of whoever opens the map.
- **An `implemented` or `planned` card is never edited here.** Keeping those true is
  `/agent-kit:screens`'s job. An ideas pass that quietly re-statuses a shipped screen is exactly the
  confusion these two commands are split to prevent — report the drift instead. An arrow *out of* a
  shipped screen into a new idea is expected and does not touch it: a transition is its own entry.
- Append within a flow rather than reordering the file, so the diff shows the change rather than
  hiding it in a reshuffle.

## The PR

Docs-only, in the shape `/agent-kit:screens` uses: its own branch off the default branch, one
commit `docs: screens ideas` (or `docs: screens ideas — <focus>` when a focus was given), touching
nothing but the map. Never merge.

Before opening it, run `node --check` on the data file if Node is available — the map is loaded as
a script, so a syntax error reaches the owner as a blank page and no message at all.

The description carries the written review, which is the other half of this pass and does not exist
anywhere else:

- What was taken, one line and one id each — `#s12` in the viewer's address bar opens that card.
- What was rejected and why, so the reason is in the history as well as on the map.
- The improvements that were not screen-shaped. This is where they live: not as cards, and not as a
  separate report file nobody opens twice.
- The drift you found and did not fix — a card the code has outgrown, a screen the roadmap promises
  and the map lacks — as input to a `/agent-kit:screens` run.
- Anything the ideas needed and the format could not express, so a real gap is visible rather than
  worked around silently.
- That the map opens by double-clicking the viewer beside it.

**When nothing lands on the map there is no PR** — every idea parked, or none worth putting up —
and then the command's own output carries the whole review: the improvements that were not
screen-shaped, the drift, the parked ideas. Say it once, in the session, and write nothing.

Otherwise end by naming what starts the work — `/agent-kit:ship` with the screen the owner wants
built — and leave it to them. This command builds nothing.
