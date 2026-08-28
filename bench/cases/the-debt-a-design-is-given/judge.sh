#!/bin/sh
# The trap first, out of the commit the world was made from: this project's
# ledger really did stand before the run. Reading the working copy would let a
# case whose plant never landed judge itself green.
git show main:docs/knowledge/debt.md > /dev/null 2>&1 ||
  { echo "no ledger was planted at all"; exit 1; }
git show main:docs/knowledge/debt.md | grep -q 'отчёт по периодам' ||
  { echo "the planted ledger holds no line"; exit 1; }

# Read out of the input the driver composed, not out of an answer that would be
# grepping itself: what is measured is that the lines reached the session.
INPUT=.agent-kit/v3/runs/add-vat/steps/0-design/attempt-1/input.md
test -f "$INPUT" || { echo "the run never had a design composed at all"; exit 1; }
grep -q 'отчёт по периодам считается вручную' "$INPUT" ||
  { echo "the design was written without the debt this project already owes itself"; exit 1; }
grep -q '6kwgcv' "$INPUT" || { echo "the line reached the design with no key to name it by"; exit 1; }
exit 0
