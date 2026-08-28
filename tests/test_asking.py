"""S7a in the driver — a step that asks, waits, and goes on either way.

The whole of the step, measured where it matters: an answer changes what gets
built, and silence costs the night twenty minutes and a block in the knowledge.
Nothing here opens a socket: the channel is two files, which is what the bench
answers with too.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.knowledge.format import identifier
from agent_kit.machine import Ledger
from agent_kit.owner import FileChannel, Owner
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStatus, RunStore, StepStatus
from agent_kit.steps import builtin_registry
from agent_kit.steps.contract import parse_output

QUESTION = "one rate, or one per country?"


def design(asks=None, **rest):
    held = {
        "title": "Money learns a VAT rate",
        "summary": "Money learns a VAT rate, so a price can be quoted with tax.",
        "changes": ["money.py — a RATE beside the amount"],
        "seams": ["AMOUNT keeps its meaning: the price before tax"],
        "proves": [],
        "asks": asks if asks is not None else [],
        "assumptions": [],
    }
    held.update(rest)
    return "```json\n" + json.dumps(held) + "\n```"


ONE_QUESTION = [
    {
        "question": QUESTION,
        "default": "one rate",
        "because": "nothing in this project has a second country yet",
    }
]


class Clock:
    def __init__(self):
        self.at = 0.0

    def __call__(self):
        return self.at

    def tick(self, seconds):
        self.at += seconds


def machine(tmp_path, wait=60, channel=True):
    ledger = Ledger(tmp_path / "daemon.sqlite")
    clock = Clock()
    owner = Owner(
        channel=FileChannel(tmp_path / "owner") if channel else None,
        ledger=ledger,
        wait=wait,
        pause=clock.tick,
        clock=clock,
    )
    return ledger, owner


def runner(tmp_path, replies, wait=60, channel=True):
    # These runs are about the owner's twenty minutes, not about a description.
    # Since S8a a run carrying `design` is asked what its project says about
    # being described, and a project that says nothing at all is refused before
    # the first session — so this one says it is not being described.
    (tmp_path / ".agent-kit/v3").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent-kit/v3/project.toml").write_text(
        '[project]\nknowledge = ""\n', encoding="utf-8"
    )
    store = RunStore(tmp_path)
    create_run(
        store, builtin_registry(), "add-vat", steps=["design"], project=str(tmp_path),
        brief="Money should quote a price with VAT",
    )
    ledger, owner = machine(tmp_path, wait=wait, channel=channel)
    return (
        StepRunner(
            store=store,
            registry=builtin_registry(),
            executors={"fake": FakeExecutor(name="fake", replies=replies)},
            default_provider="fake",
            ledger=ledger,
            owner=owner,
        ),
        store,
        owner,
    )


def step_dir(tmp_path):
    return tmp_path / ".agent-kit/v3/runs/add-vat/steps/0-design"


# --- nobody answers ---------------------------------------------------------


def test_a_question_nobody_answers_takes_its_default_and_the_run_goes_on(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    outcome = run_step.run_next("add-vat")

    assert outcome.passed
    assert store.load("add-vat").status is RunStatus.DONE
    assert QUESTION in (tmp_path / "owner.out").read_text()


def test_the_default_becomes_an_expensive_assumption_in_the_steps_own_output(tmp_path):
    """A shape the rest of the kit already reads: record writes it, deliver prints it."""
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    (assumed,) = json.loads((step_dir(tmp_path) / "output.json").read_text())["assumptions"]
    assert assumed["expensive"] is True
    assert "one rate" in assumed["what"]
    assert "владельца" in assumed["because"]


def test_what_the_model_actually_said_is_still_there_untouched(tmp_path):
    """The driver writes into the output; raw.txt is why that stays honest."""
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    raw = parse_output((step_dir(tmp_path) / "attempt-1" / "raw.txt").read_text())
    assert raw["assumptions"] == []


def test_the_step_ran_once_because_nobody_answered(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    assert store.load("add-vat").steps[0].attempts == 1


def test_what_became_of_every_question_is_written_beside_the_step(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    held = json.loads((step_dir(tmp_path) / "asks.json").read_text())
    assert held["rounds"] == 1
    assert held["settled"][0]["how"] == "nobody-answered"
    assert held["settled"][0]["id"] == identifier("add-vat", QUESTION)


# --- the owner answers ------------------------------------------------------


def test_an_answer_runs_the_step_again_with_what_they_said_enclosed(tmp_path):
    (tmp_path / "owner.in").write_text(f"/a {identifier('add-vat', QUESTION)} one per country\n")
    run_step, store, owner = runner(
        tmp_path, [design(asks=ONE_QUESTION), design(summary="One rate per country, as asked.")]
    )

    outcome = run_step.run_next("add-vat")

    assert outcome.passed
    assert outcome.output["summary"] == "One rate per country, as asked."
    assert store.load("add-vat").steps[0].attempts == 2
    assert "one per country" in (step_dir(tmp_path) / "attempt-2" / "input.md").read_text()


def test_an_answered_question_leaves_no_assumption_behind(tmp_path):
    """Nobody had to take a default, so nothing was assumed."""
    (tmp_path / "owner.in").write_text(f"/a {identifier('add-vat', QUESTION)} one per country\n")
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION), design()])

    run_step.run_next("add-vat")

    assert json.loads((step_dir(tmp_path) / "output.json").read_text())["assumptions"] == []


def test_the_same_question_asked_again_is_not_sent_twice(tmp_path):
    """One round per step. A second round is a conversation, and handovers here are files."""
    (tmp_path / "owner.in").write_text(f"/a {identifier('add-vat', QUESTION)} one per country\n")
    run_step, store, owner = runner(
        tmp_path, [design(asks=ONE_QUESTION), design(asks=ONE_QUESTION)]
    )

    outcome = run_step.run_next("add-vat")

    assert outcome.passed
    assert (tmp_path / "owner.out").read_text().count(QUESTION) == 1
    assert store.load("add-vat").steps[0].attempts == 2


# --- the state of a step that is waiting ------------------------------------


def test_a_step_that_is_waiting_says_so_in_the_run(tmp_path):
    """Waiting is a state of the step, not a sentence in a log."""
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=600)
    seen = []

    class Watched(FileChannel):
        def read(self, offset):
            seen.append(store.load("add-vat").steps[0].status)
            return super().read(offset)

    owner.channel = Watched(tmp_path / "owner")
    (tmp_path / "owner.in").write_text(f"/a {identifier('add-vat', QUESTION)} one per country\n")
    run_step.run_next("add-vat")

    assert seen == [StepStatus.ASKING]


def test_a_stop_reaches_a_run_that_is_waiting_for_a_person(tmp_path):
    """The run somebody most wants stopped is the one that is stuck."""
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=600)

    class Interrupted(FileChannel):
        """A person typing `run stop` from another terminal while the run waits."""

        def read(self, offset):
            run_step.ledger.ask_stop(str(tmp_path), "add-vat", "the owner said so")
            return super().read(offset)

    owner.channel = Interrupted(tmp_path / "owner")
    outcome = run_step.run_next("add-vat")

    assert outcome.interrupted
    run = store.load("add-vat")
    assert run.status is RunStatus.STOPPED
    assert "stopped-by-request" in run.reason
    assert run.steps[0].status is StepStatus.PENDING


# --- a machine with no channel ----------------------------------------------


def test_a_machine_with_no_channel_is_not_slower_by_a_second(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=1200, channel=False)

    outcome = run_step.run_next("add-vat")

    assert outcome.passed
    held = json.loads((step_dir(tmp_path) / "asks.json").read_text())
    assert held["settled"][0]["how"] == "no-channel"


def test_a_channel_that_cannot_be_reached_says_something_else(tmp_path):
    (tmp_path / "owner.fail").write_text("the bot token is wrong\n")
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)])

    outcome = run_step.run_next("add-vat")

    assert outcome.passed
    held = json.loads((step_dir(tmp_path) / "asks.json").read_text())
    assert held["settled"][0]["how"] == "channel-failed"


# --- news -------------------------------------------------------------------


def test_a_run_that_ends_says_so_without_anybody_opening_a_terminal(tmp_path):
    run_step, store, owner = runner(tmp_path, [design()], wait=0)
    assert not (tmp_path / "owner.out").exists()

    run_step.run_next("add-vat")

    said = (tmp_path / "owner.out").read_text()
    assert "add-vat" in said and "done" in said


def test_a_question_the_owner_answered_stops_standing_in_the_design(tmp_path):
    """It is settled, not defaulted: the pull request must not still want it."""
    (tmp_path / "owner.in").write_text(f"/a {identifier('add-vat', QUESTION)} one per country\n")
    run_step, store, owner = runner(
        tmp_path, [design(asks=ONE_QUESTION), design(asks=ONE_QUESTION)]
    )

    run_step.run_next("add-vat")

    assert json.loads((step_dir(tmp_path) / "output.json").read_text())["asks"] == []


# --- ревью: умолчание, взятое и забытое ------------------------------------


TWO_QUESTIONS = [
    {"question": QUESTION, "default": "one rate", "because": "нет второй страны"},
    {"question": "round the tax up or down?", "default": "down", "because": "так считает касса"},
]


def answers_in(tmp_path, *pairs):
    (tmp_path / "owner.in").write_text(
        "".join(f"/a {identifier('add-vat', question)} {answer}\n" for question, answer in pairs)
    )


def assumptions(tmp_path):
    return json.loads((step_dir(tmp_path) / "output.json").read_text())["assumptions"]


def settled(tmp_path):
    return {item["id"]: item for item in json.loads((step_dir(tmp_path) / "asks.json").read_text())["settled"]}


def test_two_questions_one_answered_and_the_other_default_is_still_written_down(tmp_path):
    """Ради этого весь шаг и написан: умолчание, взятое и забытое, невозможно."""
    answers_in(tmp_path, (QUESTION, "one per country"))
    run_step, store, owner = runner(
        tmp_path, [design(asks=TWO_QUESTIONS), design(asks=TWO_QUESTIONS)]
    )

    run_step.run_next("add-vat")

    taken = [item for item in assumptions(tmp_path) if "round the tax up" in item["what"]]
    assert taken, "умолчание неотвеченного вопроса не попало в допущения"
    assert taken[0]["expensive"] is True


def test_a_question_the_second_design_forgot_is_still_written_down(tmp_path):
    """Обычный случай: на часть ответили, и вторая попытка про остальное молчит."""
    answers_in(tmp_path, (QUESTION, "one per country"))
    run_step, store, owner = runner(tmp_path, [design(asks=TWO_QUESTIONS), design(asks=[])])

    run_step.run_next("add-vat")

    assert [item for item in assumptions(tmp_path) if "round the tax up" in item["what"]]


def test_an_answer_survives_a_driver_that_died_before_it_could_be_used(tmp_path):
    """Ответ лежит в asks.json, и следующий драйвер читает оттуда не только номер круга."""
    answers_in(tmp_path, (QUESTION, "one per country"))
    run_step, store, owner = runner(
        tmp_path, [design(asks=ONE_QUESTION), design(asks=ONE_QUESTION), design()]
    )
    # Первый круг целиком, потом драйвер «умирает»: шаг возвращается в pending.
    run_step.owner.channel = None
    store.start_step("add-vat", provider="fake")
    store.ask_step("add-vat", "design is asking the owner one thing")
    run_step.store.answered("add-vat", "the owner answered one thing")
    workspace = step_dir(tmp_path)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "asks.json").write_text(json.dumps({
        "rounds": 1,
        "settled": [{
            "id": identifier("add-vat", QUESTION), "question": QUESTION, "default": "one rate",
            "because": "нет второй страны", "at": "", "block": "",
            "how": "answered", "answer": "one per country", "detail": "", "when": "2026-08-24T12:00:00+00:00",
        }],
    }))

    run_step.run_next("add-vat")

    said = (step_dir(tmp_path) / f"attempt-{store.load('add-vat').steps[0].attempts}" / "input.md").read_text()
    assert "one per country" in said, "ответ владельца не вложили в новую сессию"
    assert not [item for item in assumptions(tmp_path) if "ответа не было" in item.get("because", "")]


def test_a_stop_while_waiting_does_not_spend_the_owners_round(tmp_path):
    """Человек остановил ночь, чтобы ответить. Утром его обязаны спросить снова."""
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=600)

    class Interrupted(FileChannel):
        def read(self, offset):
            run_step.ledger.ask_stop(str(tmp_path), "add-vat", "сейчас отвечу")
            return super().read(offset)

    owner.channel = Interrupted(tmp_path / "owner")
    run_step.run_next("add-vat")

    held = json.loads((step_dir(tmp_path) / "asks.json").read_text()) if (step_dir(tmp_path) / "asks.json").exists() else {"rounds": 0}
    assert held["rounds"] == 0, "прерванный круг засчитали как потраченный"


def test_a_question_nobody_was_asked_says_so_and_not_that_nobody_answered(tmp_path):
    """Пятая концовка, и у неё свой код: сообщение не уходило вовсе."""
    answers_in(tmp_path, (QUESTION, "one per country"))
    later = [{"question": "and negative rates?", "default": "refuse", "because": "остальное так же"}]
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION), design(asks=later)])

    run_step.run_next("add-vat")

    fresh = settled(tmp_path)[identifier("add-vat", "and negative rates?")]
    assert fresh["how"] == "had-their-round"
    (taken,) = [item for item in assumptions(tmp_path) if "negative rates" in item["what"]]
    assert "не спрашивали" in taken["because"]
    assert "ответа не было" not in taken["because"]


def test_every_reason_is_one_sentence_and_not_two_glued_together(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    (taken,) = assumptions(tmp_path)
    assert "ответа не было у владельца" not in taken["because"]
    assert taken["because"].count(";") <= 1


def test_asks_json_says_when_each_question_was_settled(tmp_path):
    run_step, store, owner = runner(tmp_path, [design(asks=ONE_QUESTION)], wait=0)

    run_step.run_next("add-vat")

    (one,) = settled(tmp_path).values()
    assert one["when"].startswith("20")
