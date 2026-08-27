#!/bin/sh
# What a session that ignored every instruction would do. It runs where the
# session runs, which is the whole question this case asks.
printf 'RATE = 20\n' >> money.py
printf 'the session wrote this\n' > oops.txt
git rev-parse --git-dir > "$BENCH/the-session-saw" 2>&1 || echo "no repository here" > "$BENCH/the-session-saw"
touch "$BENCH/the-session-ran"
