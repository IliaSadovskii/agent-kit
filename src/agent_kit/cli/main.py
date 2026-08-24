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
from ..errors import ConfigError, ExitCode, KitError, ProviderError, StateError, UsageError
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
    go.add_argument("--wait", type=int, metavar="SECONDS",
                    help="how long to wait for a slot or a limit to reset; 0 refuses instead of waiting")

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

    bench = commands.add_parser("bench", help="the planted traps, and which mechanisms fired")
    bench_what = bench.add_subparsers(dest="what", metavar="WHAT")

    bench_list = bench_what.add_parser("list", help="every case, and what it says must fire")
    bench_list.add_argument("--cases", metavar="DIR", help="where the cases are (default: the kit's own)")

    bench_run = bench_what.add_parser("run", help="run every case and say which mechanisms fired")
    bench_run.add_argument("--case", metavar="NAME", help="one case, by name")
    bench_run.add_argument("--cases", metavar="DIR", help="where the cases are (default: the kit's own)")
    bench_run.add_argument("--keep", metavar="DIR",
                           help="where to leave the world of a case that did not fire, for reading")

    step_run = step_what.add_parser("run", help="run the next step of a run")
    step_run.add_argument("slug")
    step_run.add_argument("--provider", help="who executes it; the role table decides when this is left out")
    step_run.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                          help="an option for the provider, as its own block documents; repeat to give several")
    step_run.add_argument("--wait", type=int, metavar="SECONDS",
                          help="how long to wait for a slot or a limit to reset; 0 refuses instead of waiting")

    commands.add_parser("machine", help="what is running here, what is queued, what is limited")

    slot = commands.add_parser("slot", help="a slot by hand: what a script does where a driver would")
    slot_what = slot.add_subparsers(dest="what", metavar="WHAT")
    take = slot_what.add_parser("take", help="hold a slot until it is given back")
    take.add_argument("--provider", required=True)
    take.add_argument("--slug", required=True)
    take.add_argument("--account", help="the quota pool; the provider's own name when left out")
    take.add_argument("--step", default="by-hand")
    take.add_argument("--ttl", type=int, help="how many seconds it lives if nobody gives it back")
    take.add_argument("--machine-max", type=int, help="the ceiling to judge it against; the configured one when left out")
    take.add_argument("--pid", type=int, help="the process this lease belongs to; this one when left out")
    hold = slot_what.add_parser("hold", help="hold a run, as its driver does")
    hold.add_argument("--slug", required=True)
    hold.add_argument("--pid", type=int, help="the process holding it; this one when left out")
    give_back = slot_what.add_parser("release", help="give back what was taken by hand, slot and run alike")
    give_back.add_argument("--slug", required=True)

    limit = commands.add_parser("limit", help="an account that is out of quota, and until when")
    limit_what = limit.add_subparsers(dest="what", metavar="WHAT")
    limit_set = limit_what.add_parser("set", help="write down that an account is limited")
    limit_set.add_argument("account")
    limit_set.add_argument("--until", help="when it resets, as a time; an hour is assumed when left out")
    limit_set.add_argument("--said-by", default="by hand", help="who found out")
    limit_clear = limit_what.add_parser("clear", help="the account is answering again")
    limit_clear.add_argument("account")

    owner = commands.add_parser("owner", help="the channel to the person this machine works for")
    owner_what = owner.add_subparsers(dest="what", metavar="WHAT")
    owner_what.add_parser("setup", help="завести канал: бот, токен, чат — одной командой")
    owner_what.add_parser("check", help="the ladder, and the rung it stopped on")
    owner_say = owner_what.add_parser("say", help="send a line to the owner, and wait for nothing")
    owner_say.add_argument("text")
    owner_what.add_parser("set-token", help="прочитать токен бота с ввода и записать его 600")

    daemon = commands.add_parser("daemon", help="the process that serves the page and sweeps up")
    daemon_what = daemon.add_subparsers(dest="what", metavar="WHAT")
    daemon_start = daemon_what.add_parser("start", help="raise it")
    daemon_start.add_argument("--foreground", action="store_true", help="do not detach; what systemd starts")
    daemon_what.add_parser("status", help="whether it is up, and where it answers")
    daemon_what.add_parser("stop", help="ask it to go away")
    daemon_what.add_parser("install", help="write the systemd user unit")

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
    if args.command == "bench":
        return _bench(args)
    if args.command == "machine":
        return _machine(paths)
    if args.command == "slot":
        return _slot(args, paths)
    if args.command == "limit":
        return _limit(args, paths)
    if args.command == "owner":
        return _owner(args, paths)
    if args.command == "daemon":
        return _daemon(args, paths)

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
    ledger = _ledger(paths)
    print(f"  ledger      {ledger.path}  {_present(ledger.path)}")
    picture = ledger.picture()
    print(f"  right now   {len(picture.held)} running, {len(picture.queue)} queued, {len(picture.limits)} limited")
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
    print(f"  waits up to  {config.machine.wait}s for a slot or a limit to reset")
    print(f"  page         http://{config.daemon.host}:{config.daemon.port}")
    print(f"  owner        {_channel_line(config, paths)}")
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
        "machine": {"max_sessions": config.machine.max_sessions, "wait": config.machine.wait},
        "daemon": {"host": config.daemon.host, "port": config.daemon.port},
        "owner": {
            "channel": config.owner.channel,
            "chat": config.owner.chat,
            "wait": config.owner.wait,
            "file": config.owner.file,
        },
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
                for line in _what_the_step_is_waiting_for(run, step):
                    print(f"     {line}")
                for line in _what_the_step_cost(store, run.slug, index, step.name):
                    print(f"     {line}")
        return int(ExitCode.OK)

    if what == "go":
        return _go(store, registry, args)

    if what == "start":
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.start_step(args.slug, provider=args.provider)
        print(f"{run.slug}: {run.current.name} running (attempt {run.current.attempts})")
        return int(ExitCode.OK)

    if what == "pass":
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.pass_step(args.slug)
        print(f"{run.slug}: {_where(run)}")
        return int(ExitCode.OK)

    if what == "fail":
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.fail_step(args.slug, args.reason)
        print(f"{run.slug}: failed — {run.reason}")
        return int(ExitCode.OK)

    if what == "stop":
        # One writer per run. If a driver holds this one, the stop is posted
        # where that driver reads it — at its next step boundary — rather than
        # written into a file it is still writing.
        driving = _driving(store, args.slug)
        if driving:
            _ledger(Paths.from_env()).ask_stop(driving[0].project, args.slug, reason=args.reason)
            # A code, not a sentence: what a script reads must not be prose
            # somebody will reword.
            print(f"stop-asked: {args.slug} — the driver (pid {driving[0].pid}) stops at the next step")
            return int(ExitCode.OK)
        run = store.stop(args.slug, args.reason)
        print(f"{run.slug}: stopped — {run.reason}")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"run {what}")


