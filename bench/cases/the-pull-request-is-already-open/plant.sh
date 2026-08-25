#!/bin/sh
set -e
# The whole of the previous attempt: the commit on the branch, pushed, and
# the pull request opened. What it never got to do is record the url.
git checkout -q -b "$BRANCH"
printf 'RATE = 20\n' >> money.py
git add -- money.py
git commit -q -m "Money learns a VAT rate"
git push -q -u origin "$BRANCH"
# What `gh pr view` reads to know a pull request is already there.
touch "$BENCH/gh-opened-$(printf '%s' "$BRANCH" | tr / -)"
