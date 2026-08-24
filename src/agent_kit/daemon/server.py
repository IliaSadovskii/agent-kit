"""The page: what is running, what is queued, which account is limited until when.

One read of the ledger, rendered twice — as a page for a person and as JSON for
the page to poll itself with. Nothing here decides anything, and there is
nothing on it to press.
"""

from __future__ import annotations

import json
import os
import signal
import threading
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pathlib import Path

from ..logs import get_logger
from ..machine import Ledger, Picture

log = get_logger("daemon")

#: How often the process sweeps up leases whose driver died. Anybody asking for
#: a slot reaps first anyway; this is so a machine nobody is asking about still
#: shows the truth on its page.
SWEEP = 30

STYLE = """
:root { color-scheme: light dark; }
body { font: 15px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; padding: 0 1rem; }
h1 { font-size: 1.3rem; } h2 { font-size: 1rem; margin-top: 2rem; text-transform: lowercase; }
table { border-collapse: collapse; width: 100%; }
td, th { text-align: left; padding: .35rem .6rem .35rem 0; border-bottom: 1px solid #8884; }
th { font-weight: 600; font-size: .85rem; opacity: .7; }
.quiet { opacity: .6; }
"""


def as_dict(ledger: Ledger) -> dict:
    picture = ledger.picture()
    return {
        "held": [
            {
                "slug": row.slug, "step": row.step, "provider": row.provider,
                "account": row.account, "project": row.project, "since": row.taken_at,
            }
            for row in picture.held
        ],
        "queue": [
            {
                "slug": row.slug, "step": row.step, "provider": row.provider,
                "account": row.account, "project": row.project, "since": row.asked_at,
            }
            for row in picture.queue
        ],
        "limits": [
            {
                "account": row.account, "until": row.until, "said_by": row.said_by,
                "said_at": row.said_at, "guessed": row.guessed,
            }
            for row in picture.limits
        ],
        "runs": [{"slug": row.slug, "project": row.project, "since": row.taken_at} for row in ledger.runs()],
    }


def as_json(ledger: Ledger) -> str:
    return json.dumps(as_dict(ledger), indent=2, ensure_ascii=False)


def page(ledger: Ledger) -> str:
    """What a person sees. The same read, in a shape a phone can hold."""
    picture = ledger.picture()
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>agent-kit</title><style>{STYLE}</style>"
        "<meta http-equiv='refresh' content='10'></head><body>"
        "<h1>agent-kit — this machine</h1>"
        f"{_running(picture)}{_queued(picture)}{_limited(picture)}"
        "<p class='quiet'>This page shows and does not act.</p>"
        "</body></html>"
    )


def _running(picture: Picture) -> str:
    if not picture.held:
        return "<h2>running</h2><p class='quiet'>nothing is running</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(row.slug)}</td><td>{escape(row.step)}</td>"
        f"<td>{escape(row.provider)}</td><td>{escape(row.account)}</td>"
        f"<td class='quiet'>{escape(row.taken_at)}</td>"
        f"<td class='quiet'>{escape(row.project)}</td>"
        "</tr>"
        for row in picture.held
    )
    head = "<tr><th>run</th><th>step</th><th>provider</th><th>account</th><th>since</th><th>project</th></tr>"
    return f"<h2>running</h2><table>{head}{rows}</table>"


def _queued(picture: Picture) -> str:
    if not picture.queue:
        return "<h2>queued</h2><p class='quiet'>nobody is waiting</p>"
    rows = "".join(
        f"<tr><td>{escape(row.slug)}</td><td>{escape(row.step)}</td>"
        f"<td>{escape(row.account)}</td><td class='quiet'>{escape(row.asked_at)}</td></tr>"
        for row in picture.queue
    )
    return f"<h2>queued</h2><table><tr><th>run</th><th>step</th><th>account</th><th>asked</th></tr>{rows}</table>"


def _limited(picture: Picture) -> str:
    if not picture.limits:
        return "<h2>limited</h2><p class='quiet'>no account is limited</p>"
    rows = "".join(
        f"<tr><td>{escape(row.account)}</td><td>{escape(row.until)}</td>"
        f"<td class='quiet'>{escape(row.said_by)}{' (an hour, guessed)' if row.guessed else ''}</td></tr>"
        for row in picture.limits
    )
    return f"<h2>limited</h2><table><tr><th>account</th><th>until</th><th>who found out</th></tr>{rows}</table>"


class Page(BaseHTTPRequestHandler):
    ledger: Ledger

    def do_GET(self) -> None:  # noqa: N802 - the name is http.server's
        if self.path.rstrip("/") in ("", "/index.html"):
            return self._answer("text/html; charset=utf-8", page(self.ledger))
        if self.path.rstrip("/") == "/json":
            return self._answer("application/json; charset=utf-8", as_json(self.ledger))
        self.send_error(404, "there are two addresses here: / and /json")

    def _answer(self, kind: str, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        log.info("page: %s", fmt % args)


def serve(ledger: Ledger, host: str, port: int) -> ThreadingHTTPServer:
    """A server, made and not started. Whoever asked decides what thread it runs on."""
    handler = type("BoundPage", (Page,), {"ledger": ledger})
    return ThreadingHTTPServer((host, port), handler)


def reap_forever(ledger: Ledger, every: int = SWEEP, stop: threading.Event | None = None) -> None:
    """The other half of the process: sweep up what died, so a quiet machine still tells the truth."""
    stop = stop or threading.Event()
    while not stop.is_set():
        try:
            gone = ledger.reap()
        except Exception:  # pragma: no cover - a sweep that fails must not take the page down
            log.exception("the sweep failed")
        else:
            if gone:
                log.info("swept up %s rows whose driver is gone", gone)
        stop.wait(every)


def run_forever(ledger: Ledger, host: str, port: int, pid_file: Path | None = None) -> None:
    """The whole of the process: the page, the sweep, and going away when asked.

    The shutdown is asked for from another thread on purpose. `shutdown()` waits
    for `serve_forever()` to come back, and a signal handler runs on the very
    thread that is standing inside it — so calling it there is a daemon that
    ignores every stop and holds the port until somebody kills it.
    """
    if pid_file is not None:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()), encoding="utf-8")

    server = serve(ledger, host, port)
    stop = threading.Event()
    sweeper = threading.Thread(target=reap_forever, args=(ledger,), kwargs={"stop": stop}, daemon=True)
    sweeper.start()

    def down(*_ignored) -> None:
        stop.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, down)
    signal.signal(signal.SIGINT, down)
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()
        if pid_file is not None:
            pid_file.unlink(missing_ok=True)
