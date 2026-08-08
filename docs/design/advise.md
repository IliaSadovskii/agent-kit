# Advise — questioning the description instead of building from it

Designed 2026-08-09, after `blueprint`, `ship`, `audit`, `sprint`, `mvp`, `fix` and `next` were all
live. The kit can describe a project and build exactly what was described, quickly and faithfully.
Nothing in it ever asks whether the description is worth building.

Two commands touch the knowledge and neither may doubt it. `blueprint` transcribes the owner's
intent and is explicitly forbidden from changing what the product must do. `audit` compares code
against the knowledge, which makes the knowledge its reference — assumed true by construction. So a
mediocre description is built carefully, tested against itself, and audited as correct.

The same hole exists one level down. All six audit lenses compare code to the `stack.md` that
already exists. The stack itself was chosen once, at interview time, before there was any code, and
is never reconsidered.

## Why this was rejected once, and what is different

[kit-v1.md](kit-v1.md) dropped `riff` and `ideate` outright: *product thinking without a build is a
conversation with the agent; a command would exist only to carry roadmap machinery.*

That objection is correct and has to be answered rather than avoided. It is answered by one thing:
**a conversation cannot be closed.** Ask the agent for ideas twice and the second session produces
the first session's list again, because nothing recorded that four of them were already refused.
A declined line in a file is closed for good, and that is the entire machinery this command carries
— the same rail `audit` already runs on. No roadmap, no queue, no priorities.

If the closing rail is ever removed, the command should be removed with it.

## What it is

Reads the knowledge and the code, proposes what neither says, and writes a list the owner decides on
in one round. **It changes no code and no tests, and decides nothing about the product** — what it
writes is its own list, plus, for the rows the owner accepted in front of it, what they answered:
an entry, a stance, or a line in the ledger. Nothing it writes is its own opinion of what the product
should be.

Three lenses, and the invocation copies `audit` exactly so nothing new has to be learned:

| You type | What happens |
|---|---|
| `advise` | every lens, `product` first |
| `advise product` | one lens |
| `advise product checkout` | one lens, narrowed to an area |
| `advise "why does signup feel so long"` | free text: say in one line what was understood, then start |

The best moment to run it is **right after `blueprint`, before `mvp`** — the description is fresh,
nothing is built, and changing it is free. The second is after a sprint, when the product is real
enough to be judged.

It needs the knowledge. The close half of `product` reads `scenarios.md` and `actions.md`; the wide
half needs `product.md` and `actors.md` at minimum. What is missing is named in the report and not
compensated for by invention.

## Every lens has two halves, and each row says which one it came from

The close half walks the files and finds what they contradict or omit. The wide half steps away from
the files and proposes what is not in them at all.

Both are wanted, and mixing them silently destroys both: a list where half the rows carry evidence
and half carry judgement is read at the weaker standard throughout. So **every row is tagged with
its origin — `from the files`, `from the domain`, `from research`** — and the owner always knows
which of the three they are reading.

The completeness rule differs by half, and the difference is stated in the report:

- **The close half's walk is complete.** Every scenario and every action gets a row: a proposal,
  `clean`, or `unjudged` with the reason. No cap — a walk that truncates itself is lying about
  coverage.
- **The wide half's walk is its own reading of the domain**, and what it raises passed a bar. So it
  ends with a mandatory *considered and rejected* section. Without it a list of five proposals is
  indistinguishable from one that stopped looking after five.

## Lens: product

**Close half.** Reference: the scenarios and the actions. Walk: each scenario end to end, then each
action. Three questions, and only three, or the half drifts into "it would also be nice if":

1. What is missing for the scenario to finish without *and then the user emails support*.
2. What exists that no scenario touches — a candidate for removal, not for improvement.
3. Which step a real person abandons at: how many fields, how many waits, how many decisions.

```
scenario 4 "the buyer returns an item"
  breaks at     step 3 — the request reaches a manager and no action answers it
  proposal      action manager.answer_return_request
  touches       actors: manager (exists) · entities: return_request (missing)
  cost          a new entity plus an admin screen
  without it    the buyer waits in silence; the scenario never finishes
```

**Wide half.** Before a single proposal, **write the reading of the domain into the report**: who
this is really for, what they are really buying, what they do *instead* today — how they solve this
without the product — where their time and money go, who else is standing next to them.

