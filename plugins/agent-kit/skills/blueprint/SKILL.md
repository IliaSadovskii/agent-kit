---
name: blueprint
description: Audit the project's knowledge contract — the slots the pipelines need answers to, where each answer lives, and whether the project's verification commands still run. Mechanical and non-interactive, no grader and no model judgement. Use when the owner asks whether the project's knowledge is current, or before trusting a build command with it.
disable-model-invocation: true
argument-hint: --check
---

# Blueprint

The knowledge layer's audit. `--check` is the only mode this version has: it answers, in seconds and
without asking anything, whether the project's own contract still holds.

## Arguments

`$ARGUMENTS`

- `--check` — run the audit and report it.
- Anything else, including no arguments at all: say plainly that blueprint's interview — filling the
  slots, placing anchors, walking the stories — lands in a later version of the kit, and that
  `--check` is what exists today. Offer to run it. Do not improvise an interview: a slot filled by
  guessing is read afterwards as the owner's decision.

## What --check does

Run the script and read its output back to the owner:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blueprint_check.py" --check
```

It reads `.agent-kit/knowledge/contract.yml` from the project root, and checks four things:

- every slot carries a **terminal verdict** — `filled`, `not_applicable` with a reason, or
  `open_question`. `empty` and `conflicts` are not verdicts;
- every `source` resolves to a file and to the heading it names;
- every bound section still hashes to the `rev` recorded for it, so an edit to the prose makes the
  slot stale;
- every command in the `verification` slot actually runs from the project root and exits 0. That
  slot is proven by running it, never by reading it.

Three exit codes, and they are the point — a later version puts this in front of every build command:

| Code | Means | What to do |
|---|---|---|
| `0` | clean | say so in one line and stop |
| `1` | findings — a slot with no verdict, an unresolved binding, a stale section | report each one; offer to fix what is mechanical |
| `2` | structural — the contract is unreadable, a source is gone, a verification command failed | report it as a failure, not as a nit |

The script never calls a grader, never asks a question, and writes nothing. Grading entries against
their criteria, and the interview that fills the slots in the first place, arrive in later versions.

## Reporting it

Findings are the owner's decisions, so hand them over rather than acting on them. Two exceptions are
yours to offer, because they are mechanical and the report already contains the answer:

- **a stale `rev`** — the section changed; once the owner confirms the prose is still the right
  answer, write the new hash the report printed into the slot;
- **a binding with no `rev`** — same, with nothing to compare against yet.

Everything else — a slot with no verdict, a `not_applicable` with no reason, a source that is gone —
is knowledge, and knowledge is the owner's to give. Ask; do not fill.

## When there is no contract

`--check` exits `2` and names the template it would start from. Say what the file is for and offer to
copy the template in, then leave the verdicts to the owner: every slot arrives `empty`, which is the
state the check exists to report. The kit does not write to the owner's documents here, and it does
not fill a slot on their behalf.
