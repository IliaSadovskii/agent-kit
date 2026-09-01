"""The command surface.

Every command returns one of the exit codes in `errors.ExitCode`, and every
failure prints a named reason on stderr rather than a stack trace.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .. import __version__
from ..config import Config, load_config
from ..errors import ConfigError, ExitCode, KitError, ProviderError, StateError, UsageError
from ..logs import get_logger, setup_logging
from ..manual import PROOF_TIMEOUT as MANUAL_TIMEOUT
from ..paths import Paths
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
        description="Водит чужие CLI-агенты по методу, который есть программа, а не проза.",
    )
    parser.add_argument("--version", action="store_true", help="напечатать версию кита и выйти")
    parser.add_argument("-v", "--verbose", action="store_true", help="говорить в stderr, что происходит")
    parser.add_argument("-C", "--project", metavar="DIR", default=".", help="проект, в котором работать (по умолчанию — этот)")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    commands.add_parser(
        "next", help="где стоит проект и что с этим делать"
    )
    commands.add_parser("doctor", help="чем настроена эта машина и чего не хватает")

    setup = commands.add_parser(
        "setup", help="ход внутрь: что запустить, чтобы провайдер здесь заработал, и что запишется в конфиг"
    )
    setup.add_argument(
        "name", nargs="?",
        help="какой провайдер настраивать (по умолчанию — тот, что уже работает, иначе первый по списку)",
    )

    manual = commands.add_parser("manual", help="работа, которую ночь сделать не может, и чем она доказывается")
    manual_what = manual.add_subparsers(dest="what", metavar="WHAT")
    manual_check = manual_what.add_parser(
        "check", help="прогнать все доказательства и снять строки, которые вернулись зелёными"
    )
    manual_check.add_argument(
        "--timeout", type=int, default=None, metavar="SECONDS",
        help=f"how long one proof is given (default: {MANUAL_TIMEOUT})",
    )

    init = commands.add_parser("init", help="записать, что проект объявляет, из того, что он уже говорит")
    init.add_argument("--force", action="store_true", help="переписать объявление, которое уже лежит")

    config = commands.add_parser("config", help="конфигурация машины")
    config_what = config.add_subparsers(dest="what", metavar="WHAT")
    config_what.add_parser("show", help="конфигурация, как она действует")
    config_what.add_parser("path", help="где лежит файл конфигурации")

    run = commands.add_parser("run", help="состояние прогона")
    run_what = run.add_subparsers(dest="what", metavar="WHAT")

    new = run_what.add_parser("new", help="создать прогон")
    new.add_argument("slug")
    new.add_argument("--brief", help="зачем этот прогон, вашими словами; это вкладывается во вход каждого шага")
    new.add_argument("--steps", help="имена шагов через запятую (по умолчанию — те, что `step list` называет умолчанием)")


    go = run_what.add_parser("go", help="пройти все оставшиеся шаги и встать на первом, который не пройдёт")
    go.add_argument("slug")
    go.add_argument("--provider", help="кто исполняет шаги, которые делает сессия; без этого решает таблица ролей")
    go.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                    help="опция провайдеру, как описано в его собственном блоке; повторяйте, чтобы дать несколько")
    go.add_argument("--wait", type=int, metavar="SECONDS",
                    help="сколько ждать слота или сброса лимита; 0 — отказать, а не ждать")
    go.add_argument("--silent", action="store_true",
                    help="про этот прогон владельцу расскажет кто-то другой; так делает партия, "
                         "so five features do not wake a phone five times")

    show = run_what.add_parser("show", help="прогон, как он стоит")
    show.add_argument("slug")
    show.add_argument("--json", action="store_true", help="само состояние, а не сводка")

    start = run_what.add_parser("start", help="запустить следующий шаг")
    start.add_argument("slug")
    start.add_argument("--provider", help="каким провайдером шла эта попытка")

    passed = run_what.add_parser("pass", help="идущий шаг удовлетворил свой контракт")
    passed.add_argument("slug")

    failed = run_what.add_parser("fail", help="идущий шаг не удовлетворил, и вот почему")
    failed.add_argument("slug")
    failed.add_argument("reason")

    stopped = run_what.add_parser("stop", help="остановить прогон и сказать почему")
    stopped.add_argument("slug")
    stopped.add_argument("reason")

    reopened = run_what.add_parser(
        "reopen", help="продолжить остановленный прогон с того шага, где он встал"
    )
    reopened.add_argument("slug")

    batch = commands.add_parser("batch", help="работа на вечер: несколько фич и что чего ждёт")
    batch_what = batch.add_subparsers(dest="what", metavar="WHAT")

    batch_compose = batch_what.add_parser(
        "compose", help="сеанс с владельцем: он рассказывает, кит собирает объявление вечера"
    )
    batch_compose.add_argument("name", help="имя партии; оно же имя каталога и заголовок отчёта")
    batch_compose.add_argument(
        "--from", dest="telling", metavar="FILE",
        help="файл с рассказом; `-` читает его с потока ввода, и тогда спросить будет некого. "
             "Без этого открывается $EDITOR, как у `git commit`",
    )
    batch_compose.add_argument(
        "--out", metavar="FILE",
        help="куда писать объявление; без этого — .agent-kit/v3/declarations/<имя>.toml",
    )
    batch_compose.add_argument("--provider", help="кто исполняет два хода сеанса; без этого решает таблица ролей")
    batch_compose.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                               help="настройка провайдера, как описано в его блоке; можно повторять")
    batch_compose.add_argument("--wait", type=int, metavar="SECONDS",
                               help="сколько ждать слота; 0 отказывает вместо ожидания")

    batch_new = batch_what.add_parser("new", help="создать партию из файла, который вы написали")
    batch_new.add_argument("file", help="объявление: фичи, задачи и что чего ждёт")


    batch_show = batch_what.add_parser("show", help="партия, как она стоит")
    batch_show.add_argument("name")
    batch_show.add_argument("--json", action="store_true", help="само состояние, а не сводка")

    batch_go = batch_what.add_parser("go", help="построить всё, что осталось, столько сразу, сколько влезет")
    batch_go.add_argument("name")
    batch_go.add_argument("--provider", help="кто исполняет шаги, которые делает сессия")
    batch_go.add_argument("--option", action="append", default=[], metavar="[FEATURE:]KEY=VALUE",
                          help="опция провайдеру; назовите сначала фичу, чтобы адресовать один прогон")

    batch_stop = batch_what.add_parser("stop", help="остановить партию и сказать почему")
    batch_stop.add_argument("name")
    batch_stop.add_argument("reason")

    batch_skip = batch_what.add_parser("skip", help="не строить эту фичу сегодня — и то, что её ждало, тоже")
    batch_skip.add_argument("name")
    batch_skip.add_argument("feature")
    batch_skip.add_argument("reason")

    batch_reopen = batch_what.add_parser(
        "reopen", help="всё-таки построить эту фичу и то, что она увела за собой"
    )
    batch_reopen.add_argument("name")
    batch_reopen.add_argument("feature")

    tree = commands.add_parser("tree", help="рабочие копии, в которых строят прогоны этого проекта")
    tree_what = tree.add_subparsers(dest="what", metavar="WHAT")
    tree_what.add_parser("list", help="каждое дерево и ветка, на которой оно стоит")
    tree_remove = tree_what.add_parser("remove", help="убрать одно; работа остаётся на ветке")
    tree_remove.add_argument("slug")

    # No `list`: what it printed is the machine's standing, and that is now one
    # reading with two screens over it — `doctor` and `setup`. A third pass at
    # the same rows is the defect §5 of the plan names.
    provider = commands.add_parser("provider", help="провайдеры, которые везёт этот кит")
    provider_what = provider.add_subparsers(dest="what", metavar="WHAT")

    check = provider_what.add_parser("check", help="уровень, который он зарабатывает, — мерянный, а не объявленный")
    check.add_argument("name")
    check.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                       help="опция провайдеру, как описано в его собственном блоке")

    step = commands.add_parser("step", help="шаги, которые знает этот кит, и запуск одного")
    step_what = step.add_subparsers(dest="what", metavar="WHAT")

    step_what.add_parser("list", help="каждый шаг и что он обязан вернуть")

    show_step = step_what.add_parser("show", help="один шаг: его проза и его контракт")
    show_step.add_argument("name")

    step_input = step_what.add_parser("input", help="что вложил бы драйвер, — без запуска")
    step_input.add_argument("slug")
    step_input.add_argument("--provider", default="by hand")

    bench = commands.add_parser("bench", help="подложенные ловушки и какие механизмы сработали")
    bench_what = bench.add_subparsers(dest="what", metavar="WHAT")

    bench_list = bench_what.add_parser("list", help="каждый случай и что, по его словам, должно сработать")
    bench_list.add_argument("--cases", metavar="DIR", help="где лежат случаи (по умолчанию — собственные кита)")

    bench_run = bench_what.add_parser("run", help="прогнать все случаи и сказать, какие механизмы сработали")
    bench_run.add_argument("--case", metavar="NAME", help="один случай, по имени")
    bench_run.add_argument("--cases", metavar="DIR", help="где лежат случаи (по умолчанию — собственные кита)")
    bench_run.add_argument("--keep", metavar="DIR",
                           help="куда положить мир случая, который не сработал, чтобы прочитать")

    bench_disarm = bench_what.add_parser(
        "disarm", help="отнять у каждого случая его ловушку и потребовать, чтобы он перестал срабатывать")
    bench_disarm.add_argument("--case", metavar="NAME", help="один случай, по имени")
    bench_disarm.add_argument("--cases", metavar="DIR", help="где лежат случаи (по умолчанию — собственные кита)")

    step_run = step_what.add_parser("run", help="запустить следующий шаг прогона")
    step_run.add_argument("slug")
    step_run.add_argument("--provider", help="кто его исполняет; без этого решает таблица ролей")
    step_run.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                          help="опция провайдеру, как описано в его собственном блоке; повторяйте, чтобы дать несколько")
    step_run.add_argument("--wait", type=int, metavar="SECONDS",
                          help="сколько ждать слота или сброса лимита; 0 — отказать, а не ждать")

    commands.add_parser("machine", help="что здесь идёт, что в очереди, что исчерпано")

    slot = commands.add_parser("slot", help="слот руками: то, что делает скрипт там, где стоял бы драйвер")
    slot_what = slot.add_subparsers(dest="what", metavar="WHAT")
    take = slot_what.add_parser("take", help="держать слот, пока его не отдадут")
    take.add_argument("--provider", required=True)
    take.add_argument("--slug", required=True)
    take.add_argument("--account", help="пул квоты; без этого — имя самого провайдера")
    take.add_argument("--step", default="by-hand")
    take.add_argument("--ttl", type=int, help="сколько секунд он живёт, если его никто не отдаст")
    take.add_argument("--machine-max", type=int, help="потолок, против которого судить; без этого — настроенный")
    take.add_argument("--pid", type=int, help="процесс, которому принадлежит аренда; без этого — этот")
    wants = slot_what.add_parser("wants", help="встать в очередь, как встаёт драйвер перед сном")
    wants.add_argument("--provider", required=True)
    wants.add_argument("--slug", required=True)
    wants.add_argument("--step", default="build")
    wants.add_argument("--account", help="пул квоты; без этого — имя самого провайдера")
    wants.add_argument("--pid", type=int, help="чей это ожидающий; мёртвого выметает как любую строку")

    hold = slot_what.add_parser("hold", help="держать прогон, как держит его драйвер")
    hold.add_argument("--slug", required=True)
    hold.add_argument("--pid", type=int, help="процесс, который его держит; без этого — этот")
    hold.add_argument("--checkout", action="store_true",
                      help="держать вместо этого рабочую копию проекта, как прогон без своего дерева")
    give_back = slot_what.add_parser("release", help="отдать то, что взяли руками, — и слот, и прогон")
    give_back.add_argument("--slug", required=True)

    ask = commands.add_parser("ask", help="вопрос владельцу руками: там, где стоял бы драйвер")
    ask_what = ask.add_subparsers(dest="what", metavar="WHAT")
    ask_plant = ask_what.add_parser("plant", help="положить вопрос так, как его оставил бы драйвер")
    ask_plant.add_argument("--slug", required=True)
    ask_plant.add_argument("--step", default="by-hand")
    ask_plant.add_argument("--id", required=True, help="имя вопроса; выводится из прогона и его слов")
    ask_plant.add_argument("--question", required=True)
    ask_plant.add_argument("--default", required=True, help="что берётся без ответа")
    ask_plant.add_argument("--message", default="", help="каким сообщением он ушёл")
    ask_plant.add_argument("--until", help="до какого часа ждёт; час вперёд, если не сказано")
    ask_clear = ask_what.add_parser("clear", help="снять вопрос, который завис")
    ask_clear.add_argument("id")

    limit = commands.add_parser("limit", help="аккаунт, у которого кончилась квота, и до какого часа")
    limit_what = limit.add_subparsers(dest="what", metavar="WHAT")
    limit_set = limit_what.add_parser("set", help="записать, что аккаунт исчерпан")
    limit_set.add_argument("account")
    limit_set.add_argument("--until", help="когда он сбросится, временем; без этого предполагается час")
    limit_set.add_argument("--said-by", default="by hand", help="кто это узнал")
    limit_clear = limit_what.add_parser("clear", help="аккаунт снова отвечает")
    limit_clear.add_argument("account")

    owner = commands.add_parser("owner", help="канал к человеку, на которого работает эта машина")
    owner_what = owner.add_subparsers(dest="what", metavar="WHAT")
    owner_what.add_parser("setup", help="завести канал: бот, токен, чат — одной командой")
    owner_what.add_parser("check", help="лестница и ступень, на которой она встала")
    owner_say = owner_what.add_parser("say", help="отправить владельцу строку и ничего не ждать")
    owner_say.add_argument("text")
    owner_what.add_parser("set-token", help="прочитать токен бота с ввода и записать его 600")

    knowledge = commands.add_parser(
        "knowledge", help="что проект знает о себе — и час, за который он это рассказывает"
    )
    knowledge_what = knowledge.add_subparsers(dest="what", metavar="WHAT")
    tell = knowledge_what.add_parser(
        "tell", help="сеанс с владельцем: он рассказывает, кит сортирует и пишет описание"
    )
    tell.add_argument(
        "--from", dest="telling", metavar="FILE",
        help="файл с рассказом; `-` читает его с потока ввода, и тогда спросить будет некого. "
             "Без этого открывается $EDITOR, как у `git commit`",
    )
    tell.add_argument("--provider", help="кто исполняет два хода сеанса; без этого решает таблица ролей")
    tell.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                      help="настройка провайдера, как описано в его блоке; можно повторять")
    tell.add_argument("--wait", type=int, metavar="SECONDS",
                      help="сколько ждать слота; 0 отказывает вместо ожидания")

    commands.add_parser(
        "verification",
        help="виды проверки, которые знает кит, и что проект отвечает о каждом",
    )

    audit = commands.add_parser(
        "audit", help="линза над кодом: отчёт и список работы; в проекте ничего не меняется"
    )
    audit.add_argument(
        "lens", metavar="LENS",
        help="какая линза; сегодня их одна — dependencies: что объявлено против того, что импортируется",
    )
    audit.add_argument(
        "--out", metavar="FILE",
        help="куда писать список кандидатов; без этого — candidates.md в каталоге аудита. "
             "Работы не нашлось — файла нет",
    )
    audit.add_argument("--provider", help="кто исполняет ход линзы; без этого решает таблица ролей")
    audit.add_argument("--option", action="append", default=[], metavar="KEY=VALUE",
                       help="настройка провайдера, как описано в его блоке; можно повторять")
    audit.add_argument("--wait", type=int, metavar="SECONDS",
                       help="сколько ждать слота; 0 отказывает вместо ожидания")

    daemon = commands.add_parser("daemon", help="процесс, который отдаёт страницу и подметает")
    daemon_what = daemon.add_subparsers(dest="what", metavar="WHAT")
    daemon_start = daemon_what.add_parser("start", help="поднять его")
    daemon_start.add_argument("--foreground", action="store_true", help="не отцепляться; так его запускает systemd")
    daemon_what.add_parser("status", help="поднят ли он и где отвечает")
    daemon_what.add_parser("stop", help="попросить его уйти")
    daemon_what.add_parser("install", help="записать пользовательский юнит systemd")

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
            print(f"  попробуйте: {error.hint}", file=sys.stderr)
        return int(error.exit_code)
    except KeyboardInterrupt:
        print(f"{PROGRAM}: остановлено", file=sys.stderr)
        return int(ExitCode.INTERRUPTED)
    except Exception as crash:  # a defect in the kit, reported rather than spilled
        get_logger("cli").exception("unhandled failure")
        print(f"{PROGRAM}: internal-error: {type(crash).__name__}: {crash}", file=sys.stderr)
        print(f"  это дефект кита; целиком он лежит в {paths.log_dir}", file=sys.stderr)
        return int(ExitCode.INTERNAL)


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace, paths: Paths) -> int:
    if args.version:
        print(f"{PROGRAM} {__version__}")
        return int(ExitCode.OK)

    if args.command is None:
        parser.print_usage(sys.stderr)
        print(f"{PROGRAM}: нужна команда; попробуйте `{PROGRAM} --help`", file=sys.stderr)
        return int(ExitCode.USAGE)

    if args.command == "next":
        return _next(Path(args.project), paths)
    if args.command == "doctor":
        return _doctor(paths)
    if args.command == "setup":
        return _setup(args, paths)
    if args.command == "manual":
        return _manual(args)
    if args.command == "init":
        return _init(Path(args.project).resolve(), args.force)
    if args.command == "config":
        return _config(args, paths)
    if args.command == "run":
        return _run(args)
    if args.command == "batch":
        return _batch(args, paths)
    if args.command == "tree":
        return _tree(args)
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
    if args.command == "ask":
        return _ask(args, paths)
    if args.command == "limit":
        return _limit(args, paths)
    if args.command == "owner":
        return _owner(args, paths)
    if args.command == "knowledge":
        return _knowledge(args, paths)
    if args.command == "verification":
        return _verification(Path(args.project))
    if args.command == "audit":
        return _audit(args, paths)
    if args.command == "daemon":
        return _daemon(args, paths)

    raise UsageError("unknown-command", args.command)


# --- the sitting -----------------------------------------------------------


def _knowledge(args: argparse.Namespace, paths: Paths) -> int:
    if args.what != "tell":
        raise UsageError("no-what", "knowledge tell — единственное, что делает эта команда")
    return _tell(args, paths)


def _tell(args: argparse.Namespace, paths: Paths) -> int:
    """The owner talks; the kit sorts, asks only what contradicts, and writes.

    Two sources and they are two on purpose. The telling comes from a file or
    from an editor, because it is long and nobody types a paragraph into a
    prompt. The answers come from the terminal and from nowhere else, because a
    sitting is with somebody: if the telling is coming from the standard input,
    there is nobody to answer, and that is printed before the first session
    rather than discovered by a refusal halfway through.
    """
    from ..sitting import Sitting, Telling

    root = Path(args.project).resolve()
    sessions = _sessions(root, args.provider, args.option, args.wait)

    told, from_the_stream = _told(args.telling)
    if from_the_stream:
        print("рассказ читается с потока ввода: ответить на противоречие будет некому.")

    sitting = Sitting(
        root=root,
        sessions=sessions,
        say=print,
        answers=None if from_the_stream else _lines_typed(),
    )
    sitting.hold(Telling(told))
    return int(ExitCode.OK)


# --- the audit -------------------------------------------------------------


def _audit(args: argparse.Namespace, paths: Paths) -> int:
    """One lens over the last commit. It writes two files and changes nothing else.

    The code is zero even when the lens found work: an audit is not a gate. Its
    output is a list of candidates, and a list that turns the build red is a
    list nobody will run twice.
    """
    from ..audit import Audit, lens_named

    root = Path(args.project).resolve()
    Audit(
        root=root,
        lens=lens_named(args.lens),
        sessions=_sessions(root, args.provider, args.option, args.wait),
        say=print,
        out=Path(args.out) if args.out else None,
    ).run()
    return int(ExitCode.OK)


def _told(where: str | None) -> tuple[str, bool]:
    if where == "-":
        return sys.stdin.read(), True
    if where:
        try:
            return Path(where).read_text(encoding="utf-8"), False
        except OSError as unreadable:
            raise UsageError("no-telling", f"{where} не прочитался: {unreadable}") from unreadable
    return _from_an_editor(), False


def _from_an_editor() -> str:
    """What `git commit` does, for the same reason: a paragraph is not typed at a prompt."""
    import subprocess
    import tempfile

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        raise UsageError(
            "no-telling",
            "читать нечего, и $EDITOR не задан",
            hint="agent-kit knowledge tell --from <файл>",
        )
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False, encoding="utf-8") as held:
        held.write(TELLING_HINT)
        path = Path(held.name)
    subprocess.run([*editor.split(), str(path)], check=False)
    text = path.read_text(encoding="utf-8")
    path.unlink(missing_ok=True)
    return "\n".join(line for line in text.splitlines() if not line.startswith("#"))


TELLING_HINT = """# Расскажите про свой продукт — как рассказали бы человеку.
# В любом порядке и любой длины: сортировать будет кит, а не вы.
# Строки, начинающиеся с #, выброшены.

