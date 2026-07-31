import contextlib
import io
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "plugins", "agent-kit", "scripts")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

sys.path.insert(0, SCRIPTS)

import knowledge_check  # noqa: E402


def run_check(fixture, extra_args=None):
    root = os.path.join(FIXTURES, fixture)
    argv = ["--root", root] + (extra_args or [])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = knowledge_check.main(argv)
    return code, out.getvalue()


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

    def test_template_contract_is_all_findings(self):
        code, output = run_check("template", ["--skip-verification"])
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

    def test_repository_contract_is_clean(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = knowledge_check.main(["--root", REPO, "--skip-verification"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
