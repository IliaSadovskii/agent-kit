#!/bin/sh
# The trap first: the repository really had nothing written down, and the hour
# really did produce a ledger and no parts.
git show main:docs/knowledge/product.md >/dev/null 2>&1 &&
  { echo "the trap was not planted: a description was there before the sitting"; exit 1; }
test -s docs/knowledge/debt.md || { echo "the trap was not planted: the ledger is empty"; exit 1; }
grep -q '## Работает плохо' docs/knowledge/debt.md ||
  { echo "the trap was not planted: the ledger has no heading of its own"; exit 1; }
test ! -e docs/knowledge/product.md ||
  { echo "the trap was not planted: parts were written after all"; exit 1; }

# A heading of the ledger is an addressable record like any other, and that is
# exactly the trap: counted, it would make this project described. Asked of the
# kit rather than of the gate — what the gate does about an undescribed project
# is `a-project-that-was-never-described`, and a judge that read it here would
# redden for that case's break as well as its own.
SAID=$(python3 -c "
from agent_kit.knowledge import Knowledge
print('described' if Knowledge('docs/knowledge').described else 'not described')
") || { echo "the kit could not say whether this project is described"; exit 3; }
test "$SAID" = "not described" ||
  { echo "a project described by nothing but its bugs is called described"; exit 1; }

# And what makes it so is the ledger's own heading, which really is a record the
# kit can address: if it were not, this case would be measuring nothing.
COUNTED=$(python3 -c "
from agent_kit.knowledge import Knowledge
print(len(Knowledge('docs/knowledge').anchors()))
") || { echo "the ledger could not be read back"; exit 3; }
test "$COUNTED" -gt 0 ||
  { echo "the trap was not planted: the ledger holds no addressable record at all"; exit 1; }
exit 0
