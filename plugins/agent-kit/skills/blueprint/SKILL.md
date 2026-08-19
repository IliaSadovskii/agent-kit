---
name: blueprint
description: The project's knowledge layer — the owner says whatever they came to say about their product and this writes it into the documentation the other commands build from: application type and stack, actors, entities, actions, screens, integrations, scenarios, MVP bounds. It reads what is already recorded on what they touched, shows the comparison before writing, and asks only about what is still missing. Run with nothing and it says where the description is thin.
argument-hint: "[whatever you want to say about the product] [--recall [part]] [--check]"
disable-model-invocation: true
---

# Blueprint

Everything the project knows about itself, in one place, written before anything is built.
`fix`, `ship`, `sprint` and `epic` read it and never write prose into it. `advise` writes what the
owner answered in front of it, and nothing else — see
`${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md`, which is the half both of you share.

**One decider, one trigger.** Only blueprint decides what an entry *requires*, and only the owner
starts blueprint. Rules the build follows must not change under a run.

Everything else may record, or transcribe — never decide. A build command leaves a block where it
had to assume something or where its feature outdated a sentence; that same command, or the next
one, writes the owner's answer into the entry and deletes the block while they are sitting there;
the session closing a batch applies a block that already states both halves. None of them settles
anything, and each change rides in a pull request the owner reads. What none of them may do is
change what the product must do — that is the sentence this rule exists for.

That is also the whole difference between you and `advise`: it may transcribe a decision the owner
made in front of it, and it may not make one. What an entry *requires* — its fields, its bar, what
counts as settled — stays here.

## How it is invoked

| Invocation | What it does |
|---|---|
| `blueprint`, with or without words after it | **the one door.** The owner says something about their product — an idea, one part in detail, the whole thing again, a list of what did not match after using it — or says nothing, and then you ask. Everything after this table is that. |
| `blueprint --recall [part]` | tells the owner what the project already says, in their language and out loud, so they never open a file to find out. Changes nothing until they ask for a change — `${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/doors.md` |
| `blueprint --check` | audits, mechanically, in seconds, asking nothing. Run the program — `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --sync` — and put its output in front of the owner with a sentence about what to do next. `--sync` moves an entry whose pull request has merged — the one thing this program writes, and never as a preflight, which would leave the tree dirty under the command that ran it. `next` and `accept` may run it too, under the same fence; a build command may not. Two audiences: as another command's preflight it is run bare and prints nothing when clean; **by hand it always prints where the project stands**. That is the raw view of the knowledge; `/agent-kit:next` is the same data ranked into a recommendation. |

Every question you put to the owner follows `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`: options
rather than prose, the recommendation first, and everything independent in one round — and its one
exception is the step below where the owner is doing the talking.

## The five steps

**Every run is these five, whatever was typed and however much of the project exists.** An empty
repository has an empty step 2 and a long step 5; a mature one is the reverse; a dictation about one
part narrows both to that part. There is no other route through this command and no phase to
announce — what differs between runs is how much of each step there is, not which of them happen.

