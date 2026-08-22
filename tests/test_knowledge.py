"""S6 — the project's knowledge, read and written by the program.

The format is the second version's, unchanged: every block is a markdown
blockquote whose first line names its kind, its date and the run that wrote it.
The one thing added is an identifier, and it is added the way the format already
adds things — one more `·` segment carrying a `key: value`, exactly like the
`pr: 29` that `frame` blocks have always carried.

Everything here is measured against the real shape, which was read out of
`beeplish` and reproduced in `REAL` below rather than imported: the suite must
not depend on another project being on this machine.
"""

import pytest

from agent_kit.knowledge import ALPHABET, Knowledge, KnowledgeError, identifier

#: The two header shapes the real knowledge uses, and nothing else. Faithful to
#: `beeplish/docs/knowledge` as it stood on 22 August 2026.
ENTITIES = """<!--
Сущности — то, что живёт дольше одного вызова.

fields: Что это, Состояния, Инварианты
-->

# Сущности

### Учётная запись
`key: account`

**Что это:** аккаунт человека в приложении
**Инварианты:** одна привязка провайдера ведёт ровно к одному аккаунту

> **[assumed 2026-08-18 · claude/2026-08-17-own-key-01-key-storage]** «Берётся список моделей этим
> ключом» проверкой ключа не является: каталог у OpenRouter публичный.

### Доступ к модели
`key: model_credential` · `state: built`

**Что это:** чей ключ OpenRouter оплачивает задания этого человека

> **[frame 2026-08-19 · 2026-08-19-teardown · pr: 29]** Записи стенда правятся с обеих сторон
> одним коммитом.
"""

STACK = """<!--
Стек — чем это построено.
-->

# Стек

## Вызовы модели

Все вызовы идут через один шлюз.

## Данные и миграции

Миграция, сносящая таблицу, восстанавливает её в `down()`.
"""


@pytest.fixture
def knowledge(tmp_path):
    root = tmp_path / "docs/knowledge"
    root.mkdir(parents=True)
    (root / "entities.md").write_text(ENTITIES, encoding="utf-8")
    (root / "stack.md").write_text(STACK, encoding="utf-8")
    return Knowledge(root)


# --- reading what is already there ------------------------------------------


def test_both_header_shapes_the_real_knowledge_uses_are_read(knowledge):
    kinds = [(block.kind, block.date, block.run) for block in knowledge.blocks()]

    assert ("assumed", "2026-08-18", "claude/2026-08-17-own-key-01-key-storage") in kinds
    assert ("frame", "2026-08-19", "2026-08-19-teardown") in kinds


def test_a_block_the_second_version_wrote_has_no_identifier(knowledge):
    assert [block.id for block in knowledge.blocks()] == ["", ""]


def test_a_record_is_addressed_by_its_key(knowledge):
    anchor = knowledge.resolve("entities.md#account")

    assert anchor.heading == "Учётная запись"


def test_a_key_line_that_carries_more_than_the_key_is_still_read(knowledge):
    # `key: model_credential` · `state: built` — the second segment is not ours.
    assert knowledge.resolve("entities.md#model_credential").heading == "Доступ к модели"


def test_a_prose_file_with_no_keys_is_addressed_by_its_heading(knowledge):
    anchor = knowledge.resolve("stack.md#Вызовы модели")

    assert anchor.heading == "Вызовы модели"


def test_an_address_naming_no_record_is_refused_by_name(knowledge):
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("entities.md#ghost")

    assert refused.value.code == "no-such-record"


def test_an_address_naming_no_file_is_refused_by_name(knowledge):
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("nowhere.md#account")

    assert refused.value.code == "no-such-file"


def test_an_address_with_no_anchor_at_all_is_refused(knowledge):
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("entities.md")

    assert refused.value.code == "bad-address"


def test_two_records_matching_one_anchor_are_refused_rather_than_guessed(knowledge, tmp_path):
    (tmp_path / "docs/knowledge/twice.md").write_text("### Одно\n\n### Одно\n", encoding="utf-8")

    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("twice.md#Одно")

    assert refused.value.code == "ambiguous-record"


