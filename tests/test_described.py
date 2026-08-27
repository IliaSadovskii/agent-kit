"""Missing is not the same as fine, and only one of them can be said out loud.

The second version answered zero, quietly, on a project with no knowledge. The
third inverted the same mistake: `design`'s contract is *stricter* for a project
that keeps knowledge, so the kit asked least of the project it knew least about.

The answer is that the declaration is the truth. `knowledge = "docs/knowledge"`
says a project is described there; `knowledge = ""` says it is not being
described, and a person typed that. Nothing is sniffed off a directory.
"""

from __future__ import annotations

import pytest

from agent_kit.errors import ConfigError, ExitCode
from agent_kit.knowledge import Knowledge
from agent_kit.project import read_project, write_project


def declaring(tmp_path, knowledge: str | None):
    said = "" if knowledge is None else f'\nknowledge = "{knowledge}"'
    (tmp_path / ".agent-kit/v3").mkdir(parents=True)
    (tmp_path / ".agent-kit/v3/project.toml").write_text(
        f'[project]\ndefault_branch = "main"{said}\n\n[commands]\ntest = "sh check.sh"\n',
        encoding="utf-8",
    )
    return read_project(tmp_path)


def test_a_project_that_says_nothing_is_described_where_the_default_says(tmp_path):
    project = declaring(tmp_path, None)
    assert project.declares_knowledge
    assert project.knowledge_dir == tmp_path / "docs/knowledge"


def test_an_empty_value_is_a_state_and_not_a_path(tmp_path):
    project = declaring(tmp_path, "")
    assert not project.declares_knowledge
    assert project.knowledge_dir is None
    assert project.knowledge_in(tmp_path / "elsewhere") is None
    assert not project.keeps_knowledge


def test_an_empty_value_is_written_back_as_it_was_read(tmp_path):
    project = declaring(tmp_path, "")
    write_project(project, force=True)
    assert 'knowledge = ""' in (tmp_path / ".agent-kit/v3/project.toml").read_text(encoding="utf-8")
    assert not read_project(tmp_path).declares_knowledge


def test_init_writes_the_default_rather_than_saying_nothing_for_the_owner(tmp_path):
    """`knowledge = ""` is a person's word. Writing it for them is the silence again."""
    from agent_kit.project import discover

    project, _ = discover(tmp_path)
    assert project.knowledge == "docs/knowledge"


def test_a_directory_of_records_is_a_described_project(tmp_path):
    root = tmp_path / "docs/knowledge"
    root.mkdir(parents=True)
    (root / "entities.md").write_text("# Сущности\n\n### Деньги\n`key: money`\n", encoding="utf-8")
    assert Knowledge(root).described


def test_a_directory_with_no_records_is_not_a_described_project(tmp_path):
    root = tmp_path / "docs/knowledge"
    root.mkdir(parents=True)
    (root / "entities.md").write_text("# Сущности\n", encoding="utf-8")
    assert not Knowledge(root).described


def test_a_directory_that_is_not_there_is_not_a_described_project(tmp_path):
    assert not Knowledge(tmp_path / "nothing").described


# --- the refusal, where a run meets it --------------------------------------


def test_a_run_of_a_project_that_was_never_described_is_refused_by_name(described_run):
    run, refuse = described_run(knowledge="docs/knowledge", records=False)
    with pytest.raises(ConfigError) as refused:
        refuse()
    assert refused.value.code == "no-description"
    assert refused.value.exit_code == ExitCode.CONFIG
    # Three doors, because a refusal that names no way out is a wall.
    assert "agent-kit init" in refused.value.hint
    assert "knowledge tell" in refused.value.hint
    assert 'knowledge = ""' in refused.value.hint


def test_a_project_that_says_it_is_not_described_is_not_refused(described_run):
    _, refuse = described_run(knowledge="", records=False)
    refuse()


def test_a_project_with_a_description_is_not_refused(described_run):
    _, refuse = described_run(knowledge="docs/knowledge", records=True)
    refuse()


def test_the_refusal_is_only_asked_of_a_run_that_has_the_step_that_reads_it(described_run):
    _, refuse = described_run(knowledge="docs/knowledge", records=False, steps=("probe",))
    refuse()


def test_a_project_that_declared_nothing_at_all_is_refused_by_the_same_code(described_run):
    """One code and three doors.

    A project that declared nothing and a project that declared a description it
    never wrote are the same state to a run about to be designed: nothing to
    design against. Two codes would make every caller tell them apart in order
    to do the same thing about both.
    """
    _, refuse = described_run(knowledge=None, records=False, declared=False)
    with pytest.raises(ConfigError) as refused:
        refuse()
    assert refused.value.code == "no-description"
    assert "agent-kit init" in refused.value.hint
    assert "knowledge tell" in refused.value.hint
    assert 'knowledge = ""' in refused.value.hint


def test_a_declaration_the_kit_cannot_read_is_refused_where_it_is_read(described_run, tmp_path):
    """The same choice its neighbour makes: the step that needs the field names it."""
    _, refuse = described_run(knowledge="docs/knowledge", records=True)
    (tmp_path / ".agent-kit/v3/project.toml").write_text("this is not toml [", encoding="utf-8")
    refuse()
