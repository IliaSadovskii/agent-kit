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




# --- what the review round found ---------------------------------------------


def test_two_blocks_with_nothing_between_them_are_two_blocks(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK
        + "\n> **[assumed 2026-08-01 · kit/one · id: aaaaaa]** первый\n"
        + "> **[assumed 2026-08-02 · kit/two · id: bbbbbb]** второй\n",
        encoding="utf-8",
    )

    assert [block.id for block in knowledge.blocks() if block.file == "stack.md"] == ["aaaaaa", "bbbbbb"]


def test_two_blocks_split_by_a_bare_quote_line_are_two_blocks(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK
        + "\n> **[assumed 2026-08-01 · kit/one · id: aaaaaa]** первый\n"
        + ">\n"
        + "> **[assumed 2026-08-02 · kit/two · id: bbbbbb]** второй\n",
        encoding="utf-8",
    )

    assert [block.id for block in knowledge.blocks() if block.file == "stack.md"] == ["aaaaaa", "bbbbbb"]


def test_closing_the_first_of_two_touching_blocks_leaves_the_second(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK
        + "\n> **[assumed 2026-08-01 · kit/one · id: aaaaaa]** первый\n"
        + "> **[assumed 2026-08-02 · kit/two · id: bbbbbb]** второй\n",
        encoding="utf-8",
    )

    knowledge.close("aaaaaa")

    text = (knowledge.root / "stack.md").read_text()
    assert "первый" not in text
    assert "второй" in text


def test_a_block_indented_under_a_list_item_is_still_a_block(knowledge):
    (knowledge.root / "stack.md").write_text(
        STACK + "\n- пункт\n\n  > **[assumed 2026-08-01 · kit/one · id: aaaaaa]** внутри списка\n",
        encoding="utf-8",
    )

    assert "aaaaaa" in [block.id for block in knowledge.blocks()]


def test_a_file_that_is_not_part_of_the_knowledge_is_not_addressable(knowledge):
    # `.md` is what `files()` reads, so a block written anywhere else could
    # never be found again: not by the index, not by `close`, not by `free_id`.
    (knowledge.root / "notes.txt").write_text("### Заметка\n", encoding="utf-8")

    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("notes.txt#Заметка")

    assert refused.value.code == "no-such-file"


def test_moving_a_block_to_another_file_reports_both_files(knowledge):
    written(knowledge)

    touched = knowledge.write(
        at="stack.md#Вызовы модели", run="kit/add-vat", body="то же самое",
        id=identifier("add-vat", "the rate is a whole percent"), date="2026-08-22",
    )

    names = sorted(path.name for path in touched)
    assert names == ["entities.md", "stack.md"]
    assert "kit/add-vat" not in (knowledge.root / "entities.md").read_text()


def test_a_file_that_ended_in_a_blank_line_still_does(knowledge):
    path = knowledge.root / "stack.md"
    path.write_text(STACK + "\n", encoding="utf-8")  # a trailing blank line of its own

    written(knowledge, at="stack.md#Вызовы модели")
    knowledge.close(identifier("add-vat", "the rate is a whole percent"))

    assert path.read_text().endswith("`down()`.\n\n")


def test_closing_a_block_at_the_head_of_a_file_leaves_no_blank_line_above(knowledge):
    path = knowledge.root / "opening.md"
    path.write_text("> **[assumed 2026-08-01 · kit/one · id: aaaaaa]** первый\n\n## Раздел\n\nтело\n",
                    encoding="utf-8")

    knowledge.close("aaaaaa")

    assert path.read_text().startswith("## Раздел")


def test_the_identifier_is_pinned_to_a_value_and_not_only_to_itself():
    """A silent change of alphabet, length or seed turns over every block in

    every project's knowledge, and no test comparing a call to another call in
    the same process would notice.
    """
    assert identifier("add-vat", "the rate is a whole percent") == "kmw26z"
    assert identifier("add-vat", "the rate is a whole percent", salt=1) == "2zgszb"


# --- what the parser was reading that is not there ---------------------------

#: What the second version's templates ship, and all six of them ship it: the
#: example record lives inside an HTML comment, so a project that has started
#: its knowledge and not filled it in has a `key:` no renderer ever shows.
TEMPLATE = """<!--
Сущности — то, что живёт дольше одного вызова.
-->

# Сущности

<!--
### Оффер
`key: offer`

**Что это:** ответ разработчика на запрос покупателя

> **[assumed 2026-08-01 · kit/example · id: cmmmm7]** пример блока, а не блок
-->

### Деньги
`key: money`

**Что это:** сумма в копейках
"""


def test_a_record_inside_a_comment_is_not_an_address(knowledge):
    (knowledge.root / "entities.md").write_text(TEMPLATE, encoding="utf-8")

    assert "entities.md#offer" not in knowledge.index()
    assert "offer" not in [anchor.anchor for anchor in knowledge.anchors()]
    with pytest.raises(KnowledgeError) as refused:
        knowledge.resolve("entities.md#offer")

    assert refused.value.code == "no-such-record"


def test_a_block_inside_a_comment_is_not_a_block(knowledge):
    (knowledge.root / "entities.md").write_text(TEMPLATE, encoding="utf-8")

    assert "cmmmm7" not in [block.id for block in knowledge.blocks()]


def test_what_stands_below_a_closed_comment_is_read(knowledge):
    (knowledge.root / "entities.md").write_text(TEMPLATE, encoding="utf-8")

    assert "money" in [anchor.anchor for anchor in knowledge.anchors()]


def test_a_comment_that_opens_and_closes_on_one_line_hides_only_itself(knowledge):
    """The real knowledge has four of these, and none of them ends a file."""
    (knowledge.root / "stack.md").write_text(
        STACK + "\n<!-- ниже — чем это меряется -->\n\n## Чем меряем\n\nодной командой.\n",
        encoding="utf-8",
    )

    assert "Чем меряем" in [anchor.anchor for anchor in knowledge.anchors()]