# --- the identifier ----------------------------------------------------------


def test_the_same_run_and_assumption_give_the_same_identifier():
    assert identifier("add-vat", "the rate is a whole percent") == identifier(
        "add-vat", "the rate is a whole percent"
    )


def test_a_different_assumption_gives_a_different_identifier():
    assert identifier("add-vat", "one") != identifier("add-vat", "two")
    assert identifier("add-vat", "one") != identifier("add-tax", "one")


def test_the_identifier_cannot_spell_a_word():
    got = identifier("add-vat", "the rate is a whole percent")

    assert len(got) == 6
    assert set(got) <= set(ALPHABET)
    assert not set(ALPHABET) & set("aeiou")


# --- writing a block ---------------------------------------------------------


def written(knowledge, at="entities.md#account", what="the rate is a whole percent",
            body="Nothing says the rate is a whole percent. Took it as one.", slug="add-vat"):
    return knowledge.write(at=at, run=f"kit/{slug}", body=body, id=identifier(slug, what), date="2026-08-22")


def test_a_written_block_carries_its_identifier_in_a_segment_of_its_own(knowledge):
    written(knowledge)

    wanted = identifier("add-vat", "the rate is a whole percent")
    line = next(l for l in (knowledge.root / "entities.md").read_text().splitlines() if "kit/add-vat" in l)
    assert line.startswith(f"> **[assumed 2026-08-22 · kit/add-vat · id: {wanted}]** ")


def test_the_block_is_read_back_by_its_identifier(knowledge):
    written(knowledge)

    wanted = identifier("add-vat", "the rate is a whole percent")
    assert wanted in [block.id for block in knowledge.blocks()]


def test_the_block_lands_at_the_end_of_the_record_it_addresses(knowledge):
    written(knowledge)

    lines = (knowledge.root / "entities.md").read_text().splitlines()
    ours = next(index for index, line in enumerate(lines) if "kit/add-vat" in line)
    heading = next(index for index, line in enumerate(lines) if line == "### Доступ к модели")
    assert ours < heading  # inside its own record, not in the next one
    assert lines[ours - 1].strip() == ""


def test_a_block_at_the_end_of_the_file_does_not_need_a_next_heading(knowledge):
    written(knowledge, at="stack.md#Данные и миграции")

    text = (knowledge.root / "stack.md").read_text()
    assert text.endswith("\n")
    assert "kit/add-vat" in text.split("## Данные и миграции")[1]


def test_lines_are_quoted_and_wrapped_where_the_real_knowledge_wraps(knowledge):
    written(knowledge, body="слово " * 80)

    lines = (knowledge.root / "entities.md").read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if "kit/add-vat" in line)
    ours = list(_quoted_from(lines, start))
    assert len(ours) > 1
    assert all(line.startswith("> ") for line in ours)
    assert all(len(line) <= 100 for line in ours)


def _quoted_from(lines, start):
    for line in lines[start:]:
        if not line.startswith(">"):
            return
        yield line


def test_writing_the_same_block_again_replaces_it_rather_than_laying_a_second(knowledge):
    written(knowledge)
    written(knowledge, body="Nothing says the rate is a whole percent. Still took it as one.")

    text = (knowledge.root / "entities.md").read_text()
    assert text.count("kit/add-vat") == 1
    assert "Still took it as one" in text


def test_a_second_write_moves_the_block_when_the_address_changed(knowledge):
    written(knowledge)
    written(knowledge, at="stack.md#Вызовы модели")

    assert "kit/add-vat" not in (knowledge.root / "entities.md").read_text()
    assert "kit/add-vat" in (knowledge.root / "stack.md").read_text()


def test_nothing_else_in_the_file_is_disturbed(knowledge):
    before = (knowledge.root / "entities.md").read_text()

    written(knowledge)

    after = (knowledge.root / "entities.md").read_text()
    for line in before.splitlines():
        assert line in after.splitlines()


# --- closing one -------------------------------------------------------------


