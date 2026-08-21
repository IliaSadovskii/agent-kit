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
from ..logs import setup_logging
from ..paths import Paths, project_paths
from ..driver import StepRunner
from ..driver.compose import compose_input
from ..providers.fake import FakeExecutor
from ..state import RunStore
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

    config = commands.add_parser("config", help="the machine's configuration")
    config_what = config.add_subparsers(dest="what", metavar="WHAT")
    config_what.add_parser("show", help="the effective configuration")
    config_what.add_parser("path", help="where the configuration file lives")

    run = commands.add_parser("run", help="a run's state")
    run_what = run.add_subparsers(dest="what", metavar="WHAT")

    new = run_what.add_parser("new", help="create a run")
    new.add_argument("slug")
    new.add_argument("--steps", help="comma-separated step names (default: the four of a feature)")

    run_what.add_parser("list", help="the runs this project holds")

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
    step_run.add_argument("--provider", default="fake", help="who executes it (only the fake exists until S3)")
    step_run.add_argument("--reply", action="append", default=[], metavar="FILE",
                          help="a file the fake provider answers with; repeat for each attempt")

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
    if args.command == "config":
        return _config(args, paths)
    if args.command == "run":
        return _run(args)
    if args.command == "step":
        return _step(args, paths)

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
    print()
    print("what is configured")
    print(f"  max sessions {config.machine.max_sessions}")
    print(f"  providers    {', '.join(sorted(config.providers)) or 'none — nothing can run yet'}")
    print(f"  roles        {', '.join(sorted(config.roles)) or 'none — every role falls back to the default'}")
    return int(ExitCode.OK)


def _present(path: Path) -> str:
    return "ok" if path.exists() else "missing"


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
            name: {"enabled": p.enabled, "model": p.model, "effort": p.effort, "max_sessions": p.max_sessions}
            for name, p in sorted(config.providers.items())
        },
        "roles": {
            name: {"provider": r.provider, "fallback": r.fallback} for name, r in sorted(config.roles.items())
        },
    }


# --- run -------------------------------------------------------------------


def _run(args: argparse.Namespace) -> int:
    store = RunStore(args.project, registry=builtin_registry())
    what = args.what
    if what is None:
        raise UsageError("missing-command", "run needs one of: new, list, show, start, pass, fail, stop")

    if what == "new":
        steps = [name.strip() for name in args.steps.split(",")] if args.steps else None
        run = store.create(args.slug, steps=steps)
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
            for index, step in enumerate(run.steps):
                mark = ">" if index == run.current_step else " "
                reason = f"  {step.reason}" if step.reason else ""
                print(f" {mark} {step.name:12} {step.status.value:8} attempts {step.attempts}{reason}")
        return int(ExitCode.OK)

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

    store = RunStore(args.project, registry=registry)

    if what == "input":
        run = store.load(args.slug)
        index = run.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{args.slug}: every step is done")
        definition = registry.get(run.steps[index].name)
        print(
            compose_input(
                run=run,
                step=run.steps[index],
                definition=definition,
                attempt=run.steps[index].attempts + 1,
                provider=args.provider,
            )
        )
        return int(ExitCode.OK)

    if what == "run":
        executors = _executors(args)
        config = load_config(paths.config_file)
        runner = StepRunner(
            store=store,
            registry=registry,
            executors=executors,
            roles=config.roles,
            default_provider=args.provider,
        )
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


def _executors(args: argparse.Namespace) -> dict:
    """Until S3 there is one provider, and it is not real."""
    if args.provider != "fake":
        raise ProviderError(
            "no-adapter",
            f"{args.provider!r} has no adapter yet; the first real one is Claude Code at S3",
        )
    replies = [Path(name).read_text(encoding="utf-8") for name in args.reply]
    if not replies:
        raise UsageError("no-reply", "the fake provider answers from files: pass --reply FILE at least once")
    return {"fake": FakeExecutor(name="fake", replies=replies)}
