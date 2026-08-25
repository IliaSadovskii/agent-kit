#!/bin/sh
# The trap first: every session really did stand at the rendezvous.
for slug in rates quote receipt; do
  test -s "$BENCH/$slug.here" || { echo "$slug never started a build session"; exit 1; }
  test -s "$BENCH/$slug.met" || { echo "$slug never met the others, so nothing was at once"; exit 1; }
done

for slug in rates quote receipt; do
  git rev-parse --verify "kit/$slug" >/dev/null 2>&1 || { echo "$slug left no branch"; exit 1; }
done
test "$(grep -c -- '--head' "$BENCH/gh-argv")" -ge 3 || { echo "three features, fewer than three pull requests"; exit 1; }
exit 0
