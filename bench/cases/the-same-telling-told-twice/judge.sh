#!/bin/sh
PRODUCT=docs/knowledge/product.md
# The key here is chosen by the first sitting rather than derived from a name,
# so nothing in this case goes stale the day `part_key` changes. What derives a
# key is measured by `a-description-from-nothing`, whose judge asks the kit.
KEY=sign-in

# The trap first, out of the commit: the first sitting really did happen and
# really did write the part this one refines. The baseline is a described
# project now, so `git show` succeeding proves nothing on its own — what proves
# it is that the part this case refines is in that commit and its second
# wording is not.
BEFORE=$(git show main:$PRODUCT 2>/dev/null) || { echo "the trap was not planted: no description at all"; exit 1; }
case "$BEFORE" in *"key: $KEY"*) : ;; *) echo "the trap was not planted: no first sitting wrote the part"; exit 1;; esac
case "$BEFORE" in *"только Google"*) : ;; *) echo "the trap was not planted: the first wording is missing"; exit 1;; esac
case "$BEFORE" in *"Google, Apple и почта"*) echo "the second wording was there before the run"; exit 1;; esac

# One line per key, not two. This is the whole case.
test "$(grep -c "key: $KEY" $PRODUCT)" -eq 1 ||
  { echo "the part was laid beside itself: $(grep -c "key: $KEY" $PRODUCT) lines carry its key"; exit 1; }
grep -q 'Google, Apple и почта' $PRODUCT || { echo "the second telling did not reach the line"; exit 1; }
grep -q 'только Google' $PRODUCT && { echo "the first wording is still standing"; exit 1; }

# The ledger says the same thing about itself.
test "$(grep -c 'импорт словаря' docs/knowledge/debt.md)" -eq 1 ||
  { echo "the ledger line was written twice"; exit 1; }

# And the sitting the owner was not part of left its own room rather than
# writing over the first one's.
test "$(ls .agent-kit/v3/sittings | wc -l)" -eq 2 ||
  { echo "the second sitting did not get a room of its own"; exit 1; }
exit 0
