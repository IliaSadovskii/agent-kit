# Knowledge contract — the mechanical half

Expanded from the owner-approved brief at
`.agent-kit/sprint/2026-07-31-knowledge-and-gates/02-knowledge-contract/spec.md`, stage 1 of
`docs/design/knowledge-and-gates.md`. Depth: normal. Run under `--brief`, so this expansion settles
what the brief left open and records nothing the brief already decided.

## What ships

A project gains one file it can be held to — `.agent-kit/knowledge/contract.yml` — and one command
that answers yes or no about it in seconds:

```text
.agent-kit/knowledge/contract.yml     human decisions: slot status, source binding, criteria
                  ↑
   /agent-kit:blueprint --check       every slot has a terminal verdict
                                      every source path resolves
                                      every bound section hash still matches
                                      every verification command runs and returns 0
```

Five pieces: the shared YAML reader, the check script, the template contract a project starts from,
this repository's own honestly-filled contract, and a deliberately thin `blueprint` command that
supports only `--check`.

## The contract file

Two top-level maps, because the design distinguishes the two kinds of slot and its own sample output
reports them on separate lines:

```yaml
version: 1

slots:                          # one answer per project
  architecture_stance:
    status: filled
    source: docs/developing.md#What must never end up in the plugin
    rev: 4d3a1f0c9b22
    criterion: >-
      the rules that decide where a change belongs …

  verification:
    status: filled
    commands:
      validate: scripts/validate.sh
    criterion: every command runs from the project root and exits 0

  scenarios:
    status: not_applicable
    reason: >-
      the kit has no product data to walk a scenario over …

collections:                    # one entry per instance; entries are stage 2
  integrations:
    status: filled
    sources:
      - plugins/agent-kit/README.md
```

Keys inside a slot are the brief's defaults — `status`, `source`, `rev`, `reason`, `criterion` — plus
`commands` on `verification` and `sources` on a collection. `commands` is a map of name → shell
command, which is the shape section 2 of the design already uses (`test: make test`) and what
stage 4's `${test}` interpolation will read: this slot is the single point where the knowledge
contract meets the step gate.

The slot list is fixed by the kit version, in code: six singular slots — `north_star`,
`architecture_stance`, `verification`, `mvp_bounds`, `scenarios`, `deferred_seams` — and five
collections — `actors`, `entities`, `actions`, `screens`, `integrations`. A slot the contract omits
is reported exactly like an `empty` one, which is decision 7 of the design's section 8: a slot added
by a later kit version shows up as needing a verdict rather than silently not existing.

## Section binding and staleness

A `source` is `path#heading`, where the fragment is the heading's literal text. The hash covers the
section **body**: everything after the heading line up to the next heading of the same level *or
shallower*, or the end of the file.

The brief says "the next heading of the same level", which is the right rule for a flat document and
wrong for a nested one — the last `###` inside a `## Section` would otherwise run past the next `##`
and swallow half the file. "Same level or shallower" is identical in the flat case and correct in the
nested one, so that is what ships. The invariant the property tests state is unchanged: **a section's
hash changes when and only when the text between its heading and its boundary changes.**

The body is hashed as `sha256`, truncated to twelve hex characters. Nothing in it is normalized
except line endings, so the invariant holds literally over the text and a CRLF checkout does not
make every binding in the project stale at once. A renamed or deleted heading is a *missing section*, reported as such;
stage 2's anchors are what will fix that, and until then it is an honest limitation rather than a
silent one. A heading text that appears twice in one file is an **ambiguous** binding and is reported
too: the kit cannot tell which of them the slot meant, and picking the first would be a guess.

## Exit codes and what lands in each

The brief settles three codes; this is the assignment of each condition to one of them.

| Exit | Meaning | Conditions |
|---|---|---|
| `0` | clean | every slot has a terminal verdict, every binding fresh, every command exits 0 |
| `1` | findings | `empty`, `conflicts`, or a missing slot; `not_applicable` with no reason; a `filled` slot with a source but no `rev`; a stale section |
| `2` | structural | the contract is missing or outside the reader's subset; a source path or glob resolves to nothing; a bound heading is missing or ambiguous; a `verification` command exits non-zero or times out |

Structural wins over findings: a run that cannot read its own inputs has nothing to say about them.
Both are reported in full before exiting — one run of `--check` shows everything wrong, not the first
thing wrong.

`open_question` is a terminal verdict and therefore clean. It is counted in the summary and never
listed as a finding: the bar is a deliberate verdict, not a full slot.

## The YAML reader

`plugins/agent-kit/scripts/kit_yaml.py`, stdlib only, imported by path the way a sibling module is —
the check script's own directory is already on `sys.path` when Python runs it.