This is not decoration, and the kit already uses the pattern: the performance lens writes its
anti-pattern catalogue into the report before using it, because otherwise the scope of the check is
invisible. Here it does something more — proposals are judged against a stated understanding instead
of the understanding being reverse-engineered from the proposals afterwards.

Then four questions:

- What an audience like this expects from a product like this, and does not find here.
- **Who is standing next to it and is not served** — an adjacent kind of person the machine already
  almost fits. This is frequently one field and one screen.
- What would make it noticeably pleasant where it currently merely works.
- **Who should stop being served.** Narrowing the audience is sometimes the win, and it is the one
  proposal nobody volunteers.

Its discipline, which replaces the file citation the close half has: every proposal names **who
exactly** (a group from the reading above), **what those people do instead today**, and **what
changes for them**. *"Add a referral programme"* does not survive those three lines. *"Sellers copy
their catalogue into Telegram by hand — a one-file import gives them an evening back"* survives, and
can be checked by asking one seller.

**The report opens with "small edits, disproportionate effect"** — cheap to build, large in effect.
That section is what the command is for; everything below it the owner can postpone.

## Lens: code

**Close half.** Reference: `stack.md`, the volumes stated in `product.md`, the ecosystem's standard
answers. Walk: every action that reads or writes at volume, and every homegrown mechanism. Two rules
carry it:

- **A proposal without a number is not a proposal.** Where it is now (file and line), at what volume
  it stops holding, and where that number came from. No number available means an `unjudged` row
  carrying the question for the owner — which is how the lens comes to ask *how many listings do you
  expect in a year* instead of guessing.
- **Always name the intermediate step** — the cheapest thing that buys time. This is what kills the
  reflex to reach for a search cluster.

```
seller.search_offers
  today         LIKE over offers.title, Offer.php:88 — no index
  breaks at     ~50 000 rows, or above 2 searches per second
  number from   product.md: "up to 1000 sellers", 50 listings each
  cheaper       a postgres full-text index — an hour's work, no new infrastructure
  dearer        a separate search engine — a service, a sync, a new failure mode
  when          when the first one stops holding
```

On a project with no code yet the close half still runs, against the approach `stack.md` describes
rather than against a file and a line. The citation changes; the number rule does not.

**Boundaries with two audit lenses, neither of them overlap.** `performance` finds code that is slow
now, for a reason visible in the code; this lens finds an approach that will not survive a volume
that does not exist yet. `conventions` checks the code against the rules the owner wrote in
`stack.md`; this lens questions those rules. Where the two disagree, `conventions` is describing what
is, and only the owner may change what should be — so a proposal here never makes a `conventions`
finding wrong, it proposes a different rule to hold the code to.

**Wide half.** Three developer questions:

- **Simpler.** Where something homegrown has a standard answer, where one idea is smeared across the
  code. The bar: name **the class of work or bugs that disappears**, never "it would be cleaner".
  Statuses as strings everywhere → one enumeration and the transitions in one place; the class
  *"nobody handled the new status"* stops existing.
- **More reliable.** Where the product loses data or lies quietly: a background job that failed and
  nobody heard, a retried payment that creates a second record, an action with no way back, no trace
  of who did what. None of the six audit lenses asks this.
- **Faster — for the user, and for the developer.** The second matters more and nobody measures it:
  how long the suite runs, how long the environment takes to come up, how many steps sit between
  *understood what to change* and *saw the result*. A slow feedback loop costs more than any query.

Its discipline: **every structural proposal carries an incremental migration path** — how to get
there without stopping work. A proposal with no such path is a rewrite and is labelled one, plainly.
Writing *"move to a different architecture"* takes a second and reading it takes an hour.

## Lens: money

**Reference: how the product earns and what it costs to run** — and on most projects the knowledge
records neither. That is the lens's first act, not a reason to skip it: say plainly that `product.md`
names no revenue model and no running costs, ask for them, and run the half that does not need them.
A lens that quietly invents a price list is worse than one that says what it could not read.

