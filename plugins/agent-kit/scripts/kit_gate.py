"""The step gate's model: pipeline definitions, run state, checks, and step transitions.

A step is closed by the gate, never by the agent. This module is the whole of what "closed" means:
it reads the ordered steps a pipeline declares, runs their `done_when` checks, and writes the verdict
into `.agent-kit/runs/<slug>.yml` — a file two `PreToolUse` hooks keep out of the agent's reach.

Three callers share it. `gate.py` is the command line the agent asks with, `stop-guard.py` holds a
turn that would end with a step still open, and the tests drive both. Nothing here asks a question or
calls a model: a gate that can deadlock a run has replaced one failure mode with a worse one, so
every path either answers or raises with a name.

Exit codes are the batch's: `1` means a check failed, `2` means the declaration or the state could
not be read. `GateError.structural` is which of the two a raise means.
"""
import datetime
import glob as globlib
import os
import re
import subprocess

import guard
import kit_knowledge
import kit_yaml

RUNS_DIR = os.path.join(".agent-kit", "runs")
DEFAULT_PIPELINES = "pipelines.default.yml"

# The verdicts a step can hold. `open` is the absence of one; the other four are terminal, and a
# terminal verdict is what lets the next step open and the Stop hook let go.
OPEN = "open"
VERIFIED = "verified"
ATTESTED = "attested"
SKIPPED = "skipped"
BLOCKED = "blocked"
TERMINAL = (VERIFIED, ATTESTED, SKIPPED, BLOCKED)

# The run itself. `blocked` releases the Stop hook exactly as `finished` does: the agent's job then
# is to report the blocker, and holding the turn would demand work the run has already established
# cannot be done.
RUN_OPEN = "open"
RUN_FINISHED = "finished"
RUN_BLOCKED = "blocked"

SUPPORTED_CHECKS = ("run", "exists", "git")
DECLARED_UNSUPPORTED = {
    "approved_by_owner": "the owner's approval is not something this version of the gate can "
                         "observe; the step is attested with evidence instead",
    "agent": "a grader-backed check needs a subagent, which the gate does not spawn in this version",
}
GIT_CHECKS = ("tree_clean", "commits_on_branch", "pushed")
ON_EXHAUSTED = ("block", "continue")
DECLARED_UNSUPPORTED_EXHAUSTED = {
    "escalate": "waking the owner needs a push channel this version of the gate does not have",
}

# A `run:` check with no bound would hang the gate, and an overnight run has nobody to notice.
# `limits.wall_clock` arrives with the project-owned pipeline file; this is the floor under it.
CHECK_TIMEOUT = 1800
# Enough of a failing command to act on, little enough that state stays readable.
OUTPUT_TAIL = 1000
# SessionStart output is capped by Claude Code at 10,000 characters for the whole hook, and
# `engine.md` is most of that budget. Past the cap the governance is written to a file and replaced
# with a preview, so it would silently stop being always-on.
STATE_CAP = 2000

_UNSAFE_IN_SLUG = re.compile(r"[^A-Za-z0-9._-]+")


class GateError(Exception):
    """Something the gate will not guess at, named rather than defaulted.

    `structural` separates "this check failed" from "this declaration cannot be read" — exit 1 and
    exit 2, the same split the rest of the batch uses.
    """

    def __init__(self, message, structural=True):
        super().__init__(message)
        self.structural = structural


# ----------------------------------------------------------------------------------------------
# Pipeline definitions


class Step:
    """One step of a pipeline, as the definition file declares it."""

    __slots__ = ("name", "requires", "checks", "max_attempts", "on_exhausted", "optional",
                 "skippable_when")

    def __init__(self, name, requires, checks, max_attempts, on_exhausted, optional,
                 skippable_when):
        self.name = name
        self.requires = requires
        self.checks = checks
        self.max_attempts = max_attempts
        self.on_exhausted = on_exhausted
        self.optional = optional
        self.skippable_when = skippable_when

    def describe(self):
        """The closing criteria, as the list `step start` prints."""
        if not self.checks:
            return ["no mechanical check — settle with `--evidence \"<what you did>\"`, "
                    "which the gate records as `attested` rather than `verified`"]
        return [f"{position}. {kind}: {value}"
                for position, (kind, value) in enumerate(self.checks, 1)]


def _require_map(value, where):
    if not isinstance(value, dict):
        raise GateError(f"{where}: expected a mapping, found {type(value).__name__}")
    return value


