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

    def path_for(self, slug: str) -> Path:
        return self.paths.run_dir(check_slug(slug)) / RUN_FILE

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
               branch: str | None = None) -> Run:
        check_slug(slug)
        if self.exists(slug):
            raise StateError("run-exists", f"{slug} already exists; a run is created once")
        run = Run.new(slug, steps=steps, project=project, branch=branch)
        self.save(run)
        log.info("run %s created on %s", run.slug, run.branch)
        return run

    def save(self, run: Run) -> Run:
        """Validate what is about to be written, then write it whole."""
        data = run.to_dict()
        Run.from_dict(data)  # the shape is checked on the way out as well as in

        directory = self.paths.run_dir(run.slug)
        directory.mkdir(parents=True, exist_ok=True)
        _write_whole(directory / RUN_FILE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
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

    def skip_step(self, slug: str, reason: str) -> Run:
        return self.update(slug, lambda run: run.skip_step(reason))

    def stop(self, slug: str, reason: str) -> Run:
        return self.update(slug, lambda run: run.stop(reason))


def _write_whole(path: Path, text: str) -> None:
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


__all__ = ["RunStore", "Run", "Step", "RUN_FILE"]
