# The trap first: requests really is imported here, really is declared nowhere,
# and the first attempt really did hang it on PyYAML.
test -s "$INVENTORY" || { echo "no inventory was written"; exit 1; }
grep -q '"module": "requests"' "$INVENTORY" || { echo "requests is imported nowhere here"; exit 1; }
grep -q '"name": "requests"' "$INVENTORY" && { echo "requests is declared after all"; exit 1; }
grep -q '"requests"' "$ROOM"/steps/0-dependencies/attempt-1/raw.txt || {
  echo "the first attempt never named requests"; exit 1; }
grep -q '"yaml", "requests"' "$ROOM"/steps/0-dependencies/attempt-1/raw.txt || {
  echo "the first attempt did not hang requests on PyYAML"; exit 1; }

# The refusal happened and it named the right thing.
test -f "$ROOM"/steps/0-dependencies/attempt-1/refusal.txt || { echo "the first attempt was not refused"; exit 1; }
grep -q "no-reason-to-remove" "$ROOM"/steps/0-dependencies/attempt-1/refusal.txt || {
  echo "the first attempt was refused for something else: $(cat "$ROOM"/steps/0-dependencies/attempt-1/refusal.txt)"; exit 1; }

# Then the mechanism: the hidden import is a finding. Read in the report and
# not in the candidate list, because whether a candidate list gets written at
# all is somebody else's mechanism, and a judge that reddens for a neighbour's
# break is a judge that cannot say what it measures.
test -s "$REPORT" || { echo "no report was written"; exit 1; }
grep -q "^## Объявить" "$REPORT" || { echo "the report found nothing to declare"; exit 1; }
grep -q '^- `requests`' "$REPORT" || { echo "requests did not reach the findings"; cat "$REPORT"; exit 1; }
exit 0
