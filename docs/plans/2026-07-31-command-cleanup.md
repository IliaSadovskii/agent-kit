# Plan — command cleanup (nine commands become six)

Spec: `docs/specs/2026-07-31-command-cleanup-design.md`.
Brief: `.agent-kit/sprint/2026-07-31-knowledge-and-gates/01-command-cleanup/spec.md`.

## File map

| File | Change |
|---|---|
| `plugins/agent-kit/skills/debug/SKILL.md` | frontmatter → internal; description names `fix` as caller; one clause on the input line |
| `plugins/agent-kit/skills/address/SKILL.md` | same, caller `fix --pr <n>` |
| `plugins/agent-kit/skills/screens-riff/SKILL.md` | same, caller `riff`; the three-command table loses its own row |
| `plugins/agent-kit/skills/fix/SKILL.md` | widened frame and description, `argument-hint` gains `[--pr <n>]`, two routing paragraphs |
| `plugins/agent-kit/skills/riff/SKILL.md` | a screen theme runs `screens-riff` |
| `plugins/agent-kit/skills/ship/SKILL.md` | `/agent-kit:address` → `/agent-kit:fix --pr <n>` |
| `plugins/agent-kit/skills/sprint/SKILL.md` | two `/agent-kit:address` references repointed |
| `plugins/agent-kit/engine.md` | the pipeline-command list drops `/agent-kit:debug`; the file must not grow past the cap |
| `README.md`, `plugins/agent-kit/README.md` | three rows out; `fix` and `riff` rows rewritten; the count sentence |
| `scripts/validate.sh` | three names into the internal allowlist; new stale-command-reference check |
| `migrations/0.17.0.md` | new |
| `CHANGELOG.md` | new `## 0.17.0` section |

## Tasks

1. **The three skills become internal.** Frontmatter and description only, plus one clause on each
   input line. Verify: `scripts/validate.sh` fails at this point — the READMEs still document three
   commands that are no longer commands, which is the check doing its job.
2. **The two callers route to them.** `fix` widens; `riff` recognises a screen theme. Verify: the
   routing paragraphs name the skill, the condition, and what happens after it returns.
3. **Repoint the four remaining references.** `ship`, `sprint` ×2, `engine.md`. Verify:
   `grep -rn "agent-kit:\(debug\|address\|screens-riff\)"` outside `CHANGELOG.md` and `migrations/`
   is empty; `wc -c plugins/agent-kit/engine.md` stays under 10,000.
4. **The READMEs.** Three rows leave both tables; `fix` and `riff` rows describe what they now
   cover; the "nine commands" sentence follows the count. Verify: both tables list exactly the
   skills whose frontmatter still carries `disable-model-invocation: true`.
5. **`validate.sh`.** The allowlist gains three names; the new check reads every `/agent-kit:<name>`
   in the repository outside history and requires it to be a live command. Verify: the check fails
   against a deliberately stale reference, then passes once it is removed.
6. **Migration note and changelog.** `migrations/0.17.0.md` in the shape of `0.4.0.md`; a `## 0.17.0`
   section directly under the changelog intro. Verify: full `scripts/validate.sh` green.

## Run log

**Branch:** claude/command-cleanup
**Steps:** Build, Test, Review, Security, PR, Docs

- context — run under `--brief`: no interactive gates, autonomous from the first step. The brief's
  design sketch is the approved unit of work; there is no `upstream.md` sibling, this being feature
  1 of 7.
- setup — `stack-playbook` freshness: current by inspection. This repository has no dependency
  manifest to fingerprint, and its registered standards are `docs/developing.md`, which is
  hand-written and not a generated playbook. Nothing to refresh.
- setup — the project interview is deliberately not run. `manifest.yml` exists with
  `bootstrapped: false` and no `instructions.md`, which is this repository's recorded state: the
  kit's roadmap is the owner's, so task selection and product scoping stay off.
- assumption — the expanded spec and this plan are committed to `docs/specs/` and `docs/plans/`,
  which no previous feature in this repository has done. The pipeline says the spec is written and
  committed, and the `Stop` hook reads the plan from `docs/plans/` on this branch, so both need to
  be on disk; committing them follows the kit's own documented behavior.
- decision — the three moved skills each keep their `$ARGUMENTS` line and gain one clause naming
  the calling skill as the other source of the same input. `$ARGUMENTS` is only substituted for a
  slash command, and `ideate` already carries one as an internal skill, so this is the smallest
  honest repair rather than a prose rewrite.
- decision — the new `validate.sh` check is the general form of the grep the brief asked for: every
  `/agent-kit:<name>` outside `CHANGELOG.md` and `migrations/` must be a skill that still carries
  `disable-model-invocation: true`. Five more features pass over these files.
