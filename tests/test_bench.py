"""S5 — the bench: planted traps, and judges that are scripts.

A trap is not a test of the kit's Python. It is a run of the kit — the command,
in its own directory, with its own home, against a real git repository and a
`gh` that is a script — and a judge that reads what the run left behind. That is
what makes it able to catch what a clean room cannot.

The tests below are about the instrument. The one that matters most is the last
one: every case the kit ships fires.
"""

import json
from pathlib import Path

import pytest

from agent_kit.bench import case_names, cases_root, read_case
from agent_kit.cli.main import main
from agent_kit.errors import ExitCode

DESIGN = {
    "title": "Money learns a VAT rate",
    "summary": "Money learns a VAT rate, so a price can be quoted with tax.",
    "changes": ["money.py — a with_vat helper"],
    "seams": ["AMOUNT stays where it is"],
    "verification": ["a check that 1000 at 20% is 1200"],
    "needs_owner": [],
    "assumptions": [
        {"what": "the rate is a whole percent", "expensive": False, "because": "nothing here uses fractions"}
    ],
}

BUILD = {
    "complete": True,
    "summary": "with_vat, and the check decided before it.",
    "files": ["money.py"],
    "tests": ["vat_is_added"],
    "deviations": [],
    "remaining": None,
}

REVIEW = {"verdict": "pass", "findings": []}


def write_case(root, name, expect, replies=(DESIGN, BUILD, REVIEW), plant=None, judge=None, overlay=None):
    """A case on disk, exactly as one the kit ships is laid out."""
    case = root / name
    (case / "replies").mkdir(parents=True)
    lines = [
        "[case]",
        f'title = "{name}"',
        'fires = "whatever this case is for"',
        "",
        "[expect]",
    ]
    for key, value in expect.items():
        if isinstance(value, dict):
            lines.append(f"{key} = {{ " + ", ".join(f'{k} = "{v}"' for k, v in value.items()) + " }")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    (case / "case.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for number, reply in enumerate(replies, start=1):
        (case / "replies" / f"{number:02d}-reply.json").write_text(
            json.dumps(reply, indent=2), encoding="utf-8"
        )
    if plant is not None:
        _script(case / "plant.sh", plant)
    if judge is not None:
        _script(case / "judge.sh", judge)
    for relative, text in (overlay or {}).items():
        path = case / "repo" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return case


def _script(path, body):
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)


#: A build that writes what it claims to have written. The fake provider answers;
#: this is what makes it also act, which is what a session does.
WROTE_IT = "printf 'RATE = 20\\n' >> money.py\n"


@pytest.fixture
def cases(tmp_path):
    return tmp_path / "cases"


def bench(cases, *argv, capsys=None):
    code = main(["bench", "run", "--cases", str(cases), *argv])
    return code, capsys.readouterr() if capsys else None


# --- the instrument ---------------------------------------------------------


def test_a_case_whose_mechanism_fires_is_reported_as_fired(cases, capsys):
    write_case(
        cases,
        "the-work-is-delivered",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
    )

    code, printed = bench(cases, capsys=capsys)

    assert "the-work-is-delivered" in printed.out
    assert "fired" in printed.out
    assert "did not fire" not in printed.out
    assert code == int(ExitCode.OK)


def test_a_case_that_does_not_fire_says_what_it_expected_and_the_bench_exits_non_zero(cases, capsys):
    write_case(
        cases,
        "expects-the-wrong-thing",
        {"exit_code": 3, "status": "failed", "refusal": "branch-exists"},
        plant=WROTE_IT,
    )

    code, printed = bench(cases, capsys=capsys)

    assert "did not fire" in printed.out
    assert "exited 0" in printed.out and "wants 3" in printed.out  # what it got, and what it wanted
    assert code == int(ExitCode.BENCH)


