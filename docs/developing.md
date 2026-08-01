# Developing the kit

## Repository layout

```text
.claude-plugin/marketplace.json   this repository is also the marketplace
plugins/agent-kit/                the plugin — everything that ships
  .claude-plugin/plugin.json      manifest; its `version` is what pins an install
  README.md                       the command list; the validator holds it to the skills
  skills/<name>/SKILL.md          one directory per command — this IS the behavior
  templates/knowledge/            the shape of each knowledge file blueprint writes
  templates/project.yml           the shape of a project's own corner
scripts/                          validate.sh, release.sh
docs/design/                      what was decided and why; kit-v1.md is the current one
```

The invariant: **behavior lives in exactly one file.** A skill that restates a rule instead of
pointing at it silently opts out of every later fix to that rule — which is how a fixed rule went on
being broken in two skills for a whole release. The same goes for the knowledge templates: they
carry the shape of a record so that no prompt has to describe it.

The kit is being rebuilt. Read [docs/design/kit-v1.md](design/kit-v1.md) before changing anything:
it records what was removed and why, and adding one of those things back needs an argument rather
than an oversight. Four of the five commands are declared stubs, and `scripts/validate.sh` enforces
that a command is either behavior or a stub marked as such in the plugin README.

## Adding a command

1. `plugins/agent-kit/skills/<name>/SKILL.md`, frontmatter first. `name` must match the directory,
   and `description` is how Claude Code decides to surface it — write it as what it does and when to
   use it. Add `disable-model-invocation: true` so it is only ever started deliberately.
2. Add the row to `plugins/agent-kit/README.md`, and drop the "not written yet" note.
3. Keep it short. Prose in a command is re-read on every step of every run, so rationale belongs
   here in `docs/design/`, not in the command.
4. `bash scripts/validate.sh`.

## Versioning

Semver from the perspective of a project that installed the kit. A command removed or renamed is a
breaking change; a command added is a minor. `1.0.0` is reserved for the release where all five
commands work — until then the rewrite ships as `0.x` so the version never claims more than exists.

`scripts/release.sh <version>` bumps `VERSION`, `plugin.json` and `marketplace.json` together,
validates, commits and tags. Publish with `git push && git push --tags`. A release that needs a
manual step on the user's side gets a note under `migrations/<version>.md`, referenced from the
changelog.

Feature commits never touch `CHANGELOG.md`; the release commit does.
