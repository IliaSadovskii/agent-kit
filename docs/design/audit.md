# Audit — comparing code to the description

Designed 2026-08-03, written in 0.20.0 with two of its seven lenses. The kit could describe a project and build from the description,
but had no way to look at code that already exists and say what is missing. Two symptoms of the same
hole: `blueprint` once answered a doubt about readiness by building a screenshot harness and
spending 19.5M tokens, and the owner independently asked for a command that would cover an inherited
codebase with tests.

## What it is

Reads existing code, compares it to `docs/knowledge/`, writes a work list. **Changes nothing, ever
— no code, no tests, no documents.** The list is consumed by `ship` and `sprint`.

Run it on code nobody watched being written: an inherited project, or a batch an autonomous run
landed overnight. After `ship` it is redundant — that diff was already reviewed against its entry.

## A lens is a comparison plus a reference

Audit always compares code to something. A lens is which something. That makes the honest way to
enumerate lenses "which references exist", not "which topics sound useful".

**A lens is legitimate only when it has a finite list to walk.** The entries, the scenarios, the
dependency manifest, the rules in `stack.md` — the list is what gives the run a stopping condition.
Without one a lens is an expedition, which is exactly how a bounded question turned into 44
screenshots.

| Lens | Reference | Walks | When |
|---|---|---|---|
| **tests** | the entries | every entry | first version |
| **deps** | registries: versions, advisories, end of life | the dependency manifest | first version |
| **scenarios** | the scenarios, run against a live application | 8–10 scenarios | second |
| **performance** | known anti-patterns of the stack | actions × patterns | second |
| **security** | vulnerability classes, stack practice | actions touching untrusted input, permissions, money, files, outbound calls | second |
| **debt** | the stances and library map in `stack.md` | the rules recorded there | later |
| **readiness** | `product.md`'s environment plus the stack's own minimum | a checklist | later |

Two lenses were considered and are not in the table.

**Conformance — does the code do what the entry says — dissolves into tests.** Answering it by
reading code is an agent forming an opinion; answering it with a test derived from the entry is a
fact. The tests lens already produces those tests, so a separate lens would buy the same answer at a
worse quality.

**Capacity — will it hold N requests — has no reference.** Most projects state no volumes or
latencies, so there is nothing to compare against. What the owner actually wants from
"performance" is the anti-pattern catalogue: N+1 queries, unbounded selects, IO inside a loop, a
missing index under a real query pattern, synchronous work that belongs on a queue, a whole table
loaded into memory. That has a finite list and mostly mechanical detection, and it is in the table.

## The baseline check

Two greps that belong to no lens and run on every invocation, because they cost seconds and catch
drift in both directions:

- a route, endpoint or command in the code that no entry describes — the application grew a surface
  nobody wrote down, and a test derived from the entries would never notice;
- an entry naming a surface that no longer exists in the code.

## How every lens works

The shape is the same, which is what keeps the cost proportional to what is found rather than to the
size of the project:

1. **Scope** — the whole project, or one named area.
2. **Mechanical pass first.** Eliminate what can be settled without judgement: an entry whose
   entities and statuses appear nowhere in the test suite is uncovered, as a fact.
3. **Judgement only on what survives**, reading only the files that pass one, never the codebase.
4. **A work list**, each item sized for one `ship` run, sorted by what matters most. No cap — an
   audit that truncates its own survey is lying about coverage; sorting is what lets the owner read
   the top ten and stop.
5. **Anything noticed outside the lens** goes in a short separate section. Seeing a real defect and
   staying silent because it was not this lens's business is the worse failure.

Output lives in `docs/audits/<lens>.md` — **one file per lens, rewritten by each run of it**, not
one per run. Git already holds the history, and a date in the filename only makes the previous state
harder to find. Each run reads its own file first: items the owner marked declined are not raised
again, which is what makes a second audit worth running.

A finding is not a pull request. Items are grouped into batches, one batch per `ship` run, so thirty
missing tests do not become thirty branches.

The search inside a lens goes **per line of an entry, not per entry**: find one test asserting this
line and stop. A count of matches around an entity is not evidence about the line that says what can
go wrong, so there is no reading cap — the question bounds itself.

## Why the scenarios lens does not write the tests it wants

It runs the end-to-end tests if they exist and reports which scenarios fail — which is where a
defect like "every action works, the path between two of them does not" appears, invisible to any
test at the level of a single action. When they do not exist, the finding is exactly that, and the
work list carries one item per scenario.

The first run on a project with no end-to-end harness is therefore nearly empty, and that is honest:
it orders the harness it needs, and every run after it is cheap and strong.

## Naming a lens should not require remembering one

Three things, none of them machinery: the skill's `argument-hint` lists the lenses as the command is
typed; free text is accepted and mapped to a lens, with the mapping said out loud before any work
starts; and every run ends by naming the next lens worth running. With no argument at all it runs
every lens, cheapest first, committing each file as it finishes — so an interrupted full run keeps
what it finished.

An unrecognised first argument stops the run before anything happens. Guessing costs a full audit;
asking costs nothing.

## What the shape guarantees, and what it does not

**Guaranteed: completeness against the description.** A lens walks a list, and every item on it gets
a row in the output — covered, gaps, unjudged, declined. Whether the run finished is a count the
owner can do, not a claim the agent makes.

**Not guaranteed: anything the description does not know about.** An area blueprint never recorded
is invisible to every lens. The baseline check is the only defence and it finds *surfaces* — routes,
endpoints, commands — so logic with no surface of its own can hide indefinitely. The output says so
in every file rather than reading as exhaustive.

**Quality is bounded by the search, not by the judgement.** "Does any test assert this line" is a
narrow yes-or-no, and narrow questions degrade little across a long run. The failure mode is finding
the wrong files: a missed test produces a spurious item costing ten seconds of reading, while the
wrong files read as covered hide a gap that nobody looks for again. Hence the rule that uncertainty
resolves to a gap, and hence no verification pass — a second agent doubles the price against a
ten-second mistake.

**Cost, against measured numbers.** A single agent reading a real codebase and producing structure
runs 2–6M (blueprint on a real project: 5.6M first run, 2.0M second). A subagent's floor is 0.3–0.7M
before it does anything. So: one subagent per lens in a full run, where isolation saves more than the
floor costs; inline for a single lens, where it saves nothing; and never per area, where eight floors
would exceed the lens itself. Above forty entries the area split earns its keep and not before.

A five-lens run on a real project should land at 5–12M — a few times in a project's life, against 27M
for one feature under the pipeline this kit replaced. It balloons from exactly three things, all of
them now forbidden: agents per area, verification passes, and reading the codebase instead of walking
the list.

## First version: tests and deps

Two lenses, both cheap, before the other five. The point is to find out whether the shape of a lens
holds: if adding the third costs a page of text, the architecture is right. If each new lens needs
special handling, the frame is wrong — and it is better to learn that on the second lens than on the
fifth.
