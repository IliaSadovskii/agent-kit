#!/usr/bin/env bash
# PreToolUse hook on Write and Edit: keep the step gate's run state out of the agent's reach.
#
# A step is closed by the gate, never by the agent, and that is only true while the agent cannot
# write the file the verdict lives in. The Bash guard refuses a shell command that names
# `.agent-kit/runs`; this refuses the tool call that would do the same thing directly.
#
# The decision is "deny", not "ask": the never-rules ask because a human is usually there to
# confirm, but nothing legitimate ever writes run state by hand, and a headless sprint child has
# nobody to answer.
#
# The path matching lives in write-guard.py, sharing the Bash guard's own rule — two spellings of
# one rule are two sets of bugs.
set -u
exec python3 "$(dirname "$0")/write-guard.py"
