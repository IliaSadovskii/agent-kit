# The trap first: there really were three dependencies in the inventory, and the
# session really answered for two of them.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
test "$(grep -c '"name":' "$INVENTORY")" = "3" || { echo "the inventory did not hold three dependencies"; exit 1; }
grep -q "ruff" "$ROOM"/steps/0-dependencies/attempt-1/raw.txt && { echo "the answer named ruff after all"; exit 1; }

# Then the mechanism: the one it left out is named, and nothing is written.
grep -q "ruff" "$BENCH/kit-said" || { echo "the refusal does not name what was missing"; exit 1; }
test ! -f "$REPORT" || { echo "half a reading reached a report"; exit 1; }
exit 0
