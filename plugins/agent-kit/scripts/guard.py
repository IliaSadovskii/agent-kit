#!/usr/bin/env python3
"""Decision logic for guard.sh — the PreToolUse hook. See the header there.

`refusal()` is the decision on its own, importable, because the hook is not the only place a shell
command gets run on the kit's behalf: `blueprint_check.py` runs the commands a project's knowledge
contract declares, and `kit_gate.py` runs the `done_when` commands a pipeline definition declares. A
`PreToolUse` hook never sees either — it fires on tool calls, not on a subprocess a script starts.
One list of never-rules, three callers: the hook decides, and a caller with nobody to ask refuses.

The decision comes in two strengths. The never-rules **ask**, because interactively the user
confirms in one click and in an unattended run nobody answers, which is what the rules promise. A
write to the step gate's run state is **denied** outright: the agent must never write it — that is
the whole construction — and a headless sprint child has nobody to answer a question, so a hanging
child would be worse than a refused write.
"""
import json
import os
import re
import shlex
import subprocess
import sys

ASK = "ask"
DENY = "deny"

# Blunt on purpose, and without an exemption. A shell command that names the run-state directory is
# refused, full stop: reading state is what the Read tool is for, and a precise rule about
# redirects, `tee`, `sed -i` and `cp` targets would leak. The gate needs no exemption because the
# gate never names the directory — it derives the path from the branch — so an exemption would only
# ever have covered `gate.py state > .agent-kit/runs/<branch>.yml`, which is the very write this
# rule exists to refuse.
RUNS_DIR = os.path.join(".agent-kit", "runs")

RUN_STATE_REASON = (
    "agent-kit: `.agent-kit/runs/` is the step gate's run state, and only the gate writes it — a "
    "step the agent could close by hand is not a gate. Ask the gate instead: `step start`, "
    "`step settle`, `step skip`. To read state, use the Read tool. If this run was abandoned and "
    "its state is in the way, `gate.py run reset --reason \"<why>\"` discards it — every step then "
    "has to be proven again from nothing, which is the point.\n\n"
    "This rule is deliberately blunt, and it is a cost, not a cage: a shell has more spellings than "
    "any text rule can model. It is here so that closing a step by hand takes a decision rather "
    "than a slip.")


class Refusal:
    """Why the kit will not run a command, and how hard it says so."""

    __slots__ = ("decision", "reason")

    def __init__(self, decision, reason):
        self.decision = decision
        self.reason = reason


def decide(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
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


def names_run_state(text):
    """Whether a word names the gate's run-state directory, however it is spelled.

    Normalised first, because `.agent-kit//runs/x.yml` and `.agent-kit/./runs/x.yml` are the same
    file to the kernel and a different string to a substring test — which is how a blunt rule ends
    up not covering the blunt case.
    """
    if not isinstance(text, str) or not text:
        return False
    normalised = os.path.normpath(text.replace("\\", "/"))
    return any(marker in candidate
               for candidate in (text, normalised)
               for marker in (RUNS_DIR, RUNS_DIR.replace(os.sep, "/")))


def names_kit_corner(text):
    """Whether a word names `.agent-kit` itself — the directory the run state lives in."""
    if not isinstance(text, str) or not text:
        return False
    parts = os.path.normpath(text.replace("\\", "/")).split("/")
    return ".agent-kit" in parts


def refusal(command):
    """Why the kit will not run this shell command unattended, or None if it is ordinary.

    Judge each pipeline segment on its own words, so `git push` inside a quoted string or an
    unrelated command never triggers.
    """
    # Newlines and a bare `&` separate commands as surely as `&&` does, and a leading `(` or `{`
    # opens a group whose first word is still the command. Missing any of them puts the real
    # command at `words[1]`, where nothing below looks — `echo hi\ngit push --force` used to pass.
    for segment in re.split(r"\|\||&&|[;&\n]|\|", command):
        try:
            words = shlex.split(segment)
        except ValueError:
            words = segment.split()
        if words:
            words[0] = words[0].lstrip("({")
            if not words[0]:
                words.pop(0)

        # Before the environment-assignment strip below, not after: `D=.agent-kit/runs` is exactly
        # the word this rule exists to catch, and stripping it first threw it away unexamined.
        if any(names_run_state(word) for word in words):
            return Refusal(DENY, RUN_STATE_REASON)

        # `cd .agent-kit && cd runs && printf … > x.yml` names the directory in no single word.
        # Nothing a pipeline legitimately does starts by stepping into the kit's own corner, and
        # nothing legitimately deletes or moves it — which is the other way to silence the gate,
        # since no state file means no run.
        if words and words[0] in ("cd", "pushd") and any(names_kit_corner(w) for w in words[1:]):
            return Refusal(DENY, RUN_STATE_REASON)
        if words and words[0] in ("rm", "rmdir", "mv", "shred") \
                and any(names_kit_corner(w) for w in words[1:]):
            return Refusal(DENY, RUN_STATE_REASON)

        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words.pop(0)
        if not words:
            continue

        if words[:3] == ["gh", "pr", "merge"]:
            return Refusal(ASK, "agent-kit: the kit never merges pull requests — the owner merges. "
                                "Confirm to override.")

        if words[0] != "git" or "push" not in words:
            continue
        rest = words[words.index("push") + 1:]

        if any(w == "-f" or w.startswith("--force") for w in rest):
            return Refusal(ASK, "agent-kit: force push rewrites remote history. "
                                "Confirm to override.")

        default = (git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").rpartition("/")[2]
                   or "main")
        refspecs = [w for w in rest if not w.startswith("-")][1:]  # first positional is the remote
        if refspecs:
            for spec in refspecs:
                dest = spec.rpartition(":")[2]
                if dest == default or dest.endswith("/" + default):
                    return Refusal(ASK, f"agent-kit: this push targets the default branch "
                                        f"({default}); the kit works on feature branches. "
                                        "Confirm to override.")
        elif git("rev-parse", "--abbrev-ref", "HEAD") == default:
            return Refusal(ASK, f"agent-kit: pushing from the default branch ({default}); "
                                "the kit works on feature branches. Confirm to override.")
    return None


if __name__ == "__main__":
    try:
        incoming = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        sys.exit(0)
    refused = refusal(incoming)
    if refused:
        decide(refused.decision, refused.reason)
    sys.exit(0)
