"""S7 — the ledger. What is true on this machine right now, in one file.

Every question here is asked with no daemon running, which is the point: a
ceiling that only holds while a process is alive is a ceiling that is off at
02:00, when it is the only thing standing between a night and the machine.
"""

from datetime import datetime, timedelta, timezone

import pytest

from agent_kit.machine import SCHEMA_VERSION, Ceilings, Ledger, Want
from agent_kit.machine.ledger import now

ACCOUNT = "anthropic"


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "daemon.sqlite")


def one(machine: int = 1, provider: dict | None = None) -> Ceilings:
    return Ceilings(max_sessions=machine, per_provider=provider or {})


def want(slug: str = "add-vat", provider: str = "claude_code", step: str = "design", **rest) -> Want:
    return Want(
        account=rest.pop("account", ACCOUNT),
        provider=provider,
        project=rest.pop("project", "/projects/thing"),
        slug=slug,
        step=step,
        **rest,
    )


def in_an_hour() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat()


def an_hour_ago() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0).isoformat()


# --- the file itself --------------------------------------------------------


def test_the_ledger_makes_itself_and_opening_it_twice_is_the_same_ledger(tmp_path):
    path = tmp_path / "state" / "daemon.sqlite"
    first = Ledger(path)
    first.take(want(), one())

    assert path.is_file()
    assert len(Ledger(path).held()) == 1


# --- slots ------------------------------------------------------------------


def test_a_slot_is_granted_and_is_visible_to_anybody_who_asks(ledger):
    lease = ledger.take(want(step="build"), one())

    assert lease.granted
    held = ledger.held()
    assert [(row.slug, row.step, row.account) for row in held] == [("add-vat", "build", ACCOUNT)]


def test_the_machine_ceiling_refuses_the_second_session_and_names_what_holds_it(ledger):
    ledger.take(want(slug="first"), one(machine=1))

    busy = ledger.take(want(slug="second"), one(machine=1))

    assert not busy.granted
    assert busy.code == "no-slot"
    assert "first" in busy.detail


def test_a_provider_ceiling_binds_before_the_machine_one(ledger):
    ledger.take(want(slug="first", provider="codex"), one(machine=4, provider={"codex": 1}))

    busy = ledger.take(want(slug="second", provider="codex"), one(machine=4, provider={"codex": 1}))

    assert busy.code == "no-slot"
    assert "codex" in busy.detail


def test_a_provider_ceiling_does_not_bind_another_provider(ledger):
    ledger.take(want(slug="first", provider="codex"), one(machine=4, provider={"codex": 1}))

    lease = ledger.take(want(slug="second", provider="claude_code"), one(machine=4, provider={"codex": 1}))

    assert lease.granted


def test_releasing_a_slot_frees_it(ledger):
    lease = ledger.take(want(slug="first"), one(machine=1))

    ledger.release(lease)

    assert ledger.held() == []
    assert ledger.take(want(slug="second"), one(machine=1)).granted


def test_releasing_twice_is_the_same_as_releasing_once(ledger):
    """S6's lesson, in another shape: an act asked for twice must not half-happen."""
    lease = ledger.take(want(slug="first"), one(machine=1))
    ledger.release(lease)
    ledger.release(lease)

    assert ledger.take(want(slug="second"), one(machine=1)).granted


# --- a lease whose driver is gone -------------------------------------------


def test_a_lease_whose_driver_is_not_alive_is_reclaimed(ledger):
    ledger.take(want(slug="dead", pid=_a_pid_that_is_gone()), one(machine=1))

    lease = ledger.take(want(slug="live"), one(machine=1))

    assert lease.granted
    assert [row.slug for row in ledger.held()] == ["live"]


def test_a_lease_from_before_the_last_reboot_is_reclaimed(ledger):
    ledger.take(want(slug="before", boot="a-boot-that-has-ended"), one(machine=1))

    assert ledger.take(want(slug="after"), one(machine=1)).granted


def test_a_lease_that_outlived_its_own_ttl_is_reclaimed(ledger):
    """The backstop for a pid that was reused, which is the one case liveness cannot see."""
    ledger.take(want(slug="stale", ttl=-1), one(machine=1))

    assert ledger.take(want(slug="fresh"), one(machine=1)).granted


# --- limits -----------------------------------------------------------------


