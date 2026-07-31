# Plan — knowledge contract, the mechanical half

Spec: [docs/specs/2026-07-31-knowledge-contract-design.md](../specs/2026-07-31-knowledge-contract-design.md).
The spec says what is being built and what done means; its "Run expansion" section carries the
mechanics this stage settled. This file is the task list, its verification, and the run's log.

## Tasks

### 1. `kit_yaml.py` — the shared reader

`plugins/agent-kit/scripts/kit_yaml.py`: `load(text, path)` → nested `dict`/`list`/scalars, stdlib
only. Subset: block maps, block lists of scalars, plain and quoted scalars, `null`/`true`/`false`/
integers, comments, blank lines. Anything outside it raises `KitYamlError` naming the construct and
the line. Indentation is spaces; a tab is an error with its own message.

*Verify:* task 7's `tests/test_kit_yaml.py`.

### 2. `kit_markdown.py` — sections and hashes

`plugins/agent-kit/scripts/kit_markdown.py`: `sections(text)` → an ordered list of
`(level, title, body)`, skipping fenced code blocks; `section(text, title)` returning one section or
raising `MissingSection` / `AmbiguousSection`; `rev(body)` → first 12 hex of `sha256` over the body
with per-line trailing whitespace and trailing blank lines stripped. A section ends at the next
heading of the same or higher level.

*Verify:* task 7's `tests/test_kit_markdown.py`, including the property layer.

### 3. `knowledge_check.py` — the check

`plugins/agent-kit/scripts/knowledge_check.py`, executable, `python3` shebang, imports the two
modules from its own directory. Flags `--root <dir>` (default `.`) and `--skip-verification`. Reads
`<root>/.agent-kit/knowledge/contract.yml` and, per the spec:

- every slot and collection has a terminal verdict — `empty` and `conflicts` are findings, an
  unknown status is a finding, `not_applicable` without a `reason` is a finding;
- every `source` resolves: a missing file or an unreadable contract is structural, a missing or
  ambiguous heading is structural;
- every binding carries a `rev` and it still matches — a mismatch is a finding, a missing `rev` on a
  bound slot is a finding;
- unless `--skip-verification`, every command under `verification.commands` runs from `<root>` with
  a timeout and must exit `0`; a non-zero exit or a timeout is structural.

Output follows the design's "Sample check output": a `slots` summary line, a `collections` line, one
`⚠` block per finding with the slot name and what is wrong, and a `stale` line. Exit `0` clean, `1`
findings, `2` structural.

*Verify:* task 7's `tests/test_knowledge_check.py` over fixtures — every exit code, the
stale/fresh distinction, and the failing command.

### 4. The template contract

`plugins/agent-kit/templates/project/contract.yml`: `version: 1`, `slots:` with `north_star`,
`architecture_stance`, `verification`, `mvp_bounds`, `scenarios`, `deferred_seams`, `collections:`
with `actors`, `entities`, `actions`, `screens`, `integrations`. Every one `status: empty` with the
other keys present and null, and a header comment saying what the file is, that `empty` is not a
terminal state, and which three states are.

*Verify:* `--check` against a fixture holding only this template reports every slot and collection
as needing a verdict and exits `1`; the reader in task 1 parses it.

### 5. This repository's own contract

`.agent-kit/knowledge/contract.yml`, honestly filled:

- `verification` — `filled`, bound to `docs/developing.md#Testing a change`,
  `commands: [scripts/validate.sh]`;
- `architecture_stance` — `filled`, bound to `docs/developing.md#Repository layout`;
- `deferred_seams` — `filled`, bound to `docs/design/knowledge-and-gates.md#9. Order of work`;
- `north_star` — `open_question` with the reason from the spec's Run expansion;
- `mvp_bounds`, `scenarios` and all five collections — `not_applicable`, each with a reason that
  says why a plugin has no such thing. Nothing is invented to fill a slot.

*Verify:* `python3 plugins/agent-kit/scripts/knowledge_check.py` prints the summary and exits `0`.

### 6. `blueprint` — the command

`plugins/agent-kit/skills/blueprint/SKILL.md`: frontmatter with `disable-model-invocation: true` and
`argument-hint: --check`; body covers what the contract is, `--check` (how to run it, the three exit
codes, what each finding means, `--skip-verification` and why it exists), how a project starts one
from the template, and one line saying the interview and the grader land in a later version. A bare
invocation says exactly that rather than improvising an interview.

Rows in `plugins/agent-kit/README.md` and `README.md` command tables. The skill lands before the
rows — the validator fails a `/agent-kit:blueprint` reference in a Markdown file until the skill
exists.

