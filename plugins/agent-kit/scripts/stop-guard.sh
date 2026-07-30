#!/usr/bin/env bash
# Stop hook: keep a pipeline from ending its turn with steps left.
#
# The kit's step order is prose, and prose loses to whatever instruction is freshest in a long
# context — a review prompt read inline can reassign the role, and the run ends with a report
# instead of a pull request. Nothing inside the model can guarantee otherwise, so the check lives
# out here: the plan's Run log names the branch and the ordered steps, and a turn that tries to end
# with one unsettled is handed back with the list.
#
# It reads only the plan on the current branch, and only when that plan carries the two header
# lines, so an ordinary conversation, a docs branch, and any repository that never ran a pipeline
# are all untouched. `done`, `skipped: why`, and `blocked: why` all settle a step — the guard asks
# for a decision on the record, not for the step to succeed.
set -u
exec python3 "$(dirname "$0")/stop-guard.py"