def test_a_limited_account_refuses_a_slot_and_says_until_when(ledger):
    reset = in_an_hour()
    ledger.limit(ACCOUNT, until=reset, said_by="add-vat/build")

    busy = ledger.take(want(), one())

    assert busy.code == "provider-limited"
    assert busy.until == reset
    assert "add-vat/build" in busy.detail


def test_a_limit_binds_the_account_and_not_the_provider(ledger):
    ledger.limit(ACCOUNT, until=in_an_hour(), said_by="add-vat/build")

    assert ledger.take(want(provider="claude_code"), one()).code == "provider-limited"
    assert ledger.take(want(provider="fake", account="another"), one()).granted


def test_a_limit_whose_hour_has_passed_is_gone(ledger):
    ledger.limit(ACCOUNT, until=an_hour_ago(), said_by="add-vat/build")

    assert ledger.take(want(), one()).granted
    assert ledger.limits() == []


def test_a_limit_with_no_hour_is_held_for_one_and_says_it_was_guessed(ledger):
    ledger.limit(ACCOUNT, until=None, said_by="add-vat/build")

    (held,) = ledger.limits()
    assert held.guessed
    assert held.until > datetime.now(timezone.utc).isoformat()
    assert ledger.take(want(), one()).code == "provider-limited"


def test_the_same_account_limited_twice_holds_the_hour_it_was_told_last(ledger):
    ledger.limit(ACCOUNT, until=in_an_hour(), said_by="first")
    later = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(microsecond=0).isoformat()
    ledger.limit(ACCOUNT, until=later, said_by="second")

    (held,) = ledger.limits()
    assert held.until == later
    assert held.said_by == "second"


# --- the queue --------------------------------------------------------------


def test_the_slot_goes_to_whoever_asked_first(ledger):
    ledger.take(want(slug="holder"), one(machine=1))
    ledger.wants_one(want(slug="patient"))
    ledger.wants_one(want(slug="hasty"))
    ledger.release(ledger.held()[0])

    assert ledger.take(want(slug="hasty"), one(machine=1)).code == "no-slot"
    assert ledger.take(want(slug="patient"), one(machine=1)).granted


def test_a_waiter_that_is_given_its_slot_stops_being_a_waiter(ledger):
    ledger.wants_one(want(slug="patient"))

    ledger.take(want(slug="patient"), one(machine=1))

    assert ledger.queue() == []


def test_a_waiter_whose_driver_died_does_not_hold_the_queue_up(ledger):
    ledger.wants_one(want(slug="dead", pid=_a_pid_that_is_gone()))

    assert ledger.take(want(slug="live"), one(machine=1)).granted


def test_the_queue_says_what_each_waiter_is_waiting_for(ledger):
    ledger.wants_one(want(slug="patient"))

    (waiting,) = ledger.queue()
    assert (waiting.slug, waiting.provider, waiting.account) == ("patient", "claude_code", ACCOUNT)


def test_giving_up_removes_the_waiter(ledger):
    asked = want(slug="patient")
    ledger.wants_one(asked)

    ledger.gives_up(asked)

    assert ledger.queue() == []


# --- one driver per run -----------------------------------------------------


def test_a_run_is_held_by_one_driver(ledger):
    ledger.hold_run("/projects/thing", "add-vat", pid=_a_pid_that_is_alive())

    busy = ledger.hold_run("/projects/thing", "add-vat", pid=_another_pid_that_is_alive())

    assert busy.code == "run-held-elsewhere"
    assert "add-vat" in busy.detail


def test_the_same_driver_asking_twice_holds_the_run_it_already_holds(ledger):
    first = ledger.hold_run("/projects/thing", "add-vat")

    again = ledger.hold_run("/projects/thing", "add-vat")

    assert again.granted
    assert again.id == first.id


def test_a_run_held_by_a_driver_that_died_is_free(ledger):
    ledger.hold_run("/projects/thing", "add-vat", pid=_a_pid_that_is_gone())

    assert ledger.hold_run("/projects/thing", "add-vat").granted


def test_the_same_slug_in_another_project_is_another_run(ledger):
    ledger.hold_run("/projects/one", "add-vat", pid=_a_pid_that_is_alive())

    assert ledger.hold_run("/projects/two", "add-vat", pid=_another_pid_that_is_alive()).granted


def test_a_run_lease_is_not_a_session_and_does_not_fill_the_machine(ledger):
    ledger.hold_run("/projects/thing", "add-vat")

    assert ledger.take(want(), one(machine=1)).granted


# --- stop -------------------------------------------------------------------


