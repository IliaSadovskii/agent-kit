"""The executors that are not sessions.

Question 1 of the plan's four — *can this be a program instead?* — applied to
the method itself. Two steps of a feature answer yes:

- `verify` runs the project's declared commands, because an agent cannot lie
  about green tests it did not run;
- `deliver` composes the pull request from what was already recorded, because a
  body assembled from the facts cannot describe work that did not happen.

They are executors like any other: the driver hands over a `StepRequest` and is
given back raw text, which the step's contract then judges. Nothing here knows
what a provider is, and no provider knows these exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..errors import ProviderError
from ..providers.base import Executor

#: Name -> what builds it. The prefix is deliberate: a program appears in a
#: run's record where a provider's name would, and the two must not be confused.
PREFIX = "program:"

_BUILDERS: dict[str, Callable[[Path], Executor]] = {}


def program_names() -> list[str]:
    return sorted(_BUILDERS)


def is_program(name: str) -> bool:
    return name.startswith(PREFIX)


def build_program(name: str, root: Path | str) -> Executor:
    builder = _BUILDERS.get(name)
    if builder is None:
        raise ProviderError(
            "unknown-program",
            f"{name!r} is not a program this kit ships: {', '.join(program_names()) or 'none'}",
        )
    return builder(Path(root))


def _register() -> None:
    from .verify import Verify

    _BUILDERS[Verify.name] = Verify


_register()

__all__ = ["PREFIX", "build_program", "is_program", "program_names"]
