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
    if value is None or (isinstance(value, str) and not value.strip()):
        raise GateError(f"{where}: `{kind}:` needs a non-empty value")
    if not isinstance(value, str):
        # `run: true` and `run: 0` are read as a boolean and a number by any YAML reader, and
        # "needs a non-empty value" is a baffling thing to be told about a value that is plainly
        # there. Stage 4 hands this file to the project, so this is the first error a person
        # editing it will meet.
        raise GateError(f"{where}: `{kind}: {value}` reads as {type(value).__name__}, not text — "
                        "quote it if that is the command you meant")
    if kind == "exists":
        _reject_escaping_glob(value.strip(), where)
    if kind == "git" and value not in GIT_CHECKS:
        raise GateError(f"{where}: `git: {value}` is not one of {', '.join(GIT_CHECKS)}")
    return kind, value.strip()


def _reject_escaping_glob(pattern, where):
    """An `exists:` pattern names a path inside the project. Checked when the file is read.

    Stage 4 hands the definition file to the project, and a glob that cannot be run is a mistake
    the owner should hear about at the first `step start` rather than three steps later as an
    exit 2 in the middle of a run.
    """
    if os.path.isabs(pattern) or ".." in pattern.replace(os.sep, "/").split("/"):
        raise GateError(f"{where}: `exists: {pattern}` must be a path inside the project")


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


def default_pipelines_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, DEFAULT_PIPELINES)


def pipelines_override():
    """The definition file in force instead of the plugin's own, or None.

    `KIT_PIPELINES` is the tests' seam — it lets a fixture project declare a pipeline with a check
    that fails on purpose, which the shipped file has no business containing. An environment
    variable is also something the agent under the gate can set, and a forged definition with
    `done_when: []` would settle a real step without running anything. So the override is not
    secret, it is *recorded*: every write stamps it into the run, and the `Stop` hook refuses to
    release a run whose steps were closed against definitions that were not the plugin's.
    """
    return os.environ.get("KIT_PIPELINES") or None


def pipelines_path():
    return pipelines_override() or default_pipelines_path()


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
    for entry in document["steps"]:
        # Every field below is read without a second thought elsewhere. A state file is working
        # state, but `.gitignore` does not apply to a path a commit already tracks, so one can
        # arrive in a pull request — and a `steps:` list of strings would reach `entry.get` as an
        # AttributeError, i.e. a traceback out of a hook.
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) \
                or entry.get("verdict") not in (OPEN,) + TERMINAL:
            raise GateError(f"{os.path.relpath(path, root)} has a step entry the gate did not "
                            f"write: {entry!r}")
    if document.get("branch") != branch:
        return None
    if _git(root, "ls-files", "--error-unmatch", "--", os.path.relpath(path, root)):
        # Only the gate writes run state, and the gate never commits it. A tracked one came from
        # somebody's commit, and every verdict in it is a claim nothing checked.
        raise GateError(f"{os.path.relpath(path, root)} is tracked by git — run state is written "
                        "by the gate and committed by nobody, so this file's verdicts prove "
                        "nothing. Remove it from the index and let the gate write its own")
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
    # `lexists`, not `exists`: a symlink to a file that does not exist yet reads as absent, and the
    # write would then create whatever it points at. O_EXCL and O_NOFOLLOW make the same statement
    # to the kernel, which is the half that cannot be raced.
    if os.path.lexists(marker):
        return
    try:
        handle = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except OSError:
        # Not being able to write it costs a dirty tree, not the run. The check will say so.
        return
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write("# The step gate's run state: working state, never repository content.\n*\n")
    except OSError:
        pass


def write_state(root, state):
    """Replace the run's state file atomically.

    Two sessions share one working tree during a sprint, and a half-written state file is
    indistinguishable from a corrupt one — which every hook reads as "there is no run".
    """
    path = state_path(root, state["branch"])
    override = pipelines_override()
    if override:
        state["overridden_definitions"] = override
    try:
        text = kit_yaml.dump(state)
    except kit_yaml.KitYamlError as exc:
        # A value the writer cannot render is a step that can never be settled, and the Stop hook
        # would then hold the turn for ever — the exact deadlock the design forbids. Say so as a
        # gate error the caller reports, rather than as a traceback out of the command.
        raise GateError(f"this run's state cannot be written as the kit's YAML subset: {exc}")
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    _self_ignore(directory)
    temporary = path + ".kit-new"
    try:
        # O_NOFOLLOW, because this sibling of the state file is a path the kit owns by name just as
        # much as the state file is — and `os.replace` would then move the *link* onto the checked
        # path, so `kit_owned` on the state file alone never sees it.
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                             0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise GateError(f"run state cannot be written: {exc}")
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return path


def discard_state(root, branch):
    """Remove this branch's run state. The only path that deletes it, and it closes nothing."""
    path = state_path(root, branch)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise GateError(f"run state cannot be discarded: {exc}")


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
    # `CLAUDE_CODE_SESSION_ID` first, because the harness sets it and the agent does not. Setting
    # a bogus owner would otherwise silence the Stop hook for the rest of the run in one command.
    # `AGENT_KIT_SESSION_ID` is what `sprint` passes as `--session-id`, so under a sprint the two
    # agree; it stands in only where the harness sets nothing.
    return (os.environ.get("CLAUDE_CODE_SESSION_ID")
            or os.environ.get("AGENT_KIT_SESSION_ID") or "").strip() or None


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
    """git's stdout, or None when git did not answer.

    None rather than `""`, because the two `git:` checks that prove anything read emptiness as
    success: an empty `status --porcelain` is a clean tree, and an empty count is nothing left to
    push. Collapsing "git said nothing" into "git said nothing is wrong" makes an index.lock, a
    broken repository or an absent git into a passing PR step — a check that fails open is worse
    than no check, because it reports in the voice of proof.
    """
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30, cwd=root)
        return done.stdout.strip() if done.returncode == 0 else None
    except Exception:                                    # noqa: BLE001 - absent git is not a crash
        return None


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
    _reject_escaping_glob(pattern, "exists")
    # `recursive=True` walks through a symlinked directory, so a link in the repository is a way to
    # ask whether a file exists in somebody's home. Keep only what really resolves inside.
    inside = os.path.realpath(root) + os.sep
    matches = sorted(m for m in globlib.glob(os.path.join(root, pattern), recursive=True)
                     if os.path.realpath(m).startswith(inside))
    code = 0 if matches else 1
    found = "\n".join(os.path.relpath(m, root) for m in matches[:20]) or "no file matches"
    return Evidence(f"exists: {pattern}", f"glob {pattern}", code, found)


def _git_check(root, which, state):
    if which == "tree_clean":
        dirty = _git(root, "status", "--porcelain")
        if dirty is None:
            return Evidence("git: tree_clean", "git status --porcelain", 1,
                            "git did not answer — the tree's state is unknown, which is not the "
                            "same as clean")
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
        made = int(count) if count and count.isdigit() else 0
        return Evidence("git: commits_on_branch", f"git rev-list --count {span}",
                        0 if made else 1,
                        f"{made} commit(s) {'since the run opened' if resolved else 'on this branch'}")

    upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if not upstream:
        return Evidence("git: pushed", "git rev-parse @{upstream}", 1,
                        "this branch has no upstream — it has never been pushed")
    ahead = _git(root, "rev-list", "--count", f"{upstream}..HEAD")
    if ahead is None or not ahead.isdigit():
        return Evidence("git: pushed", f"git rev-list --count {upstream}..HEAD", 1,
                        "git did not answer — whether this branch is pushed is unknown, which is "
                        "not the same as pushed")
    unpushed = int(ahead)
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
