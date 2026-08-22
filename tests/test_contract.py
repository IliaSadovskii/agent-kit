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


def test_a_fence_with_no_newline_after_the_tag_is_still_the_output():
    assert parse_output('```json {"branch": "kit/x"}```')["branch"] == "kit/x"


def test_a_contract_that_names_no_choices_is_refused_when_it_is_declared():
    from agent_kit.steps.contract import ContractRefusal

    with pytest.raises(ContractRefusal) as caught:
        Enum("severity")

    assert caught.value.code == "bad-contract"


# --- S6: a field a project can make required --------------------------------
#
# The join — an expensive assumption owes a block — binds a project that keeps
# knowledge and not one that keeps none. So the contract is not fixed for all
# time: the driver asks for the stricter copy, and renders that same copy into
# the step's input. The agent is told in the form the program checks.

ASSUMPTIONS = Contract(
    fields=(
        Records(
            "assumptions",
            shape=(
                Text("what"),
                Bool("expensive"),
                Text("block", required=False),
            ),
        ),
    )
)

STRICTER = ASSUMPTIONS.requiring("assumptions.block", when="expensive")


def test_the_base_contract_lets_an_expensive_assumption_through_with_no_block():
    output = ASSUMPTIONS.check({"assumptions": [{"what": "the rate is whole", "expensive": True}]})

    assert output["assumptions"][0]["block"] is None


def test_the_stricter_copy_refuses_it_and_names_the_field():
    with pytest.raises(ContractRefusal) as refused:
        STRICTER.check({"assumptions": [{"what": "the rate is whole", "expensive": True}]})

    assert refused.value.code == "output-missing-field: assumptions[0].block"


def test_the_stricter_copy_asks_nothing_of_an_assumption_that_is_not_expensive():
    output = STRICTER.check({"assumptions": [{"what": "the rate is whole", "expensive": False}]})

    assert output["assumptions"][0]["block"] is None


def test_the_stricter_copy_says_so_where_the_agent_reads_it():
    assert "required when `expensive`" in STRICTER.describe()
    assert "required when `expensive`" not in ASSUMPTIONS.describe()


def test_making_a_copy_leaves_the_original_alone():
    ASSUMPTIONS.requiring("assumptions.block", when="expensive")

    assert ASSUMPTIONS.check({"assumptions": [{"what": "x", "expensive": True}]})["assumptions"][0]["block"] is None


def test_a_path_that_names_no_field_is_a_defect_in_the_kit_not_a_refused_step():
    with pytest.raises(ContractRefusal) as refused:
        ASSUMPTIONS.requiring("assumptions.ghost", when="expensive")

    assert refused.value.code == "bad-contract"
