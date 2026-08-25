"""Running a case, and judging what it left behind.

Three outcomes, and the third is not a third kind of failure:

- **fired** — the mechanism the case plants did what it is there to do;
- **did not fire** — the run went another way, and the line says which;
- **could not be judged** — the case never got as far as producing an answer.

A judge reads the run's own state and the step directories, which is exactly
what the kit already writes. If a judge cannot see something, that is a finding
about the kit and not about the bench.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..errors import ExitCode, KitError
from ..logs import get_logger
from ..shell import kill_group
from .cases import Case, read_case
from .world import World, make_world

#: A case is a handful of shell scripts and a provider that answers from files.
#: One that has said nothing for this long is stuck.
TIMEOUT = 300

#: What a judge's exit code means. Anything else is the judge itself breaking.
JUDGE_FIRED = 0
JUDGE_DID_NOT = 1

#: Codes the kit leaves when the fault is the kit's or the case's, not a
#: mechanism regressing: a defect in the kit, a command typed wrong, a
#: configuration that is missing something. A case that expected one of these
#: is asking about something the bench cannot tell it.
BROKEN = (int(ExitCode.INTERNAL), int(ExitCode.USAGE), int(ExitCode.CONFIG))

log = get_logger("bench")


@dataclass(frozen=True)
class Verdict:
    fired: bool
    judged: bool = True
    why: str = ""


FIRED = Verdict(fired=True)


def did_not(why: str) -> Verdict:
    return Verdict(fired=False, why=why)


def unjudgeable(why: str) -> Verdict:
    return Verdict(fired=False, judged=False, why=why)


@dataclass(frozen=True)
class Result:
    name: str
    verdict: Verdict
    #: Where the world was left, when it was worth keeping.
    where: Path | None = None

    @property
    def said(self) -> str:
        if not self.verdict.judged:
            return f"could not be judged — {self.verdict.why}"
        return "fired" if self.verdict.fired else f"did not fire — {self.verdict.why}"


def run_named(root: Path, name: str, into: Path, keep: bool = False) -> Result:
    """One case, from its name. A case that cannot be read is one that cannot be judged."""
    try:
        case = read_case(root, name)
    except KitError as unreadable:
        return Result(name, unjudgeable(f"{unreadable.code}: {unreadable.detail}"))
    return run_case(case, into, keep)


def run_case(case: Case, into: Path, keep: bool = False) -> Result:
    """Make the world, run the kit in it, judge what is left, then throw it away."""
    where = into / case.name
    if where.exists():
        shutil.rmtree(where)

    verdict = _run_and_judge(case, where)
    if verdict.fired or not keep:
        shutil.rmtree(where, ignore_errors=True)
        return Result(case.name, verdict)
    return Result(case.name, verdict, where=where)


def _run_and_judge(case: Case, where: Path) -> Verdict:
    try:
        world = make_world(case, where)
    except (KitError, OSError, subprocess.SubprocessError) as broken:
        return unjudgeable(f"the world could not be made: {broken}")

    try:
        went = _drive_a_batch(case, world) if case.batch else _drive_a_run(case, world)
    except subprocess.SubprocessError as broken:
        return unjudgeable(f"the kit did not come back: {broken}")
    if isinstance(went, Verdict):
        return went

    _write_down(world, went)
    return _judge(case, world, went)


def _drive_a_run(case: Case, world: World):
    created = _kit(world, ["run", "new", case.slug, "--brief", case.brief])
    if created.returncode != 0:
        return unjudgeable(f"the run could not be created: {_said(created)}")
    waiting = [] if case.wait is None else ["--wait", str(case.wait)]
    return _kit(world, ["run", "go", case.slug, "--provider", "fake", *waiting, *_replies(case)])


def _drive_a_batch(case: Case, world: World):
    """The one thing the bench learns for S8, and it is two commands rather than one.

    A batch's declaration is a file, so the case writes the file it declared and
    the kit reads it the way a person's would be read. A case that expects the
    declaration itself to be refused wants that exit code, so `batch new` is
    what is judged where `batch go` never runs.
    """
    # Beside the world rather than inside the project: a case about two runs
    # not dirtying one working copy must not be the thing that dirties it.
    declared = Path(world.env["BENCH"]) / "batch.toml"
    declared.write_text(case.batch.declaration(), encoding="utf-8")

    made = _kit(world, ["batch", "new", str(declared)])
    if made.returncode != 0:
        # The declaration was refused. That is an answer, not a broken case: a
        # cycle and a need that names nothing are two of the mechanisms here.
        return made
    return _kit(
        world,
        ["batch", "go", case.batch.name, "--provider", "fake", *_replies_per_feature(case)],
    )


def _replies_per_feature(case: Case) -> list[str]:
    options: list[str] = []
    for feature in case.batch.features:
        for path in case.replies_for(feature.slug):
            options += ["--option", f"{feature.slug}:reply={path}"]
    return options


def _write_down(world: World, went: subprocess.CompletedProcess) -> None:
    """What the kit printed, where a judge can read it.

    A refusal that never reaches `run.json` — a machine that was full, a run
    somebody else holds — leaves a judge nothing to compare but an exit code,
    and two different refusals share one. The rule is that a case reads a code;
    this is what makes it possible for those.
    """
    said = f"{went.stdout or ''}\n{went.stderr or ''}"
    (Path(world.env["BENCH"]) / "kit-said").write_text(said, encoding="utf-8")


# --- running the kit, as a command and not as an import ---------------------


def _kit(world: World, argv: list[str]) -> subprocess.CompletedProcess:
    """The kit as somebody would run it, in the world the case made.

    Not an import: a case is a run of the command, so the exit code a judge
    reads is the one a script would have read.

    It gets its own process group, like every other place in the kit that starts
    somebody else's process. A run that has to be timed out has, by then, a
    child of its own started the same way — killing only the kit would leave it
    running against a world this function is about to delete.
    """
    return _group(
        [sys.executable, "-m", "agent_kit", "-C", str(world.repo), *argv], world.repo, world.env
    )


def _group(argv: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """One command, and everything it started dies with it."""
    child = subprocess.Popen(
        argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        kill_group(child)
        raise
    return subprocess.CompletedProcess(argv, child.returncode, stdout=stdout, stderr=stderr)


def _replies(case: Case) -> list[str]:
    options: list[str] = []
    for path in case.replies:
        options += ["--option", f"reply={path}"]
    return options


# --- the judges -------------------------------------------------------------


def _judge(case: Case, world: World, went: subprocess.CompletedProcess) -> Verdict:
    """What the case declared, and then the script it brought."""
    expect = case.expect
    if went.returncode in BROKEN and went.returncode != expect.exit_code:
        # A kit that crashed or was told something it could not read has not
        # measured the mechanism at all. Printing that in the column where a
        # regression is printed points at the wrong thing.
        return unjudgeable(f"the kit exited {went.returncode}: {_said(went)}")
    if went.returncode != expect.exit_code:
        return did_not(f"it exited {went.returncode} and the case wants {expect.exit_code}: {_said(went)}")

    if case.batch is not None:
        return _judge_a_batch(case, world, went)

    state = _state(world, case.slug)
    if state is None:
        return unjudgeable(f"no run state was left to read: {_said(went)}")

    status = state.get("status")
    if expect.status and status != expect.status:
        return did_not(f"the run is {status!r} and the case wants {expect.status!r}")

    reason = (state.get("reason") or "").strip()
    if expect.refusal and expect.refusal not in reason:
        return did_not(f"the run says {reason or 'nothing'!r}, which does not name {expect.refusal!r}")

    steps = {step.get("name"): step.get("status") for step in state.get("steps") or []}
    for name, wanted in expect.steps.items():
        if steps.get(name) != wanted:
            return did_not(f"step {name} is {steps.get(name)!r} and the case wants {wanted!r}")

    return _judge_script(case, world, went.returncode)


def _judge_a_batch(case: Case, world: World, went: subprocess.CompletedProcess) -> Verdict:
    """Every feature separately, because several runs have no one status between them."""
    if not case.expect.features:
        return _judge_script(case, world, went.returncode)

    held = _batch_state(world, case.batch.name)
    if held is None:
        return unjudgeable(f"no batch state was left to read: {_said(went)}")
    where = {feature.get("slug"): feature.get("status") for feature in held.get("features") or []}
    for slug, wanted in case.expect.features.items():
        if where.get(slug) != wanted:
            return did_not(f"feature {slug} is {where.get(slug)!r} and the case wants {wanted!r}")
    return _judge_script(case, world, went.returncode)


def _batch_state(world: World, name: str) -> dict | None:
    try:
        held = json.loads(
            (world.repo / ".agent-kit/v3/batches" / name / "batch.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    return held if isinstance(held, dict) else None


def _state(world: World, slug: str) -> dict | None:
    try:
        held = json.loads((world.run_dir / slug / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return held if isinstance(held, dict) else None


def _judge_script(case: Case, world: World, exit_code: int) -> Verdict:
    script = case.judge
    if script is None:
        return FIRED

    env = dict(
        world.env,
        SLUG=case.slug,
        BRANCH=case.branch,
        REPO=str(world.repo),
        ORIGIN=str(world.origin),
        RUN_DIR=str(world.run_dir / case.slug),
        EXIT_CODE=str(exit_code),
    )
    if case.batch is not None:
        env.update(
            BATCH=case.batch.name,
            BATCH_FILE=str(world.repo / ".agent-kit/v3/batches" / case.batch.name / "batch.json"),
            TREES=str(world.repo / ".agent-kit/v3/trees"),
        )
    try:
        done = _group(["sh", str(script)], world.repo, env)
    except subprocess.SubprocessError as broken:
        return unjudgeable(f"judge.sh did not come back: {broken}")

    said = (done.stderr or done.stdout).strip().replace("\n", "; ")
    if done.returncode == JUDGE_FIRED:
        return FIRED
    if done.returncode == JUDGE_DID_NOT:
        return did_not(said or "the judge said no and did not say why")
    return unjudgeable(f"judge.sh exited {done.returncode}: {said or 'and said nothing'}")


def _said(done: subprocess.CompletedProcess) -> str:
    printed = (done.stderr or done.stdout).strip()
    return printed.splitlines()[-1] if printed else "it said nothing"
