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
  binding kinds keep stage 1's one grammar. A heading whose literal text begins `kit:` is named as
  such by the check rather than read as an anchor.
- decision — the entry key format is the brief's default: `<actor>.<action>` for actions, a bare
  slug elsewhere. The parse cache is `index.yml` itself, beside each entry's `rev`; no second file.
  The report follows the design's section 3 sample. The rubric is the design's own bar — *can an
  implementer act on this without asking?*
