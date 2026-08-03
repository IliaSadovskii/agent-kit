---
name: audit
description: Compare existing code to what the project's description says should be true, and write a work list — missing tests, stale or vulnerable dependencies, and surfaces that exist in one place and not the other. Reads and reports; never changes code.
argument-hint: "[tests|deps|scenarios|security|performance|conventions] [area] — or what worries you"
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

## The lenses that exist

**`tests`, `deps`, `scenarios`, `security`, `performance`, `conventions`.** Those are the six, and
nothing else is runnable.

All six are written. Nothing in this file names a lens that does not exist.

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
wrong — answer four questions about the test that claims to prove it, in order, stopping at the
first "no":

1. **Is there one at all?** No match anywhere is a finding, and needs no reading.
2. **Is it about this line?** Read it. A hit inside fixture data or an assertion about neighbouring
   behavior is not coverage.
3. **Is the assertion strong enough to observe what the line claims?** A line saying the buyer is
   notified is not proven by `assertStatus(200)`.
4. **Does it cover the conditions the line names?** Three ways to go wrong and one of them asserted
   is a partial, and the partials are worth more than the absences — they are the ones that look
   covered.

**Covered is claimed with a citation, never with a word.** Every line credited as covered names the
test and the line number that proves it; a line with nothing to cite is a gap. A test's *name* is
not a citation — `it('shows the link to readers and not to the author')` is the test's claim about
itself, and the line it is credited for may be a different claim entirely.

```
author.report_post
  what changes         → ReportButtonTest.php:57
  initiator sees       → ReportButtonTest.php:64
  others see           → ReportTest.php:85
  can go wrong
    repeat report      → ReportButtonTest.php:140
    report count hidden from the author → none
```

The citation is what makes the verdict checkable in ten seconds and impossible to produce without
opening the file. An entry summarised as "covered" with no map behind it can only be believed, and
this lens exists so that nothing has to be.

**The map carries every line of the entry, and a line with nothing to cite is written `none`.**
A third marker, `n/a`, is allowed **only where the entry's line itself states that nothing happens**
— "what changes: nothing", "others see: nothing". Anywhere else it is `none` with extra steps: a
marker that needs neither a citation nor an admission is the next cheap path, and it looks like a
verdict.
Leaving it out instead is the cheap way to satisfy a citation rule: what remains looks dense and
proves nothing about what is absent. Each distinct claim inside a line gets its own row — "can go
wrong" listing three ways is three rows, not one.

**An entry with a single `none` is not covered.** It belongs among the gaps, however much of it is
cited. Covered means covered whole; anything else is a partial dressed as a verdict.

The map's completeness is arithmetic, not trust: the file's header declares its `fields:`, so a map
with fewer rows than the entry has lines is a defect in the report rather than an absence of
problems.

What this lens does **not** judge: how the test is built — brittle, slow, duplicated, sitting at the
wrong seam. That has a different reference, the project's own testing rules, and belongs to the
conventions lens. Nor does it invent conditions the entry never named: a missing edge case that no line mentions
is a hole in the description, and `blueprint` closes it.

## Lens: deps

Reference: the registries. Walks: the project's direct dependencies.

Use the ecosystem's own tooling rather than reasoning about versions — `composer outdated`,
`composer audit`, `npm outdated`, `npm audit`, `pip list --outdated`, whatever the stack has. Three
kinds of finding, in this order: a known vulnerability, a package past end of life, a major version
behind. Ignore patch drift; a project is not in trouble because something moved by 0.0.1.

**Relaying the tool's output is this lens's cheap path**, and it is what the owner could have run
themselves. So every finding carries the same kind of artefact the tests lens demands — a citation
that cannot be written without looking:

```
league/commonmark 2.4.1 → CVE-2025-… (XSS in inline HTML)
  used at        MarkdownRenderer.php:31, PostBody.php:18
  reachable      yes — post bodies are user text and pass through it
  upgrade to     2.6.0, no API change in the paths above

symfony/mailer 6.4 → end of life 2026-11
  used at        none — transitive through laravel/framework
  reachable      not directly; moves with the framework's own upgrade

filament/filament 3.2 → 4.0 available
  used at        src/Admin/** (14 panels)
  upgrade blocked by  4.0 requires Livewire 4; the project pins livewire/livewire ^3.5
```

Three fields, each of which forces a look: **where it is used** (call sites, or `none` for a
transitive dependency), **whether the vulnerable path is reachable here**, and **what the upgrade
costs or what blocks it**. A finding with no call sites and no reason is the tool's line copied
across.

Order by what the owner would act on first: a reachable vulnerability, then an unreachable one, then
end of life, then a major behind. Ignore patch drift entirely.

This lens needs no `docs/knowledge/` at all, so it is the one that works on a project the kit has
never described — and the only one that survives on a repository nobody has ever run `blueprint`
against.

## Lens: scenarios

Reference: `docs/knowledge/scenarios.md`. Walks: every scenario.

Tests prove the parts; scenarios prove the joins. A path where every action works and the step
between two of them does not is invisible to any test written at the level of one action, and it is
the defect a person notices first.

