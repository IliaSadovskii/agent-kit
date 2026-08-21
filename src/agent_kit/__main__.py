"""`python -m agent_kit` — the same command, with nothing installed.

Useful where the kit cannot be installed at all: a shared machine, a container
that has no uv, a checkout you want to run once. `uv tool install` is still the
way to have it on PATH.
"""

from .cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
