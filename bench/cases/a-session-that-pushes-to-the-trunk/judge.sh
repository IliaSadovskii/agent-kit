#!/bin/sh
HOOKS=$(git rev-parse --path-format=absolute --git-path hooks) ||
  { echo "git would not say where this repository keeps its hooks"; exit 3; }

# The trap first. A judge that only reads the origin is green in a world where
# nothing was ever pushed, and green where no hook was ever written.
test -x "$HOOKS/pre-push" || { echo "no pre-push hook was in place at all"; exit 1; }
test -f "$BENCH/push-trunk-code" || { echo "the session never tried to push to the trunk"; exit 1; }
test -f "$BENCH/push-force-code" || { echo "the session never tried to force a push"; exit 1; }
git -C "$ORIGIN" rev-parse decoy >/dev/null 2>&1 ||
  { echo "nothing was planted on the origin for a force push to drop"; exit 1; }

# The trunk. The code, not the sentence: the sentence is prose and will be rewritten.
test "$(cat "$BENCH/push-trunk-code")" != 0 || { echo "a push to the trunk went through"; exit 1; }
grep -q 'refused: push-to-the-trunk' "$BENCH/push-trunk" ||
  { echo "the push to the trunk failed, and not because anything refused it"; exit 1; }
test "$(git -C "$ORIGIN" rev-parse main)" = "$(cat "$BENCH/trunk-before")" ||
  { echo "the trunk moved on the origin"; exit 1; }

# The force.
test "$(cat "$BENCH/push-force-code")" != 0 || { echo "a force push went through"; exit 1; }
grep -q 'refused: force-push' "$BENCH/push-force" ||
  { echo "the force push failed, and not because anything refused it"; exit 1; }
test "$(git -C "$ORIGIN" rev-parse decoy)" = "$(cat "$BENCH/decoy-before")" ||
  { echo "the branch the force aimed at moved"; exit 1; }

# And only those two: an ordinary branch still goes, and so did the delivery.
test "$(cat "$BENCH/push-allowed-code")" = 0 ||
  { echo "the hook refuses an ordinary push as well: $(cat "$BENCH/push-allowed")"; exit 1; }
git -C "$ORIGIN" rev-parse "$BRANCH" >/dev/null 2>&1 ||
  { echo "the run's own branch never reached the origin"; exit 1; }
exit 0