def _what_the_step_is_waiting_for(run, step) -> list[str]:
    """The question a step is standing on, read from where it lives while it stands.

    The step's own reason says it is asking; the ledger is what says *what*, and
    when the default is taken without an answer.
    """
    from ..state import StepStatus

    if step.status is not StepStatus.ASKING:
        return []
    where = run.project or str(Path.cwd().resolve())
    said = []
    for ask in _ledger(Paths.from_env()).waiting_on_the_owner():
        if ask.slug != run.slug or ask.project != where:
            continue
        said.append(f"{ask.id}  {ask.question}")
        said.append(f"        taking without an answer at {ask.until}: {ask.default}")
    return said or ["the owner was asked, and the ledger no longer holds the question"]


def _driving(store: RunStore, slug: str) -> list:
    """The leases a driver holds on this run right now, if any."""
    held = store.load(slug)
    where = held.project or str(store.paths.root.resolve())
    ledger = _ledger(Paths.from_env())
    return [lease for lease in ledger.runs() if lease.slug == slug and lease.project == where]


def _refuse_if_a_driver_holds_it(store: RunStore, slug: str) -> None:
    """One writer per run, and a person with a keyboard is a writer like any other.

    `run stop` has somewhere else to go — the driver reads it at a step
    boundary. These three have not: advancing a run under the driver that is
    advancing it is two writers on one file, which is open question 2.
    """
    driving = _driving(store, slug)
    if driving:
        raise StateError(
            "run-held-elsewhere",
            f"{slug} is being run by process {driving[0].pid} since {driving[0].taken_at}",
            hint=f"agent-kit run stop {slug} '<why>' asks that driver to stop",
        )