"""


def _lines_typed():
    """One line per question, from the terminal, and nothing buffered ahead."""
    for line in sys.stdin:
        yield line


# --- doctor ----------------------------------------------------------------


def _manual(args) -> int:
    """The one command that runs a proof, and the only one that may.

    Not the door, which reads and never acts; not a night, which would be
    running commands in a working copy it does not hold. A person types this
    where they are standing, and what comes back zero takes its own line away.

    Exit zero whatever it finds: this is a report, and every line of it names
    its own code, which is what a judge reads.
    """
    from ..manual import check

    if args.what != "check":
        raise UsageError("what-of-manual", "agent-kit manual check")

    root = Path(args.project).resolve()
    checked = check(root, timeout=args.timeout or MANUAL_TIMEOUT)
    for key in checked.done:
        print(f"manual-done: {key} — доказательство вернуло ноль, строка снята")
    for key, why in checked.stands:
        print(f"manual-stands: {key} — {why.strip().splitlines()[-1] if why.strip() else 'ничего не сказало'}")
    for key in checked.proves_nothing:
        print(f"manual-proves-nothing: {key} — эта команда не может провалиться, она не запускалась")
    for key, why in checked.by_hand:
        print(f"manual-by-hand: {key} — {why}")
    for key in checked.unclosable:
        print(f"manual-nobody-can-close: {key} — ни команды, ни причины: снять её может только человек")
    if not (checked.done or checked.standing):
        print("руками делать нечего")
    else:
        print(f"снято: {len(checked.done)}; стоит: {checked.standing}")
    return int(ExitCode.OK)


def _next(project: Path, paths: Paths) -> int:
    """The door: one pass over what is on disk, one thing to do, exit zero.

    It exits zero whatever it finds, including a project nothing can be run
    in. Its answer is its output: a door that refuses is a door somebody can
    miss, which is the defect §5 of the plan is written against.
    """
    from ..door import what_now

    print(what_now(project, paths))
    return int(ExitCode.OK)


def _verification(project: Path) -> int:
    """The catalogue, and what this project declared about each kind of it.

    One home printed from one place: the same sentences the driver encloses into
    a design, so nobody has to join the kit's list and the project's answers by
    hand six times a night. It exits zero on a project that has answered nothing
    — the refusals are where the answers are read, and this is the list.
    """
    from ..project import read_project
    from ..verification.said import catalogue_lines

    try:
        declared = read_project(project)
    except ConfigError as unreadable:
        # An answer the kit will not read is worth more than a catalogue: the
        # code is what every other command refuses this project by.
        print(f"{unreadable.code}: {unreadable.detail}", file=sys.stderr)
        return int(unreadable.exit_code)

    print("виды проверки, которые знает этот кит, и что проект говорит о каждом")
    print()
    for line in catalogue_lines(declared):
        print(line)
    return int(ExitCode.OK)


def _doctor(paths: Paths) -> int:
    """What this machine is configured with, and what is missing from it.

    One question per screen. It used to answer three — the machine's
    configuration, the ledger's live picture, and half of whichever project it
    was standing in — which made it a third place that had to agree with
    `agent-kit machine` and with the door. The live picture is `machine`'s and
    the project is `next`'s; what is left here has no other home.

    The ledger's **path** stays, and only the path: nothing else prints it, and
    the hour somebody wants it is the hour the file is not there.

    Since S9a the provider rows are measured rather than listed, and they are
    the same rows `agent-kit setup` prints — one reading, two screens. It writes
    nothing and it spends no quota: the two rungs climbed here are the free ones.

    **It is no longer a command that only reads files, and that is the price.**
    Every call now starts each shipped provider once to ask its version — a
    subprocess per provider, bounded by `VERSION_TIMEOUT`. A listed level is a
    claim and a measured one is not, which is what the price buys; but a screen
    that starts somebody else's binaries is a different kind of screen from the
    one this was, and it is said here rather than discovered by whoever wonders
    why `doctor` reaches a disk.
    """
    from ..setup import read as read_the_machine, render as render_providers

    reading = read_the_machine(paths)
    if reading.unreadable_config is not None:
        # `doctor` has refused a configuration it cannot parse since S0, and it
        # names the key rather than the file: `machine.max_sessions must be at
        # least 1` is what sends somebody to the right line. The door is the one
        # that names it and reads on, because a door that refuses can be missed.
        raise reading.unreadable_config
    config = reading.config

    print("машина")
    print(f"  конфиг      {paths.config_file}  {_present(paths.config_file)}")
    print(f"  состояние   {paths.state_dir}  {_present(paths.state_dir)}")
    print(f"  логи        {paths.log_dir}  {_present(paths.log_dir)}")
    print(f"  секреты     {paths.secrets_file}  {_present(paths.secrets_file)}")
    # The path, not a ledger: building one creates the file, so asking an
    # object for its own path made `missing` a word this line could never
    # print — about the one thing it is here to say.
    from ..machine import ledger_path

    print(f"  леджер      {ledger_path(paths)}  {_present(ledger_path(paths))}")
    print()
    print("метод")
    registry = builtin_registry()
    print(f"  проза       {method_root()}  {_present(method_root())}")
    print(f"  шаги        {', '.join(registry.names())}")
    print()
    print("чем настроена")
    print(f"  сессий сразу {config.machine.max_sessions}")
    print(f"  ждёт до      {config.machine.wait}с слота или сброса лимита")
    print(f"  страница     http://{config.daemon.host}:{config.daemon.port}")
    print(f"  владелец     {_channel_line(config, paths)}")
    print(f"  по умолчанию {config.machine.provider or 'нет — роль, которую таблица не называет, отказана'}")
    print(f"  роли         {', '.join(sorted(config.roles)) or 'нет — каждая роль падает на умолчание'}")
    _named_but_not_there(reading)
    print()
    print("провайдеры")
    for line in render_providers(reading):
        print(line)
    if not reading.working:
        print()
        print(f"  сессию здесь пока запустить нечем: {PROGRAM} setup")
    return int(ExitCode.OK)


def _named_but_not_there(reading) -> None:
    """A role pointed at a provider this kit does not ship, said before a night finds it."""
    shipped = {one.name for one in reading.providers}
    lost = sorted(reading.named_by - shipped)
    if lost:
        print(f"  unknown-provider {', '.join(lost)} — назван здесь, и этот кит его не везёт")


def _present(path: Path) -> str:
    return "есть" if path.exists() else "нет"


# --- setup -----------------------------------------------------------------


def _setup(args: argparse.Namespace, paths: Paths) -> int:
    """The way in. It prints commands and runs none, and it spends no session.

    The answers come from the stream, which is what makes the whole walk
    something the bench can drive — the same reason S8a refused a CLI attached
    to a terminal and held the loop itself.
    """
    from ..setup import walk

    return walk(args.name, ask=_typed, say=print, paths=paths)


# --- init ------------------------------------------------------------------


def _init(root: Path, force: bool) -> int:
    """Read the repository, write the declaration, and name what was not found."""
    from ..hook import WRITTEN, write_pre_push
    from ..project import discover, is_repository, write_project

    if not is_repository(root):
        print(f"{PROGRAM}: not-a-repository: {root} — не рабочее дерево git", file=sys.stderr)
        print("  кит сдаёт на ветке и открывает pull request; для обоих нужно дерево", file=sys.stderr)
        return int(ExitCode.CONFIG)

    project, missing = discover(root)
    path = write_project(project, force=force)
    # The moment a project becomes known to the kit is the moment to put the
    # refusals in. `.git/hooks` is not repository content, so a project whose
    # declaration is committed and cloned arrives with none.
    hook = write_pre_push(root, trunk=project.default_branch)

    print(f"записано {path}")
    print(f"  ветка по умолч. {project.default_branch}")
    for command in project.commands:
        print(f"  {command.name:14}  {command.command}")
    if hook.what == WRITTEN:
        print(f"  pre-push        {hook.path}")
    elif hook.said():
        print(f"{PROGRAM}: pre-push: {hook.said()}", file=sys.stderr)
    if not missing:
        return int(ExitCode.OK)

    for gap in missing:
        print(f"{PROGRAM}: missing: {gap}", file=sys.stderr)
    print(f"  впишите руками: {path}", file=sys.stderr)
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
        raise UsageError(
            "missing-command", "run нужно одно из: new, go, show, start, pass, fail, stop, reopen"
        )

    if what == "new":
        steps = [name.strip() for name in args.steps.split(",")] if args.steps else None
        run = create_run(store, registry, args.slug, steps=steps, brief=args.brief)
        print(f"{run.slug}: создан на {run.branch}, шагов: {len(run.steps)}")
        return int(ExitCode.OK)

    if what == "show":
        run = store.load(args.slug)
        if args.json:
            print(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"{run.slug}  {run.status.value}  {run.branch}")
            if run.brief:
                print(f"  зачем: {run.brief}")
            if run.base:
                print(f"  стоит на: {run.base}")
            if run.tree:
                print(f"  в дереве: {run.tree}")
            if run.needs:
                print(f"  после: {', '.join(run.needs)}")
            for index, step in enumerate(run.steps):
                mark = ">" if index == run.current_step else " "
                reason = f"  {step.reason}" if step.reason else ""
                print(f" {mark} {step.name:12} {step.status.value:8} попыток {step.attempts}{reason}")
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
        print(f"{run.slug}: {run.current.name} идёт (попытка {run.current.attempts})")
        return int(ExitCode.OK)

    if what == "pass":
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.pass_step(args.slug)
        print(f"{run.slug}: {_where(run)}")
        return int(ExitCode.OK)

    if what == "fail":
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.fail_step(args.slug, args.reason)
        print(f"{run.slug}: упал — {run.reason}")
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
            print(f"stop-asked: {args.slug} — драйвер (pid {driving[0].pid}) остановится на границе шага")
            return int(ExitCode.OK)
        run = store.stop(args.slug, args.reason)
        print(f"{run.slug}: остановлен — {run.reason}")
        return int(ExitCode.OK)

    if what == "reopen":
        # A verb of its own, and not something `run go` does after saying so:
        # `go` is what a batch runs for every child, and a `batch go` typed
        # again would then re-pay for steps of features the method stopped on
        # purpose. Going on after a stop is a decision, and a decision has an
        # author — the same reason `refuse_step` and `fail_step` are two words.
        _refuse_if_a_driver_holds_it(store, args.slug)
        run = store.reopen(args.slug)
        print(f"{run.slug}: снова открыт — {_where(run)}")
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
            f"{slug} ведёт процесс {driving[0].pid} с {driving[0].taken_at}",
            hint=f"agent-kit run stop {slug} '<почему>' просит этот драйвер остановиться",
        )


def _go(store: RunStore, registry, args: argparse.Namespace) -> int:
    """Every step that is left, in order, until one will not pass.

    The driver already says why a step failed and leaves the reason in the run.
    This adds nothing to that: it walks, it prints, and it stops.
    """
    run = store.load(args.slug)
    if run.finished:
        raise StateError(
            "run-finished",
            f"{args.slug} — {run.status.value}; гонять больше нечего",
            hint=(
                f"agent-kit run reopen {args.slug} carries it on from the step it stopped on"
                if run.status is RunStatus.STOPPED
                else ""
            ),
        )

    runner = _runner(
        store, registry, args.provider, args.option, wait=args.wait, silent=getattr(args, "silent", False)
    )
    while True:
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  попытка {attempt.attempt} на {attempt.provider}: {mark}")
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

        print(f"{outcome.slug}: {outcome.step} прошёл")
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


def _batch(args: argparse.Namespace, paths: Paths) -> int:
    """An evening's work: several features, and what waits for what."""
    from ..batch import BatchStore, read_declaration, refuse_unless_answered
    from ..project import read_project

    root = Path(args.project).resolve()
    store = BatchStore(root)
    what = args.what
    if what is None:
        raise UsageError(
            "missing-command",
            "batch нужно одно из: compose, new, show, go, stop, skip, reopen",
        )

    if what == "compose":
        return _compose(args, paths, root)

    if what == "new":
        # Three acts in one order: the gate, then the batch, then the file it
        # is written to. Nothing is created while anything is unanswered — no
        # batch, no run, no tree — because a half-made night is a graph
        # somebody has to repair by hand. The write itself is whole or not at
        # all: `BatchStore.save` validates the shape and then replaces the file
        # in one act, so a batch.json half-written by a machine that died is
        # not a state this has to recover from.
        declaration = read_declaration(Path(args.file))
        refuse_unless_answered(declaration, read_project(root))
        batch = store.create(declaration)
        print(f"{batch.name}: создана, фич: {len(batch.features)}")
        for feature in batch.features:
            waits = f" — after {', '.join(feature.needs)}" if feature.needs else ""
            print(f"  {feature.slug}{waits}")
        return int(ExitCode.OK)

    if what == "show":
        batch = store.load(args.name)
        if args.json:
            print(json.dumps(batch.to_dict(), indent=2, ensure_ascii=False))
            return int(ExitCode.OK)
        print(f"{batch.name}  фич: {len(batch.features)}")
        if batch.reason:
            print(f"  {batch.reason}")
        for feature in batch.features:
            waits = f"  needs {', '.join(feature.needs)}" if feature.needs else ""
            said_why = f"  {feature.reason}" if feature.reason else ""
            print(f"  {feature.slug:20} {feature.status.value:9}{waits}{said_why}")
            if feature.pull_request:
                print(f"    {feature.pull_request}")
        return int(ExitCode.OK)

    if what == "go":
        return _batch_go(args, paths, root, store)

    if what == "stop":
        # One writer per batch, the way there is one per run: if a driver holds
        # it, the stop is posted where that driver reads it.
        driving = _driving_batch(root, args.name)
        if driving:
            _ledger(paths).ask_stop(str(root), args.name, reason=args.reason)
            print(f"stop-asked: {args.name} — драйвер (pid {driving[0].pid}) встанет, когда встанут дети")
            return int(ExitCode.OK)
        batch = store.load(args.name)
        batch.reason = args.reason
        store.save(batch)
        print(f"{args.name}: остановлена — {args.reason}")
        return int(ExitCode.OK)

    if what == "skip":
        driving = _driving_batch(root, args.name)
        if driving:
            _ledger(paths).ask_skip(str(root), args.name, args.feature, reason=args.reason)
            print(f"skip-asked: {args.feature} — драйвер (pid {driving[0].pid}) прочтёт это между шагами")
            return int(ExitCode.OK)
        batch = store.load(args.name)
        taken = batch.skip(args.feature, args.reason)
        store.save(batch)
        # Said at the moment it is typed: a person who wanted one feature
        # dropped and got three must hear it now, not in a report afterwards.
        print(f"{args.name}: пропускаем {', '.join(taken)} — {args.reason}")
        return int(ExitCode.OK)

    if what == "reopen":
        # Not posted to a running driver, the way a skip is: that driver read
        # the record when it started, and a night already under way is not
        # where a person decides what last night's stop is worth.
        driving = _driving_batch(root, args.name)
        if driving:
            raise StateError(
                "batch-held-elsewhere",
                f"{args.name} ведёт процесс {driving[0].pid} с {driving[0].taken_at};"
                " фичу продолжают между ночами, а не во время одной",
                hint=f"agent-kit batch stop {args.name} '<почему>' просит этот драйвер остановиться",
            )
        batch = store.load(args.name)
        given = batch.reopen(args.feature)
        # The run as well as the record: `batch go` reads a child's ending off
        # its run, so a feature whose run is still stopped comes straight back
        # stopped without a session being run at all.
        runs = RunStore(root)
        for slug in given:
            if runs.exists(slug) and runs.load(slug).status is RunStatus.STOPPED:
                runs.reopen(slug)
        store.save(batch)
        # Said now rather than in a report, for the reason a skip says it now.
        print(f"{args.name}: строим заново — {', '.join(given)}")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"batch {what}")


