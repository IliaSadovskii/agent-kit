# Developing the kit

## Repository layout

```text
.claude-plugin/marketplace.json   this repository is also the marketplace
plugins/agent-kit/                the plugin
  .claude-plugin/plugin.json      manifest; its `version` is what pins an install
  engine.md                       always-on governance, injected by the SessionStart hook
  skills/<name>/SKILL.md          one directory per skill — this IS the behavior
  agents/<name>.md                reviewer and tester subagents
  rules/                          autonomous mode, interactive mode, pull requests
  templates/project/              what bootstrap copies into a project
  templates/screens/              the screen map viewer, copied by /agent-kit:screens
  hooks/hooks.json, scripts/      session start and cloud dependency setup
scripts/                          validate.sh, release.sh
migrations/<version>.md           notes for a release that needs a manual step
```

The invariant: **behavior lives in exactly one file.** Before 0.4.0 the payload had a canonical file
plus a generated wrapper pointing at it, because it served two providers. It serves one now, so the
`SKILL.md` is the canonical file. `scripts/validate.sh` fails a skill whose body is short enough to
be a pointer rather than a procedure.

## Adding a skill

1. Create `plugins/agent-kit/skills/<name>/SKILL.md` with frontmatter. The `name` must match the
   directory, and the `description` is how Claude Code decides to surface it — write it as "what it
   does and when to use it", not as a title.
2. Add `disable-model-invocation: true` if it is a pipeline the user should trigger deliberately,
   and `argument-hint` if it takes arguments. Skills the pipelines call internally
   (`brainstorming`, `writing-plans`, and the rest) leave both off so they stay invokable.
3. If it is a user-facing command, add a row to `plugins/agent-kit/README.md` — the validator checks
   that the README and the skill directory agree in both directions.
4. `scripts/validate.sh`.

Supporting files go in the skill's own directory and are referenced as
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/references/<file>.md`. The validator resolves every such path
and fails on a dangling one.

Adding an agent is the same, with a single file under `agents/`.

## Testing a change

Load the working tree as a plugin without installing it:

```bash
claude --plugin-dir ./plugins/agent-kit
```

Then check that the components registered: `/agent-kit:` in the prompt lists the skills, `/context`
shows the agents, and `/hooks` shows the SessionStart entries. Edits to a skill are picked up by
`/reload-plugins` without restarting.

`scripts/validate.sh` covers what a session cannot tell you at a glance: manifest and version
agreement across `VERSION`, `plugin.json`, and `marketplace.json`; skill and agent frontmatter;
dangling `${CLAUDE_PLUGIN_ROOT}` references; leftover paths from the pre-plugin layout; the
`engine.md` size cap; and `claude plugin validate --strict` when the CLI is available.

### The engine size cap

`engine.md` reaches the session as SessionStart hook output, which Claude Code caps at 10,000
characters — past that it is written to a file and replaced with a preview, so the governance
silently stops being always-on. The validator fails the build before that can ship. When the engine
needs to grow, move the workflow-scoped part into the skill that uses it instead.

## Releasing

```bash
scripts/release.sh 0.4.0
```

The script refuses to run on a dirty tree, checks that `CHANGELOG.md` has an entry for the version,
writes `VERSION`, bumps `plugin.json` and `marketplace.json` to match, runs the full validation,
commits, and tags. Push with `git push && git push --tags`.

Bumping `plugin.json`'s `version` is the part that matters: Claude Code falls back to the git commit
SHA when the field is absent, which makes every commit look like a new release. With the field set,
users receive an update when you bump it and not before.

## Versioning

Semver, from the perspective of a project using the kit:

- **patch** — wording, clarifications, a bug in a pipeline step
- **minor** — a new skill or agent; new behavior that needs no action from the owner
- **major** — a change that requires the owner to do something (a renamed command, a moved
  project-owned path, a manifest key with new semantics). Ship a `migrations/<version>.md` note.

## What must never end up in the plugin

- Anything project-specific: names, stacks, doc paths. Product knowledge is referenced through
  `manifest.sources.*`, never hardcoded. The validator greps for known project names.
- A file the project owns. `templates/project/` holds what bootstrap *copies* into a repository;
  once copied it belongs to that repository, and the plugin never writes there again.
- A reimplementation of something Claude Code ships. If a step could call `/code-review`,
  `/security-review`, `/verify`, or a built-in agent, it should — the kit's job is the ordering and
  the project context, not another review harness.
