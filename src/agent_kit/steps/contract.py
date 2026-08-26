"""What a step must return, and what refusing it looks like.

A contract is declared, not written by hand at each step: the driver renders it
into the step's input, and checks what comes back against the same declaration.
One description, two readers — the agent and the program.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence

from ..errors import ExitCode, KitError

_FENCE = re.compile(r"```(?:json)?[ \t]*\n?(.*?)```", re.DOTALL)


class ContractRefusal(KitError):
    """The output does not satisfy the contract, and this says exactly where."""

    exit_code = ExitCode.STATE


@dataclass(frozen=True)
class Field:
    name: str
    required: bool = True
    help: str = ""
    #: Required exactly when this sibling of the same record is true. Set by
    #: `Contract.requiring`, never by hand at a step: it is what a *project*
    #: makes of a field, and the kit ships no project.
    required_when: str = ""
    #: Whether nothing is a thing this field can say. For most lists it is: an
    #: empty `assumptions` is a step that considered the question and had
    #: nothing, and that is not a step which did not answer — the second
    #: version could not tell the two apart and 14% of its assumptions were
    #: neither. For a few it is not: a design that will prove nothing has not
    #: decided what will prove it, and a build that wrote no file did not
    #: build. Which of the two a field is belongs to the field, so that no
    #: program has to carry a list of names.
    empty_is_an_answer: bool = True

    kind = "value"

    def needed(self, beside: dict[str, Any]) -> bool:
        return bool(beside.get(self.required_when)) if self.required_when else self.required

    def answered(self, value: Any) -> bool:
        """Whether what came back says anything.

        Everything says something unless it is empty and empty is no answer.
        A `Text` is already refused when it is blank, so in practice this is
        about the lists.
        """
        return self.empty_is_an_answer or bool(value)

    def _need(self) -> str:
        if self.required_when:
            return f"required when `{self.required_when}`"
        if not self.empty_is_an_answer:
            return "required, and an empty one is not an answer"
        return "required" if self.required else "optional"

    def check(self, value: Any, where: str) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def describe(self) -> str:
        help_text = f" — {self.help}" if self.help else ""
        return f"- `{self.name}` ({self.kind}, {self._need()}){help_text}"

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

    def __post_init__(self) -> None:
        if not self.choices:
            raise ContractRefusal("bad-contract", f"{self.name} is an enum that names no choices")

    def check(self, value: Any, where: str) -> str:
        if value not in self.choices:
            self._refuse(where, f"{where} must be one of {', '.join(self.choices)}, not {value!r}")
        return value

    def describe(self) -> str:
        help_text = f" — {self.help}" if self.help else ""
        return f"- `{self.name}` (one of {', '.join(self.choices)}, {self._need()}){help_text}"


@dataclass(frozen=True)
class TextList(Field):
    kind = "list of text"

    def check(self, value: Any, where: str) -> list[str]:
        if not isinstance(value, list):
            self._refuse(where, f"{where} must be a list of strings")
        item_field = Text(self.name, help=self.help)
        return [item_field.check(item, f"{where}[{index}]") for index, item in enumerate(value)]


@dataclass(frozen=True)
class Records(Field):
    shape: tuple[Field, ...] = ()

    kind = "list of records"

    def check(self, value: Any, where: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            self._refuse(where, f"{where} must be a list of records")
        return [_check_fields(self.shape, item, f"{where}[{index}]") for index, item in enumerate(value)]

    def describe(self) -> str:
        help_text = f" — {self.help}" if self.help else ""
        inner = "\n".join("  " + field.describe() for field in self.shape)
        return f"- `{self.name}` (list of records, {self._need()}){help_text}\n{inner}"


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

    def requiring(self, path: str, when: str = "") -> "Contract":
        """A stricter copy of this contract, because a project asked for one.

        The join S6 exists for — an expensive assumption owes a block — binds a
        project that keeps knowledge and not one that keeps none. So the
        requirement cannot live in the definition: the driver asks for the copy
        the project imposes, and renders that same copy into the step's input.
        One description, two readers, still.
        """
        head, _, inner = path.partition(".")
        fields = list(self.fields)
        for index, field in enumerate(fields):
            if field.name != head:
                continue
            if not inner:
                fields[index] = replace(field, required=True, required_when=when)
                return Contract(fields=tuple(fields))
            if not isinstance(field, Records):
                raise ContractRefusal("bad-contract", f"{head} is not a list of records, so {path} names nothing")
            shape = list(field.shape)
            for at, inside in enumerate(shape):
                if inside.name == inner:
                    shape[at] = replace(inside, required=True, required_when=when)
                    fields[index] = replace(field, shape=tuple(shape))
                    return Contract(fields=tuple(fields))
            raise ContractRefusal("bad-contract", f"{path} names no field of this contract")
        raise ContractRefusal("bad-contract", f"{path} names no field of this contract")

    def merge(self, parts: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """One output from the several a split step produced.

        The contract is the only thing that knows what a field means, so it is
        what decides: a list accumulates across the sessions, because each of
        them answered only for its own part, and anything else is the last
        session's answer, because that is the one that finished.

        Without this, a build that took two sessions hands the reviewer and the
        pull request whatever the second one happened to mention.
        """
        if not parts:
            return {}
        merged = dict(parts[-1])
        for field in self.fields:
            if not isinstance(field, (TextList, Records)):
                continue
            gathered: list[Any] = []
            for part in parts:
                for item in part.get(field.name) or []:
                    if item not in gathered:
                        gathered.append(item)
            merged[field.name] = gathered or None
        return merged


def _check_fields(fields: Sequence[Field], data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        code = "output-not-a-table" if where == "output" else f"output-bad-field: {where}"
        raise ContractRefusal(code, f"{where} must be a table of the fields the contract names")

    checked: dict[str, Any] = {}
    for field in fields:
        name = field.name
        at = name if where == "output" else f"{where}.{name}"
        if data.get(name) is None:
            if field.needed(data):
                raise ContractRefusal(f"output-missing-field: {at}", "the contract requires it and it was not returned")
            checked[name] = None
            continue
        checked[name] = field.check(data[name], at)
        if not field.answered(checked[name]):
            raise ContractRefusal(
                f"output-empty-field: {at}",
                "the contract requires it and what came back answers nothing",
            )
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
