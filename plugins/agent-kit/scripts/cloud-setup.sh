#!/usr/bin/env bash
# SessionStart hook: let a hosted session provision its own dependencies.
#
# The kit does not know how to install anything — the project does, in an idempotent
# scripts/cloud-setup.sh that idea-interview generates at bootstrap. A project without one is the
# normal case before bootstrap, so a missing script is silent success.
set -u

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT_SETUP="$ROOT/scripts/cloud-setup.sh"

[ -f "$PROJECT_SETUP" ] || exit 0

# Diagnostics go to stderr; this hook's stdout would otherwise land in the model's context.
if ! bash "$PROJECT_SETUP" >&2; then
  echo "agent-kit: scripts/cloud-setup.sh failed; the session continues without it." >&2
fi
exit 0
