# Plan — command cleanup: nine commands become six

Spec: [docs/specs/2026-07-31-command-cleanup-design.md](../specs/2026-07-31-command-cleanup-design.md).
The spec says what is being built and what done means; this file is the task list, its verification,
and the run's log.

## Tasks

### 1. The three skills become internal

`skills/debug/SKILL.md`, `skills/address/SKILL.md`, `skills/screens-riff/SKILL.md`: drop
`disable-model-invocation: true` and `argument-hint`, rewrite `description` to say which skill
invokes it and when. Prose below the frontmatter is untouched, with one exception — the
"three commands touch the map" table at `screens-riff/SKILL.md:19` repoints its own row at `riff`
on a screen theme.

*Verify:* `scripts/validate.sh` — the frontmatter and README-agreement checks both move as a result.

### 2. `fix` takes over `debug` and `address`

`skills/fix/SKILL.md`: frontmatter frame widens to the design's section 7 wording;
`argument-hint` gains `[--pr <n>]`. Two routing paragraphs before the numbered path — `--pr <n>` or a
PR URL runs `address`; a symptom whose cause is not yet known runs `debug` first, then continues
through fix's own steps. The existing escape hatch to `ship` stays.

*Verify:* `scripts/validate.sh`; both entry points readable in one pass of the file.

### 3. `riff` takes over `screens-riff`

`skills/riff/SKILL.md`: a screen theme runs `screens-riff`. Recognition is a standalone `S<digits>`
token or an explicit mention of screens or the map; ambiguity is asked about, not guessed.

*Verify:* `scripts/validate.sh`.

### 4. The callers stop naming the removed commands

`plugins/agent-kit/engine.md:7` (watch the 10,000-byte cap — 8,625 today),
`skills/ship/SKILL.md:222`, `skills/sprint/SKILL.md:320,348` → `/agent-kit:fix --pr`.

*Verify:* the new validator check in task 6.

### 5. Both READMEs

`README.md:49–57` and `plugins/agent-kit/README.md:13–21`: the three rows leave; the `fix` and `riff`
rows describe what they now cover.

*Verify:* `scripts/validate.sh` — README and skill directory must agree in both directions.

### 6. The validator

`scripts/validate.sh`: derive the command set from `disable-model-invocation: true` and use
`skill_names - command_names` in place of the hardcoded allowlist at line 177; add a check that every
`/agent-kit:<name>` reference in the repository names a skill in the command set, excluding
`CHANGELOG.md`, `migrations/`, `docs/specs/` and `docs/plans/`.

*Verify:* the check fails on a deliberately reintroduced `/agent-kit:debug` reference before it is
trusted, then `scripts/validate.sh` green.

### 7. Changelog and migration note

`CHANGELOG.md`: a `## 0.18.0` section directly under the intro paragraph, above `## 0.17.0`.
`migrations/0.18.0.md`: new, in the shape of `migrations/0.4.0.md`, naming the new entry point for
each of the three commands. `VERSION`, `plugin.json`, `marketplace.json` are not touched.

*Verify:* `scripts/validate.sh` (it checks `VERSION` still has its own changelog section).

## Run log

**Branch:** claude/command-cleanup
**Steps:** CI, Docs

- step Gate — done: technical setup present (`.agent-kit/project/manifest.yml`, `language: ru`,
  `coding_standards: docs/developing.md`); no project interview run and no `instructions.md`
  created, per the batch orientation. Product bootstrap is `bootstrapped: false` **with** a supplied
  brief, so the run proceeds — and the pull request owes the owner the standing warning: this
  repository records no product idea or roadmap, so task selection and product scoping are
  unavailable and every autonomous default is judged against the code rather than a stated intent.
  `stack-playbook` freshness: current by inspection — no dependency manifest to fingerprint here, and
  the registered standards are `docs/developing.md`, read for "Adding a skill" and "Versioning".
- step Design — done: the sketch is copied to `docs/specs/2026-07-31-command-cleanup-design.md` with
  a "Run expansion" section recording three deviations and the settled mechanics. See it for the
  reasoning; the deviations in short are (a) the release is **0.18.0**, not 0.17.0, per the batch
  orientation, so `migrations/0.18.0.md` and a `## 0.18.0` changelog section; (b) the sketch's line
  numbers have moved — same files, same edits; (c) one reference the sketch's scope list misses,
  `skills/screens-riff/SKILL.md:19`, which its own done-means grep requires.
- step Plan — done: this file.

### What later stages need from here

- **Language.** Code, identifiers, paths, commit messages and everything under `docs/` are English;
  the pull request description is Russian (`manifest.language: ru`).
- **The declared suite is `scripts/validate.sh`, and it is the whole of it.** CI runs the same script
  (`.github/workflows/ci.yml`). There is no runnable surface in this repository and no app to start,
  so the Test step's "confirm against the running app" is a named skip, not an omission.
- **No heavy verification layer is earned.** The spec says so and the design stage confirms it: this
  is documentation-shaped payload. The one thing worth proving is the new validator check, and it is
  proved by making it fail once against a reintroduced dead reference.
