"""What the routine suite measures, and what it says it did not.

`make test` used to run the whole bench twice and the whole disarm once — 142
worlds made, driven and taken away, three times over — and then `make bench`
and `make armed` measured the same worlds again in the same verification round.
Five measurements of one thing. It cost eighteen of the suite's twenty-six
minutes, and twice it came back red for want of memory on a shared machine
rather than for a mechanism that stopped firing. A suite that reddens for that
teaches everybody to run it again rather than read it.

So a test whose body is a whole measurement the Makefile already has a target
for says which target, in a mark of its own. The suite deselects it and prints
the target by name: what is not measured here is a line of the run's own
output, not a sentence somebody has to remember. `pytest --everything` runs
them here too, and `make round` is the whole round in one word.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The two whose body is a target of its own, and the target each names.
ELSEWHERE = {
    "tests/test_bench.py::test_every_shipped_case_fires": "make bench",
    "tests/test_disarm.py::test_every_shipped_case_is_armed_or_says_why_it_cannot_be": "make armed",
}


def collected(*argv):
    """What a pytest run would take, and what it says about what it would not.

    Collection and no running: the answer this file wants is which tests the
    suite takes, and running them is the six minutes apiece that started all
    this.
    """
    printed = subprocess.run(
        # No `-q` of its own: the project's own options already carry one, and
        # a second turns the listing into a count per file.
        [sys.executable, "-m", "pytest", "--collect-only",
         "tests/test_bench.py", "tests/test_disarm.py", *argv],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    lines = printed.splitlines()
    return [line for line in lines if line.startswith("tests/")], lines


def test_a_measurement_with_a_target_of_its_own_is_not_run_by_the_routine_suite():
    taken, _ = collected()

    for nodeid in ELSEWHERE:
        assert nodeid not in taken, f"{nodeid} is still measured twice"


def test_the_suite_names_what_it_did_not_measure_and_what_measures_it():
    """The line is derived from the marks, so it cannot say more than is true."""
    _, said = collected()

    for nodeid, target in ELSEWHERE.items():
        assert any(
            line.startswith("not measured here:") and nodeid in line and target in line
            for line in said
        ), f"nothing told the reader that {nodeid} was left to {target}:\n" + "\n".join(said)


def test_the_ordinary_tests_of_the_bench_are_still_taken():
    """Deselecting by a mark, and not by a file or a name: the rest stays."""
    taken, _ = collected()

    assert "tests/test_bench.py::test_the_bench_with_no_word_after_it_runs_the_cases" in taken
    assert "tests/test_disarm.py::test_a_case_whose_judge_reads_what_the_plant_left_is_armed" in taken


def test_the_long_way_round_takes_them_here_too():
    """The tests stay reachable, so they cannot rot where nobody can run them."""
    taken, said = collected("--everything")

    for nodeid in ELSEWHERE:
        assert nodeid in taken
    assert not any(line.startswith("not measured here:") for line in said)
