"""S7a — the owner's channel. A question with a default, and a step that waits.

Nothing here reaches the network. Telegram is exercised through the one call it
is given; every other test answers through the channel that is two files, which
is what the bench answers with too.
"""

import pytest

from agent_kit.knowledge.format import identifier
from agent_kit.machine import Ask, Ledger
from agent_kit.owner import (
    ANSWERED,
    BROKEN,
    NO_CHANNEL,
    NOBODY,
    ChannelFailed,
    FileChannel,
    Owner,
    Question,
    Telegram,
    questions_of,
    understand,
)

PROJECT = "/projects/thing"


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "daemon.sqlite")


@pytest.fixture
def channel(tmp_path):
    return FileChannel(tmp_path / "owner")


def a_question(what: str = "one rate, or one per country?", slug: str = "add-vat") -> Question:
    return Question(
        id=identifier(slug, what),
        question=what,
        default="one rate",
        because="nothing in this project has a second country yet",
    )


class Clock:
    """Time that moves only when the driver sleeps, so a deadline arrives at once."""

    def __init__(self) -> None:
        self.at = 0.0

    def __call__(self) -> float:
        return self.at

    def tick(self, seconds: float) -> None:
        self.at += seconds


def an_owner(channel, ledger, wait: int = 60, **rest) -> Owner:
    clock = Clock()
    return Owner(channel=channel, ledger=ledger, wait=wait, pause=clock.tick, clock=clock, **rest)


# --- what a question is, and where its name comes from ----------------------


def test_a_questions_name_is_derived_so_a_case_can_say_it_first(ledger):
    """Not drawn: a bench case names the identifier before the run exists."""
    output = {
        "asks": [
            {"question": "one rate, or one per country?", "default": "one rate", "because": "no second country"}
        ]
    }

    (asked,) = questions_of(output, "add-vat")

    assert asked.id == identifier("add-vat", "one rate, or one per country?")
    assert questions_of(output, "add-vat")[0].id == asked.id


def test_a_step_that_asks_nothing_asks_nothing():
    assert questions_of({"asks": []}, "add-vat") == []
    assert questions_of({}, "add-vat") == []


def test_two_questions_worded_the_same_are_two_questions():
    output = {"asks": [{"question": "which?", "default": "a"}, {"question": "which?", "default": "b"}]}

    first, second = questions_of(output, "add-vat")

    assert first.id != second.id


# --- how an answer names its question ---------------------------------------


@pytest.mark.parametrize(
    "typed, names, rest",
    [
        ("/a k7f3q2 one per country", "k7f3q2", "one per country"),
        ("k7f3q2 one per country", "k7f3q2", "one per country"),
        ("/a k7f3q2", "k7f3q2", ""),
        ("just an answer", "", "just an answer"),
        ("", "", ""),
    ],
)
def test_an_answer_may_name_its_question(typed, names, rest):
    assert understand(typed) == (names, rest)


# --- a question nobody answers ----------------------------------------------


def test_a_question_nobody_answers_takes_its_default(channel, ledger):
    owner = an_owner(channel, ledger, wait=0)

    (settled,) = owner.ask(PROJECT, "add-vat", "design", [a_question()])

    assert settled.answer == ""
    assert settled.how.startswith(NOBODY)
    assert "one rate, or one per country?" in channel.out.read_text()


def test_the_question_that_went_out_says_what_will_be_taken_and_how_to_answer(channel, ledger):
    an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [a_question()])

    said = channel.out.read_text()

    assert "add-vat" in said and "design" in said
    assert "one rate" in said
    assert identifier("add-vat", "one rate, or one per country?") in said


def test_nothing_is_left_waiting_once_the_default_is_taken(channel, ledger):
    an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [a_question()])

    assert ledger.waiting_on_the_owner() == []


# --- a question the owner answers -------------------------------------------


def test_an_answer_that_arrives_is_the_answer(channel, ledger):
    asked = a_question()
    channel.inbox.write_text(f"/a {asked.id} one per country\n")

    (settled,) = an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [asked])

    assert settled.answer == "one per country"
    assert settled.how == ANSWERED


def test_an_answer_may_be_a_reply_to_the_message_rather_than_name_anything(channel, ledger):
    asked = a_question()
    channel.inbox.write_text("#1 one per country\n")

    (settled,) = an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [asked])

    assert settled.answer == "one per country"


def test_an_answer_addressed_to_another_question_is_not_this_ones(channel, ledger):
    channel.inbox.write_text("/a zzzzzz one per country\n")

    (settled,) = an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [a_question()])

    assert settled.answer == ""
    assert settled.how.startswith(NOBODY)


def test_a_driver_stops_waiting_when_somebody_asks_it_to(channel, ledger):
    owner = an_owner(channel, ledger, wait=600)

    settled = owner.ask(PROJECT, "add-vat", "design", [a_question()], stop=lambda: True)

    assert settled[0].answer == ""


