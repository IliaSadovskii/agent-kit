"""The command surface.

Every command returns one of the exit codes in `errors.ExitCode`, and every
failure prints a named reason on stderr rather than a stack trace.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import __version__
from ..config import Config, load_config
from ..errors import ExitCode, KitError, ProviderError, StateError, UsageError
from ..logs import get_logger, setup_logging
from ..paths import Paths, project_paths
from ..driver import StepRunner, create_run
from ..driver.compose import compose_input
from ..providers import registry as providers
from ..state import RunStatus, RunStore
from ..steps import builtin_registry, method_root

PROGRAM = "agent-kit"


class Parser(argparse.ArgumentParser):
    """argparse's own exit code for a misuse is 2, and 2 already means a bad config here."""

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"{self.prog}: {message}", file=sys.stderr)
        raise SystemExit(int(ExitCode.USAGE))


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog=PROGRAM,
        description="Drives other people's CLI agents through a method that is a program, not prose.",
    )
    parser.add_argument("--version", action="store_true", help="print the kit's version and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="say what is happening on stderr")
    parser.add_argument("-C", "--project", metavar="DIR", default=".", help="the project to work in (default: here)")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    commands.add_parser("doctor", help="what is configured, what is missing, in one screen")

    init = commands.add_parser("init", help="write what this project declares, from what it already says")
    init.add_argument("--force", action="store_true", help="overwrite a declaration that is already there")

    config = commands.add_parser("config", help="the machine's configuration")
    config_what = config.add_subparsers(dest="what", metavar="WHAT")
    config_what.add_parser("show", help="the effective configuration")
    config_what.add_parser("path", help="where the configuration file lives")

    run = commands.add_parser("run", help="a run's state")
    run_what = run.add_subparsers(dest="what", metavar="WHAT")

    new = run_what.add_parser("new", help="create a run")
    new.add_argument("slug")
    new.add_argument("--brief", help="what this run is for, in your own words; every step's input encloses it")
    new.add_argument("--steps", help="comma-separated step names (default: what `step list` calls the default)")

    run_what.add_parser("list", help="the runs this project holds")

    go = run_what.add_parser("go", help="run every step that is left, and stop at the first that will not pass")
    go.add_argument("slug")
    go.add_argument("--provider", help="who executes the steps a session does; the role table decides when left out")
    go.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                    help="an option for the provider, as its own block documents; repeat to give several")

    show = run_what.add_parser("show", help="a run, as it stands")
    show.add_argument("slug")
    show.add_argument("--json", action="store_true", help="the state itself, not a summary")

    start = run_what.add_parser("start", help="start the next step")
    start.add_argument("slug")
    start.add_argument("--provider", help="which provider this attempt used")

    passed = run_what.add_parser("pass", help="the running step satisfied its contract")
    passed.add_argument("slug")

    failed = run_what.add_parser("fail", help="the running step did not, and here is why")
    failed.add_argument("slug")
    failed.add_argument("reason")

    stopped = run_what.add_parser("stop", help="stop the run, and say why")
    stopped.add_argument("slug")
    stopped.add_argument("reason")

    provider = commands.add_parser("provider", help="the providers this kit ships")
    provider_what = provider.add_subparsers(dest="what", metavar="WHAT")
    provider_what.add_parser("list", help="every provider, with the level it declares")

    check = provider_what.add_parser("check", help="the level it earns, measured rather than claimed")
    check.add_argument("name")
    check.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                       help="an option for the provider, as its own block documents")

    step = commands.add_parser("step", help="the steps this kit knows, and running one")
    step_what = step.add_subparsers(dest="what", metavar="WHAT")

    step_what.add_parser("list", help="every step, with what it must return")

    show_step = step_what.add_parser("show", help="one step: its prose and its contract")
    show_step.add_argument("name")

    step_input = step_what.add_parser("input", help="what the driver would enclose, without running it")
    step_input.add_argument("slug")
    step_input.add_argument("--provider", default="by hand")

    step_run = step_what.add_parser("run", help="run the next step of a run")
    step_run.add_argument("slug")
    step_run.add_argument("--provider", help="who executes it; the role table decides when this is left out")
    step_run.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                          help="an option for the provider, as its own block documents; repeat to give several")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    paths = Paths.from_env()
    setup_logging(args.verbose, log_dir=paths.log_dir)

    try:
        return _dispatch(parser, args, paths)
    except KitError as error:
        print(f"{PROGRAM}: {error.code}: {error.detail or ''}".rstrip(": "), file=sys.stderr)
        if error.hint:
            print(f"  try: {error.hint}", file=sys.stderr)
        return int(error.exit_code)
    except KeyboardInterrupt:
        print(f"{PROGRAM}: stopped", file=sys.stderr)
        return int(ExitCode.INTERRUPTED)
    except Exception as crash:  # a defect in the kit, reported rather than spilled
        get_logger("cli").exception("unhandled failure")
        print(f"{PROGRAM}: internal-error: {type(crash).__name__}: {crash}", file=sys.stderr)
        print(f"  this is a defect in the kit; the whole of it is in {paths.log_dir}", file=sys.stderr)
        return int(ExitCode.INTERNAL)


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace, paths: Paths) -> int:
    if args.version:
        print(f"{PROGRAM} {__version__}")
        return int(ExitCode.OK)

    if args.command is None:
        parser.print_usage(sys.stderr)
        print(f"{PROGRAM}: a command is required; try `{PROGRAM} --help`", file=sys.stderr)
        return int(ExitCode.USAGE)

    if args.command == "doctor":
        return _doctor(paths, Path(args.project))
    if args.command == "init":
        return _init(Path(args.project).resolve(), args.force)
    if args.command == "config":
        return _config(args, paths)
    if args.command == "run":
        return _run(args)
    if args.command == "step":
        return _step(args, paths)
    if args.command == "provider":
        return _provider(args, paths)

    raise UsageError("unknown-command", args.command)


