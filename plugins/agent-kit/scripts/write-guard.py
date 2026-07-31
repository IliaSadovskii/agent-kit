#!/usr/bin/env python3
"""Decision logic for write-guard.sh — the PreToolUse hook on Write and Edit. See the header there.

The step gate's whole construction is that run state is outside the agent's reach: the only path
into `.agent-kit/runs/**` is passing a step's checks. The Bash guard covers a shell command; without
this, one `Write` walks around it and the guarantee is paper.

The rule is the Bash guard's, shared rather than restated: a path naming the run-state directory is
refused, and the decision is `deny` — a headless run has nobody to answer an `ask`, and a hanging
child is worse than a refused write.
"""
import json
import os
import sys

import guard

# Every tool that puts bytes on disk names its target the same way; a matcher that grows a tool the
# hook does not know about should still be read rather than ignored.
PATH_FIELDS = ("file_path", "filePath", "path", "notebook_path")


def target(tool_input):
    for field in PATH_FIELDS:
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def refuses(path, cwd):
    """Whether this write lands in the gate's run state, however the path is spelled.

    Resolved against the session's directory and through `realpath`, so `.agent-kit//runs/x.yml`,
    `./.agent-kit/runs/x.yml`, a path relative to somewhere else, and a symlinked parent all come
    down to the same answer. The raw text is judged too, because a path that names the directory
    but does not exist yet has nothing for `realpath` to resolve.
    """
    if not path:
        return False
    if guard.names_run_state(path):
        return True
    try:
        resolved = os.path.realpath(os.path.join(cwd or os.getcwd(), path))
    except (OSError, ValueError):
        return False
    return guard.names_run_state(resolved)


if __name__ == "__main__":
    try:
        event = json.load(sys.stdin)
        path = target(event.get("tool_input") or {})
        where = event.get("cwd") or os.getcwd()
    except Exception:                                    # noqa: BLE001 - a wedged hook is worse
        sys.exit(0)
    if refuses(path, where):
        guard.decide(guard.DENY, (
            f"agent-kit: {path} is the step gate's run state, and only the gate writes it — a step "
            "the agent could close by hand is not a gate. Ask the gate instead: `step start`, "
            "`step settle`, `step skip`. Reading the file is fine; writing it is not."))
    sys.exit(0)
