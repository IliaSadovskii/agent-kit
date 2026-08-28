"""Ручные действия: то, чего автономная ночь сделать не может.

S8g. Файл лежит в репозитории, а не в бумагах прогона: строку кладёт вечер
партии, снимает её доказательство, которое возвращает ноль. Строка, у которой
доказательства быть не может, говорит это своими словами и не стоит на лестнице
двери — снять её может только человек.

Форма строки — реестра S8f: пункт списка с сегментами в бэктиках. Значение здесь
не выведенный ключ и не слаг, а шелл-команда и проза владельца, поэтому у записи
есть вопрос, которого у реестра нет: прочтётся ли обратно то, что записано.
"""

from __future__ import annotations

import pytest

from agent_kit.errors import ExitCode
from agent_kit.knowledge.format import read_items
from agent_kit.manual import (
    MANUAL,
    Manual,
    ManualError,
    ManualRefused,
    check,
    manual_key,
    read_actions,
    refuse_unless_each_action_is_answered,
    render_action,
)

REAL = """# Сделать руками

Что ночь сделать не может.

- положить STRIPE_KEY в окружение продакшена · `key: aaaaaa` · `proof: sh ops/key.sh`
- подтвердить домен кодом из SMS · `key: bbbbbb` · `by-hand: код приходит на телефон владельца`
"""


def manual(tmp_path, text=REAL):
    where = tmp_path / ".agent-kit/v3"
    where.mkdir(parents=True)
    if text is not None:
        (where / MANUAL).write_text(text, encoding="utf-8")
    return Manual(tmp_path)


# --- один парсер на два файла ------------------------------------------------


def test_the_peeling_is_one_function_and_stops_at_a_word_it_does_not_know():
    lines = ["- что-то · `key: aaaaaa` · `walked: 2026-08-27`", "- другое · `key: bbbbbb`"]
    held = read_items("some.md", lines, frozenset({"key"}))
    assert [one.said.get("key") for one in held] == [None, "bbbbbb"]
    # `walked:` не из этого словаря, обдирание встало на нём — и `key:` под ним
    # остался частью слов, ровно как это держит часть продукта вне реестра.
    assert "`key: aaaaaa`" in held[0].body


def test_the_peeling_does_not_read_what_a_fence_only_shows():
    lines = ["```", "- пример · `key: aaaaaa`", "```", "- настоящее · `key: bbbbbb`"]
    held = read_items("some.md", lines, frozenset({"key"}))
    assert [one.said["key"] for one in held] == ["bbbbbb"]


# --- чтение ------------------------------------------------------------------


def test_an_action_is_a_line_with_a_key_and_one_of_two_answers(tmp_path):
    held = manual(tmp_path).actions()
    assert [one.key for one in held] == ["aaaaaa", "bbbbbb"]
    assert held[0].what == "положить STRIPE_KEY в окружение продакшена"
    assert held[0].proof == "sh ops/key.sh"
    assert held[0].by_hand == ""
    assert held[1].by_hand == "код приходит на телефон владельца"
    assert held[1].proof == ""


def test_a_file_that_is_not_there_is_no_actions_and_no_refusal(tmp_path):
    assert manual(tmp_path, None).actions() == []


def test_two_lines_on_one_key_are_refused_rather_than_resolved_to_the_first(tmp_path):
    text = REAL + "- ещё одно · `key: aaaaaa` · `proof: sh ops/other.sh`\n"
    with pytest.raises(ManualError) as refused:
        manual(tmp_path, text).actions()
    assert refused.value.code == "two-actions-one-key"


def test_a_file_that_cannot_be_read_names_a_code(tmp_path):
    with pytest.raises(ManualError) as refused:
        manual(tmp_path, "```\n- открытая ограда · `key: aaaaaa`\n").actions()
    assert refused.value.code == "unreadable-manual"


# --- ключ --------------------------------------------------------------------


def test_the_key_is_derived_from_the_words_and_flattens_case_and_spacing():
    assert manual_key("Положить  STRIPE_KEY") == manual_key("положить stripe_key")


def test_a_free_key_replaces_the_same_complaint_and_walks_past_another(tmp_path):
    held = manual(tmp_path)
    what = "положить STRIPE_KEY в окружение продакшена"
    assert held.free_key(what) == "aaaaaa" or held.free_key(what) != held.free_key("другое")
    first = held.free_key("совсем новое действие")
    assert held.free_key("совсем новое действие", claimed={first}) != first