def _check_pair(raw, where):
    """One `done_when` entry as (kind, value), with the unsupported kinds named rather than passed."""
    entry = _require_map(raw, where)
    if len(entry) != 1:
        raise GateError(f"{where}: a check is one `kind: value` pair, found {sorted(entry)}")
    kind, value = next(iter(entry.items()))
    if kind in DECLARED_UNSUPPORTED:
        raise GateError(f"{where}: check kind `{kind}:` is declared in the schema and not supported "
                        f"by this version of the gate — {DECLARED_UNSUPPORTED[kind]}")
    if kind not in SUPPORTED_CHECKS:
        raise GateError(f"{where}: unknown check kind `{kind}:` "
                        f"(supported: {', '.join(SUPPORTED_CHECKS)})")
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{where}: `{kind}:` needs a non-empty value")
    if kind == "git" and value not in GIT_CHECKS:
        raise GateError(f"{where}: `git: {value}` is not one of {', '.join(GIT_CHECKS)}")
    return kind, value.strip()


def _parse_step(raw, where, known):
    entry = _require_map(raw, where)
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise GateError(f"{where}: a step needs a `name`")
    name = name.strip()
    if name in known:
        raise GateError(f"{where}: two steps are called {name!r}")

    requires = entry.get("requires") or []
    if not isinstance(requires, list) or any(not isinstance(r, str) for r in requires):
        raise GateError(f"{where}: `requires` is a list of step names")
    for needed in requires:
        if needed not in known:
            raise GateError(f"{where}: `requires: {needed}` names a step that does not come before "
                            "this one")

    raw_checks = entry.get("done_when") or []
    if not isinstance(raw_checks, list):
        raise GateError(f"{where}: `done_when` is a list of checks")
    checks = [_check_pair(c, f"{where}/done_when[{i}]") for i, c in enumerate(raw_checks)]

    attempts = entry.get("max_attempts", 1)
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise GateError(f"{where}: `max_attempts` is a positive integer")

    exhausted = entry.get("on_exhausted", "block")
    if exhausted in DECLARED_UNSUPPORTED_EXHAUSTED:
        raise GateError(f"{where}: `on_exhausted: {exhausted}` is declared in the schema and not "
                        f"supported by this version of the gate — "
                        f"{DECLARED_UNSUPPORTED_EXHAUSTED[exhausted]}")
    if exhausted not in ON_EXHAUSTED:
        raise GateError(f"{where}: `on_exhausted` is one of {', '.join(ON_EXHAUSTED)}")

    optional = entry.get("optional", False)
    if not isinstance(optional, bool):
        raise GateError(f"{where}: `optional` is true or false")

    skippable = entry.get("skippable_when") or []
    if not isinstance(skippable, list) or any(not isinstance(s, str) or not s.strip()
                                              for s in skippable):
        raise GateError(f"{where}: `skippable_when` is a list of named conditions")

    return Step(name, requires, checks, attempts, exhausted, optional,
                [s.strip() for s in skippable])


def parse_pipelines(document, where):
    """Every pipeline in a definition document, validated. Raises GateError."""
    top = _require_map(document, where)
    pipelines = _require_map(top.get("pipelines") or {}, f"{where}/pipelines")
    if not pipelines:
        raise GateError(f"{where}: no pipelines are declared")
    parsed = {}
    for name, body in pipelines.items():
        steps_raw = _require_map(body, f"{where}/pipelines/{name}").get("steps")
        if not isinstance(steps_raw, list) or not steps_raw:
            raise GateError(f"{where}/pipelines/{name}: `steps` is a non-empty list")
        steps, known = [], []
        for index, raw in enumerate(steps_raw):
            step = _parse_step(raw, f"{where}/pipelines/{name}/steps[{index}]", known)
            steps.append(step)
            known.append(step.name)
        parsed[name] = steps
    return parsed


def pipelines_path():
    """Where the definitions live.

    `KIT_PIPELINES` is the tests' seam — it lets a fixture project declare a pipeline with a check
    that fails on purpose, which the shipped file has no business containing. The plugin never sets
    it; the default is the file beside this script's own directory.
    """
    override = os.environ.get("KIT_PIPELINES")
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, DEFAULT_PIPELINES)


def load_pipelines(path=None):
    path = path or pipelines_path()
    try:
        document = kit_yaml.load_path(path)
    except OSError as exc:
        raise GateError(f"the pipeline definitions cannot be read: {exc}")
    except kit_yaml.KitYamlError as exc:
        raise GateError(f"{os.path.basename(path)} is not readable as the kit's YAML subset: {exc}")
    return parse_pipelines(document, os.path.basename(path))


def steps_of(pipeline, path=None):
    declared = load_pipelines(path)
    if pipeline not in declared:
        raise GateError(f"no pipeline named {pipeline!r} is declared "
                        f"(declared: {', '.join(sorted(declared))})")
    return declared[pipeline]


