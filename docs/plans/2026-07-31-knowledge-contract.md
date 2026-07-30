# Plan — knowledge contract, the mechanical half

Spec: `docs/specs/2026-07-31-knowledge-contract-design.md`.
Brief: `.agent-kit/sprint/2026-07-31-knowledge-and-gates/02-knowledge-contract/spec.md`.
Upstream: `.agent-kit/sprint/2026-07-31-knowledge-and-gates/02-knowledge-contract/upstream.md`.

## File map

| File | Change |
|---|---|
| `plugins/agent-kit/scripts/kit_yaml.py` | new — the stdlib-only YAML-subset reader |
| `plugins/agent-kit/scripts/blueprint_check.py` | new — section resolver, hashes, slot checks, exit codes |
| `plugins/agent-kit/templates/project/contract.yml` | new — every slot, `empty`, with the comments that explain it |
| `plugins/agent-kit/skills/blueprint/SKILL.md` | new — `--check` only |
| `.agent-kit/knowledge/contract.yml` | new — this repository's own contract, honestly filled |
| `tests/test_kit_yaml.py` | new — subset, errors, round-trip against the two shipped files |
| `tests/test_blueprint_check.py` | new — exit codes, fixtures, the section-hash properties |
| `tests/fixtures/**` | new — contract trees for the cases that do not depend on a live hash |
| `plugins/agent-kit/scripts/guard.py` | the never-rules become an importable `refusal()` (Security step) |
| `tests/test_guard.py` | new — the rules, and the hook protocol nothing could reach before |
| `scripts/validate.sh` | runs both test files; stdlib-only import check; template/slot-list sync |
| `docs/developing.md` | the stdlib-only rule, under "What must never end up in the plugin" |
| `README.md`, `plugins/agent-kit/README.md` | a `blueprint` row in both tables; the count sentence |
| `CHANGELOG.md` | bullets appended to the existing `## 0.17.0` section |

## Tasks

1. **The YAML reader.** `kit_yaml.py` over the subset the spec names, with `KitYamlError(message,
   line)` for everything outside it. Verify: `tests/test_kit_yaml.py` covers each construct, the
   `#`-in-a-value case that a naive comment stripper eats, and one error per unsupported construct
   with its line number.
2. **The section resolver and the hash.** In `blueprint_check.py`: find a heading by literal text,
   take the body to the next heading of the same level or shallower, hash it. Verify: the property
   tests — random documents from a small grammar, fixed seed — assert the hash changes when and only
   when that body changes, plus the missing and ambiguous heading cases.
3. **The checks and the CLI.** Slot list, terminal verdicts, binding resolution, staleness,
   verification commands with a timeout, the design's output layout, three exit codes. Verify:
   `tests/test_blueprint_check.py` drives the script as a subprocess over the fixtures — clean 0,
   forbidden state 1, stale 1, missing source 2, missing heading 2, failing command 2 — and asserts
   a run reports everything wrong rather than the first thing.
4. **The template contract.** Every slot `empty`, commented. Verify: a copy of the template is
   checked and reports all eleven slots as needing a verdict, exit 1; a test asserts the template's
   slot ids are exactly the list in the code.
5. **`validate.sh` and the standards.** Run both test files; parse every payload `.py` for
   non-stdlib imports; the developing.md rule. Verify: the import check fails against a deliberately
   added `import yaml` and passes once removed; full `scripts/validate.sh` green.
6. **The `blueprint` command.** SKILL.md, both README tables, the count sentence. Verify:
   `scripts/validate.sh` — the frontmatter pairing, both-README coverage, and the count are all
   enforced by it since 0.17.0.
7. **This repository's contract, and the changelog.** Bind `architecture_stance` after task 5's edit
   to that document, so the `rev` is computed against the final text. Verify: `blueprint --check`
   at the repository root prints an honest summary and exits 0; the recorded output goes in the run
   log.

## Run log

**Branch:** claude/knowledge-contract
**Steps:** Build, Test, Review, Security, PR, Docs

- context — run under `--brief`: no interactive gates, autonomous from the first step. The sketch is
  the approved unit of work; `upstream.md` is read with it and its four inherited constraints
  (validator assertions, the updated "Adding a skill", spec and plan committed, `## 0.17.0` appended
  to) are carried into this plan.
- setup — `stack-playbook`'s freshness check closes on the brief's own line: there is no dependency
  manifest in this repository to fingerprint, and the registered standards are `docs/developing.md`,
  current as of the previous feature's Docs step. Nothing to refresh.
- assumption — the expansion reads the brief's "the next heading of the same level" as "the same
  level or shallower". The literal rule swallows the rest of the document when a section is nested,
  and the two agree wherever nesting is flat.