# --- doctor ----------------------------------------------------------------


def _doctor(paths: Paths, project: Path) -> int:
    config = load_config(paths.config_file)
    project_dirs = project_paths(project.resolve())

    print("the machine")
    print(f"  config      {paths.config_file}  {_present(paths.config_file)}")
    print(f"  state       {paths.state_dir}  {_present(paths.state_dir)}")
    print(f"  logs        {paths.log_dir}  {_present(paths.log_dir)}")
    print(f"  secrets     {paths.secrets_file}  {_present(paths.secrets_file)}")
    print()
    print("the project")
    print(f"  root        {project.resolve()}")
    print(f"  kit         {project_dirs.kit_dir}  {_present(project_dirs.kit_dir)}")
    print(f"  runs        {len(RunStore(project).list())}")
    print()
    print("the method")
    registry = builtin_registry()
    print(f"  prose       {method_root()}  {_present(method_root())}")
    print(f"  steps       {', '.join(registry.names())}")
    print(f"  providers   {', '.join(providers.provider_names())}  (shipped; what this machine configured is below)")
    print()
    print("what is configured")
    print(f"  max sessions {config.machine.max_sessions}")
    print(f"  providers    {', '.join(sorted(config.providers)) or 'none — nothing can run yet'}")
    print(f"  roles        {', '.join(sorted(config.roles)) or 'none — every role falls back to the default'}")
    return int(ExitCode.OK)


def _present(path: Path) -> str:
    return "ok" if path.exists() else "missing"


# --- init ------------------------------------------------------------------


def _init(root: Path, force: bool) -> int:
    """Read the repository, write the declaration, and name what was not found."""
    from ..project import discover, is_repository, write_project

    if not is_repository(root):
        print(f"{PROGRAM}: not-a-repository: {root} is not a git working tree", file=sys.stderr)
        print("  the kit delivers on a branch and opens a pull request; both need one", file=sys.stderr)
        return int(ExitCode.CONFIG)

    project, missing = discover(root)
    path = write_project(project, force=force)

    print(f"wrote {path}")
    print(f"  default branch  {project.default_branch}")
    for command in project.commands:
        print(f"  {command.name:14}  {command.command}")
    if not missing:
        return int(ExitCode.OK)

    for gap in missing:
        print(f"{PROGRAM}: missing: {gap}", file=sys.stderr)
    print(f"  fill it in by hand: {path}", file=sys.stderr)
    return int(ExitCode.CONFIG)


