#!/bin/sh
printf 'MINE = "quote"\n' >> money.py
printf 'here\n' > "$BENCH/quote.here"
# Both are editing money.py right now. Nothing here waits politely: the point
# is that they overlap and still cannot see each other.
n=0
while [ $n -lt 300 ]; do
  [ -f "$BENCH/rates.here" ] && [ -f "$BENCH/quote.here" ] && break
  n=$((n + 1)); sleep 0.1
done
[ -f "$BENCH/rates.here" ] && [ -f "$BENCH/quote.here" ] ||
  { echo "the other session was never alive at the same time" >&2; exit 1; }
printf 'met\n' > "$BENCH/quote.met"
grep -q 'MINE = "rates"' money.py &&
  { echo "this tree can see what the other session wrote" >&2; exit 1; }
exit 0
