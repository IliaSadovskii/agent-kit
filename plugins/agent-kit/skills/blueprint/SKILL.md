---
name: blueprint
description: The project's knowledge layer — interview the owner and write the documentation the other four commands build from: application type and stack, actors, entities, actions, screens, integrations, scenarios, MVP bounds. Also audits that knowledge mechanically.
argument-hint: "[what to add or reconsider] [--check]"
disable-model-invocation: true
---

# Blueprint

Everything the project knows about itself, in one place, written before anything is built.
`fix`, `ship`, `sprint` and `mvp` read it; none of them write prose into it.

**One writer, one trigger.** Only blueprint rewrites knowledge, and only the owner starts
blueprint. Everything else can mark — a build command leaves a note, `--check` flags what went
stale — but nothing revises knowledge on its own. Rules the build follows must not change under a
run.

## How it is invoked

| Invocation | What it does |
|---|---|
| `blueprint` | continues from wherever the last session stopped: works only on what is empty, stale, or marked by an earlier run. Interactive. |
| `blueprint <what you want to add or reconsider>` | the owner has something the documents do not hold yet — a feature they have thought through, a part they want reworked, a doubt about whether something is covered. Find the slots it touches, interview about those, write, stop. Without this a finished blueprint has no way in, and the thought turns into work nobody asked for. |
| `blueprint --check` | audits. Seconds, mechanical, asks nothing, and prints nothing when everything is clean. Runs ahead of every other command. |

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

`docs/knowledge/`, one file per slot, copied from `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/` on
first use and filled in. The templates carry the shape of a record and the bar for the file being
done — read the one you are working on rather than recalling its fields.

`.agent-kit/project.yml`, from `${CLAUDE_PLUGIN_ROOT}/templates/project.yml`: the language, the
project's commands, the verdict per slot.

Prose is written in the project's language. Translate a template's headings, its field labels and
its `fields:` line together, so the file stays self-describing; keys, statuses and state names stay
English.

## The interview

**Write each slot to disk and commit it as it is settled.** A session that dies costs one slot.

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
answers and points at the owner's document: `source: docs/DEVELOPER.md#offers @a3f1c9d`, where the
hash is that section as you read it. Their prose stays theirs and is not duplicated; when they edit
it the hash diverges and `--check` says so.

## How a session ends

Not with a retelling of the product — the owner can read the files, and a summary always sounds
confident whether the understanding under it is deep or shallow. End with the things they cannot see
by looking:

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

**Commit onto the branch that is checked out**, one commit per slot, and push when there is a
remote. No pull request of its own: the owner settled every slot out loud as it was written, so
there is nothing a reviewer would catch, and an interview that may span days cannot leave the
knowledge on an unmerged branch where the other commands cannot see it. Usually that branch is the
default one and the guard asks once — the owner is present, that is their confirmation. Started
mid-feature, the knowledge lands on that feature's branch and travels with its pull request, which
is where the gap surfaced. Only if the default branch is protected does blueprint fall back to a
branch and a pull request, and it says so.

## Notes left by runs

A run that lacks knowledge does not stop and does not ask. It decides, continues, and leaves a
block under the entry it stood in for:

```markdown
> **[assumed 2026-08-02 · claude/offer-roles]** Nothing says what happens to an offer when the
> request is cancelled. Took: it goes to `withdrawn`, not deleted. Expensive to get wrong — data model.
```

A run that finds a better answer than the library map holds leaves `[found …]` the same way.

**A recorded assumption is the decision of record until the owner changes it.** A later run hitting
the same gap follows it rather than inventing a second reading — that is what keeps features
consistent with each other.

Blueprint's work list is exactly these blocks plus what `--check` flags, so a second run costs
minutes, not hours: ask the block as a yes-or-no — *"I took it that an offer goes to `withdrawn`;
right?"* — then rewrite the entry and **delete the block**. Deleting it is the resolution; there is
no `resolved` field anywhere.

Notes are only left where being wrong is expensive — data model, permissions, money, a public
contract — or where the run's own confidence was low. Everything else stays in the run file as
history. Without that filter the documents silt up after one sprint.

## What `--check` does

Mechanical only. No reading for quality, no grader, no research — that is what makes it cheap
enough to run ahead of everything.

- **States.** For every entry marked `building`, read its pull request: merged makes it `built`,
  closed unmerged puts it back to `planned`.
- **Fields.** Every record has the `fields:` its file's header declares, each with content. A field
  runs until the next field or the next heading, so one whose answer is a list on the lines below it
  is filled — reading only the label's own line reports every scenario in the file as empty.
- **References.** Every key resolves: the actor exists, the entity exists, a status an action sets
  is in that entity's states, an action named in a screen transition or a scenario step exists.
- **Orphans.** An actor with no action, an entity nothing creates, a screen nothing leads to and
  which is not an entry point.
- **Sources.** For every `source:`, the file and heading exist and the hash still matches.
- **Stack age.** The direct dependency manifests against their recorded hash; and
  `stack_researched` past six months, named once.
- **Notes.** Count the `[assumed …]` and `[found …]` blocks and list them.
- **Verdicts.** Slots with no verdict in `project.yml`.

Silent when clean. Otherwise one screen: what is open, what is stale, what does not line up.
`mvp` refuses to start when a slot in its scope is not settled; the other three report and carry on.