Before any of it, the program, always — not optional and not conditional. Left to be inferred it is
skipped, and a build command once told to "run `blueprint --check`" went looking for an executable of
that name, found none and carried on in silence:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
```

### 1. The owner talks

They came with something to say. Let them say it: an idea, one part in detail, the whole product
again, a list of what did not match after using it — **any length, any order, and not sorted for
you**. This is the one place in the kit where an open question is the right instrument and choices
are the wrong one, because options can only be written out of what you have already read.

Typed with words after the command, that is the telling and it has already happened. Typed bare, ask
for it — and say in the same breath what the check just told you, so they can take that instead:

> Seventy assumptions across twenty-three entries, six parts of nine never walked. Tell me whatever
> you came to tell me — an idea, one part in detail, what did not match when you used it — or say
> *the list* and we work through that.

Never a menu of modes. One sentence, and the microphone is open by default.

**With no `docs/knowledge/` at all**, this is the first interview: there is nothing to dictate
against, so you ask — what is this, for whom, how does it work — and follow up until you can restate
it. On a repository that already has code, read the code first and bring your reading to be
corrected, spending their attention only on what code cannot say.

### 2. Read what is written on what they touched

Not the whole knowledge every time: the entries, slots and parts their telling actually reaches.
A sentence about notifications does not need the sign-in read.

But **a telling that covers the whole product does mean reading the whole thing**, and that is the
cost of the thing being asked for — a description can only be kept current against the previous
version of itself. Do not skim it and do not sample it.

### 3. Put your reading up before you write anything

One screen, and it is the most important thing you produce:

| | |
|---|---|
| **new** | nothing recorded covers this |
| **refines** | recorded and this adds to it — name the entry |
| **contradicts** | recorded and this says otherwise — name the entry, quote both, **and this one is asked** |
| **unchanged** | you read it, they touched on it, nothing moves |

The last row is not padding and may not be dropped. Comparing a telling against fifty entries means
reading fifty entries, and the cheap way to look thorough is to read a third, find something and
report it confidently — *"three differences"* is what an honest pass and a lazy one both say. A line
per record touched, including the ones that did not move, is what a third of the reading cannot
produce.

Only contradictions are asked here, as choices, before anything is written. Everything else is
stated and written.

**A contradiction the owner found by using the product is the kit's own fork**, and it is the same
one a build hits: the description is wrong and you rewrite the prose — which nothing else may — or
the product is wrong, and that is not yours. Your reading first, their decision.
`${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/doors.md` has the table.

### What is not a change to the description

Most of what an owner brings back from using their product is not. *The button is in the second
menu and should be on the first screen* is — that is what a person sees and in what order, and it
belongs in the entry. *The spacing is wrong*, *these two buttons next to each other confuse people*,
*this crashes when the network drops* are not: the description is right and the build is not.

**Those go in `docs/technical_debt.md`, one line each, and you are the one who writes them.** Not
into the knowledge — an entry that carries a padding complaint stops being something a build can be
held to — and not into the conversation, where they die when the session closes. The ledger is
already read by `check.py` before every command, offered by `sprint` with no theme, and taken by
`epic` as work the project owes. Copy `${CLAUDE_PLUGIN_ROOT}/templates/technical_debt.md` if the
project has none yet; the format, and the field that says a line came from the owner rather than
from a run, are in its header.

Three destinations and one test between them:

| What they said | Where it goes |
|---|---|
| this changes what the product must do | the entry — yours to write |
| it does what it should and does it badly | a ledger line |
| it does not work at all | a ledger line, saying so — `fix` takes it, or the next batch does |

Say the count back when you are done — *"four went into the description, nine into the ledger"* —
because the second number is the one they cannot see anywhere else, and a complaint that reached
neither place is the thing this step exists to prevent.

### 4. Write it

Into whatever slots it touches, committed as it is settled, per
`${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md`. Then put the result up as a list of names to
correct, not as prose: *"from the lesson I got one screen, five actions and one entity"*.

### 5. Then the gaps, and only then

What is missing, asked as choices — and **the order is the cost of leaving it, not the order of the
files**:

1. **What stops `epic`** — the MVP bounds, the scenarios and their endings. Its gate refuses to
   start without them.
2. **What is expensive to get wrong** — stored shapes, permissions, money, a contract outside this
   codebase.
3. **Everything else you do not ask.** Take it, record it as an assumption, and show the lot in one
   list at the end: *here is what I decided for you*. This tier is the whole difference between a
   command that clarifies and one that interrogates — and padding a round with decisions you could
   have taken yourself is what teaches an owner to tap without reading.

Two kinds of gap, found by two different things, and only the second is yours:

- **a field that is not there** — the check already printed it: a slot with no verdict, empty
  fields, a stale `source:`, `Parts: 6 recorded, 4 walked, 2 derived`, or no parts recorded at all
  on a project written before the kit asked. Nothing to go looking for;
- **a field that is filled and says nothing** — only a session sees this, and it is held to the
  filter in *What to ask about, and what never*, below.

When the check found nothing and the owner brought nothing, **say so in one line and stop**, naming
what to run instead — usually `/agent-kit:next`, or `/agent-kit:epic` when entries are still
`planned`. An interview invented to fill the silence is the one thing an owner cannot check.

## What this command does not do

It writes knowledge. It does not build anything, start or instrument the application, write scripts,
install dependencies, produce quality or audit reports, or decide what gets worked on first — those
belong to `fix`, `ship`, `sprint`, `epic`, or to a plain conversation with the owner.

The pull is strongest when the owner voices a doubt: *is this ready?*, *does the admin area work?*
Answer it from the knowledge and the code, name what you cannot answer from those, and offer the
command that would. A three-hour audit started from a question is still not this command's job, and
the owner asked for documentation.

Gaps you do report are gaps **in the knowledge** — a screen nothing leads to, an entity nothing
creates, an actor with no actions. Those are cross-checks and cost nothing. Defects in the product
and in the code are somebody else's.

## Where it writes

`docs/knowledge/`, one file per slot, and `.agent-kit/project.yml` from
`${CLAUDE_PLUGIN_ROOT}/templates/project.yml`: the language, the project's commands, the verdict per
slot.

**And one block in the project's own `CLAUDE.md`** — a map naming where the knowledge lives, from
`${CLAUDE_PLUGIN_ROOT}/templates/where-things-are.md`, written between its markers and nowhere else
in that file. It is the only thing this kit writes there, and the reason is narrow: every command
here finds the knowledge by path, so none of them needs a map — what needs one is everything that is
**not** a command, a plain conversation in that directory, an outside agent, a person handed the
repository. Claude Code loads that file into every such session for free, which makes it the one
place a map is read without anybody deciding to. Measured across three live projects on this kit, one
had such a section — written by the owner's own hand — and two had nothing. Refresh it when the
layout changes; the check says when it is missing. The verdicts are yours alone; the rest of how a record is written —
templates, the project's language, `state: planned`, the commit per slot, hashes, the check
afterwards — is `${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md`, which `advise` follows too.

## What a finished description holds

**Six things, and this is a list of what must exist — not a route to walk.** Step 5 asks about
whichever of them the project is missing; a telling may fill three of them at once and leave the
order to the owner. Only an empty repository walks it top to bottom, and it does so because the
early items are the vocabulary the later ones are answered in, not because the list is a procedure.

**It is shaped by the product's own parts, not by the slots.** Nobody holds their product as actors,
entities and screens — they hold it as the things it does: sign-in, the lesson, the notifications,
the account. Walking the slots asks the owner to translate into a structure that is the kit's
convenience, and what does not survive that translation is what a run has to invent later. So the
questions follow the parts, and the slots are what the answers are written into: one part's telling
usually fills a screen, several actions and an entity at once.

1. **The telling.** What this is, for whom, how it works. Not a form — follow up until you can
   restate it. On a repository with real code, read the code first and bring your reading to be
   corrected, spending the owner's attention only on what code cannot say: intent, what is
   deliberately out of scope, what is coming. Store it near-verbatim as the first section of
   `product.md`.

2. **The parts, agreed as a list.** Split the telling into the product's parts and put them up as
   names to pick from, never as prose to read back.

   **What decides a part is its size, not a count.** A part is something the owner can tell a story
   about in a few minutes and that has a vocabulary of its own. Five to ten is what that usually
   comes to and is worth saying out loud as an expectation — a narrow tool honestly has one or two,
   a large product has more than ten, and forcing either into a number invents parts or hides them.
   Where the count surprises you, check the split rather than the product: many small ones usually
   means you cut by screens instead of by meaning.

   A list long enough that the interview will not fit one sitting gets **committed first**, and then
   goes one part per sitting — the resume point is a part, not a slot.

   **Order them by what the product is for**, not alphabetically: attention is freshest first, and
   later parts borrow the vocabulary the early ones settle.

   They are recorded in `product.md` and carried on each entry, because a part nobody wrote down is
   invisible to the next session — and to `epic`, which reports at its gate which parts the owner
   walked and which were only derived.

   **Each part carries its mark, and the mark is English wherever the file is written**:
   `walked: <date>` when the owner told you this part, `derived` when it came out of the code and
   documents and they have not confirmed it. The names beside them are theirs; the mark is what the
   check counts, the same way `key:` and `state:` stay English inside translated prose.

3. **Application type and stack.** Versions from the manifests, per-area decisions from the code.
   Then one bounded research pass — delegate it — on what this framework's current major
   recommends and which packages this ecosystem treats as the standard answer. It comes back as a
   proposal, never as a written record: *here is what I found, what is wrong and what is missing?*
   On an empty repository the owner says what patterns and infrastructure they want, in free form,
   and research fills in around it.
   Settle `tests.unmet` in `project.yml` here, while the runner is in front of you: what keeps a
   test off the red in this project, for the day a test has to prove a promise the product does not
   keep. The template says what to look for, and a project with several suites gets a line each.
   Leaving it blank costs a build command an invented answer at midnight.

   **And `commands.mutate`, in the same breath**, because it is the same research: whether this
   ecosystem has an off-the-shelf way to change the product's logic in small valid ways and count
   what the suite noticed. The template names one per ecosystem. It is worth proposing rather than
   asking about — the owner is unlikely to have one already, and every run after this is otherwise
   taking its own word for it that a test can fail. Bound it to the changed files, and leave it
   empty where nothing fits: a run then says the step did not happen, which is honest, where a
   whole-project command that takes an hour is a step every night quietly skips.

   **Then walk `${CLAUDE_PLUGIN_ROOT}/verification.yml` with the owner, top to bottom.** It lists
   every kind of verification this kit knows about — what each one catches, which session runs it,
   and the shape of project it does not apply to. The list is the kit's; the answers are this
   project's, and they go into `project.yml` → `verification`, one line per kind:

   ```yaml
   verification:
     visual: npx playwright test --grep @visual
     contract: no 2026-08-19 — calls nothing outside itself and publishes no API
   ```

   **An answer is a command or a dated refusal, and never a word.** `yes` is a claim no program can
   test, and this kit has already paid for one of those — a child met a declared suite that would
   not start, at three in the morning. A command is checked for starting, like every other command
   in that file. A refusal carries the date because *there is no front end* stops being true the
   week there is one, and the check asks again after six months or as soon as a dependency manifest
   moves.

   **Judge from the repository, never from `stack.md`.** Measured on three live projects: one slot
   said mutation testing was not installed while the plugin was a hard dependency of the test runner
   and the config had already been tuned for it; another carried two hundred lines of Playwright
   walking every screen in two viewports and asserting nothing, named in no document. Read the
   dependency manifests, the test directories, the CI workflows, the scripts. **The cheapest finding
   on two live projects was an instrument installed, configured and never declared** — one line
   here, and every run afterwards starts using it.

   Per kind, propose rather than ask: what is already here, what it would take, and your
   recommendation. Where the kind is missing, say what it would cost and what it would catch, and
   say plainly where it is expensive — static analysis dropped on a mature codebase reports hundreds
   of findings on untouched code, visual baselines over a page that waits on a live model flake from
   the first day, holding a paid API to its contract needs a key in CI and money per run. **What is
   offered is the decision, never the work**: standing an instrument up is a task of its own —
   `docs/technical_debt.md` when the owner defers it, a named task when they want it now — at most
   one at a time, cheapest first. An interview that turned into an installation is an interview
   nobody finishes.

   Then write `checks.verification_reviewed` with today's date.

   **And ask what runs the scenarios end to end** — the one testing question a draft cannot answer.
   Everything else in the testing section is derived: the layers, the seams, the bar all come from
   the code and the manifests. A harness that does not exist yet is invisible to that, so silence
   here is read by every later run as a decision nobody made — and `epic` stops on *every scenario
   passes*, so it is the one gap that decides whether that command can finish at all. Name the tool
   and where it runs, or write plainly that there is none and the scenarios are proved by hand. Both
   are legitimate; neither may be left to be inferred.

   **The answer goes into `commands.e2e`**, not only into the prose. That field is what the gate of
   an `epic` reads to say whether this run's finish line can be reached mechanically, what a batch
   runs over its own chain, and what the guard hook keeps out of a feature's session — a command
   only a paragraph names is a command no program can act on. Empty is a real answer and is said as
   one.
4. **Each part, told by the owner.** One part is one telling, and it goes through the five steps
   like anything else: they talk, you read what is recorded about that part, you put the comparison
   up, you write, then you ask what is still open. A part is finished when you can write its records
   without inventing a **product** answer — the mechanics you may still decide yourself.

   Two things are worth knowing before you open one.

   **Ask for it in their own words back at them.** Not *"tell me about the lesson"* but *"you said a
   lesson is a conversation with the model — take me through one, start to finish"*. Their
   vocabulary is what makes the question answerable.

   **Where the part is already built and the owner has used it, ask for the difference instead.**
   They cannot describe it as an intention — they have clicked it. *"You have used this — what did
   not match?"*, in any order, nothing sorted. Each point is then the fork in step 3: the prose is
   wrong and you rewrite it, or the product is wrong and it is not yours. A part whose entries are
   `built` is in this case, and on any project older than its first epic that is most of them.

5. **Across the parts: `scenarios`.** Eight to ten walked end to end on real names and numbers, and
   deliberately across parts, because that is where a split by parts is blind — a person signing in,
   getting a lesson and answering it crosses three.

   **Read every scenario's ending back as a choice, never as prose.** *"After the first right answer
   the word becomes: `seen`, confidence 0.4 · `ok`, confidence 0.6 · something else"*. A wall of text
   with a yes-or-no under it gets a yes: agreeing is free and produces nothing. On a measured run six
   endings went unread that way, contradicted the product, and cost that run its finish.

6. **MVP bounds** — the last to be drawn honestly, because before the parts are told there is
   nothing to draw them around. Two explicit lists.

## What to ask about, and what never

The filter step 5 is held to. It decides whether a round is worth the owner's attention, and getting
it wrong in the generous direction is what teaches them to tap without reading:

| ask | never ask |
|---|---|
| what the person sees, and in what order | how it is stored |
| what happens when it does not work | which request, which index, which schema |
| what is kept about them that they could notice | protocols, headers, the shape of a table |
| who may, and **who may not** | how it is layered, which pattern, where the logic lives |
| what costs money | |

Measured on a real run, four out of five decisions a build takes are the right-hand column — whether
the web build can use secure storage, whether a sign-in must carry a nonce. The owner cannot answer
those and should not be asked; a run decides them and records the decision.

The two rows worth naming, because they look alike and are not: **who may not** is always asked —
the code shows who can and never says whether that was intended — and **how it is built** never is,
however architectural the question feels. A layering the owner has an opinion about belongs in
`stack.md` as a stance, put there once, not asked per part.

Questions are derived from what they just said, never from a checklist. Two to four options each,
several on a screen, per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`.

**Draft what the code can witness; ask what it cannot.** Both are right, and which applies is decided
by the answer's kind rather than by whether the project is new — a repository full of code and
documents still cannot say why any of it is there.

| The answer is about | Who goes first |
|---|---|
| what exists — routes, screens, stored shapes, states, the calls it makes | the draft. *"Here are the nine things a developer can do, taken from the code — what is wrong, what is missing?"* costs the owner less than nine questions, and on an inherited project it is most of the work |
| what it is for, what it deliberately does not do, why, what is coming | the owner. No code witnesses intent, and a document claiming it is a witness rather than the truth |
| **what a thing ends with, what may never happen, where the bounds are** | the owner, always — even where the documents look complete |

The last row is the one worth the extra minute, and it has a test of its own: **can the code be wrong
about this without anyone noticing?** A screen's existence, no — it is there or it is not. A
scenario's ending, yes, for months: on a measured run six endings were drafted rather than asked,
the product contradicted every one of them, and it cost that run its finish.

Batch independent decisions into one structured round with a recommendation on each; a question whose
answer would moot another goes in a later round.

**Going fast is allowed, and it is recorded rather than hidden.** A part drafted and confirmed
without a walk stays marked derived in `product.md`, and `epic` says so at its gate. That is what
makes the speed safe: the owner chose it and can see they did.

**Check every slot against the owner's own telling.** It is short, so re-read it as you open each
slot and name what it mentions that no entry covers: *"you mentioned agencies and a moderator — the
agency is recorded, the moderator is nowhere. Is it an actor?"* Close the interview with the same
sweep. This is the one judgement `--check` cannot make, which is why it lives here.

**Closing a slot** means giving it a verdict in `project.yml`: `filled`, `not_applicable` with the
reason, or `open_question` for a known unknown accepted deliberately. The bar is a deliberate
verdict, not literal fullness — a slot the product does not need but is forced to fill gets filled
with invention, and invented knowledge is worse than a gap: a run is careful around a gap and
confident around a wrong answer.

**When knowledge already exists elsewhere**, do not restate it. The entry keeps the structured
answers and points at the owner's document: `source: docs/DEVELOPER.md#offers @a3f1c9d`. Their prose
stays theirs and is not duplicated; when they edit it the hash diverges and the check says so. The
hash is recorded by the program and never written by hand — see the shared rule.

### Knowledge written by an older kit

A project carried across a year of releases has files whose shape stopped matching what the commands
expect. Nobody can see that by reading: each file declares its own `fields:` line and is checked
against **that**, so an entry missing a field the templates gained years later passes every check
there is. The owner cannot be asked to remember release notes either.

So the check does it. `check.py` compares this project's knowledge and `.agent-kit/project.yml`
against the templates that ship beside it — how many fields a record declares, how many sections a
file has, which keys the manifest holds — and prints what is behind. **Structure only**: the
templates are in English and the files are in the project's language, so it counts and never
compares words, and it never says *which* field is missing, because pairing two lists across
languages is a guess.

Pairing them is yours, with the owner there, and it is the reason this arrives as a plain
`blueprint` rather than a flag nobody remembers:

- **a field the records do not have** — put the two lists up, agree which is new, then fill it for
  the entries that matter. Not all of them at once: an old project with forty entries and a new
  field is a batch of work, so take the ones the owner is about to build in and say the rest is
  outstanding. **A field you fill without asking gets an `[assumed …]` block** — the knowledge did
  not say and you decided, which is what that block is for, and it is the difference between forty
  records answered and forty records inferred. Filling them silently would leave every check in the
  kit quiet, which reads as done;
- **a section a file does not have** — usually one interview step that did not exist when the file
  was written. `Parts` is exactly that: a project from before it has no record of what its parts
  are and nobody has walked any of them, which is what `epic` reports at its gate;
- **a key the manifest is missing** — settle it the same way the interview settles it new.

**It is a statement, not a defect**, and it changes no exit code: an older project is not broken, it
is behind, and only a session with the owner in it can move it forward.

### A document is a witness, not the truth

The code is the fact. The owner is the authority on intent. A document is neither: it may be a year
stale, half-written, or wrong in the one sentence a run will build from — and adopting it silently is
how a confident description produces a product nobody wanted.

So **nothing taken from an existing document enters an entry until it is one of three**, and settling
that is yours:

| | What you do |
|---|---|
| **the code agrees** | take it, with a `source:` and its hash — the check watches for drift from here on |
| **the code says otherwise** | do not take either. Put both sides up as a choice: *"the document says the offer is withdrawn, the code archives it — which is right?"* |
| **cannot be checked** — intent, plans, why | do not take it at all. It goes into the part's interview as an ordinary question |

The third is the one that looks safest and is not: *why* and *what next* are exactly what no code can
contradict, so a stale intention survives every mechanical check the kit has and is followed by every
run for months.

What an inherited repository changes is only **how much of the telling and the parts you can
draft** — both come as a proposal from the code and the documents, and the owner corrects by
tapping. It changes nothing about which answers may be drafted at all: that is decided by the kind
of answer, in *Draft what the code can witness*, and the third row of that table holds on the
best-documented project there is.

## How a session ends

Per `${CLAUDE_PLUGIN_ROOT}/rules/closing.md`, and here that means naming the things the owner cannot
see by reading the files:

- **Where each slot came from** — derived from the code, taken from their own documents by
  reference, or told to you in the interview. This is what says how much of it is really theirs.
- **Where it is thin** — slots left `open_question`, entries with fields you could not fill,
  and what the cross-checks found.
- **Where the product stands against its own MVP bounds** — which entries inside them are not
  `built` yet. Mechanical, and it is the question owners actually ask.
- **What `built` rests on.** Those entries have code; nothing in this file says they work. The
  scenarios are that check, they run against a live application, and on a project the kit adopted
  nobody has ever run them. Say it once, plainly, rather than letting fifty `built` markers imply
  more than they carry.
- **What you did not do**, when something obvious was left alone.
- **Then invite the rest**: this is what I understood, and here is where it is thin — what is wrong,
  and what is missing? Naming your own weak spots is what makes that question answerable; asking
  "anything to add?" after a confident summary gets "looks good" and hides everything.

Run `commands.test` from `project.yml` once before you close, and report what it returned. The
point is narrow: you recorded that command, and every later command depends on it, so a wrong one is
found here rather than in the middle of a build. Report the result and never fix it — a red suite on
a project the kit has just adopted is the owner's news, not this command's work.

Committing follows `${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md` — one commit per slot as it is
settled — and **where it lands is yours to state, because it differs from `advise`.**

**Onto the branch that is checked out, and no pull request of its own.** The owner settled every slot
out loud as it was written, so there is nothing a reviewer would catch, and an interview that may
span days cannot leave the knowledge on an unmerged branch where the other commands cannot see it.
Usually that branch is the default one, and the owner being here is the confirmation — nothing asks a
second time. Started mid-feature, the knowledge lands on that feature's branch and travels with its
pull request, which is where the gap surfaced. Only if the default branch is protected does blueprint
fall back to a branch and a pull request, and it says so.

**Look at the branch before the first commit rather than assuming.** On a spent feature branch —
one whose pull request has already merged — say so and branch from the default instead.

### While a run of this kit is in flight

The check prints that first, before anything else. **It does not stop you** — you write no code, and
a description dictated at midnight is worth more than a night of waiting. Three things change, and
the first is the only one that is not obvious:

- **Take a tree of your own** — `git worktree add ../<project>-knowledge <default branch>` — and
  work there. The project's own checkout belongs to the run: the driver starts every child in it, so
  moving its branch pulls the working tree out from under a live session. The guard hook refuses
  that move, so this is the way through rather than the polite option.
- **From the default branch, and never from the run's own branch** — however tempting, and it is
  tempting for a real reason. An `epic` runs for days and writes into knowledge as it goes: blocks,
  state lines, the frame. Working from the default branch you cannot see any of that, and you may
  rewrite prose the run has already corrected. **Read it instead of building on it** — reading costs
  nothing and changes no delivery:

  ```bash
  git diff <default branch>...<the run's branch> -- docs/knowledge/
  ```

  What basing on it costs is two things, and a live session found both the hard way: a knowledge
  branch cut from an unfinished epic **cannot merge on its own**, and its pull request into the
  default branch **carries the whole epic** — 88 files and sixty commits of somebody else's code on
  the run that measured it — so merging it would take that epic into the default branch past its own
  review. `check.py --pr-base` says this before the pull request is opened.
- **Commit on a branch and open a pull request.** The same guard refuses a push to the default
  branch while a run is in flight, and that is right: the knowledge lands when the batch does.
- **Merge order: the batch first, this branch last.** A batch is a chain of branches and rebasing it
  is expensive; this is one branch and rebases in a minute. Say it in the pull request.

The run is not affected by any of it — it reads the knowledge off the branch it forked from, so
nothing you write moves under it. What the two of you share is one meeting point, the merge, and
`check.py --run` names there which records moved while the batch ran.

**Conflicts in `docs/knowledge/` are the expected cost, and most of them are not disagreements.** A
run appends its blocks at the end of a record and you rewrite the fields inside it, so the usual
conflict is two additions at the same seam and the resolution is *keep both*. The one that matters
is where both rewrote the same sentence: that is the description and the build saying different
things, and settling it is yours, with the owner — nothing else in the kit may.

## Notes left by runs

A run never stops over the knowledge and never asks it to be rewritten. It leaves a block and
carries on — `[assumed …]`, `[found …]`, `[stale …]`, `[accepted …]`, `[frame …]`. **Deleting the block is the
resolution**, and who may delete which is one table, in
`${CLAUDE_PLUGIN_ROOT}/rules/channels.md`: some of these you are the only closer of, and two of
them a build command with the owner in the room, or the session closing a batch, may also close.
What each means and how each ends, when the check names one:
`${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/blocks.md`.

Blueprint's work list is exactly these blocks plus what the check flags, so a second run costs
minutes rather than hours.

## What `--check` does

Mechanical only, in seconds: states, fields, references, orphans, sources, stack age, the five kinds
of block, verdicts, unmet promises, debt, and whether this project's knowledge is behind the shape
the templates ship. Silent when clean, exit code 1 when not — except unmet promises and the older-kit
statement, which are listed whenever they exist and change no code, because neither is a defect in
the knowledge. `epic` refuses to start when a slot in its scope is unsettled; the others report and
carry on.

The rules are in `scripts/check.py`, which is what lets every command run them and keeps one rule
from meaning two things. Rule by rule: the design note `docs/design/check.md`, in the kit's own
repository — not in an installed copy of this plugin, which carries the payload and nothing else.

Your job around it is the part a program cannot do: say which of its findings matter for what the
owner is about to do, and offer to fix them here and now.
