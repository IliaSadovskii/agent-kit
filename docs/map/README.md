# The map

A read of the whole kit as it stood at **2.28.2, 21 August 2026**, made before the session layer
moves out and the kit starts building for other agent CLIs. Twelve agents each read one sector in
full and wrote nodes and edges in one shared vocabulary with a `file:line` citation under every
claim; two more merged them into one graph and one verified findings list.

The published page on top of these files:
https://claude.ai/code/artifact/ae3d59e7-009c-4f75-a409-9f959c98cc31

## The four answers

**Who writes it** — a mapping run, from scratch. Nothing here is appended to over time; a second
map replaces this one wholesale, because a half-updated map is worse than a dated one.

**Who reads it** — a session about to change the kit's structure, and the owner deciding what to
change. It is not read by any program and no command depends on it.

**Who may close it, and where** — the owner, by deleting the directory, once the numbers stop
matching the code. Every file carries the version it was read at, and a claim that no longer
matches the source is wrong, not stale: check the source, not this.

**What becomes impossible without it** — nothing mechanical. What it buys is one read instead of
twelve: without it, every structural change re-derives the same map from the same 6900 lines and
gets a slightly different answer each time.

## What is here

| File | What it holds |
|---|---|
| `FINDINGS.md` | 58 findings, ranked, each CONFIRMED / REFUTED / UNVERIFIABLE against the real source. Five were reproduced by running the program. Start here. |
| `GRAPH.md` | 250 nodes, 495 edges, merged and normalized: dangling edges, orphan nodes, and 15 places two sectors describe one thing differently. |
| `seams.md` | Every binding to Claude Code and to the local session layer, with blast radius. Written for the multi-provider work. |
| `orchestrate.md`, `check.md`, `hooks-runfile.md` | The three code sectors: CLI surfaces, state machines, decision trees, failure models. |
| `blueprint.md`, `ship.md`, `sprint.md`, `epic.md`, `fix-accept-next.md`, `audit-advise.md` | One per command family: phases, gates, refusals, IO, promises to other parts. |
| `rules.md` | The nine shared rules, their mechanics, their readers, and whether a program enforces each. |
| `data-and-scripts.md` | Templates to artifacts, the project data layer, `verification.yml`, and every check `validate.sh` performs. |

## How to read a sector file

Each has `NODES`, `EDGES`, an IO table, owner gates, refusals, and an `UNCERTAIN / CONTRADICTORY`
section — that last one is where the sector says plainly what it could not settle. Node ids share
prefixes across sectors (`cmd:`, `phase:`, `gate:`, `script:`, `hook:`, `agent:`, `rule:`, `tpl:`,
`file:`, `session:`, `ext:`), which is what let `GRAPH.md` join them and find the edges that point
at nothing.
