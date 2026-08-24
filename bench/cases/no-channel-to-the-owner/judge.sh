#!/bin/sh
test -s "$BENCH/owner-was-never-configured" || { echo "the case never established that no channel was set"; exit 1; }
test ! -e "$BENCH/owner.out" || { echo "something was sent on a machine with no channel"; exit 1; }

grep -q '"how": "no-channel"' "$RUN_DIR/steps/0-design/asks.json" ||
  { echo "the question did not end as one nobody could be asked"; exit 1; }
grep -q 'нет канала к владельцу' "$RUN_DIR/steps/0-design/output.json" ||
  { echo "the default was taken and not written down as an assumption"; exit 1; }
exit 0