- assumption — the two contract keys the brief did not name: `commands` on `verification` (a map of
  name → shell command, the shape the design's section 2 already uses) and `sources` on a collection
  (the glob list the brief asks collections to carry).
- assumption — tests are two executable Python files under `tests/`, driven by stdlib `unittest` and
  invoked by `scripts/validate.sh`. The brief calls for "plain executable checks" on the grounds that
  there is no test framework here; `unittest` needs no framework installed and is the shape a Python
  script's tests take.
- assumption — CI does not run `--check` against this repository's own contract: that contract names
  `scripts/validate.sh`, so the build would recurse. The structural half is covered in CI through the
  module API, the command half by hand. Reasoning in the spec.
- decision — `docs/developing.md` is edited on this branch rather than in a separate docs PR, for
  the reason 01 recorded and this feature inherits: it documents a rule that exists only here, and
  five more stacked features are about to touch the same files. The stdlib-only rule went in with
  the check that enforces it rather than waiting for the Docs step, because a rule whose enforcement
  ships in a different commit is a rule nobody can date.
- step Build — done. Two commits: the reader and the check, then the command and this repository's
  own contract.
- test — nothing to provision. The repository declares one command, `scripts/validate.sh`, and the
  new test layer runs inside it (`python3 tests/test_*.py`); `python3` was already this build's only
  interpreter, so `.github/workflows/ci.yml` needs no change and there is no `cloud-setup.sh` here
  to extend.
- test — the `tester` agent wrote `tests/test_kit_yaml.py` (42) and `tests/test_blueprint_check.py`
  (48) with nine fixture contract trees, proved each behaviour can fail with 41 source mutations,
  and returned red on two real defects, both fixed here:
  a `verification` command that is not a string — the shape a half-filled template produces —
  crashed with a `TypeError` and exited 1 where the contract says 2; and a heading ending in `#`
  (`## Why C#`) could not be bound at all, because the closing-sequence pattern ate the character.
- deviation — `|+` block scalars are now refused by name instead of being read as clip. The reader's
  own contract is that anything outside the subset is reported rather than guessed at, and returning
  a silently wrong value is the one outcome it exists to prevent. One test the tester left
  deliberately agnostic was rewritten to assert the refusal.
- note — a test asserts this repository's own contract is structurally sound *and fresh*, so editing
  the section of `docs/developing.md` that `architecture_stance` binds to fails the build until the
  `rev` is updated. That is the contract doing its job on the repository that ships it; the failure
  renders the whole check report, including the new hash to paste in.
- step Test — done. `scripts/validate.sh` green: 114 tests, plus manifests, frontmatter, references,
  payload syntax, the new stdlib-only import check, and `claude plugin validate --strict`. The
  runnable surface is the check itself, exercised against this repository's real documents: clean
  exits 0; editing the bound section reports it stale with both hashes; editing a different section
  of the same file stays clean; renaming the bound heading is reported as a missing section, exit 2.
- review — the `code-review` plugin is enabled here, so the `reviewer` agent carried the
  design-conformance question alone and the bug hunt goes to the PR step. Its verdict: this is the
  feature that was approved — every "Done means" bullet true, nothing from "Out" present, the four
  constraints from `upstream.md` met, `VERSION` / `plugin.json` / `marketplace.json` untouched. It
  raised nineteen findings; three major, and those are fixed:
  `validate.sh`'s new test step passed vacuously when the glob matched nothing (it now counts the
  files first and fails on zero); the test written for the crashing-command defect asserted only a
  non-zero exit, so a return to exit 1 would have passed it; and an apostrophe in a plain scalar —
  `criterion: the owner's rules` — opened a quote that never closed, so a trailing comment was read
  into the value silently, which is the one outcome the reader's own contract forbids.
- review — fixed alongside them: a bound document that cannot be read no longer escapes as a
  traceback; the template ships a `reason` placeholder on every slot, not only the first; the
  `deferred_seams` and `architecture_stance` entries in this repository's contract say more exactly
  what they claim; three sentences in the spec that the implementation had outgrown; two
  documentation lines the diff had made stale.
- deviation — the property test the reviewer asked for (lines added and removed, not only edited in
  place) found a genuine collision: joined without terminators, a section holding one blank line and
  a section holding nothing hash the same. Section bodies now keep each line's terminator, which is
  what the file has. That changes every recorded `rev`, so this repository's contract and the
  fixtures were recomputed.
- review, deliberately not acted on — `open_question` on `north_star` is a stretched reading of "a
  known unknown", and the alternative was to give the README's opening paragraphs a heading purely
  so a slot could bind to them; the contract's own comment explains the gap instead. The template
  still has no automatic path into a project: bootstrap does not copy it, because the interview that
  owns that file is stage 7 and the brief's scope does not include wiring it — `--check` says where
  the template is and the command offers to copy it. A usage error exits 2, the same code stage 6
  will read as structural; recorded rather than changed, since inventing a fourth code to
  distinguish a typo from a broken contract buys nothing yet.
