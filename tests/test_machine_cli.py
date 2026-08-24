"""S7 — what a person types at the machine, and what the page answers.

The commands here are an operator's surface, not a door of the method: they
show what is held, they hand a slot to a script that is standing in for a
driver, and they post a stop where the run's own driver reads it.
"""

import json
import os
import time
from pathlib import Path

import pytest

from agent_kit.cli.main import main
from agent_kit.config import DEFAULT_WAIT, load_config
from agent_kit.errors import ExitCode
from agent_kit.machine import Ledger, Want, ledger_path
from agent_kit.paths import Paths

from conftest import reset_at


@pytest.fixture
def machine(tmp_path, monkeypatch, machine_home):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path / "project")
    return tmp_path


@pytest.fixture
def ledger(machine):
    return Ledger(ledger_path(Paths.from_env()))


def run(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- the configuration finally has a reader ---------------------------------


def test_the_machine_can_say_how_long_a_run_waits(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[machine]\nmax_sessions = 2\nwait = 60\n", encoding="utf-8")

    config = load_config(path)

    assert (config.machine.max_sessions, config.machine.wait) == (2, 60)


def test_waiting_has_a_default_so_nobody_has_to_choose_one(tmp_path):
    assert load_config(tmp_path / "nothing.toml").machine.wait == DEFAULT_WAIT


def test_the_page_is_a_choice_of_this_machine(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[daemon]\nhost = "0.0.0.0"\nport = 8081\n', encoding="utf-8")

    config = load_config(path)

    assert (config.daemon.host, config.daemon.port) == ("0.0.0.0", 8081)


def test_the_page_answers_on_loopback_unless_it_is_told_otherwise(tmp_path):
    daemon = load_config(tmp_path / "nothing.toml").daemon

    assert (daemon.host, daemon.port) == ("127.0.0.1", 8080)


# --- what a person reads -----------------------------------------------------


def test_machine_prints_what_is_held_queued_and_limited(machine, ledger, capsys):
    ledger.take(Want(account="anthropic", provider="claude_code", project="/p", slug="one", step="build"),
                _four())
    ledger.wants_one(Want(account="anthropic", provider="claude_code", project="/p", slug="two", step="build"))
    resets = reset_at()
    ledger.limit("openai", until=resets, said_by="three/build")

    code, out, _ = run(["machine"], capsys)

    assert code == ExitCode.OK
    assert "one" in out and "two" in out
    assert "openai" in out and resets[11:16] in out


def test_machine_says_so_plainly_when_nothing_is_happening(machine, ledger, capsys):
    code, out, _ = run(["machine"], capsys)

    assert code == ExitCode.OK
    assert "nothing" in out.lower()


def test_doctor_says_where_the_ledger_is(machine, capsys):
    code, out, _ = run(["doctor"], capsys)

    assert code == ExitCode.OK
    assert "daemon.sqlite" in out


# --- a slot by hand ----------------------------------------------------------


def test_a_slot_can_be_taken_and_given_back_by_hand(machine, ledger, capsys):
    code, out, _ = run(["slot", "take", "--provider", "fake", "--slug", "by-hand"], capsys)

    assert code == ExitCode.OK
    assert [row.slug for row in ledger.held()] == ["by-hand"]

    code, _, _ = run(["slot", "release", "--slug", "by-hand"], capsys)

    assert code == ExitCode.OK
    assert ledger.held() == []


def test_a_slot_that_cannot_be_had_is_refused_by_name(machine, ledger, capsys):
    ledger.take(Want(account="fake", provider="fake", project="/p", slug="holder", step="build"), _four())

    code, _, err = run(
        ["slot", "take", "--provider", "fake", "--slug", "second", "--machine-max", "1"], capsys
    )

    assert code == ExitCode.PROVIDER
    assert "no-slot" in err


def test_a_slot_taken_by_hand_lives_as_long_as_it_was_asked_for(machine, ledger, capsys):
    run(["slot", "take", "--provider", "fake", "--slug", "brief", "--ttl", "0"], capsys)

    assert ledger.held() == [], "a lease with no life left outlived itself"


def test_a_slot_can_be_held_for_a_process_that_is_not_this_one(machine, ledger, capsys):
    """What the bench needs: a lease held by a driver that is alive and is not the run."""
    code, _, _ = run(["slot", "take", "--provider", "fake", "--slug", "somebody", "--pid", "1"], capsys)

    assert code == ExitCode.OK
    assert [row.pid for row in ledger.held()] == [1]


def test_a_run_can_be_held_by_hand_so_a_second_driver_meets_the_first(machine, ledger, capsys):
    code, _, _ = run(["slot", "hold", "--slug", "add-vat", "--pid", "1"], capsys)

    assert code == ExitCode.OK
    assert [row.slug for row in ledger.runs()] == ["add-vat"]


def test_a_run_held_by_hand_does_not_fill_the_machine(machine, ledger, capsys):
    run(["slot", "hold", "--slug", "add-vat", "--pid", "1"], capsys)

    assert ledger.held() == []


# --- a limit by hand ---------------------------------------------------------


def test_a_limit_can_be_set_and_cleared_by_hand(machine, ledger, capsys):
    code, _, _ = run(["limit", "set", "anthropic", "--until", reset_at()], capsys)

    assert code == ExitCode.OK
    assert [row.account for row in ledger.limits()] == ["anthropic"]

    code, _, _ = run(["limit", "clear", "anthropic"], capsys)

    assert code == ExitCode.OK
    assert ledger.limits() == []


def test_a_limit_that_is_not_a_time_is_refused_before_it_is_written(machine, ledger, capsys):
    code, _, err = run(["limit", "set", "anthropic", "--until", "half past nine"], capsys)

    assert code == ExitCode.USAGE
    assert "bad-time" in err
    assert ledger.limits() == []


# --- stop --------------------------------------------------------------------


def test_stopping_a_run_nobody_is_driving_writes_the_state(machine, capsys, tmp_path):
    run(["run", "new", "add-vat", "--steps", "probe"], capsys)

    code, out, _ = run(["run", "stop", "add-vat", "the owner said so"], capsys)

    assert code == ExitCode.OK
    state = json.loads((tmp_path / "project/.agent-kit/v3/runs/add-vat/run.json").read_text())
    assert state["status"] == "stopped"


def test_stopping_a_run_a_driver_holds_posts_it_where_the_driver_reads_it(machine, ledger, capsys, tmp_path):
    run(["run", "new", "add-vat", "--steps", "probe"], capsys)
    ledger.hold_run(str((tmp_path / "project").resolve()), "add-vat", pid=1)

    code, out, _ = run(["run", "stop", "add-vat", "the owner said so"], capsys)

    assert code == ExitCode.OK
    assert "driver" in out
    state = json.loads((tmp_path / "project/.agent-kit/v3/runs/add-vat/run.json").read_text())
    assert state["status"] == "created", "the state was written under a driver that is still writing it"
    assert ledger.stop_asked(str((tmp_path / "project").resolve()), "add-vat") == "the owner said so"


# --- the page ----------------------------------------------------------------


def test_the_page_shows_what_the_ledger_holds(machine, ledger):
    from agent_kit.daemon import page

    ledger.take(Want(account="anthropic", provider="claude_code", project="/p", slug="one", step="build"),
                _four())

    html = page(ledger)

    assert "one" in html and "claude_code" in html
    assert "<html" in html.lower()


def test_the_page_has_nothing_to_press(machine, ledger):
    """Read-only until somebody asks for more: every button is a way to break a night."""
    from agent_kit.daemon import page

    html = page(ledger).lower()

    assert "<form" not in html and "<button" not in html


def test_what_the_page_polls_is_the_picture_and_nothing_else(machine, ledger):
    from agent_kit.daemon import as_json

    ledger.wants_one(Want(account="anthropic", provider="claude_code", project="/p", slug="two", step="build"))

    answered = json.loads(as_json(ledger))

    assert [row["slug"] for row in answered["queue"]] == ["two"]
    assert answered["held"] == [] and answered["limits"] == []


def test_the_daemon_says_where_it_would_answer(machine, capsys):
    code, out, _ = run(["daemon", "status"], capsys)

    assert code == ExitCode.OK
    assert "8080" in out


def test_the_unit_starts_the_daemon_this_machine_has(machine, capsys, tmp_path):
    code, out, _ = run(["daemon", "install"], capsys)

    assert code == ExitCode.OK
    unit = (tmp_path / "home/.config/systemd/user/agent-kit.service").read_text()
    assert "daemon start" in unit
    assert "systemctl --user enable" in out


def _four():
    from agent_kit.machine import Ceilings

    return Ceilings(max_sessions=4)


# --- the process actually going away ----------------------------------------


def test_the_daemon_goes_away_when_it_is_asked_to(tmp_path, machine_home):
    """A shutdown asked for from the signal handler on the thread that is serving

    deadlocks: `serve_forever` cannot come back while the handler that is
    stopping it is standing on its stack. The daemon then ignores every stop
    and the port stays held until somebody kills it.
    """
    import signal
    import socket
    import subprocess
    import sys
    import time

    home = tmp_path / "home"
    (home / ".config/agent-kit").mkdir(parents=True)
    port = _a_free_port()
    (home / ".config/agent-kit/config.toml").write_text(
        f'[daemon]\nport = {port}\n', encoding="utf-8"
    )
    env = {
        "HOME": str(home), "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    child = subprocess.Popen(
        [sys.executable, "-m", "agent_kit", "daemon", "start", "--foreground"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for(port)
        child.send_signal(signal.SIGTERM)
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        raise AssertionError("the daemon was asked to stop and did not")
    finally:
        if child.poll() is None:
            child.kill()

    assert child.returncode == 0
    assert not (home / ".local/state/agent-kit/daemon.pid").exists()


def test_the_page_answers_while_the_daemon_is_up(tmp_path, machine_home):
    import socket
    import subprocess
    import sys
    import urllib.request

    from agent_kit.machine import Ceilings, Ledger, Want

    home = tmp_path / "home"
    (home / ".config/agent-kit").mkdir(parents=True)
    port = _a_free_port()
    (home / ".config/agent-kit/config.toml").write_text(f'[daemon]\nport = {port}\n', encoding="utf-8")
    # A page asked what it holds while it holds nothing answers the same as a
    # page that cannot read the ledger at all.
    Ledger(home / ".local/state/agent-kit/daemon.sqlite").take(
        Want(account="fake", provider="fake", project="/p", slug="running", step="build", pid=1),
        Ceilings(max_sessions=4),
    )
    env = {
        "HOME": str(home), "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    child = subprocess.Popen(
        [sys.executable, "-m", "agent_kit", "daemon", "start", "--foreground"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for(port)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as answer:
            html = answer.read().decode("utf-8")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as answer:
            said = json.loads(answer.read().decode("utf-8"))
    finally:
        child.kill()
        child.wait(timeout=10)

    assert "agent-kit" in html and "running" in html
    assert [row["slug"] for row in said["held"]] == ["running"]


def _a_free_port() -> int:
    import socket

    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        return held.getsockname()[1]


def _wait_for(port: int, seconds: float = 10.0) -> None:
    import socket
    import time

    until = time.monotonic() + seconds
    while time.monotonic() < until:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise AssertionError(f"nothing ever answered on {port}")


# --- the review round --------------------------------------------------------


def test_a_daemon_that_cannot_bind_leaves_the_standing_one_addressable(tmp_path, machine_home):
    """It wrote its pid, failed to bind, and its `finally` unlinked the pid file.

    After that `daemon status` says nothing is running and `daemon stop` says
    there is nothing to stop, while the port stays held by a daemon nobody can
    address any more.
    """
    import socket

    from agent_kit.daemon import run_forever
    from agent_kit.machine import Ledger

    held = socket.socket()
    held.bind(("127.0.0.1", 0))
    held.listen(1)
    port = held.getsockname()[1]

    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("4242", encoding="utf-8")
    try:
        with pytest.raises(OSError):
            run_forever(Ledger(tmp_path / "daemon.sqlite"), "127.0.0.1", port, pid_file)
    finally:
        held.close()

    assert pid_file.read_text().strip() == "4242", "it took the standing daemon's record with it"


def test_the_daemon_is_stopped_by_the_door_a_person_uses(tmp_path, machine_home, capsys):
    """The signal is proven; `agent-kit daemon stop` is the thing anybody types."""
    import subprocess
    import sys
    import time

    home = tmp_path / "home"
    (home / ".config/agent-kit").mkdir(parents=True)
    port = _a_free_port()
    (home / ".config/agent-kit/config.toml").write_text(f"[daemon]\nport = {port}\n", encoding="utf-8")
    env = {
        "HOME": str(home), "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    child = subprocess.Popen(
        [sys.executable, "-m", "agent_kit", "daemon", "start", "--foreground"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for(port)
        stopped = subprocess.run(
            [sys.executable, "-m", "agent_kit", "daemon", "stop"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert stopped.returncode == 0, stopped.stderr
        child.wait(timeout=15)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)

    assert child.returncode == 0


def test_stopping_a_daemon_that_is_not_there_is_refused_by_name(machine, capsys):
    code, _, err = run(["daemon", "stop"], capsys)

    assert code == ExitCode.STATE
    assert "no-daemon" in err


def test_the_sweeper_sweeps_on_its_own(machine, ledger):
    """The other half of the process: a quiet machine still tells the truth."""
    import sqlite3
    import threading

    from agent_kit.daemon import reap_forever
    from agent_kit.machine import Ceilings, Want

    ledger.take(Want(account="fake", provider="fake", project="/p", slug="a-ghost", step="build",
                     pid=4_194_305), Ceilings(max_sessions=4))
    stop = threading.Event()
    sweeper = threading.Thread(target=reap_forever, args=(ledger,), kwargs={"every": 0, "stop": stop})
    sweeper.start()
    for _ in range(100):
        rows = sqlite3.connect(str(ledger.path)).execute("SELECT slug FROM leases").fetchall()
        if not rows:
            break
        time.sleep(0.05)
    stop.set()
    sweeper.join(timeout=5)

    assert rows == [], "nothing swept the dead lease up"


def test_a_run_a_driver_holds_is_not_advanced_by_hand(machine, ledger, capsys, tmp_path):
    """`run stop` was fixed and its three neighbours were not.

    One writer per run means one writer, and a person with a keyboard is a
    writer like any other.
    """
    run(["run", "new", "add-vat", "--steps", "probe"], capsys)
    ledger.hold_run(str((tmp_path / "project").resolve()), "add-vat", pid=1)

    code, _, err = run(["run", "start", "add-vat"], capsys)

    assert code == ExitCode.STATE
    assert "run-held-elsewhere" in err


def test_the_configuration_shows_the_settings_this_step_added(machine, capsys):
    code, out, _ = run(["config", "show"], capsys)

    assert code == ExitCode.OK
    said = json.loads(out)
    assert said["machine"]["wait"] == DEFAULT_WAIT
    assert said["daemon"] == {"host": "127.0.0.1", "port": 8080}


def test_a_machine_that_may_run_nothing_is_a_machine_that_may_run_nothing(machine, ledger, capsys):
    """`--machine-max 0` was read as "nothing was said" and the configured ceiling used."""
    code, _, err = run(
        ["slot", "take", "--provider", "fake", "--slug", "first", "--machine-max", "0"], capsys
    )

    assert code == ExitCode.PROVIDER
    assert "no-slot" in err


def test_the_limit_says_what_the_provider_said_when_the_hour_was_guessed(machine, ledger, capsys):
    ledger.limit("fake", until="5pm (America/Los_Angeles)", said_by="add-vat/build")

    code, out, _ = run(["machine"], capsys)

    assert "guessed" in out
    assert "5pm (America/Los_Angeles)" in out


def test_a_slot_may_name_the_account_it_spends(machine, ledger, capsys):
    """Two providers on one subscription: the pool is what the ceiling counts."""
    code, _, _ = run(
        ["slot", "take", "--provider", "fake", "--slug", "by-hand", "--account", "anthropic"], capsys
    )

    assert code == ExitCode.OK
    assert [row.account for row in ledger.held()] == ["anthropic"]


def test_stopping_a_daemon_whose_pid_belongs_to_somebody_else_is_refused_by_name(machine, capsys):
    """A pid file outlives its process, and pids come round again."""
    from agent_kit.paths import Paths

    paths = Paths.from_env()
    paths.ensure()
    (paths.state_dir / "daemon.pid").write_text("1", encoding="utf-8")

    code, _, err = run(["daemon", "stop"], capsys)

    assert code == ExitCode.STATE
    assert "not-ours" in err


# --- S7a: what a person types at the owner's channel ------------------------


def a_config(machine, text):
    path = Paths.from_env().config_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_token_is_typed_rather_than_passed_as_an_argument(machine, capsys, monkeypatch):
    """An argument lands in a shell history; a secret must not."""
    import io
    import stat

    monkeypatch.setattr("sys.stdin", io.StringIO("12345:abcdef\n"))

    code, out, _ = run(["owner", "set-token"], capsys)

    secrets = Paths.from_env().secrets_file
    assert code == ExitCode.OK
    assert "12345:abcdef" not in out
    assert stat.S_IMODE(secrets.stat().st_mode) == 0o600


def test_owner_check_on_a_machine_with_no_channel_says_which_rung(machine, capsys):
    code, out, err = run(["owner", "check"], capsys)

    assert code == ExitCode.CONFIG
    assert "channel" in (out + err)


def test_owner_check_walks_the_ladder_and_says_where_it_stopped(machine, capsys):
    """Лестница, а не одна строка: у `provider check` она есть, и уровень канала
    меряется так же — иначе это заявление вместо следа."""
    a_config(machine, f'[owner]\nchannel = "file"\nfile = "{machine}/owner"\n')

    code, out, _ = run(["owner", "check"], capsys)

    assert code == ExitCode.OK
    for rung in ("канал настроен", "канал отвечает", "сообщение ушло", "ответы читаются"):
        assert rung in out, f"ступень {rung!r} не названа"
    assert (machine / "owner.out").exists()


def test_owner_check_names_the_rung_it_stopped_on(machine, capsys):
    a_config(machine, f'[owner]\nchannel = "file"\nfile = "{machine}/owner"\n')
    (machine / "owner.fail").write_text("бот не отвечает\n")

    code, out, err = run(["owner", "check"], capsys)

    assert code == ExitCode.CHANNEL
    assert "канал настроен" in out
    assert "сообщение ушло" not in out
    assert "channel-failed" in (out + err)


def test_owner_check_on_telegram_asks_telegram_who_it_is(machine, capsys, monkeypatch):
    """Ступень «канал отвечает» — это getMe, а не догадка по конфигу."""
    asked = []

    class Bot:
        name = "telegram"

        def me(self):
            asked.append("getMe")
            return "vat_night_bot"

        def send(self, text):
            asked.append("sendMessage")
            return "1"

        def read(self, offset):
            asked.append("getUpdates")
            return [], "1"

    monkeypatch.setattr("agent_kit.owner.open_channel", lambda *a, **k: Bot())
    a_config(machine, '[owner]\nchannel = "telegram"\nchat = "55"\n')

    code, out, _ = run(["owner", "check"], capsys)

    assert code == ExitCode.OK
    assert asked == ["getMe", "sendMessage", "getUpdates"]
    assert "vat_night_bot" in out


def test_owner_say_reaches_the_channel(machine, capsys):
    a_config(machine, f'[owner]\nchannel = "file"\nfile = "{machine}/owner"\n')

    code, out, _ = run(["owner", "say", "the night is over"], capsys)

    assert code == ExitCode.OK
    assert "the night is over" in (machine / "owner.out").read_text()


def test_a_channel_that_cannot_be_reached_says_so_by_name(machine, capsys):
    a_config(machine, f'[owner]\nchannel = "file"\nfile = "{machine}/owner"\n')
    (machine / "owner.fail").write_text("no\n")

    code, out, err = run(["owner", "say", "hello"], capsys)

    assert code == ExitCode.CHANNEL
    assert "channel-failed" in err


def test_machine_prints_what_is_waiting_on_the_owner(machine, ledger, capsys):
    from agent_kit.machine import Ask

    ledger.asked(
        Ask(id="k7f3q2", project="/p", slug="add-vat", step="design",
            question="one rate, or one per country?", default="one rate",
            until="2099-01-01T00:00:00+00:00")
    )

    code, out, _ = run(["machine"], capsys)

    assert code == ExitCode.OK
    assert "k7f3q2" in out
    assert "one rate, or one per country?" in out


def test_doctor_says_whether_there_is_a_channel_at_all(machine, capsys):
    code, out, _ = run(["doctor"], capsys)

    assert code == ExitCode.OK
    assert "owner" in out.lower()


def test_the_page_shows_what_is_waiting_for_the_owner(machine, ledger):
    """A phone cannot read a config file over ssh, and it cannot read run.json either."""
    from agent_kit.daemon.server import as_dict, page
    from agent_kit.machine import Ask

    ledger.asked(
        Ask(id="k7f3q2", project="/p", slug="add-vat", step="design",
            question="one rate, or one per country?", default="one rate",
            until="2099-01-01T00:00:00+00:00")
    )

    assert "one rate, or one per country?" in page(ledger)
    assert as_dict(ledger)["asks"][0]["id"] == "k7f3q2"


def test_the_page_still_has_nothing_to_press(machine, ledger):
    from agent_kit.daemon.server import page

    assert "<button" not in page(ledger) and "<form" not in page(ledger)


def test_run_show_names_what_is_being_waited_for_and_until_when(machine, ledger, capsys):
    from agent_kit.machine import Ask
    from agent_kit.state import RunStore

    store = RunStore(Path.cwd())
    store.create("add-vat", steps=["design"], project=str(Path.cwd()), brief="VAT")
    store.start_step("add-vat", provider="fake")
    store.ask_step("add-vat", "design is asking the owner one thing")
    ledger.asked(
        Ask(id="k7f3q2", project=str(Path.cwd()), slug="add-vat", step="design",
            question="one rate, or one per country?", default="one rate",
            until="2099-01-01T00:00:00+00:00")
    )

    code, out, _ = run(["run", "show", "add-vat"], capsys)

    assert code == ExitCode.OK
    assert "asking" in out
    assert "one rate, or one per country?" in out
    assert "2099" in out


def test_owner_setup_is_the_door_that_owner_check_points_at(machine, capsys):
    """Девять дверей — это дефект второй версии. Отказ называет ту, что нужна."""
    code, out, err = run(["owner", "check"], capsys)

    assert code == ExitCode.CONFIG
    assert "owner setup" in (out + err)


def test_doctor_points_at_the_same_door(machine, capsys):
    code, out, _ = run(["doctor"], capsys)

    assert "owner setup" in out


def test_owner_setup_refuses_when_nobody_is_there_to_type(machine, capsys, monkeypatch):
    """Настройка — разговор с человеком. Без терминала ей не с кем разговаривать."""
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))

    code, out, err = run(["owner", "setup"], capsys)

    assert code == ExitCode.CONFIG
    assert "no-token" in err
