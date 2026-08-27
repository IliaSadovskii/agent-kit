# The trap first: ruff really was declared, really was imported nowhere, and the
# session really called it used without saying why.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"name": "ruff"' "$INVENTORY" || { echo "ruff was never declared here"; exit 1; }
grep -q "used-without-importing" "$ROOM"/steps/0-dependencies/attempt-1/raw.txt || {
  echo "the answer never claimed a plugin"; exit 1; }

# Then the mechanism: refused, and nothing written.
test ! -f "$REPORT" || { echo "an unexplained claim reached the report"; exit 1; }
exit 0
