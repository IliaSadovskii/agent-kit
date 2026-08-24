#!/bin/sh
test -s "$BENCH/owner-was-never-configured" || { echo "the case never established that no channel was set"; exit 1; }
test ! -e "$BENCH/owner.out" || { echo "something was sent on a machine with no channel"; exit 1; }

# Код исхода, а не фраза: прозу перепишут, и случай станет мерить предложение.
grep -q '"how": "no-channel"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the question did not end as one nobody could be asked"; exit 1; }

# И умолчание записано как дорогое допущение — по форме записи, не по словам.
grep -q '"expensive": true' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default was taken and not written down as an expensive assumption"; exit 1; }
exit 0