The subset is defined by what the kit's own files use: nested maps by indentation, lists of scalars
and lists of maps, plain and quoted scalars, `null` / `true` / `false` / integers / floats, comments,
literal (`|`) and folded (`>`) block scalars with the `-` chomping variant, and empty flow
collections (`[]`, `{}`). Everything else — anchors, aliases, non-empty flow collections, multiple
documents, tabs for indentation — raises an error naming the construct and the line, which `--check`
prints instead of guessing.

One detail decides whether the reader is usable at all here: `#` starts a comment only at the start
of a line or after whitespace. A `source:` value is `docs/developing.md#What must never end up in
the plugin`, and a reader that treats every `#` as a comment eats the binding.

The reader is a reader, not a writer. The two files this feature ships are written by hand in the
subset, and a round-trip test reads both back and asserts the values are what the file says.

## The check script

`plugins/agent-kit/scripts/blueprint_check.py`, importable as well as runnable, because
`scripts/validate.sh` uses the module directly for the one thing it cannot do by running the command
— see below. It reads `.agent-kit/knowledge/contract.yml` relative to the working directory and runs
verification commands from that same directory, with a five-minute per-command timeout so a wedged
command fails loudly rather than hanging the gate stage 6 will put in front of every build command.

Output follows the design's sample: a summary line per category, a line per verification command
that ran, then one block per finding, then a `stale` line. Nothing else — no progress, no banner, no
audit trail of what was fine. It never calls a grader and it never writes anything.

## The trust boundary around the verification slot

`verification` is proven by running it — settled, and the point where this contract meets the step
gate two stages from now. What the brief did not consider is that the contract is a file *in the
repository*, so its commands can arrive in a pull request from someone else.

Running the project's own commands is not a new capability: every pipeline here already runs the
project's declared suite. What is new is that these run from inside a script, and a `PreToolUse`
hook fires on tool calls, not on a subprocess a script starts — so the kit's never-rules, which
`guard.sh` turns into a confirmation everywhere else, would not be applied. Three limits close that:

- the decision in `guard.py` becomes an importable `refusal()`, and the check refuses — without
  running it — any command the hook would have asked about. The hook asks; a caller with nobody to
  ask refuses;
- every command is printed before it runs, so what a command did never reaches the reader ahead of
  what the command was;
- a `source` or a `sources` glob that resolves outside the project root is a structural failure.
  Bindings name documents in this repository, and a contract is not a way to read `~/.ssh` or to
  ask whether a path exists.

What remains is deliberate and belongs in the pull request rather than in a guard: on a repository
the owner does not control, `--check` runs that repository's commands. Stage 6, which puts this in
front of every build command, is where a policy about untrusted repositories belongs; inventing one
here would be inventing a stage this feature is not.

## Why CI does not run `--check` on this repository

The repository's own `verification` slot names `scripts/validate.sh`, which is the entire declared
test command. If `validate.sh` ran `--check`, `--check` would run `validate.sh`, and the build would
recurse until something ran out.

So CI covers the machinery through fixtures whose commands are `true` and `false`, and covers *this
repository's* contract by importing the check module and asserting the structural half — every slot
has a terminal verdict, every source resolves, every `rev` matches — without running any command.
The full command, verification included, is run by hand and its output recorded in the run log. No
flag is invented to break the cycle; the module API already draws the line in the right place.

## Enforcing stdlib-only

"No script the kit ships imports anything outside the standard library" is a claim in the brief's
*Done means*, and a claim in a document is not a check. `validate.sh` gains one: every `.py` under
the payload is parsed with `ast`, and each imported top-level module must be in
`sys.stdlib_module_names` or be a sibling module shipped beside it. A hook that dies on `ImportError`
on someone else's machine takes the whole kit down with it, so the rule is also written into
`docs/developing.md` under "What must never end up in the plugin", where the kit's other
payload-boundary rules live.

## The blueprint command

`plugins/agent-kit/skills/blueprint/SKILL.md`, `disable-model-invocation: true`, one mode. `--check`
runs the script and reads its output back to the owner. A bare invocation says plainly that the
interview lands in a later version and offers `--check`; it does not improvise an interview. A
project with no contract yet is told where the template is, and the command offers to copy it in —
on an explicit yes, and with every slot arriving `empty`. What this feature never does is write to
the owner's prose documents, or put a verdict in a slot on their behalf: `--check` itself writes
nothing at all, and the two edits the skill may offer — a stale `rev`, and a binding that has none —
are the mechanical ones whose answer is already in the report.

It joins the command table in both READMEs, and the storefront's count sentence goes from six to
seven.

## Out

No grader, no anchors, no `index.yml`, no collection entries, no cross-checks (stage 2). No
annotations and no `--resolve` (stage 5). No gate in front of any other command (stage 6). `docs`
stays a command of its own; there is nothing to absorb it into until blueprint has an interview.
