#!/bin/sh
# The trap first: both sessions were alive at once and both edited one file.
for slug in rates quote; do
  test -s "$BENCH/$slug.met" || { echo "$slug never overlapped with the other"; exit 1; }
done

# Each commit holds its own line and not the other's.
git show kit/rates:money.py | grep -q 'MINE = "rates"' || { echo "rates did not commit its own change"; exit 1; }
git show kit/rates:money.py | grep -q 'MINE = "quote"' && { echo "rates committed quote's work"; exit 1; }
git show kit/quote:money.py | grep -q 'MINE = "quote"' || { echo "quote did not commit its own change"; exit 1; }
git show kit/quote:money.py | grep -q 'MINE = "rates"' && { echo "quote committed rates' work"; exit 1; }

# And the project's own working copy was never touched by either of them.
test "$(git rev-parse --abbrev-ref HEAD)" = main || { echo "the project was left on somebody's branch"; exit 1; }
test -z "$(git status --porcelain)" || { echo "the project's working copy was written into"; exit 1; }
exit 0
