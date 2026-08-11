---
name: blueprint
description: The project's knowledge layer — interview the owner and write the documentation the other commands build from: application type and stack, actors, entities, actions, screens, integrations, scenarios, MVP bounds. Run with nothing when you do not know what is wrong: it says what is missing, what is behind the kit's current shape, and what to do about each — or that there is nothing to do.
argument-hint: "[what to add or reconsider] [--check]"
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
| `blueprint` | continues from wherever the last session stopped: works only on what is empty, stale, marked by an earlier run — **or written by an older kit**, which is the one nobody can spot by reading. Interactive. |
| `blueprint <what you want to add or reconsider>` | the owner has something the documents do not hold yet — a feature they have thought through, a part they want reworked, a doubt about whether something is covered. Find the slots it touches, interview about those, write, stop. Without this a finished blueprint has no way in, and the thought turns into work nobody asked for. |
| `blueprint <what did not match, after using it>` | the same door from the other side: the owner has clicked through what a run built and can say what is wrong. One fork per complaint, and half of them are not blueprint's work — `${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/doors.md` |
| `blueprint --recall [part]` | tells the owner what the project already says, in their language and out loud, so they never open a file to find out. Changes nothing until they ask for a change — `${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/doors.md` |
| `blueprint --check` | audits, mechanically, in seconds, asking nothing. Run the program — `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --sync` — and put its output in front of the owner with a sentence about what to do next. `--sync` moves an entry whose pull request has merged — the one thing this program writes, and never as a preflight, which would leave the tree dirty under the command that ran it. `next` and `accept` may run it too, under the same fence; a build command may not. Two audiences: as another command's preflight it is run bare and prints nothing when clean; **by hand it always prints where the project stands**. That is the raw view of the knowledge; `/agent-kit:next` is the same data ranked into a recommendation. |

Every question you put to the owner follows `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`: options
rather than prose, the recommendation first, and everything independent in one round.

## Where a plain run starts