# --- запись и обратное чтение ------------------------------------------------


def test_what_the_writer_writes_the_reader_reads_back(tmp_path):
    held = manual(tmp_path, None)
    held.write("применить миграцию 0007", proof="sh ops/migrated.sh", key="cccccc")
    read = held.actions()
    assert [one.key for one in read] == ["cccccc"]
    assert read[0].proof == "sh ops/migrated.sh"
    assert read[0].what == "применить миграцию 0007"


def test_a_line_is_replaced_where_it_stands_rather_than_laid_twice(tmp_path):
    held = manual(tmp_path)
    held.write("положить STRIPE_KEY в окружение продакшена", proof="sh ops/new.sh", key="aaaaaa")
    read = held.actions()
    assert len(read) == 2
    assert read[0].proof == "sh ops/new.sh"


def test_the_header_is_written_once_and_a_standing_file_keeps_its_own(tmp_path):
    held = manual(tmp_path)
    held.write("применить миграцию", proof="sh ops/m.sh", key="cccccc")
    assert held.path.read_text(encoding="utf-8").startswith("# Сделать руками\n")
    assert "Что ночь сделать не может.\n" in held.path.read_text(encoding="utf-8")


def test_closing_is_deletion_and_takes_only_its_own_line(tmp_path):
    held = manual(tmp_path)
    held.close("aaaaaa")
    assert [one.key for one in held.actions()] == ["bbbbbb"]


def test_closing_what_is_not_there_names_a_code(tmp_path):
    with pytest.raises(ManualError) as refused:
        manual(tmp_path).close("zzzzzz")
    assert refused.value.code == "no-such-action"


def test_a_file_the_repository_ignores_is_refused_rather_than_written(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".agent-kit/\n", encoding="utf-8")
    held = manual(tmp_path, None)
    with pytest.raises(ManualError) as refused:
        held.write("положить ключ", proof="sh ops/key.sh")
    assert refused.value.code == "manual-ignored"
    assert not held.path.exists()


# --- что нельзя записать -----------------------------------------------------


@pytest.mark.parametrize(
    "row",
    [
        {"what": "положить ключ", "proof": "sh -c 'echo `date`'"},
        {"what": "положить ключ", "proof": "sh a.sh · sh b.sh"},
        {"what": "положить `ключ`", "proof": "sh a.sh"},
        {"what": "положить ключ", "by_hand": "нужен человек · с телефоном"},
        {"what": "положить ключ", "proof": "sh a.sh\nsh b.sh"},
    ],
)
def test_a_value_the_reader_could_not_read_back_is_refused_before_a_key_is_derived(row):
    with pytest.raises(ManualRefused) as refused:
        refuse_unless_each_action_is_answered({"manual": [row]})
    assert refused.value.code.startswith("action-that-cannot-be-written")


def test_an_action_with_neither_a_proof_nor_a_reason_is_refused():
    with pytest.raises(ManualRefused) as refused:
        refuse_unless_each_action_is_answered({"manual": [{"what": "положить ключ"}]})
    assert refused.value.code.startswith("action-unproved")


def test_an_action_with_both_has_decided_neither():
    with pytest.raises(ManualRefused) as refused:
        refuse_unless_each_action_is_answered(
            {"manual": [{"what": "класть ключ", "proof": "sh a.sh", "by_hand": "нужен человек"}]}
        )
    assert refused.value.code.startswith("action-proved-and-by-hand")


def test_a_proof_that_cannot_fail_is_refused_before_anything_is_written():
    with pytest.raises(ManualRefused) as refused:
        refuse_unless_each_action_is_answered({"manual": [{"what": "класть ключ", "proof": "true"}]})
    assert refused.value.code.startswith("proof-that-proves-nothing")


def test_an_action_with_no_words_is_not_an_action():
    with pytest.raises(ManualRefused) as refused:
        refuse_unless_each_action_is_answered({"manual": [{"what": "  ", "proof": "sh a.sh"}]})
    assert refused.value.code.startswith("action-with-no-words")


def test_a_design_that_names_nothing_owes_nothing():
    refuse_unless_each_action_is_answered({})
    refuse_unless_each_action_is_answered({"manual": []})


# --- доказательство, которое запускается -------------------------------------


