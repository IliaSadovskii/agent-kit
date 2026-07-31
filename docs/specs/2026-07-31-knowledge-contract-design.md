# 02 · Knowledge contract — the mechanical half

Owner-approved design sketch for a `ship --brief` run. What is settled here is settled; what is
left open becomes the run's logged assumptions. Depth agreed at the brief: **normal**.

## Context: this repository is the kit itself

The working repo is the agent-kit **plugin source**, not a bootstrapped agent-kit project.
`.agent-kit/project/manifest.yml` exists and records `language: ru`, `bootstrapped: false`, and
`coding_standards: docs/developing.md`; there is no `instructions.md`. Do not run the project
interview and do not create one.

`stack-playbook`'s freshness check closes on a single line: there is no dependency manifest to
fingerprint here, and the registered standards are `docs/developing.md`. Follow its
"Adding a skill" procedure. `scripts/validate.sh` is this repository's entire declared test command
and must stay green.

Code, identifiers, paths, commit messages, and every document under `docs/` are English. The pull
request description is Russian (`manifest.language: ru`).

The full design this batch implements is `docs/design/knowledge-and-gates.md` — read section 3 and
section 9's stage 1. This feature is **stage 1**. Section 8's decided list is closed; do not
re-litigate it.

## Batch position

Feature 2 of 7 in a strictly linear stack. Base branch: `claude/command-cleanup`, which has already
turned `debug`, `address`, and `screens-riff` into internal skills. Read `upstream.md` next to this
spec if it exists — it records what actually happened upstream, against which this sketch was
written from imagination.

Append this feature's bullets to the existing `## 0.17.0` section in `CHANGELOG.md`. **Do not bump
`VERSION`, `plugin.json`, or `marketplace.json`.** Add a note to `migrations/0.17.0.md` only if this
feature requires action from an owner who already installed the kit.

## Goal

Give the kit a knowledge contract it can check mechanically: a slot list with deliberate verdicts, a
binding from each slot to the prose that answers it, and a `--check` that detects staleness and
proves the project's verification commands actually run.

## Shape

```
.agent-kit/knowledge/contract.yml     human decisions: slot status, source binding, criteria
                    ↑
     /agent-kit:blueprint --check      seconds, no grader:
                                         · every slot has a terminal verdict
                                         · every source path resolves
                                         · every bound section hash still matches
                                         · every verification command runs and returns 0
```

## Scope

In:

- `.agent-kit/knowledge/contract.yml` **for this repository**, honestly filled. `verification` is
  `filled` and names `scripts/validate.sh` — the one slot here whose readiness is proven by running
  the command. `architecture_stance` binds to a section of `docs/developing.md`. The product slots
  are `not_applicable` with the reason recorded: this is a plugin, not a product with a domain
  model. Nothing is invented to make a slot look full — an invented answer is worse than a gap.
- `plugins/agent-kit/templates/project/contract.yml` — the template a project starts from, every
  slot present and `empty`, which `--check` reports as the state that must be resolved.
- A stdlib-only YAML reader shared by the kit's scripts (see "Settled decisions").
- The check itself, as a plugin script under `plugins/agent-kit/scripts/`.
- `plugins/agent-kit/skills/blueprint/SKILL.md` — a new, deliberately thin command supporting only
  `--check`. A bare invocation says plainly that the interview lands in a later version. It joins
  the command tables in both READMEs.
- The full slot list, singular and collection alike, so the file's shape does not change between
  this feature and the next: `north_star`, `architecture_stance`, `verification`, `mvp_bounds`,
  `scenarios`, `deferred_seams`, and the five collections `actors`, `entities`, `actions`,
  `screens`, `integrations`. Collections carry status and source globs only here; their entries,
  anchors, index, and grading are stage 2's work.

Out:

- No grader, no anchors, no `index.yml`, no collection entries, no cross-checks — all stage 2.
- No annotations, no `--resolve` — stage 5.
- No gate in front of other commands — stage 6.
- The kit does not write to the owner's documents in this feature at all.

## Settled decisions

- **Slot statuses.** Three terminal states: `filled`, `not_applicable` (with a reason),
  `open_question`. `empty` and `conflicts` are forbidden as terminal states — `--check` reports
  them as findings. The bar is "every slot has a deliberate verdict", not "every slot is filled".
