#!/bin/sh
set -e
git checkout -q -b "$BRANCH"
echo "somebody else was here" > other.py
git add -A
git commit -q -m "other.py by somebody else"
git rev-parse HEAD > "$BENCH/tip"
git checkout -q main
