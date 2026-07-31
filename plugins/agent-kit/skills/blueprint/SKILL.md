---
name: blueprint
description: Audit the project's knowledge contract and derive its index — the slots the pipelines need answers to, the instances each collection enumerates, where every answer lives, and whether the keys agree with each other. Use when the owner asks whether the project's knowledge is current, before trusting a build command with it, or to parse documents the contract binds.
disable-model-invocation: true
argument-hint: --check | --index
---

# Blueprint

The knowledge layer. Two modes, and the difference between them is cost: `--check` answers in
seconds without a model in the loop, `--index` spends a grader call per document to re-read what
changed.

## Arguments

`$ARGUMENTS`

- `--check` — the audit. Mechanical, non-interactive, no grader.
- `--index` — re-derive `.agent-kit/knowledge/index.yml` for the entries whose prose changed.
- Anything else, including no arguments at all: say plainly that blueprint's interview — filling the
  slots, walking the stories — lands in a later version of the kit, and that `--check` and `--index`
  are what exist today. Offer to run the audit. Do not improvise an interview: a slot filled by
  guessing is read afterwards as the owner's decision.

## What --check does

Run the script and read its output back to the owner:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blueprint_check.py" --check
```

It reads `.agent-kit/knowledge/contract.yml` from the project root, and checks:

- every slot carries a **terminal verdict** — `filled`, `not_applicable` with a reason, or
  `open_question`. `empty` and `conflicts` are not verdicts;
- every `source` and every entry's `at` resolves to a file and to the heading or anchor it names;
- every bound section still hashes to the `rev` recorded for it, so an edit to the prose makes the
  slot stale and an edit under an entry makes that entry due for a re-parse;
- every command in the `verification` slot actually runs from the project root and exits 0. That
  slot is proven by running it, never by reading it;
- the **cross-checks** over the derived index: a status an action sets exists in that entity's
  lifecycle, an action is one its actor may perform, a screen an action names is on the map and a
  live screen on the map is reached by some action, an entity the product writes has an action that
  creates it and one that closes it, and nothing references an instance no entry describes.

Three exit codes, and they are the point — a later version puts this in front of every build command:

| Code | Means | What to do |
|---|---|---|
| `0` | clean | say so in one line and stop |
| `1` | findings — a slot with no verdict, a cross-check that fired, an entry whose prose does not answer something, a binding that drifted | report each one; offer to fix what is mechanical |
| `2` | structural — the contract is unreadable, a document is gone, an anchor resolves to two places, a verification command failed | report it as a failure, not as a nit |

The script never calls a grader, never asks a question, and writes nothing. A stale entry is
reported, not re-parsed: re-parsing is `--index`, and keeping the two apart is what lets this stay
cheap enough to run before everything else.

## What --index does

Three steps, and the middle one is yours — the script is stdlib Python and cannot call a model.

**1. Ask what needs parsing.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blueprint_index.py" --plan
```

JSON on stdout: one group per document, each carrying only the sections whose hash no longer
matches the index, with their text. **Nothing below runs when the plan is empty**; that is the whole
point of the cache.

An empty plan means the index is current *for every entry that resolves*. Read stderr before saying
so: an entry whose binding no longer resolves cannot be parsed, and the script lists each one there
by name. Report those instead — the repair is `--check`'s drift section, not a grader call.

**2. Grade each group, one subagent call per group.**

One call per document, not per entry, and never one call for everything. Send the group's entries
with the rubric at
`${CLAUDE_PLUGIN_ROOT}/skills/blueprint/references/grader.md`, which defines the facts to extract
and the bar to judge against. The grader reads prose and returns data; it does not edit anything.

Collect the results into one JSON file, a flat list. **Copy `collection`, `key` and `rev` from the
plan entry verbatim** — `rev` is the hash of the text the grader actually read, and it is what makes
a document edited mid-run come back stale instead of being recorded as parsed:

```json
[{"collection": "actions", "key": "developer.create_offer", "rev": "a3f1c9d4e2b1",
  "facts": {"actor": "developer", "statuses_set": ["offer.pending"], "screens": ["S12"]},
  "gaps": []}]
```