- **Parsing is stdlib only.** No PyYAML, no third-party import anywhere in the kit's scripts. Write
  one small shared YAML-subset reader in `plugins/agent-kit/scripts/` covering what the kit's own
  files use — nested maps, lists, scalars, comments — and have the kit write the machine-owned
  files in that same subset. `guard.py` and `stop-guard.py` are zero-dependency today and every
  script this batch adds stays that way; a hook that dies on `ImportError` on someone else's machine
  takes the whole kit with it. When the reader meets something outside its subset, `--check` says so
  by name and line rather than guessing.
- **Staleness is per section, not per file.** A slot binds to `file#heading`, and the hash covers
  the text from that heading to the next heading of the same level. Whole-file hashing would make
  every slot bound to a large document stale on any edit, and a signal that is always on is a signal
  nobody reads. This is also the machinery stage 2 needs as its fallback when an owner refuses
  anchors, so it is written once here.
- **A renamed heading reads as a missing section**, and `--check` reports it that way. Stage 2's
  anchors are what fix that; until then it is an honest limitation, not a silent one.
- **`--check` never calls a grader.** It is the cheap, mechanical, non-interactive mode that stage 6
  puts in front of every build command, so it must cost seconds. It reports what needs a grader —
  "3 entries stale" — and stops there.
- **Three exit codes**, which stage 6's policy is built on:
  - `0` — clean;
  - `1` — findings (a slot in a forbidden state, a stale section, an unresolved binding);
  - `2` — structural failure (the contract cannot be read, a source file is gone, a `verification`
    command exits non-zero).
- **`verification` is proven by running it**, not by reading it. That is the one slot whose
  readiness criterion is mechanical today, and it is the point where this contract meets the step
  gate two features from now.

## Left to the run

- Which document and heading each of this repository's own `filled` slots binds to — default: what
  `docs/developing.md` and `README.md` actually contain; bind only where the prose genuinely answers
  the slot, and mark the rest `not_applicable` with a reason.
- The exact YAML key names inside a slot — default: `status`, `source`, `rev`, `reason`,
  `criterion`, following the design's own examples.
- The layout of `--check` output — default: the sample in the design's section 3, "Sample check
  output".
- Where the shared YAML reader lives and what it is called — default: a module beside the other
  scripts, imported by path the way the existing scripts are invoked.

## Done means

- `blueprint --check` run in this repository prints an honest summary and exits `0`.
- Editing the section of `docs/developing.md` that `architecture_stance` binds to makes the next
  `--check` report that slot stale and exit `1`; editing a *different* section of the same file
  does not.
- Deleting or renaming a bound heading is reported as a missing section, exit `2`.
- A slot set to `empty` or `conflicts` is reported as a finding, exit `1`.
- A `verification` entry whose command exits non-zero is caught by *running* it, exit `2` — proven
  by pointing a fixture contract at a deliberately failing command.
- The template contract ships every slot the design names, and `--check` against a project that has
  only the template reports every slot as needing a verdict.
- No script the kit ships imports anything outside the standard library.

## Verification

- The check script needs its own executable tests invoked from `scripts/validate.sh`; there is no
  test framework in this repository, so plain executable checks are the right shape. Cover the exit
  codes, the stale/fresh section distinction, and the failing-verification-command case with
  fixture contracts under a test directory.
- **Property-based tests on the section resolver and the hash** — this is where the parsing and the
  invariants are, and an unattended run can afford them. The invariant worth stating: a section's
  hash changes when and only when the text between its heading and the next heading of the same
  level changes.
- Round-trip tests on the YAML reader against the kit's own files: everything the kit writes, the
  kit reads back identically.
- No runnable app surface. Say so rather than skipping the check in silence.

---

## Run expansion

Written by the `design` stage of the `ship --brief` run. The sketch above is the owner's approved
record and is unchanged; this section records what exploration settled beyond it and where it
deviates.

### Deviations from the sketch

1. **The release is 0.18.0, not 0.17.0.** v0.17.0 shipped after the sketches were written. Bullets
   go into the existing `## 0.18.0` section of `CHANGELOG.md`; `migrations/0.18.0.md` exists. No
   migration note is owed by this feature — it adds a command and a template and asks nothing of an
   owner who already installed the kit.
2. **The command set is derived from frontmatter now** (feature 01 rewrote `scripts/validate.sh`).
   `blueprint` needs `disable-model-invocation: true` plus a row in `plugins/agent-kit/README.md`;
   the root `README.md` table is a convention, not a validator rule, and gets the row too. The
   validator's new dead-link check means `/agent-kit:blueprint` may not be written into any `*.md`
   outside `CHANGELOG.md`, `migrations/`, `docs/specs/`, `docs/plans/`, `docs/design/` and
   `.agent-kit/sprint/` until the skill exists — so the skill lands before the READMEs do.