- **The base branch for `agent-kit:reviewer` is `main`** — this is feature 1 of 7 and the only one in
  the stack based on the default branch.
- **The PR must end as a draft.** It is a stacked feature in a sprint; the conversion is the
  `deliver` stage's last action.
- **Do not bump `VERSION`, `plugin.json` or `marketplace.json`.** `scripts/release.sh` owns those and
  the validator checks they agree with the `## <VERSION>` changelog heading; a bump inside a feature
  branch breaks the validator for every other branch in the stack.

- step Build — done: tasks 1–7 all applied as scoped. One mechanic settled beyond the sketch and the
  design-stage expansion: the validator's dead-reference check walks `*.md` files only (a shell
  script's `pgrep -f '/agent-kit:s'` pattern is not a documentation reference and matched the naive
  regex), and excludes `.agent-kit/sprint/` and `docs/design/` alongside the sketch's four
  exclusions — both hold dated sprint sketches/reports and this batch's forward-looking design doc
  (which names `/agent-kit:blueprint`, a command that does not exist yet), neither of which is an
  instruction anyone follows today. `README.md` and `plugins/agent-kit/README.md` command tables now
  list exactly `docs`, `fix`, `riff`, `screens`, `ship`, `sprint` — the six skills whose frontmatter
  still carries `disable-model-invocation: true`.
- step Test — done: no test layer beyond `scripts/validate.sh` is earned, per the spec's
  "Not earned here" — documentation-shaped payload, no runnable surface. `scripts/validate.sh` is
  green. The new dead-reference check was proven by reintroducing `/agent-kit:debug` into `README.md`
  (validator failed with `README.md references /agent-kit:debug, which is not a live command`) and
  reverting it (validator green again). The done-means grep
  `grep -rn "agent-kit:\(debug\|address\|screens-riff\)"` returns hits only in `CHANGELOG.md`,
  `migrations/`, `docs/specs/`, and `docs/plans/`.
- step PR — done: [#17](https://github.com/IliaSadovskii/agent-kit/pull/17), opened ready against
  `main` (feature 1 of 7 — the only one in the stack based on the default branch). Description in
  Russian per `manifest.language`, with the standing `bootstrapped: false` warning, the run's
  assumptions table, and the Testing section from the Test step's record. Conversion to draft is the
  `deliver` stage's last action, not this one's.
- step Review — done: one wave over the frozen diff at `6c33d04`, then one round of fixes
  (`18174c9`). Passes: `agent-kit:reviewer` against the spec, plan, orientation and
  `docs/developing.md` with base `main`; the `code-review` plugin on PR #17, which posted
  [its comment](https://github.com/IliaSadovskii/agent-kit/pull/17#issuecomment-5143586316) with two
  findings above its confidence bar. The security pass is a **named skip**: the diff's only
  executable surface is `scripts/validate.sh`, a build-time script reading this repository's own
  tracked files — no untrusted input, no network, no secrets, no runtime surface. The rest is
  documentation-shaped payload. `/simplify` skipped as well — the diff is small and prose-shaped.
  Fixed: `fix`/`riff` routing now hands arguments over and names where control resumes (the
  `$ARGUMENTS` hole in the three now-internal skills, and `debug` handing back into step 3 rather
  than step 1); `riff`'s "nothing is written" rule no longer reads as a ban on `screens-riff`'s own
  cards; the stale "Three commands touch the map" header and "Nine commands" README line; and
  `docs/developing.md`, which described the validator this feature changed. The fix diff went back
  through `agent-kit:reviewer` once, as the flow requires: no critical or major finding, and the
  minors it raised — self-references the "Three passes" rename left behind in `screens-riff`, two
  over-broad sentences in the refreshed `docs/developing.md`, `address` naming only the `--pr` entry
  of its two, and the strategy pointer that named no next action — are closed in the same round.
  **Deliberately deferred** — the validator no longer forces a *new internal* skill to declare
  itself anywhere (the derived command set only guards commands), it walks `*.md` only so
  `templates/screens/screens.html` and `scripts/sprint-watchdog.sh` keep unguarded command
  references, and `docs/design/` is exempt from the dead-link check though it is a live design; the
  `## 0.18.0` changelog intro reads as this feature's rather than the release's, which the release
  commit rewrites; and commit `6be72b3` used the branch slug as its conventional-commit scope with
  no `!` for a breaking change, left alone rather than rewriting pushed history.
- step CI — done: `gh pr checks 17` — `validate` pass (11s).
- step Docs — done: `docs-reflection` scope is `docs/developing.md`, already brought current in the
  Review step's fix round against this feature's validator change; `README.md` and
  `plugins/agent-kit/README.md` command tables were updated at Build. No screen map
  (`manifest.sources.screens` is null — this repository has no screens of its own). Nothing else
  diverged. PR #17 converted to draft, this being a stacked feature in a sprint batch — the deliver
  stage's last action.
