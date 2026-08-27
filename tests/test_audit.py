"""The audit: one lens over one commit, and everything it cannot do.

The whole of the step's honesty is here in three parts. The program measures
before anybody is asked; the session may only classify what was measured; and
the session stands where there is nothing to change. Everything below drives it
with the fake provider, which is what the bench does too — a shape that cannot
be driven cannot be trapped.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_kit.audit import Audit, lens_named, lenses
from agent_kit.audit.lenses.dependencies import (
    AuditRefusal,
    Inventory,
    measure,
    judge,
    normalise,
    render_candidates,
)
from agent_kit.audit.tree import unpack_head
from agent_kit.driver.session import Sessions
from agent_kit.errors import ConfigError, ExitCode, ProviderError, StateError
from agent_kit.machine import Ledger, ledger_path
from agent_kit.paths import Paths
from agent_kit.providers.fake.adapter import FakeExecutor

MANIFEST = """[project]
name = "money"
dependencies = ["PyYAML", "tabulate>=0.9", "requests"]

[project.optional-dependencies]
web = ["flask"]

[dependency-groups]
dev = ["pytest", {include-group = "extra"}]
"""

CODE = "import yaml\nimport tabulate\nfrom flask import Flask\nimport os\nAMOUNT = 1000\n"


def repository(tmp_path, manifest=MANIFEST, code=CODE, declared=True):
    """A tiny project with a commit in it, which is what an audit measures."""
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)
    if manifest is not None:
        (root / "pyproject.toml").write_text(manifest, encoding="utf-8")
    if code is not None:
        (root / "money.py").write_text(code, encoding="utf-8")
    if declared:
        (root / ".agent-kit/v3").mkdir(parents=True, exist_ok=True)
        (root / ".agent-kit/v3/project.toml").write_text(
            '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "sh check.sh"\n',
            encoding="utf-8",
        )
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "bench@example.com")
    _git(root, "config", "user.name", "the bench")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "the commit an audit measures")
    return root


def _git(root: Path, *argv: str) -> None:
    subprocess.run(["git", "-C", str(root), *argv], check=True, capture_output=True)


def unpacked(tmp_path, root):
    where = tmp_path / "tree"
    return where, unpack_head(root, where)


def inventory_of(tmp_path, root) -> Inventory:
    where, held = unpacked(tmp_path, root)
    return measure(where, commit=held.commit, branch=held.branch, dirty=held.dirty, files=held.files)


def answer(**over):
    one = {
        "declared": [
            {"name": "PyYAML", "verdict": "imported", "imports": ["yaml"]},
            {"name": "tabulate", "verdict": "imported", "imports": ["tabulate"]},
            {"name": "flask", "verdict": "imported", "imports": ["flask"]},
            {"name": "requests", "verdict": "unused", "imports": ["requests"], "why": "по сети никто не ходит"},
            {"name": "pytest", "verdict": "used-without-importing", "imports": ["pytest"],
             "why": "им гоняют тесты"},
        ],
        "undeclared": [],
    }
    one.update(over)
    return one


def audit(root, replies, today="2026-08-27", out=None):
    fake = FakeExecutor(
        name="fake",
        replies=[json.dumps(one, ensure_ascii=False) if isinstance(one, dict) else one for one in replies],
    )
    sessions = Sessions(
        executors={"fake": fake},
        root=root,
        ledger=Ledger(ledger_path(Paths.from_env())),
        default_provider="fake",
        backoff=0,
    )
    said: list[str] = []
    return (
        Audit(root=root, lens=lens_named("dependencies"), sessions=sessions, today=today,
              say=said.append, out=out),
        said,
        fake,
    )


# --- what the program measures before anybody is asked ----------------------


def test_the_inventory_reads_every_group_of_the_manifest(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    # In the order two manifests of one package would agree on, which is the
    # normalised name — so `PyYAML` stands where `pyyaml` does.
    assert [one.name for one in held.declared] == ["flask", "pytest", "PyYAML", "requests", "tabulate"]
    assert held.keys["pyyaml"].where == "project.dependencies"
    assert held.keys["flask"].where == "project.optional-dependencies.web"
    assert held.keys["pytest"].where == "dependency-groups.dev"


def test_a_requirement_is_read_down_to_its_name(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    # `tabulate>=0.9` is one dependency named `tabulate`, and `PyYAML` and
    # `pyyaml` are one name, so a second telling cannot lay a second row beside
    # the first.
    assert "tabulate" in held.keys
    assert normalise("PyYAML") == normalise("pyyaml") == "pyyaml"


def test_the_imports_are_counted_with_the_line_they_first_stand_on(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    assert sorted(held.modules) == ["flask", "tabulate", "yaml"]
    assert held.modules["yaml"].first_seen == "money.py:1"
    assert held.modules["yaml"].count == 1


def test_the_standard_library_and_the_project_itself_are_not_asked_about(tmp_path):
    root = repository(tmp_path, code="import os\nimport money\nimport yaml\n")
    held = inventory_of(tmp_path, root)
    # Measured, named in the denominator, and never put to a session: a filter
    # nobody prints is the silence this layer exists against.
    assert "os" not in held.modules and "os" in held.stdlib
    assert "money" not in held.modules and "money" in held.own


def test_a_module_beside_the_file_that_imports_it_is_this_project_own(tmp_path):
    """Measured on the kit itself, where it was wrong the first time.

    `tests/` carries no `__init__.py`, so `import conftest` and `import
    test_bench` were read as two packages nobody declared. They are files lying
    beside the file that imports them, which is how Python resolves them — so
    the name of any module in the tree is this project's own.
    """
    root = repository(tmp_path, code="import yaml\n")
    (root / "tests").mkdir()
    (root / "tests/conftest.py").write_text("HOME = 1\n", encoding="utf-8")
    (root / "tests/test_money.py").write_text("import conftest\nimport yaml\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "a test directory that is not a package")

    held = inventory_of(tmp_path, root)
    assert "conftest" not in held.modules and "conftest" in held.own
    assert "yaml" in held.modules


def test_a_relative_import_names_no_dependency(tmp_path):
    root = repository(tmp_path, code="from . import money\nfrom .money import AMOUNT\n")
    assert inventory_of(tmp_path, root).imports == ()


def test_a_file_that_will_not_parse_is_counted_rather_than_read_as_empty(tmp_path):
    root = repository(tmp_path, code="import yaml\n")
    (root / "broken.py").write_text("def (\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "a file nobody can parse")
    held = inventory_of(tmp_path, root)
    assert held.unreadable == ("broken.py",)


def test_a_project_with_no_manifest_is_refused_by_name(tmp_path):
    root = repository(tmp_path, manifest=None)
    with pytest.raises(ConfigError) as refused:
        inventory_of(tmp_path, root)
    assert refused.value.code == "nothing-to-measure"
    assert refused.value.exit_code == ExitCode.CONFIG


def test_a_manifest_that_will_not_parse_is_the_same_refusal(tmp_path):
    root = repository(tmp_path, manifest="[project\nname = ")
    with pytest.raises(ConfigError) as refused:
        inventory_of(tmp_path, root)
    assert refused.value.code == "nothing-to-measure"


def test_a_project_that_declares_no_dependencies_is_measured_and_not_refused(tmp_path):
    # The kit itself once did this, and refusing it would be the lens calling a
    # project undescribed because it has nothing to remove.
    root = repository(tmp_path, manifest='[project]\nname = "money"\ndependencies = []\n', code="import os\n")
    held = inventory_of(tmp_path, root)
    assert held.declared == () and held.imports == ()


# --- the commit, unpacked where there is nothing to change ------------------


def test_the_unpacked_commit_carries_no_repository(tmp_path):
    root = repository(tmp_path)
    where, held = unpacked(tmp_path, root)
    assert (where / "money.py").is_file()
    # No `.git`, so the session cannot commit, branch or push. The possibility
    # is gone rather than forbidden.
    assert not (where / ".git").exists()
    assert held.commit and held.branch == "main" and held.files == 3


def test_what_is_only_in_the_working_copy_is_not_measured_and_is_said(tmp_path):
    root = repository(tmp_path)
    (root / "money.py").write_text("import requests\n", encoding="utf-8")
    where, held = unpacked(tmp_path, root)
    assert held.dirty is True
    assert "requests" not in measure(where).modules


def test_a_directory_with_no_commit_is_refused_by_name(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    with pytest.raises(ConfigError) as refused:
        unpack_head(root, tmp_path / "tree")
    assert refused.value.code == "no-commit"


def test_something_that_is_not_a_repository_is_refused_by_name(tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    with pytest.raises(ConfigError) as refused:
        unpack_head(root, tmp_path / "tree")
    assert refused.value.code == "not-a-repository"


# --- what a row may say ------------------------------------------------------


def test_a_complete_answer_is_judged_into_findings(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    judged = judge(answer(), held)
    assert [one.name for one in judged.findings] == ["requests"]
    assert [row["name"] for row in judged.unimported] == ["pytest"]


def test_a_row_may_not_name_a_dependency_nobody_declared(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = answer()["declared"] + [
        {"name": "urllib3", "verdict": "unused", "imports": ["urllib3"], "why": "нигде"}
    ]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "not-declared"
    assert "urllib3" in refused.value.detail


def test_a_row_may_not_name_a_module_nobody_imports(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(undeclared=[{"module": "numpy", "why": "считает"}]), held)
    assert refused.value.code == "not-declared"
    assert "undeclared[0].module" in refused.value.detail


def test_one_entry_may_not_have_two_rows(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = answer()["declared"] + [{"name": "pyyaml", "verdict": "imported", "imports": ["yaml"]}]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "named-twice"


def test_a_module_may_not_have_two_rows(tmp_path):
    root = repository(tmp_path, manifest='[project]\nname = "money"\ndependencies = []\n')
    held = inventory_of(tmp_path, root)
    twice = [{"module": "yaml", "why": "раз"}, {"module": "yaml", "why": "два"}]
    with pytest.raises(AuditRefusal) as refused:
        judge({"declared": [], "undeclared": twice}, held)
    assert refused.value.code == "named-twice"


def test_a_declared_dependency_left_out_is_named(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = [one for one in answer()["declared"] if one["name"] != "pytest"]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "not-accounted-for"
    assert "pytest" in refused.value.detail


def test_a_measured_module_nobody_claims_is_named(tmp_path):
    # `yaml` is imported and no declared row says it provides it, so it is a
    # package this project uses and does not declare — the direction a session
    # skips by simply not writing a row.
    root = repository(tmp_path, manifest='[project]\nname = "money"\ndependencies = ["tabulate"]\n',
                      code="import yaml\nimport tabulate\n")
    held = inventory_of(tmp_path, root)
    rows = [{"name": "tabulate", "verdict": "imported", "imports": ["tabulate"]}]
    with pytest.raises(AuditRefusal) as refused:
        judge({"declared": rows, "undeclared": []}, held)
    assert refused.value.code == "not-accounted-for"
    assert "yaml" in refused.value.detail


def test_calling_an_imported_dependency_unused_is_refused_with_the_line(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = [
        dict(one, verdict="unused", why="кажется, лишний") if one["name"] == "PyYAML" else one
        for one in answer()["declared"]
    ]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "verdict-against-the-inventory"
    assert "money.py:1" in refused.value.detail


def test_calling_a_dependency_imported_when_nothing_imports_it_is_refused(tmp_path):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = [
        dict(one, verdict="imported") if one["name"] == "requests" else one
        for one in answer()["declared"]
    ]
    rows = [{k: v for k, v in one.items() if k != "why"} if one["name"] == "requests" else one for one in rows]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "verdict-against-the-inventory"


@pytest.mark.parametrize("verdict", ["unused", "used-without-importing"])
def test_a_row_that_is_not_imported_owes_a_reason(tmp_path, verdict):
    held = inventory_of(tmp_path, repository(tmp_path))
    rows = [
        {"name": "requests", "verdict": verdict, "imports": ["requests"]}
        if one["name"] == "requests" else one
        for one in answer()["declared"]
    ]
    with pytest.raises(AuditRefusal) as refused:
        judge(answer(declared=rows), held)
    assert refused.value.code == "no-reason-to-remove"


def test_an_undeclared_module_owes_a_reason_by_the_contract(tmp_path):
    from agent_kit.steps.contract import ContractRefusal

    with pytest.raises(ContractRefusal) as refused:
        lens_named("dependencies").definition.contract.check(
            {"declared": [], "undeclared": [{"module": "yaml"}]}
        )
    assert "undeclared[0].why" in refused.value.code


def test_a_project_with_nothing_declared_may_answer_with_two_empty_lists():
    # `declared` says nothing because there is nothing to say, and that is not
    # the same as a step which did not answer.
    checked = lens_named("dependencies").definition.contract.check({"declared": [], "undeclared": []})
    assert checked["declared"] == [] and checked["undeclared"] == []


# --- one audit, end to end ---------------------------------------------------


def test_an_audit_writes_a_report_and_a_candidate_list(tmp_path):
    root = repository(tmp_path)
    held, said, _ = audit(root, [answer()])
    outcome = held.run()
    assert outcome.findings == 1
    assert outcome.report.read_text(encoding="utf-8").startswith("# Аудит зависимостей")
    assert "requests" in outcome.candidates.read_text(encoding="utf-8")
    assert outcome.report.name == "report.md" and outcome.room.name == "dependencies-2026-08-27"


def test_the_candidate_list_is_a_telling_a_sitting_can_be_given(tmp_path):
    """The seam, measured rather than asserted.

    `batch compose` reads a telling and every feature it returns points at the
    line it came from. So the file this lens writes has to be a telling — and
    the way to know is to hand it to the one that resolves those ranges.
    """
    from agent_kit.sitting import Telling

    root = repository(tmp_path)
    held, _, _ = audit(root, [answer()])
    outcome = held.run()
    telling = Telling(outcome.candidates.read_text(encoding="utf-8"))
    line = next(
        number for number, text in enumerate(telling.lines, start=1) if "requests" in text
    )
    assert "requests" in telling.said(f"L{line}", "candidates")[0]
    # And the first line says whose words these are: in that sitting `said`
    # means *the owner said this*, and here nobody did.
    assert telling.lines[0].startswith("Это измерил кит")


def test_an_audit_leaves_the_working_copy_exactly_as_it_found_it(tmp_path):
    root = repository(tmp_path)
    before = _said(root, "rev-list", "--all", "--count")
    held, _, _ = audit(root, [answer()])
    held.run()
    assert _said(root, "status", "--porcelain") == ""
    assert _said(root, "rev-list", "--all", "--count") == before
    assert _said(root, "for-each-ref", "--format=%(refname)", "refs/heads") == "refs/heads/main"


def test_the_room_is_not_repository_content(tmp_path):
    root = repository(tmp_path)
    held, _, _ = audit(root, [answer()])
    held.run()
    assert (root / ".agent-kit/v3/audits/.gitignore").read_text(encoding="utf-8").endswith("*\n")


def test_the_session_stands_outside_the_repository_it_is_measuring(tmp_path):
    """The half no reading found and a bench trap did.

    git looks for a repository by walking *up*. An unpacked copy under
    `.agent-kit/` is two directories below the project's own `.git`, so the
    session would stand inside the very repository it must not be able to
    touch — and committing, branching and pushing all come back.
    """
    root = repository(tmp_path)
    stood: list[Path] = []

    def reply(request):
        stood.append(Path(request.where))
        return json.dumps(answer(), ensure_ascii=False)

    _driving(root, [reply]).run()
    where = stood[0]
    assert root not in where.parents
    assert _said(where, "rev-parse", "--git-dir") == ""
    # And it does not outlive the audit: everything the session was worth is in
    # the room, and the tree is a copy of a commit.
    assert not where.exists()


def test_an_unpacked_tree_that_lands_inside_a_repository_is_refused(tmp_path):
    # A `TMPDIR` inside somebody's checkout would put the session back inside a
    # repository without a word, so the one thing the location has to be true
    # about is asked rather than trusted.
    root = repository(tmp_path)
    with pytest.raises(ConfigError) as refused:
        unpack_head(root, root / "somewhere" / "under" / "it")
    assert refused.value.code == "tree-inside-a-repository"
    assert refused.value.exit_code == ExitCode.CONFIG


def test_a_lens_that_found_nothing_writes_no_candidate_list(tmp_path):
    root = repository(tmp_path, manifest='[project]\nname = "money"\ndependencies = ["PyYAML"]\n',
                      code="import yaml\n")
    held, said, _ = audit(root, [{"declared": [{"name": "PyYAML", "verdict": "imported", "imports": ["yaml"]}],
                                  "undeclared": []}])
    outcome = held.run()
    assert outcome.findings == 0
    # A file saying *nothing to do* in prose is not an answer a script can read.
    assert outcome.candidates is None
    assert not (outcome.room / "candidates.md").exists()
    assert any("Работы не нашлось" in line for line in said)


def test_the_inventory_is_on_disk_before_the_session_is_asked_anything(tmp_path):
    root = repository(tmp_path)

    def reply(request):
        held = json.loads((Path(request.workdir).parents[2] / "inventory.json").read_text(encoding="utf-8"))
        assert [one["name"] for one in held["declared"]]
        return json.dumps(answer(), ensure_ascii=False)

    fake = FakeExecutor(name="fake", replies=[reply])
    sessions = Sessions(
        executors={"fake": fake}, root=root, ledger=Ledger(ledger_path(Paths.from_env())),
        default_provider="fake", backoff=0,
    )
    Audit(root=root, lens=lens_named("dependencies"), sessions=sessions, say=lambda line: None).run()


def test_an_answer_the_judge_refuses_is_mended_by_the_next_attempt(tmp_path):
    root = repository(tmp_path)
    lying = answer(declared=[dict(one, verdict="unused", why="кажется") if one["name"] == "PyYAML" else one
                             for one in answer()["declared"]])
    held, _, fake = audit(root, [lying, answer()])
    outcome = held.run()
    assert outcome.findings == 1
    assert fake.requests[1].input_text.count("verdict-against-the-inventory") == 1


def test_an_audit_refused_every_time_writes_no_report(tmp_path):
    root = repository(tmp_path)
    lying = answer(declared=[])
    held, _, _ = audit(root, [lying, lying, lying])
    with pytest.raises(StateError) as refused:
        held.run()
    assert refused.value.code == "audit-refused"
    assert refused.value.exit_code == ExitCode.STATE
    assert not (root / ".agent-kit/v3/audits/dependencies-2026-08-27/report.md").exists()


def test_a_refused_audit_leaves_no_tree_behind(tmp_path):
    root = repository(tmp_path)
    stood: list[Path] = []

    def reply(request):
        stood.append(Path(request.where))
        return json.dumps(answer(declared=[]), ensure_ascii=False)

    with pytest.raises(StateError):
        _driving(root, [reply, reply, reply]).run()
    assert stood and not stood[0].exists()


def test_a_repository_that_declares_nothing_to_the_kit_is_still_measured(tmp_path):
    """The audit reads the project's declaration and does not require one.

    Nothing here has a reader for it: the role table is optional and already
    read that way, and the papers go under this project's own kit directory
    whether or not anybody ran `init`. A refusal with no reader is a refusal
    this project's own rules delete rather than document.
    """
    root = repository(tmp_path, declared=False)
    held, _, _ = audit(root, [answer()])
    assert held.run().findings == 1


def test_a_project_with_nothing_to_measure_spends_no_session(tmp_path):
    root = repository(tmp_path, manifest=None)
    held, _, fake = audit(root, [answer()])
    with pytest.raises(ConfigError) as refused:
        held.run()
    assert refused.value.code == "nothing-to-measure"
    assert fake.requests == []
    assert not (root / ".agent-kit/v3/audits/dependencies-2026-08-27").exists()


def test_the_candidate_list_goes_where_it_was_asked_to(tmp_path):
    root = repository(tmp_path)
    where = tmp_path / "tonight.md"
    held, _, _ = audit(root, [answer()], out=where)
    outcome = held.run()
    assert outcome.candidates == where and "requests" in where.read_text(encoding="utf-8")


def test_a_second_audit_on_one_day_gets_a_room_of_its_own(tmp_path):
    root = repository(tmp_path)
    audit(root, [answer()])[0].run()
    outcome = audit(root, [answer()])[0].run()
    assert outcome.room.name == "dependencies-2026-08-27-2"


def test_a_lens_the_kit_does_not_have_is_refused_by_name():
    from agent_kit.errors import UsageError

    with pytest.raises(UsageError) as refused:
        lens_named("security")
    assert refused.value.code == "unknown-lens"
    assert sorted(lenses()) == ["dependencies"]


def _driving(root: Path, replies, today: str = "2026-08-27"):
    """An audit whose provider is a callable, so a test can see where it stood."""
    fake = FakeExecutor(name="fake", replies=list(replies))
    sessions = Sessions(
        executors={"fake": fake}, root=root, ledger=Ledger(ledger_path(Paths.from_env())),
        default_provider="fake", backoff=0,
    )
    return Audit(root=root, lens=lens_named("dependencies"), sessions=sessions, today=today,
                 say=lambda line: None)


def _said(root: Path, *argv: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True)
    return done.stdout.strip()
