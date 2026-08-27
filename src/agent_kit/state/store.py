"""The one door to a run's state.

One writer per run — its own driver. Everyone else reads. Every write is whole:
written beside the file and renamed over it, so a writer that dies leaves the
previous record intact rather than half of the next one.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Callable

from ..errors import StateError
from ..logs import get_logger
from ..paths import ProjectPaths, project_paths
from .migrations import migrate
from .schema import Run, Step, check_slug

RUN_FILE = "run.json"

log = get_logger("state")


class RunStore:
    """Runs of one project, under `.agent-kit/v3/runs/`."""

    def __init__(self, root: Path | str) -> None:
        self.paths: ProjectPaths = project_paths(root)

    # --- reading ----------------------------------------------------------

    def run_root(self, slug: str) -> Path:
        return self.paths.run_dir(check_slug(slug))

    def path_for(self, slug: str) -> Path:
        return self.run_root(slug) / RUN_FILE

    def exists(self, slug: str) -> bool:
        return self.path_for(slug).is_file()

    def list(self) -> list[str]:
        if not self.paths.runs_dir.is_dir():
            return []
        return sorted(entry.name for entry in self.paths.runs_dir.iterdir() if (entry / RUN_FILE).is_file())

    def load(self, slug: str) -> Run:
        path = self.path_for(slug)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise StateError("unknown-run", f"{slug}: no run under {self.paths.runs_dir}") from error
        except OSError as error:
            raise StateError("unreadable-run", f"{path}: {error}") from error

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise StateError("unreadable-run", f"{path} is not valid JSON: {error}") from error
        if not isinstance(data, dict):
            raise StateError("unreadable-run", f"{path} does not hold a run")

        return Run.from_dict(migrate(data, where=str(path)))

    # --- writing ----------------------------------------------------------

    def create(self, slug: str, steps: list[str] | tuple[str, ...] | None = None, project: str | None = None,
               branch: str | None = None, brief: str | None = None, base: str | None = None,
               tree: str | None = None, needs: list[str] | None = None) -> Run:
        check_slug(slug)
        if self.exists(slug):
            raise StateError("run-exists", f"{slug} already exists; a run is created once")
        run = Run.new(
            slug, steps=steps, project=project, branch=branch, brief=brief,
            base=base, tree=tree, needs=needs,
        )
        self.save(run)
        log.info("run %s created on %s", run.slug, run.branch)
        return run

    def save(self, run: Run) -> Run:
        """Validate what is about to be written, then write it whole."""
        data = run.to_dict()
        Run.from_dict(data)  # the shape is checked on the way out as well as in

        directory = self.paths.run_dir(run.slug)
        directory.mkdir(parents=True, exist_ok=True)
        keep_runs_out_of_git(self.paths.runs_dir)
        write_whole(directory / RUN_FILE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return run

    def update(self, slug: str, change: Callable[[Run], object]) -> Run:
        """Read, change through the program, write back."""
        run = self.load(slug)
        change(run)
        return self.save(run)

    # --- advancing, the verbs the driver uses -----------------------------

    def start_step(self, slug: str, provider: str | None = None) -> Run:
        return self.update(slug, lambda run: run.start_step(provider))

    def pass_step(self, slug: str) -> Run:
        return self.update(slug, lambda run: run.pass_step())

    def fail_step(self, slug: str, reason: str) -> Run:
        return self.update(slug, lambda run: run.fail_step(reason))

    def ask_step(self, slug: str, note: str) -> Run:
        """The step returned a question, and the driver is waiting for an answer."""
        return self.update(slug, lambda run: run.ask_step(note))

    def answered(self, slug: str, note: str) -> Run:
        """A person answered; the step is run again with what they said."""
        return self.update(slug, lambda run: run.answered(note))

    def refuse_step(self, slug: str, reason: str) -> Run:
        """One attempt was refused; the step waits for the next."""
        return self.update(slug, lambda run: run.refuse_step(reason))

    def continue_step(self, slug: str, note: str) -> Run:
        """The step ran out of room; what it did is kept and a new session carries on."""
        return self.update(slug, lambda run: run.continue_step(note))

    def fail_run(self, slug: str, reason: str) -> Run:
        return self.update(slug, lambda run: run.fail(reason))

    def halt(self, slug: str, reason: str) -> Run:
        """A step passed and said the run must not go on."""
        return self.update(slug, lambda run: run.halt(reason))

    def stop(self, slug: str, reason: str) -> Run:
        return self.update(slug, lambda run: run.stop(reason))

    def reopen(self, slug: str) -> Run:
        """A stopped run goes on from the step it stopped on."""
        return self.update(slug, lambda run: run.reopen())


def keep_runs_out_of_git(runs_dir: Path) -> None:
    """A run's state is not repository content, and the project should not have to say so.

    It covers `runs/` and not the whole of `.agent-kit/v3/`, because what the
    project *declares* about itself is repository content and belongs in the
    history beside the code. Writing this beside the state rather than into the
    project's own `.gitignore` leaves the project's files alone: removing the
    kit removes every trace of it.
    """
    ignore = runs_dir / ".gitignore"
    if ignore.exists():
        return
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_whole(ignore, "# The kit's own state. Not repository content — see docs/runs/ for what is.\n*\n")


def keep_sittings_out_of_git(sittings_dir: Path) -> None:
    """An hour of somebody's speech, verbatim, is not repository content either.

    The same shape as `runs/` and for a sharper reason: the room holds
    `telling.txt` — what the owner said, word for word — every answer they
    typed, and the raw text of every attempt. The kit ends a sitting by asking
    them to read the diff and commit it, so anything left uncovered here is a
    thing they will commit without meaning to.
    """
    ignore = sittings_dir / ".gitignore"
    if ignore.exists():
        return
    sittings_dir.mkdir(parents=True, exist_ok=True)
    write_whole(
        ignore,
        "# The kit's own paperwork for an hour with the owner: what they said, what they\n"
        "# answered, and what each attempt returned. Not repository content.\n*\n",
    )


def write_whole(path: Path, text: str) -> None:
    """Write beside, rename over: a writer that dies leaves the previous file whole."""
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


__all__ = ["RunStore", "Run", "Step", "RUN_FILE", "keep_runs_out_of_git", "write_whole"]
