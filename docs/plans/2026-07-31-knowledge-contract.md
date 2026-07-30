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
