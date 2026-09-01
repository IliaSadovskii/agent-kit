"""The world a case runs in, and it touches nothing outside itself.

A temporary directory, its own `HOME`, its own git identity, a bare remote a
directory away, and a `gh` on `PATH` that is a script. Nothing reaches the
network, so a case is the same on a machine with no login as on one with — which
is the whole reason the bench can compare one version of the kit against the next.

The baseline project is deliberately tiny: one file worth changing and one
command worth running. What a case plants goes on top of it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..errors import StateError
from .cases import Case

#: The project every case starts from. `check.sh` is what `verify` runs: a
#: command that is instantly green, so a case that is not about the suite does
#: not pay for one, and a case that is about it replaces this file.
BASELINE = {
    "money.py": "AMOUNT = 1000\n",
    "check.sh": "#!/bin/sh\nexit 0\n",
    # A described project, because that is the ordinary one. A baseline with no
    # description would make every case run in a world the kit refuses, and a
    # baseline that said `knowledge = ""` would measure every mechanism about
    # knowledge in a project that declares it keeps none. The case about a
    # project nobody described takes this file away in its own `plant.sh`, so
    # what the disarm gives back is the ordinary world.
    # Two records and not one. With a single heading, a judge asking whether a
    # block landed *under the record it addressed* is green for a block anywhere
    # in the file — the end of the section and the end of the file are the same
    # line — and a judge that cannot fail is not a judge.
    "docs/knowledge/product.md": (
        "# Продукт\n"
        "\n"
        "## Части\n"
        "\n"
        "- деньги — сумма и ставка, из которых считается цена — `key: money` · `walked: 2026-08-20`\n"
        "\n"
        "## Чего мы не делаем\n"
        "\n"
        "Ничего, кроме денег.\n"
    ),
    ".agent-kit/v3/project.toml": (
        "[project]\n"
        'default_branch = "main"\n'
        "command_timeout = 20\n"
        "\n"
        "[commands]\n"
        'test = "sh check.sh"\n'
    ),
}

#: What the machine a case runs on has chosen, and it chooses two things.
#:
#: No pause between attempts: the pause is the kit's, not the case's, and a case
#: about something else would sit through it for nothing — three refused
#: sessions in a case about a feature that does not land would cost minutes of
#: waiting to measure something that has nothing to do with waiting. The case
#: that *is* about the pause plants its own number over this file.
#:
#: And the provider it runs on, which is true of this world rather than new to
#: it: every case already drives the kit with `--provider fake`, which beats
#: both the role table and this default, so nothing here changes what any case
#: measures. What it changes is the door, whose first rung asks the machine
#: before the project since S9a — a world that named no provider would answer
#: `no-provider` in all of them.
#:
#: **A case that plants its own `config.toml` writes this file whole and does
#: not inherit the line.** Harmless today: no case that replaces the machine's
#: configuration also asks the door a question. A case that does both would
#: need to write the provider back in, and would answer `no-provider` until it
#: did — so a new door case planted among them must be read with this in mind.
MACHINE = '[machine]\nbackoff = 0\nprovider = "fake"\n'

#: A `gh` that answers the two things delivery asks it, and writes down every
#: call so a judge can read what it was asked.
#: Who a case's commits are by. Written into the environment as well as the
#: repository's config, because git prefers the environment and would
#: otherwise sign the commit with the name of whoever ran the bench.
IDENTITY = ("the bench", "bench@example.com")

#: One flag per branch, and parallelism is what made that necessary: with one
#: flag for the whole world the second feature's `pr view` found the first
#: one's pull request and delivered without ever opening its own.
GH = """#!/bin/sh
printf '%s\\n' "$@" >> "$BENCH/gh-argv"
mark() { echo "$BENCH/gh-opened-$(printf '%s' "$1" | tr / -)"; }
if [ "$2" = "view" ]; then
  [ -f "$(mark "$3")" ] || exit 1
  echo https://github.com/owner/project/pull/7
  exit 0
fi
head=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--head" ]; then head="$2"; fi
  shift
