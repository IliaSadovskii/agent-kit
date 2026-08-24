"""The step directory: where two sessions meet without ever talking.

    steps/<n>-<name>/
      attempt-<k>/input.md    exactly what the driver enclosed
      attempt-<k>/raw.txt     what came back, before anything judged it
      attempt-<k>/meta.json   provider, model, timing
      attempt-<k>/refusal.txt why it was not accepted, when it was not
      output.json             the output that satisfied the contract
      meta.json               which attempt produced it

The plan draws these flat, which is the one-attempt case. An attempt that was
refused has to stay readable without re-running the night, so each attempt keeps
its own directory and the accepted output sits at the top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..state.store import write_whole


@dataclass(frozen=True)
class StepWorkspace:
    root: Path
    index: int
    name: str

    @property
    def dir(self) -> Path:
        return self.root / "steps" / f"{self.index}-{self.name}"

    def attempt_dir(self, attempt: int) -> Path:
        return self.dir / f"attempt-{attempt}"

    def write_input(self, attempt: int, text: str) -> Path:
        return self._write(self.attempt_dir(attempt) / "input.md", text)

    def write_raw(self, attempt: int, text: str) -> Path:
        return self._write(self.attempt_dir(attempt) / "raw.txt", text)

    def write_meta(self, attempt: int, meta: dict) -> Path:
        return self._write(self.attempt_dir(attempt) / "meta.json", _json(meta))

    def write_refusal(self, attempt: int, reason: str) -> Path:
        return self._write(self.attempt_dir(attempt) / "refusal.txt", reason + "\n")

    def add_part(self, output: dict) -> Path:
        """A splittable step that stopped short. Every part is kept, not only the last."""
        parts = self.read_parts()
        parts.append(output)
        return self._write(self.dir / "parts.json", _json({"parts": parts}))

    def read_parts(self) -> list[dict]:
        held = _read(self.dir / "parts.json") or {}
        parts = held.get("parts")
        return [part for part in parts if isinstance(part, dict)] if isinstance(parts, list) else []

    def write_asks(self, rounds: int, settled: list[dict]) -> Path:
        """Что здесь спрашивали у владельца и чем кончился каждый вопрос.

        Рядом с `input.md` и `output.json`, потому что здесь кит так и передаёт
        работу: файл, который можно перечитать, сравнить и предъявить потом.

        Это запись, а не счётчик. Драйвер, поднявший шаг заново, читает отсюда
        и ответы, и уже взятые умолчания: ревью нашло, что раньше он брал
        только номер круга, и ответ владельца, переживший смерть драйвера,
        выбрасывался, а в знание уезжало «ответа не было».
        """
        return self._write(self.dir / "asks.json", _json({"rounds": rounds, "settled": settled}))

    def read_asks(self) -> dict:
        return _read(self.dir / "asks.json") or {}

    def accept(self, attempt: int, output: dict, meta: dict) -> Path:
        self._write(self.dir / "meta.json", _json({**meta, "attempt": attempt}))
        return self._write(self.dir / "output.json", _json(output))

    def read_meta(self) -> dict | None:
        return _read(self.dir / "meta.json")

    def read_output(self) -> dict | None:
        return _read(self.dir / "output.json")

    def _write(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, text)
        return path


def _read(path: Path) -> dict | None:
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return found if isinstance(found, dict) else None


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
