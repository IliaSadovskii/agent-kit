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
    PROVIDER = 4  # an agent CLI is missing, unauthenticated or limited
    REFUSED = 5  # the method said no: a blocking finding, a red suite, an unfinished build
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
