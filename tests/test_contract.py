"""S2 — the contract. What a step must return, and what refusing looks like."""

import pytest

from agent_kit.steps.contract import (
    Bool,
    Contract,
    ContractRefusal,
    Enum,
    Records,
    Text,
    TextList,
    parse_output,
)

CONTRACT = Contract(
    fields=(
        Text("branch", help="the branch this working copy has checked out"),
        Bool("can_write", help="whether the agent could write a file"),
        TextList("notes", required=False, help="anything worth saying"),
        Records(
            "findings",
            required=False,
            shape=(Text("what"), Enum("severity", choices=("note", "advice", "blocking"))),
        ),
    )
)


def test_a_valid_output_comes_back_clean():
    output = CONTRACT.check({"branch": "kit/add-login", "can_write": True})

    assert output == {"branch": "kit/add-login", "can_write": True, "notes": None, "findings": None}


def test_a_missing_field_is_named():
    with pytest.raises(ContractRefusal) as caught:
        CONTRACT.check({"can_write": True})

    assert caught.value.code == "output-missing-field: branch"


def test_a_field_of_the_wrong_kind_is_named():
    with pytest.raises(ContractRefusal) as caught:
        CONTRACT.check({"branch": "kit/x", "can_write": "yes"})

    assert caught.value.code == "output-bad-field: can_write"
    assert "true or false" in caught.value.detail


def test_a_record_is_checked_field_by_field():
    with pytest.raises(ContractRefusal) as caught:
        CONTRACT.check(
            {
                "branch": "kit/x",
                "can_write": True,
                "findings": [{"what": "the test lies", "severity": "fatal"}],
            }
        )

    assert caught.value.code == "output-bad-field: findings[0].severity"
    assert "note, advice, blocking" in caught.value.detail


def test_records_come_back_whole():
    output = CONTRACT.check(
        {
            "branch": "kit/x",
            "can_write": True,
            "findings": [{"what": "the test lies", "severity": "blocking"}],
        }
    )

    assert output["findings"] == [{"what": "the test lies", "severity": "blocking"}]


def test_what_the_contract_did_not_ask_for_is_dropped_not_refused():
    """An agent that says one extra thing has not failed its step."""
    output = CONTRACT.check({"branch": "kit/x", "can_write": True, "mood": "cheerful"})

    assert "mood" not in output


def test_an_output_that_is_not_a_table_is_refused():
    with pytest.raises(ContractRefusal) as caught:
        CONTRACT.check(["branch"])

    assert caught.value.code == "output-not-a-table"


def test_the_contract_describes_itself_for_the_input():
    described = CONTRACT.describe()

    assert "branch" in described and "required" in described
    assert "note, advice, blocking" in described
    assert "notes" in described and "optional" in described


# --- finding the output in what an agent said ------------------------------


def test_a_fenced_json_block_is_the_output():
    raw = 'I looked around.\n\n```json\n{"branch": "kit/x"}\n```\n\nThat is all.'

    assert parse_output(raw) == {"branch": "kit/x"}


def test_the_last_block_wins_because_agents_think_out_loud():
    raw = '```json\n{"branch": "first"}\n```\nOn reflection:\n```json\n{"branch": "second"}\n```'

    assert parse_output(raw)["branch"] == "second"


def test_bare_json_is_accepted():
    assert parse_output('  {"branch": "kit/x"}  ') == {"branch": "kit/x"}


@pytest.mark.parametrize("raw", ["", "   ", "I could not do it, sorry.", "```json\n{oops\n```"])
def test_anything_else_is_refused_by_name(raw):
    with pytest.raises(ContractRefusal) as caught:
        parse_output(raw)

    assert caught.value.code in ("output-missing", "output-not-json")
