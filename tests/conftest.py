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