def _compose(args: argparse.Namespace, paths: Paths, root: Path) -> int:
    """The evening, composed in front of the person whose evening it is.

    Two sources and they are two on purpose, exactly as they are for the hour
    about the product: the telling comes from a file or an editor, because it is
    long; the answers come from the terminal and from nowhere else, because a
    sitting is with somebody. Where the telling is coming from the standard
    input there is nobody to answer, and that is printed before the first
    session rather than discovered by a refusal halfway through.
    """
    from ..batch.composing import ComposingSitting
    from ..sitting import Telling

    told, from_the_stream = _told(args.telling)
    if from_the_stream:
        print("рассказ читается с потока ввода: ответить на противоречие будет некому.")

    sitting = ComposingSitting(
        args.name,
        root=root,
        sessions=_sessions(root, args.provider, args.option, args.wait),
        say=print,
        answers=None if from_the_stream else _lines_typed(),
        out=Path(args.out) if args.out else None,
    )
    sitting.hold(Telling(told))
    return int(ExitCode.OK)


def _batch_go(args: argparse.Namespace, paths: Paths, root: Path, store) -> int:
    from ..batch import BatchDriver, FeatureStatus

    config = load_config(paths.config_file)
    ledger = _ledger(paths)
    outcome = BatchDriver(
        project=root,
        store=store,
        runs=RunStore(root),
        registry=builtin_registry(),
        ledger=ledger,
        ceilings=_ceilings(config),
        owner=_owner_of(config, paths, ledger),
        options=args.option,
        provider=args.provider,
        say=print,
    ).go(args.name)

    for feature in outcome.batch.features:
        print(f"{feature.slug}: {feature.status.value}{'  ' + feature.pull_request if feature.pull_request else ''}")
    for conflict in outcome.conflicts:
        print(f"не сольётся: {conflict.said()}", file=sys.stderr)

    if outcome.interrupted:
        return int(ExitCode.INTERRUPTED)
    behind = outcome.batch.first_that_did_not_land()
    if behind is None or all(
        feature.status in (FeatureStatus.DONE, FeatureStatus.SKIPPED) for feature in outcome.batch.features
    ):
        # A skipped feature is the owner's own decision, and a night that did
        # everything it was allowed to do did not fail at anything.
        return int(ExitCode.OK)
    # Otherwise the code of the first feature that did not land, with the
    # meaning that code already has. A batch does not invent one for "some of
    # it worked": that is what the report above is for.
    print(f"{outcome.batch.name}: {behind.slug} — {behind.reason or behind.status.value}", file=sys.stderr)
    if behind.status is FeatureStatus.PENDING:
        # Nothing was attempted for it: the machine had no room, or no agent
        # could be run at all. That is the code a lone run leaves for the same
        # thing, and `batch go` again is what answers it — not a person looking
        # for a state that refused something.
        return int(ExitCode.PROVIDER)
    return int(ExitCode.STATE)


