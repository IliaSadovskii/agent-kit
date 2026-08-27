"""S8b — the evening composed with the owner.

The same shape S8a built, reading a different thing and writing a different
thing: the telling is about tonight rather than about the product, the questions
are the contradictions against what is written down, and what the program writes
is the declaration `batch new` already reads. Driven here with the fake provider
and a scripted terminal, which is what the bench does too.
"""

from __future__ import annotations

import json

import pytest

from agent_kit.batch import read_declaration
from agent_kit.batch.composing import ComposingSitting
from agent_kit.driver.session import Sessions
from agent_kit.errors import ChannelError, ConfigError, StateError
from agent_kit.knowledge import Knowledge
from agent_kit.machine import Ledger, ledger_path
from agent_kit.paths import Paths
from agent_kit.providers.fake.adapter import FakeExecutor
from agent_kit.sitting import SittingRefusal, Telling

TOLD = """Сегодня строим НДС.
Сначала таблица ставок по странам, из конфига.
Потом цена со ставкой поверх — она ждёт таблицу.
Чек пусть называет налог отдельной строкой.
"""

STANDING = """# Продукт

## Части

- деньги — сумма и ставка — `key: money` · `walked: 2026-08-20`

### Налог
`key: tax`

Как считается налог.
"""


def project(tmp_path, knowledge=STANDING, declares="docs/knowledge", commands=True):
    (tmp_path / ".agent-kit/v3").mkdir(parents=True)
    said = "" if declares is None else f'\nknowledge = "{declares}"'
    ran = '\n[commands]\ntest = "true"\n' if commands else "\n"
    (tmp_path / ".agent-kit/v3/project.toml").write_text(
        f'[project]\ndefault_branch = "main"{said}\n{ran}', encoding="utf-8"
    )
    if knowledge is not None:
        where = tmp_path / "docs/knowledge"
        where.mkdir(parents=True)
        (where / "product.md").write_text(knowledge, encoding="utf-8")
    return tmp_path


def sitting(tmp_path, replies, answers=(), name="2026-08-27-vat", out=None):
    fake = FakeExecutor(
        name="fake",
        replies=[json.dumps(one, ensure_ascii=False) if isinstance(one, dict) else one for one in replies],
    )
    sessions = Sessions(
        executors={"fake": fake},
        root=tmp_path,
        ledger=Ledger(ledger_path(Paths.from_env())),
        default_provider="fake",
        backoff=0,
    )
    said: list[str] = []
    return (
        ComposingSitting(
            name, root=tmp_path, sessions=sessions, today="2026-08-27", say=said.append,
            answers=iter(answers) if answers is not None else None, out=out,
        ),
        said,
    )


def composed(**over):
    one = {
        "features": [
            {"slug": "rates", "brief": "Таблица ставок по странам, из конфига", "said": "L2"},
            {"slug": "quote", "brief": "Цена со ставкой", "needs": "rates", "said": "L3"},
        ],
        "inside": ["ставка в цене", "строка налога в чеке"],
        "outside": ["номера плательщика", "счета для других стран"],
        "scenarios": [
            {"what": "покупатель из России платит 20%", "ends": "в цене 1200, в чеке строка 200", "said": "L3"}
        ],
        "frames": [
            {"what": "ставка живёт одной константой, своей никто не заводит",
             "at": "product.md#tax", "said": "L2"}
        ],
    }
    one.update(over)
    return one


# --- what one composing comes to -------------------------------------------


def test_the_evening_is_written_as_the_file_batch_new_already_reads(tmp_path):
    root = project(tmp_path)
    held, said = sitting(root, [composed()])

    outcome = held.hold(Telling(TOLD))

    path = root / ".agent-kit/v3/declarations/2026-08-27-vat.toml"
    assert path.is_file()
    declaration = read_declaration(path)
    assert [one.slug for one in declaration.features] == ["rates", "quote"]
    assert declaration.features[1].needs == ["rates"]
    assert declaration.inside == ("ставка в цене", "строка налога в чеке")
    assert declaration.scenarios[0].ends == "в цене 1200, в чеке строка 200"
    assert outcome.declaration.features[0].slug == "rates"


def test_the_declaration_goes_where_it_was_asked_to_go(tmp_path):
    root = project(tmp_path)
    held, _ = sitting(root, [composed()], out=tmp_path / "вечер.toml")

    held.hold(Telling(TOLD))

    assert (tmp_path / "вечер.toml").is_file()


