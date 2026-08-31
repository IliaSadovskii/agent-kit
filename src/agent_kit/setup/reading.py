"""Where this machine stands, provider by provider — measured, never claimed.

Everything here is read or measured; nothing is declared by the kit about a
machine it has not looked at. The two rungs climbed are the free ones — the
binary is there, and it answers what it is — because this reading is taken
every time somebody types `doctor`, and a reading that cost quota would be a
screen nobody could afford to look at.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from shutil import which

from ..config import Config, ProviderConfig, load_config
from ..errors import KitError
from ..paths import Paths
from ..providers import registry
from ..providers.measured import Measurement, measured_levels


@dataclass(frozen=True)
class Standing:
    """One provider, as this machine finds it."""

    name: str
    title: str
    notes: str
    declared_level: str
    #: False for `fake`, and the only reader of the field. A fixture is on the
    #: screen because it is shipped, and it is marked because nobody installs it.
    real: bool
    #: The free rungs, in order — `driver.check.Rung`, the same objects
    #: `provider check` fills, so what is printed here and what is measured
    #: there cannot say different things about one rung.
    rungs: list = field(default_factory=list)
    install: list[str] = field(default_factory=list)
    login: list[str] = field(default_factory=list)
    #: The first word of `install`, when this machine has no such command. What
    #: holds a declaration the kit will never run: it is argv, so its first word
    #: can be asked of PATH before it is printed at somebody.
    installer_missing: str = ""
    #: What was measured the last time anybody climbed the paid rungs.
    measured: Measurement | None = None
    #: What this machine chose about it, from `config.toml`.
    chosen: ProviderConfig | None = None

    @property
    def stopped_on(self) -> str:
        """The first free rung not held, or empty when both are."""
        return next((rung.name for rung in self.rungs if not rung.held), "")

    @property
    def ready(self) -> bool:
        """The tool is here and it answers. Whether the account does is a session away."""
        return not self.stopped_on

    @property
    def detail(self) -> str:
        return next((rung.detail for rung in self.rungs if not rung.held), "")

    @property
    def configured(self) -> str:
        if self.chosen is None:
            return "not configured here"
        return "enabled" if self.chosen.enabled else "disabled"


@dataclass(frozen=True)
class Reading:
    """One pass over the machine. Both screens print this and nothing else."""

    config: Config
    providers: list[Standing]
    #: The failure itself where `config.toml` would not parse, and None where it
    #: did. The whole error and not a copy of its code, because its readers want
    #: different halves of it: the door prints the code and the walk and `doctor`
    #: raise it again, and a `bad-value` that lost *which key* would send
    #: somebody to a file of thirty lines with nothing to look for.
    unreadable_config: KitError | None = None

    @property
    def default(self) -> str:
        return self.config.machine.provider

    @property
    def working(self) -> list[Standing]:
        """Everything a role could be pointed at today: shipped, real, and standing."""
        return [one for one in self.providers if one.real and one.ready]

    @property
    def named_by(self) -> set[str]:
        """Every provider some role or the default names, whether it is there or not."""
        named = {role.provider for role in self.config.roles.values()}
        named |= {spare for role in self.config.roles.values() for spare in role.fallback}
        return named | ({self.default} if self.default else set())

    def named(self, name: str) -> Standing | None:
        return next((one for one in self.providers if one.name == name), None)


def read(paths: Paths | None = None) -> Reading:
    """The machine, once: the file it chose with, and the two free rungs climbed."""
    paths = paths or Paths.from_env()
    unreadable: KitError | None = None
    try:
        config = load_config(paths.config_file)
    except KitError as broken:
        # Carried, not raised here. Whether it stops the caller is the caller's
        # question: the door names it and reads on, `doctor` and the walk raise
        # it. Reading it in one place is what keeps the three from disagreeing.
        config = Config()
        unreadable = broken

    measured = measured_levels(paths)
    standing = [_standing(name, config, measured) for name in registry.provider_names()]
    return Reading(config=config, providers=standing, unreadable_config=unreadable)


def _standing(name: str, config: Config, measured: dict) -> Standing:
    from ..driver.check import free_rungs

    facts = registry.facts(name)
    return Standing(
        name=name,
        title=facts.title,
        notes=facts.notes.strip(),
        declared_level=facts.level,
        real=facts.real,
        rungs=free_rungs(name),
        install=facts.install,
        login=facts.login,
        installer_missing=_missing(facts.install),
        measured=measured.get(name),
        chosen=config.providers.get(name),
    )


def _missing(install: list[str]) -> str:
    """The word that would have to run, when this machine has no such command."""
    if not install:
        return ""
    first = install[0]
    if "/" in first:
        return "" if Path(first).is_file() else first
    return "" if which(first) else first


# --- the screen -------------------------------------------------------------


def render(reading: Reading) -> list[str]:
    """The provider rows both screens print. One pass, one shape, one place."""
    lines = []
    for one in reading.providers:
        lines.append(f"  {one.name:12} {one.title}")
        lines.append(f"    {'level':10} declares {one.declared_level} · {_measured(one)}")
        if not one.real:
            lines.append(f"    {'':10} a fixture, not an agent — nobody installs it")
        for rung in one.rungs:
            # Three marks, as `provider check` prints them: it passed, it failed,
            # or it could not be put to this provider at all. A rung nobody can
            # climb printed as `ok` is a screen saying a fixture works.
            mark = "ok" if rung.passed else ("--" if not rung.applies else "no")
            lines.append(f"    {rung.name:10} {mark}  {rung.detail}")
        lines.append(f"    {'machine':10} {one.configured}{_account(one)}")
    return lines


def _measured(one: Standing) -> str:
    if one.measured is None:
        return "never measured against an account"
    return f"measured {one.measured.level or 'no level'} on {one.measured.measured_at[:10]}"


def _account(one: Standing) -> str:
    if one.chosen is None or not one.chosen.account:
        return ""
    return f", quota pooled as {one.chosen.account!r}"
