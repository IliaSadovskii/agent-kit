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

#: Сколько драйвер ждёт, прежде чем попробовать отказавший шаг ещё раз, и
#: число удваивается с каждым отказом: 30 секунд, потом 60, потом 120. Провайдер,
#: которого на минуту завалило, отвечает ровно так же и через секунду, а цепь без
#: паузы тратит все свои попытки за то время, за которое стартуют три сессии.
#: Потолка у удвоения нет и не нужно: попыток три на провайдера, и они его и держат.
DEFAULT_BACKOFF = 30

#: Where the daemon's page answers. Loopback, because the server's own proxy is
#: what puts it in the tailnet, and the tailnet is the only way in from outside.
#: Port 8080 is this project's block in the machine's registry.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

#: How long a question waits against a person's phone before the default is
#: taken. Twenty minutes: the second version measured it and it worked. It is
#: not `machine.wait`, which is how long a run waits for the machine — the two
#: answer the same question about different things, and the table says which.
DEFAULT_ANSWER_WAIT = 20 * 60

_MACHINE_KEYS = {"max_sessions", "wait", "backoff", "provider"}
_DAEMON_KEYS = {"host", "port"}
_PROVIDER_KEYS = {"enabled", "model", "effort", "max_sessions", "account"}
_ROLE_KEYS = {"provider", "fallback", "model", "effort"}
_OWNER_KEYS = {"channel", "chat", "wait", "file"}
_TOP_KEYS = {"machine", "daemon", "owner", "providers", "roles"}


@dataclass(frozen=True)
class MachineConfig:
    max_sessions: int = DEFAULT_MAX_SESSIONS
    wait: int = DEFAULT_WAIT
    backoff: int = DEFAULT_BACKOFF
    #: Which provider runs a role the table does not name. Empty is a machine
    #: that names none, and then a step whose role is unlisted is refused by
    #: `no-provider` — which is what every machine did before this key.
    #:
    #: It is here rather than as nine `[roles.*]` blocks a program writes,
    #: because nine generated blocks go stale the day a step declares a tenth
    #: role: an old machine would then refuse in the middle of a night, for a
    #: role nobody knew to write down. Its reader is `default_provider` in
    #: `driver/session.py`, which until now only the command line could set.
    provider: str = ""


@dataclass(frozen=True)
class DaemonConfig:
    """Where the page answers. It holds no truth; the ledger does."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


@dataclass(frozen=True)
class OwnerConfig:
    """The person this machine works for, and how to reach them.

    No token: that is a secret and lives in `~/.local/state/agent-kit/secrets`.
    An empty `channel` is a machine with no channel at all, which is what every
    machine was before S7a and what every machine may stay — a question there
    takes its default at once and says so.
    """

    channel: str = ""
    chat: str = ""
    wait: int = DEFAULT_ANSWER_WAIT
    #: Where the file channel keeps its two files. Read by nothing else.
    file: str = ""


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
    owner: OwnerConfig = field(default_factory=OwnerConfig)
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
        owner=_owner(_table(raw.get("owner", {}), "owner")),
        providers=_providers(_table(raw.get("providers", {}), "providers")),
        roles=roles_from_table(_table(raw.get("roles", {}), "roles")),
        source=path,
    )


#: Где начинается и кончается блок, который правит команда. Всё остальное в
#: файле — чужое: комментарии человека, его отступы, его порядок строк.
_BLOCK = "[owner]"


def write_owner_block(path: Path | str, owner: "OwnerConfig") -> Path:
    """Переписать `[owner]` и не тронуть ни байта вокруг.

    План: *одна правда, три редактора* — команды, страница демона и текстовый
    редактор пишут в один файл. Значит команда, которая перечитала бы TOML и
    записала его заново, стёрла бы комментарии человека, а файл заведён именно
    для того, чтобы их держать. Поэтому правится ровно свой блок, текстом.
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    kept: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            inside = stripped == _BLOCK
        if not inside:
            kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()

    block = [_BLOCK, f'channel = "{owner.channel}"']
    if owner.chat:
        block.append(f'chat    = "{owner.chat}"')
    block.append(f"wait    = {owner.wait}")
    if owner.file:
        block.append(f'file    = "{owner.file}"')

    written = "\n".join(([*kept, ""] if kept else []) + block) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    from .state.store import write_whole

    write_whole(path, written)
    return path


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
        # And here it means try again at once, which is what every kit did
        # before this number existed.
        backoff=_whole(table.get("backoff", DEFAULT_BACKOFF), "machine.backoff"),
        provider=table.get("provider") and _str(table["provider"], "machine.provider") or "",
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


def _owner(table: dict[str, Any]) -> OwnerConfig:
    _refuse_unknown(table, _OWNER_KEYS, "owner.")
    return OwnerConfig(
        channel=table.get("channel") and _str(table["channel"], "owner.channel") or "",
        chat=table.get("chat") and _str(str(table["chat"]), "owner.chat") or "",
        # Zero is a real answer: take the default at once, and still say so.
        wait=_whole(table.get("wait", DEFAULT_ANSWER_WAIT), "owner.wait"),
        file=table.get("file") and _str(table["file"], "owner.file") or "",
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