**Close half.** Walk: every action and integration that costs money to serve. What is given away
that costs per use — an outbound call, storage, a paid API behind a free path; where a limit that
exists in the plan is not enforced in the code; which action calls a metered integration without a
bound; what the audience clearly values and there is no way to charge for. Same rule as `code`: **a
proposal without an amount or a rate is not a proposal.**

```
guest.preview_report
  costs         one call to the metered PDF service, ~$0.004, no cache, no rate limit
  reachable by  anonymous visitors, Report.php:64
  today         nothing bounds it; the plan says 20 a month, nothing enforces 20
  proposal      enforce the plan's limit, cache by document hash
  worth         at 1000 previews a day the free path alone is ~$120 a month
```

**Wide half.** How products in this space charge and what this audience is used to paying for; the
cheapest thing here that someone would pay for today; which running cost will dominate at the volumes
`product.md` states; what could be dropped to cut the bill without anyone noticing.

**Boundary with the wide half of `product`**, which is close but not the same question: `product`
asks who else would *use* it, `money` asks who would *pay* and for what. A row that answers both is
raised once, under `money`, with the other lens named.

## Research comes after the reading of the domain, never before

Search first and the reading of the domain becomes a summary of the first page of results. Write the
reading first and the search can be checked against it — and **a disagreement is itself a finding**:
*I took this to be for small sellers, and the market moved to agencies this year.*

One delegated pass per lens, briefed from that reading — exactly what `blueprint` already does with
the stack: *one bounded research pass, delegate it, it comes back as a proposal and never as a
written record.* Delegation is not decoration here: search debris must not settle into the run's
context, which is the same reason the audit gives each lens its own subagent.

**What is searched.** For `product`: how this job is done today without you — the live products in
the space; what people dislike about products like these, in reviews and forums, where finished
proposals are lying around; what changed in the space this year; regulation and seasonality where
they apply. For `code`: current majors and what they now recommend, the known traps of the chosen
approach, what the ecosystem treats as the standard answer to the homegrown piece. For `money`: what
products in this space charge and how they package it, and the current published prices of the
services this one runs on. This does not duplicate `blueprint` — that pass ran once, at interview
time, before there was any code.

**A research row carries a link and a date.** The cheapest path to a plausible research finding is
recalling one: *competitors usually do it this way.* It reads as research, is not, and is a year
stale. A link with a date cannot be produced that way, so the path stops being available rather than
being discouraged. It also repairs the declines: a refusal that carries a link and a date can be
rechecked later; a refusal resting on somebody's memory cannot.

**And if there is no network, or the search found nothing, the report says so and marks those rows
unresearched.** It does not fill the space with general knowledge. The kit has paid for this rule
three times — `--offline` blinded `next` to pull requests while staying as quiet as a clean run.
Silence must mean *nothing was found* and nothing else.

## Four lists a proposal is checked against before it is raised

The fastest way to make a command nobody runs twice is to propose work the owner has already decided
on. Three of these lists `check.py` already prints on every run, so the filter costs nothing:

- **what is `planned`** — described in the knowledge and not built yet. Proposing it is proposing
  what already exists on paper.
- **the open boxes in `docs/audits/*`** — already found, already sized into `ship` runs.
- **`docs/technical_debt.md`** — already decided against, by a run, with its reasoning in a pull
  request.
- **the previous `docs/advice/<lens>.md`** — refused once already.

Where a proposal genuinely restates one of these, it is not raised as a proposal. It may be raised
once as a **priority remark** — *this is already planned and it is the thing standing between you and
the adjacent audience* — which is a different claim and is marked as one.

**And the fifth list is the sharpest: "what it deliberately does not do", in `product.md`.**

That section is the most valuable target the wide half has, and the most dangerous. Blueprint records
it because an autonomous run needs to know where to stop, and it is worth more to a run than the list
of what the product *is*. A lens that cheerfully proposes what the owner already ruled out is
worthless twice over: it wastes the round, and it makes the exclusion look unread.

So: **read that section first, and a proposal that reopens an exclusion must quote the recorded
reason and say what changed since.** A changed number, a changed market, a capability that did not
exist when the line was written. No answer to *what changed* means the exclusion stands and the
proposal is not raised. With an answer it becomes the single most valuable row in the report,
because reopening a deliberate decision is the one thing the owner will never do unprompted.

## The cheap paths, named before the first run

Per [method.md](method.md), it is cheaper to close these before a run than after four:

