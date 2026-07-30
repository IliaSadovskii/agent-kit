#!/usr/bin/env python3
"""Decision logic for guard.sh — the PreToolUse hook. See the header there.

`refusal()` is the decision on its own, importable, because the hook is not the only place a shell
command gets run on the kit's behalf: `blueprint_check.py` runs the commands a project's knowledge
contract declares, and a `PreToolUse` hook never sees those — it fires on tool calls, not on a
subprocess a script starts. One list of never-rules, two callers: the hook asks, and a caller with
nobody to ask refuses.
"""
import json
import re
import shlex
import subprocess
import sys


def ask(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def git(*args):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def refusal(command):
    """Why the kit will not run this shell command unattended, or None if it is ordinary.

    Judge each pipeline segment on its own words, so `git push` inside a quoted string or an
    unrelated command never triggers.
    """
    for segment in re.split(r"\|\||&&|;|\|", command):
        try:
            words = shlex.split(segment)
        except ValueError:
            words = segment.split()
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words.pop(0)
        if not words:
            continue

        if words[:3] == ["gh", "pr", "merge"]:
            return ("agent-kit: the kit never merges pull requests — the owner merges. "
                    "Confirm to override.")

        if words[0] != "git" or "push" not in words:
            continue
        rest = words[words.index("push") + 1:]

        if any(w == "-f" or w.startswith("--force") for w in rest):
            return "agent-kit: force push rewrites remote history. Confirm to override."

        default = (git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").rpartition("/")[2]
                   or "main")
        refspecs = [w for w in rest if not w.startswith("-")][1:]  # first positional is the remote
        if refspecs:
            for spec in refspecs:
                dest = spec.rpartition(":")[2]
                if dest == default or dest.endswith("/" + default):
                    return (f"agent-kit: this push targets the default branch ({default}); "
                            "the kit works on feature branches. Confirm to override.")
        elif git("rev-parse", "--abbrev-ref", "HEAD") == default:
            return (f"agent-kit: pushing from the default branch ({default}); "
                    "the kit works on feature branches. Confirm to override.")
    return None


if __name__ == "__main__":
    try:
        incoming = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        sys.exit(0)
    reason = refusal(incoming)
    if reason:
        ask(reason)
    sys.exit(0)
