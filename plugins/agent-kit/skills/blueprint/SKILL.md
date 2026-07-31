---
name: blueprint
description: Check the project's knowledge contract — a slot list with a deliberate verdict per slot, bound to the prose that answers it, and a mechanical --check that catches staleness and proves the project's verification commands actually run. Use when the owner asks to check, start, or ask about the project's knowledge contract or contract.yml.
argument-hint: "--check"
disable-model-invocation: true
---

# Blueprint

The kit does not need a file format — it needs **filled slots**: questions its pipelines must have
a deliberate answer to before they trust the project's own knowledge. `.agent-kit/knowledge/contract.yml`
holds those answers, in the owner's hand, bound to wherever in the project's own documents the
answer actually lives. The project's `docs/` stay the source of truth; the contract only indexes
them.

## The contract

Six singular slots — `north_star`, `architecture_stance`, `verification`, `mvp_bounds`, `scenarios`,
`deferred_seams` — and five collections — `actors`, `entities`, `actions`, `screens`,
`integrations`. Every one carries a `status`, and only three are terminal:

- `filled` — answered, bound to `source: file#heading` in the project's own prose, with a `rev`
  recorded against that section's current text.
- `not_applicable` — not relevant to this project, with a `reason`.
- `open_question` — a known unknown, accepted on purpose.

`empty` (nobody looked) and `conflicts` (sources disagree) are not terminal states; `--check` reports
both as findings. The bar is "every slot has a deliberate verdict", not "every slot is filled" — an
invented answer is worse than an honest gap, because a gap is treated with caution and a fabrication
is treated as the owner's decision.

## `--check`

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/knowledge_check.py" --root <project-root>
```

Cheap and non-interactive — seconds, no grader. It reads `<root>/.agent-kit/knowledge/contract.yml`
and reports:

- every slot and collection has a terminal verdict;
- every `source` a slot binds to resolves — the file exists and the heading is there exactly once;
- every bound slot's `rev` still matches the section's current hash — a changed section reads as
  stale;
- unless `--skip-verification`, every command under `verification.commands` actually runs from the
  project root and exits `0`.

Exit codes:

- `0` — clean.
- `1` — findings: a slot stuck in `empty` or `conflicts`, an unknown status, `not_applicable` with
  no `reason`, a stale or missing `rev` on a bound slot.
- `2` — structural failure: the contract cannot be read at all, a bound source file or heading is
  missing or ambiguous, or a verification command exited non-zero or timed out. A structural failure
  is worse than a finding — nothing else in the contract can be trusted until it is fixed.

Use `--skip-verification` when the project's own verification slot names the very command that runs
`--check` — running the commands would otherwise call the check from inside itself. Document the
project's own reason for using it rather than leaving it as a silent flag; this repository's own
`scripts/validate.sh` is the worked example.

## Starting a contract

A project with none yet copies `${CLAUDE_PLUGIN_ROOT}/templates/project/contract.yml` to
`.agent-kit/knowledge/contract.yml` — every slot ships `status: empty`, which `--check` then reports
as the state every slot starts in and must be resolved out of. `--check` against a project with no
contract at all names that same path rather than only saying the file is missing.

Fill each slot by hand: set `status`, and for a `filled` slot, `source` and its `rev`. Write the
`source` first and run `--check` — a bound slot with no `rev` yet is reported with the section's
current hash, which is the value to record. There is no `--resolve` that writes it for you until a
later version.

## Bare invocation

`/agent-kit:blueprint` with no arguments does not run an interview. Say plainly that authoring a
contract from scratch — the interview, the story pass, grading collection entries — lands in a
later version of this command, and point at the template path above as today's starting point.