**Typed with nothing, this is the command an owner reaches for when they do not know what is wrong.**
They may have never read a release note, may not know a flag exists, and may be coming back to a
project a year older than the kit it was written with. So a plain run does not guess where it
stopped — it asks the program, first, before anything else:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
```

That is not optional and not conditional. Left to be inferred, it is skipped — a build command was
once told to "run `blueprint --check`", went looking for an executable of that name, found none and
carried on silently, which is why these rules live in a program at all.

Then take what it printed, in this order, and stop at the first that applies:

| What it says | What you do |
|---|---|
| no `docs/knowledge/` | this is a first interview. Go to *The interview* |
| **written by an older kit** | say it in one screen — what the shape is missing and what it is for — and offer to bring it forward — *Knowledge written by an older kit*, below. Do this before any other work: the interview that follows writes into the new shape, and doing it the other way round means writing every entry twice |
| a slot with no verdict, empty fields, an open `[assumed …]`, a stale `source:` | that is the work list. Say how much of it there is, and start |
| entries the owner has never walked — parts marked derived | offer the walk, part by part. It is the one gap the check can see and cannot fix |
| nothing | **say so in one line and stop.** Then name what to run instead — usually `/agent-kit:next`, or `/agent-kit:epic` when there are entries still `planned`. An interview invented to fill the silence is the one thing an owner cannot check |

Say the count before you start on any of it. *"Four things are behind, two slots have gaps, and six
parts of nine you have never walked — that is about an hour"* is a sentence they can act on; opening
with the first question is not.

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
slot. The verdicts are yours alone; the rest of how a record is written —
templates, the project's language, `state: planned`, the commit per slot, hashes, the check
afterwards — is `${CLAUDE_PLUGIN_ROOT}/rules/knowledge-writing.md`, which `advise` follows too.

## The interview

**It is shaped by the product's own parts, not by the slots.** Nobody holds their product as actors,
entities and screens — they hold it as the things it does: sign-in, the lesson, the notifications,
the account. Walking the slots asks the owner to translate into a structure that is the kit's
convenience, and what does not survive that translation is what a run has to invent later. So the
questions follow the parts, and the slots are what the answers are written into: one part's telling
usually fills a screen, several actions and an entity at once.

Six phases:

1. **The telling.** One open question: what is this, for whom, how does it work. Not a form — follow
   up until you can restate it. On a repository with real code, read the code first and bring your
   reading to be corrected, spending the owner's attention only on what code cannot say: intent,
   what is deliberately out of scope, what is coming. Store it near-verbatim as the first section of
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

   **And ask what runs the scenarios end to end** — the one testing question a draft cannot answer.
   Everything else in the testing section is derived: the layers, the seams, the bar all come from
   the code and the manifests. A harness that does not exist yet is invisible to that, so silence
   here is read by every later run as a decision nobody made — and `epic` stops on *every scenario
   passes*, so it is the one gap that decides whether that command can finish at all. Name the tool
   and where it runs, or write plainly that there is none and the scenarios are proved by hand. Both
   are legitimate; neither may be left to be inferred.
4. **One part at a time**, and each is two moves.

   **The telling, in the owner's own words back at them.** Not *"tell me about the lesson"* but
   *"you said a lesson is a conversation with the model — take me through one, start to finish"*.
   Their vocabulary is what makes the question answerable.

   **Then what is still open, as choices.** Two to four options each, several questions on a screen,
   per `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`. Derived from what they just said, never from a
   checklist — and held to one filter, because it decides whether the round is worth their attention:

   | ask | never ask |
   |---|---|
   | what the person sees, and in what order | how it is stored |
   | what happens when it does not work | which request, which index, which schema |
   | what is kept about them that they could notice | protocols, headers, the shape of a table |
   | who may, and who may not | |
   | what costs money | |

   Measured on a real run, four out of five decisions a build takes are the right-hand column —
   whether the web build can use secure storage, whether a sign-in must carry a nonce. The owner
   cannot answer those and should not be asked; a run decides them and records the decision. Asking
   anyway is what teaches an owner to tap without reading.

   Then write the part into whatever slots it touches — actors, entities, actions, screens,
   integrations — and put the result up as a list of names to correct, not as prose: *"from the
   lesson I got one screen, five actions and one entity"*.

   A part is finished when you can write its records without inventing a **product** answer. The
   mechanics you may still decide yourself.

5. **Across the parts: `scenarios`.** Eight to ten walked end to end on real names and numbers, and
   deliberately across parts, because that is where a split by parts is blind — a person signing in,
   getting a lesson and answering it crosses three.

   **Read every scenario's ending back as a choice, never as prose.** *"After the first right answer
   the word becomes: `seen`, confidence 0.4 · `ok`, confidence 0.6 · something else"*. A wall of text
   with a yes-or-no under it gets a yes: agreeing is free and produces nothing. On a measured run six
   endings went unread that way, contradicted the product, and cost that run its finish.

6. **MVP bounds** — last, because before the walks they cannot be drawn honestly. Two explicit
   lists.

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

What an inherited repository changes is only **how much of phases 1 and 2 you can draft** — the
telling and the parts come as a proposal from the code and the documents, and the owner corrects by
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

## Notes left by runs

A run never stops over the knowledge and never asks it to be rewritten. It leaves a block, carries
on, and you are the only one who may resolve it — `[assumed …]`, `[found …]`, `[stale …]`,
`[accepted …]`. **Deleting the block is the resolution**; nothing else in the kit removes one.
What each means and how each ends, when the check names one:
`${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/blocks.md`.

Blueprint's work list is exactly these blocks plus what the check flags, so a second run costs
minutes rather than hours.

## What `--check` does

Mechanical only, in seconds: states, fields, references, orphans, sources, stack age, the four kinds
of block, verdicts, unmet promises, debt, and whether this project's knowledge is behind the shape
the templates ship. Silent when clean, exit code 1 when not — except unmet promises and the older-kit
statement, which are listed whenever they exist and change no code, because neither is a defect in
the knowledge. `epic` refuses to start when a slot in its scope is unsettled; the others report and
carry on.

The rules are in `scripts/check.py`, which is what lets every command run them and keeps one rule
from meaning two things. Rule by rule: [docs/design/check.md](../../../../docs/design/check.md).

Your job around it is the part a program cannot do: say which of its findings matter for what the
owner is about to do, and offer to fix them here and now.