def _go(store: RunStore, registry, args: argparse.Namespace) -> int:
    """Every step that is left, in order, until one will not pass.

    The driver already says why a step failed and leaves the reason in the run.
    This adds nothing to that: it walks, it prints, and it stops.
    """
    run = store.load(args.slug)
    if run.finished:
        raise StateError("run-finished", f"{args.slug} is {run.status.value}; there is nothing left to run")

    runner = _runner(store, registry, args.provider, args.option, wait=args.wait)
    while True:
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  attempt {attempt.attempt} on {attempt.provider}: {mark}")
        if not outcome.passed:
            print(f"{outcome.slug}: {outcome.reason}", file=sys.stderr)
            if outcome.interrupted:
                # A person stopped this. Reading that as `refused` would say the
                # method turned the work down, and the method said nothing.
                return int(ExitCode.INTERRUPTED)
            # `stopped` means the method said no, whichever step said it. A gate
            # that closes already exited 5; a step refused for a reason the
            # method expects — a blocking finding, a build that never finished —
            # stops the run the same way and must exit the same way.
            return int(_over(store.load(args.slug)))

        print(f"{outcome.slug}: {outcome.step} passed")
        run = store.load(args.slug)
        if not run.finished:
            continue
        if run.status is RunStatus.DONE:
            return int(ExitCode.OK)
        print(f"{outcome.slug}: {run.reason}", file=sys.stderr)
        return int(_over(run))


def _over(run) -> ExitCode:
    """How a run that is not going on ended: the method said no, or the kit could not."""
    return ExitCode.REFUSED if run.status is RunStatus.STOPPED else ExitCode.STATE


def _where(run) -> str:
    if run.status.value in ("done", "stopped", "failed"):
        return run.status.value
    index = run.current_step if run.current_step is not None else run.next_pending()
    return f"next: {run.steps[index].name}" if index is not None else run.status.value


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
        prose = (
            str(method_root() / definition.method)
            if definition.method
            else f"none — {definition.executor} is a program, and nobody reads instructions to one"
        )
        print(f"  prose     {prose}")
        print()
        print("returns:")
        # What *this project* asks of the step, which is what the driver will
        # show the session and check the answer against. One description, and
        # now a person reads the same one.
        from ..project import read_project

        declared = read_project(Path(args.project).resolve())
        print(definition.contract_in(bool(declared and declared.keeps_knowledge)).describe())
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
        runner = _runner(store, registry, args.provider, args.option, wait=args.wait)
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  attempt {attempt.attempt} on {attempt.provider}: {mark}")
        if outcome.passed:
            print(f"{outcome.slug}: {outcome.step} passed")
            return int(ExitCode.OK)
        print(f"{outcome.slug}: {outcome.reason}", file=sys.stderr)
        return int(ExitCode.INTERRUPTED if outcome.interrupted else ExitCode.STATE)

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


# --- bench -----------------------------------------------------------------


def _bench(args: argparse.Namespace) -> int:
    """One line per case: fired, did not fire, or could not be judged.

    Two non-zero codes, because they call for different things. A mechanism that
    stopped firing is a regression in the kit and somebody has to fix it. A case,
    a world or a judge that broke is the instrument being wrong, and nothing was
    measured at all — reading that as a regression points at the wrong thing.
    """
    from tempfile import TemporaryDirectory

    from ..bench import CaseError, case_names, cases_root, read_case, run_named

    # A bare `agent-kit bench` means `bench run`, so the options belong to a
    # subcommand that was not typed and are read as absent rather than crashed on.
    where = getattr(args, "cases", None)
    only = getattr(args, "case", None)
    keeping = getattr(args, "keep", None)

    root = Path(where).resolve() if where else cases_root()
    what = args.what or "run"
    names = case_names(root)

    if what == "list":
        return _bench_list(root, names, read_case, CaseError)
    if what != "run":
        raise UsageError("unknown-command", f"bench {what}")

    if only is not None:
        if only not in names:
            raise UsageError("unknown-case", f"{only!r} is not a case: {', '.join(names) or 'there are none'}")
        names = [only]

    keep = Path(keeping).resolve() if keeping else None
    if keep is not None:
        keep.mkdir(parents=True, exist_ok=True)

    results = []
    with TemporaryDirectory(prefix="agent-kit-bench-") as scratch:
        into = keep or Path(scratch)
        for name in names:
            result = run_named(root, name, into, keep=keep is not None)
            results.append(result)
            print(f"{result.name:38}  {result.said}")
            if result.where is not None:
                print(f"{'':38}  left in {result.where}")

    fired = [result for result in results if result.verdict.fired]
    broken = [result for result in results if not result.verdict.judged]
    print()
    print(f"{len(fired)} of {len(results)} mechanisms fired")
    if broken:
        print(f"{len(broken)} could not be judged, so the bench answered for {len(results) - len(broken)}")
        return int(ExitCode.BROKEN_BENCH)
    return int(ExitCode.OK if len(fired) == len(results) else ExitCode.BENCH)


