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

from agent_kit.bench import cases_root, read_cases
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
    assert code == int(ExitCode.BENCH)


def test_a_case_that_cannot_be_set_up_is_could_not_be_judged_rather_than_a_failure(cases, capsys):
    case = write_case(cases, "unreadable", {"exit_code": 0, "status": "done"})
    (case / "case.toml").write_text("this is not toml at all\n", encoding="utf-8")

    code, printed = bench(cases, capsys=capsys)

    assert "could not be judged" in printed.out
    assert code == int(ExitCode.BENCH)


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
    shipped = read_cases(cases_root())

    assert len(shipped) >= 14
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
