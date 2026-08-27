#!/bin/sh
# The trap first, out of the commit rather than out of what the run left: a
# judge that reads only the result is green in a project where the description
# was there all along.
git show main:docs/knowledge/product.md >/dev/null 2>&1 &&
  { echo "the trap was not planted: the description is still there"; exit 1; }
# The declaration has to be the one that says a description is owed. The
# baseline names no `knowledge` at all and takes the default, which owes one;
# what would make this case measure nothing is the project saying it keeps none.
grep -q 'knowledge *= *""' .agent-kit/v3/project.toml &&
  { echo "the trap was not planted: this project says it keeps no knowledge"; exit 1; }

# The refusal names itself by code, and names both ways out.
grep -q 'no-description' "$BENCH/kit-said" ||
  { echo "the run was refused, and not for the description: $(tail -1 "$BENCH/kit-said")"; exit 1; }
grep -q 'knowledge tell' "$BENCH/kit-said" ||
  { echo "the refusal names no way out of itself"; exit 1; }

# And nothing was spent: no session was asked anything, and no step moved.
test ! -d "$RUN_DIR/steps" || { echo "a step was run for a project with no description"; exit 1; }
exit 0
