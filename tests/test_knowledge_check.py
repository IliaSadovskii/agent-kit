import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "plugins", "agent-kit", "scripts")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TEMPLATE = os.path.join(
    REPO, "plugins", "agent-kit", "templates", "project", "contract.yml"
)

sys.path.insert(0, SCRIPTS)

import knowledge_check  # noqa: E402


def run_root(root, extra_args=None):
    argv = ["--root", root] + (extra_args or [])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = knowledge_check.main(argv)
    return code, out.getvalue()


def run_check(fixture, extra_args=None):
    return run_root(os.path.join(FIXTURES, fixture), extra_args)


@contextlib.contextmanager
def project(contract=None, files=None):
    """A throwaway project root, optionally with a contract and source files."""
    root = tempfile.mkdtemp()
    try:
        if contract is not None:
            path = os.path.join(root, ".agent-kit", "knowledge", "contract.yml")
            os.makedirs(os.path.dirname(path))
            if isinstance(contract, bytes):
                with open(path, "wb") as fh:
                    fh.write(contract)
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(contract)
        for name, content in (files or {}).items():
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            mode = "wb" if isinstance(content, bytes) else "w"
            with open(path, mode) as fh:
                fh.write(content)
        yield root
    finally:
        shutil.rmtree(root)


class KnowledgeCheckTests(unittest.TestCase):
    def test_clean_is_exit_0(self):
        code, output = run_check("clean", ["--skip-verification"])
        self.assertEqual(code, 0)
        self.assertIn("stale        none", output)

    def test_clean_runs_verification_commands(self):
        # No --skip-verification: the fixture's "true" command must actually run and pass.
        code, _output = run_check("clean")
        self.assertEqual(code, 0)

    def test_empty_slot_is_a_finding(self):
        code, output = run_check("empty_slot", ["--skip-verification"])
        self.assertEqual(code, 1)
        self.assertIn("architecture_stance", output)

    def test_conflicts_slot_is_a_finding(self):
        code, output = run_check("conflicts_slot", ["--skip-verification"])
        self.assertEqual(code, 1)
        self.assertIn("architecture_stance", output)

    def test_edited_bound_section_is_stale(self):
        code, output = run_check("edited_bound_section", ["--skip-verification"])
        self.assertEqual(code, 1)
        self.assertIn("stale", output.splitlines()[-1])

    def test_edit_to_different_section_does_not_go_stale(self):
        code, output = run_check("edited_other_section", ["--skip-verification"])
        self.assertEqual(code, 0)
        self.assertIn("stale        none", output)

    def test_renamed_heading_is_structural(self):
        code, output = run_check("renamed_heading", ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("architecture_stance", output)

    def test_missing_source_file_is_structural(self):
        code, output = run_check("missing_source_file", ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("architecture_stance", output)

    def test_unparseable_contract_is_structural(self):
        code, output = run_check("unparseable_contract", ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("contract", output)

    def test_failing_verification_command_is_structural(self):
        code, output = run_check("failing_command")
        self.assertEqual(code, 2)
        self.assertIn("verification", output)

    def test_shipped_template_is_all_findings(self):
        # The file the kit actually ships, not a copy of it under fixtures — a copy
        # can drift from the template, or outlive its deletion, without failing.
        with open(TEMPLATE, encoding="utf-8") as fh:
            template = fh.read()
        with project(contract=template) as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 1)
        for name in (
            "north_star",
            "architecture_stance",
            "verification",
            "mvp_bounds",
            "scenarios",
            "deferred_seams",
            "actors",
            "entities",
            "actions",
            "screens",
            "integrations",
        ):
            self.assertIn(name, output)

    def test_no_contract_names_the_template_to_copy(self):
        with project() as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("templates/project/contract.yml", output)

    def test_slots_not_a_mapping_is_structural(self):
        # A structurally broken contract must reach stage 6's gate as exit 2,
        # not as a traceback and not as "findings".
        with project(contract="version: 1\nslots:\n  - a\n  - b\n") as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("slots", output)

    def test_binary_source_file_is_structural(self):
        contract = (
            "version: 1\n"
            "slots:\n"
            "  architecture_stance:\n"
            "    status: filled\n"
            "    source: docs/GUIDE.md#Testing\n"
            "    rev: aaaaaaaaaaaa\n"
        )
        with project(contract=contract, files={"docs/GUIDE.md": b"\xff\xfe\x00binary"}) as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read source file", output)

    def test_filled_with_nothing_behind_it_is_a_finding(self):
        contract = (
            "version: 1\n"
            "slots:\n"
            "  north_star:\n"
            "    status: filled\n"
            "    source: null\n"
            "    rev: null\n"
        )
        with project(contract=contract) as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 1)
        self.assertIn("nothing backs it", output)

    def test_missing_rev_reports_the_current_one(self):
        contract = (
            "version: 1\n"
            "slots:\n"
            "  architecture_stance:\n"
            "    status: filled\n"
            "    source: docs/GUIDE.md#Testing\n"
            "    rev: null\n"
        )
        files = {"docs/GUIDE.md": "# Testing\n\nbody\n"}
        with project(contract=contract, files=files) as root:
            code, output = run_root(root, ["--skip-verification"])
        self.assertEqual(code, 1)
        self.assertIn("current rev is", output)
        # The value it prints is the one that makes the slot clean.
        printed = output.split("current rev is ")[1].split()[0]
        with project(
            contract=contract.replace("rev: null", "rev: {}".format(printed)), files=files
        ) as root:
            self.assertEqual(run_root(root, ["--skip-verification"])[0], 0)

    def test_commands_of_an_unsettled_slot_do_not_run(self):
        marker = os.path.join(tempfile.gettempdir(), "kit_unsettled_marker")
        if os.path.exists(marker):
            os.remove(marker)
        contract = (
            "version: 1\n"
            "slots:\n"
            "  verification:\n"
            "    status: empty\n"
            "    commands:\n"
            '      - "touch {}"\n'.format(marker)
        )
        with project(contract=contract) as root:
            code, _output = run_root(root)
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(marker))

    def test_repository_contract_is_clean(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = knowledge_check.main(["--root", REPO, "--skip-verification"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