# --- config ----------------------------------------------------------------


def _config(args: argparse.Namespace, paths: Paths) -> int:
    what = args.what or "show"
    if what == "path":
        print(paths.config_file)
        return int(ExitCode.OK)
    if what == "show":
        config = load_config(paths.config_file)
        print(json.dumps(_config_as_data(config), indent=2, ensure_ascii=False))
        return int(ExitCode.OK)
    raise UsageError("unknown-command", f"config {what}")


def _config_as_data(config: Config) -> dict:
    return {
        "source": str(config.source) if config.source else None,
        "machine": {"max_sessions": config.machine.max_sessions},
        "providers": {
            name: {
                "enabled": p.enabled,
                "model": p.model,
                "effort": p.effort,
                "account": p.account,
                "max_sessions": p.max_sessions,
            }
            for name, p in sorted(config.providers.items())
        },
        "roles": {
            name: {"provider": r.provider, "fallback": r.fallback, "model": r.model, "effort": r.effort}
            for name, r in sorted(config.roles.items())
        },
    }


# --- run -------------------------------------------------------------------


def _run(args: argparse.Namespace) -> int:
    store = RunStore(args.project)
    registry = builtin_registry()
    what = args.what
    if what is None:
        raise UsageError("missing-command", "run needs one of: new, list, show, start, pass, fail, stop")

    if what == "new":
        steps = [name.strip() for name in args.steps.split(",")] if args.steps else None
        run = create_run(store, registry, args.slug, steps=steps, brief=args.brief)
        print(f"{run.slug}: created on {run.branch} with {len(run.steps)} steps")
        return int(ExitCode.OK)

    if what == "list":
        slugs = store.list()
        if not slugs:
            print("no runs yet")
        for slug in slugs:
            run = store.load(slug)
            print(f"{slug:24} {run.status.value:9} {_where(run)}")
        return int(ExitCode.OK)

    if what == "show":
        run = store.load(args.slug)
        if args.json:
            print(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"{run.slug}  {run.status.value}  {run.branch}")
            if run.brief:
                print(f"  for: {run.brief}")
            for index, step in enumerate(run.steps):
                mark = ">" if index == run.current_step else " "
                reason = f"  {step.reason}" if step.reason else ""
                print(f" {mark} {step.name:12} {step.status.value:8} attempts {step.attempts}{reason}")
                for line in _what_the_step_cost(store, run.slug, index, step.name):
                    print(f"     {line}")
        return int(ExitCode.OK)

    if what == "go":
        return _go(store, registry, args)

    if what == "start":
        run = store.start_step(args.slug, provider=args.provider)
        print(f"{run.slug}: {run.running.name} running (attempt {run.running.attempts})")
        return int(ExitCode.OK)

    if what == "pass":
        run = store.pass_step(args.slug)
        print(f"{run.slug}: {_where(run)}")
        return int(ExitCode.OK)

    if what == "fail":
        run = store.fail_step(args.slug, args.reason)
        print(f"{run.slug}: failed — {run.reason}")
        return int(ExitCode.OK)

    if what == "stop":
        run = store.stop(args.slug, args.reason)
        print(f"{run.slug}: stopped — {run.reason}")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"run {what}")


