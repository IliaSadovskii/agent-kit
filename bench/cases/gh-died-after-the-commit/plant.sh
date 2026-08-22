#!/bin/sh
set -e
# What an earlier delivery left behind before gh refused it: the commit
# this run would write, on the branch, pushed, and no pull request.
git checkout -q -b "$BRANCH"
printf 'RATE = 20\n' >> money.py
git add -- money.py
git commit -q -m "Money learns a VAT rate"
git push -q -u origin "$BRANCH"
# The working copy is left where the failed delivery left it: on the branch,
# clean, with the work committed and nothing to say for it.
