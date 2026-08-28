#!/bin/sh
# The trap first: a kind really is answered with a command that cannot fail,
# and the project really does declare the same word where it is allowed.
grep -q 'command = "true"' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: no kind is proved by a no-op"; exit 1; }
grep -q 'lint = "true"' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: the allowed half of it is not there"; exit 1; }

grep -q 'command-that-proves-nothing' "$BENCH/kit-said" ||
  { echo "the answer was not refused by name: $(tail -1 "$BENCH/kit-said")"; exit 1; }
grep -q 'no-such-command' "$BENCH/kit-said" &&
  { echo "it was refused for the wrong question: this command starts"; exit 1; }

# And nothing was spent: no session was asked anything, and no step moved.
test ! -d "$RUN_DIR/steps" || { echo "a step was run for a project whose kind proves nothing"; exit 1; }
exit 0
