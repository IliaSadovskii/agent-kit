# Updating the kit

```bash
.agent-kit/scripts/kit-update.sh              # latest release
.agent-kit/scripts/kit-update.sh --dry-run    # preview, write nothing
.agent-kit/scripts/kit-update.sh --ref v0.3.0 # pin a specific release
```

The shim reads the kit repository from `.agent-kit/kit.lock`, fetches that repository, and runs
`install.sh update` against your project. Equivalent, if you have a local clone:

```bash
bash ~/src/agent-kit/install.sh update --from ~/src/agent-kit
```

## How your edits survive

For every kit-owned file, `kit.lock` stores two checksums: what the release shipped, and what your
project had after the last run. Comparing both against the file on disk resolves the three cases
that matter:

| On disk | Upstream | Result |
|---|---|---|
| matches the last release | changed | **updated** — no history to lose |
| you edited it | unchanged since your edit | **kept, silently** — an accepted customization |
| you edited it | also changed | **conflict** — your file stays; the release copy is written to `<file>.kit-new` |

Conflicts are listed at the end of the run with a ready-to-paste `diff -u` per file. Resolve one by
merging what you want into your file and deleting the `.kit-new` copy. The next update sees your
merged file as the accepted local version, and stops reporting it — until upstream touches that file
again.

`--force` skips all of this and overwrites kit files with the release. It never touches user-owned
files.

## Files that disappear between releases

When a release drops a file your project got from an older one — a renamed workflow, a retired
wrapper — the updater deletes it if it still matches what was shipped, so stale commands do not
linger in the provider's discovery. If you had edited it, it stays and you get a warning.

## Checking state

```bash
bash install.sh status
```

```text
agent-kit 0.2.0
  source:    https://github.com/IliaSadovskii/agent-kit
  ref:       v0.2.0  (commit 4f2c…)
  installed: 2026-07-22T19:51:44Z
  providers: claude,codex
  files:     76

Locally modified kit files (an update will keep these and park the release copy):
  modified .agent-kit/workflows/ship.md

Latest release: v0.3.0 — run: install.sh update
```

`install.sh diff` prints the actual diff between the release and each locally modified file.

## Drift is a signal

A locally modified kit file means your project and the kit disagree. Two good resolutions, one bad:

- **Upstream it.** If the change is generally right, send it to the kit repository. Everything you
  own then keeps updating cleanly.
- **Move it out.** Project-specific rules belong in `.agent-kit/project/instructions.md`, which no
  update rewrites. Most local edits to `engine.md` or a workflow really belong there.
- **Carry a permanent local fork of a kit file.** Works — the updater keeps it — but every upstream
  change to that file becomes a manual merge. Do it knowingly, not by accident.

## Version pinning and migrations

`kit_version` is written to both `.agent-kit/kit.lock` and `.agent-kit/project/manifest.yml`. Pin a
release with `--ref` when you want a reproducible environment, e.g. in CI.

Releases that need a manual step ship a note in `migrations/<version>.md` in the kit repository; the
installer points at it when one exists for the version being installed. Anything the installer can
do itself, it does — migration notes are for what only the project owner can decide.

## Updating in a hosted session

Cloud sessions run with the network disabled during the agent phase. Either run the update during
the setup phase, or install from a local checkout with `--from`. If neither is possible, record it
as a manual action rather than retrying against a blocked proxy.