def _go(store: RunStore, registry, args: argparse.Namespace) -> int:
    """Every step that is left, in order, until one will not pass.

    The driver already says why a step failed and leaves the reason in the run.
    This adds nothing to that: it walks, it prints, and it stops.
    """
    run = store.load(args.slug)
    if run.finished:
        raise StateError("run-finished", f"{args.slug} is {run.status.value}; there is nothing left to run")

    runner = _runner(store, registry, args.provider, args.option)
    while True:
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  attempt {attempt.attempt} on {attempt.provider}: {mark}")
        if not outcome.passed:
            print(f"{outcome.slug}: {outcome.reason}", file=sys.stderr)
            return int(ExitCode.STATE)

        print(f"{outcome.slug}: {outcome.step} passed")
        run = store.load(args.slug)
        if not run.finished:
            continue
        if run.status is RunStatus.DONE:
            return int(ExitCode.OK)
        print(f"{outcome.slug}: {run.reason}", file=sys.stderr)
        return int(ExitCode.STATE)


def _where(run) -> str:
    if run.status.value in ("done", "stopped", "failed"):
        return run.status.value
    index = run.current_step if run.current_step is not None else run.next_pending()
    return f"next: {run.steps[index].name}" if index is not None else run.status.value


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


# --- step ------------------------------------------------------------------


def _step(args: argparse.Namespace, paths: Paths) -> int:
    registry = builtin_registry()
    what = args.what
    if what is None:
        raise UsageError("missing-command", "step needs one of: list, show, input, run")

    if what == "list":
        for definition in registry.all():
            print(f"{definition.name:12} {definition.role:10} {definition.title}")
        return int(ExitCode.OK)

    if what == "show":
        definition = registry.get(args.name)
        print(f"{definition.name} — {definition.title}")
        print(f"  role      {definition.role}")
        print(f"  prose     {method_root() / definition.method}")
        print()
        print("returns:")
        print(definition.contract.describe())
        return int(ExitCode.OK)

    store = RunStore(args.project)

    if what == "input":
        run = store.load(args.slug)
        if run.finished:
            raise StateError("run-finished", f"{args.slug} is {run.status.value}; there is no next step")
        index = run.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{args.slug}: no step is waiting to run")
        definition = registry.get(run.steps[index].name)
        print(
            compose_input(
                run=run,
                definition=definition,
                attempt=1,
                provider=args.provider,
            )
        )
        return int(ExitCode.OK)

    if what == "run":
        runner = _runner(store, registry, args.provider, args.option)
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  attempt {attempt.attempt} on {attempt.provider}: {mark}")
        if outcome.passed:
            print(f"{outcome.slug}: {outcome.step} passed")
            return int(ExitCode.OK)
        print(f"{outcome.slug}: {outcome.reason}", file=sys.stderr)
        return int(ExitCode.STATE)

    raise UsageError("unknown-command", f"step {what}")


def _provider(args: argparse.Namespace, paths: Paths) -> int:
    what = args.what or "list"
    if what == "check":
        return _provider_check(args)
    if what != "list":
        raise UsageError("unknown-command", f"provider {what}")

    from ..providers.measured import measured_levels

    config = load_config(paths.config_file)
    measured = measured_levels(paths)
    for facts in providers.all_facts():
        chosen = config.providers.get(facts.name)
        state = "not configured here" if chosen is None else ("enabled" if chosen.enabled else "disabled")
        real = "" if facts.real else "  (a fixture, not an agent)"
        seen = measured.get(facts.name)
        earned = (
            f"not measured — {facts.level} is what it claims"
            if seen is None
            else f"measured {seen.level or 'no level'} on {seen.measured_at[:10]}"
        )
        print(f"{facts.name:12} declares {facts.level:2} {earned:38} {state:20}{real}")
    return int(ExitCode.OK)


