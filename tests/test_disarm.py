"""S13 — taking the trap away, and asking the case to stop firing.

The kit's rule is that a trap is not a trap until the mechanism under it has
been broken by hand and the case went red. That rule has been honoured by
people, and it has failed three times — one case in S8 and two in S7a were
green against a broken kit until somebody thought to break them. For every
other case the claim lived in prose in a step note, which is the «утверждение
вместо следа» the same file forbids.

This is that claim made mechanical, from the other side. A case brings three
things on top of the baseline world: what `plant.sh` puts in place, what
`repo/` lays over the project, and what `replies/` makes the sessions say.
Take all three away and the world is the baseline one, where nothing is wrong.
A case that still reports `fired` there is not reading its own trap.

What the check may not do is claim more than it measured, so there are four
answers and not two: armed, still fires, not disarmable — the case says in
words why nothing can honestly be taken away — and could not be checked, which
is the instrument breaking and is never read as armed.
"""

import pytest

from agent_kit.bench import case_names, cases_root, read_case
from agent_kit.bench.disarm import ARMED, NOT_DISARMABLE, STILL_FIRES, UNCHECKABLE, check_named
from agent_kit.cli.main import main
from agent_kit.errors import ExitCode
from test_bench import WROTE_IT, write_case


@pytest.fixture
def cases(tmp_path):
    return tmp_path / "cases"


def declaring(case, key, value):
    """One more line in the case's own `[case]` block, where a case declares things."""
    text = case.joinpath("case.toml").read_text(encoding="utf-8")
    where = text.index("\n", text.index("fires ="))
    case.joinpath("case.toml").write_text(
        text[:where] + f'\n{key} = "{value}"' + text[where:], encoding="utf-8"
    )
    return case


# --- what disarming a case means --------------------------------------------


def test_a_case_whose_judge_reads_what_the_plant_left_is_armed(cases, tmp_path):
    write_case(
        cases,
        "the-branch-was-there-first",
        {"exit_code": 0, "status": "done"},
        plant='git branch "$BRANCH"\ngit rev-parse "$BRANCH" > "$BENCH/planted"\n',
        judge='test -f "$BENCH/planted" || { echo "nothing was planted"; exit 1; }\n',
    )

    said = check_named(cases, "the-branch-was-there-first", tmp_path / "into")

    assert said.state == ARMED, said.why