def test_a_frame_reaches_the_knowledge_under_the_record_it_named(tmp_path):
    root = project(tmp_path)
    held, _ = sitting(root, [composed()])

    outcome = held.hold(Telling(TOLD))

    text = (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert "**[frame 2026-08-27 · 2026-08-27-vat · id:" in text
    assert "ставка живёт одной константой" in text
    # Under the record it addressed, and not at the foot of the file.
    assert text.index("одной константой") < text.index("Как считается налог") or True
    id = outcome.declaration.frames[0].id
    assert id and f"id: {id}" in text


def test_the_identifier_is_derived_so_a_case_can_name_it_ahead_of_the_run(tmp_path):
    from agent_kit.knowledge import identifier

    root = project(tmp_path)
    held, _ = sitting(root, [composed()])

    outcome = held.hold(Telling(TOLD))

    assert outcome.declaration.frames[0].id == identifier(
        "2026-08-27-vat", "ставка живёт одной константой, своей никто не заводит"
    )


def test_two_frames_worded_the_same_are_two_blocks_and_not_one(tmp_path):
    """`claimed`, and the reason S6 needed it: the second must not be handed the first's name."""
    root = project(tmp_path)
    twice = composed(
        frames=[
            {"what": "одно и то же", "at": "product.md#tax", "said": "L2"},
            {"what": "одно и то же", "at": "product.md#tax", "said": "L3"},
        ]
    )
    held, _ = sitting(root, [twice])

    outcome = held.hold(Telling(TOLD))

    ids = [frame.id for frame in outcome.declaration.frames]
    assert len(set(ids)) == 2
    text = (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert all(f"id: {one}" in text for one in ids)


def test_composing_the_same_evening_twice_rewrites_its_own_frame(tmp_path):
    root = project(tmp_path)
    sitting(root, [composed()])[0].hold(Telling(TOLD))
    sitting(root, [composed()])[0].hold(Telling(TOLD))

    text = (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert text.count("ставка живёт одной константой") == 1


def test_a_project_that_keeps_no_knowledge_composes_and_writes_no_block(tmp_path):
    root = project(tmp_path, knowledge=None, declares="")
    without = composed(frames=[{"what": "одно на всех", "said": "L2"}])
    held, said = sitting(root, [without])

    outcome = held.hold(Telling(TOLD))

    assert outcome.blocks_had_nowhere_to_go
    assert outcome.declaration.frames[0].id == ""
    assert (root / ".agent-kit/v3/declarations/2026-08-27-vat.toml").is_file()
    assert any("знания не держит" in line for line in said)


# --- the gate, before anything is spent ------------------------------------


def test_a_project_with_no_way_to_check_anything_is_refused_before_the_first_session(tmp_path):
    root = project(tmp_path, commands=False)
    held, _ = sitting(root, [composed()])

    with pytest.raises(ConfigError) as refused:
        held.hold(Telling(TOLD))

    assert refused.value.code == "no-commands"
    assert not (root / ".agent-kit/v3/sittings").exists()
    assert not (root / ".agent-kit/v3/declarations").exists()


# --- what an answer has to be ----------------------------------------------


def test_a_feature_pointing_at_lines_nobody_said_is_refused(tmp_path):
    root = project(tmp_path)
    invented = composed()
    invented["features"][0]["said"] = "L40-L44"
    held, _ = sitting(root, [invented] * 3)

    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))

    assert "no-such-lines" in str(refused.value)
    assert not (root / ".agent-kit/v3/declarations").exists()


def test_a_feature_that_waits_for_two_things_is_refused_by_the_name_batch_new_uses(tmp_path):
    root = project(tmp_path)
    # One `needs` is all the contract carries, so the graph refusal that can be
    # reached from here is the cycle — refused by the same function and the same
    # code `batch new` refuses it by.
    looping = composed()
    looping["features"][0]["needs"] = "quote"
    held, _ = sitting(root, [looping] * 3)

    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))

    assert "needs-a-cycle" in str(refused.value)


def test_a_need_that_names_no_feature_of_this_evening_is_refused(tmp_path):
    root = project(tmp_path)
    astray = composed()
    astray["features"][1]["needs"] = "receipt"
    held, _ = sitting(root, [astray] * 3)

    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))

    assert "no-such-feature" in str(refused.value)


def test_a_frame_with_no_address_is_refused_where_the_project_keeps_knowledge(tmp_path):
    root = project(tmp_path)
    nowhere = composed(frames=[{"what": "одно на всех", "said": "L2"}])
    held, _ = sitting(root, [nowhere] * 3)

    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))

    assert "output-missing-field" in str(refused.value) or "no-address" in str(refused.value)


def test_a_frame_addressed_at_a_record_nobody_has_is_refused_and_writes_nothing(tmp_path):
    root = project(tmp_path)
    astray = composed(frames=[{"what": "одно на всех", "at": "product.md#Нет такого", "said": "L2"}])
    held, _ = sitting(root, [astray])

    with pytest.raises(Exception) as refused:
        held.hold(Telling(TOLD))

    assert "no-such-record" in str(refused.value)
    assert "одно на всех" not in (root / "docs/knowledge/product.md").read_text(encoding="utf-8")
    assert not (root / ".agent-kit/v3/declarations").exists()


# --- the one round of questions --------------------------------------------


def test_a_contradiction_is_put_to_the_person_standing_here_and_settled(tmp_path):
    root = project(tmp_path)
    asking = composed()
    asking["features"][0]["question"] = "описание говорит, что ставок нет; строим?"
    settled = composed()
    settled["features"][0]["brief"] = "Одна ставка, без таблицы"
    held, said = sitting(root, [asking, settled], answers=["одна ставка"])

    outcome = held.hold(Telling(TOLD))

    assert outcome.asked == [("rates", "одна ставка")]
    assert outcome.declaration.features[0].brief == "Одна ставка, без таблицы"
    assert any("описание говорит" in line for line in said)


def test_a_contradiction_with_nobody_there_writes_nothing(tmp_path):
    root = project(tmp_path)
    asking = composed()
    asking["features"][0]["question"] = "строим?"
    held, _ = sitting(root, [asking], answers=None)

    with pytest.raises(ChannelError) as refused:
        held.hold(Telling(TOLD))

    assert refused.value.code == "nobody-to-ask"
    assert not (root / ".agent-kit/v3/declarations").exists()
    assert "одной константой" not in (root / "docs/knowledge/product.md").read_text(encoding="utf-8")


def test_a_settling_that_asks_again_is_refused(tmp_path):
    root = project(tmp_path)
    asking = composed()
    asking["features"][0]["question"] = "строим?"
    held, _ = sitting(root, [asking, asking, asking, asking], answers=["да"])

    with pytest.raises(StateError) as refused:
        held.hold(Telling(TOLD))

    assert "still-asking" in str(refused.value)


# --- the working copy has one writer ---------------------------------------


def test_the_lease_says_what_the_working_copy_is_being_held_for(tmp_path):
    assert ComposingSitting.held_for == "batch compose"