def _driving_batch(root: Path, name: str) -> list:
    """The lease a driver holds on this batch right now, if any."""
    ledger = _ledger(Paths.from_env())
    return [lease for lease in ledger.batches() if lease.slug == name and lease.project == str(root)]


def _tree(args: argparse.Namespace) -> int:
    """The working copies this project's runs build in."""
    from ..driver.tree import remove_tree, trees

    root = Path(args.project).resolve()
    what = args.what
    if what is None:
        raise UsageError("missing-command", "tree нужно одно из: list, remove")

    if what == "list":
        standing = trees(root)
        if not standing:
            print("деревьев нет")
        for slug, where, branch in standing:
            print(f"{slug:20} {branch:24} {where}")
        return int(ExitCode.OK)

    if what == "remove":
        gone = remove_tree(root, args.slug)
        print(f"{args.slug}: {'убрано; работа остаётся на ветке' if gone else 'дерева с таким именем нет'}")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"tree {what}")


def _step(args: argparse.Namespace, paths: Paths) -> int:
    registry = builtin_registry()
    what = args.what
    if what is None:
        raise UsageError("missing-command", "step нужно одно из: list, show, input, run")

    if what == "list":
        for definition in registry.all():
            print(f"{definition.name:12} {definition.role:10} {definition.title}")
        return int(ExitCode.OK)

    if what == "show":
        definition = registry.get(args.name)
        print(f"{definition.name} — {definition.title}")
        print(f"  роль      {definition.role}")
        prose = (
            str(method_root() / definition.method)
            if definition.method
            else f"нет — {definition.executor} это программа, а программе инструкций не читают"
        )
        print(f"  проза     {prose}")
        print()
        print("возвращает:")
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
            raise StateError("run-finished", f"{args.slug} — {run.status.value}; следующего шага нет")
        index = run.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{args.slug}: ни один шаг не ждёт запуска")
        definition = registry.get(run.steps[index].name)
        # What the *driver* would enclose, which is what this command says it
        # prints. It used to compose with no enclosures at all, so a person
        # reading it was shown neither what earlier steps returned nor the index
        # of the knowledge — the two things the driver puts in front of a
        # session so that nobody has to go looking. A command that answers a
        # different question from the one in its own help is the shape of defect
        # this plan is written against.
        driver = StepRunner(store=store, registry=registry, executors={})
        enclosures, _ = driver.enclosures(run, index, definition)
        print(
            compose_input(
                run=run,
                definition=definition,
                attempt=1,
                provider=args.provider,
                enclosures=enclosures,
                contract=definition.contract_in(driver.keeps_knowledge(run)),
            )
        )
        return int(ExitCode.OK)

    if what == "run":
        runner = _runner(
        store, registry, args.provider, args.option, wait=args.wait, silent=getattr(args, "silent", False)
    )
        outcome = runner.run_next(args.slug)
        for attempt in outcome.attempts:
            mark = "passed" if attempt.passed else f"refused — {attempt.refusal}"
            print(f"  попытка {attempt.attempt} на {attempt.provider}: {mark}")
        if outcome.passed:
            print(f"{outcome.slug}: {outcome.step} прошёл")
            return int(ExitCode.OK)
        print(f"{outcome.slug}: {outcome.reason}", file=sys.stderr)
        return int(ExitCode.INTERRUPTED if outcome.interrupted else ExitCode.STATE)

    raise UsageError("unknown-command", f"step {what}")


