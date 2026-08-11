---
name: blueprint
description: The project's knowledge layer — interview the owner and write the documentation the other four commands build from: application type and stack, actors, entities, actions, screens, integrations, scenarios, MVP bounds. Also audits that knowledge mechanically.
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
| `blueprint` | continues from wherever the last session stopped: works only on what is empty, stale, or marked by an earlier run. Interactive. |
| `blueprint <what you want to add or reconsider>` | the owner has something the documents do not hold yet — a feature they have thought through, a part they want reworked, a doubt about whether something is covered. Find the slots it touches, interview about those, write, stop. Without this a finished blueprint has no way in, and the thought turns into work nobody asked for. |
| `blueprint <what did not match, after using it>` | the same door, arrived at from the other side: the owner has clicked through what a run built and can say what is wrong. See below — it is one fork per complaint, and half of them are not blueprint's work at all. |
| `blueprint --recall [part]` | tells the owner what the project already says, in their language and out loud, so they never open a file to find out. Changes nothing until they ask for a change — see *Reading it back*. |
| `blueprint --check` | audits, mechanically, in seconds, asking nothing. Run the program — `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --sync` — and put its output in front of the owner with a sentence about what to do next. `--sync` is yours alone: it moves an entry whose pull request has merged, which is the one thing this program writes, and a preflight that wrote it would leave the tree dirty under the command that ran it. Two audiences: as another command's preflight it is run bare and prints nothing when clean; **by hand it always prints where the project stands**. That is the raw view of the knowledge; `/agent-kit:next` is the same data ranked into a recommendation. |

Every question you put to the owner follows `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`: options
rather than prose, the recommendation first, and everything independent in one round.

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

**Propose, don't interrogate.** An open question is for what a draft cannot cover. *"Here are the
nine things a developer can do, taken from the code and the request flow — what is wrong, what is
missing?"* costs the owner less than nine questions and costs fewer tokens than the ping-pong.
Batch independent decisions into one structured round with a recommendation on each; a question
whose answer would moot another goes in a later round.

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

This is the whole difference between an empty repository and an inherited one. On an inherited one
phases 1 and 2 — the telling and the parts — you propose from the code and the documents and the
owner corrects by tapping. Phases 4 to 6 are the same either way.

## Reading it back

The owner works through a session, not through a text editor. So when they have forgotten what a
part says, or doubt it, or want to rework it, **the answer is not "open `docs/knowledge/actions.md`"**
— it is you, retelling it.

`--recall` with nothing names the parts, one line each, and asks which to open. `--recall <part>`
tells that one:

- what it is for, in a sentence;
- who does what in it, and what the person sees;
- what happens when it does not work;
- what is **not** built yet — `planned` entries, open blocks, promises the product does not keep;
- and what is thin: fields nobody filled, and whether the owner ever walked this part or it was
  derived.

**A retelling, never the file.** Reading the entries out is the same wall of text they came here to
avoid, and it is what makes them stop asking. One screenful per part; if it will not fit, the part
is too big and say so.

Then one round of choices: *right as it stands* · *change this* · *rework the part*. The first ends
the session. The second and third are the ordinary interview, on that part alone, and everything
about how it is written and committed is unchanged.

**It decides nothing and writes nothing on its own.** That is what separates it from `--check`,
which is mechanical and silent when clean: this one always speaks, in prose, and is for a person.

## After the owner has used it

The first run of anything is wrong somewhere, and the owner finds out by clicking through it rather
than by reading. That is a different input from an interview: not what they imagine, what they saw.
It arrives as a list of complaints, in their words, in no order.

**Every complaint is one fork, and it is a fork the kit already knows** — the same one a build hits
when an entry promises what the code does not:

| What is wrong | Where it goes |
|---|---|
| **the description** — the product behaves correctly and is described wrongly | yours: rewrite the prose, which nothing else may |
| **the product** — the description is right and the build is not | not yours: a line for `fix`, or an entry back to `state: planned` for a build command |

Put that fork up per complaint, with your reading first. Do not resolve it by rewriting the entry to
match the code — that is how a product decision gets made by whoever typed last, and the entry stops
being something the build can be held to.

This is where `accept` hands over: it says what to open and what to click, and this takes what was
seen there.

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
on, and you are the only one who may resolve it. Four kinds, and each has its own ending:

