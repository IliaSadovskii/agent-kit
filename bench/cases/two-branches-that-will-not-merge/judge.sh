#!/bin/sh
# The trap first: both really landed, and both really rewrote that line.
for slug in rates quote; do
  test "$(git rev-list --count main..kit/$slug)" -ge 1 || { echo "$slug did not land"; exit 1; }
done
git show kit/rates:money.py | grep -q 'rates' || { echo "rates did not rewrite the line"; exit 1; }
git show kit/quote:money.py | grep -q 'quote' || { echo "quote did not rewrite the line"; exit 1; }

# The branch and the file, and both of them are this case's own planting. The sentence around them said `will not merge`, and
# a case that greps that is measuring an English sentence: it went red the day
# the screens were translated and the mechanism had not moved. A branch in
# brackets appears nowhere else in the message — the per-feature lines carry a
# slug and a pull request — so finding both is finding the conflict report.
# The kit names the branch that will not go in over what is already there, so
# it is the second of the two — one conflict, not two. Both are checked above:
# this is about what the person was told.
grep -qF "(kit/quote)" "$BENCH/kit-said" ||
  { echo "nobody was told which branch will not merge"; exit 1; }
grep -q 'money.py' "$BENCH/kit-said" || { echo "the conflict does not name the file"; exit 1; }

# And nothing was merged, pushed or left behind by the asking.
test "$(git rev-parse main)" = "$(git rev-parse origin/main)" || { echo "the trunk was moved"; exit 1; }
git worktree list | grep -q 'merge-check' && { echo "the scratch tree was left behind"; exit 1; }
test -z "$(git status --porcelain)" || { echo "the merge check left the project dirty"; exit 1; }
exit 0
