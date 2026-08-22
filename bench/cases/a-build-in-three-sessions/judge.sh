#!/bin/sh
held=$(git show --name-only --format= HEAD | sort | tr "\n" " ")
echo "$held" | grep -q money.py || { echo "the first session's work is missing: $held"; exit 1; }
echo "$held" | grep -q gross.py || { echo "the second session's work is missing: $held"; exit 1; }
echo "$held" | grep -q rounding.py || { echo "the last session's work is missing: $held"; exit 1; }