def _bench_list(root: Path, names: list[str], read_case, CaseError) -> int:
    """Every case and the mechanism it plants. One unreadable case hides none of the others."""
    broken = []
    for name in names:
        try:
            case = read_case(root, name)
        except CaseError as unreadable:
            broken.append(name)
            print(f"{name:38}  unreadable — {unreadable.code}: {unreadable.detail}")
            continue
        print(f"{name:38}  {case.title}")
        print(f"{'':38}  fires: {case.fires}")
    return int(ExitCode.BROKEN_BENCH if broken else ExitCode.OK)


def _runner(store: RunStore, registry, provider: str | None, options: list[str],
            wait: int | None = None) -> StepRunner:
    """Everything a run needs to advance: who executes, which role names them, and what the machine allows."""
    from ..programs import build_program, program_names
    from ..project import read_project

    paths = Paths.from_env()
    config = load_config(paths.config_file)
    typed = _options(options)
    root = store.paths.root
    ledger = _ledger(paths)
    machine = dict(
        ledger=ledger,
        ceilings=_ceilings(config),
        accounts=_accounts(config),
        wait=config.machine.wait if wait is None else wait,
        say=print,
        owner=_owner_of(config, paths, ledger),
    )

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
            **machine,
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
    return StepRunner(store=store, registry=registry, executors=executors, roles=roles, **machine)


def _owner_of(config: Config, paths: Paths, ledger) -> object:
    """The person this run can ask, or nobody — which is a run like any other.

    A channel that is configured and unusable is not a night's problem: the
    question takes its default and the record says the channel could not be
    reached, which is a different sentence from nobody answering.
    """
    from ..owner import Owner, open_channel

    try:
        channel = open_channel(config.owner, paths.secrets_file)
    except KitError as unusable:
        print(f"{PROGRAM}: {unusable.code}: {unusable.detail}", file=sys.stderr)
        channel = None
    return Owner(channel=channel, ledger=ledger, wait=config.owner.wait, say=print)


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


# --- the machine ------------------------------------------------------------


def _ledger(paths: Paths):
    from ..machine import Ledger, ledger_path

    return Ledger(ledger_path(paths))


def _ceilings(config: Config, machine_max: int | None = None):
    """What this installation chose, in the shape the ledger judges against."""
    from ..machine import Ceilings

    return Ceilings(
        max_sessions=config.machine.max_sessions if machine_max is None else machine_max,
        per_provider={
            name: chosen.max_sessions
            for name, chosen in config.providers.items()
            if chosen.max_sessions is not None
        },
    )


def _accounts(config: Config) -> dict[str, str]:
    """The quota pool per provider. Where none is named, a provider is its own."""
    return {name: chosen.account or name for name, chosen in config.providers.items()}


def _machine(paths: Paths) -> int:
    """One screen: what is running, what is waiting, what is out of quota."""
    ledger = _ledger(paths)
    picture = ledger.picture()
    runs = ledger.runs()

    print("running")
    for row in picture.held:
        print(f"  {row.slug:20} {row.step:10} {row.provider:12} {row.account:12} since {row.taken_at}")
    if not picture.held:
        print("  nothing is running")

    print()
    print("queued")
    for row in picture.queue:
        print(f"  {row.slug:20} {row.step:10} {row.account:12} asked at {row.asked_at}")
    if not picture.queue:
        print("  nobody is waiting")

    print()
    print("limited")
    for row in picture.limits:
        guessed = f"  (an hour, guessed from {row.said!r})" if row.guessed else ""
        print(f"  {row.account:20} until {row.until}   {row.said_by} found out{guessed}")
    if not picture.limits:
        print("  no account is limited")

    print()
    print("waiting for the owner")
    for row in ledger.waiting_on_the_owner():
        print(f"  {row.id:8} {row.slug:16} {row.step:10} until {row.until}")
        print(f"           {row.question}")
        print(f"           taking without an answer: {row.default}")
    if not ledger.waiting_on_the_owner():
        print("  no question is waiting")

    print()
    print("runs with a driver on them")
    for row in runs:
        print(f"  {row.slug:20} {row.project}  since {row.taken_at}")
    if not runs:
        print("  nothing is being driven")
    return int(ExitCode.OK)


