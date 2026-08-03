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

**A lens is legitimate on three counts: a finite list to walk, a reference to walk it against, and
observability — what it checks has to be visible from where the audit stands.** The list is what
gives the run a stopping condition; without one a lens is an expedition, which is exactly how a
bounded question turned into 44 screenshots. The third count was added last and cost a lens.

**Readiness was removed by it.** "Is this ready" splits in two: whether everything inside the MVP
bounds is built and its scenarios pass, which the `built` markers and the scenarios lens already
answer; and whether the thing survives production — migrations on deploy, secrets out of the
repository, error tracking, backups, a health check, workers actually running. The second is real
and nothing else covers it, but **half of it cannot be seen from a repository at all**: whether
backups exist, whether monitoring receives anything, whether a restore was ever tested. A lens that
checks half its checklist honestly and guesses the other half is worse than none, because its output
reads as a checklist. The observable remainder — secrets in the repository — belongs to the security
lens, and the rest is left out.

That is the second time a removal beat an addition; the first was conformance dissolving into
tests.

| Lens | Reference | Walks | When |
|---|---|---|---|
| **tests** | the entries | every entry | first version |
| **deps** | registries: versions, advisories, end of life | the dependency manifest | first version |
| **scenarios** | the scenarios, run against a live application or traced through the code | 8–10 scenarios | first version |
| **performance** | known anti-patterns of the stack, derived from `stack.md` and never shipped with the kit | actions × patterns | first version |
| **security** | vulnerability classes and stack practice, **plus the "must never" lines of the entries** — a generic scanner cannot know this product's own authorization rules | actions touching untrusted input, permissions, money, files, outbound calls | first version |
| **conventions** | the testing rules, stances and library map in `stack.md` | the rules recorded there | third — it owns half of "is this test any good" |

Two lenses were considered and are not in the table.

**Conformance — does the code do what the entry says — dissolves into tests.** Answering it by
reading code is an agent forming an opinion; answering it with a test derived from the entry is a
fact. The tests lens already produces those tests, so a separate lens would buy the same answer at a
worse quality.

**Readiness — see the three counts above; it fails observability.**

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

## The scenarios lens walks the code when there is nothing to run

It runs the end-to-end tests if they exist and reports which scenarios fail — which is where a defect
like "every action works, the path between two of them does not" appears, invisible to any test at
the level of a single action.

When they do not exist, it **walks the scenario through the code**, step by step, and says where the
path breaks. An earlier draft had it report "nothing to run" and stop, which would make the first run
on most projects empty. Tracing is bounded by the same list — eight to ten scenarios — and finds the
break today, before anything is built.

It still does not write the tests. Tracing answers "what is broken now"; end-to-end tests answer
"will it break again", and building them means fixtures, seeding and often a harness that does not
exist yet — a decision for the owner and a `ship` run, not a side effect of an audit. So the work
list opens with the harness, marked as the owner's decision, and carries one item per scenario after
it. The trace also makes that work better: whoever writes the test already knows which scenarios are
broken, so it can be written to fail first.

## Naming a lens should not require remembering one

Three things, none of them machinery: the skill's `argument-hint` lists the lenses as the command is
typed; free text is accepted and mapped to a lens, with the mapping said out loud before any work
starts; and every run ends by naming the next lens worth running. With no argument at all it runs
every lens, cheapest first, committing each file as it finishes — so an interrupted full run keeps
what it finished.

An unrecognised first argument stops the run before anything happens. Guessing costs a full audit;
asking costs nothing.

## Depth is not what the list bounds

The first live run cost 1.7M and three minutes, and it was too cheap. Its verdicts of "covered"
rested on grep hits — a match near an entity was read as proof that the entity's riskiest line was
asserted — and two of thirty-five test files were opened. Sixteen gaps were facts, because absence of
any match is a fact. The seventeen coverings were guesses.

That was a design error, not an agent's shortcut: the text said "judge only over the files the
mechanical pass pointed at" and also "stop at the first match", and the cheaper reading won.

The correction is a recalibration of what audit optimises for. It is the **rarest** command in the
kit — a few times in a project's life — and its output has the longest life: it decides whether fifty
`built` markers can be believed. Cheapness is not its virtue; **being actable on** is. A false
"covered" is the worst product it can make, because nobody looks for it again.

> **The list bounds the breadth. Depth per item is not economised.**

Two rules follow, and they apply to every lens:

- **A verdict rests on something read.** A search locates a candidate and settles nothing.
- **A finding is interpreted for this project**, not relayed from a tool. Whether an advisory
  matters depends on whether the vulnerable path is reachable here.

Doubling the cost of a cheap thing leaves it cheap: the tests lens moves from ~1.7M to ~3–5M, which
buys the difference between a report you act on and one you re-check.

