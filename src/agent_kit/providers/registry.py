"""Which providers exist. The registry reads the folder; nobody keeps a list.

Adding a provider at level A is a `provider.toml` alone. Promoting it to level B
adds an `adapter.py` beside it. Neither touches any file outside this package.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from ..errors import ProviderError
from .base import Executor
from .process import Declaration, build_from_declaration

PROVIDERS_DIR = Path(__file__).resolve().parent
DECLARATION = "provider.toml"


def provider_names() -> list[str]:
    return sorted(
        entry.name
        for entry in PROVIDERS_DIR.iterdir()
        if entry.is_dir() and (entry / DECLARATION).is_file()
    )


def facts(name: str) -> Declaration:
    path = PROVIDERS_DIR / name / DECLARATION
    if not path.is_file():
        raise ProviderError(
            "unknown-provider",
            f"{name!r} is not a provider this kit ships: {', '.join(provider_names())}",
        )
    return Declaration.read(name, path)


def all_facts() -> list[Declaration]:
    return [facts(name) for name in provider_names()]


def build_executor(name: str, options: dict[str, list[str]] | None = None) -> Executor:
    """A provider's own module makes its executor — or, at level A, its declaration does."""
    declared = facts(name)
    options = options or {}
    try:
        module = import_module(f"{__package__}.{declared.name}.adapter")
    except ModuleNotFoundError:
        # A folder with only a provider.toml is a level A provider, which is
        # what the plan says level A is. Nothing else is needed to run a CLI.
        return build_from_declaration(declared, options)

    factory = getattr(module, "build_executor", None)
    if factory is None:
        raise ProviderError("no-adapter", f"{name} ships an adapter with no build_executor()")
    return factory(options)
