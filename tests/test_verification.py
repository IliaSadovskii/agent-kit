"""S8e — the catalogue of kinds of verification, and what a project answers.

Two levels, one catalogue. This file is the project's level: what the kit knows
about, what a project may say about each kind, and the three ways an answer is
refused. The feature's level — what a design owes and what verify walks — is in
`test_proving.py`.
"""

import pytest

from agent_kit.errors import ConfigError, ExitCode
from agent_kit.project import PROJECT_FILE, read_project, require_project
from agent_kit.verification import (
    CATALOGUE,
    commands_that_prove_nothing,
    kind_named,
    owed_by_a_feature,
    refuse_commands_that_prove_nothing,
    unanswered,
)


def declare(root, text):
    path = root / ".agent-kit/v3" / PROJECT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- the catalogue, which lives in the kit and nowhere else -----------------


def test_every_kind_says_what_defect_it_catches_and_never_a_tool():
    assert CATALOGUE
    for kind in CATALOGUE:
        assert kind.catches.strip(), f"{kind.name} does not say what it catches"


def test_one_kind_may_never_be_excused_and_the_others_may():
    never = [kind.name for kind in CATALOGUE if kind.never_skippable]
    assert never == ["suite"]


def test_a_kind_the_catalogue_does_not_hold_is_nobody():
    assert kind_named("suite").name == "suite"
    assert kind_named("mutation") is None


# --- what a project answers -------------------------------------------------


def test_a_project_answers_a_kind_with_a_command(tmp_path):
    declare(
        tmp_path,
        '[commands]\ntest = "sh check.sh"\n\n[verification.suite]\ncommand = "sh check.sh"\n',
    )

    project = require_project(tmp_path)

    answer = project.answer_for("suite")
    assert answer.command == "sh check.sh"
    assert answer.why == ""


def test_a_project_answers_a_kind_with_a_dated_refusal(tmp_path):
    declare(
        tmp_path,
        '[verification.types]\nwhy = "nothing here is typed"\nsince = "2026-08-28"\n',
    )

    answer = require_project(tmp_path).answer_for("types")

    assert answer.why == "nothing here is typed"
    assert answer.since == "2026-08-28"


def test_a_project_that_answered_nothing_is_the_project_every_older_kit_wrote(tmp_path):
    declare(tmp_path, '[commands]\ntest = "sh check.sh"\n')

    project = require_project(tmp_path)

    assert project.verification == ()
    assert owed_by_a_feature(project) == ()
    assert [kind.name for kind in unanswered(project)] == [kind.name for kind in CATALOGUE]


def test_a_bare_word_is_not_an_answer(tmp_path):
    declare(tmp_path, '[verification.types]\nwhy = ""\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-verification-answer: types"
    assert refused.value.exit_code == ExitCode.CONFIG


def test_a_refusal_with_no_date_is_not_an_answer(tmp_path):
    declare(tmp_path, '[verification.types]\nwhy = "nothing here is typed"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-verification-answer: types"


def test_a_date_that_is_not_a_date_is_not_an_answer(tmp_path):
    declare(tmp_path, '[verification.types]\nwhy = "none"\nsince = "last tuesday"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-verification-answer: types"


def test_a_kind_answered_both_ways_is_not_a_decision(tmp_path):
    declare(
        tmp_path,
        '[verification.types]\ncommand = "sh check.sh"\nwhy = "none"\nsince = "2026-08-28"\n',
    )

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "bad-verification-answer: types"


def test_a_kind_the_kit_does_not_know_is_refused_rather_than_invented(tmp_path):
    declare(tmp_path, '[verification.mutation]\ncommand = "sh check.sh"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "unknown-kind"


def test_a_field_the_kit_does_not_read_about_an_answer_is_refused(tmp_path):
    declare(tmp_path, '[verification.suite]\ncommand = "sh check.sh"\nurgency = "high"\n')

    with pytest.raises(ConfigError) as refused:
        read_project(tmp_path)

    assert refused.value.code == "unknown-key"


# --- a command is held to proving something ---------------------------------


@pytest.mark.parametrize("word", ["true", ":", "yes", "echo ok", "printf x"])
def test_a_command_that_always_exits_zero_proves_nothing(tmp_path, word):
    declare(tmp_path, f'[verification.suite]\ncommand = "{word}"\n')
    project = require_project(tmp_path)

    assert [one.kind for one in commands_that_prove_nothing(project)] == ["suite"]

    with pytest.raises(ConfigError) as refused:
        refuse_commands_that_prove_nothing(project)

    assert refused.value.code == "command-that-proves-nothing"
    assert refused.value.exit_code == ExitCode.CONFIG


def test_the_same_word_in_the_projects_commands_is_still_allowed(tmp_path):
    # `[commands]` says what to run; `[verification]` says what proves a kind.
    # A project whose lint command is `:` declares a real thing, and the kit
    # has said so since S4.
    declare(tmp_path, '[commands]\nlint = ":"\ntest = "sh check.sh"\n')

    refuse_commands_that_prove_nothing(require_project(tmp_path))


def test_an_answer_this_machine_cannot_start_is_named_by_the_code_verify_uses(tmp_path):
    from agent_kit.project import refuse_commands_that_start_nothing

    declare(tmp_path, '[verification.suite]\ncommand = "definitely-not-a-command --all"\n')

    with pytest.raises(ConfigError) as refused:
        refuse_commands_that_start_nothing(require_project(tmp_path))

    assert refused.value.code == "no-such-command"


# --- what a feature of this project owes ------------------------------------


def test_a_kind_answered_with_a_command_is_owed_by_every_feature(tmp_path):
    declare(
        tmp_path,
        '[verification.suite]\ncommand = "sh check.sh"\n\n'
        '[verification.types]\nwhy = "nothing here is typed"\nsince = "2026-08-28"\n',
    )

    owed = owed_by_a_feature(require_project(tmp_path))

    assert [kind.name for kind in owed] == ["suite"]


def test_a_kind_the_project_refused_is_refused_for_every_feature_of_it(tmp_path):
    declare(
        tmp_path,
        '[verification.types]\nwhy = "nothing here is typed"\nsince = "2026-08-28"\n',
    )

    assert owed_by_a_feature(require_project(tmp_path)) == ()
    assert [kind.name for kind in unanswered(require_project(tmp_path))] == ["suite", "end-to-end"]


# --- it survives being written out ------------------------------------------


def test_what_a_project_answered_survives_being_written_out_again(tmp_path):
    from agent_kit.project import render

    declare(
        tmp_path,
        '[commands]\ntest = "sh check.sh"\n\n'
        '[verification.suite]\ncommand = "sh check.sh"\n\n'
        '[verification.types]\nwhy = "nothing here is typed"\nsince = "2026-08-28"\n',
    )
    project = require_project(tmp_path)

    (tmp_path / ".agent-kit/v3" / PROJECT_FILE).write_text(render(project), encoding="utf-8")

    again = require_project(tmp_path)
    assert again.verification == project.verification


def test_init_answers_the_suite_from_what_it_already_found(tmp_path):
    from agent_kit.project import discover

    (tmp_path / "Makefile").write_text("test:\n\techo hi\n")

    project, _ = discover(tmp_path)

    assert project.answer_for("suite").command == "make test"
