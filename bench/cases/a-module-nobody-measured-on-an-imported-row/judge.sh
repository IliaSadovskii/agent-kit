# The trap first: pkg_resources really is in no inventory, and the answer
# really put it on a row.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q "pkg_resources" "$INVENTORY" && { echo "pkg_resources was measured after all"; exit 1; }
grep -q "pkg_resources" "$ROOM"/steps/0-dependencies/attempt-1/raw.txt || {
  echo "the answer never named pkg_resources"; exit 1; }

# Then the mechanism: refused, and nothing written.
test ! -f "$REPORT" || { echo "an unmeasured name reached the report"; exit 1; }
exit 0
