"""Лестница канала: уровень меряется, а не объявляется.

То же правило, что у провайдеров — `agent-kit provider check <имя>` проходит
ступени и называет ту, на которой споткнулся. Канал это чужая служба ровно так
же, и «канал настроен» без проверки — заявление вместо следа.

Ревью S7a нашло здесь ровно это: команда печатала одну неизменную строку
«лестница держится», не спросив у телеграма даже, кто он.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .channel import Channel, ChannelFailed

#: Ступени, в том порядке, в каком они стоят друг на друге.
RUNGS = ("канал настроен", "канал отвечает", "сообщение ушло", "ответы читаются")


@dataclass
class Report:
    """Пройденные ступени и та, на которой встали."""

    passed: list[tuple[str, str]] = field(default_factory=list)
    stopped: str = ""
    why: str = ""

    @property
    def held(self) -> bool:
        return not self.stopped


def walk(channel: Channel, said: str, say: Callable[[str], None]) -> Report:
    """Пройти лестницу до конца или до первой ступени, которая не держит."""
    report = Report()

    def rung(name: str, step: Callable[[], str]) -> bool:
        """Ступень называется вслух сразу, а не в конце.

        Иначе команда, споткнувшаяся на второй ступени, молчит и про первую —
        а человек пришёл узнать именно, докуда дошло.
        """
        try:
            what = step()
        except ChannelFailed as broke:
            report.stopped, report.why = name, f"{broke.code}: {broke.detail}"
            say(f"  {name:16} НЕ ДЕРЖИТ — {report.why}")
            return False
        report.passed.append((name, what))
        say(f"  {name:16} {what}")
        return True

    if not rung(RUNGS[0], lambda: channel.name):
        return report
    if not rung(RUNGS[1], channel.me):
        return report
    if not rung(RUNGS[2], lambda: channel.send(said) or "без номера"):
        return report
    rung(RUNGS[3], lambda: f"с {channel.read('')[1] or 'начала'}")
    return report
