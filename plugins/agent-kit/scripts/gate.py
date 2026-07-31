#!/usr/bin/env python3
"""The step gate's command line — how a pipeline asks for a step to be opened and closed.

    gate.py step start  <Name> [--pipeline ship]   checks order, opens the step, prints what closes it
    gate.py step settle <Name> [--evidence "…"]    runs done_when and WRITES the verdict
    gate.py step skip   <Name> --reason <named>    only a condition the definition names
    gate.py state                                  the branch's run, or nothing at all
    gate.py run reset   --reason "<why>"           discard this branch's run entirely

The agent asks; the gate answers. It cannot write the answer itself — two `PreToolUse` hooks refuse
every path into `.agent-kit/runs/**` that is not this script.

Exit codes:

    0   the step moved
    1   the gate says no — a check failed, or this run's own state refuses the request
    2   the gate cannot answer — the invocation is malformed, or the declaration or the state
        cannot be read
"""
import os
import sys

import kit_gate

USAGE = __doc__.strip()

# Evidence is free text the agent wrote. The summary quotes it so a resumed session knows what was
# claimed, and keeps it short so it cannot become a document.
EVIDENCE_IN_SUMMARY = 120


def fail(message, code=2):
    print(f"gate: {message}", file=sys.stderr)
    return code


def _root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _branch(root):
    branch = kit_gate.branch_of(root)
    if not branch:
        raise kit_gate.GateError("no branch is checked out — the gate keys a run by its branch, and "
                                 "a detached HEAD has none")
    return branch


def _find(steps, name):
    for index, step in enumerate(steps):
        if step.name == name:
            return index, step
    raise kit_gate.GateError(f"no step named {name!r} in this pipeline "
                             f"(declared: {', '.join(s.name for s in steps)})")


def _settle(state, name, verdict, **fields):
    entry = kit_gate.step_state(state, name)
    entry["verdict"] = verdict
    entry["settled_at"] = kit_gate.now()
    entry.update(fields)


def _close_run_if_done(state, steps):
    if not kit_gate.unsettled(state, steps):
        state["state"] = kit_gate.RUN_FINISHED


# ----------------------------------------------------------------------------------------------


def cmd_start(root, name, pipeline):
    branch = _branch(root)
    state = kit_gate.load_state(root, branch)

    if state is None:
        if not pipeline:
            declared = ", ".join(sorted(kit_gate.load_pipelines()))
            return fail(f"there is no run on {branch} yet, so the first `step start` has to say "
                        f"which pipeline it opens: --pipeline <{declared}>")
        kit_gate.steps_of(pipeline)                      # validates before anything is written
        state = kit_gate.new_state(root, branch, pipeline)
    elif pipeline and pipeline != state["pipeline"]:
        return fail(f"this run is the {state['pipeline']!r} pipeline; `--pipeline {pipeline}` "
                    "would be a different one. One run, one pipeline.")

    steps = kit_gate.steps_of(state["pipeline"])
    index, step = _find(steps, name)

    if state["state"] != kit_gate.RUN_OPEN:
        return fail(f"this run is {state['state']} — no further step opens on it", code=1)

    verdict = kit_gate.verdict_of(state, name)
    if verdict in kit_gate.TERMINAL:
        return fail(f"{name} is already settled as {verdict}; a terminal verdict is not reopened",
                    code=1)

    # Order is the failure this whole feature exists for: a step read inline reassigns the role and
    # the turn ends with a report where a pull request was due. `requires:` needs no separate test —
    # the parser has already established that it names an earlier step, and every earlier step is
    # covered here.
    blocking = [s.name for s in steps[:index] if not kit_gate.is_terminal(state, s.name)]
    if blocking:
        return fail(f"{name} does not open yet: {', '.join(blocking)} "
                    f"{'has' if len(blocking) == 1 else 'have'} no terminal verdict. Settle or skip "
                    "in order.", code=1)

    if verdict is None:
        state["steps"].append({"name": name, "verdict": kit_gate.OPEN, "attempts": 0,
                               "opened_at": kit_gate.now()})
    kit_gate.write_state(root, state)

    print(f"step {name} — open ({state['pipeline']}, attempt limit {step.max_attempts})")
    print("closes when:")
    for line in step.describe():
        print("  " + line)
    if step.skippable_when:
        print(f"skippable when: {', '.join(step.skippable_when)}")
    elif step.optional:
        print("optional: may be skipped with a named reason")
    return 0