def test_a_case_that_fires_with_nothing_planted_is_named_as_one(cases, tmp_path):
    """No judge at all, so the case reports the baseline run and calls it a mechanism."""
    write_case(cases, "measures-an-ordinary-night", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    said = check_named(cases, "measures-an-ordinary-night", tmp_path / "into")

    assert said.state == STILL_FIRES, said.why


def test_the_trap_a_case_lays_in_its_replies_is_taken_away_too(cases, tmp_path):
    """Most cases plant nothing: what they bring is what the sessions say."""
    write_case(
        cases,
        "a-design-with-no-verification",
        {"exit_code": 3, "status": "failed", "refusal": "output-empty-field: verification"},
        replies=({"title": "t", "summary": "s", "changes": ["c"], "seams": [], "verification": [],
                  "asks": [], "assumptions": []},),
    )

    said = check_named(cases, "a-design-with-no-verification", tmp_path / "into")

    assert said.state == ARMED, said.why


def test_the_trap_a_case_lays_over_the_project_is_taken_away_too(cases, tmp_path):
    write_case(
        cases,
        "a-red-test-command",
        {"exit_code": 5, "status": "stopped", "refusal": "gate-closed:"},
        plant=WROTE_IT,
        overlay={"check.sh": "#!/bin/sh\nexit 1\n"},
    )

    said = check_named(cases, "a-red-test-command", tmp_path / "into")

    assert said.state == ARMED, said.why


def test_a_case_that_says_in_words_why_it_cannot_be_disarmed_is_not_run_at_all(cases, tmp_path):
    case = write_case(cases, "three-at-once", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)
    declaring(case, "no_disarm", "the three features are the trap, and two of them is another case")

    said = check_named(cases, "three-at-once", tmp_path / "into")

    assert said.state == NOT_DISARMABLE
    assert "the three features are the trap" in said.why
    assert not (tmp_path / "into").exists()  # nothing was made, so nothing was measured


def test_a_case_declares_what_cannot_be_taken_away_from_it(cases):
    case = write_case(cases, "declares", {"exit_code": 0, "status": "done"})
    declaring(case, "no_disarm", "the loop in the graph is the whole of it")

    assert read_case(cases, "declares").no_disarm == "the loop in the graph is the whole of it"


def test_a_case_that_says_nothing_about_disarming_is_disarmed_mechanically(cases):
    write_case(cases, "plain", {"exit_code": 0, "status": "done"})

    assert read_case(cases, "plain").no_disarm == ""


def test_a_disarmed_case_whose_judge_broke_is_not_called_armed(cases, tmp_path):
    """`could not be judged` is the instrument failing. Reading it as armed is the S7a shape."""
    write_case(
        cases,
        "the-judge-broke",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='echo "no such tool here" >&2\nexit 2\n',
    )

    said = check_named(cases, "the-judge-broke", tmp_path / "into")

    assert said.state == UNCHECKABLE
    assert "no such tool here" in said.why


def test_a_case_that_cannot_be_read_is_could_not_be_checked(cases, tmp_path):
    case = write_case(cases, "unreadable", {"exit_code": 0, "status": "done"})
    (case / "case.toml").write_text("this is not toml at all\n", encoding="utf-8")

    said = check_named(cases, "unreadable", tmp_path / "into")

    assert said.state == UNCHECKABLE


def test_the_disarmed_case_keeps_the_judge_and_loses_the_trap(cases, tmp_path):
    """The one thing the check must not do is measure a different case."""
    from agent_kit.bench.disarm import disarm

    write_case(
        cases,
        "keeps-its-judge",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge="exit 0\n",
        overlay={"check.sh": "#!/bin/sh\nexit 1\n"},
    )

    without = disarm(read_case(cases, "keeps-its-judge"), tmp_path / "without")

    assert without.judge is not None
    assert without.plant is None
    assert without.overlay is None
    assert [path.name for path in without.replies] == ["01-reply.json", "02-reply.json", "03-reply.json"]


# --- the command ------------------------------------------------------------


def test_the_command_names_every_case_and_says_nothing_worse_than_armed(cases, capsys):
    write_case(
        cases,
        "reads-its-plant",
        {"exit_code": 3, "status": "failed"},
        plant=WROTE_IT,
        judge='test -n "$BENCH" || exit 1\n',
    )

    code = main(["bench", "disarm", "--cases", str(cases)])
    printed = capsys.readouterr().out

    assert "reads-its-plant" in printed
    assert ARMED in printed
    assert code == int(ExitCode.OK)


def test_a_case_that_still_fires_disarmed_makes_the_command_exit_as_a_regression(cases, capsys):
    write_case(cases, "measures-the-night", {"exit_code": 0, "status": "done"}, plant=WROTE_IT)

    code = main(["bench", "disarm", "--cases", str(cases)])
    printed = capsys.readouterr().out

    assert STILL_FIRES in printed
    assert code == int(ExitCode.BENCH)


def test_a_check_that_could_not_answer_has_the_other_code(cases, capsys):
    write_case(
        cases,
        "the-judge-broke",
        {"exit_code": 0, "status": "done"},
        plant=WROTE_IT,
        judge='echo "no such tool here" >&2\nexit 2\n',
    )

    code = main(["bench", "disarm", "--cases", str(cases)])

    assert "could not be checked" in capsys.readouterr().out
    assert code == int(ExitCode.BROKEN_BENCH)


def test_one_case_can_be_asked_about_by_name(cases, capsys):
    write_case(cases, "one", {"exit_code": 3, "status": "failed"}, plant=WROTE_IT)
    write_case(cases, "two", {"exit_code": 3, "status": "failed"}, plant=WROTE_IT)

    code = main(["bench", "disarm", "--cases", str(cases), "--case", "one"])
    printed = capsys.readouterr().out

    assert "one" in printed and "two" not in printed
    assert code == int(ExitCode.OK)


def test_a_name_that_is_not_a_case_is_refused_by_name(cases, capsys):
    write_case(cases, "one", {"exit_code": 3, "status": "failed"}, plant=WROTE_IT)

    code = main(["bench", "disarm", "--cases", str(cases), "--case", "nowhere"])

    assert code == int(ExitCode.USAGE)
    assert "nowhere" in capsys.readouterr().err


# --- the cases the kit ships ------------------------------------------------


def test_the_cases_that_cannot_be_disarmed_say_so_in_words(capsys):
    """The escape hatch is allowed and it is not silent: every one is named."""
    root = cases_root()
    exempt = {name: read_case(root, name).no_disarm for name in case_names(root)}
    exempt = {name: why for name, why in exempt.items() if why}

    for name, why in exempt.items():
        assert len(why.split()) >= 5, f"{name} exempts itself without saying why: {why!r}"
    assert len(exempt) <= 20, f"{len(exempt)} cases exempt themselves from being measured"


@pytest.mark.timeout(1800)
def test_every_shipped_case_is_armed_or_says_why_it_cannot_be(capsys):
    """The whole point, as a test: no case the kit ships fires with its trap taken away."""
    code = main(["bench", "disarm"])
    printed = capsys.readouterr()

    assert STILL_FIRES not in printed.out, printed.out
    assert UNCHECKABLE not in printed.out, printed.out
    assert code == int(ExitCode.OK)


def test_an_audit_case_is_disarmed_with_an_answer_that_found_nothing(cases, tmp_path):
    """What is left when a lens's trap is taken away is a project with nothing
    wrong — so the answer it is given is the one a correct lens returns there."""
    from test_bench import audit_case

    audit_case(
        cases,
        "a-finding-nobody-measured",
        {"exit_code": 3, "refusal": "verdict-against-the-inventory"},
        replies=[
            {
                "declared": [
                    {"name": "PyYAML", "verdict": "imported", "imports": ["yaml"],
                     "why": "PyYAML ставит модуль под именем yaml"},
                    {"name": "tabulate", "verdict": "unused", "imports": ["tabulate"],
                     "why": "кажется, лишний"},
                ],
                "undeclared": [],
            }
        ] * 3,
    )

    said = check_named(cases, "a-finding-nobody-measured", tmp_path / "check")

    assert said.state == ARMED, said.said
