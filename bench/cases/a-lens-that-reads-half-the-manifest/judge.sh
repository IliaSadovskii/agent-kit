# The trap first: there really were two dependencies in the inventory, and the
# session really answered for one of them.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
test "$(grep -c '"name":' "$INVENTORY")" = "2" || { echo "the inventory did not hold two dependencies"; exit 1; }
grep -q "tabulate" "$ROOM"/steps/0-dependencies/attempt-1/raw.txt && { echo "the answer named tabulate after all"; exit 1; }

# Then the mechanism: refused, and nothing written.
test ! -f "$REPORT" || { echo "half a reading reached a report"; exit 1; }
exit 0
