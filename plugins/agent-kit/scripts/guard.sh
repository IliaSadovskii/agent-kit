#!/usr/bin/env bash
# PreToolUse hook: turn the governance's "never" rules into a confirmation instead of a promise.
#
# Matches only what the always-on rules forbid outright — merging a pull request, pushing the
# default branch, force-pushing. The decision is "ask", never "deny": interactively the user
# confirms in one click; in an unattended autonomous run nobody answers, so the command does not
# run — which is exactly what the rules promise. Everything else passes through untouched.
#
# The command parsing lives in guard.py — shell-level pattern matching cannot tell `git push`
# from `echo "git push"`, and a guard that cries wolf teaches everyone to click through it.
set -u
exec python3 "$(dirname "$0")/guard.py"
