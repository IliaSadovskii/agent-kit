#!/bin/sh
# The trap first: the project really does declare no command.
grep -q '^\[commands\]' .agent-kit/v3/project.toml &&
  { echo "the trap was not planted: the project still declares a command"; exit 1; }

# The refusal names itself by code, and not by a sentence anybody can rewrite.
grep -q 'no-commands' "$BENCH/kit-said" ||
  { echo "refused, and not for the commands: $(tail -1 "$BENCH/kit-said")"; exit 1; }

# And nothing was made. Not a batch, not a run, not a tree: a night refused at
# the gate leaves no graph for anybody to repair by hand.
test ! -d .agent-kit/v3/batches || { echo "a batch was created for a night that cannot start"; exit 1; }
test ! -d .agent-kit/v3/runs    || { echo "a run was created for a night that cannot start"; exit 1; }
test ! -d "$TREES"              || { echo "a tree was made for a night that cannot start"; exit 1; }
exit 0