def _runner(store: RunStore, registry, provider: str | None, options: list[str]) -> StepRunner:
    """Everything a run needs to advance: who executes, and which role names them."""
    from ..programs import build_program, program_names
    from ..project import read_project

    paths = Paths.from_env()
    config = load_config(paths.config_file)
    typed = _options(options)
    root = store.paths.root

    # The programs are not providers: nobody chooses them, nobody configures
    # them, and a step that names one names it in the kit's own registry. They
    # are always there, whatever the role table says.
    executors = {name: build_program(name, root) for name in program_names()}

    if provider is not None:
        # Somebody typed a provider. Configuration does not overrule what was
        # asked for — but what it says *about* that provider still applies.
        executors[provider] = providers.build_executor(provider, _settings(config, provider, typed))
        return StepRunner(
            store=store,
            registry=registry,
            executors=executors,
            roles={},
            default_provider=provider,
        )

    # Nobody named one, so the role table decides. A project's own table wins
    # over the machine's, and only for the roles it names.
    declared = read_project(root)
    roles = {**config.roles, **(declared.roles if declared else {})}
    named = {role.provider for role in roles.values()}
    named |= {spare for role in roles.values() for spare in role.fallback}
    executors.update(
        {name: providers.build_executor(name, _settings(config, name, typed)) for name in sorted(named)}
    )
    return StepRunner(store=store, registry=registry, executors=executors, roles=roles)


def _settings(config: Config, provider: str, typed: dict[str, list[str]]) -> dict[str, list[str]]:
    """`provider.toml` asks; `config.toml` answers; what was typed wins over both."""
    chosen = config.providers.get(provider)
    answered: dict[str, list[str]] = {}
    if chosen is not None:
        for key in ("model", "effort", "account"):
            value = getattr(chosen, key)
            if value is not None:
                answered[key] = [value]
    return {**answered, **typed}


def _options(pairs: list[str]) -> dict[str, list[str]]:
    """`--option key=value`, repeatable. What a key means is the provider's business."""
    parsed: dict[str, list[str]] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            raise UsageError("bad-option", f"{pair!r} is not KEY=VALUE")
        parsed.setdefault(key.strip(), []).append(value)
    return parsed


def _provider_check(args: argparse.Namespace) -> int:
    """The ladder, printed. A level nobody measured is a claim, not a fact."""
    from ..driver.check import check_provider

    report = check_provider(
        args.name, _options(args.option), project=Path(args.project).resolve(), remember=True
    )

    for rung in report.rungs:
        mark = "ok  " if rung.passed else ("--  " if not rung.applies else "no  ")
        print(f"  {mark}{rung.name:10} {rung.detail}")
    print()

    if report.level is None:
        print(f"{args.name}: no level — it failed at {report.failed}", file=sys.stderr)
        return int(ExitCode.PROVIDER)

    print(f"{args.name}: level {report.level}, declared {report.declared_level}")
    if report.facts.observed:
        share = report.facts.context_share or 0
        print(f"  context   {report.facts.context_used:,} of {report.facts.context_window:,} ({share:.1%})")
    if report.facts.transcript:
        print(f"  session   {report.facts.session}")
        print(f"  record    {report.facts.transcript}")
    if not report.earns_what_it_declares:
        print(
            f"{args.name}: it declares level {report.declared_level} and earned {report.level}"
            f" — it failed at {report.failed}",
            file=sys.stderr,
        )
        return int(ExitCode.PROVIDER)
    return int(ExitCode.OK)


def _what_the_step_cost(store: RunStore, slug: str, index: int, name: str) -> list[str]:
    """What the driver wrote about a step, read back. Every field it writes has a reader."""
    from ..driver.workspace import StepWorkspace

    meta = StepWorkspace(store.run_root(slug), index, name).read_meta()
    if not meta:
        return []

    said = []
    where = " on ".join(part for part in (meta.get("model"), meta.get("provider")) if part)
    if where:
        said.append(where)
    if meta.get("context_used") and meta.get("context_window"):
        share = meta["context_used"] / meta["context_window"]
        said.append(f"context {meta['context_used']:,} of {meta['context_window']:,} ({share:.1%})")
    if meta.get("cost_usd") is not None:
        said.append(f"${meta['cost_usd']:.2f}")
    if meta.get("duration_ms"):
        said.append(f"{meta['duration_ms'] / 1000:.1f}s")
    if meta.get("limited_until"):
        said.append(f"limited until {meta['limited_until']}")
    return [", ".join(said)] if said else []