**3. Apply.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blueprint_index.py" --apply results.json
```

The script writes `.agent-kit/knowledge/index.yml` and drops entries the contract no longer lists.
It refuses a result with no `rev`, by name, rather than guessing one from the current file. An entry
whose binding broke while the grader was running is skipped by name on stderr and the rest of the
batch is kept, so one renamed heading never costs a whole run's calls. Then run `--check` and report
what the cross-checks found.

Commit the index. It is derived, but derived by dozens of grader calls, and a clone, a CI run and a
headless run should inherit the cache rather than pay for it again.

## Placing anchors

An entry binds either to a heading — which drifts the day someone renames it — or to an anchor:

```markdown
### Создание оффера застройщиком
<!-- kit: developer.create_offer -->
```

Anchors are the default, and **the kit places them, never the owner**. This is the one moment the
kit writes into the owner's own documents, and it asks first:

1. find the entry boundaries — a grader proposes them, because a heading-level rule does not survive
   real documents where entries sit at different depths or inside lists;
2. show the list — *"found 23 actions, here is where the anchors go"* — one line per anchor, naming
   the document and the heading;
3. wait for an explicit yes. Not an inferred one, not "proceeding unless you object". In an
   autonomous run there is nobody to ask, so the anchors are **not** written: record the proposal
   and say so;
4. then, and only then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blueprint_index.py" --anchors proposal.json
```

where each proposal is `{"collection": …, "key": …, "path": …, "heading": …}`. The script writes
each anchor on its own line under its heading and records the matching `entries:` block in the
contract — one surgical edit that leaves every other byte of that file, comments included, alone.
It validates the whole proposal before writing anything, so a run that fails leaves no anchor the
contract does not know about.

Commit the documents and the contract together.

**An anchor removed by hand is never silently re-added.** `--check` reports it as drift, `--index`
refuses to parse that entry, and putting it back goes through this flow with its own yes. The owner
deleting an anchor is a decision, not a typo to repair.

The `file#heading` binding stays supported for owners who refuse anchors. Its drift is reported
separately, because the fix differs: a removed anchor is re-proposed, a renamed heading is
repointed.

## The verification slot runs

It is the one slot proven by running rather than reading, so `--check` executes what the contract
declares. Two things follow, and they are worth saying out loud rather than leaving in the script.

**The contract is a file in the repository, so its commands are code from the repository.** They
can arrive in a pull request like anything else. The script announces each command before it runs
it, and refuses outright — without running it — any command the kit's own never-rules cover, since
a subprocess is invisible to the hook that normally turns those into a confirmation. On a
repository the owner does not control, read the `verification` block before running the check at
all. The commands themselves are the project's, and running the project's own commands is what
every pipeline here already does; what is new is only that the list lives in a file someone else
may have edited.

**A failing command's output goes into the report.** The last few lines of it are what makes the
failure readable, and they are also where a connection string or a token would be. Read them before
they go anywhere else: the always-on rule that secrets never enter commits, logs, plans, or PR
descriptions applies to a tail you pasted as much as to one you typed.

## Reporting it

Findings are the owner's decisions, so hand them over rather than acting on them. Three exceptions
are yours to offer, because they are mechanical and the report already contains the answer:

- **a stale `rev`** — the section changed; once the owner confirms the prose is still the right
  answer, write the new hash the report printed into the slot;
- **a binding with no `rev`** — same, with nothing to compare against yet;
- **a stale entry** — that is what `--index` is for, and it costs one grader call per document.

Everything else — a slot with no verdict, a `not_applicable` with no reason, a source that is gone,
a cross-check that fired — is knowledge, and knowledge is the owner's to give. A cross-check finding
in particular is a real disagreement between two documents; guessing which one is right and editing
it is exactly the invention this whole layer exists to prevent. Ask; do not fill.

## When there is no contract

`--check` exits `2` and names the template it would start from. Say what the file is for and offer to
copy the template in, then leave the verdicts to the owner: every slot arrives `empty`, which is the
state the check exists to report. The kit does not write to the owner's documents here, and it does
not fill a slot on their behalf.
