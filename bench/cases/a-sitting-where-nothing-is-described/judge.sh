#!/bin/sh
# The trap first: this project really does say out loud that it keeps none.
grep -q 'knowledge = ""' .agent-kit/v3/project.toml ||
  { echo "the trap was not planted: this project declares a knowledge after all"; exit 1; }

grep -q 'no-knowledge-declared' "$BENCH/kit-said" ||
  { echo "refused, and not for the declaration: $(tail -1 "$BENCH/kit-said")"; exit 1; }
# It names the way out, which is the line the owner has to delete.
grep -q 'knowledge = ""' "$BENCH/kit-said" ||
  { echo "the refusal names no way out of itself"; exit 1; }

# Nothing was spent and nothing was written: not a session, not a room, not a file.
test ! -d .agent-kit/v3/sittings || { echo "a sitting left paperwork it had nowhere to write"; exit 1; }
# The baseline's own description is still there and untouched: a project that
# says it keeps none is not a project whose files the kit may rewrite.
git diff --quiet -- docs/ || { echo "a file was written into a knowledge nobody declared"; exit 1; }
grep -q 'Google и Apple' docs/knowledge/product.md &&
  { echo "the telling was written into a knowledge nobody declared"; exit 1; }
exit 0
