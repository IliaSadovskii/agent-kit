"""A question with a default, the twenty minutes it waits, and what it becomes.

The shape S7a settles: a step's contract may declare `asks`, the driver reads
the field, sends the questions and waits. An answer sends the step back to be
run again with what the owner said enclosed. A question nobody answered folds
into the step's own output as an expensive assumption — which is a thing this
kit already knows what to do with, so `record` writes it into the knowledge and
`deliver` prints it in the open half of the pull request, and neither of them
learns anything new.

Every path ends with the run going on. That is what `default` being required
buys: a question with no default is not a question, it is a step refusing to
finish, and the contract refuses it by name.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any, Callable

from ..knowledge.format import identifier
from ..logs import get_logger
from ..machine import Ask, Ledger
from .channel import Channel, ChannelFailed

#: How often the channel is polled while a step is asking. Not once a second:
#: a person is not a ledger, and every poll is somebody else's service.
POLL = 5.0

#: How a question ended, as a code rather than a sentence. Prose is reworded and
#: a judge that reads one measures the sentence; these four are what a bench
#: case, `run show` and a person reading a record in the morning all compare.
ANSWERED = "answered"
NOBODY = "nobody-answered"
BROKEN = "channel-failed"
NO_CHANNEL = "no-channel"
#: Спросить было можно, но не стали: у владельца уже был круг в этом прогоне.
#: Пятый исход, и у него свой код, потому что запись «никто не ответил» про
#: сообщение, которое не отправляли, — это неправда в знании владельца.
HAD_ROUND = "had-their-round"

log = get_logger("owner")


@dataclass(frozen=True)
class Question:
    """One thing only the owner can settle, and what is taken if they do not.

    `at` and `block` are what a project that keeps knowledge asks for, through
    the same mechanism that makes an expensive assumption owe a block: the
    default, once taken, is exactly such an assumption.
    """

    id: str
    question: str
    default: str
    because: str = ""
    at: str = ""
    block: str = ""


@dataclass(frozen=True)
class Settled:
    """What became of one question. Four endings, and they must look different."""

    question: Question
    how: str
    answer: str = ""
    detail: str = ""


def questions_of(output: dict[str, Any] | None, slug: str) -> list[Question]:
    """The questions a step's output carries, each with the name it will be asked under.

    The name is derived from the run and the question's own words rather than
    drawn, for the same three reasons the knowledge's identifiers are: a bench
    case can say it before the run exists, a driver that died after asking finds
    its own question instead of planting a second, and it is short enough to
    retype from a phone.
    """
    asked: list[Question] = []
    taken: set[str] = set()
    for item in (output or {}).get("asks") or []:
        if not isinstance(item, dict):
            continue
        what = str(item.get("question") or "").strip()
        if not what:
            continue
        # Two questions worded the same are two questions, and the second may
        # not be handed the name the first is already using.
        salt = 0
        id = identifier(slug, what)
        while id in taken:
            salt += 1
            id = identifier(slug, what, salt=salt)
        taken.add(id)
        asked.append(
            Question(
                id=id,
                question=what,
                default=str(item.get("default") or "").strip(),
                because=str(item.get("because") or "").strip(),
                at=str(item.get("at") or "").strip(),
                block=str(item.get("block") or "").strip(),
            )
        )
    return asked


class Owner:
    """The person this machine works for, and the twenty minutes they get.

    No session is involved: nothing here decides whether an answer arrived, what
    it means, or when the waiting is over. It is a program, which is the first
    of the four questions every mechanism of the third version answers.
    """

    def __init__(
        self,
        channel: Channel | None,
        ledger: Ledger,
        wait: int,
        pause: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
        say: Callable[[str], None] | None = None,
        quiet: bool = False,
    ) -> None:
        self.channel = channel
        self.ledger = ledger
        self.wait = wait
        self.pause = pause or time.sleep
        # The deadline is this kit's own clock and nothing else. S7's blocker was
        # an hour somebody else's tool printed, believed as if it were a time.
        self.clock = clock or time.monotonic
        self.say = say or log.info
        #: True when somebody else is telling the owner about this run — a
        #: batch, which sends one message for the whole of it. Questions are
        #: unaffected: a question has its own deadline against a person.
        self.quiet = quiet

    # --- the one thing it does --------------------------------------------

    def ask(
        self,
        project: str,
        slug: str,
        step: str,
        questions: list[Question],
        stop: Callable[[], bool] | None = None,
    ) -> list[Settled]:
        if not questions:
            return []
        if self.channel is None:
            # A kit with no channel behaves exactly as it did before this step,
            # except that the default is now written down instead of invisible.
            return [Settled(question=asked, how=NO_CHANNEL) for asked in questions]

        went, broke, why = self._send(project, slug, step, questions)
        if not went:
            self.say(f"{slug}: {step} спросил владельца, и {why}")
            self.ledger.forget([asked.id for asked in questions])
            return [Settled(question=asked, how=BROKEN, detail=why) for asked in questions]

        try:
            # Ждём только то, что действительно ушло. Вопрос, который владелец
            # уже видит на телефоне, нельзя выбросить вместе с недоставленным:
            # ответ на него придёт, и его должно быть куда положить.
            settled = self._wait(slug, step, went, stop)
        finally:
            self.ledger.forget([asked.id for asked in questions])
        return settled + [Settled(question=asked, how=BROKEN, detail=why) for asked in broke]

    def news(self, text: str) -> None:
        """Something the owner would want to know, and nothing waits on it."""
        if self.channel is None or self.quiet:
            return
        try:
            self.channel.send(text)
        except ChannelFailed as unreachable:
            # News is not worth a night. It is worth a line in the log.
            log.info("the owner's channel is not answering: %s", unreachable.detail)

    # --- sending ----------------------------------------------------------

    def _send(
        self, project: str, slug: str, step: str, questions: list[Question]
    ) -> tuple[list[Question], list[Question], str]:
        """Что ушло, что не ушло, и почему не ушло.

        Канал может лечь посреди списка. Ушедшее при этом остаётся ушедшим — оно
        уже на телефоне у человека, — и ждут именно его.
        """
        from ..machine.ledger import after

        until = after(self.wait)
        went: list[Question] = []
        for number, asked in enumerate(questions):
            # Имя спрашивается у реестра до отправки: сообщение уже нельзя будет
            # переписать, а имя в нём должно быть тем, под которым лежит строка.
            named = replace(asked, id=self.ledger.free_ask_id(project, slug, asked.id))
            try:
                message = self.channel.send(worded(slug, step, named, self.wait))
            except ChannelFailed as unreachable:
                return went, questions[number:], unreachable.detail
            self.ledger.asked(
                Ask(
                    id=named.id, project=project, slug=slug, step=step,
                    question=named.question, default=named.default,
                    until=until, message=message,
                )
            )
            went.append(named)
        self.say(f"{slug}: {step} спрашивает владельца {_questions(len(went))}, {_minutes(self.wait)}")
        return went, [], ""

    # --- waiting ----------------------------------------------------------

    def _wait(
        self,
        slug: str,
        step: str,
        questions: list[Question],
        stop: Callable[[], bool] | None,
    ) -> list[Settled]:
        wanted = [asked.id for asked in questions]
        deadline = self.clock() + self.wait
        broken = ""
        while True:
            try:
                self._poll()
            except ChannelFailed as unreachable:
                # It answered once, and now it does not. The default is taken and
                # the record says which silence this was.
                broken = unreachable.detail
                break
            if all(self._answer_to(id) is not None for id in wanted):
                break
            if stop is not None and stop():
                break
            left = deadline - self.clock()
            if left <= 0:
                break
            # Never longer than what is left: a machine told to wait two seconds
            # must not sleep five, and the bench's cases are exactly that machine.
            self.pause(min(POLL, left))

        settled = []
        for asked in questions:
            answer = self._answer_to(asked.id)
            if answer is not None:
                settled.append(Settled(question=asked, how=ANSWERED, answer=answer))
            elif broken:
                settled.append(Settled(question=asked, how=BROKEN, detail=broken))
            else:
                settled.append(Settled(question=asked, how=NOBODY, detail=_minutes(self.wait)))
        for one in settled:
            log.info("%s: %s — %s: %s", slug, step, one.question.id, one.how)
        return settled

    def _answer_to(self, id: str) -> str | None:
        held = self.ledger.ask_of(id)
        return None if held is None or held.answer is None else held.answer

    def _poll(self) -> None:
        """One read of the channel, by whoever holds the right to read it.

        `getUpdates` is single-consumer, so the reader is a lease. Whoever holds
        it writes down every answer it sees, including answers to somebody
        else's question — which is how the other driver hears without ever
        calling the channel itself.
        """
        held = self.ledger.read_channel()
        if not held.granted:
            return
        try:
            heard, offset = self.channel.read(self.ledger.offset())
            for one in heard:
                id = one.names or self._sent_as(one.answers)
                if not id:
                    # An answer to no question. The offset still moves past it:
                    # what was read once is never read onto a later question.
                    log.info("the owner said something that answers nothing: %r", one.text[:80])
                    continue
                if not self.ledger.answered(id, one.text):
                    log.info("%s was already answered, or is not a question here", id)
            self.ledger.remember_offset(offset)
        finally:
            self.ledger.release(held)

    def _sent_as(self, message: str) -> str:
        found = self.ledger.ask_sent_as(message)
        return found.id if found is not None else ""


# --- what goes to the phone, and what a default becomes ---------------------


def worded(slug: str, step: str, asked: Question, wait: int) -> str:
    """The message a person reads on a phone, and everything they need to answer it."""
    lines = [f"{slug} · {step}", asked.question]
    if wait > 0:
        lines.append(f"Через {_minutes(wait)} возьму: {asked.default}")
    else:
        lines.append(f"Беру: {asked.default}")
    if asked.because:
        lines.append(f"Почему: {asked.because}")
    lines.append(f"Ответить на это сообщение, или: /a {asked.id} <ответ>")
    return "\n".join(lines)


def as_assumption(settled: Settled) -> dict[str, Any]:
    """A default nobody answered, in the shape the rest of the kit already reads.

    Expensive by construction: only the owner could have settled it, and nobody
    did. So `record` writes it into the knowledge and `deliver` prints it in the
    open half of the pull request, and neither of them needed a new field.
    """
    assumed = {
        "what": f"{settled.question.question} — взято: {settled.question.default}",
        "expensive": True,
        "because": _because(settled),
    }
    # Absent, not empty: a field this kit does not have an answer for is left
    # out, and one it has is filled in. An empty string is neither, and the
    # contract refuses it — which is right, and is why it never gets written.
    if settled.question.at:
        assumed["at"] = settled.question.at
    if settled.question.block:
        assumed["block"] = settled.question.block
    return assumed


def _because(settled: Settled) -> str:
    """Одно предложение, и оно правда.

    Пять исходов — пять фраз. Раньше их было четыре, и пятый склеивался из
    четвёртого со своей деталью: получалось «спросили владельца, ответа не было
    у владельца уже был круг», где и предложение не собрано, и утверждение
    ложно — сообщение не отправляли.
    """
    reasons = {
        NOBODY: f"спросили владельца, ответа не было {settled.detail}".strip(),
        BROKEN: f"спросить владельца не вышло: {settled.detail}",
        NO_CHANNEL: "на этой машине нет канала к владельцу, спросить было нечем",
        HAD_ROUND: "владельца об этом не спрашивали: круг вопросов в этом прогоне уже был",
    }
    said = reasons.get(settled.how, settled.how)
    return f"{said}; {settled.question.because}" if settled.question.because else said


def _minutes(seconds: int) -> str:
    if seconds <= 0:
        return "не ждём"
    if seconds % 60 == 0:
        return f"{seconds // 60} мин"
    return f"{seconds} с"


def _questions(count: int) -> str:
    return "об одном" if count == 1 else f"о {count}"
