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


@pytest.fixture
def described_run(tmp_path):
    """A run whose project declares what it does about a description.

    Returns the run and a callable that asks the driver's preflight the one
    question this fixture exists for, without spending a session on it.
    """
    from agent_kit.driver.runner import StepRunner, create_run
    from agent_kit.state import RunStore
    from agent_kit.steps import builtin_registry

    def make(knowledge=None, records=False, steps=("design", "verify"), declared=True):
        if declared:
            said = "" if knowledge is None else f'\nknowledge = "{knowledge}"'
            (tmp_path / ".agent-kit/v3").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".agent-kit/v3/project.toml").write_text(
                f'[project]\ndefault_branch = "main"{said}\n', encoding="utf-8"
            )
        if records:
            where = tmp_path / (knowledge or "docs/knowledge")
            where.mkdir(parents=True, exist_ok=True)
            (where / "entities.md").write_text("# Сущности\n\n### Деньги\n`key: money`\n", encoding="utf-8")

        store = RunStore(tmp_path)
        run = create_run(
            store, builtin_registry(), "add-vat", steps=list(steps),
            project=str(tmp_path), brief="a brief",
        )
        runner = StepRunner(
            store=store, registry=builtin_registry(), executors={}, default_provider="fake"
        )
        return run, lambda: runner._is_described_at_all(store.load("add-vat"))

    return make
