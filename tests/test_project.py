"""S4 — what a project declares about itself, and the command that writes it down.

`agent-kit init` reads what is already in the repository rather than asking. A
Makefile with a `test` target is the test command; what it cannot find it says
is missing instead of guessing.
"""

import subprocess

import pytest

from agent_kit.cli.main import main
from agent_kit.errors import ConfigError, ExitCode
from agent_kit.project import (
    DEFAULT_COMMAND_TIMEOUT,
    PROJECT_FILE,
    read_project,
    require_project,
)


def git(root, *argv):
    subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "kit@example.com")
    git(tmp_path, "config", "user.name", "kit")
    (tmp_path / "README.md").write_text("a project\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "first")
    return tmp_path


def declare(root, text):
    path = root / ".agent-kit/v3" / PROJECT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- reading what a project declares ---------------------------------------


def test_a_project_declares_its_commands_in_the_order_they_run(tmp_path):
    declare(
        tmp_path,
        '[project]\ndefault_branch = "trunk"\n\n[commands]\nlint = "make lint"\ntest = "make test"\n',
    )

    project = require_project(tmp_path)

    assert project.default_branch == "trunk"
    assert [(command.name, command.command) for command in project.commands] == [
        ("lint", "make lint"),
        ("test", "make test"),
    ]


def test_a_project_may_say_which_provider_runs_a_role_here(tmp_path):
    declare(tmp_path, '[commands]\ntest = "pytest"\n\n[roles.build]\nprovider = "fake"\n')

    assert require_project(tmp_path).roles["build"].provider == "fake"


def test_a_project_that_declared_nothing_is_not_guessed_at(tmp_path):
    assert read_project(tmp_path) is None

    with pytest.raises(ConfigError) as refused:
        require_project(tmp_path)
    assert refused.value.code == "no-project"


def test_a_setting_the_kit_does_not_read_is_refused(tmp_path):
    declare(tmp_path, '[project]\nnickname = "sandbox"\n')

    with pytest.raises(ConfigError) as refused:
        require_project(tmp_path)
    assert refused.value.code == "unknown-key"


def test_a_command_that_is_not_a_command_is_refused(tmp_path):
    declare(tmp_path, "[commands]\ntest = 7\n")

    with pytest.raises(ConfigError) as refused:
        require_project(tmp_path)
    assert refused.value.code == "bad-value"


# --- init reads the repository ---------------------------------------------


def test_init_finds_the_test_command_in_the_makefile(repo, capsys):
    (repo / "Makefile").write_text("test:\n\tpytest\n\nlint:\n\truff check .\n")

    code = main(["-C", str(repo), "init"])

    assert code == int(ExitCode.OK)
    project = require_project(repo)
    assert dict((c.name, c.command) for c in project.commands) == {
        "test": "make test",
        "lint": "make lint",
    }
    assert project.default_branch == "main"


def test_init_falls_back_to_pytest_when_there_is_no_makefile(repo):
    (repo / "pyproject.toml").write_text('[project]\nname = "p"\n\n[tool.pytest.ini_options]\n')

    assert main(["-C", str(repo), "init"]) == int(ExitCode.OK)
    assert [c.command for c in require_project(repo).commands] == ["pytest"]


def test_init_says_what_is_missing_rather_than_guessing(repo, capsys):
    code = main(["-C", str(repo), "init"])

    assert code == int(ExitCode.CONFIG)
    assert "test" in capsys.readouterr().err
    assert require_project(repo).commands == ()


def test_init_outside_a_repository_is_refused(tmp_path, capsys):
    code = main(["-C", str(tmp_path), "init"])

    assert code == int(ExitCode.CONFIG)
    assert "not-a-repository" in capsys.readouterr().err


def test_init_does_not_overwrite_what_somebody_edited(repo, capsys):
    (repo / "Makefile").write_text("test:\n\tpytest\n")
    main(["-C", str(repo), "init"])
    declare(repo, '[commands]\ntest = "make test-by-hand"\n')

    code = main(["-C", str(repo), "init"])

    assert code == int(ExitCode.CONFIG)
    assert "exists" in capsys.readouterr().err
    assert require_project(repo).commands[0].command == "make test-by-hand"


def test_init_writes_over_it_when_asked(repo):
    """`--force` fills the gaps. What is already declared was declared on purpose."""
    (repo / "Makefile").write_text("test:\n\tpytest\n\nlint:\n\truff check .\n")
    declare(repo, '[commands]\ntest = "make test-by-hand"\n')

    assert main(["-C", str(repo), "init", "--force"]) == int(ExitCode.OK)

    found = dict((c.name, c.command) for c in require_project(repo).commands)
    assert found["test"] == "make test-by-hand"  # the hand edit stands
    assert found["lint"] == "make lint"  # and the gap is filled


def test_what_init_writes_is_what_the_kit_reads_back(repo):
    (repo / "Makefile").write_text("test:\n\tpytest\n")

    main(["-C", str(repo), "init"])

    assert require_project(repo).source == repo / ".agent-kit/v3" / PROJECT_FILE


def test_what_a_project_declares_is_repository_content_and_its_runs_are_not(repo):
    from agent_kit.state import RunStore

    (repo / "Makefile").write_text("test:\n\tpytest\n")
    main(["-C", str(repo), "init"])
    RunStore(repo).create("add-vat", steps=["probe"])

    def ignored(relative):
        return subprocess.run(
            ["git", "check-ignore", "-q", relative], cwd=repo, capture_output=True
        ).returncode == 0

    assert not ignored(".agent-kit/v3/" + PROJECT_FILE)
    assert ignored(".agent-kit/v3/runs/add-vat/run.json")


# --- what the review found: init destroys what it cannot write --------------


def test_init_keeps_what_it_did_not_write(repo):
    (repo / "Makefile").write_text("test:\n\tpytest\n")
    declare(
        repo,
        '[commands]\ntest = "make test"\nsmoke = "make smoke"\n\n[roles.build]\nprovider = "codex"\n',
    )

    assert main(["-C", str(repo), "init", "--force"]) == int(ExitCode.OK)

    project = require_project(repo)
    assert dict((c.name, c.command) for c in project.commands)["smoke"] == "make smoke"
    assert project.roles["build"].provider == "codex"


def test_a_command_somebody_edited_by_hand_wins_over_what_init_found(repo):
    (repo / "Makefile").write_text("test:\n\tpytest\n")
    declare(repo, '[commands]\ntest = "make test-by-hand"\n')

    main(["-C", str(repo), "init", "--force"])

    assert require_project(repo).commands[0].command == "make test-by-hand"


def test_roles_survive_a_round_trip_through_the_file(repo):
    declare(repo, '[commands]\ntest = "pytest"\n\n[roles.design]\nprovider = "fake"\nfallback = ["codex"]\n')
    (repo / "Makefile").write_text("test:\n\tpytest\n")

    main(["-C", str(repo), "init", "--force"])

    role = require_project(repo).roles["design"]
    assert role.provider == "fake"
    assert role.fallback == ["codex"]


def test_a_project_from_an_older_kit_stops_hiding_its_own_declaration(repo):
    """S0-S3 wrote the ignore one directory up, where it covers project.toml too."""
    old = repo / ".agent-kit/v3/.gitignore"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text("# The kit's own state.\n*\n")
    (repo / "Makefile").write_text("test:\n\tpytest\n")

    main(["-C", str(repo), "init"])

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".agent-kit/v3/" + PROJECT_FILE], cwd=repo, capture_output=True
    ).returncode == 0
    assert not ignored
    assert not old.exists()


# --- how long the project will wait for its own commands --------------------


def test_a_project_says_how_long_it_waits_for_its_own_commands(tmp_path):
    declare(tmp_path, '[project]\ncommand_timeout = 30\n\n[commands]\ntest = "true"\n')

    assert read_project(tmp_path).command_timeout == 30


def test_a_project_that_says_nothing_waits_the_hour_a_suite_is_allowed(tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')

    assert read_project(tmp_path).command_timeout == DEFAULT_COMMAND_TIMEOUT


def test_a_waiting_time_that_is_not_a_number_of_seconds_is_refused_by_name(tmp_path):
    declare(tmp_path, '[project]\ncommand_timeout = "soon"\n\n[commands]\ntest = "true"\n')

    with pytest.raises(ConfigError) as caught:
        read_project(tmp_path)

    assert caught.value.code == "bad-value"
    assert "command_timeout" in caught.value.detail


def test_what_the_project_declared_survives_being_written_out_again(repo):
    declare(repo, '[project]\ndefault_branch = "main"\ncommand_timeout = 45\n\n[commands]\ntest = "make test"\n')

    main(["-C", str(repo), "init", "--force"])

    assert read_project(repo).command_timeout == 45
