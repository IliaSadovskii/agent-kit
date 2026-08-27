# The trap first: the inventory really measured tabulate as imported, and the
# session really called it unused. A judge that only checks that nothing was
# written is green where no lens ever ran.
test -s "$INVENTORY" || { echo "no inventory was written, so nothing was measured"; exit 1; }
grep -q '"module": "tabulate"' "$INVENTORY" || { echo "tabulate is not in the measured imports"; exit 1; }
grep -q '"unused"' "$ROOM"/steps/0-dependencies/attempt-*/raw.txt || { echo "no attempt called anything unused"; exit 1; }

# Then the mechanism: nothing reached a report or a candidate list.
test ! -f "$REPORT" || { echo "an invented finding reached the report"; exit 1; }
test ! -f "$CANDIDATES" || { echo "an invented finding reached the candidates"; exit 1; }
