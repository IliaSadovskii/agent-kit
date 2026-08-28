"""The ledger of what is built and works badly, read as data rather than prose.

S8a gave `<knowledge>/debt.md` a writer — the hour with the owner — and left it
with no reader and no closer. A line carries a key and no mark, which is what
keeps it out of `parts()`: a mark is what makes a list item a part of the
product, and a line about work that is wrong is not one.

What S8f adds here is the reading: a line is data, it goes into the index every
`design` and every sitting is handed, and it can be closed by the work that does
it.
"""

from __future__ import annotations

import pytest

from agent_kit.knowledge import Knowledge, KnowledgeError, identifier
from agent_kit.knowledge.debt import BADLY, BROKEN, LEDGER, debt_key, read_debt

REAL = """# Технический долг

Что уже построено и работает не так.

## Работает плохо

- кнопка ничего не говорит про удержание (notes.ts:90) · `key: aaaaaa` · `run: kit/rates`
- счётчик профиля расходится с записью · `key: bbbbbb`

## Не работает

- выгрузка отчёта падает на пустом периоде · `key: cccccc`
"""


def line_for(held, key):
    """The line by its key: a new `badly` line lands in its own section, which is
    not the end of the file — the ledger holds two sections and `broken` is below."""
    return [one for one in held.debt() if one.key == key][0]


def knowledge(tmp_path, files):
    root = tmp_path / "docs" / "knowledge"
    root.mkdir(parents=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return Knowledge(root)


def test_a_line_carries_a_key_and_no_mark(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL}).debt()
    assert [one.key for one in held] == ["aaaaaa", "bbbbbb", "cccccc"]
    assert held[0].what == "кнопка ничего не говорит про удержание (notes.ts:90)"


def test_the_run_says_a_night_found_it_and_its_absence_says_the_owner_did(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL}).debt()
    assert held[0].run == "kit/rates"
    assert held[1].run == ""


def test_a_part_is_not_a_ledger_line(tmp_path):
    """A mark is what makes a list item a part, and a part is never debt."""
    text = REAL + "\n- деньги — сумма и ставка — `key: money` · `walked: 2026-08-20`\n"
    assert [one.key for one in read_debt(LEDGER, text.splitlines())] == ["aaaaaa", "bbbbbb", "cccccc"]


def test_only_the_ledger_is_read_as_debt(tmp_path):
    """`debt.md` is the kit's own name; a list item elsewhere is the project's."""
    held = knowledge(tmp_path, {LEDGER: REAL, "product.md": "# Продукт\n\n- что-то · `key: zzzzzz`\n"})
    assert [one.key for one in held.debt()] == ["aaaaaa", "bbbbbb", "cccccc"]


def test_two_lines_answering_to_one_key_are_refused(tmp_path):
    text = REAL + "\n- что-то ещё · `key: aaaaaa`\n"
    with pytest.raises(KnowledgeError) as refused:
        knowledge(tmp_path, {LEDGER: text}).debt()
    assert refused.value.code == "two-lines-one-key"


def test_the_ledger_does_not_make_a_project_described(tmp_path):
    assert knowledge(tmp_path, {LEDGER: REAL}).described is False


# --- writing ----------------------------------------------------------------


def test_a_line_is_written_into_the_section_its_kind_names(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.write_debt("отчёт считает вручную", BADLY)
    held.write_debt("почта не уходит вовсе", BROKEN)
    lines = (held.root / LEDGER).read_text(encoding="utf-8").splitlines()
    badly = lines.index("## Работает плохо")
    broken = lines.index("## Не работает")
    assert badly < lines.index([one for one in lines if "отчёт считает вручную" in one][0]) < broken
    assert broken < lines.index([one for one in lines if "почта не уходит вовсе" in one][0])


def test_the_file_is_made_with_its_own_head_when_there_is_none(tmp_path):
    held = knowledge(tmp_path, {})
    path = held.write_debt("отчёт считает вручную", BADLY)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Технический долг")
    assert "`agent-kit knowledge tell`" in text
    assert f"`key: {debt_key('отчёт считает вручную')}`" in text


def test_a_line_written_by_a_run_carries_the_run(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.write_debt("отчёт считает вручную", BADLY, run="kit/quote")
    assert "`run: kit/quote`" in (held.root / LEDGER).read_text(encoding="utf-8")
    assert line_for(held, debt_key("отчёт считает вручную")).run == "kit/quote"


def test_the_same_words_replace_their_own_line_rather_than_laying_a_second(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.write_debt("отчёт считает вручную", BADLY)
    held.write_debt("отчёт считает вручную", BADLY, run="kit/quote")
    assert len(held.debt()) == 4
    assert line_for(held, debt_key("отчёт считает вручную")).run == "kit/quote"


def test_a_key_the_caller_names_is_the_key_that_is_written(tmp_path):
    """The salt walk happens where the finding is read; the writer honours it."""
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.write_debt("одно и то же", BADLY, key="dddddd")
    assert line_for(held, "dddddd").what == "одно и то же"
    assert debt_key("одно и то же") not in [one.key for one in held.debt()]


# --- the key, derived and free ----------------------------------------------


def test_the_key_is_derived_from_the_words_so_a_case_can_name_it(tmp_path):
    assert debt_key("Отчёт  считает вручную") == identifier("debt", "отчёт считает вручную")


def test_a_line_with_the_same_words_is_ours_and_a_different_one_is_walked_past(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.write_debt("отчёт считает вручную", BADLY)
    assert held.free_key("отчёт считает вручную") == debt_key("отчёт считает вручную")
    assert held.free_key("отчёт считает вручную", claimed={debt_key("отчёт считает вручную")}) != debt_key(
        "отчёт считает вручную"
    )


def test_two_findings_worded_alike_get_two_keys(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    claimed: set[str] = set()
    first = held.free_key("одно и то же", claimed)
    claimed.add(first)
    assert held.free_key("одно и то же", claimed) != first


# --- closing ----------------------------------------------------------------


def test_closing_takes_the_line_and_leaves_its_neighbour(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    held.close_debt("aaaaaa")
    text = (held.root / LEDGER).read_text(encoding="utf-8")
    assert "кнопка ничего не говорит" not in text
    assert "счётчик профиля расходится" in text
    assert "## Работает плохо" in text
    assert [one.key for one in held.debt()] == ["bbbbbb", "cccccc"]


def test_closing_a_line_nobody_wrote_is_refused_by_name(tmp_path):
    held = knowledge(tmp_path, {LEDGER: REAL})
    with pytest.raises(KnowledgeError) as refused:
        held.close_debt("ffffff")
    assert refused.value.code == "no-such-debt"


# --- what the sessions are handed -------------------------------------------


def test_the_index_carries_the_lines_and_not_only_the_headings(tmp_path):
    index = knowledge(tmp_path, {LEDGER: REAL}).index()
    assert "aaaaaa" in index
    assert "кнопка ничего не говорит про удержание" in index
    assert "kit/rates" in index
