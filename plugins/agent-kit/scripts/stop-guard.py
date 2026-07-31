#!/usr/bin/env python3
"""Decision logic for stop-guard.sh — the Stop hook. See the header there."""
import json
import os
import sys

import kit_gate


def held(event):
    """The steps this turn may not end on, or [] when there is nothing to hold.

    Every path out of here is silence unless a run is demonstrably open, owned by this session, and
    missing a terminal verdict. Anything unreadable is silence too: a wedged hook is worse than no
    hook, and an unreadable state file means there is no run to hold.
    """
    if event.get("stop_hook_active"):
        # The hook fires again on the turn it forced open. Nudge once: a guard that cannot be
        # satisfied is a loop, and the point is to hand attention back, not to hold the session.
        return []

    root = event.get("cwd") or os.getcwd()
    branch = kit_gate.branch_of(root)
    if not branch:
        return []

    state = kit_gate.load_state(root, branch)
    if state is None or state.get("state") != kit_gate.RUN_OPEN:
        return []
    if state.get("overridden_definitions"):
        # A step closed against definitions that were not the plugin's proves nothing about the
        # pipeline the skill is running. The override exists so the tests can declare a check that
        # fails on purpose; an environment variable is also something the agent can set, so a run
        # that used one is held rather than released.
        return ["<this run's steps were closed against "
                f"{state['overridden_definitions']}, not the plugin's own definitions>"]
    if not kit_gate.owned_by(state, event.get("session_id")):
        # A sprint orchestrator and its child share one working tree, and the child checks it out
        # onto its own branch. Holding the orchestrator here would demand, every turn, the exact
        # action the sprint contract forbids it to take.
        return []

    return kit_gate.unsettled(state, kit_gate.steps_of(state["pipeline"]))


try:
    incoming = json.load(sys.stdin)
except Exception:                                        # noqa: BLE001 - fail open, always
    sys.exit(0)

try:
    left = held(incoming)
except Exception:                                        # noqa: BLE001 - fail open, always
    sys.exit(0)

if not left:
    sys.exit(0)

print(json.dumps({
    "decision": "block",
    "reason": (
        "agent-kit: this run's pipeline is not finished. Steps with no verdict from the gate:\n"
        + ", ".join(left)
        + "\n\nPick up the first one and carry on — you are mid-pipeline, not done. Do not restate "
          "what you already reported, and do not write the verdict yourself: a step is closed by "
          "the gate.\n"
          "  step start  <Name>            opens it and prints what will close it\n"
          "  step settle <Name>            runs the checks and writes the verdict\n"
          "  step skip   <Name> --reason   only a condition the pipeline names\n"
          "A step that genuinely cannot pass settles as blocked once its attempts run out, and that "
          "ends this guard. Silence does not."
    ),
}))
sys.exit(0)