def test_a_stop_is_read_by_the_driver_and_read_once(ledger):
    ledger.ask_stop("/projects/thing", "add-vat", reason="the owner said so")

    asked = ledger.stop_asked("/projects/thing", "add-vat")
    assert asked == "the owner said so"
    assert ledger.stop_asked("/projects/thing", "add-vat") is None


def test_a_stop_asked_for_twice_stops_the_run_once(ledger):
    ledger.ask_stop("/projects/thing", "add-vat", reason="first")
    ledger.ask_stop("/projects/thing", "add-vat", reason="second")

    assert ledger.stop_asked("/projects/thing", "add-vat") is not None
    assert ledger.stop_asked("/projects/thing", "add-vat") is None


def test_a_stop_is_addressed_to_one_run(ledger):
    ledger.ask_stop("/projects/thing", "add-vat", reason="stop")

    assert ledger.stop_asked("/projects/thing", "another") is None
    assert ledger.stop_asked("/projects/elsewhere", "add-vat") is None


# --- what the page and `machine` read --------------------------------------


def test_everything_the_page_shows_comes_from_one_read(ledger):
    ledger.take(want(slug="running"), one(machine=4))
    ledger.wants_one(want(slug="queued"))
    ledger.limit("another", until=in_an_hour(), said_by="somebody/build")

    picture = ledger.picture()

    assert [row.slug for row in picture.held] == ["running"]
    assert [row.slug for row in picture.queue] == ["queued"]
    assert [row.account for row in picture.limits] == ["another"]


# --- helpers ----------------------------------------------------------------


def _a_pid_that_is_gone() -> int:
    """A pid nothing can be running under: pid 2**22 is above every Linux maximum."""
    return 4_194_305


def _a_pid_that_is_alive() -> int:
    import os

    return os.getpid()


def _another_pid_that_is_alive() -> int:
    """Pid 1 is always there, and it is never this test."""
    return 1


# --- more than one thread ----------------------------------------------------