def _provider(args: argparse.Namespace, paths: Paths) -> int:
    """One thing, and it is the one that spends. `list` died into the reading.

    Where the machine's standing is printed is `doctor`; where it is changed is
    `setup`. What is left here is the ladder above the free rungs — the one
    question about a provider that costs a real session — and that is why it is
    still its own command rather than a flag on either of them.
    """
    what = args.what
    if what is None:
        raise UsageError(
            "missing-command",
            "provider нужно одно: check",
            hint=f"{PROGRAM} doctor — что есть у этой машины; {PROGRAM} setup — как это изменить",
        )
    if what != "check":
        raise UsageError("unknown-command", f"provider {what}")
    return _provider_check(args)


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
    if what not in ("run", "disarm"):
        raise UsageError("unknown-command", f"bench {what}")

    if only is not None:
        if only not in names:
            raise UsageError("unknown-case", f"{only!r} — не случай: {', '.join(names) or 'их нет вовсе'}")
        names = [only]

    if what == "disarm":
        return _bench_disarm(root, names)

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
                print(f"{'':38}  осталось в {result.where}")

    fired = [result for result in results if result.verdict.fired]
    broken = [result for result in results if not result.verdict.judged]
    print()
    print(f"механизмов сработало: {len(fired)} из {len(results)}")
    if broken:
        print(f"не удалось судить: {len(broken)}, значит стенд ответил про {len(results) - len(broken)}")
        return int(ExitCode.BROKEN_BENCH)
    return int(ExitCode.OK if len(fired) == len(results) else ExitCode.BENCH)


