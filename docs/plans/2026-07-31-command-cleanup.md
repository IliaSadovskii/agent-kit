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
**Steps:** Gate, Design, Plan

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
