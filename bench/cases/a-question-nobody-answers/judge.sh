#!/bin/sh
# The trap first: the question really went out, under the name the kit derives
# from the run and the question's own words. A judge that reads only the end
# state is green against a kit that never asked anybody anything.
test -s "$BENCH/owner.out" || { echo "no question ever went to the owner"; exit 1; }
grep -q 'one VAT rate for everything, or one per country?' "$BENCH/owner.out" || { echo "what went out is not the question the design asked"; exit 1; }
grep -q '2xdhdn' "$BENCH/owner.out" || { echo "the question went out under a name the kit would not derive again"; exit 1; }
test ! -s "$BENCH/owner.in" 2>/dev/null || { echo "somebody answered, so this case measured the wrong ending"; exit 1; }

# Nobody answered, so the default was taken and the step ran once.
test -f "$RUN_DIR/steps/0-design/asks.json" || { echo "nothing was written down about the question"; exit 1; }
grep -q '"how": "nobody-answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the question did not end in silence"; exit 1; }
test ! -d "$RUN_DIR/steps/0-design/attempt-2" ||
  { echo "the design ran twice, and nobody had answered"; exit 1; }

# And the default reached the owner's knowledge as an expensive assumption.
grep -q 'Никто не ответил' docs/knowledge/entities.md ||
  { echo "the default nobody answered left no block in the knowledge"; exit 1; }
git show --name-only --format= HEAD | grep -q 'docs/knowledge/entities.md' ||
  { echo "the block was written but never committed"; exit 1; }
exit 0