- step Review — done.
- security — `/security-review` over the branch diff, with an adversarial pass in a fresh context.
  One high finding, and it is the one the brief's settled decision creates: `--check` executes shell
  commands taken verbatim from a file that lives in the repository being checked, and a contract can
  arrive in a pull request. Running the project's own commands is not new — every pipeline here runs
  the project's declared suite — but running them from inside a script is: a `PreToolUse` hook fires
  on tool calls, not on a subprocess, so `guard.sh`'s never-rules were not being applied to them.
  A contract naming `gh pr merge --admin` or `git push --force origin main` would have routed around
  the one mechanism the kit enforces mechanically.
- security — fixed by moving the decision rather than duplicating it: `guard.py`'s rules become an
  importable `refusal()`, the hook asks as before, and the check refuses without running. Every
  command is printed before it runs. A `source` or glob resolving outside the project root is now a
  structural failure — it was a working existence-and-hash oracle over any absolute path. A contract
  that breaks the checker in a way nobody enumerated now exits 2 rather than 1 through a traceback,
  which matters because 1 is the code that means "findings, act on them". `tests/test_guard.py` is
  new: the hook had no tests, and restructuring load-bearing code without them is how a hook stops
  firing quietly. Writing the path-confinement test also turned up a real defect of its own — an
  all-digit `rev` parsed as an integer and could never equal its own hexdigest, so roughly one slot
  in two hundred could never come clean.
- security, deliberately not changed — on a repository the owner does not control, `--check` still
  runs that repository's declared commands. That is the settled decision, and the policy about
  untrusted repositories belongs to stage 6, which is what puts this in front of every build
  command; inventing one here would be inventing a stage this feature is not. Recorded in the spec
  and in the skill, which now tells the reader to read the `verification` block first on a
  repository they do not control, and not to paste a failing command's output anywhere without
  reading it — that tail is where a token would be.
- step Security — done.
- pr — PR #13, draft against `claude/command-cleanup`, CI (`validate`) green on the first run.
- note — the `code-review` plugin's own eligibility check refuses to review a draft, and the kit's
  pull-request rule *requires* a stacked sprint feature to be a draft. Left alone, those two rules
  cancel each other and every stacked feature silently loses its PR-step review. The fan was run
  deliberately instead. Worth the owner's attention: this affects all five features still queued
  behind this one, not just this run.
- pr — that pass found five real defects, all fixed, all now covered by tests that fail without the
  fix. Four are one class — the reader returning a silently wrong value, which is the single
  outcome its own contract exists to prevent: a `rev` of all digits with a leading zero came back
  as a number, so a slot whose hash happened to look like one was stale for ever and copying the
  printed hash back in did not help (found independently by two reviewers, and *my own* comment
  claimed the earlier `str()` cast had covered it); a line dedented one space out of a block scalar
  was swallowed into the prose above it, so a `status: filled` edit vanished and the check reported
  the contract clean; `|2` was read as the two-character string `"|2"`; an unknown escape in a
  double-quoted scalar dropped its backslash, turning `"C:\Users"` into `C:Users`. The fifth is in
  the section resolver: a fence was matched on three characters, so a document that shows how to
  nest code fences closed the outer one early and read the example's own `#` line as a heading,
  truncating the section and hashing something nobody would call that section.
- note — the first end-to-end test written for the leading-zero `rev` passed against the bug,
  because the hash it happened to use was not all digits. The body in it now is one whose section
  hash really is `031657175672`, found by search, so the case is exercised rather than described.
- step PR — done. PR #13, draft (a stacked feature cannot land code), CI green on the first run and
  again after the review round's fixes. The round's outcome is posted on the pull request.
- docs — `docs-reflection` found one divergence beyond what the Build step had already corrected:
  the root README's layout block described `scripts/` as session start, cloud setup and the guard,
  which is no longer all of it. Fixed here. `docs/developing.md` was updated on this branch with
  the change that caused it — the same deviation feature 01 recorded and this one inherits, since a
  docs PR cut from `main` would describe a validator `main` does not have.
- docs — deliberately not touched: `docs/design/knowledge-and-gates.md` still opens "proposed, not
  implemented". On `main` that is still true, and this branch is one of six stacked features that
  have not landed. Rewriting it here would make a claim about work the default branch does not
  have; it belongs to whoever merges the sprint's integration pull request.
- docs — no screen map in this repository (`manifest.sources.screens` is null), so the Docs step's
  map update does not apply.
- step Docs — done.
