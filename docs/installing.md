# Installing the kit

## Requirements

- `bash` 4+, `git`, and `sha256sum` or `shasum`
- `python3` — optional; only used to merge the kit's SessionStart hook into a `.claude/settings.json`
  or `.codex/hooks.json` your project already has

## The one-liner

```bash
cd your-project
curl -fsSL https://raw.githubusercontent.com/IliaSadovskii/agent-kit/main/install.sh \
  | bash -s -- install
```

Piping a script from the internet into `bash` is a trust decision. If you would rather look first:

```bash
curl -fsSL -o /tmp/agent-kit-install.sh \
  https://raw.githubusercontent.com/IliaSadovskii/agent-kit/main/install.sh
less /tmp/agent-kit-install.sh
bash /tmp/agent-kit-install.sh install
```

Without `--ref`, the installer resolves the highest semver tag on the remote and installs that
release — not the tip of `main`.

## Options

| Flag | Effect |
|---|---|
| `--dir <path>` | Target project (default: the Git root of the current directory) |
| `--ref <tag>` | Install a specific release, branch, or commit |
| `--from <path>` | Install from a local kit checkout — no network |
| `--repo <url>` | Install from a fork |
| `--providers claude,codex` | Which adapters to install (default: both) |
| `--dry-run` | Print every action, write nothing |
| `--force` | Overwrite locally modified kit files instead of reporting conflicts |

## What lands in your project

```text
.agent-kit/                 canonical behavior (kit-owned)
  project/                  manifest.yml + instructions.md — created once, then yours
  kit.lock                  version, source ref, and per-file checksums
  scripts/kit-update.sh     update shim
.claude/                    commands, skills, agents (Claude Code)
.agents/  .codex/           skills and custom agents (Codex)
CLAUDE.md  AGENTS.md        managed block + your own overrides
.gitignore                  one line: .claude/settings.local.json
```

Commit all of it. The kit is vendored deliberately: the agent reads ordinary files in your
repository, code review sees exactly what governs the agent, and nothing depends on a network fetch
at session start.

## Installing into a repository that already has agent instructions

This is the normal case and it is safe:

- **`CLAUDE.md` / `AGENTS.md` already exist** — the kit's bootstrap goes into a
  `<!-- kit:managed:start -->…<!-- kit:managed:end -->` block at the top; everything you wrote stays
  below it, and future updates only ever rewrite what is between the markers. The installer warns
  when it has to create the block for the first time.
- **`.claude/settings.json` already exists** — the kit appends only its `SessionStart` hook, leaving
  your permissions and other hooks untouched. If the hook is already there, nothing happens.
- **You already have `docs/`** — the kit never moves or duplicates product documentation. Bootstrap
  records where each document lives in `.agent-kit/project/manifest.yml` and reads it from there.

Files the installer will never overwrite, on any run, with or without `--force`:
`.agent-kit/project/*`, your product docs, your source, and anything outside the managed blocks.

## Choosing providers

`--providers claude` installs `.claude/` and `CLAUDE.md` only; `--providers codex` installs
`.agents/`, `.codex/`, and `AGENTS.md`. `.agent-kit/` is shared and always installed. The choice is
recorded in `kit.lock` and reused on update, so you set it once. To add a provider later:

```bash
bash install.sh update --providers claude,codex
```

## After installing

1. **Review the diff and commit.**
2. **Start a new session** — Claude Code and Codex read skills and subagents at startup, so an
   already-running session will not see them.
3. **Run `/go`** (Claude Code) or `$go` (Codex).

On a project with no manifest, or with `bootstrapped: false`, `/go` runs the one-time interview: it
asks about the product, records existing documentation by path, generates only the foundations that
are missing, fills in `.agent-kit/project/instructions.md` with your real commands, and opens a
bootstrap PR. Merge it, then invoke `/ship` for the first feature.

## Verifying an install

```bash
.agent-kit/scripts/validate.sh   # structure, catalog coverage, no provider leakage
bash install.sh status           # version, source ref, local modifications
```

## Uninstalling

```bash
bash install.sh uninstall
```

Removes every file recorded in `kit.lock` and the lock itself. Your project's own files stay,
including `.agent-kit/project/` and the managed blocks in `CLAUDE.md` / `AGENTS.md` — delete those
blocks by hand, since after uninstalling they import files that no longer exist.