def _bench_disarm(root: Path, names: list[str]) -> int:
    """Every case with its trap taken away, and one that still fires is a regression.

    The same two codes the bench itself uses, meaning the same two things. A
    case that fires against a world with nothing planted in it is not reading
    its trap, and somebody has to make its judge read one. A check that could
    not answer is the instrument being wrong, and nothing was measured.
    """
    from tempfile import TemporaryDirectory

    from ..bench import check_named
    from ..bench.disarm import ARMED, NOT_DISARMABLE, STILL_FIRES, UNCHECKABLE

    said = []
    with TemporaryDirectory(prefix="agent-kit-disarm-") as scratch:
        for name in names:
            answer = check_named(root, name, Path(scratch) / name)
            said.append(answer)
            print(f"{answer.name:38}  {answer.said}")

    counted = {state: [one for one in said if one.state == state] for state in
               (ARMED, STILL_FIRES, NOT_DISARMABLE, UNCHECKABLE)}
    print()
    print(f"перестают срабатывать без ловушки: {len(counted[ARMED])} из {len(said)}")
    if counted[NOT_DISARMABLE]:
        print(f"{len(counted[NOT_DISARMABLE])} говорят словами, почему честно отнять нечего")
    if counted[UNCHECKABLE]:
        print(f"{len(counted[UNCHECKABLE])} не проверить, значит стенд ответил про остальные")
        return int(ExitCode.BROKEN_BENCH)
    return int(ExitCode.OK if not counted[STILL_FIRES] else ExitCode.BENCH)


