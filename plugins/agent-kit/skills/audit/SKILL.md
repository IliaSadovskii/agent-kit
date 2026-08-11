---
name: audit
description: Compare existing code to what the project's description says should be true, and write a work list — missing tests, stale or vulnerable dependencies, and surfaces that exist in one place and not the other. Reads and reports; never changes code.
argument-hint: "[tests|deps|scenarios|security|performance|conventions] [area] — or what worries you"
disable-model-invocation: true
---

# Audit

Reads existing code, compares it to `docs/knowledge/`, and writes a work list that `ship` and
`sprint` execute.

**It changes nothing but its own work list.** Not code, not tests, not the knowledge — the one file
it writes is `docs/audits/<lens>.md`, and that is the whole output. Running a suite or a linter is
reading. The moment an audit starts fixing what it finds it loses its stopping condition, which is
how a bounded question once turned into an afternoon of screenshots.

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

## The lenses that exist

**`tests`, `deps`, `scenarios`, `security`, `performance`, `conventions`.** Those are the six, and
nothing else is runnable.

All six are written, one file each under
`${CLAUDE_PLUGIN_ROOT}/skills/audit/references/`. Nothing here names a lens that does not exist.

## The baseline check

Two comparisons that belong to no lens and run **once per invocation, not once per lens** — a full
run does them before the first lens and never again, and they go in `docs/audits/baseline.md` of
their own. Repeating them in each lens file costs the same work twice and leaves two places for one
fact to disagree with itself.

They cost seconds and catch drift in both directions:

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
2. **A verdict rests on something you read, never on a search hit.** Grep locates a candidate and
   settles nothing: a match can be a fixture, a variable name, or an assertion about the neighbouring
   behavior. Open it and look. This is the rule that decides whether the report can be acted on —
   a false "covered" is never looked for again by anyone.
3. **Search per line, not per entry.** For each line of an entry, find the assertion that proves it.
   Twenty tests around an entity prove nothing about the line that says what can go wrong.
4. **Interpret the finding for this project.** A tool's output is an input, not a verdict: an
   advisory matters differently depending on whether the vulnerable path is reachable here.
5. **Work area by area, writing the file as each area finishes.** The last entry of a long run is
   then judged on as small a working set as the first, and an interrupted run keeps what it did.
6. **Group the findings into batches**, each batch one `ship` run, **in every lens**. A single
   missing test is five minutes, not a pull request, and thirty of them as thirty items would be
   thirty branches. What a batch is differs by lens and the shape does not: "apply these two
   security patches" is one run, "drop the three unused packages" is another, "move to the next
   framework major" is a project of its own and says so. The work list is what a `sprint` reads
   instead of composing a batch itself, so a lens that reports findings without units of work has
   not finished its job.
7. **Write the lens's file and commit it** before moving to the next lens, so an interrupted run
   keeps everything it finished.

**Uncertainty resolves to a gap, never to "covered".** The two mistakes are not symmetrical: a
finding that turns out to be already covered costs the owner ten seconds of reading, and a gap
recorded as covered costs a bug that nobody will look for again.

**Every item in scope gets a row**, including the ones that came out clean and the ones you could
not judge. A lens walking the entries has five verdicts and invents no sixth:

| | |
|---|---|
| `covered` | nothing is missing here |
| `gaps` | something is, and it is in the work list |
| `unjudged` | you could not settle it, and the row says why |
| `deferred` | there is nothing to judge yet — the entry is still `planned` |
| `declined` | looked at, and the work is not worth doing |

A lens that walks something else — scenarios, packages, the rules in `stack.md` — names its own
verdicts in its own file and marks them the same way.

**Write the verdict in the project's language and put the mark beside it in backticks** —
``**покрыто** `covered` `` — exactly as a translated heading carries `key:` and `state:`. The word
the owner reads is theirs; the mark is what the check reads, and it is the same in every language.

That matters in one place beyond bookkeeping: a ticked box in a work list means the work is done and
takes the item off every future list. Both things allowed to tick one must name the pull request
that closed it. A refusal is not that kind of tick — no pull request will ever close one — so it
carries the mark instead: `` - [x] `declined`: … ``.

**And the file says what it walked, in one line the check adds up:**

```
<!-- agent-kit:audit lens=tests walked=49 covered=33 gaps=8 unjudged=1 deferred=7 declined=0 -->
```

`walked` is the size of the scope this lens took; the rest are how it broke down, and they have to
sum to it. What the buckets are called is the lens's own business — the scenarios lens counts
`walks`, `breaks` and `unfollowable` — and the check knows none of them by name: it checks the
arithmetic, which survives translation.

Every lens defends in prose against the same failure — a lens that quietly narrows its own scope
reports cleanly about five things and says nothing about the thirty it never opened. Three of them
go as far as calling that countable. Until this line existed, the counting was left to the same
session that wrote the report.

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

## The lenses themselves

One file each, under `${CLAUDE_PLUGIN_ROOT}/skills/audit/references/`: `tests.md`, `deps.md`,
`scenarios.md`, `security.md`, `performance.md`, `conventions.md`.

**Read the one you are running, and no others.** Six descriptions is three hundred lines, and a
single-lens run that carries five it will never use pays for them on every step it takes afterwards.
A full run reads each one as it reaches that lens.

## The work list

`docs/audits/<lens>.md`, one file per lens, rewritten by each run of that lens, plus
`docs/audits/baseline.md` for the check that belongs to no lens. Git holds the
history; a date in the filename would only make the previous state harder to find.

```markdown
# Tests — 2026-08-04

<!-- agent-kit:audit lens=tests walked=35 covered=10 gaps=21 unjudged=1 deferred=0 declined=3 -->

Suite: `make test` → 0, 118 passed. 35 entries, 21 with gaps, 3 declined.

## Moderation — one ship run
- [ ] `validator.check_post` — "what can go wrong" (engine unavailable) has no test
- [ ] `moderator.reject_post` — nothing asserts the author is notified
- [x] `declined`: `moderator.open_queue` — visual only
- [x] `moderator.hide_post` — closed by PR #48

## Covered
`guest.open_post`
  what changes    → PostPageTest.php:41
  initiator sees  → PostPageTest.php:58
  can go wrong    → PostPageTest.php:72, 90

## Also noticed
- `PostPolicy::update` allows an author to edit a published post; no entry says that is possible
```

The covered section is the longest part of the file and that is correct: it is the only part a
reader can check, and an audit whose reassuring half cannot be checked is worth less than one that
reports nothing.

**Read the previous file before writing the new one.** Items marked `declined` stay declined and
are not raised again; items that are gone since last time are gone because someone did them. An
audit that repeats what was already refused is an audit nobody runs twice.

**A ticked item leaves the new file, and that is deliberate.** Its work is done, the pull request
that closed it is named in the old file, and git keeps that. Say the count in the header — *four
items this list carried are closed* — so the reader can tell items that were finished from items
that were dropped. The signature on a tick lives from the tick until your next run; nothing is meant
to carry it further, and this line exists so that dropping it is a decision rather than an oversight.

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