*Verify:* `scripts/validate.sh` — command set against both directions of the README table, skill
frontmatter, and the dead-reference check.

### 7. The tests and the suite

`tests/` — stdlib `unittest`:

- `test_kit_yaml.py`: the subset, the error messages by line, and reading back every YAML file the
  kit owns (both manifests, both contracts).
- `test_kit_markdown.py`: boundaries, fenced-code headings, missing and ambiguous headings, and the
  property layer — random documents over fixed seeds, asserting a section's hash changes when and
  only when that section's text changes.
- `test_knowledge_check.py`: fixture projects under `tests/fixtures/` — clean (`0`), a slot left
  `empty` (`1`), a `conflicts` slot (`1`), an edited bound section (`1`), an edit to a *different*
  section of the same file (`0`), a renamed heading (`2`), a missing source file (`2`), an
  unparseable contract (`2`), a verification command that exits non-zero (`2`), and the template
  contract (`1`).

`scripts/validate.sh`: a new step running `python3 -m unittest discover -s tests -t .`, plus the
repository's own contract through `knowledge_check.py --skip-verification` — the flag is what keeps
the suite from calling itself.

*Verify:* `scripts/validate.sh` green; each new test seen failing once against the defect it
describes before it is trusted.

### 8. Changelog

Bullets appended to the existing `## 0.18.0` section of `CHANGELOG.md`. No migration note: this
feature adds a command and a template and asks nothing of an owner who already installed the kit.

*Verify:* `scripts/validate.sh`.

## Run log

**Branch:** claude/knowledge-contract
**Steps:** Gate, Design, Plan

- step Gate — done: technical setup present (`.agent-kit/project/manifest.yml`, `language: ru`,
  `coding_standards: docs/developing.md`); no project interview run and no `instructions.md`
  created, per the batch orientation. Product bootstrap is `bootstrapped: false` **with** a supplied
  brief, so the run proceeds — and the pull request owes the owner the standing warning: this
  repository records no product idea or roadmap, so task selection and product scoping are
  unavailable and every autonomous default is judged against the code rather than a stated intent.
  `stack-playbook` freshness: current by inspection — there is no dependency manifest to fingerprint
  here, and the registered standards are `docs/developing.md`, read for "Adding a skill",
  "Testing a change" and "What must never end up in the plugin".
- step Design — done: the sketch is copied to `docs/specs/2026-07-31-knowledge-contract-design.md`
  with a "Run expansion" section recording three deviations and the settled mechanics. The
  deviations in short: (a) the release is **0.18.0**, not 0.17.0, and this feature owes no migration
  note; (b) the command set is derived from frontmatter now, and the validator's dead-reference check
  forbids naming `/agent-kit:blueprint` in any `*.md` until the skill exists, which orders task 6;
  (c) this repository's `north_star` is a recorded `open_question` rather than a binding, because the
  README's intro has no heading of its own and binding it would cover the whole file — the opposite
  of what section-level staleness is for.
- step Plan — done: this file.

### What later stages need from here

- **Language.** Code, identifiers, paths, commit messages and everything under `docs/` and
  `plugins/` are English; the pull request description is Russian (`manifest.language: ru`).
- **The declared suite is `scripts/validate.sh`, and it is the whole of it.** CI runs the same
  script (`.github/workflows/ci.yml`), so the new `tests/` step reaches CI by being added there and
  nowhere else. There is no runnable app surface in this repository — the Test step's "confirm
  against the running app" is a named skip, not an omission.
- **The heavy verification layer this feature earns is the property layer on the section resolver
  and the hash**, named by the spec and planned in task 7. It is part of the build stage's work, not
  optional.
- **The base branch for `agent-kit:reviewer` is `claude/command-cleanup`** — feature 2 of 7 in a
  linear stack. Diffing against `main` would review feature 01 again.
- **The PR must end as a draft.** It is a stacked feature in a sprint; the conversion is the
  `deliver` stage's last action.
- **Do not bump `VERSION`, `plugin.json` or `marketplace.json`.** `scripts/release.sh` owns those
  and the validator checks they agree with the `## <VERSION>` changelog heading; a bump inside a
  feature branch breaks the validator for every other branch in the stack.
- **Docs divergence already known to the Docs step:** `docs/developing.md` "Repository layout" does
  not mention `plugins/agent-kit/scripts/`' new modules or the new top-level `tests/`, and
  "Testing a change" does not mention the new validate step. Note that "Repository layout" is the
  section this repository's `architecture_stance` binds to — editing it means updating the slot's
  `rev` in the same commit, or `scripts/validate.sh` fails. That is the mechanism working, not a
  defect.
