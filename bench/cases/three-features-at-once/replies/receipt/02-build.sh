#!/bin/sh
printf 'RATE = 20\n' >> receipt.py
printf 'ok\n' > "$BENCH/receipt.here"
# The whole proof of *at once*: this session does not finish until the other
# two are alive too. Sequential building never gets past this line.
n=0
while [ $n -lt 300 ]; do
  if [ -f "$BENCH/rates.here" ] && [ -f "$BENCH/quote.here" ] && [ -f "$BENCH/receipt.here" ]; then
    printf 'met\n' > "$BENCH/receipt.met"
    exit 0
  fi
  n=$((n + 1))
  sleep 0.1
done
echo "the other sessions were never alive at the same time" >&2
exit 1
