#!/usr/bin/env bash
# Stop hook: keep a pipeline from ending its turn with steps left.
#
# The kit's step order is prose, and prose loses to whatever instruction is freshest in a long
# context — a review prompt read inline can reassign the role, and the run ends with a report
# instead of a pull request. Nothing inside the model can guarantee otherwise, so the check lives
# out here.
#
# It reads run state, not markdown: `.agent-kit/runs/<branch>.yml`, which only the gate writes.
# Every terminal verdict the gate can write settles a step — verified, attested, skipped, blocked —
# so the guard asks for a decision on the record, not for the step to succeed. No state file means
# no run, which leaves an ordinary conversation and any repository that never ran a pipeline
# untouched, and a run belongs to the session that opened it, which keeps a sprint orchestrator out
# of its own child's pipeline.
set -u
exec python3 "$(dirname "$0")/stop-guard.py"
