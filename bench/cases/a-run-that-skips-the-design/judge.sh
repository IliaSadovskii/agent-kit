#!/bin/sh
# The trap first: this run really has no design in it, and the project really
# does check itself for a kind somebody had to answer for.
grep -q 'verification.suite' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project answers no kind of verification"; exit 1; }
test ! -d "$RUN_DIR/steps/0-design" ||
  { echo "the trap was not planted: the run carries a design after all"; exit 1; }
test -d "$RUN_DIR/steps/0-build" ||
  { echo "the trap was not planted: nothing was built"; exit 1; }
grep -q 'touch ran' check.sh ||
  { echo "the trap was not planted: the project's command leaves nothing behind when it runs"; exit 1; }

grep -q 'kind-unproved' "$RUN_DIR/run.json" ||
  { echo "verify did not ask what nobody had answered: $(tail -1 "$BENCH/kit-said")"; exit 1; }

# And it asked before the suite was paid for. The refusal was knowable before
# the first command, so a run that pays for one first buys nothing with it.
test ! -f ran ||
  { echo "the project's command ran before the kind nobody answered was asked about"; exit 1; }
exit 0
