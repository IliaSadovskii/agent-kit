#!/usr/bin/env bash
# SessionStart hook: put the kit's always-on governance into context.
#
# Claude Code adds a SessionStart hook's stdout to the session context, so printing the file is
# enough — no JSON envelope, no escaping, no python. Hook output is capped at 10,000 characters;
# engine.md is kept well under that on purpose, and the pipelines load their own detail on demand.
set -eu

ENGINE="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is not set}/engine.md"

[ -f "$ENGINE" ] || exit 0
cat "$ENGINE"
