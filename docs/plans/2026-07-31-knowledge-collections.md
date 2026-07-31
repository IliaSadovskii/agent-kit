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
8. **The realest measurement.** Two documents parsed through the heading path against a scratch
   copy, cost recorded, cross-checks run, numbers and labelled extrapolation into the PR. Verify:
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
  fixture projects — one per cross-check, each differing from the clean one only in what it has to.
  It ran its own mutation harness over the payload: 40 deliberate breakages, 39 killed, 1 equivalent
  mutant (dead code, since removed).
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

**Extrapolation — an extrapolation, not a measurement.** The brief counts 17 markdown documents
under realest's `docs/`. At the per-call cost measured above, and on the finding that the cost is
per call rather than per entry, a first full parse is on the order of **675k tokens and ~45 minutes
serially** (17 × ~39.7k tokens, 17 × ~154 s), or a few minutes with calls running concurrently.
Every number in that sentence is derived from two data points, and the per-entry marginal cost is
too small at this size to be measured from them at all — a corpus with thirty entries in one
document would test that and this one did not. What is measured, and what the design's open
question 1 actually asked, is the shape: it is documents that cost money, and `--plan` already
groups by document, so the cache is against the right unit. Every run after the first pays only for
the documents that changed.

- step Review — done. Delegated to `agent-kit:reviewer` for the question nothing else answers — is
  this the feature that was approved. The `code-review` plugin is enabled here, so the bug hunt is
  left to the PR step rather than duplicated. The first attempt died on a session limit partway
  through; rerun with a tighter reading order.
- review — verdict: yes, this is the approved feature. All seven settled decisions honoured, both
  scope lists correct, `validate.sh` green, realest untouched. No critical findings; four major and
  fifteen minor.
- review — the four major, all fixed. (1) `--index --plan` dropped an entry whose binding no longer
  resolved without a word, and the skill tells the agent an empty plan means the index is current —
  so a contract whose every binding had broken reported itself up to date. `--plan` now names each
  skipped entry and its reason on stderr, and the skill says to read it. (2) The brief's screens
  cross-check is *"reached by some actor and launches some action"* and only the action half was
  built; the `screens` collection was inert besides, its `screen` fact read by nothing. Both halves
  are now checked, and a `screens` entry naming an id the map does not have — or naming none — is a
  finding. (3) `--apply` raised on the first entry whose binding had broken since the plan, throwing
  away every other result in the batch: at the measured ~40k tokens a document, that is the most
  expensive failure in the feature. It now skips that entry by name and keeps the rest. (4) The
  extrapolation the brief asks for was implied rather than stated; it is above, labelled.
- review — twelve minor findings fixed, most of them prose that had drifted from the code: three
  stale docstrings (`do_apply` still promised the pre-review `rev` behaviour, `_check_sources`
  still called entries "stage 2's work", the module docstring's exit-code table predated
  cross-checks and drift), `do_anchors` claiming an atomicity the write loop does not have, the
  changelog claiming the code re-proposes a deleted anchor when that is the skill's procedure, and
  the spec missing the `idea` skip, the two extra `rights` findings, the exit-2 case for a
  malformed `at`, and the suppression of `gaps` on a stale entry. In code: `blueprint_index` now
  exits 2 rather than 1 on an `OSError` — stage 6 gates on those codes and 1 means "findings";
  `--check` reports a screen map the manifest names and does not have, instead of silently losing
  the check; and `set_entries` now quotes through `kit_yaml.scalar`/`key` rather than a weaker
  duplicate that wrote a heading containing a tab before a `#` unquoted, which the reader then
  truncated. Dead code removed: `documents_matching`, and the `FACTS` table that duplicated the
  rubric's and was read by nothing.
- review — deliberately not changed: `set_entries` appends the `entries:` block after `reason:` and
  `criterion:` while the template's comment shows it after `sources:` (cosmetic, and the reader does
  not care about key order); the `# noqa: F401` on the re-export in `blueprint_check` marks intent
  for a reader even though this repository runs no linter; and the realest-flavoured examples in the
  template comments and the rubric (`docs/OFFERS.md#Оффер от агентства`, `broker`, `lot`) stay —
  they are the examples the brief and the design approved, and they name no project.
- review — the fixes are covered by twelve new checks in `tests/test_kit_knowledge.py`
  (`BrokenBindingTest`, `ScreenReachabilityTest`, `NamedScreenMapTest`, `EntryQuotingTest`), and
  five targeted mutations over the changed lines were all killed. `scripts/validate.sh` green
  again: 91 + 78 + 63 + 11 checks.
- security — `/security-review` over the branch, then read against the layer's own threat model:
  the contract, the index, the manifest and every document are content of a repository the developer
  may not control. Two findings, both real, both fixed.
