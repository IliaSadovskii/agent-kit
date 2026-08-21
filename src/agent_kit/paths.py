"""Where files live. Three places, one owner each — see the plan, "Where everything lives"."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

APP_NAME = "agent-kit"

#: The third version owns `.agent-kit/v3/` and never touches what version 2 wrote.
PROJECT_DIR = ".agent-kit"
PROJECT_KIT_DIR = "v3"


@dataclass(frozen=True)
class Paths:
    """The machine: what this installation chose, and what is true right now."""

    config_dir: Path
    state_dir: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Paths":
        env = os.environ if env is None else env
        home = Path(env.get("HOME") or Path.home())
        config_home = Path(env.get("XDG_CONFIG_HOME") or home / ".config")
        state_home = Path(env.get("XDG_STATE_HOME") or home / ".local/state")
        return cls(config_dir=config_home / APP_NAME, state_dir=state_home / APP_NAME)

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"

    @property
    def log_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def secrets_file(self) -> Path:
        return self.state_dir / "secrets"

    def ensure(self) -> "Paths":
        """Create the directories. A missing config file is not an error."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True)
class ProjectPaths:
    """The project: what this repository declares and what its runs left behind."""

    root: Path

    @property
    def kit_dir(self) -> Path:
        return self.root / PROJECT_DIR / PROJECT_KIT_DIR

    @property
    def runs_dir(self) -> Path:
        return self.kit_dir / "runs"

    def run_dir(self, slug: str) -> Path:
        return self.runs_dir / slug


def project_paths(root: Path | str) -> ProjectPaths:
    return ProjectPaths(Path(root))