def _slot(args: argparse.Namespace, paths: Paths) -> int:
    """A slot by hand. Its readers are a person diagnosing a stuck machine and the bench."""
    from ..machine import Want

    what = args.what
    if what is None:
        raise UsageError("missing-command", "slot needs one of: take, hold, release")

    ledger = _ledger(paths)
    project = str(Path(args.project).resolve())

    if what == "take":
        want = Want(
            account=args.account or args.provider,
            provider=args.provider,
            project=project,
            slug=args.slug,
            step=args.step,
            **({"ttl": args.ttl} if args.ttl is not None else {}),
            **({"pid": args.pid} if args.pid is not None else {}),
        )
        got = ledger.take(want, _ceilings(load_config(paths.config_file), args.machine_max))
        if not got.granted:
            raise ProviderError(got.code, got.detail)
        print(f"{args.slug}: holding a slot on {args.provider} until {got.expires_at}")
        return int(ExitCode.OK)

    if what == "hold":
        held = ledger.hold_run(project, args.slug, pid=args.pid)
        if not held.granted:
            raise StateError(held.code, held.detail)
        print(f"{args.slug}: held by process {held.pid}")
        return int(ExitCode.OK)

    if what == "release":
        for lease in ledger.held() + ledger.runs():
            if lease.slug == args.slug and lease.project == project:
                ledger.release(lease)
                print(f"{args.slug}: the {lease.kind} is given back")
                return int(ExitCode.OK)
        raise StateError("no-such-slot", f"nothing here holds a slot or a run for {args.slug!r}")

    raise UsageError("unknown-command", f"slot {what}")


def _limit(args: argparse.Namespace, paths: Paths) -> int:
    what = args.what
    if what is None:
        raise UsageError("missing-command", "limit needs one of: set, clear")

    ledger = _ledger(paths)
    if what == "set":
        until = _a_time(args.until)
        held = ledger.limit(args.account, until=until, said_by=args.said_by)
        guessed = " (an hour, guessed)" if held.guessed else ""
        print(f"{held.account}: limited until {held.until}{guessed}")
        return int(ExitCode.OK)

    if what == "clear":
        ledger.unlimit(args.account)
        print(f"{args.account}: answering again")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"limit {what}")


def _a_time(value: str | None) -> str | None:
    """A time the ledger can compare, or a refusal before anything is written."""
    from datetime import datetime

    if value is None:
        return None
    try:
        datetime.fromisoformat(value)
    except ValueError as error:
        raise UsageError(
            "bad-time", f"{value!r} is not a time: give it as 2026-08-24T17:00:00+00:00"
        ) from error
    return value


def _typed(prompt: str) -> str:
    """Строка от человека. Печатается в stderr, чтобы вывод команды остался выводом."""
    print(prompt, end="", file=sys.stderr, flush=True)
    return sys.stdin.readline()


def _channel_line(config: Config, paths: Paths) -> str:
    """Что за канал у этой машины. Имя канала знает только `owner/`."""
    from ..owner import described

    return described(config.owner, paths.secrets_file)


