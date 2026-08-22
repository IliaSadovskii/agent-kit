"""What a provider actually earned, written down.

A level that is printed and thrown away is a claim again by morning. This is
the machine's memory of the last measurement — state, not settings: it says what
was true when somebody last looked, and it survives nothing but the machine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..logs import get_logger
from ..paths import Paths
from ..state.store import write_whole

FILE = "providers.json"

log = get_logger("providers.measured")


@dataclass(frozen=True)
class Measurement:
    provider: str
    level: str | None
    failed: str | None
    measured_at: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "failed": self.failed,
            "measured_at": self.measured_at,
            "detail": self.detail,
        }


def path(paths: Paths | None = None) -> Path:
    return (paths or Paths.from_env()).state_dir / FILE


def measured_levels(paths: Paths | None = None) -> dict[str, Measurement]:
    """What was measured, last time anybody measured. Empty is an honest answer."""
    try:
        stored = json.loads(path(paths).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(stored, dict):
        return {}

    remembered = {}
    for name, block in stored.items():
        if isinstance(block, dict) and isinstance(block.get("measured_at"), str):
            remembered[name] = Measurement(
                provider=name,
                level=block.get("level"),
                failed=block.get("failed"),
                measured_at=block["measured_at"],
                detail=block.get("detail", ""),
            )
    return remembered


def remember(provider: str, level: str | None, failed: str | None, detail: str = "",
             paths: Paths | None = None) -> Measurement:
    paths = paths or Paths.from_env()
    measurement = Measurement(
        provider=provider,
        level=level,
        failed=failed,
        measured_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        detail=detail,
    )
    stored = {name: found.as_dict() for name, found in measured_levels(paths).items()}
    stored[provider] = measurement.as_dict()

    target = path(paths)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_whole(target, json.dumps(stored, indent=2, ensure_ascii=False) + "\n")
    log.info("%s measured at level %s", provider, level or "none")
    return measurement