def test_a_proof_that_comes_back_green_takes_its_own_line_away(tmp_path):
    (tmp_path / "yes.sh").write_text("exit 0\n", encoding="utf-8")
    (tmp_path / "no.sh").write_text("exit 1\n", encoding="utf-8")
    held = manual(
        tmp_path,
        "# Сделать руками\n\n"
        "- первое · `key: aaaaaa` · `proof: sh yes.sh`\n"
        "- второе · `key: bbbbbb` · `proof: sh no.sh`\n",
    )
    checked = check(tmp_path)
    assert checked.done == ["aaaaaa"]
    assert [key for key, _ in checked.stands] == ["bbbbbb"]
    assert [one.key for one in held.actions()] == ["bbbbbb"]


def test_a_red_proof_does_not_stop_the_walk(tmp_path):
    (tmp_path / "yes.sh").write_text("exit 0\n", encoding="utf-8")
    manual(
        tmp_path,
        "# Сделать руками\n\n"
        "- первое · `key: aaaaaa` · `proof: sh nothing-here.sh`\n"
        "- второе · `key: bbbbbb` · `proof: sh yes.sh`\n",
    )
    checked = check(tmp_path)
    assert checked.done == ["bbbbbb"]
    assert [key for key, _ in checked.stands] == ["aaaaaa"]


def test_a_line_only_a_person_can_close_is_never_run_and_never_taken_away(tmp_path):
    held = manual(tmp_path)
    checked = check(tmp_path)
    assert [key for key, _ in checked.by_hand] == ["bbbbbb"]
    assert "bbbbbb" in [one.key for one in held.actions()]


def test_a_proof_that_cannot_fail_is_not_run_and_the_line_stands(tmp_path):
    held = manual(tmp_path, "# Сделать руками\n\n- первое · `key: aaaaaa` · `proof: true`\n")
    checked = check(tmp_path)
    assert checked.proves_nothing == ["aaaaaa"]
    assert checked.done == []
    assert [one.key for one in held.actions()] == ["aaaaaa"]


def test_a_proof_that_says_nothing_is_stopped_and_its_line_stands(tmp_path):
    held = manual(
        tmp_path, "# Сделать руками\n\n- первое · `key: aaaaaa` · `proof: sleep 30`\n"
    )
    checked = check(tmp_path, timeout=1)
    assert [key for key, _ in checked.stands] == ["aaaaaa"]
    assert [one.key for one in held.actions()] == ["aaaaaa"]


def test_the_walk_over_a_project_with_no_file_answers_nothing_and_refuses_nothing(tmp_path):
    checked = check(manual(tmp_path, None).root)
    assert checked.done == [] and checked.stands == [] and checked.by_hand == []


def test_the_refusal_carries_the_state_code():
    assert ManualError("x").exit_code == ExitCode.STATE


def test_render_and_read_are_the_same_shape():
    line = render_action("aaaaaa", "положить ключ", proof="sh a.sh")
    held = read_actions(MANUAL, [line])
    assert held[0].key == "aaaaaa" and held[0].proof == "sh a.sh"


# --- the hook the design's answer hangs on -----------------------------------


def test_the_design_is_asked_about_its_actions_on_a_project_that_answers_no_kind():
    """The hook returned nothing at all when a project owed no kind of verification —
    which is most projects and almost every world of the bench. A check hung inside
    that one would be a check nobody performs."""
    from agent_kit.steps.contract import ContractRefusal
    from agent_kit.verification.owed import recount_for

    held = recount_for("design", {}, None)

    assert held is not None
    with pytest.raises(ContractRefusal) as refused:
        held({"manual": [{"what": "положить ключ", "proof": "true"}]})
    assert refused.value.code.startswith("proof-that-proves-nothing")


def test_a_design_with_nothing_wrong_passes_the_same_hook():
    from agent_kit.verification.owed import recount_for

    recount_for("design", {}, None)({"manual": [{"what": "положить ключ", "proof": "sh a.sh"}]})


def test_the_step_declares_the_field_and_a_design_that_names_none_still_stands():
    from agent_kit.steps import builtin_registry

    design = builtin_registry().get("design")
    assert any(one.name == "manual" for one in design.contract.fields)
    said = design.contract.check(
        {"title": "t", "summary": "s", "changes": ["c"], "seams": [], "asks": [], "assumptions": []}
    )
    from agent_kit.manual import actions_of

    # Absent is what an optional record list comes back as, exactly like
    # `proves`: a design written before this existed answers for no chores.
    assert actions_of(said) == []