| Cheap path | Artefact it cannot produce |
|---|---|
| a generic feature list — notifications, referrals, gamification | the scenario step number, in the project's own names, or the three lines of *who / what they do instead / what changes* |
| an ecosystem name-drop — put a search engine on it | the volume at which today's approach stops holding, and where that number came from |
| research recalled from memory | a link with a date |
| "it would be cleaner" | the class of bugs or work that disappears |
| a rewrite dressed as a proposal | an incremental migration path |
| raising five proposals and calling it a survey | the *considered and rejected* section, and a complete walk in the close half |
| plausible confidence about a domain the model barely knows | the two closing lines below |

The wide half closes with **what I know about this domain and where from**, and **three questions
whose answers would change this list**. Model knowledge of a marketplace or a booking service is
good; of niche B2B logistics it is nearly absent, and there it will invent fluently. Those two lines
are what let the owner tell experience from polite fiction, and they are the same rule every report
in this kit already follows — say what the command cannot see.

## Closing: three answers, each with one home

The owner goes through the rows in one round at the end of the run, following `rules/asking.md` —
options, recommendation first, everything independent in one batch. A list left in a file for nobody
is not the product of this command: the whole value of the product lens is the owner saying *that one
we deliberately do not do, and that one I forgot*.

Three answers are possible, and each has exactly one home.

### Accepted, and it changes what the product is or what the code is held to

**The entry is written there and then, in the same round, complete.** Not a marker for a later
session — the owner is sitting there, they have just decided, and this is the cheapest moment the
fields will ever be answerable. An hour later both sides are reconstructing why.

This is the kit's own rule rather than an exception to it. Blueprint's fence is *deciding*, not
*writing*: **"that same command, or the next one, writes the owner's answer into the entry and
deletes the block while they are sitting there."** The prohibition on a build command touching
knowledge is about runs with nobody in the room — `ship` may not rewrite prose because `ship` runs
at midnight. Here the owner is the one answering.

The shape is not carried in this command either. It lives in
`templates/knowledge/<slot>.md`, read by whoever writes a record, once — which is the whole point of
having templates. `advise` reads the template for the slot it is writing, exactly as `blueprint`
does, and writes `state: planned`.

And the interview is small, because the proposal already did most of it. A `product` row names the
actor, which entities exist and which are missing, what changes and what happens without it — that
is most of an action entry. What is left is confirming the derived fields and asking the two or three
that cannot be derived. This is not a brainstorm; it is finishing a form that is already three
quarters filled.

**The rule that stops it inventing, and it is all-or-nothing per item:** every field is either the
owner's own words from this round, or derived and put in front of them for correction in this round.
**A field with no answer means the item does not become an entry at all — it becomes a block.** There
is no such thing here as a mostly-written entry, because a run is careful around a gap and confident
around an invented answer, and an invented field is indistinguishable from an answered one once the
session is closed.

The backstop is a program, not this paragraph: `check.py` already verifies that every record has the
`fields:` its file declares, each with content. Run it after writing, and a malformed entry is caught
in seconds by the thing that already knows the rule.

**The block is the fallback, not the path.** `[accepted …]` is written in exactly three cases: the
owner says yes but wants to settle the details later; they tire partway through a long round; or
nobody is in the room at all. It is the fourth kind in the rail the kit already has — three block
kinds (`[assumed …]`, `[found …]`, `[stale …]`), all written by runs, all counted by `check.py` and
printed before every command, all resolvable only by `blueprint`, all closed by deletion. Writer
`advise`, reader `check.py`, resolver `blueprint`.

It is not `[assumed …]` under another name. That block means *a run guessed and the owner may
disagree*, and blueprint resolves it by asking whether it was right. This one means *the owner
already said yes and the fields are outstanding*, and blueprint resolves it by finishing the
interview. Collapsing them would have blueprint re-ask a question answered last week, and re-asked
questions are how a list stops being read.

Entries and blocks are committed the way blueprint commits them: onto the branch that is checked out,
one commit per slot, as each is settled. A round that dies costs one item.

### Is an entry written here as good as one written by `blueprint`

