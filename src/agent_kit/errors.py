"""Failures, and the exit code each one leaves behind.

Every code means one thing. A caller that reads the number knows what happened
without reading the message, which is what makes the kit scriptable.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    USAGE = 1  # the command was typed wrong
    CONFIG = 2  # the machine's configuration is missing something or is wrong
    STATE = 3  # a run's state refuses what was asked of it
    PROVIDER = 4  # an agent cannot be run right now: missing, unauthenticated, limited, or no slot
    CHANNEL = 8  # the owner cannot be reached: no channel, a bad token, a service that is down
    REFUSED = 5  # the method said no: a blocking finding, a red suite, an unfinished build
    BENCH = 6  # a mechanism the bench planted did not fire
    BROKEN_BENCH = 7  # the bench itself could not answer: a case, a world or a judge broke
    INTERRUPTED = 130  # the operator stopped it
    INTERNAL = 70  # a defect in the kit: it should have been one of the above


class KitError(Exception):
    """A failure with a named reason and one exit code."""

    exit_code = ExitCode.USAGE

    def __init__(self, code: str, detail: str = "", *, hint: str = "") -> None:
        self.code = code
        self.detail = detail
        self.hint = hint
        super().__init__(f"{code}: {detail}" if detail else code)


class UsageError(KitError):
    exit_code = ExitCode.USAGE


class ConfigError(KitError):
    exit_code = ExitCode.CONFIG


class StateError(KitError):
    exit_code = ExitCode.STATE


class ProviderError(KitError):
    exit_code = ExitCode.PROVIDER


class ChannelError(KitError):
    """Владельца не дозваться.

    Свой код, потому что 4 означает «агента сейчас не запустить», а это другое
    событие с другим ответом: ночь при нём идёт дальше и берёт умолчания. Код,
    означающий две вещи, — это то, что план измерил как неавтоматизируемое.

    У ночи, у часа с владельцем и у входа на новую машину этот код значит одно
    событие и три развилки, и все три надо знать. **Ночью** он не останавливает ничего: умолчание берётся,
    прогон идёт дальше, а в записи стоит, до какой ступени дошли. **В сеансе**
    (`agent-kit knowledge tell`) он означает «не написано ничего»: у вопроса
    там нет умолчания, потому что весь смысл часа в том, что человек стоит
    рядом, — а половина описания хуже, чем ненаписанное. Рассказ при этом
    сохранён, и отказ называет, где он лежит. **В ходе** (`agent-kit setup`)
    он значит то же самое и по той же причине: ход печатает команду и ждёт
    строку от того, кто стоит рядом, умолчания у этого вопроса нет, и в
    `config.toml` не записано ничего. Машина, про которую записали провайдера,
    потому что никто не ответил, — это машина, которая думает, что у неё есть
    агент.
    """

    exit_code = ExitCode.CHANNEL