def _owner(args: argparse.Namespace, paths: Paths) -> int:
    """The channel to a person, and it is measured rather than declared.

    `provider check` walks a ladder and names the rung it stopped on; a channel
    is somebody else's service too, and a level nobody measured is the same
    class of claim as a rule nobody tested.
    """
    from ..owner import TELEGRAM_TOKEN, open_channel, walk, write_secret

    what = args.what
    if what is None:
        raise UsageError("missing-command", "owner needs one of: setup, check, say, set-token")

    if what == "setup":
        from .. import owner as channel_of

        channel_of.setup(ask=_typed, say=print, paths=paths)
        return int(ExitCode.OK)

    if what == "set-token":
        # С потока ввода, а не аргументом: аргумент оседает в истории оболочки.
        token = sys.stdin.readline().strip()
        if not token:
            # Тот же код, что и у настройки, и тот же выход: одна и та же вещь
            # называется одинаково — ревью нашло здесь два кода на один отказ.
            raise ConfigError("no-token", "ничего не введено; токен читается с потока ввода")
        path = write_secret(paths.secrets_file, TELEGRAM_TOKEN, token)
        print(f"токен записан в {path}")
        return int(ExitCode.OK)

    config = load_config(paths.config_file)
    if not config.owner.channel:
        print(f"{PROGRAM}: no-channel: this machine has no channel to its owner", file=sys.stderr)
        print("  every question takes its default at once, and the default is written down", file=sys.stderr)
        print("  agent-kit owner setup заводит его целиком: бот, токен, чат", file=sys.stderr)
        return int(ExitCode.CONFIG)

    channel = open_channel(config.owner, paths.secrets_file)
    if what == "say":
        channel.send(args.text)
        print(f"said it on {channel.name}")
        return int(ExitCode.OK)

    if what == "check":
        # Лестница, а не одна строка про лестницу: уровень меряется, как у
        # провайдера, и команда называет ступень, на которой споткнулась.
        held = walk(
            channel,
            f"{PROGRAM} owner check — эта машина до тебя достаёт. Отвечать ни на что не нужно.",
            say=print,
        )
        if held.held:
            print(f"ждёт ответа на вопрос {config.owner.wait} с, потом берёт умолчание")
            return int(ExitCode.OK)
        print(f"{PROGRAM}: {held.why}", file=sys.stderr)
        return int(ExitCode.CHANNEL)

    raise UsageError("unknown-command", f"owner {what}")


def _daemon(args: argparse.Namespace, paths: Paths) -> int:
    """The process: the page and the sweep. It holds nothing the ledger does not."""
    import os
    import shutil
    import signal
    import subprocess
    import sys as _sys

    from ..daemon import run_forever
    from ..machine import is_alive, is_ours, unit_file, unit_path

    what = args.what or "status"
    config = load_config(paths.config_file)
    where = f"http://{config.daemon.host}:{config.daemon.port}"
    pid_file = paths.state_dir / "daemon.pid"

    def named() -> int | None:
        try:
            return int(pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def running() -> int | None:
        held = named()
        return held if held is not None and is_ours(held) else None

    if what == "status":
        held = running()
        print(f"page       {where}")
        print(f"ledger     {_ledger(paths).path}")
        print(f"process    {'up, pid ' + str(held) if held else 'not running'}")
        return int(ExitCode.OK)

    if what == "install":
        path = unit_path(Path.home())
        path.parent.mkdir(parents=True, exist_ok=True)
        # The command this machine actually has, so the unit does not point at
        # whatever happened to be argv[0] the day it was written.
        binary = shutil.which(PROGRAM) or _sys.argv[0] or PROGRAM
        path.write_text(unit_file(binary), encoding="utf-8")
        print(f"wrote {path}")
        print("  systemctl --user daemon-reload")
        print("  systemctl --user enable --now agent-kit")
        return int(ExitCode.OK)

    if what == "stop":
        held = running()
        if held is None:
            written = named()
            if written is not None and is_alive(written):
                # The number is taken, and not by us. Sending a signal to it is
                # how a pid file that outlived its process takes a stranger down.
                raise StateError(
                    "not-ours",
                    f"{pid_file} names process {written}, which is not an agent-kit daemon",
                    hint=f"delete {pid_file} if you are sure the daemon is gone",
                )
            raise StateError("no-daemon", "nothing is running here; the ledger is unchanged either way")
        try:
            os.kill(held, signal.SIGTERM)
        except (ProcessLookupError, PermissionError) as refused:
            raise StateError("not-ours", f"process {held} would not take the signal: {refused}") from refused
        print(f"asked the daemon (pid {held}) to go away")
        return int(ExitCode.OK)

    if what != "start":
        raise UsageError("unknown-command", f"daemon {what}")

    held = running()
    if held is not None:
        raise StateError("already-running", f"the daemon is already up as pid {held}")

    if not args.foreground:
        child = subprocess.Popen(
            [_sys.executable, "-m", "agent_kit", "daemon", "start", "--foreground"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"the daemon is up as pid {child.pid}; the page is at {where}")
        return int(ExitCode.OK)

    paths.ensure()
    print(f"the page is at {where}", flush=True)
    run_forever(_ledger(paths), config.daemon.host, config.daemon.port, pid_file)
    return int(ExitCode.OK)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
