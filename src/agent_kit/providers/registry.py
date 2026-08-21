"""Which providers exist. The registry reads the folder; nobody keeps a list.

Adding a provider at level A is a `provider.toml` alone. Promoting it to level B
adds an `adapter.py` beside it. Neither touches any file outside this package.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from ..errors import ProviderError
from .base import Executor

PROVIDERS_DIR = Path(__file__).resolve().parent
DECLARATION = "provider.toml"


@dataclass(frozen=True)
class ProviderFacts:
    """What is true about a tool, declared by the kit — never a choice of this machine."""

    name: str
    title: str
    level: str
    real: bool
    binary: str | None = None
    notes: str = ""


def provider_names() -> list[str]:
    return sorted(
        entry.name
        for entry in PROVIDERS_DIR.iterdir()
        if entry.is_dir() and (entry / DECLARATION).is_file()
    )


def facts(name: str) -> ProviderFacts:
    path = PROVIDERS_DIR / name / DECLARATION
    if not path.is_file():
        raise ProviderError(
            "unknown-provider",
            f"{name!r} is not a provider this kit ships: {', '.join(provider_names())}",
        )
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as error:
        raise ProviderError("bad-declaration", f"{path} cannot be read: {error}") from error

    declared: Any = document.get("provider")
    if not isinstance(declared, dict):
        raise ProviderError(
            "bad-declaration",
            f"{path} has no [provider] table; silence must not read as a real level A agent",
        )
    return ProviderFacts(
        name=name,
        title=declared.get("title", name),
        level=declared.get("level", "A"),
        real=bool(declared.get("real", True)),
        binary=declared.get("binary"),
        notes=declared.get("notes", ""),
    )


def all_facts() -> list[ProviderFacts]:
    return [facts(name) for name in provider_names()]


def build_executor(name: str, options: dict[str, list[str]] | None = None) -> Executor:
    """Ask a provider's own module for an executor. Only it knows how to make one."""
    declared = facts(name)
    try:
        module = import_module(f"{__package__}.{declared.name}.adapter")
    except ModuleNotFoundError as error:
        raise ProviderError(
            "no-adapter", f"{name} declares itself but ships no executor: {error}"
        ) from error

    factory = getattr(module, "build_executor", None)
    if factory is None:
        raise ProviderError("no-adapter", f"{name} ships no build_executor()")
    return factory(options or {})
