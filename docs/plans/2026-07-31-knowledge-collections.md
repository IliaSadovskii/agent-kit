# Plan — collections, anchors, the derived index, and cross-checks

Spec: `docs/specs/2026-07-31-knowledge-collections-design.md`.
Brief: `.agent-kit/sprint/2026-07-31-knowledge-and-gates/03-knowledge-collections/spec.md`.
Upstream: `.agent-kit/sprint/2026-07-31-knowledge-and-gates/03-knowledge-collections/upstream.md`.

## File map

| File | Change |
|---|---|
| `plugins/agent-kit/scripts/kit_yaml.py` | gains `dump()` — the writer the index needs; the reader is untouched |
| `plugins/agent-kit/scripts/kit_knowledge.py` | new — anchors, entry resolution, index read/write, staleness, the cross-checks |
| `plugins/agent-kit/scripts/blueprint_index.py` | new — the `--index` CLI: `--plan`, `--apply`, `--anchors` |
| `plugins/agent-kit/scripts/blueprint_check.py` | entries, index staleness and cross-checks join the report |
| `plugins/agent-kit/templates/project/contract.yml` | the `entries:` block, documented |
| `plugins/agent-kit/skills/blueprint/SKILL.md` | `--index` and the placement flow; `argument-hint` grows |
| `plugins/agent-kit/skills/blueprint/references/grader.md` | new — the rubric and the fact vocabulary |
| `tests/test_kit_yaml.py` | the writer, and its round trip through the reader |
| `tests/test_kit_knowledge.py` | new — anchors, cross-checks, the cache, the surgical contract edit |
| `tests/test_blueprint_check.py` | the report's new sections, and the exit codes they carry |
| `tests/fixtures/**` | new fixture projects, one per cross-check, violating and clean |
| `README.md`, `plugins/agent-kit/README.md` | the `blueprint` rows carry the new mode |
| `CHANGELOG.md` | bullets appended to the existing `## 0.17.0` section |

## Tasks

1. **The YAML writer.** `kit_yaml.dump()` over the same subset the reader accepts, quoting whatever
   would read back as something else. Verify: `tests/test_kit_yaml.py` round-trips generated
   structures — dump, load, compare — including the values that need quoting (all-digit hashes,
   `true`, a leading `#`, an empty string, non-ASCII prose).
2. **Anchors and entry resolution.** In `kit_knowledge.py`: find `<!-- kit: key -->`, resolve the
   section it sits in, and reuse stage 1's `section_body` for the heading path. Verify: property
   tests over generated documents — anchor and heading resolve to the same section until the heading
   is renamed; duplicate anchors raise; an anchor above the first heading binds the preamble.
3. **The index and the cache.** Read and write `index.yml`, compute what is stale, group the stale
   sections by document, merge results back. Verify: `refresh(root, fake_grader)` — one call per
   document on the first run, zero on the second, one call carrying one section after one edit.
4. **The cross-checks.** Set completeness first, then statuses, rights, screens, lifecycle, with the
   screen ids read out of `screens.data.js`. Verify: one fixture per check that fires it and one
   that does not, asserted on the message and not only on the count.
5. **`--check` reports entries.** Per-collection entry counts, drift split by binding kind, index
   staleness, cross-check findings, `gaps`. Verify: the fixture trees drive the script as a
   subprocess; an unresolved entry is 1, a missing document is 2, a duplicate anchor is 2.
6. **The `--index` CLI and the placement flow.** `--plan` to JSON, `--apply` from JSON, `--anchors`
   writing anchor lines and the surgical `entries:` block. Verify: an anchor is written on its own
   line under its heading; a second anchor for the same key is refused; the contract edit leaves
   every other byte, comments included, untouched.
7. **The skill, the rubric, the template, the READMEs, the changelog.** Verify:
   `scripts/validate.sh` green — it holds the frontmatter pairing, both README tables and the
   `${CLAUDE_PLUGIN_ROOT}` reference to the new rubric.
8. **The realest measurement.** Two documents parsed through the heading path against a scratch copy,
   cost recorded, cross-checks run, the numbers and the labelled extrapolation into the PR. Verify:
   `git -C /projects/realest status --porcelain` is empty.

## Run log

**Branch:** claude/knowledge-collections
**Steps:** Build, Test, Review, Security, PR, Docs

- context — run under `--brief`: no interactive gates, autonomous from the first step. The brief is
  the approved unit of work; what it left open is settled in the spec and recorded here.
- setup — `stack-playbook`'s freshness check closes on one line, as the brief said it would: this
  repository has no dependency manifest to fingerprint, and `docs/developing.md` is the registered
  standard. `scripts/validate.sh` is the whole declared suite.
- setup — the session is not in auto permission mode; said so once at the start and continued.
- assumption — `upstream.md` calls `kit_yaml.py` "the reader and writer". It is the reader only;
  there is no `dump()`. Writing `index.yml` needs one, so the writer is task 1 of this feature
  rather than something to reuse.