- security — (1) **arbitrary file write.** `write_index` joined `.agent-kit/knowledge/index.yml`
  onto the root and opened it for writing. Git checks a symlink out like any other file, so a pull
  request could leave one there and `--index` would write the derived index straight through it —
  creating or truncating a file in the developer's home directory. The kit's own paths now go
  through `kit_owned()`, which refuses a symlink outright and re-checks containment; `contract.yml`
  and the manifest go through it too, since this feature made the first of them writable.
  (2) **an entry could read anything in the repository.** `at` was containment-checked and nothing
  more, and `--plan` prints the section it names as the grader's payload — so a contract arriving in
  a pull request could bind an entry to a `.env` the developer has locally and read it out through
  the model. An entry must now live in a document its own collection's `sources` name.
- security — the second fix does not make a hostile contract safe, and the spec says so: whoever
  writes the entries writes the `sources`. What it does is move the hostile line into the one block
  a reviewer reads. The skill's trust-boundary section now covers bindings as well as commands, and
  tells the reader to look at `sources` before running anything on a repository they do not control.
- security — eight new checks in `tests/test_kit_knowledge.py` (`KitOwnedPathTest`,
  `SourceConfinementTest`), including one asserting the secret never reaches `--plan`'s output at
  all; both fixes' mutations were killed. `scripts/validate.sh` green: 99 + 78 + 63 + 11.
- step Security — done.
- pr — PR #14, draft against `claude/knowledge-contract`, CI (`validate`) green on the first run.
- note — the `code-review` plugin refuses a draft, and the kit's pull-request rule *requires* a
  stacked sprint feature to be a draft. 02 hit this and so did this run: left alone, those two rules
  cancel the PR-step review for every stacked feature. The fan was run manually on the open draft
  instead, five independent passes plus the confidence filter, and its outcome is posted on the PR.
  This is now the second consecutive feature to lose the automatic review in silence.
- pr — the fan found six things, two of them code. The serious one is a hole in **this run's own
  security fix**: the confinement of an entry to its collection's `sources` was skipped when the
  collection declared none, on the reasoning that `--check` already reports a filled collection with
  no sources. It does — but entries are read whatever the collection's *status* is, and every
  collection ships `status: empty` with `sources: []`, so the out-of-the-box shape was the way
  around the check. A contract with `status: empty` and one entry bound to `.env` still leaked the
  section into `--plan`'s output. Every collection is now confined, including one that declares
  nothing.
- pr — the second: `kit_yaml.key()` escaped a non-plain mapping key the way a *value* is escaped,
  but the reader takes a key back by stripping its quotes and never unescapes — so a key holding a
  backslash or a tab was written as the escape sequence and read back as the sequence, leaving the
  entry permanently unbound with nothing in the report pointing at why. `key()` now proves its own
  round trip and refuses what the subset cannot hold, and `--anchors` refuses a key that could not
  survive `<!-- kit: … -->` before it writes anything.
- pr — four prose findings, all fixed: the rubric claimed every fact in its table is read by a
  cross-check when five are not (they are now marked); `_body`'s docstring said line endings are
  normalized and then that every line keeps its own terminator; `set_entries` promised to leave
  every other byte alone without naming the trailing newline it adds; and the skill said a broken
  binding is repaired through `--check`'s drift section, when only some of them are drift and the
  rest are structural.
- pr — three new checks cover the fixes and all three mutations were killed. `scripts/validate.sh`
  green again: 101 + 78 + 63 + 11.
- step PR — done. PR #14, draft (a stacked feature cannot land code), CI green on the first run and
  again after each round of fixes. The manual fan's outcome is posted on the pull request.
- docs — `docs-reflection` found one divergence. `docs/developing.md`'s "A file the project owns"
  rule said the plugin never writes into a project's own files after bootstrap, and this feature
  writes two: the `entries:` block of the knowledge contract, and an anchor inside the owner's own
  markdown. The rule now names what is allowed and on what terms — replace the one block the command
  owns and leave every other byte, never load-and-re-emit, and ask before touching a document. A
  second bullet records the security finding as the rule it traced back to: a payload script never
  follows a symlink at a path the kit itself owns. Both are the trigger the reflection step names —
  a finding that will otherwise repeat is a missing rule.
- docs — that edit landed inside the section this repository's own contract binds, so the build went
  red until the `rev` was updated: `2f280be7ed4b → c7879d4ef356`. The contract doing its job on the
  repository that ships it, and the first time in this sprint that it has caught a real edit.
- docs — the documentation change stays on this branch rather than going to a docs-only PR from
  `main`, on 01's reasoning, which is stronger here: it describes rules that only exist because of
  the code in this pull request.
- docs — deliberately not touched: `docs/design/knowledge-and-gates.md` still opens "proposed, not
  implemented", which is still true of `main`. Rewriting it here would claim work the default branch
  does not have; it belongs to whoever merges the sprint's integration pull request.
- docs — no screen map in this repository (`manifest.sources.screens` is null), so the Docs step's
  map update does not apply. No roadmap or product idea document either — this project is
  `bootstrapped: false` by choice.
- step Docs — done.
