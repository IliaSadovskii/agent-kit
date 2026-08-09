# Writing into the knowledge

Two commands write `docs/knowledge/`: `blueprint`, which interviews the owner and fills the slots,
and `advise`, which writes what the owner answered about a proposal they just accepted. This file is
what they share. What each of them asks, and in what order, is its own.

**The line that separates them from every other command is the owner's presence, not the command's
name.** A run with nobody in the room may move an entry's `state:` line and leave a block, and that
is all — it may not write prose, because prose is a decision and there is no one there to make it.
With the owner sitting there, their answer goes into the entry as they give it. That is transcribing,
not deciding, and it is why the same sentence is safe here and forbidden at midnight.

## The shape is in the template, never in the command

`docs/knowledge/`, one file per slot, copied from `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/` on
first use. Each template's header declares the record's `fields:` and the bar for the file being
done.

**Read the template for the slot you are about to write, and write from it** — not from what you
remember a record looks like. A second description of a record living in a command is how the two
come to disagree, and the one in the command is always the one that is out of date.

## The project's language

Prose is written in the project's language, from `.agent-kit/project.yml`. Translate a template's
headings, its field labels and its `fields:` line together, so the file stays self-describing.
Keys, statuses and state names stay English.

## A new entry is `planned`, and nothing else

An entry written before any code says `state: planned`. `building (pr: N)` belongs to the command
that opens the pull request, and `built` to the bookkeeping that sees it merged. Writing either of
those here would claim work that does not exist.

## Every key it names has to exist

A record's own template says it: every actor, entity, status and screen an entry names must exist in
its own file. So an entry that reaches for something not yet written pulls that slot with it, and the
order is the one `blueprint` interviews in — the actor, then the entity, then the action, then the
screen it is reached from, then the scenario it appears in.

**Write the whole of it or none of it.** A cascade left half-written is worse than nothing: a run is
careful around a gap and confident around a record that looks complete. Where the owner will not
settle the rest now, leave the whole item as a block and say so.

## Never write a hash by hand

Where an entry points at the owner's own document — `source: docs/DEVELOPER.md#offers @a3f1c9d` —
the hash is recorded by the program that computes it, never typed and never copied from printed
output:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --record
```

A value carried by hand is how the hashes written before that program existed came to be invented,
and a hash nobody can recompute proves nothing.

## Write it, commit it, then check it

**Commit each slot as it is settled**, one commit per slot. A session that dies then costs one slot
rather than the whole sitting. Push when there is a remote.

**Where those commits land is not shared, and each command says it itself.** Which branch, and
whether the work travels in a pull request, differs between the two — because what the owner
actually approved differs. In `blueprint` they dictated every slot as it was written, over a sitting
that may span days; in `advise` they said yes to a proposal of one line and the command composed the
record's fields around it. The first has nothing a reviewer would catch and cannot afford to sit on
an unmerged branch; the second is prose worth reading before it becomes the thing every later run
builds from.

**Never assume the branch that is checked out is the right one.** It is whatever the last command
left behind — after a sprint, a spent feature branch whose pull request has already merged. A run
that committed there without looking put six commits on a dead branch and pushed them, and only the
owner asking caught it.

**Then run the check**, and read what it says before closing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" . --status
```

It verifies mechanically what prose cannot: that every declared field has content, and that every key
resolves. A record that was written badly is found in seconds by the program that already knows the
rule, rather than by a build command a week later.