- decision — an entry whose binding no longer resolves is a **finding** (exit 1), where stage 1
  makes an unresolved *slot* binding structural (exit 2). An entry is one instance among many and
  the rest of the collection is still checkable; a missing document, an unreadable contract and a
  duplicate anchor stay structural. Recorded in the spec.
- decision — `at: path#kit:<key>` names an anchor and any other fragment names a heading, so both
  binding kinds keep stage 1's one grammar. The cost is a heading whose literal text begins `kit:`:
  that binding reads as an anchor and the check reports a missing anchor. A documented limit with a
  loud symptom, rather than a second field on every entry.
- decision — the entry key format is the brief's default: `<actor>.<action>` for actions, a bare
  slug elsewhere. The parse cache is `index.yml` itself, beside each entry's `rev`; no second file.
  The report follows the design's section 3 sample. The rubric is the design's own bar — *can an
  implementer act on this without asking?*
- step Build — done. `kit_yaml.dump`, `kit_knowledge.py`, `blueprint_index.py`, the entry half of
  `blueprint_check.py`, the template, the skill and its rubric, both READMEs, the changelog.
- deviation — an anchor line is **not** part of the hashed section body. The spec's own placement
  flow would otherwise invalidate every entry it had just bound, so adopting anchors would cost a
  second full parse of the corpus for a change that adds no information. The anchor is the kit's
  marker, not the owner's prose. Proven by test rather than argued.
- test — delegated to `agent-kit:tester`: 79 checks in a new `tests/test_kit_knowledge.py`, 17 more
  on the writer in `tests/test_kit_yaml.py`, 21 more in `tests/test_blueprint_check.py`, and seven
  fixture projects — one per cross-check, differing only in `index.yml`. It ran its own mutation
  harness over the payload: 40 deliberate breakages, 39 killed, 1 equivalent mutant (dead code,
  since removed).
- test — it found three real defects, all fixed here. (1) `apply_results` recorded the *current*
  file's hash while the facts described the text the grader had been given, so a document edited
  mid-run was filed as parsed and never re-read — the exact opposite of what its own docstring
  promised. A result now carries the `rev` the plan handed it, and a result without one is refused
  by name. (2) An entry referencing an undescribed key through two facts produced two identical
  findings; the design says one finding, not four. Deduplicated on the key, which also made the
  `unknown` set the other checks were passed dead — removed. (3) `set_entries` on a contract whose
  last line had no terminator glued the new block onto it and made the file unparsable — the kit
  breaking a file it was editing.
- test — three smaller things the tester reported without a red test, all fixed: the preamble path
  of `anchor_section` did not drop anchor lines while every other body did; `render` printed
  "1 entries"; `dump({})` failed with the round-trip message instead of naming the cause. One
  report was against the spec rather than the code — a heading whose literal text begins `kit:` is
  read as an anchor and reported as a missing anchor, which the spec claimed was named by kind. The
  spec now records the limit as it actually behaves.
- step Test — done. `scripts/validate.sh` green: 79 + 63 + 78 + 11 checks, plus manifests,
  frontmatter, references, payload syntax and the stdlib-only import parse. No runnable app
  surface — this is a script and a skill — so step 4's check against a running app is the CLI
  driven end to end by hand over a scratch project, which is recorded in the realest measurement
  below. Static analysis: the repository has no linter or type checker; `validate.sh`'s AST pass
  over the payload is the whole static layer and it is green.

### The realest measurement

Two documents of the read-only corpus, parsed through the `file#heading` path against a scratch
copy under `/tmp` — `/projects/realest` itself was never written to, and
`git -C /projects/realest status --porcelain` is empty.

| | `docs/OFFERS.md` | `docs/user-stories/DEVELOPER_SELLER.md` | total |
|---|---|---|---|
| entries bound | 4 | 9 | 13 |
| grader calls | 1 | 1 | 2 |
| tokens | 39,597 | 39,825 | 79,422 |
| wall clock | 145 s | 163 s | 163 s concurrent, 309 s serial |

Result: 44 gaps, 7 cross-check findings, 14 unreached screens. `--check` over the finished index
runs in **0.05 s**.

The finding that matters for the design's open question 1: **nine entries cost the same as four.**
Two calls is thin evidence, but at this size the per-call fixed cost — reading the rubric, the
screen map and the group — dominates the marginal cost of an entry so completely that the two
totals came out within 0.6% of each other. If that holds, the corpus cost scales with the number of
**documents**, not entries, which is exactly the unit `--plan` already groups by.

- decision — `--plan` sends whole-section text and the rubric is re-read per call. Both are the
  reason a call costs what it does, and both are deliberate: a grader with a partial section invents
  the rest, and a rubric summarised into the prompt is a rubric nobody can revise in one place.
- note — the 14 "screen on the map, and no action is launched from it" findings and 6 of the 7
  cross-check findings are artefacts of parsing 2 documents out of 14: the actors and screens they
  name are described elsewhere in the corpus. The one that is not an artefact is
  `actions/agency.clone_lot names actors/agency, which no entry describes`, and it is the check
  working. Worth knowing before stage 6 puts this in front of a build: on a **partially** adopted
  contract the map-coverage check is the noisiest of the five.