| Block | What it means | What you do with it |
|---|---|---|
| `[assumed …]` under the entry | the knowledge did not say, the run decided | ask it as a yes-or-no — *"I took it that an offer goes to `withdrawn`; right?"* — write the answer into the entry, delete the block |
| `[found …]` under `stack.md` | a ready-made answer the library map does not name | confirm it belongs, add the package and what it covers to the library map, delete the block |
| `[stale …]` under the entry | the feature that shipped made the entry's prose false | nothing to ask: rewrite the prose to what is true now, delete the block |
| `[accepted …]` in the slot it names | `advise` proposed it, the owner said yes, and the fields were left for later | nothing to decide — it is already agreed. Interview the fields the record declares, write the entry, delete the block |

The check prints all four before every command. **Deleting the block is the resolution**; there is
no `resolved` field anywhere, and nothing else in the kit removes one.

`[accepted …]` is the one that arrives already answered, so do not re-open it: asking again whether
the owner wants what they accepted last week is how a list stops being read. If they have changed
their mind, they will say so in a sentence and the block goes without an entry.

**And a ledger line whose work you have just done, you delete** — in `docs/technical_debt.md`, in
the same commit, exactly as any run does when it finishes an item. A line asking for prose to be
rewritten has no other closer: `ship` and `fix` may not touch prose, so if you leave it the work is
done and the line stays for ever. Only the ones you actually closed, and nothing else in that file.

**A recorded assumption is the decision of record until the owner changes it.** A later run hitting
the same gap follows it rather than inventing a second reading — that is what keeps features
consistent with each other.

Blueprint's work list is exactly these blocks plus what `--check` flags, so a second run costs
minutes rather than hours.

Blocks are only left where being wrong is expensive — data model, permissions, money, a public
contract — or where the run's own confidence was low. Everything else stays in the run file as
history. Without that filter the documents silt up after one sprint. A `[stale …]` has no such bar:
prose that contradicts the product is always worth a block, because every later run reads it as
true.

## What `--check` does

`scripts/check.py`, and this section describes it rather than instructing you: the rules live in the
program, which is why every command can run them and why the same rule cannot mean two things.

Mechanical only. No reading for quality, no grader, no research — that is what makes it cheap
enough to run ahead of everything.

- **States.** For every entry marked `building`, read its pull request: merged makes it `built`,
  closed unmerged puts it back to `planned`.
- **Fields.** Every record has the `fields:` its file's header declares, each with content. A field
  runs until the next field or the next heading, so one whose answer is a list on the lines below it
  is filled — reading only the label's own line reports every scenario in the file as empty.
- **References.** Every key resolves: the actor exists, the entity exists, an action named in a
  screen transition or a scenario step exists. Whether a status an action sets is one the entity
  declares is **not** checked — the program says so in its own closing line, and reading it as
  checked is how a wrong status survives.
- **Orphans.** An actor with no action, an entity nothing creates, a screen nothing leads to and
  which is not an entry point.
- **Sources.** For every `source:`, the file and heading exist and the hash still matches.
- **Stack age.** The direct dependency manifests against their recorded hash; and
  `stack_researched` past six months, named once.
- **Notes.** Count the `[assumed …]`, `[found …]`, `[stale …]` and `[accepted …]` blocks and list
  them.
- **Verdicts.** Slots with no verdict in `project.yml`.
- **Unmet promises.** Every test carrying `agent-kit:unmet` outside `docs/`, with the entry it
  names — flagging a key no entry defines, and a project that has marks but no `tests.unmet`.
- **Hashes it can compute itself.** `--record` rewrites every `source:` and every dependency hash in
  place. Use it rather than copying a printed value into a file: a hash carried by hand is how the
  pre-4-August ones came to be invented, and a value nobody can recompute proves nothing. A recorded
  hash shorter than eight characters is from that era — re-record and move on, no document changed.
- **Debt.** The open items of `docs/technical_debt.md` — work earlier runs decided not to do.

Silent when clean, exit code 1 when not — with one exception: unmet promises are listed whenever
they exist and change no exit code, because a recorded promise is a statement about the product, not
a defect in the knowledge. Otherwise one screen: what is open, what is stale, what does not line up,
and what it could not see. `epic` refuses to start when a slot in its scope is not settled; the other
three report and carry on.

Your job around it is the part a program cannot do: say which of its findings matter for what the
owner is about to do, and offer to fix them here and now.