def _bench_list(root: Path, names: list[str], read_case, CaseError) -> int:
    """Every case and the mechanism it plants. One unreadable case hides none of the others."""
    broken = []
    for name in names:
        try:
            case = read_case(root, name)
        except CaseError as unreadable:
            broken.append(name)
            print(f"{name:38}  не читается — {unreadable.code}: {unreadable.detail}")
            continue
        print(f"{name:38}  {case.title}")
        print(f"{'':38}  срабатывает: {case.fires}")
    return int(ExitCode.BROKEN_BENCH if broken else ExitCode.OK)


def _sessions(root: Path, provider: str | None, options: list[str], wait: int | None = None):
    """The chain, the slot and the pause, configured the way a run configures them.

    The same object a driver holds, built from the same machine and the same
    role table: a sitting must not be able to slip past a ceiling a run cannot,
    and a second way of building one is a second place for that to be true.
    """
    from ..driver.session import Sessions

    runner = _runner(RunStore(root), builtin_registry(), provider, options, wait=wait, silent=True)
    return runner.sessions


def _runner(store: RunStore, registry, provider: str | None, options: list[str],
            wait: int | None = None, silent: bool = False) -> StepRunner:
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
        backoff=config.machine.backoff,
        say=print,
        owner=_owner_of(config, paths, ledger, silent=silent),
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
    # And the machine's own default, which is what a role the table does not
    # name falls back to. It has to join the executors as well as the argument:
    # `session.py` refuses `unknown-provider` for a default nothing was built
    # for, which would be a correctly configured machine refused by name.
    if config.machine.provider:
        named |= {config.machine.provider}
    executors.update(
        {name: providers.build_executor(name, _settings(config, name, typed)) for name in sorted(named)}
    )
    return StepRunner(
        store=store,
        registry=registry,
        executors=executors,
        roles=roles,
        default_provider=config.machine.provider or None,
        **machine,
    )


def _owner_of(config: Config, paths: Paths, ledger, silent: bool = False) -> object:
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
    # `silent` is somebody else speaking for this run — a batch, which sends one
    # message for all of its features rather than waking a phone once each. A
    # question still goes out: it has a deadline against a person, and holding
    # it back would be a second kind of waiting on top of the one S7a measured.
    return Owner(channel=channel, ledger=ledger, wait=config.owner.wait, say=print, quiet=silent)


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
            raise UsageError("bad-option", f"{pair!r} — не КЛЮЧ=ЗНАЧЕНИЕ")
        parsed.setdefault(key.strip(), []).append(value)
    return parsed