`ship`, `sprint` and `mvp` read entries, not the command that produced them, so the question is
entirely about the entry — and most of it answers mechanically. An action declares nine fields and
its template states the bar: *every key it names — actor, entity, status, screen — exists in its own
file.* `check.py` checks both, every field for content and every key for a target. An entry that
passes is indistinguishable in every way that matters from one blueprint wrote, because nothing
downstream can see anything else.

Two things do not answer mechanically, and both would fail silently.

**A new entry can pull three slots with it.** An action naming an entity that does not exist yet
needs that entity first — states, transitions, invariants — and possibly a screen and an actor. That
cascade is why blueprint's interview runs in the order it does, each slot feeding the next. So the
round follows the same order for what it writes, and the same all-or-nothing rule applies one level
up: **anything the owner is not willing to settle right now makes the whole item a block, not a
partly-written cascade.** The proposal row already names what it touches — *entities:
`return_request` (missing)* — so the size is known before the first question, and it is said out loud
before the round starts.

**And the feature has to reach a scenario, or `mvp` will never prove it.** This is the one real hole
and it is invisible until much later. `mvp` stops on *every scenario inside the bounds passes against
the running application*, and each scenario is bound to an end-to-end test carrying
`agent-kit:scenario <key>`. An entry that appears in no scenario is built, marked `built`, and never
proved by anything — the scenarios lens does not know to look for it, and `mvp`'s finish criterion
steps straight over it.

So an accepted product proposal ends its round in one of exactly two states: **attached to a
scenario** — an existing one gains a step in the owner's own words, or a new scenario is written —
**or explicitly outside the MVP bounds**, which is the other question that must be asked, because
`mvp` reads those bounds to know when to stop and a new entry silently widens or does not widen them.

Two questions, both cheap, both asked in the same round. Without them the entry is fine and the
project is not: `ship` builds it correctly, and nothing ever checks that it works.

### Accepted, and it is work under rules that already hold

**A line in `docs/technical_debt.md`**, in that file's existing four-field format, and nothing new
anywhere. Most of what `code` and `money` produce is this: replace the homegrown thing, enforce the
limit the plan already states, cache the metered call. No rule changes, so there is nothing for
`blueprint` to write — it is work somebody has to do.

That ledger is already exactly this: work decided on and not done, read before every command,
rankable by `next`, closed by deletion in the commit that does it. Routing here costs zero mechanisms
and buys a consumer immediately.

**The split between the two is the question "does this change a rule, or follow one?"** A stance —
money in minor units, every outbound call idempotent — is knowledge and goes to a block. Applying
that stance in eleven places is work and goes to the ledger.

### Declined, or not now

**A line in `docs/advice/<lens>.md`, and never a block.** A block is a promise to change something
and here there is nothing to change. The line has one reader — the next run of this lens, which must
not raise it again. It carries the proposal, the reason and the date.

*Not now* is the third answer and it is not a decline: the row simply stays open in the file, and the
next run carries it forward rather than presenting it as new. Without this it comes back next month
looking like a fresh idea, and the owner refuses it a second time — which is exactly the failure the
declined list exists to prevent, one square over.

**And the lenses decline differently.** A product refusal is permanent. A `code` or `money` refusal
holds until a condition: *no sharding needed, we have 400 rows* stops being true at 400 000, and
*not worth charging for* changes with the bill. So those refusals record the number they rested on,
and the next run's first act is to check whether the number moved. That is cheap, and it is what
keeps a dead list alive.

### What the file holds afterwards

Open rows and declined rows. **An accepted row leaves the file** the moment its entry, its block or
its ledger line is written — from then on the fact lives in the knowledge or in the ledger, and two
homes for one fact is the thing this kit keeps paying for. Git holds what was here; the audits' ticked boxes
are a different rule for a different reason, because that list is consumed by `sprint` and has to
show what is already done.

### No owner in the room, nothing is written but the list

If this command is ever run unattended, it writes its list and stops: nothing is accepted, no entry,
no block and no ledger line. The closing line says the round is outstanding. Acceptance is a decision
about what the product must do, and blueprint's rule is that only the owner makes it — a run that
wrote an entry on its own judgement would be the exact violation that rule exists to prevent,
arriving inside the mechanism built to respect it, and it would arrive as a fully-shaped entry that
reads exactly like an answered one. This is the one place in the design where the failure would be
silent, so it is fenced explicitly rather than left to follow from the closing round being
interactive.