**Two passes, and the first needs no code.**

1. **Chain the steps against the entries.** Step N sets a status, step N+1 lists its preconditions —
   a mismatch is a finding without opening anything. The same for surfaces: if step N+1 is reached
   from a screen, some earlier step must lead to that screen. The entries already carry all of this.
2. **Trace the path through the code**, step by step: the implementation of each step exists, and
   the surface the next step needs is reachable from where the previous one leaves the actor.

Run the end-to-end tests first if the project has any, and report per scenario what they returned.
Where there are none, trace instead — an earlier draft of this lens reported "nothing to run" and
stopped, which on most projects means an empty audit and a defect left in place.

**The cheap path here is a verdict with no trace behind it** — "the path looks fine". So each
scenario is written as its steps, each step citing the code that carries it, and the break named at
the step where it happens:

```
Nino tells a story about a neighbour
  1. author.submit_post     SubmitPostAction.php:24 · route web.php:57 · from screen.new_post   ok
  2. author.edit_post_body  EditPostBodyAction.php:18                                           ok
  3. validator.check_post   ClaimPostForValidationAction.php:31                                 ok
  4. → published            PublishPostAction.php:40, sets post.published                       ok
  5. guest.browse_feed      Feed.php:66                                                         BREAKS
     the card links to the story only when the body is over 500 characters
     (post-card.blade.php:34), and this story is shorter
  verdict: breaks at step 5 — reachable in the entries, not reachable in the application
```

Each step carries **two citations, not one**: what implements it, and **what gets the actor to it
from the previous step** — the route, the link, the redirect, the button. The second is the one that
matters: an action can exist, be correct, be tested, and be unreachable from where the person
actually is, which is the whole class of defect this lens exists for.

**Citations come from the code, never from the entries.** An entry saying a step is reached from a
screen is the claim under test; quoting it back is the same substitution as crediting a test because
of its name. If the link is not in a template, a route or a controller, it is not there.

**Walk the whole scenario, past a break.** When a step breaks, assume it fixed and keep going: the
remaining steps may hold two more, and finding them a week later — one per fix — is the slow way to
learn what the owner wanted in one pass.

**Where end-to-end tests exist, name which test covers which scenario and check it walks the same
steps.** A green suite is not evidence that this path is the one covered; that is the test's own
claim about itself again.

Three verdicts, and no fourth may be invented: a scenario whose every step is cited and reachable
`walks`; one with a break is `breaks at step N` (all of them, listed); one with a step whose
implementation you could not find is `unfollowable` — which is not `walks`.

**Every scenario and every step appears in the map.** The file's own numbering says how many steps a
scenario has, so a shorter trace is a defect in the report, countable without reading it.

**It does not write the end-to-end tests it wants.** Tracing answers what is broken now; the tests
answer whether it breaks again, and building them means fixtures, seeding and often a harness the
project does not have — an owner's decision and a `ship` run, not a side effect of an audit. So the
work list opens with the harness when there is none, marked as the owner's decision, and carries one
item per scenario after it. Whoever writes those tests then knows which ones should fail first.

## Lens: security

Reference: two of them, and only one is generic. Walks: the actions that touch anything dangerous.

**Choosing the list is the first finding.** Go through every entry and mark it in or out, with the
reason in three words — untrusted input, permissions, money, files or processes, an outbound call, a
migration. Write the whole table, including the ones you excluded. A lens that quietly narrows its
own scope produces a clean report about five actions and says nothing about the thirty it never
looked at, and nobody can tell which happened.

**Half of this lens is about rules no scanner can know.** Every entry's *must never* lines and its
actor's — "a developer never sees another developer's offers", "the author is not shown the report
count" — are this product's own authorization rules. **Every one of them appears in the report**,
with a citation or `none`; leaving out the ones you could not place is how a report ends up dense
and silent about the gap.

For each, **two citations, not one: where the check is written, and where it is invoked on the path
the actor takes.** A policy method can be correct and never called, a middleware can be defined and
missing from the route group — the same defect the scenarios lens exists for, in permissions. One
citation proves the rule was thought about; two prove it runs.

And a name is not a check. `PostPolicy::report` existing, or `auth` appearing in a route file, is the
code's claim about itself — the same substitution as crediting a test for its name. Read the body.

**The other half is the generic classes, and the tool exists.** Run `/security-review` over the
files the risky actions live in — you can invoke it, unlike the review commands only a person can
start — rather than reasoning about injection and deserialization from scratch. Point it at those
files, not at the repository.

Also check what the repository itself gives away: credentials in tracked files, a committed `.env`,
keys in fixtures or seeds. That is the one part of production readiness a repository can actually
show.

**Every finding carries where and whether**, the same artefact the deps lens produces:

```
author.view_my_posts — must never: the moderation trail must not reach the author
  enforced at   MyPosts.php:71 (select list), MyPostsPolicy.php:18
  holds for     attempt_no, reason codes, human flag
  does not for  body_snapshot, raw_response — both selected, both rendered at my-posts.blade.php:88
  reachable     yes, any author on their own rejected story
```