# ----------------------------------------------------------------------------------------------
# Run state


def slug(branch):
    """A file name for a branch. The full name is recorded inside the file and verified on read."""
    return _UNSAFE_IN_SLUG.sub("-", branch).strip("-") or "detached"


def state_path(root, branch):
    """The absolute path of this branch's run state, refusing a symlink at a path the kit owns."""
    relative = os.path.join(RUNS_DIR, slug(branch) + ".yml")
    try:
        kit_knowledge.kit_owned(root, RUNS_DIR)
        return kit_knowledge.kit_owned(root, relative)
    except kit_knowledge.SectionError as exc:
        raise GateError(str(exc))


def branch_of(cwd):
    """The checked-out branch, or "" when there is none.

    `symbolic-ref` rather than `rev-parse`: it answers before the first commit too, and a detached
    HEAD failing here is the right answer — no branch means no run.
    """
    try:
        done = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5, cwd=cwd)
        return done.stdout.strip() if done.returncode == 0 else ""
    except Exception:                                    # noqa: BLE001 - no branch, not a crash
        return ""


def load_state(root, branch):
    """This branch's run, or None when there is none.

    A state file whose `branch:` disagrees with the checked-out branch is not this branch's run:
    two branches can slug to one name, and silently sharing a run between them would be the worst
    possible answer. Raises GateError on anything unreadable, so callers that must fail open —
    every hook — can catch it in one place.
    """
    path = state_path(root, branch)
    if not os.path.exists(path):
        return None
    try:
        document = kit_yaml.load_path(path)
    except OSError as exc:
        raise GateError(f"run state cannot be read: {exc}")
    except kit_yaml.KitYamlError as exc:
        raise GateError(f"run state is not readable as the kit's YAML subset: {exc}")
    if not isinstance(document, dict) or not isinstance(document.get("steps"), list):
        raise GateError(f"{os.path.relpath(path, root)} is not a run state file")
    if document.get("branch") != branch:
        return None
    return document


def _self_ignore(directory):
    """Make the run-state directory ignore itself, once, when it is created.

    Run state is working state and never repository content — but the project's own `.gitignore` is
    the project's file, and a `git: tree_clean` check that fails on the gate's own artifact would
    make the PR step unpassable in every repository that had not been told about this release. A
    `.gitignore` *inside* a directory the kit owns entirely needs nobody's permission, and git reads
    it even though its own `*` covers it.
    """
    marker = os.path.join(directory, ".gitignore")
    if os.path.exists(marker):
        return
    try:
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("# The step gate's run state: working state, never repository content.\n"
                         "*\n")
    except OSError:
        # Not being able to write it costs a dirty tree, not the run. The check will say so.
        pass


def write_state(root, state):
    """Replace the run's state file atomically.

    Two sessions share one working tree during a sprint, and a half-written state file is
    indistinguishable from a corrupt one — which every hook reads as "there is no run".
    """
    path = state_path(root, state["branch"])
    text = kit_yaml.dump(state)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    _self_ignore(directory)
    temporary = path + ".kit-new"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise GateError(f"run state cannot be written: {exc}")
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return path


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def session_id():
    """Who owns this run.

    A sprint orchestrator and its headless child share one working tree, and the child checks that
    tree out onto its own branch — so a run keyed by branch alone is read by the orchestrator as its
    own, and the old Stop guard demanded of it, every turn, the exact action the sprint contract
    forbids. `sprint` sets `AGENT_KIT_SESSION_ID` to the same uuid it passes as `--session-id`, so
    under a sprint the owner is correct by construction; `CLAUDE_CODE_SESSION_ID` covers an ordinary
    session. Unset is legal and means "held for whoever is here", which is right for a repository
    with one session in it.
    """
    return (os.environ.get("AGENT_KIT_SESSION_ID")
            or os.environ.get("CLAUDE_CODE_SESSION_ID") or "").strip() or None


def new_state(root, branch, pipeline):
    return {
        "version": 1,
        "branch": branch,
        "pipeline": pipeline,
        "session": session_id(),
        "state": RUN_OPEN,
        "opened_at": now(),
        "opened_at_commit": _git(root, "rev-parse", "HEAD") or "",
        "steps": [],
    }


def step_state(state, name):
    for entry in state["steps"]:
        if entry.get("name") == name:
            return entry
    return None


def verdict_of(state, name):
    entry = step_state(state, name)
    return entry.get("verdict") if entry else None


def is_terminal(state, name):
    return verdict_of(state, name) in TERMINAL


def unsettled(state, steps):
    """The declared steps with no terminal verdict, in declaration order."""
    return [step.name for step in steps if not is_terminal(state, step.name)]