def test_a_judge_of_its_own_reads_what_the_run_left_behind(cases, capsys):
    write_case(
        cases,
        "the-commit-holds-one-file",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='test "$(git show --name-only --format= HEAD)" = "money.py"\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out
    assert code == int(ExitCode.OK)


def test_a_judge_that_says_no_makes_the_case_not_fire(cases, capsys):
    write_case(
        cases,
        "the-judge-refuses",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='echo "the branch holds nothing I recognise" >&2\nexit 1\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "did not fire" in printed.out
    assert "the branch holds nothing I recognise" in printed.out
    assert code == int(ExitCode.BENCH)


def test_a_judge_that_could_not_judge_is_not_counted_as_fired(cases, capsys):
    """Exit 0 fired, exit 1 did not, anything else means the judge itself broke."""
    write_case(
        cases,
        "the-judge-broke",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='echo "no such tool here" >&2\nexit 2\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "could not be judged" in printed.out
    assert "did not fire" not in printed.out
    assert code == int(ExitCode.BROKEN_BENCH)


def test_a_case_that_cannot_be_set_up_is_could_not_be_judged_rather_than_a_failure(cases, capsys):
    case = write_case(cases, "unreadable", {"exit_code": 0, "status": "done"})
    (case / "case.toml").write_text("this is not toml at all\n", encoding="utf-8")

    code, printed = bench(cases, capsys=capsys)

    assert "could not be judged" in printed.out
    assert code == int(ExitCode.BROKEN_BENCH)


def test_one_case_can_be_asked_for_by_name(cases, capsys):
    write_case(cases, "one", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)
    write_case(cases, "two", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    code, printed = bench(cases, "--case", "one", capsys=capsys)

    assert "one" in printed.out
    assert "two" not in printed.out
    assert code == int(ExitCode.OK)


def test_a_name_that_is_not_a_case_is_refused_by_name(cases, capsys):
    write_case(cases, "one", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    code = main(["bench", "run", "--cases", str(cases), "--case", "nowhere"])

    assert code == int(ExitCode.USAGE)
    assert "nowhere" in capsys.readouterr().err


def test_the_cases_are_named_without_running_them(cases, capsys):
    write_case(cases, "one", {"exit_code": 0, "status": "done"})

    code = main(["bench", "list", "--cases", str(cases)])
    printed = capsys.readouterr().out

    assert "one" in printed
    assert "whatever this case is for" in printed  # what it says must fire
    assert code == int(ExitCode.OK)


# --- what a case may not do -------------------------------------------------


def test_a_case_touches_neither_the_home_nor_the_repository_of_whoever_ran_it(cases, capsys, machine_home, tmp_path):
    write_case(
        cases,
        "kept-for-reading",
        {"exit_code": 0, "status": "failed"},  # it will not fire, so it is kept
        plant=WROTE_IT,
    )

    bench(cases, "--keep", str(tmp_path / "kept"), capsys=capsys)

    world = tmp_path / "kept" / "kept-for-reading"
    assert (world / "home/.local/state/agent-kit").is_dir()  # the case's kit wrote its state there
    assert (world / "project/.agent-kit/v3/runs/add-vat").is_dir()  # and its run there
    assert not (machine_home / ".config/agent-kit").exists()
    assert not (Path.cwd() / ".agent-kit/v3/runs/add-vat").exists()  # not in the kit's own checkout


def test_a_case_that_fires_leaves_nothing_behind(cases, capsys, tmp_path):
    write_case(cases, "tidy", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    bench(cases, "--keep", str(tmp_path / "kept"), capsys=capsys)

    assert not (tmp_path / "kept" / "tidy").exists()


def test_the_case_runs_against_a_gh_that_is_a_script_and_a_remote_that_is_a_directory(cases, capsys, tmp_path):
    """Nothing reaches the network, so a case is the same on a machine with no login."""
    write_case(
        cases,
        "no-network",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='git ls-remote --heads origin | grep -q "kit/"\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out
    assert code == int(ExitCode.OK)


# --- the cases the kit ships ------------------------------------------------


def test_every_shipped_case_is_readable_and_says_what_must_fire(capsys):
    root = cases_root()
    shipped = [read_case(root, name) for name in case_names(root)]

    assert len(shipped) >= 15
    for case in shipped:
        assert case.fires.strip(), f"{case.name} does not say what mechanism it plants"
        assert case.title.strip()


def test_every_shipped_case_fires(capsys):
    """S5's own condition, as a test: break any mechanism and exactly one case says so."""
    code = main(["bench", "run"])
    printed = capsys.readouterr()

    assert "did not fire" not in printed.out, printed.out
    assert "could not be judged" not in printed.out, printed.out
    assert code == int(ExitCode.OK)


# --- what the review of S5 found ---------------------------------------------


def test_every_file_a_case_needs_is_in_the_repository():
    """A bench that is green only in one working copy measures that copy.

    `.gitignore` held `.agent-kit/`, which is the run state a project must not
    commit — and it silently swallowed the two cases that declare a project of
    their own. From a fresh clone the bench was red and nobody would know why.
    """
    import subprocess

    root = Path(__file__).resolve().parents[1]
    printed = subprocess.run(
        ["git", "status", "--ignored", "--short", "--", "bench/cases"],
        cwd=root, capture_output=True, text=True,
    ).stdout
    ignored = [line for line in printed.splitlines() if line.startswith("!!")]

    assert ignored == [], "the bench needs files git is not keeping:\n" + "\n".join(ignored)


def test_a_case_whose_trap_was_never_planted_does_not_fire(tmp_path, capsys):
    """A judge must prove the trap sprang, not merely that nothing went wrong.

    Both weak judges had the same shape: they read a state the world reaches
    anyway when the trap is absent, so the case reported `fired` against a
    mechanism it never exercised.
    """
    import shutil

    from agent_kit.bench import cases_root

    for name in ("a-command-that-hangs", "branch-holds-nothing"):
        elsewhere = tmp_path / name
        shutil.rmtree(elsewhere, ignore_errors=True)
        (tmp_path / "cases").mkdir(exist_ok=True)
        shutil.copytree(cases_root() / name, tmp_path / "cases" / name)
        _script(tmp_path / "cases" / name / "plant.sh", "exit 0\n")  # the trap is not laid
        if name == "a-command-that-hangs":
            _script(tmp_path / "cases" / name / "repo" / "check.sh", "sleep 60\n")  # and nothing is spawned

        main(["bench", "run", "--cases", str(tmp_path / "cases"), "--case", name])
        printed = capsys.readouterr().out
        said = next(line for line in printed.splitlines() if line.startswith(name))

        assert "did not fire" in said, f"{name} fires with no trap in place: {said}"


def test_a_judge_reads_the_reason_the_run_recorded(cases, capsys):
    write_case(
        cases,
        "wants-a-reason-that-is-not-there",
        {"exit_code": 0, "status": "done", "refusal": "branch-exists"},
        plant=WROTE_IT,
    )

    code, printed = bench(cases, capsys=capsys)

    assert "did not fire" in printed.out
    assert "branch-exists" in printed.out
    assert code == int(ExitCode.BENCH)


def test_a_judge_reads_the_status_each_step_ended_on(cases, capsys):
    write_case(
        cases,
        "wants-a-step-that-did-not-fail",
        {"exit_code": 0, "status": "done", "steps": {"verify": "failed"}},
        plant=WROTE_IT,
    )

    code, printed = bench(cases, capsys=capsys)

    assert "did not fire" in printed.out
    assert "verify" in printed.out
    assert code == int(ExitCode.BENCH)


def test_a_trap_that_could_not_be_laid_is_could_not_be_judged(cases, capsys):
    """A plant that fails leaves a world that is not the one the case is about."""
    write_case(
        cases,
        "the-trap-would-not-lie-down",
        {"exit_code": 0, "status": "done"},
        plant='echo "there is no such branch here" >&2\nexit 1\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "could not be judged" in printed.out
    assert "there is no such branch here" in printed.out
    assert code == int(ExitCode.BROKEN_BENCH)


def test_a_kit_that_crashed_is_not_reported_as_a_mechanism_that_did_not_fire(cases, capsys, monkeypatch):
    """Exit 70 is a defect in the kit. Reading it as a regression points at the wrong thing."""
    import subprocess

    write_case(cases, "the-kit-broke", {"exit_code": 3, "status": "failed"}, plant=WROTE_IT)

    from agent_kit.bench import runner

    real = runner._group

    def crashing(argv, cwd, env):
        if "go" in argv:
            return subprocess.CompletedProcess(
                argv, 70, stdout="", stderr="agent-kit: internal-error: TypeError: nope"
            )
        return real(argv, cwd, env)

    monkeypatch.setattr(runner, "_group", crashing)

    code, printed = bench(cases, capsys=capsys)

    assert "could not be judged" in printed.out
    assert "did not fire" not in printed.out
    assert code == int(ExitCode.BROKEN_BENCH)


def test_a_bench_that_broke_and_a_mechanism_that_regressed_have_different_codes(cases, capsys):
    """The distinction the kit spent S5 learning to make, applied to the bench itself."""
    write_case(cases, "regressed", {"exit_code": 3, "status": "failed"}, plant=WROTE_IT)
    regression, _ = bench(cases, "--case", "regressed", capsys=capsys)

    write_case(cases, "broke", {"exit_code": 0, "status": "done"}, plant="exit 1\n")
    broken, _ = bench(cases, "--case", "broke", capsys=capsys)

    assert regression == int(ExitCode.BENCH)
    assert broken == int(ExitCode.BROKEN_BENCH)
    assert regression != broken


def test_the_bench_with_no_word_after_it_runs_the_cases(cases, capsys):
    write_case(cases, "one", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    code = main(["bench"])
    printed = capsys.readouterr()

    assert "internal-error" not in printed.err
    assert "fired" in printed.out
    assert code in (int(ExitCode.OK), int(ExitCode.BENCH))


def test_one_unreadable_case_does_not_hide_the_others_in_the_listing(cases, capsys):
    write_case(cases, "readable", {"exit_code": 0, "status": "done"})
    broken = write_case(cases, "unreadable", {"exit_code": 0, "status": "done"})
    (broken / "case.toml").write_text("this is not toml at all\n", encoding="utf-8")

    code = main(["bench", "list", "--cases", str(cases)])
    printed = capsys.readouterr().out

    assert "readable" in printed
    assert "unreadable" in printed  # named, with what is wrong with it
    assert code == int(ExitCode.BROKEN_BENCH)


def test_a_case_does_not_borrow_the_git_identity_of_the_machine(cases, capsys, tmp_path, monkeypatch):
    """Determinism the bench exists for: the commit is the bench's, not the machine's."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "somebody else")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "elsewhere@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "somebody else")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "elsewhere@example.com")
    write_case(
        cases,
        "whose-commit-is-it",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='git log -1 --format=%an%ae | grep -q elsewhere && { echo "the machine signed it"; exit 1; }\nexit 0\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out, printed.out
    assert code == int(ExitCode.OK)


def test_a_case_cannot_be_pointed_at_the_repository_it_is_run_from(cases, capsys, monkeypatch, tmp_path):
    """`git` reads GIT_DIR before anything else. A bench run from a hook must not follow it."""
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-a-repo"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    write_case(cases, "its-own-repository", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out, printed.out
    assert code == int(ExitCode.OK)


def test_the_judge_is_told_where_the_run_is(cases, capsys):
    write_case(
        cases,
        "the-judge-knows-where-it-stands",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge=(
            'test -n "$RUN_DIR" && test -d "$RUN_DIR" || { echo "RUN_DIR: $RUN_DIR"; exit 1; }\n'
            'test -n "$ORIGIN" && test -d "$ORIGIN" || { echo "ORIGIN: $ORIGIN"; exit 1; }\n'
            'test "$EXIT_CODE" = 0 || { echo "EXIT_CODE: $EXIT_CODE"; exit 1; }\n'
            'test -n "$BENCH" && test -n "$BRANCH" && test -n "$SLUG" || { echo "a name is missing"; exit 1; }\n'
        ),
    )

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out, printed.out
    assert code == int(ExitCode.OK)


def test_a_reply_that_acts_reaches_the_working_copy_through_the_bench(cases, capsys):
    """The fixture's script is tested on its own; this is the whole path, end to end."""
    write_case(
        cases,
        "the-session-wrote-something",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='git show HEAD:money.py | grep -q "RATE = 20" || { echo "the work never landed"; exit 1; }\n',
    )

    code, printed = bench(cases, capsys=capsys)

    assert "fired" in printed.out, printed.out
    assert code == int(ExitCode.OK)


# --- S6: the four knowledge cases, and their judges ---------------------------


def test_a_knowledge_case_whose_project_keeps_none_does_not_fire(tmp_path, capsys):
    """Take the knowledge away and every mechanism about it must go quiet.

    The join binds a project that keeps knowledge. A case that still reported
    `fired` against a project keeping none would be measuring the run, not the
    join — the S5 shape, in the step that most invites it.
    """
    import shutil

    from agent_kit.bench import cases_root

    names = (
        "an-expensive-assumption-with-no-block",
        "an-address-that-names-no-record",
        "closing-a-block-that-is-not-there",
        "a-block-that-reaches-the-knowledge",
    )
    for name in names:
        room = tmp_path / name / "cases"
        room.mkdir(parents=True)
        shutil.copytree(cases_root() / name, room / name)
        shutil.rmtree(room / name / "repo" / "docs")  # the trap is not laid

        main(["bench", "run", "--cases", str(room), "--case", name])
        said = next(line for line in capsys.readouterr().out.splitlines() if line.startswith(name))

        assert "did not fire" in said, f"{name} fires against a project that keeps no knowledge: {said}"


def test_the_judge_of_the_green_case_proves_its_own_trap_was_laid(tmp_path, capsys):
    """The declaration alone would pass here: a run with nothing to record goes green.

    So this disarms the trap *and* keeps the run green, which is the only way to
    ask the judge whether it is armed rather than asking the case.
    """
    import json
    import shutil

    from agent_kit.bench import cases_root

    name = "a-block-that-reaches-the-knowledge"
    room = tmp_path / "cases"
    room.mkdir()
    shutil.copytree(cases_root() / name, room / name)
    shutil.rmtree(room / name / "repo" / "docs")

    design = room / name / "replies" / "01-reply.json"
    written = json.loads(design.read_text(encoding="utf-8"))
    written["closes"] = []
    written["assumptions"][0]["expensive"] = False  # nothing is owed, so the run goes green
    design.write_text(json.dumps(written, ensure_ascii=False), encoding="utf-8")

    main(["bench", "run", "--cases", str(room), "--case", name])
    said = next(line for line in capsys.readouterr().out.splitlines() if line.startswith(name))

    assert "did not fire" in said, said
    assert "no knowledge was planted at all" in said, said