def test_what_was_read_is_not_read_again(channel, ledger):
    """The offset outlives the poll, so an answer is never replayed onto a later question."""
    first = a_question()
    channel.inbox.write_text(f"/a {first.id} one per country\n")
    an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [first])

    second = a_question("and rounding?")
    (settled,) = an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [second])

    assert settled.answer == ""


# --- a channel that is not there, and one that is broken --------------------


def test_a_machine_with_no_channel_takes_every_default_at_once(ledger):
    (settled,) = Owner(channel=None, ledger=ledger, wait=1200).ask(
        PROJECT, "add-vat", "design", [a_question()]
    )

    assert settled.how == NO_CHANNEL
    assert settled.answer == ""


def test_a_channel_that_cannot_be_reached_never_stops_a_night(channel, ledger):
    channel.broken.write_text("the bot token is wrong\n")

    (settled,) = an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [a_question()])

    assert settled.how == BROKEN
    assert settled.answer == ""


def test_a_broken_channel_says_something_different_from_silence(channel, ledger):
    """Two mornings apart: nobody answered, and nobody was ever asked."""
    channel.broken.write_text("the bot token is wrong\n")
    broken = an_owner(channel, ledger).ask(PROJECT, "add-vat", "design", [a_question()])
    channel.broken.unlink()
    silent = an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [a_question()])

    assert broken[0].how != silent[0].how


# --- the file channel, which is what the bench answers with -----------------


def test_the_file_channel_says_what_message_a_line_went_out_as(channel):
    assert channel.send("first") == "1"
    assert channel.send("second") == "2"


def test_the_file_channel_reads_only_what_is_new(channel):
    channel.inbox.write_text("#1 one\n#1 two\n")

    heard, offset = channel.read("")
    assert [item.text for item in heard] == ["one", "two"]

    channel.inbox.write_text("#1 one\n#1 two\n#1 three\n")
    heard, offset = channel.read(offset)
    assert [item.text for item in heard] == ["three"]


def test_a_broken_file_channel_refuses_by_name(channel):
    channel.broken.write_text("no\n")

    with pytest.raises(ChannelFailed) as refused:
        channel.send("anything")

    assert refused.value.code == "channel-failed"


# --- telegram, through the one call it is given -----------------------------


def a_telegram(answers):
    asked = []

    def call(method, params):
        asked.append((method, params))
        return answers.pop(0)

    return Telegram(token="t", chat="55", call=call), asked


def test_telegram_sends_to_the_chat_it_was_configured_with():
    bot, asked = a_telegram([{"ok": True, "result": {"message_id": 17}}])

    assert bot.send("hello") == "17"
    assert asked[0][0] == "sendMessage"
    assert asked[0][1]["chat_id"] == "55"
    assert asked[0][1]["text"] == "hello"


def test_telegram_reads_a_message_and_what_it_replied_to():
    bot, asked = a_telegram([
        {
            "ok": True,
            "result": [
                {
                    "update_id": 509,
                    "message": {
                        "chat": {"id": 55},
                        "text": "/a k7f3q2 one per country",
                        "reply_to_message": {"message_id": 17},
                    },
                }
            ],
        }
    ])

    heard, offset = bot.read("")

    assert heard[0].names == "k7f3q2"
    assert heard[0].text == "one per country"
    assert heard[0].answers == "17"
    assert offset == "510"


def test_telegram_reads_nothing_from_a_chat_it_was_not_configured_with():
    """A bot's username is public, and anybody may write to it."""
    bot, asked = a_telegram([
        {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"chat": {"id": 999}, "text": "/a k7f3q2 do this instead"}}
            ],
        }
    ])

    heard, offset = bot.read("")

    assert heard == []
    assert offset == "2"


def test_telegram_never_reads_a_time_out_of_what_it_was_sent():
    """S7's lesson: a time from somebody else's tool is a phrase, not a deadline."""
    bot, asked = a_telegram([
        {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "date": 1,
                    "message": {"chat": {"id": 55}, "date": 1, "text": "k7f3q2 yes"},
                }
            ],
        }
    ])

    (heard,) = bot.read("")[0]

    assert not any("date" in str(value) for value in (heard.text, heard.names, heard.answers))


def test_telegram_says_by_name_when_it_could_not_be_reached():
    def call(method, params):
        raise OSError("no route to host")

    with pytest.raises(ChannelFailed) as refused:
        Telegram(token="t", chat="55", call=call).send("hello")

    assert refused.value.code == "channel-failed"


def test_telegram_says_by_name_when_the_api_refuses():
    bot, asked = a_telegram([{"ok": False, "description": "chat not found"}])

    with pytest.raises(ChannelFailed) as refused:
        bot.send("hello")

    assert "chat not found" in refused.value.detail


