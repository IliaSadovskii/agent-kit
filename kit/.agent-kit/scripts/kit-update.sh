#!/usr/bin/env bash
#
# Update the agent kit installed in this project.
#
#   .agent-kit/scripts/kit-update.sh              # update to the latest release
#   .agent-kit/scripts/kit-update.sh --dry-run    # show what would change
#   .agent-kit/scripts/kit-update.sh --ref v0.3.0 # pin a specific release
#
# A convenience shim so a project never has to remember the installer URL: it reads the kit
# repository from .agent-kit/kit.lock, downloads that release's installer, and runs `update`.
# Local edits to kit files are preserved — see `install.sh status`.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOCK="$ROOT/.agent-kit/kit.lock"

[ -f "$LOCK" ] || {
  printf 'error: %s not found — this project has no installer-managed kit.\n' "$LOCK" >&2
  exit 1
}

REPO="$(sed -n 's/^source: \{1,\}//p' "$LOCK" | head -1)"
[ -n "$REPO" ] || {
  printf 'error: no `source:` recorded in %s\n' "$LOCK" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --quiet --depth 1 "$REPO" "$TMP/kit" || {
  printf 'error: could not clone %s\n' "$REPO" >&2
  exit 1
}

exec bash "$TMP/kit/install.sh" update --dir "$ROOT" --repo "$REPO" "$@"