def cmd_settle(root, name, evidence):
    branch = _branch(root)
    state = kit_gate.load_state(root, branch)
    if state is None:
        return fail(f"there is no run on {branch} — open the step first with `step start {name}`",
                    code=1)
    steps = kit_gate.steps_of(state["pipeline"])
    step = _find(steps, name)[1]

    entry = kit_gate.step_state(state, name)
    if entry is None:
        return fail(f"{name} was never opened — `step start {name}` first", code=1)
    if entry.get("verdict") in kit_gate.TERMINAL:
        return fail(f"{name} is already settled as {entry['verdict']}", code=1)

    if not step.checks:
        # The gate is honest about what it guarantees. A step nothing mechanical can prove is
        # `attested`, and it costs the agent a sentence saying what it actually did.
        if not (evidence or "").strip():
            return fail(f"{name} declares no mechanical check, so it settles as attested and needs "
                        "`--evidence \"<what you did>\"`. An empty attestation is not evidence.",
                        code=1)
        _settle(state, name, kit_gate.ATTESTED, evidence=evidence.strip())
        entry["attempts"] = entry.get("attempts", 0) + 1
        _close_run_if_done(state, steps)
        kit_gate.write_state(root, state)
        print(f"step {name} — attested: {evidence.strip()}")
        return 0

    found = [kit_gate.run_check(root, kind, value, state) for kind, value in step.checks]
    failed = [e for e in found if not e.passed]
    entry["attempts"] = entry.get("attempts", 0) + 1

    if not failed:
        _settle(state, name, kit_gate.VERIFIED, evidence=[e.record() for e in found])
        _close_run_if_done(state, steps)
        kit_gate.write_state(root, state)
        print(f"step {name} — verified")
        for item in found:
            print(f"  {item.check} → {item.exit_code}")
        return 0

    history = entry.setdefault("history", [])
    for item in failed:
        record = item.record()
        record["attempt"] = entry["attempts"]
        history.append(record)

    exhausted = entry["attempts"] >= step.max_attempts
    if exhausted:
        _settle(state, name, kit_gate.BLOCKED)
        if step.on_exhausted == "block":
            state["state"] = kit_gate.RUN_BLOCKED
        else:
            _close_run_if_done(state, steps)
    kit_gate.write_state(root, state)

    print(f"step {name} — attempt {entry['attempts']} of {step.max_attempts} failed",
          file=sys.stderr)
    for item in failed:
        print(f"  {item.check} → exit {item.exit_code}", file=sys.stderr)
        for line in (item.output or "(no output)").splitlines()[-20:]:
            print(f"    {line}", file=sys.stderr)
    if exhausted:
        print(f"step {name} — blocked: attempts exhausted.", file=sys.stderr)
        print("the run is blocked — stop, and report this step as the blocker"
              if step.on_exhausted == "block"
              else "on_exhausted is `continue` — carry on and say so in the pull request",
              file=sys.stderr)
    else:
        print("fix what failed and settle again.", file=sys.stderr)
    return 1


def cmd_skip(root, name, reason):
    branch = _branch(root)
    state = kit_gate.load_state(root, branch)
    if state is None:
        return fail(f"there is no run on {branch} — there is nothing to skip", code=1)
    steps = kit_gate.steps_of(state["pipeline"])
    index, step = _find(steps, name)

    if kit_gate.verdict_of(state, name) in kit_gate.TERMINAL:
        return fail(f"{name} is already settled as {kit_gate.verdict_of(state, name)}", code=1)
    if not (reason or "").strip():
        return fail("`step skip` needs `--reason <named condition>`", code=1)
    reason = reason.strip()

    # Free text used to close any step, so the constraint did not exist. A skip now names a
    # condition the definition itself declares.
    if step.skippable_when:
        if reason not in step.skippable_when:
            return fail(f"{name} is skippable when {', '.join(step.skippable_when)} — "
                        f"{reason!r} is not one of them", code=1)
    elif not step.optional:
        return fail(f"{name} is neither optional nor skippable under any named condition. Settle "
                    "it, or let it block.", code=1)

    blocking = [s.name for s in steps[:index] if not kit_gate.is_terminal(state, s.name)]
    if blocking:
        return fail(f"{name} does not settle yet: {', '.join(blocking)} came first and "
                    f"{'has' if len(blocking) == 1 else 'have'} no terminal verdict.", code=1)

    if kit_gate.step_state(state, name) is None:
        state["steps"].append({"name": name, "verdict": kit_gate.OPEN, "attempts": 0,
                               "opened_at": kit_gate.now()})
    _settle(state, name, kit_gate.SKIPPED, reason=reason)
    _close_run_if_done(state, steps)
    kit_gate.write_state(root, state)
    print(f"step {name} — skipped: {reason}")
    return 0


