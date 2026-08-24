"""The suite never touches the home of whoever runs it.

`main()` reads the real environment and `setup_logging` writes a file under
`~/.local/state`. One test that forgets to redirect HOME would write there, so
no test is trusted to remember.
"""

import pytest


@pytest.fixture(autouse=True)
def machine_home(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    return home


def reset_at(hours: int = 3) -> str:
    """An hour a provider might really print, and one that is still ahead of this run.

    It used to be a fixed hour on the day it was written — `2026-08-24T17:00:00+00:00` —
    and the suite went red every day after that hour, because a limit whose time has
    passed is swept, correctly, by the sweep the test was measuring. What these cases
    are about is the *shape*: a time with a zone, which is what a CLI says, rather than
    the `2027-01-01` that no provider will ever print.
    """
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=hours)).isoformat()
