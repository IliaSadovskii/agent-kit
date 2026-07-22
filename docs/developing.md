# Developing the kit

## Repository layout

```text
kit/                    the payload — copied verbatim into a project
  .agent-kit/           canonical behavior (no project/ — that is generated per project)
  .claude/ .agents/ .codex/   generated discovery wrappers
  root/*.block.md       the managed blocks spliced into CLAUDE.md / AGENTS.md
templates/              installed only when the target file does not exist yet
catalog.tsv             authoring source for every wrapper
install.sh              install / update / status / diff / uninstall
scripts/                generate-adapters.py, validate.sh, release.sh
migrations/<version>.md notes for a release that needs a manual step
```

The invariant behind all of it: **canonical behavior lives in exactly one file under
`kit/.agent-kit/`, and every provider wrapper is a generated pointer to it.** `scripts/validate.sh`
fails a wrapper that grows past 20 lines or stops referencing `.agent-kit/`.

## Adding a workflow

1. Write the canonical pipeline in `kit/.agent-kit/workflows/<name>.md`.
2. Add one row to `catalog.tsv`.
3. `scripts/generate-adapters.py` — writes the Claude command, the Codex skill, and refreshes
   `kit/.agent-kit/catalog.txt`.
4. `scripts/validate.sh`.

Adding a skill or a role is the same, with the canonical file under `skills/` or `roles/`.

Removing one is symmetric: drop the row and the canonical file, regenerate (the generator deletes
the orphaned wrappers), and the next `install.sh update` removes them from projects too.

## catalog.tsv columns

| Column | Meaning |
|---|---|
| `kind` | `workflow`, `skill`, or `role` |
| `name` | slug; must match the canonical file name |
| `title` | reads as "Execute the canonical **&lt;title&gt;** with …" |
| `claude_desc` / `codex_desc` | the description each provider shows in its picker |
| `also` | an extra canonical file the wrapper must read; `refs` on a skill means "and its references" |
| `tools` | Claude subagent tool list (roles) |
| `sandbox` | Codex `sandbox_mode` (roles) |
| `claude_note` / `codex_note` | one extra sentence in the wrapper body |

Empty columns are written as `-`. `scripts/generate-adapters.py --check` fails CI when the payload
has drifted from this file.

## Testing a change against a real project

```bash
bash install.sh install --from . --dir /path/to/scratch-project --dry-run
bash install.sh install --from . --dir /path/to/scratch-project
```

`scripts/validate.sh` already does this against a throwaway repository, and additionally asserts the
update semantics: a second update changes nothing, a locally edited file is preserved and reported
as a conflict, and user-owned files are never overwritten.

## Releasing

```bash
scripts/release.sh 0.3.0
```

The script refuses to run on a dirty tree, checks that `CHANGELOG.md` has an entry for the version,
writes `VERSION`, runs the full validation, commits, and tags `v0.3.0`. Push with
`git push && git push --tags`.

Projects install the highest semver tag by default, so a release becomes live for everyone the
moment the tag is pushed. Nothing auto-updates: each project decides when to run the updater.

## Versioning

Semver, from the perspective of a project that installed the kit:

- **patch** — wording, clarifications, a bug in a workflow step
- **minor** — a new workflow, skill, or role; new behavior that needs no action from the owner
- **major** — a change that requires the owner to do something (a moved user-owned path, a manifest
  key with new semantics, a removed command). Ship a `migrations/<version>.md` note with it.

## What must never end up in the payload

- Anything project-specific: names, stacks, doc paths. Product knowledge is referenced through
  `manifest.sources.*`, never hardcoded. The validator greps for known project names.
- Behavior inside a provider wrapper.
- Provider-specific tool names or invocation syntax inside `.agent-kit/` — those belong in
  `.agent-kit/platforms/`.
- A user-owned file inside `kit/`. `templates/` is for files the project takes ownership of;
  `kit/` is for files the installer may overwrite.
