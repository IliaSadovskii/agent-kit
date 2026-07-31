---
name: riff
description: Standalone product thinking before any feature is chosen — generate ideas widely across the product, argue them out, and roadmap the survivors. Builds nothing, writes no code.
argument-hint: "[theme]"
disable-model-invocation: true
---

# Riff

Product thinking with no feature chosen yet and nothing to ship at the end of it. This is the broad
scope of `ideate`; inside `ship` the same skill runs narrowed to one already-chosen feature.

Theme: `$ARGUMENTS`. If none was given, ask in one message what to riff on rather than guessing —
"the whole product" produces shallow ideas.

A screen theme — a standalone `S<digits>` token, or an explicit mention of screens or the screen
map — runs the `screens-riff` skill instead: it studies the screen map, the product documents, and
the code, then proposes screens the app is missing, landing taken proposals on the map as `idea`
cards and turned-down ones as `rejected` memory. When the theme could be either a screen question or
a strategy question, ask rather than guessing.

If `.agent-kit/project/manifest.yml` is missing or registers no idea and roadmap, there is no north
star to judge ideas against. Say so and offer `/agent-kit:ship`, which runs the bootstrap interview
first; if the user wants to riff anyway, work from the code and `README.md` and say plainly that
the judgments have no stated product intent behind them.

Run `ideate` in its broad scope: load the product's north star and roadmap from the manifest
sources, generate widely across the lenses it lists, then judge honestly. Sort the results into
keep, park, and cut, and append only the keepers to the roadmap, with the user's explicit
go-ahead and phrased as user value.

Two things to hold onto here, because nothing downstream will catch them:

- **Nothing is built and nothing is committed except the roadmap lines the user approved.** No
  branch, no code, no handoff into `ship` on your own initiative. If an idea excites you, that is
  still not a mandate to start it.
- **The roadmap is append-only in this skill.** Reordering or rewriting entries that are already
  there is the owner's call, not a side effect of a brainstorm.

End by naming the command that starts whatever the user picked — usually
`/agent-kit:ship <the idea>` — and let them decide when to run it.
