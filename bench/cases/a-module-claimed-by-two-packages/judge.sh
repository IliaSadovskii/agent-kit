# The trap first: yaml really was measured once, and both rows really claimed it.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"module": "yaml"' "$INVENTORY" || { echo "yaml was never measured"; exit 1; }
grep -q '"tabulate", "yaml"' "$ROOM"/steps/0-dependencies/attempt-1/raw.txt || {
  echo "the answer did not claim yaml twice"; exit 1; }

# Then the mechanism: refused, and nothing written.
test ! -f "$REPORT" || { echo "a module claimed twice reached the report"; exit 1; }
exit 0
