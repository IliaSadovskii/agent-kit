"""S0 — the machine's paths. One home per kind of file, XDG or nothing."""

from pathlib import Path

from agent_kit.paths import Paths, project_paths


def test_defaults_follow_xdg(tmp_path):
    paths = Paths.from_env({"HOME": str(tmp_path)})

    assert paths.config_file == tmp_path / ".config/agent-kit/config.toml"
    assert paths.state_dir == tmp_path / ".local/state/agent-kit"
    assert paths.log_dir == paths.state_dir / "logs"
    assert paths.secrets_file == paths.state_dir / "secrets"


def test_xdg_variables_win(tmp_path):
    paths = Paths.from_env(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "cfg"),
            "XDG_STATE_HOME": str(tmp_path / "st"),
        }
    )

    assert paths.config_dir == tmp_path / "cfg/agent-kit"
    assert paths.state_dir == tmp_path / "st/agent-kit"


def test_ensure_creates_only_the_machine_directories(tmp_path):
    paths = Paths.from_env({"HOME": str(tmp_path)}).ensure()

    assert paths.config_dir.is_dir()
    assert paths.log_dir.is_dir()
    assert not paths.config_file.exists()  # a missing config is not an error


def test_the_third_version_owns_its_own_project_directory(tmp_path):
    """Open question 1: version 2 keeps .agent-kit/runs/, version 3 never touches it."""
    project = project_paths(tmp_path)

    assert project.kit_dir == tmp_path / ".agent-kit/v3"
    assert project.runs_dir == tmp_path / ".agent-kit/v3/runs"
    assert Path(".agent-kit/runs") not in [p.relative_to(tmp_path) for p in (project.kit_dir, project.runs_dir)]