def cmd_reset(root, reason):
    """Discard this branch's run. Not a way to close a step — a way to stop having one.

    A run that was abandoned, or whose branch was reset under it, otherwise nudges every turn for
    ever and refuses to reopen its terminal verdicts. Deleting the file by hand is refused, and
    rightly: `sprint`'s own retry path relaunches a feature on a branch that still carries the
    previous attempt's state, and it has no human to ask.

    This grants nothing the design did not already allow. No state file means no run, exactly as in
    a repository that never ran a pipeline; what it cannot do is mark anything done. Every step of
    a reset run has to be proven again from nothing.
    """
    if not (reason or "").strip():
        return fail("`run reset` needs `--reason \"<why>\"` — discarding a run is a decision, and "
                    "it is the only record of it", code=1)
    branch = _branch(root)
    state = kit_gate.load_state(root, branch)
    if state is None:
        return fail(f"there is no run on {branch} to discard", code=1)
    settled = [f"{s['name']}={s.get('verdict')}" for s in state["steps"]
               if s.get("verdict") in kit_gate.TERMINAL]
    kit_gate.discard_state(root, branch)
    print(f"run on {branch} discarded: {reason.strip()}")
    print("verdicts thrown away: " + (", ".join(settled) or "none"))
    print("every step has to be proven again from nothing — say so in the Run log.")
    return 0


def summary(root):
    """The run's own account of where it stands, or "" when there is no run on this branch."""
    branch = kit_gate.branch_of(root)
    if not branch:
        return ""
    state = kit_gate.load_state(root, branch)
    if state is None or state.get("state") != kit_gate.RUN_OPEN:
        return ""
    try:
        steps = kit_gate.steps_of(state["pipeline"])
    except kit_gate.GateError:
        return ""

    lines = [f"## agent-kit — unfinished run on {branch}", "",
             f"Pipeline `{state['pipeline']}`, opened {state.get('opened_at')}. Steps are closed by "
             "the gate, not by you: `step settle <Name>`.", ""]
    open_step = None
    for step in steps:
        entry = kit_gate.step_state(state, step.name) or {}
        verdict = entry.get("verdict") or kit_gate.OPEN
        detail = entry.get("reason") or (entry.get("evidence")
                                         if isinstance(entry.get("evidence"), str) else "")
        lines.append(f"- {step.name} — {verdict}" + (f": {_quote(detail)}" if detail else ""))
        if open_step is None and verdict not in kit_gate.TERMINAL:
            open_step = (step, entry)

    if open_step:
        step, entry = open_step
        lines += ["", f"**Next: {step.name}** — attempt {entry.get('attempts', 0) + 1} of "
                      f"{step.max_attempts}."]
        for record in (entry.get("history") or [])[-3:]:
            lines.append(f"- attempt {record.get('attempt')}: {record.get('check')} → exit "
                         f"{record.get('exit')}")
    text = "\n".join(lines) + "\n"
    if len(text) > kit_gate.STATE_CAP:
        text = text[:kit_gate.STATE_CAP - 40].rstrip() + "\n… (state truncated)\n"
    return text


def _quote(text):
    """One line of somebody's free text, marked as a record rather than as a sentence to obey.

    This lands in the next session's context through the SessionStart hook, on every start, resume,
    clear and compact of the branch — which makes it the most durable writing surface in the run,
    in the most trusted voice in the window. A multi-line evidence string could otherwise open with
    a blank line and a heading of its own and read as the kit's own governance.
    """
    flat = " ".join(str(text).split())
    if len(flat) > EVIDENCE_IN_SUMMARY:
        flat = flat[:EVIDENCE_IN_SUMMARY - 1].rstrip() + "…"
    return f"[recorded by the agent: {flat}]"


def cmd_state(root):
    sys.stdout.write(summary(root))
    return 0


# ----------------------------------------------------------------------------------------------


def parse(argv):
    """(command, name, options) or a message. A tiny parser: argparse's errors are not the gate's."""
    options = {}
    positional = []
    it = iter(argv)
    for token in it:
        if token in ("--pipeline", "--evidence", "--reason"):
            value = next(it, None)
            if value is None:
                return None, f"{token} needs a value"
            options[token[2:]] = value
        elif token.startswith("--"):
            return None, f"unknown option {token}"
        else:
            positional.append(token)
    return (positional, options), None


def main(argv):
    parsed, problem = parse(argv)
    if problem:
        return fail(problem)
    positional, options = parsed

    if not positional:
        print(USAGE)
        return 2

    try:
        root = _root()
        if positional[0] == "state":
            return cmd_state(root)
        if positional[:2] == ["run", "reset"]:
            return cmd_reset(root, options.get("reason"))
        if positional[0] != "step" or len(positional) < 3:
            print(USAGE, file=sys.stderr)
            return 2
        action, name = positional[1], positional[2]
        if action == "start":
            return cmd_start(root, name, options.get("pipeline"))
        if action == "settle":
            return cmd_settle(root, name, options.get("evidence"))
        if action == "skip":
            return cmd_skip(root, name, options.get("reason"))
        print(USAGE, file=sys.stderr)
        return 2
    except kit_gate.GateError as exc:
        return fail(str(exc), code=2 if exc.structural else 1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
