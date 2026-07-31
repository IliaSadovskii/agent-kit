# 01 · Command cleanup — nine commands become six

Owner-approved design sketch for a `ship --brief` run. What is settled here is settled; what is
left open becomes the run's logged assumptions. Depth agreed at the brief: **light**.

## Context: this repository is the kit itself

The working repo is the agent-kit **plugin source**, not a bootstrapped agent-kit project.
`.agent-kit/project/manifest.yml` exists and records `language: ru`, `bootstrapped: false`, and
`coding_standards: docs/developing.md`; there is no `instructions.md`. Do not run the project
interview and do not create one.

`stack-playbook`'s freshness check closes on a single line: there is no dependency manifest to
fingerprint here, and the registered standards are `docs/developing.md`. Follow its
"Adding a skill" procedure and its Versioning section. `scripts/validate.sh` is this repository's
entire declared test command and must stay green.

Code, identifiers, paths, commit messages, and every document under `docs/` are English. The pull
request description is Russian (`manifest.language: ru`).

The full design this batch implements is `docs/design/knowledge-and-gates.md` — read section 7 and
section 9's stage 0. This feature is **stage 0**.

## Batch position

Feature 1 of 7 in a strictly linear stack. Base branch: `main`. Everything after this builds on
`claude/command-cleanup`, so a mistake here is inherited six times — keep the diff mechanical.

The batch ships as one breaking release, **0.17.0**. Append this feature's bullets to a
`## 0.17.0` section in `CHANGELOG.md`, creating the section (directly under the intro paragraph,
above `## 0.16.0`). **Do not bump `VERSION`, `plugin.json`, or `marketplace.json`** — the release
commit is the owner's, after the integration PR merges. This feature also creates
`migrations/0.17.0.md`; later features in the batch append to it.

## Goal

Remove three command entry points without losing a line of what they do: `debug`, `address`, and
`screens-riff` become internal skills that `fix` and `riff` invoke.

## The mechanism, already verified against the code

A skill in `plugins/agent-kit/skills/` is a user-facing command exactly when its frontmatter carries
`disable-model-invocation: true`. Skills without it — `brainstorming`, `ideate`, `writing-plans`,
`idea-interview`, `docs-reflection`, `stack-playbook` — are internal and model-invocable, and
`scripts/validate.sh` (the "Every command promised in the plugin README" check, near line 172)
carries an explicit allowlist of those six names so they are not required to have a README row.

So the move is: drop `disable-model-invocation: true` and `argument-hint`, rewrite the
`description` to say who invokes the skill and when, and add the name to that allowlist.

## Scope

In:

- `skills/debug/SKILL.md` — becomes internal. Description: invoked by `fix` when the cause of a
  failure is unknown.
- `skills/address/SKILL.md` — becomes internal. Description: invoked by `fix --pr <n>`; its
  execution contract is unchanged, only the entry point moved.
- `skills/screens-riff/SKILL.md` — becomes internal. Description: invoked by `riff` on a screen
  theme. **Its ability to write taken proposals onto the screen map as `idea` cards, and turned-down
  ones as `rejected` memory, is preserved whole** — losing that artifact would make this a
  downgrade, not a cleanup.
- `skills/fix/SKILL.md` — the frame widens to the design's own section 7 wording: *"something is
  wrong: your words, a PR review, or an observed failure."* `argument-hint` gains `[--pr <n>]`. Two
  routing paragraphs: `--pr <n>` or a PR URL runs `address`; a symptom whose cause is not yet known
  runs `debug` first and then continues through fix's own tail. The existing escape hatch — a task
  that turns out to need a design stops and offers `ship` — stays.
- `skills/riff/SKILL.md` — a screen theme runs `screens-riff`.
- `scripts/validate.sh` — the three new names join the internal-skill allowlist.
- `README.md` and `plugins/agent-kit/README.md` — three rows leave the command tables; the `fix` and
  `riff` rows change to describe what they now cover.
- `plugins/agent-kit/engine.md` line 7 names `/agent-kit:debug` in its list of pipeline commands —
  replace it. This file is delivered through a `SessionStart` hook whose output Claude Code caps at
  10,000 characters, and `validate.sh` enforces the cap: do not grow it.
- `skills/ship/SKILL.md` (line ~121) and `skills/sprint/SKILL.md` (lines ~232, ~260) point at
  `/agent-kit:address` — repoint at `/agent-kit:fix --pr`.
- `migrations/0.17.0.md` — new, naming where each of the three commands went, in the shape of the
  existing `migrations/0.4.0.md`.
- `CHANGELOG.md` — the `## 0.17.0` section.

Out:

- **`docs` is not touched.** It is absorbed into `blueprint --check` at stage 7, when blueprint
  exists; removing it now would drop the capability for six stages.
- `riff` itself is not removed. Its survival is decided later on evidence.
- No behavior inside the three moved skills changes. This is a re-wiring, not a rewrite.

## Settled decisions

- The three skills keep their prose whole. Only frontmatter, descriptions, and the two callers
  change.