## What has to be built

- `skills/advise/SKILL.md` — invocation, the two halves, the origin tags, the closing round, and the
  two questions above. It carries the act of writing, never a second copy of the shape.
- `rules/knowledge-writing.md` — **extracted from `blueprint`, not written twice.** The handful of
  rules that are not the shape of a record and not the interview: the project's language and how a
  template's headings are translated, a commit per slot onto the checked-out branch, `state: planned`
  on a new entry, `--record` for any `source:`, and the check run afterwards. Two commands now write
  knowledge, and the kit's own rule is that anything two commands need lives in `rules/` — if it is
  in two `SKILL.md` files it is already wrong. `blueprint` loses those lines and points at the file.
- `skills/advise/references/product.md`, `references/code.md`, `references/money.md` — one per lens, only the one being
  run is read.
- `check.py` learns the fourth block kind: one word in `NOTE_RE` (`check.py:48`) plus its own line in
  the report, counted and listed in `--status` beside the other three. Like `[stale …]` and unlike
  the other two it is not a question to the owner, so it does not change the exit code.
- `blueprint` learns one row in its notes table: `[accepted …]` → finish the interview, write the
  entry, delete the block.
- Both READMEs, since `validate.sh` checks that they match the commands that ship.

**That is one new mechanism**, against the ceiling in [2026-08-05-audit.md](2026-08-05-audit.md), and
it is the fallback path rather than the main one. Everything else routes into files that already
exist and already have readers: the knowledge, the ledger, `check.py`'s existing report and its
existing field check.

Two alternatives were rejected on the way. **Putting accepted product ideas in the ledger too** —
a ledger line can be closed by anyone who does the work, so `ship` would pick up a feature with no
entry behind it, which is the failure the knowledge layer exists to prevent. And **making the block
the main path, with `blueprint` writing every entry afterwards** — it costs the owner a second
session per accepted idea, at the moment when the context that makes the fields answerable has
already evaporated, and it leaves a record whose closer is a command somebody has to remember to
run. Records nobody was allowed to close cost this kit a release; records nobody remembers to close
are the same defect wearing a different hat.

## Cost, and what the shape guarantees

Measured comparators: `blueprint` on a real project runs 2.0–5.6M, a subagent's floor is 0.3–0.7M,
a full six-lens audit sweep cost 21.4M. A single `advise` lens should land at **3–6M** — the close
walk is bounded by the scenario and action lists, the wide half is one pass plus one delegated
search, and neither reads the codebase. It balloons from the same three things audit forbids: agents
per area, verification passes, and reading the code instead of walking a list.

**Guaranteed: the close half is complete against the description**, countable by the owner rather
than claimed by the run.

**Not guaranteed: anything at all about the wide half.** It is judgement, it is tagged as judgement,
and its quality moves with how well the domain is known — which is exactly why it must state that
and name the three questions that would change it.

**Not attempted: priority.** This command does not decide what gets built next. `next` ranks, the
owner chooses, and an advice list that started ordering the work would be the roadmap machinery
kit-v1 refused, arriving through the back door.

## First version

`product` and `code`, one live run each on a real project, per [method.md](method.md) — a command
that has never run is a hypothesis. `product` first, because the wide half's discipline is the part
most likely to be wrong, and it is better to learn that on the lens whose value is easiest to judge.
`money` ships in the same command and is run third, after the closing rail has been exercised twice:
it is the lens most likely to find that the knowledge it needs was never written down, and that is a
better thing to discover with the rest already working.

The measurement that matters is not cost. It is what the owner does with the list: how many rows
were accepted, how many refused, and how many were neither — read, shrugged at, and left. A third
column that fills up means the bar is too low, and the bar is the whole command.

## Names

The second lens is `code`, not `stack`. `stack` collides with the knowledge slot `stack.md`, so
`advise stack` would read as *advise about that file*, and it understates a lens whose wide half is
about how the code is built, how it fails and how fast it is to change — none of which is a choice of
framework.

`money` is the third, and it is deliberately the plain word rather than *pricing* or *unit economics*:
it covers both halves of the question, what comes in and what goes out, and the kit's rule is that
one thing is always called the same thing.
