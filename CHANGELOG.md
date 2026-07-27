# Changelog

All notable changes to the kit. Versions follow semver from the perspective of a project that
installed it — see [docs/developing.md](docs/developing.md#versioning).

## 0.3.0

The kit targets Claude Code only. Codex support is removed rather than left to rot: it doubled
every surface — two adapter trees, two root instruction files, two description columns per catalog
row, a provider switch through the installer and both validators — while only one of them was
actually used. See [migrations/0.3.0.md](migrations/0.3.0.md) for the manual cleanup an installed
project needs.

### Removed

- The Codex payload: `.agents/skills/`, `.codex/agents/`, `AGENTS.md` and its managed block, and
  the `.codex/hooks.json` template.
- `install.sh --providers`, the `providers:` key in `kit.lock`, and the providers line in
  `install.sh status`.
- `.agent-kit/platforms/`. The provider abstraction had one implementation left; its three
  Claude-specific rules moved into `.agent-kit/engine.md`.

### Changed

- `catalog.tsv` drops the per-provider columns: `claude_desc`/`codex_desc` collapse to `desc`,
  `claude_note`/`codex_note` to `note`, and the Codex-only `sandbox` column is gone.
- `scripts/generate-adapters.py` emits only `.claude/` wrappers; the payload is 22 generated files
  instead of 41.
- Both validators check a single adapter surface. The repository validator additionally asserts
  that no Codex artefact reappears in the payload or in a fresh install.

## 0.2.0

First release as a standalone repository. The kit previously lived inside the project it was
developed in; the behavior is unchanged, the distribution is new.

### Added

- `install.sh` — install, update, status, diff, and uninstall, with `--dry-run`, `--ref`,
  `--from`, `--providers`, and `--force`.
- `.agent-kit/kit.lock` — records the installed version, source ref, and two checksums per file, so
  an update can tell an untouched file from one the project customized.
- `.agent-kit/scripts/kit-update.sh` — in-project update shim; no URL to remember.
- `catalog.tsv` + `scripts/generate-adapters.py` — every provider wrapper is generated from one
  authoring source, and CI fails if the payload drifts from it.
- `scripts/validate.sh` — validates the payload, performs a real install into a scratch repository,
  and asserts the update semantics (idempotent re-run, preserved local edits, untouched user files).
- Clean `templates/` for the user-owned corner: an unbootstrapped manifest, neutral project
  instructions, and root instruction files with the managed-block markers.

### Changed

- Role wrappers now also read the provider platform adapter, and every wrapper body is generated,
  so the four adapter surfaces stay consistent.
- `.claude/settings.json` and `.codex/hooks.json` are treated as shared project files: the installer
  adds its SessionStart hook once and never rewrites them.
- The in-project validator resolves the project root from its own location instead of the caller's
  working directory.