- `fix` widens its frame rather than staying "the light path for a small change" — a review round on
  a `ship` PR is not small, and after this it arrives through `fix --pr`.
- Version `0.17.0`; feature branches write the changelog section, the release commit does not.

## Left to the run

- How `fix` decides the cause is unknown — default: the model's judgment from the task text, no new
  flag.
- How `riff` recognises a screen theme — default: the same standalone `S<digits>` token grammar
  `ship` already documents under "Screen references", plus an explicit mention of screens or the
  map. `riff` is interactive, so genuine ambiguity is asked rather than guessed.
- Exact wording of the new README rows and the migration note.

## Done means

- `scripts/validate.sh` is green.
- `grep -rn "agent-kit:\(debug\|address\|screens-riff\)"` over the repository returns hits only in
  `CHANGELOG.md` and `migrations/`.
- The command tables in both READMEs list exactly the skills whose frontmatter still carries
  `disable-model-invocation: true`, and nothing else.
- `migrations/0.17.0.md` names the new entry point for each of the three removed commands.
- The three moved SKILL.md files each state in their description which skill invokes them, and
  `screens-riff` still documents writing proposals onto the map.

## Verification

`scripts/validate.sh` is the mechanical gate and covers the structural half of the done-means above
(frontmatter, README/skill agreement, dangling `${CLAUDE_PLUGIN_ROOT}` references, the engine.md
size cap). Add to it only what it does not already check and this feature needs — the grep for dead
command references is worth a check there, since five more features will pass over these files.

There is no runnable surface, so no app to start. No heavy verification layer is earned here: the
change is a re-wiring of documentation-shaped payload, and mutation or property testing has nothing
to bite on. Say so explicitly rather than skipping in silence.

---

# Run expansion — what the design stage settled

Appended by `ship --brief --stage design` on 2026-07-31. Everything above is the owner's approved
sketch and stands unchanged; this section records the mechanics it left open, and the two places
exploration proved it stale.

## Deviations from the sketch

- **The release is 0.18.0, not 0.17.0.** v0.17.0 shipped after the sketch was written; the batch's
  `orientation.md` overrides the sketch on this point. So: a `## 0.18.0` section at the top of
  `CHANGELOG.md`, and `migrations/0.18.0.md` rather than `0.17.0.md`. `VERSION`, `plugin.json` and
  `marketplace.json` stay untouched, as the sketch says.
- **The line numbers in the sketch's scope list have moved.** The live references are
  `skills/ship/SKILL.md:222` and `skills/sprint/SKILL.md:320,348`; the validator's internal-skill
  allowlist is at `scripts/validate.sh:177`, not 172. Same files, same edits.
- **One reference the sketch's scope list misses.** `skills/screens-riff/SKILL.md:19` names
  `/agent-kit:screens-riff` in its own "three commands touch the map" table. The sketch's done-means
  grep requires that hit to go, so the row is repointed at `riff` on a screen theme. This is the
  skill describing its own entry point, not a behavior change.

## Mechanics settled here

**How `fix` decides the cause is unknown** — the sketch's default stands: the model's judgment from
the task text, no new flag. The routing paragraph names the shape it is judging (a symptom, a stack
trace, a wrong result with no named culprit) so the judgment is anchored rather than free.

**How `riff` recognises a screen theme** — the sketch's default stands: a standalone `S<digits>`
token under the same grammar `ship` documents under "Screen references", or an explicit mention of
screens or the screen map. `riff` is interactive, so a genuinely ambiguous theme is asked about
rather than guessed. When it does route, `screens-riff`'s own rules govern what gets written —
`riff`'s "nothing is committed except approved roadmap lines" is a rule about `riff`'s own path.

**The validator check.** The sketch asks for the three names to join the internal-skill allowlist,
and for a check on dead command references. Both are done by deriving the split from frontmatter
instead of maintaining the hardcoded list:

- a skill is a command exactly when its frontmatter carries `disable-model-invocation: true`, which
  is the definition the sketch itself works from. The set of six names hardcoded at
  `scripts/validate.sh:177` is today identical to the set that lack the field, so replacing the
  literal with `skill_names - command_names` changes no verdict on the current tree;
- every `/agent-kit:<name>` reference in the repository must name a skill in that command set.
  `CHANGELOG.md`, `migrations/`, `docs/specs/` and `docs/plans/` are excluded: they are dated records
  of what a release or a run did, not instructions anyone follows. This is the sketch's done-means
  grep, enforced rather than run by hand.

Replacing the allowlist rather than extending it is the smaller thing to carry: five more features in
this batch move skills between the two sets, and each would otherwise have to remember to edit a
literal that the frontmatter already answers.

## Not earned here

No test layer beyond `scripts/validate.sh`. The change is documentation-shaped payload — frontmatter,
prose, and README rows — with no runnable surface and nothing for mutation or property testing to
bite on. The validator's structural checks plus the new reference check are the whole verification,
and the design stage records that as a deliberate choice rather than a gap.
