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
    write_project,
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


# --- S6: where this project keeps its knowledge -----------------------------


def test_a_project_keeps_its_knowledge_where_the_second_version_left_it(tmp_path):
    declare(tmp_path, '[project]\ndefault_branch = "main"\n')

    assert read_project(tmp_path).knowledge == "docs/knowledge"


def test_a_project_may_say_otherwise(tmp_path):
    declare(tmp_path, '[project]\nknowledge = "docs/база"\n')

    assert read_project(tmp_path).knowledge == "docs/база"


def test_what_it_declared_survives_being_written_out(tmp_path):
    declare(tmp_path, '[project]\nknowledge = "docs/база"\n')
    project = read_project(tmp_path)

    write_project(project, force=True)

    assert read_project(tmp_path).knowledge == "docs/база"


def test_a_knowledge_directory_that_leaves_the_project_is_refused_by_name(tmp_path):
    declare(tmp_path, '[project]\nknowledge = "../shared"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-field: project.knowledge"


def test_an_absolute_knowledge_directory_is_refused_by_name(tmp_path):
    declare(tmp_path, '[project]\nknowledge = "/etc"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-field: project.knowledge"


# --- and the pre-push hook, which is where a project becomes known ----------


def test_init_writes_the_pre_push_hook(repo):
    from agent_kit.hook import hooks_dir

    main(["-C", str(repo), "init"])

    hook = hooks_dir(repo) / "pre-push"
    assert hook.is_file()
    assert hook.stat().st_mode & 0o111


def test_init_writes_the_hook_against_the_branch_the_project_declared(repo):
    from agent_kit.hook import hooks_dir

    git(repo, "checkout", "-b", "trunk")
    declare(repo, '[project]\ndefault_branch = "trunk"\n\n[commands]\ntest = "pytest"\n')

    main(["-C", str(repo), "init", "--force"])

    assert "trunk" in (hooks_dir(repo) / "pre-push").read_text()


def test_init_says_what_it_found_rather_than_overwriting_a_hook(repo, capsys):
    from agent_kit.hook import hooks_dir

    theirs = hooks_dir(repo) / "pre-push"
    theirs.write_text("#!/bin/sh\nexit 0\n")

    main(["-C", str(repo), "init"])

    assert theirs.read_text() == "#!/bin/sh\nexit 0\n"
    said = capsys.readouterr()
    assert "pre-push" in said.out + said.err


# --- a declared command that starts nothing ---------------------------------
#
# `test = "make test"` in a repository with no make passes init, passes design,
# passes build, and fails at verify — after two sessions have been paid for, and
# again every night until somebody edits the file. The first word of a command
# is the cheapest thing there is to ask about.


def test_a_command_whose_first_word_is_on_no_path_is_named(tmp_path):
    from agent_kit.project import commands_that_start_nothing

    declare(tmp_path, '[commands]\ntest = "definitely-not-here --all"\nlint = "true"\n')

    lost = commands_that_start_nothing(read_project(tmp_path))

    assert [command.name for command in lost] == ["test"]


def test_a_command_the_machine_can_start_is_not_named(tmp_path):
    from agent_kit.project import commands_that_start_nothing

    declare(tmp_path, '[commands]\ntest = "sh -c \'exit 0\'"\n')

    assert commands_that_start_nothing(read_project(tmp_path)) == []


def test_a_shell_builtin_is_not_a_command_to_look_for(tmp_path):
    """`cd`, `:` and `echo` are the shell's own, and `which` finds none of them."""
    from agent_kit.project import commands_that_start_nothing

    declare(tmp_path, '[commands]\nlint = ":"\ntest = "cd . && echo done"\n')

    assert commands_that_start_nothing(read_project(tmp_path)) == []


def test_a_command_given_as_a_path_is_looked_for_where_it_says(tmp_path):
    from agent_kit.project import commands_that_start_nothing

    script = tmp_path / "check.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    declare(tmp_path, f'[commands]\ntest = "{script}"\nlint = "{tmp_path}/nowhere.sh"\n')

    assert [command.name for command in commands_that_start_nothing(read_project(tmp_path))] == ["lint"]


def test_a_line_the_kit_cannot_read_as_a_command_is_left_alone(tmp_path):
    """A variable, a subshell, an assignment: the shell decides, and this does not guess."""
    from agent_kit.project import commands_that_start_nothing

    declare(tmp_path, '[commands]\ntest = "MODE=ci make test"\nlint = "$LINTER --all"\n')

    assert commands_that_start_nothing(read_project(tmp_path)) == []


def test_the_refusal_names_the_command_and_the_word(tmp_path):
    from agent_kit.project import refuse_commands_that_start_nothing

    declare(tmp_path, '[commands]\ntest = "definitely-not-here --all"\n')

    with pytest.raises(ConfigError) as refused:
        refuse_commands_that_start_nothing(read_project(tmp_path))

    assert refused.value.code == "no-such-command"
    assert "test" in refused.value.detail
    assert "definitely-not-here" in refused.value.detail
    assert refused.value.exit_code == ExitCode.CONFIG


def test_the_door_says_which_declared_command_starts_nothing(tmp_path, capsys, machine_home, monkeypatch):
    """What `doctor` used to answer about a project, asked where a project is now read.

    The question has not moved: it is still *what would `verify` be refused
    for*, printed before a night rather than after two sessions. Only the
    screen it is printed on has, because `doctor` answers about this machine
    and this is about a project.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    declare(tmp_path, '[commands]\ntest = "definitely-not-here --all"\n')

    main(["-C", str(tmp_path), "next"])

    out = capsys.readouterr().out
    assert "no-such-command" in out
    assert "definitely-not-here" in out
    assert "test" in out
