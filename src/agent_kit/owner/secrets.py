"""The kit's first secret, in the file the plan gave it.

`~/.local/state/agent-kit/secrets`, mode 600, never in git. It is not
`config.toml`: that file states what this machine *chose*, and the plan's
sentence about it — *safe to commit and safe to show* — has to stay true.

TOML, because the kit already reads TOML and a person may open this one too.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from ..errors import ConfigError

TELEGRAM_TOKEN = "telegram_token"


def read_secret(path: Path | str, name: str) -> str:
    """One secret, or nothing. A file that is not there is not an error."""
    return str(_all(Path(path)).get(name) or "")


def write_secret(path: Path | str, name: str, value: str) -> Path:
    """Write it where only its owner can read it, keeping whatever was there."""
    path = Path(path)
    held = _all(path)
    held[name] = value

    path.parent.mkdir(parents=True, exist_ok=True)
    # Created 600 rather than created and then chmodded: between the two there
    # is a moment when the token is readable by the machine's other projects.
    handle = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        file.write("# The kit's secrets. Not configuration, and never in git.\n")
        for key, secret in sorted(held.items()):
            file.write(f'{key} = "{secret}"\n')
    os.chmod(path, 0o600)
    return path


def _all(path: Path) -> dict[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise ConfigError("unreadable-secrets", f"{path} could not be read: {error}") from error
    try:
        held = tomllib.loads(raw)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError("unreadable-secrets", f"{path} is not valid TOML: {error}") from error
    return {key: str(value) for key, value in held.items() if isinstance(value, (str, int))}
