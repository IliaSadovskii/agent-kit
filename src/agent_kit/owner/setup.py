"""`agent-kit owner setup` — от токена до работающего канала, одной командой.

Шесть шагов в чужой документации — это шесть мест, где можно ошибиться, и кит
уже знает, что правило, которое держится на человеке, выполняется два раза из
трёх. Поэтому здесь программа: она проверяет токен у самого телеграма, ждёт,
пока человек напишет боту, и берёт идентификатор чата из того, что пришло, — а
не просит его где-то посмотреть и куда-то переписать.

Настройка либо вся, либо никакая. Токен, который телеграм не принял, не
записывается никуда: полработы здесь — это машина, которая думает, что канал у
неё есть.
"""

from __future__ import annotations

import time
from typing import Callable

from ..config import DEFAULT_ANSWER_WAIT, OwnerConfig, write_owner_block
from ..errors import ConfigError
from ..logs import get_logger
from ..paths import Paths
from .secrets import TELEGRAM_TOKEN, read_secret, write_secret
from .telegram import Telegram

#: Сколько ждём сообщения от человека боту. Дольше, чем нужно, чтобы открыть
#: телеграм и нажать «отправить», и короче, чем терпение у того, кто настраивает.
WAIT_FOR_A_MESSAGE = 300

#: Как часто спрашиваем телеграм, не написал ли уже. Человек не реестр.
POLL = 2.0

log = get_logger("owner")


def setup(
    ask: Callable[[str], str],
    say: Callable[[str], None],
    bot: Callable[..., Telegram] = Telegram,
    paths: Paths | None = None,
    wait: int = WAIT_FOR_A_MESSAGE,
    pause: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
    ledger: "Ledger | None" = None,
) -> OwnerConfig:
    from ..machine import Ledger, ledger_path

    paths = paths or Paths.from_env()
    ledger = ledger or Ledger(ledger_path(paths))
    pause = pause or time.sleep
    clock = clock or time.monotonic

    say("Заведи бота: напиши @BotFather команду /newbot и придумай имя.")
    say("Он ответит токеном вида 8123456:AAF… — вставь его сюда.")
    token = ask("токен: ").strip()
    if not token:
        raise ConfigError("no-token", "ничего не введено; без токена канала не будет")

    # Сначала спрашиваем телеграм, а не человека: токен, который не приняли,
    # лучше узнать здесь, чем ночью в середине прогона.
    talking = bot(token=token, chat="")
    who = talking.me()
    say("")
    say(f"Бот живой: @{who}")
    say(f"Открой https://t.me/{who} и отправь ему любое сообщение — иначе он не")
    say("имеет права писать тебе первым. Жду…")

    chat, name, offset = _wait_for_a_word(talking, ledger, wait, pause, clock)
    if not chat:
        raise ConfigError(
            "no-chat",
            f"никто не написал @{who} за это время, поэтому записывать нечего",
            hint="agent-kit owner setup — и отправь боту сообщение, пока он ждёт",
        )

    # Только теперь, когда всё известно и всё проверено, что-то пишется. И либо
    # пишется всё: токен без канала — это машина, которая думает, что канала у
    # неё нет, при живом боте, и человек об этом не узнает никак.
    had = read_secret(paths.secrets_file, TELEGRAM_TOKEN)
    write_secret(paths.secrets_file, TELEGRAM_TOKEN, token)
    written = OwnerConfig(channel="telegram", chat=chat, wait=DEFAULT_ANSWER_WAIT)
    try:
        where = write_owner_block(paths.config_file, written)
    except BaseException:
        write_secret(paths.secrets_file, TELEGRAM_TOKEN, had)
        raise

    talking.chat = chat
    talking.send(
        f"Готово, {name}. Отсюда придут вопросы, на которые может ответить только ты,\n"
        f"и новости о том, чем кончилась ночь. На вопрос отвечай реплаем на сообщение\n"
        f"или командой /a <id> <ответ>. Без ответа кит через "
        f"{DEFAULT_ANSWER_WAIT // 60} минут возьмёт своё\n"
        f"умолчание и запишет его в pull request."
    )

    say("")
    say(f"Токен  → {paths.secrets_file} (режим 600, не в git)")
    say(f"Канал  → {where}")
    say(f"Чат    → {chat} ({name})")
    say("В телеграм ушло подтверждение. Проверить ещё раз: agent-kit owner check")
    log.info("the owner's channel is set up for chat %s", chat)
    return written


def _wait_for_a_word(
    talking: Telegram,
    ledger,
    wait: int,
    pause: Callable[[float], None],
    clock: Callable[[], float],
) -> tuple[str, str, str]:
    """Ждём, пока человек напишет боту, и берём чат из того, что он написал.

    Идентификатор чата не спрашивают у человека: его негде посмотреть, кроме
    как в ответе того же API, и переписывание числа руками — это ровно тот шаг,
    ради удаления которого команда и заведена.

    Читается канал под арендой читателя, как и везде: `getUpdates` рассчитан на
    одного потребителя, и команда, которая канал заводит, — не исключение из
    правила, которое она заводит. Держит аренду кто-то другой — эта команда
    молчит и ждёт своей очереди, а не забирает чужие сообщения.
    """
    deadline = clock() + wait
    offset = ""
    while True:
        held = ledger.read_channel()
        if held.granted:
            try:
                chat, name, offset = talking.listen(offset)
            finally:
                ledger.release(held)
            if chat:
                return chat, name, offset
        if clock() >= deadline:
            return "", "", offset
        pause(min(POLL, deadline - clock()))
