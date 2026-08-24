"""Telegram's Bot API: the only thing in this kit that opens a socket to a service.

Settled in the plan — *news and questions go to Telegram, thirty lines around
one HTTP call, both directions*. `sendMessage` out, `getUpdates` in.

No webhook: a webhook wants an address on the public internet, and this machine
is reachable only inside Tailscale.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

from .channel import ChannelFailed, Heard, understand

API = "https://api.telegram.org"

#: How long the kit will hold a request open. `getUpdates` is asked with no long
#: poll of its own — the driver's loop is what paces this — so both calls are
#: short, and a machine with no network says so in seconds rather than in hours.
TIMEOUT = 20


class Telegram:
    """One chat, one bot, and one function that makes the call.

    The call is injected so that everything about *what is said* can be tested
    without a socket, and so the bench never has one to open.
    """

    name = "telegram"

    def __init__(self, token: str, chat: str, call: Callable[[str, dict], dict] | None = None) -> None:
        self.token = token
        self.chat = str(chat)
        self._call = call or self._over_http

    def send(self, text: str) -> str:
        answer = self._ask("sendMessage", {"chat_id": self.chat, "text": text})
        return str((answer.get("result") or {}).get("message_id") or "")

    def read(self, offset: str) -> tuple[list[Heard], str]:
        asked: dict[str, Any] = {"timeout": 0}
        if offset.isdigit():
            asked["offset"] = int(offset)
        answer = self._ask("getUpdates", asked)

        heard: list[Heard] = []
        seen = int(offset) if offset.isdigit() else 0
        for update in answer.get("result") or []:
            seen = max(seen, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or {}
            # A bot's username is public and anybody may write to it. An update
            # from any other chat is dropped without being looked at.
            if str((message.get("chat") or {}).get("id")) != self.chat:
                continue
            # Nothing here reads a time. The `date` on an update is their stamp
            # on their clock; what decides whether an answer arrived in time is
            # the moment this kit read it.
            names, text = understand(message.get("text") or "")
            heard.append(
                Heard(
                    text=text,
                    names=names,
                    answers=str((message.get("reply_to_message") or {}).get("message_id") or ""),
                )
            )
        return heard, str(seen)

    # --- the one call -----------------------------------------------------

    def _ask(self, method: str, params: dict) -> dict:
        try:
            answer = self._call(method, params)
        except ChannelFailed:
            raise
        except Exception as unreachable:
            # Somebody else's service, somebody else's network. Named, so that
            # the run's record can tell this apart from nobody answering.
            raise ChannelFailed(
                "channel-failed", f"telegram {method} could not be reached: {unreachable}"
            ) from unreachable
        if not isinstance(answer, dict) or not answer.get("ok"):
            said = (answer or {}).get("description") if isinstance(answer, dict) else answer
            raise ChannelFailed("channel-failed", f"telegram {method} refused: {said}")
        return answer

    def _over_http(self, method: str, params: dict) -> dict:
        body = json.dumps(params).encode("utf-8")
        request = urllib.request.Request(
            f"{API}/bot{self.token}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read().decode("utf-8"))
