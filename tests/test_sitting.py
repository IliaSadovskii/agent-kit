"""The hour with the owner: what the kit reads, what it asks, what it writes.

Two turns, one round of questions, and the writing is the program's. Everything
below drives it with the fake provider and a scripted terminal, which is what
the bench does too — a shape that cannot be driven cannot be trapped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_kit.driver.session import Sessions
from agent_kit.errors import ChannelError, ConfigError, ExitCode, StateError, UsageError
from agent_kit.knowledge import Knowledge, part_key
from agent_kit.machine import Ledger, ledger_path
from agent_kit.paths import Paths
from agent_kit.providers.fake.adapter import FakeExecutor
from agent_kit.sitting import Sitting, SittingRefusal, Telling
from agent_kit.sitting.steps import READING

TOLD = """Продукт — тренажёр английского.
Вход через Google и Apple, и почтой можно.
Уведомления вечером, окно человек выбирает сам.
Импорт словаря еле ползёт на больших файлах.
"""

STANDING = """# Продукт

## Части

- вход — только Google — `key: sign-in` · `walked: 2026-08-20`
"""


def project(tmp_path, knowledge=STANDING, declares="docs/knowledge"):
    (tmp_path / ".agent-kit/v3").mkdir(parents=True)
    said = "" if declares is None else f'\nknowledge = "{declares}"'
    (tmp_path / ".agent-kit/v3/project.toml").write_text(
        f'[project]\ndefault_branch = "main"{said}\n', encoding="utf-8"
    )
    if knowledge is not None:
        where = tmp_path / "docs/knowledge"
        where.mkdir(parents=True)
        (where / "product.md").write_text(knowledge, encoding="utf-8")
    return tmp_path


def sitting(tmp_path, replies, answers=(), today="2026-08-27"):
    fake = FakeExecutor(name="fake", replies=[json.dumps(one, ensure_ascii=False) if isinstance(one, dict) else one for one in replies])
    sessions = Sessions(
        executors={"fake": fake},
        root=tmp_path,
        ledger=Ledger(ledger_path(Paths.from_env())),
        default_provider="fake",
        backoff=0,
    )
    said: list[str] = []
    return Sitting(
        root=tmp_path, sessions=sessions, today=today, say=said.append,
        answers=iter(answers) if answers is not None else None,
    ), said, fake


def reading(**over):
    one = {
        "parts": [
            {"key": "sign-in", "verdict": "refines", "name": "вход",
             "says": "Google, Apple и почта", "said": "L2"},
            {"verdict": "new", "name": "уведомления", "says": "вечером, окно выбирает человек", "said": "L3"},
        ],
        "ledger": [{"what": "импорт словаря еле ползёт", "kind": "badly", "said": "L4"}],
    }
    one.update(over)
    return one


# --- what one sitting comes to ---------------------------------------------


def test_a_sitting_writes_the_parts_the_owner_told(tmp_path):
    root = project(tmp_path)
    held, said, _ = sitting(root, [reading()])
    outcome = held.hold(Telling(TOLD))
    text = (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert "- вход — Google, Apple и почта — `key: sign-in` · `walked: 2026-08-27`" in text
    assert f"`key: {part_key('уведомления')}` · `walked: 2026-08-27`" in text
    assert outcome.written is not None and len(outcome.written.parts) == 2


def test_a_repository_with_no_knowledge_ends_the_sitting_with_one(tmp_path):
    """The done-when: nothing there before, a description the design step can read after."""
    root = project(tmp_path, knowledge=None)
    held, _, _ = sitting(root, [reading(parts=[
        {"verdict": "new", "name": "вход", "says": "Google, Apple и почта", "said": "L2"},
    ], ledger=[])])
    held.hold(Telling(TOLD))
    knowledge = Knowledge(root / "docs/knowledge")
    assert knowledge.described
    assert [part.name for part in knowledge.parts()] == ["вход"]
    assert "the parts of the product" in knowledge.index()


def test_the_telling_is_on_disk_before_a_session_is_asked_anything(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [])  # nothing scripted: the first turn cannot answer
    with pytest.raises(StateError):
        held.hold(Telling(TOLD))
    kept = list((root / ".agent-kit/v3/sittings").glob("*/telling.txt"))
    assert kept and kept[0].read_text(encoding="utf-8") == TOLD


def test_an_empty_telling_is_refused_before_anything_else(tmp_path):
    root = project(tmp_path)
    held, _, fake = sitting(root, [reading()])
    with pytest.raises(UsageError) as refused:
        held.hold(Telling("   \n\n"))
    assert refused.value.code == "nothing-was-told"
    assert not fake.requests


def test_a_project_that_says_it_keeps_no_knowledge_has_nowhere_to_put_one(tmp_path):
    root = project(tmp_path, knowledge=None, declares="")
    held, _, _ = sitting(root, [reading()])
    with pytest.raises(ConfigError) as refused:
        held.hold(Telling(TOLD))
    assert refused.value.code == "no-knowledge-declared"


# --- the reading, and what a program can check about it ---------------------


def test_a_reading_that_drops_a_standing_part_is_refused_by_name(tmp_path):
    root = project(tmp_path)
    short = reading(parts=[
        {"verdict": "new", "name": "уведомления", "says": "вечером", "said": "L3"},
    ])
    held, _, _ = sitting(root, [short, short, short])
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "reading-misses-a-part" in str(refused.value)
    assert "sign-in" in str(refused.value)


def test_the_refusal_is_enclosed_and_the_next_attempt_is_asked_again(tmp_path):
    root = project(tmp_path)
    short = reading(parts=[{"verdict": "new", "name": "уведомления", "says": "вечером", "said": "L3"}])
    held, _, fake = sitting(root, [short, reading()])
    held.hold(Telling(TOLD))
    assert len(fake.requests) == 2
    assert "reading-misses-a-part" in fake.requests[1].input_text


def test_a_line_pointing_at_lines_the_telling_does_not_have_is_refused(tmp_path):
    root = project(tmp_path)
    invented = reading(parts=[
        {"key": "sign-in", "verdict": "refines", "name": "вход", "says": "что угодно", "said": "L40"},
    ])
    held, _, _ = sitting(root, [invented] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "no-such-lines" in str(refused.value)


def test_a_range_that_covers_only_blank_lines_is_refused(tmp_path):
    telling = Telling("сказал одно\n\n\nи ещё\n")
    with pytest.raises(SittingRefusal) as refused:
        telling.said("L2-L3", "parts[0]")
    assert refused.value.code == "nothing-was-said"


def test_a_part_the_product_already_has_cannot_be_added_again(tmp_path):
    root = project(tmp_path)
    twice = reading(parts=[
        {"key": "sign-in", "verdict": "new", "name": "вход", "says": "ещё раз", "said": "L2"},
    ])
    held, _, _ = sitting(root, [twice] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "part-already-there" in str(refused.value)


def test_one_part_cannot_have_two_readings(tmp_path):
    root = project(tmp_path)
    twice = reading(parts=[
        {"key": "sign-in", "verdict": "unchanged"},
        {"key": "sign-in", "verdict": "unchanged"},
    ], ledger=[])
    held, _, _ = sitting(root, [twice] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "part-named-twice" in str(refused.value)


def test_a_new_part_whose_name_derives_a_taken_key_is_refused(tmp_path):
    root = project(tmp_path, knowledge=(
        "# Продукт\n\n## Части\n\n- вход — только Google — `walked: 2026-08-20`\n"
    ))
    clashing = reading(parts=[
        {"key": part_key("вход"), "verdict": "unchanged"},
        {"verdict": "new", "name": "вход", "says": "снова вход", "said": "L2"},
    ], ledger=[])
    held, _, _ = sitting(root, [clashing] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "part-already-there" in str(refused.value)


def test_a_part_that_did_not_move_needs_its_key_and_nothing_else(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading(parts=[{"key": "sign-in", "verdict": "unchanged"}], ledger=[])])
    outcome = held.hold(Telling(TOLD))
    assert outcome.reading is not None and outcome.reading.counted("unchanged") == 1
    # Not even the mark moves: the line somebody wrote stays exactly as it was.
    assert "- вход — только Google — `key: sign-in` · `walked: 2026-08-20`" in (
        (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    )


def test_a_contradiction_with_no_question_is_refused_by_name(tmp_path):
    root = project(tmp_path)
    mute = reading(parts=[
        {"key": "sign-in", "verdict": "contradicts", "name": "вход", "says": "иначе", "said": "L2"},
    ], ledger=[])
    held, _, _ = sitting(root, [mute] * 3, answers=["что угодно"])
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "no-question-for-a-contradiction" in str(refused.value)


# --- the one round of questions ---------------------------------------------


def contradicting():
    return reading(parts=[
        {"key": "sign-in", "verdict": "contradicts", "name": "вход", "says": "Google, Apple и почта",
         "said": "L2", "question": "Записано: только Google. Вы сказали: и Apple. Что верно?"},
    ], ledger=[])


def test_only_the_contradictions_are_put_to_the_owner(tmp_path):
    root = project(tmp_path)
    first = reading(parts=[
        {"key": "sign-in", "verdict": "contradicts", "name": "вход", "says": "Google, Apple и почта",
         "said": "L2", "question": "только Google или ещё Apple?"},
        {"verdict": "new", "name": "уведомления", "says": "вечером", "said": "L3"},
    ], ledger=[])
    second = {"parts": [
        {"key": "sign-in", "verdict": "refines", "name": "вход", "says": "Google, Apple и почта", "said": "L2"},
    ]}
    held, said, _ = sitting(root, [first, second], answers=["и Apple тоже"])
    outcome = held.hold(Telling(TOLD))
    assert [key for key, _ in outcome.asked] == ["sign-in"]
    asked = [line for line in said if line.startswith("? ")]
    assert len(asked) == 1


def test_a_contradiction_with_nobody_at_the_terminal_writes_nothing(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [contradicting()], answers=[])
    with pytest.raises(ChannelError) as refused:
        held.hold(Telling(TOLD))
    assert refused.value.code == "nobody-to-ask"
    assert refused.value.exit_code == ExitCode.CHANNEL
    # Nothing written: half a description is worse than none.
    assert "- вход — только Google" in (root / "docs/knowledge/product.md").read_text(encoding="utf-8")


def test_the_settling_answers_only_for_what_was_asked(tmp_path):
    root = project(tmp_path)
    wide = {"parts": [
        {"key": "sign-in", "verdict": "refines", "name": "вход", "says": "Google и Apple", "said": "L2"},
        {"verdict": "new", "name": "ещё что-то", "says": "и вот это", "said": "L3"},
    ]}
    held, _, _ = sitting(root, [contradicting(), wide, wide, wide], answers=["и Apple"])
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "part-nobody-asked-about" in str(refused.value)


def test_the_answer_is_enclosed_in_the_settling_turn(tmp_path):
    root = project(tmp_path)
    second = {"parts": [
        {"key": "sign-in", "verdict": "refines", "name": "вход", "says": "Google, Apple", "said": "L2"},
    ]}
    held, _, fake = sitting(root, [contradicting(), second], answers=["и Apple тоже"])
    held.hold(Telling(TOLD))
    assert "и Apple тоже" in fake.requests[1].input_text
    assert "what the owner answered" in fake.requests[1].input_text


def test_there_is_one_round_and_the_settling_is_not_asked_again(tmp_path):
    root = project(tmp_path)
    second = {"parts": [
        {"key": "sign-in", "verdict": "contradicts", "name": "вход", "says": "Google, Apple",
         "said": "L2", "question": "а точно?"},
    ]}
    held, said, fake = sitting(root, [contradicting(), second], answers=["и Apple тоже"])
    held.hold(Telling(TOLD))
    assert len(fake.requests) == 2
    assert len([line for line in said if line.startswith("? ")]) == 1


# --- the counts, and the denominator ----------------------------------------


def test_the_counts_are_said_back_with_the_denominator(tmp_path):
    root = project(tmp_path)
    (root / "docs/knowledge/entities.md").write_text(
        "# Сущности\n\n### Деньги\n`key: money`\n", encoding="utf-8"
    )
    held, said, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    printed = "\n".join(said)
    assert "new 1 · refines 1 · contradicts 0 · unchanged 0" in printed
    assert "badly 1 · broken 0" in printed
    assert "сверено частей: 2" in printed
    assert "записей вне частей не читалось: 2" in printed


# --- the ledger --------------------------------------------------------------


def test_the_ledger_takes_the_lines_that_are_not_about_what_the_product_must_do(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading(ledger=[
        {"what": "импорт словаря еле ползёт", "kind": "badly", "said": "L4"},
        {"what": "экспорт падает совсем", "kind": "broken", "said": "L4"},
    ])])
    held.hold(Telling(TOLD))
    text = (root / "docs/knowledge/debt.md").read_text(encoding="utf-8")
    assert "## Работает плохо" in text and "## Не работает" in text
    assert text.index("импорт словаря") < text.index("## Не работает")
    assert text.index("## Не работает") < text.index("экспорт падает")


def test_a_ledger_line_is_not_a_part_of_the_product(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    keys = [part.key for part in Knowledge(root / "docs/knowledge").parts()]
    assert len(keys) == 2, "a line about work that is wrong was read as a part of the product"


# --- the same telling, twice --------------------------------------------------


def told_again():
    """The second telling of the same thing: every standing part answered for again."""
    return reading(parts=[
        {"key": "sign-in", "verdict": "refines", "name": "вход",
         "says": "Google, Apple и почта", "said": "L2"},
        {"key": part_key("уведомления"), "verdict": "refines", "name": "уведомления",
         "says": "вечером, окно выбирает человек", "said": "L3"},
    ])


def test_the_same_telling_told_twice_rewrites_rather_than_duplicates(tmp_path):
    root = project(tmp_path)
    for answer in (reading(), told_again()):
        held, _, _ = sitting(root, [answer])
        held.hold(Telling(TOLD))
    text = (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert text.count("key: sign-in") == 1
    assert text.count(f"key: {part_key('уведомления')}") == 1
    assert (root / "docs/knowledge/debt.md").read_text(encoding="utf-8").count("импорт словаря") == 1


def test_a_second_sitting_gets_a_room_of_its_own(tmp_path):
    root = project(tmp_path)
    for answer in (reading(), told_again()):
        held, _, _ = sitting(root, [answer])
        held.hold(Telling(TOLD))
    rooms = sorted(one.name for one in (root / ".agent-kit/v3/sittings").iterdir() if one.is_dir())
    assert rooms == ["2026-08-27", "2026-08-27-2"]


def test_a_block_a_run_wrote_under_a_part_survives_the_part_being_refined(tmp_path):
    root = project(tmp_path, knowledge=STANDING)
    held, _, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    text = (root / "docs/knowledge/product.md")
    text.write_text(
        text.read_text(encoding="utf-8")
        + "\n> **[assumed 2026-08-27 · kit/x · id: aaa111]** что-то допущено\n",
        encoding="utf-8",
    )
    held, _, _ = sitting(root, [told_again()])
    held.hold(Telling(TOLD))
    assert "id: aaa111" in text.read_text(encoding="utf-8")


# --- the two turns are not steps of any run ------------------------------------


def test_the_sitting_turns_are_not_in_the_registry_a_run_orders_from(tmp_path):
    from agent_kit.steps import builtin_registry

    assert not builtin_registry().has(READING.name)
    assert not builtin_registry().has("settling")


def test_the_input_of_a_sitting_names_no_branch(tmp_path):
    root = project(tmp_path)
    held, _, fake = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    assert "do not create it" not in fake.requests[0].input_text


# --- one writer per working copy ---------------------------------------------


def test_a_sitting_will_not_write_under_a_run_that_holds_the_checkout(tmp_path):
    """The rule is the kit's already: a working copy has one writer.

    A sitting writes two files into the project's own checkout, which is exactly
    where a run started by hand is building. The refusal is the one that already
    means this, by the code it already has.
    """
    root = project(tmp_path)
    ledger = Ledger(ledger_path(Paths.from_env()))
    # This process, so the lease is alive and is not reaped as a dead driver's.
    assert ledger.hold_checkout(str(root), "add-vat").granted

    held, _, fake = sitting(root, [reading()])
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert refused.value.code == "checkout-held-elsewhere"
    assert not fake.requests, "a session was spent on a sitting that could not write"


def test_a_sitting_gives_the_checkout_back_when_it_is_done(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    ledger = Ledger(ledger_path(Paths.from_env()))
    assert not [one for one in ledger.checkouts() if one.project == str(root)]


def test_a_sitting_gives_the_checkout_back_when_it_is_refused(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [])
    with pytest.raises(StateError):
        held.hold(Telling(TOLD))
    ledger = Ledger(ledger_path(Paths.from_env()))
    assert not [one for one in ledger.checkouts() if one.project == str(root)]


def test_an_answer_already_given_is_kept_when_the_next_question_has_nobody(tmp_path):
    """They typed it. Losing it because the stream ended is losing their work."""
    root = project(tmp_path, knowledge=(
        "# Продукт\n\n## Части\n\n"
        "- вход — только Google — `key: sign-in` · `walked: 2026-08-20`\n"
        "- оплата — только карта — `key: pay` · `walked: 2026-08-20`\n"
    ))
    both = reading(parts=[
        {"key": "sign-in", "verdict": "contradicts", "name": "вход", "says": "и Apple",
         "said": "L2", "question": "а Apple?"},
        {"key": "pay", "verdict": "contradicts", "name": "оплата", "says": "и счёт",
         "said": "L2", "question": "а счёт?"},
    ], ledger=[])
    held, _, _ = sitting(root, [both], answers=["да, и Apple"])
    with pytest.raises(ChannelError):
        held.hold(Telling(TOLD))
    kept = list((root / ".agent-kit/v3/sittings").glob("*/answers.txt"))
    assert kept and "да, и Apple" in kept[0].read_text(encoding="utf-8")


# --- the refusals that had no test of their own -----------------------------


def test_a_said_that_is_not_a_range_at_all_is_refused_by_name(tmp_path):
    """A range is arithmetic. A sentence in that field is a quote by another name."""
    root = project(tmp_path)
    quoted = reading(parts=[
        {"key": "sign-in", "verdict": "refines", "name": "вход", "says": "и Apple",
         "said": "он сказал про Apple"},
    ], ledger=[])
    held, _, _ = sitting(root, [quoted] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "not-a-range" in str(refused.value)


def test_a_range_the_telling_does_not_have_and_one_it_does(tmp_path):
    telling = Telling("одна\nдве\nтри\n")
    assert telling.said("L2", "parts[0]") == ["две"]
    assert telling.said("L1-L3", "parts[0]") == ["одна", "две", "три"]
    for where in ("L0", "L4", "L3-L1", "L2-L9"):
        with pytest.raises(SittingRefusal) as refused:
            telling.said(where, "parts[0]")
        assert refused.value.code in ("no-such-lines", "not-a-range"), where


def test_a_reading_that_names_a_part_this_product_has_not_got_is_refused(tmp_path):
    root = project(tmp_path)
    invented = reading(parts=[
        {"key": "sign-in", "verdict": "unchanged"},
        {"key": "nowhere", "verdict": "refines", "name": "что-то", "says": "и вот", "said": "L2"},
    ], ledger=[])
    held, _, _ = sitting(root, [invented] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "no-such-part" in str(refused.value)
    assert "nowhere" in str(refused.value)


def test_a_row_that_changes_something_and_names_no_key_is_refused(tmp_path):
    root = project(tmp_path)
    nameless = reading(parts=[
        {"key": "sign-in", "verdict": "unchanged"},
        {"verdict": "refines", "name": "что-то", "says": "и вот", "said": "L2"},
    ], ledger=[])
    held, _, _ = sitting(root, [nameless] * 3)
    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))
    assert "no-such-part" in str(refused.value)


def test_a_telling_that_could_not_be_read_is_refused_before_anything(tmp_path):
    """`--from` naming nothing: the one refusal that happens before a room exists."""
    from agent_kit.cli.main import main

    root = project(tmp_path)
    code = main(["-C", str(root), "knowledge", "tell", "--from", str(tmp_path / "nothing.md")])
    assert code == int(ExitCode.USAGE)
    assert not (root / ".agent-kit/v3/sittings").exists()


# --- the ledger is not a description ----------------------------------------


def test_an_hour_spent_only_on_bugs_leaves_a_project_nobody_has_described(tmp_path):
    root = project(tmp_path, knowledge=None)
    held, _, _ = sitting(root, [reading(parts=[], ledger=[
        {"what": "импорт еле ползёт", "kind": "badly", "said": "L4"},
    ])])
    held.hold(Telling(TOLD))
    knowledge = Knowledge(root / "docs/knowledge")
    assert (root / "docs/knowledge/debt.md").is_file()
    assert not knowledge.described, "a ledger heading counted as a description of the product"


def test_a_description_beside_a_ledger_is_still_a_description(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    assert Knowledge(root / "docs/knowledge").described


# --- what a room holds is not repository content -----------------------------


def test_the_room_of_a_sitting_is_kept_out_of_git(tmp_path):
    root = project(tmp_path)
    held, _, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    ignore = root / ".agent-kit/v3/sittings/.gitignore"
    assert ignore.is_file() and ignore.read_text(encoding="utf-8").strip().endswith("*")


# --- what a part already carries, before it is rewritten ----------------------


def test_the_blocks_standing_where_a_part_is_about_to_be_rewritten_are_said(tmp_path):
    root = project(tmp_path, knowledge=(
        "# Продукт\n\n## Части\n\n"
        "- вход — только Google — `key: sign-in` · `walked: 2026-08-20`\n\n"
        "> **[assumed 2026-08-20 · kit/x · id: aaa111]** что-то допущено\n"
    ))
    held, said, _ = sitting(root, [reading()])
    held.hold(Telling(TOLD))
    assert any("блоков, написанных до правки: 1" in line for line in said)
