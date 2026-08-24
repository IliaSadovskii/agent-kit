"""The machine's configuration: `~/.config/agent-kit/config.toml`.

It holds only what this installation *chose* — which account, which model, which
role, how many at once. What is *true about a tool* belongs to that provider's
own `provider.toml` in the kit, and is refused here.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError

DEFAULT_MAX_SESSIONS = 4

#: How long a run waits for a slot or for a limited account before it gives up
#: and says so. Longer than a limit's reset, shorter than a night.
DEFAULT_WAIT = 2 * 60 * 60

#: Where the daemon's page answers. Loopback, because the server's own proxy is
#: what puts it in the tailnet, and the tailnet is the only way in from outside.
#: Port 8080 is this project's block in the machine's registry.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

_MACHINE_KEYS = {"max_sessions", "wait"}
_DAEMON_KEYS = {"host", "port"}
_PROVIDER_KEYS = {"enabled", "model", "effort", "max_sessions", "account"}
_ROLE_KEYS = {"provider", "fallback", "model", "effort"}
_TOP_KEYS = {"machine", "daemon", "providers", "roles"}


@dataclass(frozen=True)
class MachineConfig:
    max_sessions: int = DEFAULT_MAX_SESSIONS
    wait: int = DEFAULT_WAIT


@dataclass(frozen=True)
class DaemonConfig:
    """Where the page answers. It holds no truth; the ledger does."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    enabled: bool = True
    model: str | None = None
    effort: str | None = None
    account: str | None = None
    max_sessions: int | None = None


@dataclass(frozen=True)
class RoleConfig:
    name: str
    provider: str
    fallback: list[str] = field(default_factory=list)
    model: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class Config:
    machine: MachineConfig = field(default_factory=MachineConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    roles: dict[str, RoleConfig] = field(default_factory=dict)
    source: Path | None = None


def load_config(path: Path | str) -> Config:
    """Read the file, or return the defaults if there is none."""
    path = Path(path)
    if not path.exists():
        return Config()

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError("unreadable-config", f"config.toml is not valid TOML: {error}") from error
    except OSError as error:
        raise ConfigError("unreadable-config", f"config.toml could not be read: {error}") from error

    _refuse_unknown(raw, _TOP_KEYS, "")
    return Config(
        machine=_machine(_table(raw.get("machine", {}), "machine")),
        daemon=_daemon(_table(raw.get("daemon", {}), "daemon")),
        providers=_providers(_table(raw.get("providers", {}), "providers")),
        roles=roles_from_table(_table(raw.get("roles", {}), "roles")),
        source=path,
    )


def _refuse_unknown(table: dict[str, Any], known: set[str], prefix: str) -> None:
    for key in table:
        if key not in known:
            where = f"{prefix}{key}"
            raise ConfigError("unknown-key", f"{where} is not a setting this kit reads")


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError("bad-value", f"{where} must be a table")
    return value


def _machine(table: dict[str, Any]) -> MachineConfig:
    _refuse_unknown(table, _MACHINE_KEYS, "machine.")
    return MachineConfig(
        max_sessions=_positive_int(table.get("max_sessions", DEFAULT_MAX_SESSIONS), "machine.max_sessions"),
        # Zero is a real answer: it means refuse rather than wait.
        wait=_whole(table.get("wait", DEFAULT_WAIT), "machine.wait"),
    )


def _whole(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConfigError("bad-value", f"{where} must be a whole number of seconds, 0 or more")
    return value


def _daemon(table: dict[str, Any]) -> DaemonConfig:
    _refuse_unknown(table, _DAEMON_KEYS, "daemon.")
    return DaemonConfig(
        host=_str(table.get("host", DEFAULT_HOST), "daemon.host"),
        port=_positive_int(table.get("port", DEFAULT_PORT), "daemon.port"),
    )


def _providers(table: dict[str, Any]) -> dict[str, ProviderConfig]:
    providers = {}
    for name, block in table.items():
        where = f"providers.{name}"
        block = _table(block, where)
        _refuse_unknown(block, _PROVIDER_KEYS, f"{where}.")
        providers[name] = ProviderConfig(
            name=name,
            enabled=_bool(block.get("enabled", True), f"{where}.enabled"),
            model=_optional_str(block.get("model"), f"{where}.model"),
            effort=_optional_str(block.get("effort"), f"{where}.effort"),
            account=_optional_str(block.get("account"), f"{where}.account"),
            max_sessions=None if "max_sessions" not in block else _positive_int(block["max_sessions"], f"{where}.max_sessions"),
        )
    return providers


def roles_from_table(table: dict[str, Any]) -> dict[str, RoleConfig]:
    """A role table, wherever it was declared: the machine's or the project's."""
    roles = {}
    for name, block in table.items():
        where = f"roles.{name}"
        block = _table(block, where)
        _refuse_unknown(block, _ROLE_KEYS, f"{where}.")
        if "provider" not in block:
            raise ConfigError("missing-key", f"{where}.provider is required: a role without a provider runs nowhere")
        roles[name] = RoleConfig(
            name=name,
            provider=_str(block["provider"], f"{where}.provider"),
            fallback=_str_list(block.get("fallback", []), f"{where}.fallback"),
            model=_optional_str(block.get("model"), f"{where}.model"),
            effort=_optional_str(block.get("effort"), f"{where}.effort"),
        )
    return roles


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError("bad-value", f"{where} must be a whole number of at least 1")
    return value


def _bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError("bad-value", f"{where} must be true or false")
    return value


def _str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("bad-value", f"{where} must be a non-empty string")
    return value


def _optional_str(value: Any, where: str) -> str | None:
    return None if value is None else _str(value, where)


def _str_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ConfigError("bad-value", f"{where} must be a list of provider names")
    return list(value)
