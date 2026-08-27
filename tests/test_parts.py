"""The parts of the product: a list item that carries a mark.

The second version wrote them as list items under `## Части` in `product.md`,
each ending in `walked: <date>` or `derived`. That is the format, and no line
of it is rewritten: what the third version adds is a key, in a segment of a
kind the same line already carries.
"""

from __future__ import annotations

import pytest

from agent_kit.knowledge import Knowledge, KnowledgeError
from agent_kit.knowledge.parts import DERIVED, part_key, read_parts, render_part

REAL = """# Продукт

## Части

<!-- Метка на каждой строке: `walked: <дата>` — владелец рассказал эту часть сам. -->

- задание — описание, ответ, проверка моделью — `walked: 2026-08-13`
- вход — Google, Apple, учётная запись — `derived`

## Для чего он

Чтобы человек продолжал учить английский.
"""


def knowledge(tmp_path, files):
    root = tmp_path / "docs" / "knowledge"
    root.mkdir(parents=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return Knowledge(root)


def test_a_part_is_a_list_item_that_carries_a_mark(tmp_path):
    parts = knowledge(tmp_path, {"product.md": REAL}).parts()
    assert [part.name for part in parts] == ["задание", "вход"]
    assert parts[0].mark == "2026-08-13"
    assert parts[1].mark == DERIVED
    assert parts[0].says == "описание, ответ, проверка моделью"


def test_a_list_item_with_no_mark_is_not_a_part(tmp_path):
    text = REAL.replace("- вход — Google, Apple, учётная запись — `derived`", "- вход — Google, Apple")
    parts = knowledge(tmp_path, {"product.md": text}).parts()
    assert [part.name for part in parts] == ["задание"]


def test_the_key_of_a_line_that_carries_none_is_derived_from_its_name(tmp_path):
    parts = knowledge(tmp_path, {"product.md": REAL}).parts()
    assert parts[0].key == part_key("задание")
    assert parts[0].key != parts[1].key
    # Derived, not drawn: the same words give the same key on every machine,
    # which is what lets a bench case name it before the run.
    assert part_key("задание") == part_key("задание")


def test_a_key_written_into_the_line_is_the_one_that_is_read(tmp_path):
    text = REAL.replace("— `walked: 2026-08-13`", "— `key: brief` · `walked: 2026-08-13`")
    parts = knowledge(tmp_path, {"product.md": text}).parts()
    assert parts[0].key == "brief"
    assert parts[0].says == "описание, ответ, проверка моделью"


def test_a_part_is_rendered_as_one_line_carrying_its_key_and_its_mark():
    line = render_part("sign-in", "вход", "Google, Apple", "2026-08-27")
    assert line == "- вход — Google, Apple — `key: sign-in` · `walked: 2026-08-27`"


def test_writing_a_part_twice_rewrites_its_line_rather_than_laying_a_second(tmp_path):
    held = knowledge(tmp_path, {"product.md": REAL})
    held.write_part("sign-in", "вход", "Google и Apple", "2026-08-27")
    held.write_part("sign-in", "вход", "Google, Apple и почта", "2026-08-28")
    text = (held.root / "product.md").read_text(encoding="utf-8")
    assert text.count("key: sign-in") == 1
    assert "Google, Apple и почта" in text
    assert "Google и Apple" not in text
    assert [part.key for part in held.parts()].count("sign-in") == 1


def test_a_new_part_lands_among_the_parts_and_not_at_the_end_of_the_file(tmp_path):
    held = knowledge(tmp_path, {"product.md": REAL})
    held.write_part("payment", "оплата", "карта и счёт", "2026-08-27")
    lines = (held.root / "product.md").read_text(encoding="utf-8").splitlines()
    where = [number for number, line in enumerate(lines) if "key: payment" in line][0]
    after = [number for number, line in enumerate(lines) if line.startswith("## Для чего")][0]
    assert where < after, "a new part was written past the section the parts stand in"


def test_a_part_that_was_never_touched_keeps_its_line_exactly(tmp_path):
    held = knowledge(tmp_path, {"product.md": REAL})
    held.write_part("payment", "оплата", "карта", "2026-08-27")
    text = (held.root / "product.md").read_text(encoding="utf-8")
    assert "- задание — описание, ответ, проверка моделью — `walked: 2026-08-13`" in text
    assert "- вход — Google, Apple, учётная запись — `derived`" in text


def test_a_project_with_no_product_file_gets_one(tmp_path):
    root = tmp_path / "docs" / "knowledge"
    held = Knowledge(root)
    held.write_part("sign-in", "вход", "Google, Apple", "2026-08-27")
    assert (root / "product.md").is_file()
    assert [part.name for part in held.parts()] == ["вход"]


def test_a_part_the_kit_wrote_is_read_back_as_the_same_part(tmp_path):
    held = knowledge(tmp_path, {"product.md": REAL})
    held.write_part("sign-in", "вход и регистрация", "Google, Apple", "2026-08-27")
    written = [part for part in held.parts() if part.key == "sign-in"]
    assert len(written) == 1
    assert written[0].name == "вход и регистрация"
    assert written[0].says == "Google, Apple"
    assert written[0].mark == "2026-08-27"


def test_renaming_a_part_moves_its_line_rather_than_adding_one(tmp_path):
    """The whole reason the key is written into the line rather than derived every time."""
    held = knowledge(tmp_path, {"product.md": REAL})
    held.write_part("sign-in", "вход", "Google, Apple", "2026-08-27")
    held.write_part("sign-in", "вход и регистрация", "Google, Apple, почта", "2026-08-28")
    text = (held.root / "product.md").read_text(encoding="utf-8")
    assert text.count("key: sign-in") == 1
    assert "вход и регистрация" in text


def test_two_parts_with_one_key_are_a_named_refusal(tmp_path):
    text = REAL.replace(
        "- вход — Google, Apple, учётная запись — `derived`",
        "- вход — Google — `key: one` · `derived`\n- оплата — карта — `key: one` · `derived`",
    )
    held = knowledge(tmp_path, {"product.md": text})
    with pytest.raises(KnowledgeError) as refused:
        held.parts()
    assert refused.value.code == "two-parts-one-key"


def test_the_index_prints_every_part_with_its_key_and_its_mark(tmp_path):
    printed = knowledge(tmp_path, {"product.md": REAL}).index()
    assert "the parts of the product" in printed
    assert part_key("задание") in printed
    assert "2026-08-13" in printed
    assert DERIVED in printed


def test_a_project_with_no_knowledge_says_so_in_the_index(tmp_path):
    printed = Knowledge(tmp_path / "nothing").index()
    assert "keeps no knowledge" in printed
