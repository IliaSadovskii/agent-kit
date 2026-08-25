#!/bin/sh
# The trap first: rates put a file on its own branch, which is what quote
# was supposed to be standing on.
git show kit/rates --name-only --format= | grep -q '^rates.py$' ||
  { echo "rates never wrote the file this case is about"; exit 1; }

grep -q '"base": "kit/rates"' "$REPO/.agent-kit/v3/runs/quote/run.json" ||
  { echo "quote does not say it is built on kit/rates"; exit 1; }

# And the pull request opens against that branch rather than the trunk.
grep -A 1 -- '^--base$' "$BENCH/gh-argv" | grep -q '^kit/rates$' ||
  { echo "no pull request opened against kit/rates"; exit 1; }
exit 0
