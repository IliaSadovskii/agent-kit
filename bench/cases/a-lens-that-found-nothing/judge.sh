# The trap first: there really were two dependencies to answer for, and both
# were really measured as imported. Without this the case is green over a
# project the lens never looked at.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"name": "PyYAML"' "$INVENTORY" || { echo "PyYAML was not measured"; exit 1; }
grep -q '"module": "yaml"' "$INVENTORY" || { echo "the import of yaml was not measured"; exit 1; }

# Then the mechanism: it said so, in a report, with the count in it.
test -s "$REPORT" || { echo "a lens that found nothing wrote no report"; exit 1; }
grep -q "Найдено: 0" "$REPORT" || { echo "the report does not say that nothing was found"; exit 1; }
grep -q "PyYAML" "$REPORT" || { echo "the report does not account for PyYAML"; exit 1; }

# And no candidate list: a file saying «nothing to do» in prose is not an
# answer a script can read, and `test -s` is.
test ! -f "$CANDIDATES" || { echo "a lens with no findings wrote a candidate list"; exit 1; }
