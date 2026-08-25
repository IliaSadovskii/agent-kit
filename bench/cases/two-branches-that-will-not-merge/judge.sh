#!/bin/sh
# The trap first: both really landed, and both really rewrote that line.
for slug in rates quote; do
  test "$(git rev-list --count main..kit/$slug)" -ge 1 || { echo "$slug did not land"; exit 1; }
done
git show kit/rates:money.py | grep -q 'rates' || { echo "rates did not rewrite the line"; exit 1; }
git show kit/quote:money.py | grep -q 'quote' || { echo "quote did not rewrite the line"; exit 1; }

grep -q 'will not merge' "$BENCH/kit-said" || { echo "nobody was told these two will not merge"; exit 1; }
grep -q 'money.py' "$BENCH/kit-said" || { echo "the conflict does not name the file"; exit 1; }

# And nothing was merged, pushed or left behind by the asking.
test "$(git rev-parse main)" = "$(git rev-parse origin/main)" || { echo "the trunk was moved"; exit 1; }
git worktree list | grep -q 'merge-check' && { echo "the scratch tree was left behind"; exit 1; }
test -z "$(git status --porcelain)" || { echo "the merge check left the project dirty"; exit 1; }
exit 0
