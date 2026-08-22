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

from ..errors import KitError
from ..logs import get_logger
from .cases import Case, read_case
from .world import World, make_world

#: A case is a handful of shell scripts and a provider that answers from files.
#: One that has said nothing for this long is stuck.
TIMEOUT = 300

#: What a judge's exit code means. Anything else is the judge itself breaking.
JUDGE_FIRED = 0
JUDGE_DID_NOT = 1

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
        created = _kit(world, ["run", "new", case.slug, "--brief", case.brief])
        if created.returncode != 0:
            return unjudgeable(f"the run could not be created: {_said(created)}")
        went = _kit(world, ["run", "go", case.slug, "--provider", "fake", *_replies(case)])
    except subprocess.SubprocessError as broken:
        return unjudgeable(f"the kit did not come back: {broken}")

    return _judge(case, world, went)


# --- running the kit, as a command and not as an import ---------------------


def _kit(world: World, argv: list[str]) -> subprocess.CompletedProcess:
    """The kit as somebody would run it, in the world the case made.

    Not an import: a case is a run of the command, so the exit code a judge
    reads is the one a script would have read.
    """
    return subprocess.run(
        [sys.executable, "-m", "agent_kit", "-C", str(world.repo), *argv],
        cwd=world.repo,
        env=world.env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def _replies(case: Case) -> list[str]:
    options: list[str] = []
    for path in case.replies:
        options += ["--option", f"reply={path}"]
    return options


# --- the judges -------------------------------------------------------------


def _judge(case: Case, world: World, went: subprocess.CompletedProcess) -> Verdict:
    """What the case declared, and then the script it brought."""
    expect = case.expect
    if went.returncode != expect.exit_code:
        return did_not(f"it exited {went.returncode} and the case wants {expect.exit_code}: {_said(went)}")

    state = _state(world, case.slug)
    if state is None:
        return unjudgeable(f"no run state was left to read: {_said(went)}")

    status = state.get("status")
    if status != expect.status:
        return did_not(f"the run is {status!r} and the case wants {expect.status!r}")

    reason = (state.get("reason") or "").strip()
    if expect.refusal and expect.refusal not in reason:
        return did_not(f"the run says {reason or 'nothing'!r}, which does not name {expect.refusal!r}")

    steps = {step.get("name"): step.get("status") for step in state.get("steps") or []}
    for name, wanted in expect.steps.items():
        if steps.get(name) != wanted:
            return did_not(f"step {name} is {steps.get(name)!r} and the case wants {wanted!r}")

    return _judge_script(case, world, went.returncode)


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
    try:
        done = subprocess.run(
            ["sh", str(script)], cwd=world.repo, env=env, capture_output=True, text=True, timeout=TIMEOUT
        )
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
