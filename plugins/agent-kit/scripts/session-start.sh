#!/usr/bin/env bash
# SessionStart hook: put the kit's always-on governance into context, and the run this branch is
# in the middle of.
#
# Claude Code adds a SessionStart hook's stdout to the session context, so printing the file is
# enough — no JSON envelope, no escaping, no python. Hook output is capped at 10,000 characters;
# engine.md is kept well under that on purpose, `gate.py state` caps its own share, and
# scripts/validate.sh holds the sum below the limit. Past the cap the output is written to a file
# and replaced with a preview, so the governance would silently stop being always-on.
#
# A resumed or compacted session is the one that most needs the second half: it has lost the run's
# working memory and would otherwise have to be told where it stands. `gate.py state` prints
# nothing at all when this branch has no unfinished run, and is never allowed to fail the hook.
set -eu

ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is not set}"

[ -f "$ROOT/engine.md" ] || exit 0
cat "$ROOT/engine.md"

python3 "$ROOT/scripts/gate.py" state 2>/dev/null || true