## Test quality splits in two, and both halves already have a reference

"Is this test any good" is not one question:

- **Does it prove the entry's line** — is it about that line at all, is the assertion strong enough
  to observe what the line claims, does it cover the conditions the line names. Reference: the entry.
  This is the tests lens, and it costs almost nothing extra, because the expensive part is opening
  the file and that is now happening anyway.
- **Is it well built** — brittle, slow, duplicated, sitting at the wrong seam. Reference: the
  project's own testing rules in `stack.md`. This is the conventions lens, which is why it moved up
  the queue.

Neither invents conditions the entry never named. A missing edge case nobody wrote down is a hole in
the description, and `blueprint` closes it — an audit that invents requirements has no stopping
condition.

## Instructions lose to the cheap path; formats do not

Two corrections were written as instructions — read the file, do not stop at a grep hit — and both
were followed in letter and skipped in substance. The second live run indexed every test *name* in
the suite and judged from those, which cost almost nothing and read plausibly: a name like
`it('shows the link to readers and not to the author')` is a claim about the test, not its content.
It produced a false covering that took one grep to disprove — the entry's line was about hiding the
report *count* from the author, and the assertion was about hiding the report *button*.

A false covering is the worst thing this command can produce, and an instruction not to make one is
worth nothing against a cheaper path. So the third correction is a **format**, not a rule:

> A line is covered only when the file names the test and line number proving it. No citation, no
> coverage.

A citation cannot be written without opening the file, so the shortcut stops being available rather
than being discouraged. It also removes the older hole where covered entries were listed as bare
names: nineteen of them, with no way to see which line each was credited by, and therefore nothing
to check.

The third run answered: cost went 2.0M to 5.1M, file reads 3 to 34, coverings 19 to 12, and the file
carried 155 real citations with line numbers. The format held.

It also opened the next cheap path, which is the same shape one level down: **cite what can be
cited and quietly omit the rest**. The disputed line — the report count hidden from an author —
simply did not appear in the map, and the entry stayed covered. Dense citation reads as thorough,
and nothing in the file said what was missing from it.

So the rule needs a completeness clause, and that one is arithmetic rather than trust: the map lists
every line of the entry, a line with nothing to cite is written `none`, and a single `none` moves the
entry out of covered. The entry's own header declares its `fields:`, so a short map is a defect in
the report, countable without reading it.

The lesson generalises past this lens, and it took three runs to state properly. Where a cheaper path
exists and produces plausible output, demand an artefact that path cannot produce — **and demand that
the artefact be complete**, or the omission becomes the new cheap path.

## The fourth run, and what a lens costs to make rigorous

| | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| cost | 1.7M | 2.0M | 5.1M | 5.1M |
| files read | 2 | 3 | 34 | 46 |
| report | 124 lines | 140 | 448 | 841 |
| citations | 0 | 0 | 155 | 392 |
| covered | 17 | 19 | 12 | 13 |

Cost reached a plateau while trustworthiness kept rising, which is the point the lens was aiming at:
three times the first run's price for a report that can be checked rather than believed. Spot-checking
citations against the test files found them exact to the line. The entry that produced the false
covering is now in the gaps, demoted by a single `none`.

The fourth run also invented a third marker, `n/a`, for lines whose entry says nothing happens. Used
honestly there — and it is the next cheap path everywhere else, since it demands neither a citation
nor an admission. Allowed only where the entry's own line states the absence.

**And the architecture answered its own question.** Bringing the deps lens to the same rigour cost a
paragraph: the cheap path there is relaying the tool's output, so the artefact is where the package
is used in this codebase, whether the vulnerable path is reachable, and what the upgrade costs. Same
shape, one page, no special handling — which is what shipping two lenses first was meant to find out.

## Extrapolating the cheap paths to a new lens

Four cheap paths appeared over four runs of the tests lens, each replacing evidence with something
that resembles it: a grep hit for a reading, a test's *name* for its content, omission for an
admission, and an invented marker that demands neither. Three of the four have exact analogues in
any lens, and it is cheaper to close them before the first run than after it.

For scenarios the analogues are: crediting reachability to **the entry that claims it** rather than
to the code (the name substitution, and the sharpest one here, since the entry is precisely what is
under test); citing the implementation of a step while leaving the *link between steps* unevidenced —
which is the entire class of defect the lens exists for, an action that is correct, tested and
unreachable; skipping a step or a scenario; and inventing a fourth verdict such as "partially walks".

Two more are specific to this lens. Stopping at the first break is cheaper and leaves the remaining
breaks to be discovered one per fix over the following weeks. And a green end-to-end suite is not
evidence that the covered path is *this* scenario — the test's claim about itself, one more time.

All six are closed in the lens as written, which is the first time this has happened before a run
rather than after four.

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