3. **`north_star` for this repository is `open_question`, not a binding.** The kit's purpose is the
   README's intro, which sits under `# agent-kit` and has no heading of its own; binding to that
   heading would cover the whole file, and section-level staleness rather than file-level staleness
   is the entire point of the mechanism. Recording it as a deliberate `open_question` with that
   reason is the honest verdict the contract asks for, and stage 2's anchors are what give it a real
   binding. Binding it anyway would also have made every feature in this stack — each of which edits
   the root README's command table — report the slot stale.

### Settled mechanics

- **Three modules under `plugins/agent-kit/scripts/`, stdlib only.** `kit_yaml.py` (the YAML-subset
  reader), `kit_markdown.py` (section resolution and hashing — stage 2 needs it as its
  anchor fallback, so it is its own module from the start), and `knowledge_check.py` (the check).
  Underscored names because two of the three are imported; the hyphenated `guard.py`/`stop-guard.py`
  are hook payloads invoked through a `.sh` wrapper and are never imported. `knowledge_check.py` is
  executable and invoked as `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/knowledge_check.py`; it adds
  its own directory to `sys.path` to reach the other two, which is how a script with no package
  around it imports its neighbours.
- **Two flags: `--root <dir>` and `--skip-verification`.** The contract is always
  `<root>/.agent-kit/knowledge/contract.yml` and every source path in it resolves against `<root>`,
  so a fixture is a directory shaped like a project and the check needs no second path argument.
- **`--skip-verification` exists because this repository's `verification` slot names
  `scripts/validate.sh`, and `scripts/validate.sh` runs the check.** Without the flag the two would
  call each other forever. The flag is what lets a project's own suite hold its contract fresh — the
  mechanical half of the check is what CI can afford on every push, and running the verification
  commands is what the suite is already doing by existing. Documented in the skill and in
  `docs/developing.md` rather than left as a private option.
- **The section a binding names ends at the next heading of the same *or higher* level.** The
  sketch's "same level" is the same rule for a well-formed document and differs only where a deeper
  section is followed by a shallower heading, where ending at the same level would swallow the rest
  of the file. Headings inside fenced code blocks are not headings. A heading text that appears
  twice in one file is an ambiguous binding and is reported as a structural failure (exit `2`)
  rather than silently resolved to the first match.
- **`rev` is `sha256` of the section text, first 12 hex characters**, over the text from the line
  after the heading to the line before the next heading, with trailing whitespace stripped per line
  and trailing blank lines dropped — so a reflowed trailing newline is not a staleness event but any
  edit to the words is.
- **Contract shape:** a top-level `version: 1`, a `slots:` map for the six singular slots, and a
  `collections:` map for the five collections. Slot keys are `status`, `source`, `rev`, `reason`,
  `criterion`, plus `commands` on `verification`; a collection carries `status`, `reason` and
  `sources` (globs) only, its entries being stage 2's work. Two blocks rather than one flat map so
  that stage 2 can add `entries:` under a collection without moving anything.
- **The YAML reader's subset is what the kit's own files use:** nested block maps, block lists of
  scalars, plain and quoted scalars, `null`/`true`/`false`/integers, comments, blank lines. Anything
  else — flow collections, block scalars, anchors, aliases, multiple documents — is reported by name
  and line rather than guessed at. Round-trip in this feature means *read back*: the reader parses
  every YAML file the kit owns (`templates/project/manifest.yml`, the new contract template, this
  repository's own manifest and contract) without reaching its unsupported path. No writer is
  written here — nothing in this feature writes YAML, and a dumper with no caller is a maintenance
  cost stage 2 can pay when it has one.
- **The template contract ships but nothing copies it yet.** `idea-interview` is not rewired: the
  sketch puts every write outside this feature. `blueprint` with no arguments, and `--check` against
  a project with no contract, both name the template path and say to copy it.

### Verification, as planned

`tests/` is new in this repository. Stdlib `unittest`, discovered from `scripts/validate.sh` as a
new step, so CI runs it unchanged. Fixtures are directories under `tests/fixtures/` shaped like
projects. The property-based layer the sketch asks for is hand-rolled over `random` with fixed
seeds — there is no dependency manifest here and no third-party import is permitted — and states the
invariant the sketch names: a section's hash changes when and only when the text of that section
changes.