def owned_by(state, session):
    """Whether a session may be held for this run.

    Unset holds anyone: a repository with one session in it behaves exactly as it does today. A run
    that names its owner holds only the owner, which is what keeps a sprint orchestrator out of its
    own child's pipeline.
    """
    owner = state.get("session")
    return not owner or not session or owner == session


# ----------------------------------------------------------------------------------------------
# Checks


class Evidence:
    """What one check did, kept in state so a resumed session learns it from the file."""

    __slots__ = ("check", "command", "exit_code", "output", "at")

    def __init__(self, check, command, exit_code, output):
        self.check = check
        self.command = command
        self.exit_code = exit_code
        self.output = output
        self.at = now()

    @property
    def passed(self):
        return self.exit_code == 0

    def record(self):
        return {"check": self.check, "command": self.command, "exit": self.exit_code,
                "output": self.output, "at": self.at}


def _tail(text):
    text = (text or "").strip()
    return text[-OUTPUT_TAIL:] if len(text) > OUTPUT_TAIL else text


def _git(root, *args):
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30, cwd=root)
        return done.stdout.strip() if done.returncode == 0 else ""
    except Exception:                                    # noqa: BLE001 - absent git is not a crash
        return ""


def _shell(root, command):
    try:
        done = subprocess.run(command, shell=True, capture_output=True, text=True,
                              timeout=CHECK_TIMEOUT, cwd=root)
    except subprocess.TimeoutExpired:
        return 124, f"no output after {CHECK_TIMEOUT}s — the gate stopped waiting"
    except OSError as exc:
        return 126, str(exc)
    return done.returncode, _tail((done.stdout or "") + (done.stderr or ""))


def _run_check(root, command):
    refused = guard.refusal(command)
    if refused:
        # A pipeline definition is repository content, and stage 4 hands the file to the project.
        # A `PreToolUse` hook never sees a subprocess a script starts, so this is the only place
        # the kit's never-rules can be enforced on a command the gate itself runs.
        return Evidence(f"run: {command}", command, 125,
                        f"refused without running — {refused.reason}")
    code, output = _shell(root, command)
    return Evidence(f"run: {command}", command, code, output)


def _exists_check(root, pattern):
    if os.path.isabs(pattern) or ".." in pattern.split("/"):
        raise GateError(f"`exists: {pattern}` must be a path inside the project")
    matches = sorted(globlib.glob(os.path.join(root, pattern), recursive=True))
    code = 0 if matches else 1
    found = "\n".join(os.path.relpath(m, root) for m in matches[:20]) or "no file matches"
    return Evidence(f"exists: {pattern}", f"glob {pattern}", code, found)


def _git_check(root, which, state):
    if which == "tree_clean":
        dirty = _git(root, "status", "--porcelain")
        return Evidence("git: tree_clean", "git status --porcelain", 1 if dirty else 0,
                        _tail(dirty) or "the working tree is clean")

    if which == "commits_on_branch":
        # Against the commit HEAD pointed at when the run opened, not against the default branch:
        # every feature in a stacked sprint sits on its parent's branch, and the default-branch
        # comparison would count the parent's commits and pass a step that produced nothing.
        since = state.get("opened_at_commit") or ""
        # The commit may be gone — a rebase, an amended first commit — and a span naming it would
        # make git fail rather than answer. Fall back to the whole branch and say which was counted.
        resolved = _git(root, "rev-parse", "--verify", "--quiet", since + "^{commit}") if since \
            else ""
        span = f"{resolved}..HEAD" if resolved else "HEAD"
        count = _git(root, "rev-list", "--count", span)
        made = int(count) if count.isdigit() else 0
        return Evidence("git: commits_on_branch", f"git rev-list --count {span}",
                        0 if made else 1,
                        f"{made} commit(s) {'since the run opened' if resolved else 'on this branch'}")

    upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if not upstream:
        return Evidence("git: pushed", "git rev-parse @{upstream}", 1,
                        "this branch has no upstream — it has never been pushed")
    ahead = _git(root, "rev-list", "--count", f"{upstream}..HEAD")
    unpushed = int(ahead) if ahead.isdigit() else 0
    return Evidence("git: pushed", f"git rev-list --count {upstream}..HEAD",
                    1 if unpushed else 0,
                    f"{unpushed} commit(s) not on {upstream}" if unpushed
                    else f"level with {upstream}")


def run_check(root, kind, value, state):
    """Execute one check and report what it found. Raises GateError only on a malformed check."""
    if kind == "run":
        return _run_check(root, value)
    if kind == "exists":
        return _exists_check(root, value)
    if kind == "git":
        return _git_check(root, value, state)
    raise GateError(f"unknown check kind `{kind}:`")
