#!/usr/bin/env python3
"""Decision logic for stop-guard.sh — the Stop hook. See the header there."""
import glob
import json
import os
import re
import subprocess
import sys

SETTLED = re.compile(r"^- step (.+?) —", re.M)
STEPS = re.compile(r"^\*\*Steps:\*\*(.+)$", re.M)
BRANCH = re.compile(r"^\*\*Branch:\*\*\s*(\S+)", re.M)


def branch_of(cwd):
    try:
        # symbolic-ref, not rev-parse: it answers before the first commit too, and a detached
        # HEAD failing here is the right answer — no branch means no run to hold open.
        out = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5, cwd=cwd)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# The hook fires again on the turn it forced open. Nudge once: a guard that cannot be satisfied
# is a loop, and the point is to hand attention back, not to hold the session hostage.
if event.get("stop_hook_active"):
    sys.exit(0)

cwd = event.get("cwd") or os.getcwd()
branch = branch_of(cwd)
if not branch:
    sys.exit(0)

pending = []
for path in sorted(glob.glob(os.path.join(cwd, "docs", "plans", "*.md"))):
    try:
        with open(path, encoding="utf-8") as fh:
            head, sep, log = fh.read().partition("## Run log")
    except OSError:
        continue
    if not sep:
        continue

    # Only the plan of the run happening on this branch: every other plan in the repository is
    # finished history, and a plan without the two header lines predates this contract.
    on_branch = BRANCH.search(log)
    declared = STEPS.search(log)
    if not on_branch or not declared or on_branch.group(1) != branch:
        continue

    steps = [s.strip() for s in declared.group(1).split(",") if s.strip()]
    settled = {m.strip() for m in SETTLED.findall(log)}
    left = [s for s in steps if s not in settled]
    if left:
        pending.append((os.path.relpath(path, cwd), left))

if not pending:
    sys.exit(0)

lines = [f"{plan}: {', '.join(left)}" for plan, left in pending]
print(json.dumps({
    "decision": "block",
    "reason": (
        "agent-kit: this run's pipeline is not finished. Steps with no line in the plan's Run log:\n"
        + "\n".join(lines)
        + "\n\nPick up the first unsettled step and carry on — you are mid-pipeline, not done. "
          "Do not restate what you already reported. If a step genuinely cannot run, settle it in "
          "the Run log as `- step <Name> — skipped: <reason>` or `- step <Name> — blocked: <reason>` "
          "and say so in the PR; a named skip ends this guard, silence does not."
    ),
}))
sys.exit(0)