def _provider_check(args: argparse.Namespace) -> int:
    """The ladder, printed. A level nobody measured is a claim, not a fact."""
    from ..driver.check import check_provider
    from ..providers.process import tail

    report = check_provider(
        args.name, _options(args.option), project=Path(args.project).resolve(), remember=True
    )

    for rung in report.rungs:
        mark = "ok  " if rung.passed else ("--  " if not rung.applies else "no  ")
        print(f"  {mark}{rung.name:10} {rung.detail}")
    print()

    if report.said:
        # The end of it, not the beginning. A CLI puts its banner first and its
        # reason last, and the owner's first live climb printed the banner and
        # cut off before the 401 — the cause had to be found by running the tool
        # by hand. This is the screen somebody typed to get a diagnosis, so it
        # carries more than a night's log line does.
        print("  что сказала сессия, последние строки:")
        for line in tail(report.said).splitlines():
            print(f"    {line}")
        print()

    if report.level is None:
        # The code, and it is the walk's own: a judge reads a code, and this is
        # the same state `agent-kit setup` refuses by name. Two commands looking
        # at one ladder must not call its answer two different things.
        print(
            f"{PROGRAM}: provider-not-ready: {args.name} споткнулся на ступени `{report.failed}`",
            file=sys.stderr,
        )
        return int(ExitCode.PROVIDER)

    print(f"{args.name}: {report.level}, объявлен {report.declared_level}")
    if report.facts.observed:
        share = report.facts.context_share or 0
        print(f"  контекст  {report.facts.context_used:,} из {report.facts.context_window:,} ({share:.1%})")
    if report.facts.transcript:
        print(f"  сессия    {report.facts.session}")
        print(f"  запись    {report.facts.transcript}")
    if not report.earns_what_it_declares:
        print(
            f"{args.name}: объявлен {report.declared_level}, а заработал {report.level}"
            f" — споткнулся на {report.failed}",
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

    print("идут")
    for row in picture.held:
        print(f"  {row.slug:20} {row.step:10} {row.provider:12} {row.account:12} с {row.taken_at}")
    if not picture.held:
        print("  ничего не идёт")

    print()
    print("в очереди")
    for row in picture.queue:
        print(f"  {row.slug:20} {row.step:10} {row.account:12} попросил в {row.asked_at}")
    if not picture.queue:
        print("  никто не ждёт")

    print()
    print("исчерпаны")
    for row in picture.limits:
        guessed = f"  (an hour, guessed from {row.said!r})" if row.guessed else ""
        print(f"  {row.account:20} до {row.until}   узнал {row.said_by}{guessed}")
    if not picture.limits:
        print("  ни один аккаунт не исчерпан")

    print()
    print("ждут владельца")
    for row in ledger.waiting_on_the_owner():
        print(f"  {row.id:8} {row.slug:16} {row.step:10} до {row.until}")
        print(f"           {row.question}")
        print(f"           без ответа возьмёт: {row.default}")
    if not ledger.waiting_on_the_owner():
        print("  ни одного вопроса не стоит")

    print()
    print("прогоны под драйвером")
    for row in runs:
        print(f"  {row.slug:20} {row.project}  since {row.taken_at}")
    if not runs:
        print("  никого не ведут")

    print()
    print("рабочие копии, в которых строят")
    checkouts = ledger.checkouts()
    for row in checkouts:
        print(f"  {row.slug:20} {row.project}  since {row.taken_at}")
    if not checkouts:
        print("  ни один прогон не строит в самой копии проекта")

    print()
    print("партии под драйвером здесь")
    batches = ledger.batches()
    for row in batches:
        print(f"  {row.slug:20} {row.project}  since {row.taken_at}")
    if not batches:
        print("  ни одна партия не идёт")
    return int(ExitCode.OK)


def _slot(args: argparse.Namespace, paths: Paths) -> int:
    """A slot by hand. Its readers are a person diagnosing a stuck machine and the bench."""
    from ..machine import Want

    what = args.what
    if what is None:
        raise UsageError("missing-command", "slot нужно одно из: take, wants, hold, release")

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
        print(f"{args.slug}: держит слот на {args.provider} до {got.expires_at}")
        return int(ExitCode.OK)

    if what == "wants":
        ledger.wants_one(
            Want(
                account=args.account or args.provider,
                provider=args.provider,
                project=project,
                slug=args.slug,
                step=args.step,
                **({"pid": args.pid} if args.pid is not None else {}),
            )
        )
        print(f"{args.slug}: стоит в очереди за {args.account or args.provider}")
        return int(ExitCode.OK)

    if what == "hold":
        take = ledger.hold_checkout if args.checkout else ledger.hold_run
        held = take(project, args.slug, pid=args.pid)
        if not held.granted:
            raise StateError(held.code, held.detail)
        what_is_held = "the working copy" if args.checkout else "the run"
        print(f"{args.slug}: {what_is_held} держит процесс {held.pid}")
        return int(ExitCode.OK)

    if what == "release":
        for lease in ledger.held() + ledger.runs() + ledger.checkouts():
            if lease.slug == args.slug and lease.project == project:
                ledger.release(lease)
                print(f"{args.slug}: {lease.kind} отдан обратно")
                return int(ExitCode.OK)
        raise StateError("no-such-slot", f"здесь никто не держит ни слота, ни прогона для {args.slug!r}")

    raise UsageError("unknown-command", f"slot {what}")


def _ask(args: argparse.Namespace, paths: Paths) -> int:
    """Вопрос руками. Читатели те же, что у `slot hold`: стенд и человек.

    Стенду нужно встать там, где стоял бы драйвер — оставить строку, какую он
    оставил бы, умерев. Человеку нужен выход, когда вопрос завис и прогона за
    ним уже нет: то же, чем `limit clear` отвечает на лимит, который не снялся.
    """
    from ..machine import Ask
    from ..machine.ledger import after

    what = args.what
    if what is None:
        raise UsageError("missing-command", "ask нужно одно из: plant, clear")
    ledger = _ledger(paths)

    if what == "plant":
        held = ledger.asked(
            Ask(
                id=args.id, project=str(Path(args.project).resolve()), slug=args.slug, step=args.step,
                question=args.question, default=getattr(args, "default"),
                until=args.until or after(3600), message=args.message,
            )
        )
        print(f"{held.id} {held.slug}/{held.step} до {held.until} сообщение {held.message or 'без номера'}")
        return int(ExitCode.OK)

    if what == "clear":
        ledger.forget([args.id])
        print(f"{args.id}: снят")
        return int(ExitCode.OK)

    raise UsageError("unknown-command", f"ask {what}")


def _limit(args: argparse.Namespace, paths: Paths) -> int:
    what = args.what
    if what is None:
        raise UsageError("missing-command", "limit нужно одно из: set, clear")

    ledger = _ledger(paths)
    if what == "set":
        until = _a_time(args.until)
        held = ledger.limit(args.account, until=until, said_by=args.said_by)
        guessed = " (an hour, guessed)" if held.guessed else ""
        print(f"{held.account}: исчерпан до {held.until}{guessed}")
        return int(ExitCode.OK)

    if what == "clear":
        ledger.unlimit(args.account)
        print(f"{args.account}: снова отвечает")
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
            "bad-time", f"{value!r} — не время: пишите как 2026-08-24T17:00:00+00:00"
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
        raise UsageError("missing-command", "owner нужно одно из: setup, check, say, set-token")

    if what == "setup":
        # Из модуля, а не из пакета: `owner.setup` — это модуль, и одноимённое
        # имя в пакете затирало бы его собой.
        from ..owner.setup import setup as set_the_channel_up

        set_the_channel_up(ask=_typed, say=print, paths=paths)
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
        print(f"{PROGRAM}: no-channel: у этой машины нет канала к владельцу", file=sys.stderr)
        print("  каждый вопрос сразу берёт умолчание, и умолчание записывается", file=sys.stderr)
        print("  agent-kit owner setup заводит его целиком: бот, токен, чат", file=sys.stderr)
        return int(ExitCode.CONFIG)

    channel = open_channel(config.owner, paths.secrets_file)
    if what == "say":
        channel.send(args.text)
        print(f"сказано через {channel.name}")
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
        print(f"процесс    {'поднят, pid ' + str(held) if held else 'не запущен'}")
        return int(ExitCode.OK)

    if what == "install":
        path = unit_path(Path.home())
        path.parent.mkdir(parents=True, exist_ok=True)
        # The command this machine actually has, so the unit does not point at
        # whatever happened to be argv[0] the day it was written.
        binary = shutil.which(PROGRAM) or _sys.argv[0] or PROGRAM
        path.write_text(unit_file(binary), encoding="utf-8")
        print(f"записано {path}")
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
                    f"{pid_file} называет процесс {written}, а это не демон agent-kit",
                    hint=f"удалите {pid_file}, если уверены, что демона больше нет",
                )
            raise StateError("no-daemon", "здесь ничего не запущено; леджер в любом случае не тронут")
        try:
            os.kill(held, signal.SIGTERM)
        except (ProcessLookupError, PermissionError) as refused:
            raise StateError("not-ours", f"процесс {held} не принял сигнал: {refused}") from refused
        print(f"демона (pid {held}) попросили уйти")
        return int(ExitCode.OK)

    if what != "start":
        raise UsageError("unknown-command", f"daemon {what}")

    held = running()
    if held is not None:
        raise StateError("already-running", f"демон уже поднят, pid {held}")

    if not args.foreground:
        child = subprocess.Popen(
            [_sys.executable, "-m", "agent_kit", "daemon", "start", "--foreground"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"демон поднят, pid {child.pid}; страница на {where}")
        return int(ExitCode.OK)

    paths.ensure()
    print(f"страница на {where}", flush=True)
    run_forever(_ledger(paths), config.daemon.host, config.daemon.port, pid_file)
    return int(ExitCode.OK)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