**The scanner returning nothing is not a verdict.** It knows the classes in its own catalogue and
nothing about this product's rules; say what it covered and keep the two halves visibly separate in
the report.

Walk every risky action, past the first finding: stopping early leaves the rest to be found one per
fix. And do not attempt an exploit — the citation is the evidence, and a lens that changes state to
prove a point has stopped being a lens.

## Lens: performance

Reference: the anti-patterns of this stack. Walks: every action, against every pattern.

Not "will it hold ten thousand requests" — that needs numbers no project has written down. This
lens finds the code that is slow for a reason anyone would recognise, early, while it is cheap to
change.

**Write the catalogue into the report before using it.** Derive it from `stack.md` and the
framework's own documented pitfalls — a query per row of a loop, a select with no bound, IO inside a
loop, a missing index under a query the code actually makes, work done synchronously that the stack
would queue, a whole table pulled into memory, a hot read with no cache. The kit does not ship a
catalogue: what is an anti-pattern in one stack is the idiom of another, and a list baked in here
would be an opinion about somebody else's project. Writing it down is also what makes the scope of
the check visible — a finding-free report against three patterns is a different thing from one
against nine.

**The query is not where the cost is.** An action can build a perfectly bounded query and the extra
round trips happen in the template it feeds, in a serializer, in an accessor touched during
rendering. So each action carries **two citations: where the data is fetched, and where it is
consumed** — and the verdict is about the pair. Eager loading that covers what the action uses and
misses what the view uses is the normal shape of this defect, not an unusual one.

A method named `withRelations` is not evidence that the relations the view touches are loaded. Read
it, and read what the view touches.

**Name every consumer, not the first one.** An action's data can reach a list, a detail page, a
notification and an export; reading one template and citing it leaves a row that looks checked while
two consumers were never opened. Where you cannot enumerate them, say so — an honest `unjudged` is
worth more than a clean row nobody can trust.

**Every action in scope gets a row** — `clean`, a finding, or `unjudged` with the reason. A report
that lists only the problems cannot be told apart from one that stopped looking. Walk them all, past
the first finding.

```
guest.browse_feed
  fetched at    Feed.php:206 — with(['author','tags']), paginate(20)
  consumed at   post-card.blade.php:21 $post->origins->…  — not eager loaded
  pattern       a query per row of a loop
  cost          20 extra queries per page, one per card
  clean for     author, tags
```

**Profiler output is an input, not a verdict.** If the project runs a query counter, a debug bar or
a tracer, quote what it reported and say which path produced it; a number with no path behind it
explains nothing and cannot be rechecked. The kit adds no tooling and runs no benchmark — measuring
is somebody's work, and this lens is reading.

## Lens: conventions

Reference: `docs/knowledge/stack.md`. Walks: every rule written there.

The other five lenses check what the product does. This one checks **how it is built, against the
project's own words about how it should be** — the stances per area, the library map, the testing
rules, the list of what this project does not do.

**The rules are the list, so write them out and walk them one at a time.** A rule with nothing
violating it gets a row saying where you looked; a rule you could not check gets `unjudged` and the
reason. Reading the file and reporting three violations tells the owner nothing about the other
fifteen rules.

Four kinds of finding, and the first is the most valuable:

- **Hand-rolled where the library map names a package.** The project already depends on something
  that covers this, and someone wrote it again. Cite both — the code and the map line it ignores.
- **A stance broken.** The area's stance says one thing, the code does another. Cite the stance and
  the place.
- **Something on the "we do not do this" list, done.**
- **How a test is built** — brittle, slow, duplicated, asserting the implementation instead of the
  behavior, sitting at a lower seam than the project's rules ask for. The tests lens answers whether
  a test proves the entry; this one answers whether it was worth writing that way. Neither invents a
  rule the project never wrote down.

**A rule the project did not write is not a finding.** Your opinion about layering, naming or file
size is not this reference, and smuggling it in as a violation is how a lens becomes an argument.
Where the code is plainly worse than the rules require but no rule covers it, that is one line in
"also noticed" and a candidate for `blueprint` to record — not a violation of something unwritten.

**Say how thin the reference is.** This lens is worth exactly what `stack.md` is worth: on a project
whose stances were derived and confirmed, it finds real divergence; on one with three vague lines it
finds little, and that is a fact about `stack.md` rather than about the code. State which of the two
you were working with, in the file, before the findings.

## The work list

`docs/audits/<lens>.md`, one file per lens, rewritten by each run of that lens, plus
`docs/audits/baseline.md` for the check that belongs to no lens. Git holds the
history; a date in the filename would only make the previous state harder to find.

```markdown
# Tests — 2026-08-04

Suite: `make test` → 0, 118 passed. 35 entries, 21 with gaps, 3 declined.

## Moderation — one ship run
- [ ] `validator.check_post` — "what can go wrong" (engine unavailable) has no test
- [ ] `moderator.reject_post` — nothing asserts the author is notified
- [x] declined: `moderator.open_queue` — visual only

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
