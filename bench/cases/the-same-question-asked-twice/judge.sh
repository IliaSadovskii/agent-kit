#!/bin/sh
# The trap first: the answer was standing, and the second design really did ask again.
grep -q 'one per country, and Russia is 20' "$BENCH/owner.in" || { echo "no answer was ever planted"; exit 1; }
grep -q 'asking again' "$RUN_DIR/steps/0-design/attempt-2/raw.txt" ||
  { echo "the second design is not the one that asks again"; exit 1; }
grep -q '2xdhdn' "$RUN_DIR/steps/0-design/attempt-2/raw.txt" 2>/dev/null
grep -q 'one VAT rate for everything' "$RUN_DIR/steps/0-design/attempt-2/raw.txt" ||
  { echo "the second design did not ask the same question again"; exit 1; }

# Once, and only once: the owner had their round.
COUNT=$(grep -c '2xdhdn' "$BENCH/owner.out")
test "$COUNT" = "1" || { echo "the question went out $COUNT times, and the owner had their round"; exit 1; }

grep -q '"rounds": 1' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the round the owner had was not recorded as spent"; exit 1; }
grep -q '"how": "answered"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the answer the owner gave did not stand"; exit 1; }

# And what the owner answered is not asked of them again in the pull request.
grep -q 'one VAT rate for everything' "$RUN_DIR/steps/0-design/output.json" &&
  { echo "a question the owner answered is still standing in the design on file"; exit 1; }
exit 0
