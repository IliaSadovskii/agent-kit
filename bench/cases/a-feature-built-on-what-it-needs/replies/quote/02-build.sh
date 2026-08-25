#!/bin/sh
# Built on rates, so what rates wrote is in this tree, merged by nobody.
test -f rates.py || { echo "this tree was cut from the trunk, not from kit/rates" >&2; exit 1; }
printf 'QUOTE = 1\n' >> quote.py