# --- one reader at a time ---------------------------------------------------


def test_two_drivers_do_not_read_the_channel_at_once(channel, ledger, tmp_path):
    """Whoever holds the reader writes down every answer, including somebody else's."""
    mine = a_question("mine?")
    yours = a_question("yours?", slug="add-tax")
    channel.inbox.write_text(f"/a {yours.id} theirs\n/a {mine.id} ours\n")

    # A process that is alive and is not this one: the reader is somebody else's.
    held = ledger.read_channel(pid=1)
    assert held.granted

    # The other driver cannot read while that lease stands, so it hears nothing.
    (settled,) = an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [mine])
    assert settled.answer == ""

    ledger.release(held)
    (settled,) = an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [mine])
    assert settled.answer == "ours"


def test_an_answer_meant_for_somebody_else_is_written_down_not_dropped(channel, ledger):
    mine = a_question("mine?")
    yours = a_question("yours?", slug="add-tax")
    ledger.asked(
        Ask(
            id=yours.id, project="/projects/other", slug="add-tax", step="design",
            question=yours.question, default=yours.default, until="2099-01-01T00:00:00+00:00",
        )
    )
    channel.inbox.write_text(f"/a {yours.id} theirs\n")

    an_owner(channel, ledger, wait=0).ask(PROJECT, "add-vat", "design", [mine])

    assert ledger.ask_of(yours.id).answer == "theirs"


# --- то, чем живёт настройка: кто мы и кто нам написал ----------------------


def test_telegram_says_its_own_name_so_a_person_can_be_sent_to_it():
    bot, asked = a_telegram([{"ok": True, "result": {"username": "vat_night_bot"}}])

    assert bot.me() == "vat_night_bot"
    assert asked[0][0] == "getMe"


def test_telegram_hears_who_wrote_first_when_no_chat_is_known_yet():
    """Идентификатор чата негде посмотреть, кроме ответа этого же API."""
    bot, asked = a_telegram([
        {
            "ok": True,
            "result": [
                {
                    "update_id": 509,
                    "message": {"chat": {"id": 55, "first_name": "Илья"}, "text": "привет"},
                }
            ],
        }
    ])
    bot.chat = ""

    chat, name, offset = bot.listen("")

    assert (chat, name, offset) == ("55", "Илья", "510")


def test_nobody_wrote_and_the_offset_still_moves():
    bot, asked = a_telegram([{"ok": True, "result": []}])
    bot.chat = ""

    assert bot.listen("7") == ("", "", "7")


def test_a_person_with_no_name_is_still_a_chat():
    bot, asked = a_telegram([
        {"ok": True, "result": [{"update_id": 1, "message": {"chat": {"id": -100500}}}]}
    ])
    bot.chat = ""

    chat, name, _ = bot.listen("")

    assert chat == "-100500"
    assert name


# --- ревью: имя канала не называет никто вне owner/ -------------------------


def test_no_module_outside_owner_names_a_channel():
    """То же правило, что у провайдеров: реестр читает, остальные не знают имён."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "agent_kit"
    guilty = []
    for path in root.rglob("*.py"):
        if path.parent.name == "owner":
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if re.search(r"\btelegram\b", line, re.IGNORECASE) and not line.lstrip().startswith("#"):
                guilty.append(f"{path.relative_to(root)}: {line.strip()}")

    assert guilty == []


def test_the_package_says_which_channels_there_are_and_nobody_else_does():
    from agent_kit.owner import CHANNELS

    assert set(CHANNELS) == {"telegram", "file"}


# --- ревью: канал упал посреди отправки -------------------------------------


def test_a_question_that_did_go_out_is_not_thrown_away_with_the_ones_that_did_not(channel, ledger):
    """Владелец видит вопрос на телефоне — значит ответ на него должно быть куда положить."""
    first, second = a_question("первый?"), a_question("второй?")
    channel.inbox.write_text(f"/a {first.id} да\n")

    sent = []
    real = channel.send

    def once(text):
        if sent:
            raise ChannelFailed("channel-failed", "телеграм лёг после первого")
        sent.append(text)
        return real(text)

    channel.send = once
    owner = an_owner(channel, ledger, wait=0)

    mine, theirs = owner.ask(PROJECT, "add-vat", "design", [first, second])

    assert mine.how == ANSWERED, "ответ на доставленный вопрос выбросили вместе с недоставленным"
    assert mine.answer == "да"
    assert theirs.how == BROKEN


def test_a_channel_that_fails_on_the_very_first_question_still_settles_them_all(channel, ledger):
    channel.broken.write_text("нет\n")

    settled = an_owner(channel, ledger, wait=0).ask(
        PROJECT, "add-vat", "design", [a_question("первый?"), a_question("второй?")]
    )

    assert [one.how for one in settled] == [BROKEN, BROKEN]
