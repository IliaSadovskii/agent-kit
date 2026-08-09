---
name: blueprint
description: The project's knowledge layer — interview the owner and write the documentation the other four commands build from: application type and stack, actors, entities, actions, screens, integrations, scenarios, MVP bounds. Also audits that knowledge mechanically.
argument-hint: "[what to add or reconsider] [--check]"
disable-model-invocation: true
---

# Blueprint

Everything the project knows about itself, in one place, written before anything is built.
`fix`, `ship`, `sprint` and `mvp` read it and never write prose into it. `advise` writes what the
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
| `blueprint --check` | audits, mechanically, in seconds, asking nothing. Run the program — `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status --sync` — and put its output in front of the owner with a sentence about what to do next. `--sync` is yours alone: it moves an entry whose pull request has merged, which is the one thing this program writes, and a preflight that wrote it would leave the tree dirty under the command that ran it. Two audiences: as another command's preflight it is run bare and prints nothing when clean; **by hand it always prints where the project stands**. That is the raw view of the knowledge; `/agent-kit:next` is the same data ranked into a recommendation. |

Every question you put to the owner follows `${CLAUDE_PLUGIN_ROOT}/rules/asking.md`: options
rather than prose, the recommendation first, and everything independent in one round.

## What this command does not do

It writes knowledge. It does not build anything, start or instrument the application, write scripts,
install dependencies, produce quality or audit reports, or decide what gets worked on first — those
belong to `fix`, `ship`, `sprint`, `mvp`, or to a plain conversation with the owner.

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

Order, because each step feeds the next:

1. **The owner's own telling.** One open question: what is this, for whom, how does it work. Not a
   form — follow up until you can restate it, then restate it in a few lines and get a yes. On a
   repository with real code, read the code first and bring your reading to be corrected, spending
   the owner's attention only on what code cannot say: intent, what is deliberately out of scope,
   what is coming. Store it near-verbatim as the first section of `product.md`.
2. **Application type and stack.** Versions from the manifests, per-area decisions from the code.
   Then one bounded research pass — delegate it — on what this framework's current major
   recommends and which packages this ecosystem treats as the standard answer. It comes back as a
   proposal, never as a written record: *here is what I found, what is wrong and what is missing?*
   On an empty repository the owner says what patterns and infrastructure they want, in free form,
   and research fills in around it.
   Settle `tests.unmet` in `project.yml` here, while the runner is in front of you: what keeps a
   test off the red in this project, for the day a test has to prove a promise the product does not
   keep. The template says what to look for, and a project with several suites gets a line each.
   Leaving it blank costs a build command an invented answer at midnight.
3. **`product`** — what it is for, and what it deliberately does not do. The second is worth more
   to an autonomous run than the first.
4. **`actors`**, then **`entities`**, then **`actions`**. Actions are the bulk: take one actor at a
   time, put up the whole list of what it can do before filling anything in, then fill entries in
   batches.
5. **`screens`** — derived from the actions and from the routes and views in the code; propose and
   let the owner correct. Do not start the application to find out what it has: when the code will
   not tell you, say so, mark the slot `open_question` and move on. An honest gap costs a line; an
   audit of a running app costs an afternoon and is not what was asked for.
   **`integrations`** the same way.
6. **`scenarios`** — walk eight to ten end to end on real names and numbers. This is the
   completeness test, not a longer questionnaire: where the honest answer is "we would add another
   field", the knowledge is wrong, and you find it here rather than in the build.
7. **MVP bounds** — last, because before the walks they cannot be drawn honestly. Two explicit
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
and what it could not see. `mvp` refuses to start when a slot in its scope is not settled; the other
three report and carry on.

Your job around it is the part a program cannot do: say which of its findings matter for what the
owner is about to do, and offer to fix them here and now.
