"""What a step must return, and what refusing it looks like.

A contract is declared, not written by hand at each step: the driver renders it
into the step's input, and checks what comes back against the same declaration.
One description, two readers — the agent and the program.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ..errors import ExitCode, KitError

_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


class ContractRefusal(KitError):
    """The output does not satisfy the contract, and this says exactly where."""

    exit_code = ExitCode.STATE


@dataclass(frozen=True)
class Field:
    name: str
    required: bool = True
    help: str = ""

    kind = "value"

    def check(self, value: Any, where: str) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def describe(self) -> str:
        need = "required" if self.required else "optional"
        help_text = f" — {self.help}" if self.help else ""
        return f"- `{self.name}` ({self.kind}, {need}){help_text}"

    def _refuse(self, where: str, detail: str) -> None:
        raise ContractRefusal(f"output-bad-field: {where}", detail)


@dataclass(frozen=True)
class Text(Field):
    kind = "text"

    def check(self, value: Any, where: str) -> str:
        if not isinstance(value, str) or not value.strip():
            self._refuse(where, f"{where} must be a non-empty string")
        return value.strip()


@dataclass(frozen=True)
class LongText(Text):
    kind = "text, several sentences"


@dataclass(frozen=True)
class Bool(Field):
    kind = "true or false"

    def check(self, value: Any, where: str) -> bool:
        if not isinstance(value, bool):
            self._refuse(where, f"{where} must be true or false, not {value!r}")
        return value


@dataclass(frozen=True)
class Int(Field):
    kind = "whole number"

    def check(self, value: Any, where: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            self._refuse(where, f"{where} must be a whole number, not {value!r}")
        return value


@dataclass(frozen=True)
class Enum(Field):
    choices: tuple[str, ...] = ()

    kind = "one of"

    def check(self, value: Any, where: str) -> str:
        if value not in self.choices:
            self._refuse(where, f"{where} must be one of {', '.join(self.choices)}, not {value!r}")
        return value

    def describe(self) -> str:
        need = "required" if self.required else "optional"
        help_text = f" — {self.help}" if self.help else ""
        return f"- `{self.name}` (one of {', '.join(self.choices)}, {need}){help_text}"


@dataclass(frozen=True)
class TextList(Field):
    kind = "list of text"

    def check(self, value: Any, where: str) -> list[str]:
        if not isinstance(value, list):
            self._refuse(where, f"{where} must be a list of strings")
        return [Text(self.name).check(item, f"{where}[{index}]") for index, item in enumerate(value)]


@dataclass(frozen=True)
class Records(Field):
    shape: tuple[Field, ...] = ()

    kind = "list of records"

    def check(self, value: Any, where: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            self._refuse(where, f"{where} must be a list of records")
        return [_check_fields(self.shape, item, f"{where}[{index}]") for index, item in enumerate(value)]

    def describe(self) -> str:
        need = "required" if self.required else "optional"
        help_text = f" — {self.help}" if self.help else ""
        inner = "\n".join("  " + field.describe() for field in self.shape)
        return f"- `{self.name}` (list of records, {need}){help_text}\n{inner}"


@dataclass(frozen=True)
class Contract:
    """The whole of what a step returns."""

    fields: tuple[Field, ...]

    def check(self, data: Any) -> dict[str, Any]:
        return _check_fields(self.fields, data, "output")

    def describe(self) -> str:
        return "\n".join(field.describe() for field in self.fields)

    def field(self, name: str) -> Field | None:
        return next((field for field in self.fields if field.name == name), None)


def _check_fields(fields: Sequence[Field], data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        code = "output-not-a-table" if where == "output" else f"output-bad-field: {where}"
        raise ContractRefusal(code, f"{where} must be a table of the fields the contract names")

    checked: dict[str, Any] = {}
    for field in fields:
        name = field.name
        at = name if where == "output" else f"{where}.{name}"
        if data.get(name) is None:
            if field.required:
                raise ContractRefusal(f"output-missing-field: {at}", "the contract requires it and it was not returned")
            checked[name] = None
            continue
        checked[name] = field.check(data[name], at)
    return checked  # what the contract did not ask for is dropped, not refused


def parse_output(raw: str) -> Any:
    """Find the output in what an agent said.

    Agents think out loud, so the last fenced block wins; bare JSON is accepted
    for the providers that answer with nothing else.
    """
    if not raw or not raw.strip():
        raise ContractRefusal("output-missing", "the session returned nothing at all")

    blocks = [block.strip() for block in _FENCE.findall(raw)]
    candidates: Iterable[str] = reversed(blocks) if blocks else [raw.strip()]

    last_error = ""
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = str(error)

    raise ContractRefusal(
        "output-not-json",
        f"no JSON output was found in what the session returned ({last_error or 'no fenced block'})",
    )
