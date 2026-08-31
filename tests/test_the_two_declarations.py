"""S9 — two providers nobody here has run, declared from their own documentation.

Every key in a `provider.toml` is a claim about somebody else's tool, and these
two were written from the tools' published references rather than from a machine
they were run on. So what these tests hold is the half that can be held without
them: the declaration parses, it carries only keys the kit reads, the walk can
print an install and a login for it, and the two free rungs can be *put* to it.

What they do not hold, and no test in this repository can: that `codex` accepts
`exec`, that `gemini` goes non-interactive on a pipe, that either answers
`--version`. That is `agent-kit provider check <name>` on a machine where the
tool is installed, and until somebody runs it the level in each block is a claim.
"""

import pytest

from agent_kit.providers import registry

SHIPPED = ("codex", "gemini_cli")


@pytest.mark.parametrize("name", SHIPPED)
def test_it_is_in_the_catalogue_because_it_is_a_folder(name):
    assert name in registry.provider_names()


@pytest.mark.parametrize("name", SHIPPED)
def test_it_declares_a_level_it_has_not_earned_and_says_so(name):
    """`level` is what a provider claims; `provider check` is what it earns.

    There is no third state and none is invented here: `Declaration.read`
    defaults a missing `level` to "A" silently, so leaving it out would claim
    exactly the same thing with nobody able to see that it had been left out.
    It is written, and what it is worth is said in the notes.
    """
    facts = registry.facts(name)

    assert facts.level == "A"
    assert facts.real is True
    assert "nobody" in facts.notes.lower() or "not been run" in facts.notes.lower()


@pytest.mark.parametrize("name", SHIPPED)
def test_the_walk_has_both_commands_to_print(name):
    """A declaration with no install is a provider the way in cannot help with."""
    facts = registry.facts(name)

    assert facts.install and facts.login
    assert all(isinstance(word, str) and word for word in facts.install + facts.login)


@pytest.mark.parametrize("name", SHIPPED)
def test_both_free_rungs_can_be_put_to_it(name):
    """Not that they pass — the tool is not here — but that they are asked.

    A provider with no `version` flag is *not asked* the second rung, which is
    right for a tool that declares none and wrong for these two: a level nobody
    can measure for free is a level nobody looks at.
    """
    from agent_kit.driver.check import free_rungs

    facts = registry.facts(name)
    assert facts.binary
    assert facts.flags.get("version")

    rungs = free_rungs(name)
    assert [rung.name for rung in rungs] == ["binary", "answers"]
    assert all(rung.applies for rung in rungs) or not rungs[0].passed


def test_codex_is_told_to_write_where_the_run_builds():
    """`codex exec` sandboxes to read-only unless told otherwise, and a provider
    that cannot write earns no level since the `writes` rung. `workspace-write`
    and not `danger-full-access`: a run builds in its own worktree, so the
    workspace is the whole of what it has any business editing."""
    flags = registry.facts("codex").flags

    assert flags["full_access"] == ["-s", "workspace-write", "-a", "never"]
    assert flags["headless"] == ["exec"]


def test_gemini_declares_no_headless_flag_on_purpose():
    """It goes non-interactive by itself when stdin is not a terminal, and the
    kit always hands it a pipe. This is the case that made the flag-key check
    worth building: absent and misspelt build the identical argv."""
    flags = registry.facts("gemini_cli").flags

    assert "headless" not in flags
    assert flags["full_access"] == ["--approval-mode", "yolo"]


@pytest.mark.parametrize("name", SHIPPED)
def test_neither_claims_to_read_a_limit_or_a_transcript(name):
    """Level A reads neither, so declaring either would be a field with no
    reader — and the `limits` rung measures the declared phrases against a
    sentence the kit builds out of them, so phrases nobody has seen a tool say
    would earn a green rung for nothing."""
    facts = registry.facts(name)

    assert facts.reads_limits is False
    assert facts.transcript_root is None
    assert facts.answer == {}


@pytest.mark.parametrize("name", SHIPPED)
def test_an_effort_neither_tool_has_a_flag_for_is_refused_not_dropped(name):
    """Codex sets reasoning effort by config override and Gemini has no such
    idea at all, so neither declares the flag — and a machine that names one
    hears about it before it spends rather than after."""
    from agent_kit.errors import ConfigError

    with pytest.raises(ConfigError) as caught:
        registry.build_executor(name, {"effort": ["high"]})

    assert caught.value.code == "effort-not-selectable"


@pytest.mark.parametrize("name", SHIPPED)
def test_a_model_either_tool_can_be_told_is_passed_on(name):
    """Both document `--model`, so both declare it and neither refuses one."""
    executor = registry.build_executor(name, {"model": ["a-model"]})

    assert "--model" in executor.command()
    assert "a-model" in executor.command()