def test_closing_removes_the_whole_block_and_nothing_around_it(knowledge):
    written(knowledge)
    wanted = identifier("add-vat", "the rate is a whole percent")

    knowledge.close(wanted)

    text = (knowledge.root / "entities.md").read_text()
    assert "kit/add-vat" not in text
    assert "### Учётная запись" in text
    assert "### Доступ к модели" in text
    assert "claude/2026-08-17-own-key-01-key-storage" in text
    assert "\n\n\n" not in text


def test_closing_an_identifier_the_knowledge_does_not_hold_is_refused(knowledge):
    with pytest.raises(KnowledgeError) as refused:
        knowledge.close("zzzzzz")

    assert refused.value.code == "no-such-block"


def test_a_block_with_no_identifier_cannot_be_closed_and_the_index_says_so(knowledge):
    assert "cannot be closed" in knowledge.index()


# --- the index the driver encloses -------------------------------------------


def test_the_index_names_every_file_every_record_and_every_block(knowledge):
    index = knowledge.index()

    assert "entities.md#account" in index
    assert "entities.md#model_credential" in index
    assert "stack.md#Вызовы модели" in index
    assert "Сущности — то, что живёт дольше одного вызова." in index  # what the file is for
    assert "claude/2026-08-17-own-key-01-key-storage" in index


def test_the_index_does_not_grow_with_what_the_records_say(knowledge):
    # The real knowledge is 7 380 lines: a window, not an enclosure. What makes
    # the index affordable is that a record's body never reaches it.
    before = knowledge.index()
    path = knowledge.root / "entities.md"
    path.write_text(path.read_text().replace("аккаунт человека в приложении", "слово " * 2000), encoding="utf-8")

    assert knowledge.index() == before
    assert "Инварианты" not in before


def test_a_block_reaches_the_index_by_its_first_line_and_not_by_its_body(knowledge):
    path = knowledge.root / "entities.md"
    path.write_text(path.read_text().replace("публичный.", "публичный. " + "ещё " * 200), encoding="utf-8")

    line = next(l for l in knowledge.index().splitlines() if "own-key-01" in l)
    assert len(line) < 200


def test_a_project_that_keeps_no_knowledge_says_so_rather_than_breaking(tmp_path):
    none = Knowledge(tmp_path / "docs/knowledge")

    assert none.exists is False
    assert none.blocks() == []
    assert "keeps no knowledge" in none.index()


# --- what the index costs ----------------------------------------------------


def test_the_file_s_own_title_is_not_an_address(knowledge):
    # A block "under `# Сущности`" is a block anywhere in the file.
    assert "entities.md#Сущности" not in knowledge.index()

    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("entities.md#Сущности")

    assert refused.value.code == "no-such-record"


def test_a_block_reaches_the_index_by_what_it_says_not_by_its_header(knowledge):
    # The kind, the date and the run are columns of the index already. Printing
    # the header again inside the glimpse spends the enclosure on itself.
    line = next(l for l in knowledge.index().splitlines() if "own-key-01" in l)

    assert "«Берётся список моделей этим" in line
    assert "**[assumed" not in line


# --- what a careful read of it found -----------------------------------------


def test_a_heading_inside_a_code_fence_is_not_an_address(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK + "\n```md\n### Пример\n`key: sample`\n```\n", encoding="utf-8"
    )

    assert "stack.md#sample" not in knowledge.index()
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("stack.md#sample")

    assert refused.value.code == "no-such-record"


def test_a_quoted_block_inside_a_code_fence_is_not_a_block(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK + "\n```md\n> **[assumed 2026-08-01 · kit/example · id: qqqqqq]** пример\n```\n",
        encoding="utf-8",
    )

    assert "qqqqqq" not in [block.id for block in knowledge.blocks()]


def test_a_file_that_cannot_be_read_is_refused_by_name_not_by_a_stack_trace(knowledge):
    (knowledge.root / "broken.md").write_bytes(b"### \xff\xfe\n")

    with pytest.raises(KnowledgeError) as refused:
        knowledge.index()

    assert refused.value.code == "unreadable-knowledge"
    assert "broken.md" in refused.value.detail


def test_an_address_cannot_climb_out_of_the_knowledge(knowledge):
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("../../../etc/passwd#root")

    assert refused.value.code == "no-such-file"


