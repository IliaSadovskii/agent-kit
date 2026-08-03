---
name: audit
description: Compare existing code to what the project's description says should be true, and write a work list — missing tests, stale or vulnerable dependencies, and surfaces that exist in one place and not the other. Reads and reports; never changes code.
argument-hint: "[тесты|зависимости | tests|deps] [area] — or say what worries you"
disable-model-invocation: true
---

# Audit

Reads existing code, compares it to `docs/knowledge/`, and writes a work list that `ship` and
`sprint` execute.

**It changes nothing.** Not code, not tests, not the description. Running a suite or a linter is
reading; writing a single line into the project is not this command's job. The moment an audit
starts fixing what it finds it loses its stopping condition, which is how a bounded question once
turned into an afternoon of screenshots.

Run it on code nobody watched being written: an inherited project, or a batch an autonomous run
landed overnight. After `ship` it is redundant — that diff was already reviewed against its entry.

## Invocation

| You type | What happens |
|---|---|
| `audit` | every lens, cheapest first, each writing its own file as it finishes |
| `audit tests` | one lens. Names are recognised in either language — `тесты` and `tests` are the same lens |
| `audit tests moderation` | one lens, narrowed to an area |
| `audit "why is moderation so slow"` | free text: map it to a lens, **say in one line what you understood**, then start |

If the first word is neither a lens nor clearly about one, **stop before doing anything**: print the
lenses and the one clarification worth making — whether they meant an area, which goes second.
Guessing costs a full run; asking costs nothing.

Lens files are named in English whatever language the lens was typed in, so a project that changes
its language does not end up with two sets.

## The baseline check

Two comparisons that belong to no lens and run every time, because they cost seconds and catch drift
in both directions:

- **a surface in the code that no entry describes** — a route, endpoint or command the application
  grew and nobody wrote down. Tests derived from the entries would never notice it.
- **an entry naming a surface that is gone.**

List the surfaces the way the stack itself does — `php artisan route:list`, the router's own dump,
the CLI's help. If the stack offers no such thing, skip the check and say so rather than guessing
from file names.

## How a lens works

The same shape every time, which is what keeps the cost proportional to what is found rather than to
the size of the project:

1. **Mechanical pass first.** Settle everything that needs no judgement. An entry whose entities,
   statuses and action key appear nowhere in the test suite is uncovered as a matter of fact — no
   reading required.
2. **Judgement only on what survived**, and only over the files the first pass pointed at. Never the
   codebase.
3. **Search per line, not per entry.** For each line of an entry, look for one test asserting it and
   stop at the first. Twenty tests around an entity prove nothing about the line that says what can
   go wrong — the count of matches is not evidence.
4. **Work area by area, writing the file as each area finishes.** The last entry of a long run is
   then judged on as small a working set as the first, and an interrupted run keeps what it did.
5. **Group the findings into batches**, each batch one `ship` run. A single missing test is five
   minutes, not a pull request; thirty of them as thirty items would be thirty pull requests.
6. **Write the lens's file and commit it** before moving to the next lens, so an interrupted run
   keeps everything it finished.

**Uncertainty resolves to a gap, never to "covered".** The two mistakes are not symmetrical: a
finding that turns out to be already covered costs the owner ten seconds of reading, and a gap
recorded as covered costs a bug that nobody will look for again.

**Every entry in scope gets a row**, including the covered ones and the ones you could not judge —
`covered`, `gaps`, `unjudged`, `declined`. Completeness is then something the owner can count rather
than something you claim.

**No verification pass.** A second agent re-checking the first doubles the price to catch a mistake
that costs ten seconds. That stacking is what once produced thirty findings and then twenty more.

**Delegation, and its limits.** A full run gives each lens its own subagent: lenses are independent,
and without the isolation the fifth carries everything the first four accumulated. A single-lens run
does the work inline — there a subagent pays the cost of orienting itself for context the session
already has.

Areas are **not** delegated. A subagent's floor is a few hundred thousand tokens before it produces
anything, and eight areas would spend more on orientation than the whole lens costs; the area walk is
about order and incremental writes, not isolation. The exception is a scope so large one session
cannot carry it — over forty entries, split by area.

Read entries the way `ship` does — a section at a time, never the whole file:

```bash
awk -v RS='\n### ' '/`key: developer\.create_offer`/{print "### " $0}' docs/knowledge/actions.md
```

## Lens: tests

Reference: the entries. Walks: every entry in scope.

Run the project's declared suite once first, from `project.yml` → `commands.test`, so the report
knows whether the existing tests even pass. Report the result; never fix it.

Then, per entry, per line — what changes, what the initiator sees, what others see, what can go
wrong — find the test that asserts it. A line with no test is a finding. An entry whose every line
has one is covered, and covered entries are worth one line in the file, not a section.

Say plainly in the file's header that a covered entry means a test exists, not that the test is
good.

## Lens: deps

Reference: the registries. Walks: the project's direct dependencies.

Use the ecosystem's own tooling rather than reasoning about versions — `composer outdated`,
`composer audit`, `npm outdated`, `npm audit`, `pip list --outdated`, whatever the stack has. Three
kinds of finding, in this order: a known vulnerability, a package past end of life, a major version
behind. Ignore patch drift; a project is not in trouble because something moved by 0.0.1.

This lens needs no `docs/knowledge/` at all, so it is the one that works on a project the kit has
never described.

## The work list

`docs/audits/<lens>.md`, one file per lens, rewritten by each run of that lens. Git holds the
history; a date in the filename would only make the previous state harder to find.

```markdown
# Tests — 2026-08-04

Suite: `make test` → 0, 118 passed. 35 entries, 21 with gaps, 3 declined.

## Moderation — one ship run
- [ ] `validator.check_post` — "what can go wrong" (engine unavailable) has no test
- [ ] `moderator.reject_post` — nothing asserts the author is notified
- [x] declined: `moderator.open_queue` — visual only

## Also noticed
- `PostPolicy::update` allows an author to edit a published post; no entry says that is possible
```

**Read the previous file before writing the new one.** Items the owner marked declined stay
declined and are not raised again; items that are gone since last time are gone because someone did
them. An audit that repeats what was already refused is an audit nobody runs twice.

Sort by what matters, and never truncate: an audit that caps its own survey is lying about coverage.
Sorting is what lets the owner read the top of the list and stop.

**Anything noticed outside the lens goes in "Also noticed".** Seeing a real defect and staying quiet
because it belonged to another lens is the worse failure.

**State the blind spot in the file, every time.** This list is complete against the description: an
area the description never mentioned is not in it, and the baseline check finds surfaces the code
exposes, not logic that has none. A report that names what it cannot see can be used; one that reads
as exhaustive cannot.

## Closing

Per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`: what is thin — which entries could not be judged and
why, whether the suite was red before you started — and then the one line naming what to run next,
which is usually the next lens or the `sprint` that eats this list.