def test_the_ledger_answers_from_any_thread(ledger):
    """The daemon sweeps on one thread and serves the page on others.

    A connection that belongs to the thread that opened it makes the page an
    empty reply and the sweep a stack trace in a log nobody is reading.
    """
    import threading

    said = []

    def ask():
        try:
            said.append(len(ledger.picture().held))
        except Exception as broken:  # the failure this test exists for
            said.append(broken)

    ledger.take(want(), one())
    threads = [threading.Thread(target=ask) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert said == [1, 1, 1, 1]




# --- the review round: what a provider actually says the hour is -------------


def test_an_hour_the_provider_worded_its_own_way_is_read_as_a_time(ledger):
    """What a CLI says is a phrase, not an ISO timestamp.

    It was stored as it came and compared with `<=` against a timestamp, so
    `"5pm (America/Los_Angeles)"` sorted above every date there will ever be
    and the account was limited for good.
    """
    held = ledger.limit(ACCOUNT, until="5pm (America/Los_Angeles)", said_by="add-vat/build")

    assert held.guessed, "an hour that could not be read must not pass as one that was"
    assert held.until < (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert held.said == "5pm (America/Los_Angeles)", "what the provider said is lost"


def test_an_hour_that_reads_as_a_time_but_sorts_wrong_is_still_read(ledger):
    """`"17:00"` sorts below every date, so the limit vanished at the first sweep."""
    held = ledger.limit(ACCOUNT, until="17:00", said_by="add-vat/build")

    assert held.until > now()
    assert ledger.take(want(), one()).code == "provider-limited"


def test_an_hour_in_another_offset_is_held_as_the_moment_it_names(ledger):
    """+03:00, сравниваемое со строкой в UTC, — три часа выброшенной квоты.

    Час считается вперёд от прогона, а не записан в код: прежняя версия держала
    момент, а не форму, — тот же класс дефекта, из-за которого восемь случаев
    краснели каждый день после своего часа. И проверяется, что лимит стоит: без
    этого тест мерил бы одно лишь переписывание строки.
    """
    from datetime import datetime, timedelta, timezone

    theirs = timezone(timedelta(hours=3))
    when = (datetime.now(theirs) + timedelta(hours=3)).replace(microsecond=0)

    held = ledger.limit(ACCOUNT, until=when.isoformat(), said_by="add-vat/build")

    assert held.until == when.astimezone(timezone.utc).isoformat()
    assert ledger.take(want(), one()).code == "provider-limited"


def test_an_hour_that_has_already_passed_in_any_wording_does_not_stand(ledger):
    ledger.limit(ACCOUNT, until="2020-01-01T00:00:00+00:00", said_by="add-vat/build")

    assert ledger.limits() == []


# --- the review round: a lease is given back by the driver that took it ------


def test_giving_back_a_lease_twice_does_not_take_somebody_else_s(ledger):
    """sqlite hands out the same rowid again once a row is gone.

    So a driver whose lease was swept for being stale, releasing it afterwards,
    deleted whatever had since been given that number — and the ceiling was
    quietly one session wider than the machine allows.
    """
    mine = ledger.take(want(slug="mine"), one(machine=2))
    ledger.release(mine)
    theirs = ledger.take(want(slug="theirs", pid=1), one(machine=2))
    assert theirs.id == mine.id, "this test only means something while rowids are reused"

    ledger.release(mine)

    assert [row.slug for row in ledger.held()] == ["theirs"]


# --- the review round: a stop nobody is there to read ------------------------


def test_a_stop_whose_driver_never_came_back_does_not_stop_the_next_run(ledger):
    ledger.hold_run("/projects/thing", "add-vat", pid=_a_pid_that_is_gone())
    ledger.ask_stop("/projects/thing", "add-vat", reason="the owner said so")

    ledger.reap()

    assert ledger.stop_asked("/projects/thing", "add-vat") is None


def test_a_stop_for_a_run_a_driver_still_holds_survives_a_sweep(ledger):
    ledger.hold_run("/projects/thing", "add-vat")
    ledger.ask_stop("/projects/thing", "add-vat", reason="the owner said so")

    ledger.reap()

    assert ledger.stop_asked("/projects/thing", "add-vat") == "the owner said so"


# --- the review round: the schema says which version wrote it ----------------


def test_a_ledger_from_a_newer_kit_is_refused_by_name(tmp_path):
    import sqlite3

    from agent_kit.errors import KitError

    path = tmp_path / "daemon.sqlite"
    Ledger(path).close()
    db = sqlite3.connect(str(path))
    db.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
    db.close()

    with pytest.raises(KitError) as refused:
        Ledger(path)

    assert refused.value.code == "ledger-too-new"


def test_a_ledger_this_kit_wrote_says_which_version_wrote_it(tmp_path):
    import sqlite3

    path = tmp_path / "daemon.sqlite"
    Ledger(path)

    (held,) = sqlite3.connect(str(path)).execute("PRAGMA user_version").fetchone()
    assert held == SCHEMA_VERSION


# --- the review round: a sweep from another thread is a sweep ----------------


def test_a_sweep_on_another_thread_really_swept(ledger):
    """The first version of this asked `held()`, which sweeps on the asking thread.

    So it was green against a sweeper thread that had crashed — which is the
    defect the thread it was written for actually had.
    """
    import sqlite3
    import threading

    ledger.take(want(slug="dead", pid=_a_pid_that_is_gone()), one())
    thread = threading.Thread(target=ledger.reap)
    thread.start()
    thread.join()

    rows = sqlite3.connect(str(ledger.path)).execute("SELECT slug FROM leases").fetchall()
    assert rows == []


def test_a_ledger_that_cannot_be_read_is_a_named_refusal(tmp_path):
    """The one failure here that is not the kit's fault must still have a name.

    A locked database, a state directory that is not writable: exit 70 says
    "a defect in the kit", and a busy machine is not a defect.
    """
    from agent_kit.errors import ExitCode, KitError

    path = tmp_path / "daemon.sqlite"
    path.write_text("this is not a database, and nobody promised it was", encoding="utf-8")

    with pytest.raises(KitError) as refused:
        Ledger(path).take(want(), one())

    assert refused.value.code == "unreadable-ledger"
    assert refused.value.exit_code is not ExitCode.INTERNAL


# --- S7a: questions waiting on a person ------------------------------------


def an_ask(id: str = "k7f3q2", slug: str = "add-vat", **rest):
    from agent_kit.machine import Ask

    return Ask(
        id=id,
        project=rest.pop("project", "/projects/thing"),
        slug=slug,
        step=rest.pop("step", "design"),
        question=rest.pop("question", "one rate, or one per country?"),
        default=rest.pop("default", "one rate"),
        until=rest.pop("until", in_an_hour()),
        message=rest.pop("message", "17"),
        **rest,
    )


def test_a_question_is_a_row_while_it_waits(ledger):
    ledger.asked(an_ask())

    (waiting,) = ledger.waiting_on_the_owner()
    assert waiting.id == "k7f3q2"
    assert waiting.slug == "add-vat"
    assert waiting.answer is None


def test_asking_the_same_question_twice_is_asking_it_once(ledger):
    """A driver that died after asking must find its own question, not plant a second."""
    ledger.asked(an_ask())
    ledger.answered("k7f3q2", "one per country")

    ledger.asked(an_ask())

    assert len(ledger.waiting_on_the_owner()) == 0
    assert ledger.ask_of("k7f3q2").answer == "one per country"


def test_an_answer_is_written_where_its_own_driver_will_find_it(ledger):
    """Час, когда ответили, живёт в `asks.json` шага: здесь у него читателя нет."""
    ledger.asked(an_ask())

    assert ledger.answered("k7f3q2", "one per country") is True

    assert ledger.ask_of("k7f3q2").answer == "one per country"


def test_an_answer_to_a_question_nobody_asked_is_not_written(ledger):
    assert ledger.answered("nobody", "hello") is False
    assert ledger.ask_of("nobody") is None


def test_the_first_answer_is_the_answer(ledger):
    ledger.asked(an_ask())
    ledger.answered("k7f3q2", "one per country")

    assert ledger.answered("k7f3q2", "changed my mind") is False
    assert ledger.ask_of("k7f3q2").answer == "one per country"


def test_a_question_is_found_by_the_message_it_was_sent_as(ledger):
    """What a person actually does on a phone is reply to the message."""
    ledger.asked(an_ask(message="17"))

    assert ledger.ask_sent_as("17").id == "k7f3q2"
    assert ledger.ask_sent_as("999") is None


def test_only_one_process_reads_the_channel_at_a_time(ledger):
    """getUpdates is single-consumer: two readers steal each other's answers."""
    first = ledger.read_channel()
    assert first.granted

    second = ledger.read_channel(pid=first.pid + 1, boot="another-boot")
    assert not second.granted
    assert second.code == "channel-held-elsewhere"

    ledger.release(first)
    assert ledger.read_channel(pid=first.pid + 1, boot="another-boot").granted


def test_the_offset_outlives_the_process_that_read_it(ledger, tmp_path):
    ledger.remember_offset("509")

    assert Ledger(tmp_path / "daemon.sqlite").offset() == "509"


def test_the_offset_starts_at_nothing(ledger):
    assert ledger.offset() == ""


def test_a_question_long_past_its_hour_is_swept(ledger):
    from agent_kit.machine.ledger import after

    ledger.asked(an_ask(id="old", until=after(-2 * 60 * 60)))
    ledger.asked(an_ask(id="fresh"))

    ledger.reap()

    assert [row.id for row in ledger.waiting_on_the_owner()] == ["fresh"]


def test_a_question_just_past_its_deadline_is_not_swept_from_under_its_driver(ledger):
    """The driver reads one last time after the deadline. Sweeping there loses an answer."""
    from agent_kit.machine.ledger import after

    ledger.asked(an_ask(id="justnow", until=after(-5)))

    ledger.reap()

    assert [row.id for row in ledger.waiting_on_the_owner()] == ["justnow"]


# --- ревью: вопрос, заданный повторно, называет новое сообщение -------------


def test_asking_again_refreshes_the_message_and_the_hour(ledger):
    """Драйвер умер, шаг подняли заново, вопрос ушёл новым сообщением.

    Строка обязана назвать это сообщение и новый час: иначе реплай не находит
    вопрос, а выметание сносит строку из-под живого ждущего драйвера.
    """
    from agent_kit.machine.ledger import after

    ledger.asked(an_ask(message="1", until=after(60)))
    later = after(3600)

    again = ledger.asked(an_ask(message="2", until=later))

    assert again.message == "2"
    assert again.until == later
    assert ledger.ask_sent_as("2").id == "k7f3q2"


def test_asking_again_does_not_lose_an_answer_that_already_came(ledger):
    ledger.asked(an_ask(message="1"))
    ledger.answered("k7f3q2", "one per country")

    again = ledger.asked(an_ask(message="2"))

    assert again.answer == "one per country"


def test_a_question_asked_again_is_not_swept_by_the_hour_it_first_had(ledger):
    from agent_kit.machine.ledger import after

    ledger.asked(an_ask(until=after(-2 * 60 * 60)))
    ledger.asked(an_ask(until=after(3600)))

    ledger.reap()

    assert [row.id for row in ledger.waiting_on_the_owner()] == ["k7f3q2"]


def test_two_projects_asking_the_same_thing_are_two_questions(ledger):
    """Имя прогона и слова вопроса совпадают — идентификатор один, а вопроса два."""
    mine = ledger.free_ask_id("/projects/one", "add-vat", "k7f3q2")
    ledger.asked(an_ask(id=mine, project="/projects/one"))

    theirs = ledger.free_ask_id("/projects/two", "add-vat", "k7f3q2")

    assert theirs != mine
    ledger.asked(an_ask(id=theirs, project="/projects/two"))
    ledger.answered(theirs, "их ответ")

    assert ledger.ask_of(mine).answer is None
    assert ledger.ask_of(theirs).answer == "их ответ"


def test_the_same_project_asking_again_keeps_its_own_name(ledger):
    ledger.asked(an_ask(id="k7f3q2", project="/projects/one"))

    assert ledger.free_ask_id("/projects/one", "add-vat", "k7f3q2") == "k7f3q2"


# --- S8: a batch, a skip, and the machine's own ceiling ---------------------


def test_one_driver_per_batch_the_way_there_is_one_per_run(ledger):
    first = ledger.hold_batch("/projects/thing", "2026-08-26-vat")

    assert first.granted
    assert ledger.hold_batch("/projects/thing", "2026-08-26-vat", pid=first.pid + 1).code == (
        "batch-held-elsewhere"
    )


def test_the_same_driver_holds_what_it_already_holds(ledger):
    first = ledger.hold_batch("/projects/thing", "2026-08-26-vat")

    assert ledger.hold_batch("/projects/thing", "2026-08-26-vat").id == first.id


def test_a_skip_reaches_the_batch_driver_by_the_feature_it_names(ledger):
    ledger.hold_batch("/projects/thing", "vat")
    ledger.ask_skip("/projects/thing", "vat", "rates", reason="not settled yet")
    ledger.ask_skip("/projects/thing", "vat", "quote", reason="nor is this")

    assert ledger.skips_asked("/projects/thing", "vat") == [
        ("rates", "not settled yet"),
        ("quote", "nor is this"),
    ]
    assert ledger.skips_asked("/projects/thing", "vat") == []


def test_a_skip_nobody_is_there_to_read_is_swept(ledger):
    """The same rule a stop has: a request left standing skips whatever next carries that name."""
    ledger.ask_skip("/projects/thing", "vat", "rates", reason="not settled yet")

    ledger.reap()

    assert ledger.skips_asked("/projects/thing", "vat") == []


def test_a_stop_for_a_batch_a_driver_holds_survives_a_sweep(ledger):
    ledger.hold_batch("/projects/thing", "vat")
    ledger.ask_stop("/projects/thing", "vat", reason="enough for tonight")

    ledger.reap()

    assert ledger.stop_asked("/projects/thing", "vat") == "enough for tonight"


def test_when_the_machine_is_what_binds_the_oldest_waiter_of_all_goes_first(ledger):
    """S7's second debt, and a batch across two providers is what makes it real.

    The queue orders per account, so two waiters on *different* accounts were
    ordered by whoever polled at the right moment rather than by who asked
    first — and with one provider configured there was one account, which is
    why S7 refused to fix it on a guess.
    """
    ledger.take(want(slug="holder", account="anthropic"), one(machine=1))
    ledger.wants_one(want(slug="patient", account="openai", provider="codex"))
    ledger.wants_one(want(slug="hasty", account="anthropic"))
    ledger.release(ledger.held()[0])

    assert ledger.take(want(slug="hasty", account="anthropic"), one(machine=1)).code == "no-slot"
    assert ledger.take(want(slug="patient", account="openai", provider="codex"), one(machine=1)).granted


def test_a_provider_s_own_ceiling_is_still_its_account_s_queue(ledger):
    """Only the machine's ceiling is answered across accounts.

    A provider's ceiling binds one provider and a limit binds one account:
    letting a waiter on another account jump that queue would order it by
    something that does not hold it back at all.
    """
    ledger.take(want(slug="holder", provider="codex", account="openai"), one(machine=4, provider={"codex": 1}))
    ledger.wants_one(want(slug="elsewhere", provider="claude_code", account="anthropic"))
    ledger.wants_one(want(slug="waiting", provider="codex", account="openai"))

    got = ledger.take(want(slug="waiting", provider="codex", account="openai"), one(machine=4, provider={"codex": 1}))

    assert got.code == "no-slot"
    assert "codex" in got.detail
