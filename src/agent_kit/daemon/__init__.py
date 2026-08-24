"""The process, which is not where the truth lives.

Slots, limits and the queue are in the ledger, which every driver writes
directly — see `machine/`. What is left for a permanent process is the thing a
process is genuinely needed for: a page, because a phone cannot read a config
file over ssh, and reaping what died, because somebody should do it even when
nothing is asking.

Read-only. Every button is a way to break a night from a bus, and *showing* is
what was missing.
"""

from .server import as_json, page, reap_forever, run_forever, serve

__all__ = ["as_json", "page", "reap_forever", "run_forever", "serve"]