done
touch "$(mark "$head")"
echo https://github.com/owner/project/pull/7
"""


class WorldError(StateError):
    """The world could not be made, so nothing was judged."""


@dataclass(frozen=True)
class World:
    """Where a case lives while it runs."""

    repo: Path
    origin: Path
    env: dict[str, str]

    @property
    def run_dir(self) -> Path:
        return self.repo / ".agent-kit/v3/runs"


def make_world(case: Case, into: Path) -> World:
    """Everything the case needs, in one directory that can be deleted whole."""
    into.mkdir(parents=True, exist_ok=True)
    home = _made(into / "home")
    binaries = _made(into / "bin")
    repo = _made(into / "project")
    origin = into / "origin.git"

    env = _environment(into, home, binaries, repo)
    _write_gh(binaries / "gh")
    _write(home / ".config/agent-kit/config.toml", MACHINE)

    _lay_out(repo, case)
    _make_repository(repo, origin, env)
    _plant(case, repo, origin, env)

    return World(repo=repo, origin=origin, env=env)


#: What a case may inherit from the machine, and nothing else.
#:
#: An allow-list, not a deny-list, and the difference is the whole point. A
#: deny-list was written first and it let `GIT_AUTHOR_NAME` through, so every
#: commit a case made was signed by whatever the surrounding machine carried —
#: and `GIT_DIR` a variable away, which would have pointed a case's git at the
#: repository the bench was run from. A variable nobody thought of is the
#: normal case, so the answer cannot be a list of the ones somebody did.
INHERITED = (
    "PATH",  # replaced below, but its value is the machine's
    "LANG",
    "LC_ALL",
    "TERM",
    "TZ",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "SYSTEMROOT",
)


def _environment(bench: Path, home: Path, binaries: Path, repo: Path) -> dict[str, str]:
    """A machine of its own. Nothing here reads the one the bench is running on."""
    env = {name: os.environ[name] for name in INHERITED if name in os.environ}
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            # git reads two files outside the repository unless it is told not to.
            "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
            "GIT_CONFIG_SYSTEM": str(home / ".gitconfig-system"),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": IDENTITY[0],
            "GIT_AUTHOR_EMAIL": IDENTITY[1],
            "GIT_COMMITTER_NAME": IDENTITY[0],
            "GIT_COMMITTER_EMAIL": IDENTITY[1],
            "PATH": f"{binaries}{os.pathsep}{os.environ.get('PATH', '')}",
            # The case must run the kit that is running the bench, not one
            # that happens to be installed on this machine — otherwise the
            # bench measures a version nobody asked it about.
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            # Read by the scripts a case plants, and by the `gh` above.
            "BENCH": str(bench),
            # The project itself, which is not where a session stands: with a
            # tree per run the cwd is the run's own worktree, so a script that
            # wants to reach the project — to skip a feature, to read a run —
            # has to be told where it is.
            "REPO": str(repo),
            # How a plant or a judge runs the kit it is measuring. The same
            # interpreter, so a case never reaches a version nobody asked about.
            "KIT": f"{sys.executable} -m agent_kit",
            # The same interpreter on its own, so a judge can ask the kit what
            # a fact of its own is instead of writing the answer down beside
            # it. A judge that checks a string it wrote itself measures
            # nothing — the precedent is S8a's derived part key.
            "PYTHON": sys.executable,
        }
    )
    return env


def _write_gh(path: Path) -> None:
    path.write_text(GH, encoding="utf-8")
    path.chmod(0o755)


def _lay_out(repo: Path, case: Case) -> None:
    """The baseline, then what the way in needs, then whatever the case lays over it.

    The middle one is for a case that declares an audit, and for no other. A
    lens needs something to measure, and putting a manifest into the baseline
    would put it into ninety cases that are about something else — and a change
    to what every case starts from is a change that can quietly disarm the ones
    that were reading it. `BatchCase.declaration()` is the precedent, word for
    word.
    """
    for relative, text in BASELINE.items():
        _write(repo / relative, text)
    if case.audit is not None:
        for relative, text in case.audit.world().items():
            _write(repo / relative, text)
    overlay = case.overlay
    if overlay is not None:
        shutil.copytree(overlay, repo, dirs_exist_ok=True)


def _make_repository(repo: Path, origin: Path, env: dict[str, str]) -> None:
    _git(repo, env, "init", "-b", "main")
    _git(repo, env, "config", "user.email", IDENTITY[1])
    _git(repo, env, "config", "user.name", IDENTITY[0])
    _run(["git", "init", "--bare", "-b", "main", str(origin)], repo.parent, env)
    _git(repo, env, "remote", "add", "origin", str(origin))
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-m", "the baseline every case starts from")
    _git(repo, env, "push", "-u", "origin", "main")


def _plant(case: Case, repo: Path, origin: Path, env: dict[str, str]) -> None:
    script = case.plant
    if script is None:
        return
    planting = dict(env, SLUG=case.slug, BRANCH=case.branch, REPO=str(repo), ORIGIN=str(origin))
    done = subprocess.run(
        ["sh", str(script)], cwd=repo, env=planting, capture_output=True, text=True, timeout=120
    )
    if done.returncode != 0:
        raise WorldError(
            "plant-failed",
            f"{case.name}: plant.sh вышел с кодом {done.returncode}: "
            f"{(done.stderr or done.stdout).strip()[:400] or 'and said nothing'}",
        )


def _made(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if path.suffix == ".sh":
        path.chmod(0o755)


def _git(repo: Path, env: dict[str, str], *argv: str) -> None:
    _run(["git", *argv], repo, env)


def _run(argv: list[str], cwd: Path, env: dict[str, str]) -> None:
    done = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise WorldError(
            "world-failed",
            f"{' '.join(argv)} вышел с кодом {done.returncode}: "
            f"{(done.stderr or done.stdout).strip()[:400] or 'and said nothing'}",
        )
