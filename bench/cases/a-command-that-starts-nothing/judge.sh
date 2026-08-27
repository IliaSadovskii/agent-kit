#!/bin/sh
# The trap first: the project really does declare a command this machine has
# no way to start.
grep -q 'definitely-not-a-command' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: no such command is declared"; exit 1; }
command -v definitely-not-a-command >/dev/null 2>&1 &&
  { echo "the trap was not planted: this machine can start it after all"; exit 1; }

# The refusal names itself, by code and not by sentence.
grep -q 'no-such-command' "$BENCH/kit-said" ||
  { echo "the run was refused, and not for the command: $(tail -1 "$BENCH/kit-said")"; exit 1; }

# And nothing was spent: no session was asked anything, and no step moved.
test ! -d "$RUN_DIR/steps" || { echo "a step was run for a project that cannot be verified"; exit 1; }
exit 0
