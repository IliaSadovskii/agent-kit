"""The knowledge check, against documents built to fail it.

    python3 -m unittest discover -s tests

A check that reports nothing is indistinguishable from a check that finds nothing, so every rule
here is shown failing on a document that breaks it and silent on one that does not.
"""

import contextlib
import importlib.util
import json
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check", ROOT / "plugins" / "agent-kit" / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

ACTORS = """<!--
fields: How they appear, What they can do
-->
# Actors

### A guest
`key: guest`

**How they appear:** opens the site
**What they can do:** read the feed
"""

ACTIONS = """<!--
fields: Who, What happens, Can go wrong
-->
# Actions

### Guest reads the feed
`key: guest.browse_feed` · `state: built`

**Who:** guest
**What happens:** the feed is rendered, newest first
**Can go wrong:** nothing that matters
"""

MANIFEST = "knowledge:\n" + "".join(f"  {slot}: filled\n" for slot in check.SLOTS)


def without_shape(text):
    """Drop the "written by an older kit" statement.

    These fixtures are deliberately minimal — two slots, three fields — so they are behind the
    shipped templates by construction, and that block would appear in every assertion about every
    other rule. It is orthogonal to all of them and has tests of its own, which keep it.
    """
    if "Written by an older kit" not in text:
        return text
    kept, dropping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("Written by an older kit"):
            dropping = True
            if kept and kept[-1] == "\n":
                kept.pop()
            continue
        if dropping and (line.startswith("  ") or line == "\n"):
            continue
        dropping = False
        kept.append(line)
    return "".join(kept)


class CheckCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "docs" / "knowledge").mkdir(parents=True)
        (self.root / ".agent-kit").mkdir()
        self.write("actors.md", ACTORS)
        self.write("actions.md", ACTIONS)
        (self.root / ".agent-kit" / "project.yml").write_text(MANIFEST, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        (self.root / "docs" / "knowledge" / name).write_text(text, encoding="utf-8")

    def run_check(self, *args, keep_shape=False):
        """Run the check, and by default drop the "written by an older kit" block.

        These fixtures are deliberately minimal — two slots, three fields — so they are behind the
        shipped templates by construction, and that statement would appear in every assertion about
        every other rule. It is orthogonal to all of them and has its own tests, which ask for it.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([str(self.root), "--offline", *args])
        text = out.getvalue()
        return code, text if keep_shape else without_shape(text)

    # ---- the baseline has to be silent, or nothing below means anything -----------------------

    def test_clean_knowledge_says_nothing(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_status_prints_the_standing_even_when_clean(self):
        code, output = self.run_check("--status")
        self.assertEqual(code, 0)
        self.assertIn("built: 1", output)

    # ---- the product's parts, and who has walked them -------------------------------------------

    def test_parts_are_counted_walked_against_derived(self):
        """Two commands were told to read this and neither had anything to read it with: a plain
        blueprint offers the walk, and an epic's gate says how much of the description nobody has
        ever seen."""
        self.write("product.md", "# Product\n\n## Parts\n\n"
                                 "- вход и аккаунт — `walked: 2026-08-09`\n"
                                 "- карта тем — `derived`\n"
                                 "- урок — `walked: 2026-08-10`\n")
        _code, output = self.run_check("--status")
        self.assertIn("Parts: 3 recorded, 2 walked", output)
        self.assertIn("1 derived", output)

    def test_a_product_with_no_parts_recorded_says_so(self):
        self.write("product.md", "# Product\n\n## What it is for\n\nA feed.\n")
        _code, output = self.run_check("--status")
        self.assertIn("Parts: none recorded", output)

    def test_the_templates_own_example_is_not_counted_as_a_part(self):
        """A file copied and not yet filled in would otherwise report three parts nobody has."""
        template = (ROOT / "plugins" / "agent-kit" / "templates" / "knowledge" / "product.md")
        self.write("product.md", template.read_text(encoding="utf-8"))
        _code, output = self.run_check("--status")
        self.assertIn("Parts: none recorded", output)

    def test_the_parts_count_is_a_statement_and_not_a_finding(self):
        self.write("product.md", "# Product\n\n## Parts\n\n- вход — `derived`\n")
        code, _output = self.run_check("--status")
        self.assertEqual(code, 0)

    # ---- knowledge written by an older kit -----------------------------------------------------

    def test_a_record_declaring_fewer_fields_than_the_template_is_named(self):
        """Each file is checked against its own `fields:` line, so a field the templates gained
        later is invisible to every other check there is."""
        self.write("actions.md", ACTIONS.replace("fields: Who, What happens, Can go wrong",
                                                 "fields: Who, What happens"))
        code, output = self.run_check(keep_shape=True)
        self.assertEqual(code, 0, "behind is not broken")
        self.assertIn("Written by an older kit", output)
        self.assertIn("actions.md declares 2 fields per record", output)

    def test_it_names_neither_side_as_the_missing_one(self):
        """The template is in English and the files are in the project's language, so pairing them
        is a guess — both lists are printed and the pairing is done with the owner."""
        self.write("actions.md", ACTIONS.replace("fields: Who, What happens, Can go wrong",
                                                 "fields: Кто, Что происходит"))
        _code, output = self.run_check(keep_shape=True)
        self.assertIn("Template:", output)
        self.assertIn("Here: Кто, Что происходит", output)

    def test_a_project_matching_the_templates_says_nothing(self):
        for name in ("product", "actors", "entities", "actions", "screens", "integrations",
                     "scenarios", "stack"):
            model = ROOT / "plugins" / "agent-kit" / "templates" / "knowledge" / f"{name}.md"
            self.write(f"{name}.md", model.read_text(encoding="utf-8"))
        (self.root / ".agent-kit" / "project.yml").write_text(
            (ROOT / "plugins" / "agent-kit" / "templates" / "project.yml").read_text(encoding="utf-8"),
            encoding="utf-8")
        _code, output = self.run_check(keep_shape=True)
        self.assertNotIn("Written by an older kit", output)

    # ---- the channels a program can check ------------------------------------------------------

    def test_a_file_in_a_run_directory_that_belongs_to_nothing_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text('{"slug": "x"}', encoding="utf-8")
        (directory / "run.log").write_text("", encoding="utf-8")
        _code, output = self.run_check()
        self.assertNotIn("not a run's own", output)
        (directory / "advance.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("x/advance.sh", output)

    def test_an_audit_box_ticked_without_its_pull_request_is_named(self):
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text(
            "# Tests\n\n- [x] closed by PR #21\n- [ ] still open\n- [x] done, honest\n",
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("ticked without naming the pull request", output)
        self.assertIn("tests.md (1)", output)

    def test_a_declined_item_is_not_a_tick_waiting_for_a_pull_request(self):
        """The lens's own way of recording a refusal. No pull request will ever close one, so a
        rule demanding a number would be permanently wrong about a format the kit prescribes."""
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text(
            "# Tests\n\n- [x] `declined`: `guest.open_post` — visual only\n", encoding="utf-8")
        _code, output = self.run_check()
        self.assertNotIn("ticked without naming the pull request", output)

    # ---- what a lens says it walked ------------------------------------------------------------

    def audit(self, name, text):
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True, exist_ok=True)
        (audits / f"{name}.md").write_text(text, encoding="utf-8")

    def test_a_lens_whose_own_numbers_do_not_add_up(self):
        """Three lenses call their completeness countable and leave the counting to the agent that
        wrote the report. This is the counting."""
        self.audit("tests", "# Tests\n\n<!-- agent-kit:audit lens=tests walked=40 covered=30 "
                            "gaps=5 -->\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("walked 40 and accounts for 35", output)

    def test_a_lens_that_adds_up_says_nothing_and_is_counted(self):
        self.audit("tests", "# Tests\n\n<!-- agent-kit:audit lens=tests walked=40 covered=30 "
                            "gaps=5 unjudged=3 deferred=1 declined=1 -->\n")
        code, output = self.run_check("--status")
        self.assertEqual(code, 0)
        self.assertIn("Audit tests: walked 40", output)

    def test_the_buckets_are_the_lenss_own_business(self):
        """`walks`/`breaks` for scenarios, `covered`/`gaps` for tests — the check knows neither."""
        self.audit("scenarios", "# Scenarios\n\n<!-- agent-kit:audit lens=scenarios walked=9 "
                                "walks=7 breaks=1 unfollowable=1 -->\n")
        code, _output = self.run_check()
        self.assertEqual(code, 0)

    def test_a_lens_file_with_no_counters_is_named_once_for_all_of_them(self):
        self.audit("tests", "# Tests\n")
        self.audit("deps", "# Deps\n")
        _code, output = self.run_check()
        self.assertIn("no `agent-kit:audit` counters (2)", output)
        self.assertIn("deps, tests", output)

    def test_a_file_that_belongs_to_no_lens_is_not_asked_for_counters(self):
        self.audit("baseline", "# Baseline\n")
        _code, output = self.run_check()
        self.assertNotIn("counters", output)
        self.assertNotIn("neither a lens", output)

    def test_a_file_that_is_no_lens_and_not_the_baseline_is_named_rather_than_skipped(self):
        """It used to be skipped in silence, which made a lens nobody wired in — or a typo in a
        file name — read exactly like the baseline: no counters added up, and nothing said so."""
        self.audit("accessibility", "# Accessibility\n\n- [ ] contrast on the offer card\n")
        _code, output = self.run_check()
        self.assertIn("neither a lens this kit runs nor the baseline", output)
        self.assertIn("accessibility.md", output)

    def advice(self, name, text):
        path = self.root / "docs" / "advice"
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{name}.md").write_text(text, encoding="utf-8")

    def test_a_file_no_lens_of_advise_writes_is_named(self):
        """`docs/audits/` has had this rule since a lens nobody wired in read exactly like the
        baseline. This side had none of it: a report under any name at all sat there with its scope
        added up by nobody, and the silence read as a clean directory."""
        self.advice("prodcut", "# Продукт\n\n- what users cannot finish\n")
        _code, output = self.run_check()
        self.assertIn("no lens of `advise` writes", output)
        self.assertIn("prodcut.md", output)

    def test_the_three_lenses_of_advise_say_nothing(self):
        for lens in ("product", "code", "money"):
            self.advice(lens, f"# {lens}\n\n- something\n")
        _code, output = self.run_check()
        self.assertNotIn("no lens of `advise` writes", output)

    # ---- the batch records a project already has -----------------------------------------------

    def batch_file(self, name, text):
        runs = self.root / "docs" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / name).write_text(text, encoding="utf-8")

    def test_a_batch_record_nothing_can_read_is_said_rather_than_passed(self):
        self.batch_file("2026-08-05-offers.json", "slug: offers\n")
        _code, output = self.run_check()
        self.assertIn("cannot be read as a record (1)", output)

    def test_a_batch_record_with_a_key_nothing_knows(self):
        self.batch_file("2026-08-05-offers.json",
                        json.dumps({"slug": "x", "tokens": 400000}))
        _code, output = self.run_check()
        self.assertIn("fields the template does not: tokens (1)", output)

    def test_a_batch_record_in_the_shipped_shape_says_nothing(self):
        template = json.loads((ROOT / "plugins" / "agent-kit" / "templates" / "batch.json")
                              .read_text(encoding="utf-8"))
        self.batch_file("2026-08-05-offers.json",
                        json.dumps({k: v for k, v in template.items() if not k.startswith("_")}))
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_refusal_is_marked_and_not_counted_as_an_unsigned_tick(self):
        self.audit("tests", "# Tests\n\n<!-- agent-kit:audit lens=tests walked=1 declined=1 -->\n\n"
                            "- [x] `declined`: `guest.open_post` — визуальное, проверять нечего\n")
        _code, output = self.run_check()
        self.assertNotIn("ticked without naming the pull request", output)

    def test_the_english_word_in_a_sentence_is_not_the_mark(self):
        """The mark is backticked. A tick whose prose happens to say the word is still unsigned."""
        self.audit("tests", "# Tests\n\n<!-- agent-kit:audit lens=tests walked=1 gaps=1 -->\n\n"
                            "- [x] the owner declined this last week, so it is done\n")
        _code, output = self.run_check()
        self.assertIn("ticked without naming the pull request", output)

    def test_unsigned_ticks_are_counted_per_file_rather_than_listed(self):
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text("# Tests\n\n" + "- [x] done\n" * 12, encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("(12)", output)
        self.assertNotIn("tests.md:3", output)

    # ---- the brief: what a run reads before it designs, in one call ---------------------------

    def test_a_brief_carries_the_entry_the_corner_and_the_map(self):
        self.write("stack.md", "# Stack\n\nLaravel, and no ORM tricks.\n")
        code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertEqual(code, 0)
        self.assertIn("Guest reads the feed", output)
        self.assertIn("newest first", output)
        self.assertIn("knowledge:", output)            # the project's own corner
        self.assertIn("no ORM tricks", output)         # the library map

    def test_a_brief_pulls_in_what_the_entry_names(self):
        self.write("stack.md", "# Stack\n")
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("A guest", output, "the actor the entry names comes with it")

    def test_a_brief_says_what_it_could_not_find(self):
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("does not exist", output, "a missing library map is said, not left out")

    def test_a_brief_names_its_own_boundary(self):
        """Silence in a brief has to mean one thing. Without the boundary, a brief that dropped
        the entry its entry depends on reads like one where the entry depends on nothing."""
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("pulled in:", output)
        self.assertIn("is not looked up", output)

    def test_a_brief_names_a_key_the_knowledge_never_defined(self):
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:**", "**Reached from:** `screen.feed`\n\n**Can go wrong:**"))
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("defined nowhere", output)
        self.assertIn("screen.feed", output)

    def test_a_brief_does_not_call_prose_a_missing_key(self):
        """A status, a column and a config path all look like a key. Guessing at them named
        twenty-two innocents in one entry on a real project."""
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:**", "**What changes:** the post goes to `archived`, "
                                 "`posts.author_id` stays\n\n**Can go wrong:**"))
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertNotIn("archived", output.split("pulled in:")[-1])
        self.assertNotIn("posts.author_id", output.split("pulled in:")[-1])

    def test_an_unknown_key_names_the_near_miss_instead_of_guessing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _output = self.run_check("--brief", "guest.browse_fee")
        self.assertEqual(code, 2)
        self.assertIn("guest.browse_feed", err.getvalue())

    # ---- one rule at a time --------------------------------------------------------------------

    def test_an_empty_field_is_a_finding(self):
        self.write("actions.md", ACTIONS.replace("**What happens:** the feed is rendered, newest first",
                                                 "**What happens:**"))
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Fields", output)
        self.assertIn("What happens", output)

    def test_a_field_answered_by_a_list_below_it_is_filled(self):
        self.write("actions.md", ACTIONS.replace(
            "**What happens:** the feed is rendered, newest first",
            "**What happens:**\n1. the feed is rendered\n2. newest first"))
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_an_action_whose_actor_does_not_exist(self):
        self.write("actions.md", ACTIONS.replace("guest.browse_feed", "ghost.browse_feed"))
        _code, output = self.run_check()
        self.assertIn("no actor 'ghost'", output)

    def test_a_key_named_but_never_defined(self):
        self.write("actions.md", ACTIONS.replace("**Can go wrong:** nothing that matters",
                                                 "**Can go wrong:** falls back to `screen.missing`"))
        _code, output = self.run_check()
        self.assertIn("screen.missing is not defined", output)

    def test_prose_with_a_dot_in_it_is_not_mistaken_for_a_key(self):
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:** nothing that matters",
            "**Can go wrong:** nothing — see `config.languages` and `post-card.blade`"))
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_an_actor_nobody_acts_for(self):
        self.write("actors.md", ACTORS + "\n### A ghost\n`key: ghost`\n\n"
                                         "**How they appear:** never\n**What they can do:** nothing\n")
        _code, output = self.run_check()
        self.assertIn("no action belongs to this actor", output)

    def test_a_slot_with_no_verdict(self):
        (self.root / ".agent-kit" / "project.yml").write_text("knowledge:\n  actors: filled\n",
                                                              encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("no verdict", output)

    def test_an_open_question_is_reported(self):
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST.replace("scenarios: filled", "scenarios: open_question — no one has walked them"),
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("scenarios — open question", output)

    # ---- the hash both sides have to agree on --------------------------------------------------

    def test_a_source_is_clean_at_the_hash_this_program_prints(self):
        """Asked of the function every writer of a hash goes through — `--record` and the check
        itself. It used to go through a `--hash` flag that nothing but this test ever called."""
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        idea = (self.root / "idea.md").read_text(encoding="utf-8")
        recorded = check.digest(check.section_of(idea, "Idea"))
        self.write("product.md", f"# Product\n\n`source: idea.md#Idea @{recorded}`\n")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_a_source_that_moved_on_is_reported(self):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        self.write("product.md", "# Product\n\n`source: idea.md#Idea @deadbeef`\n")
        _code, output = self.run_check()
        self.assertIn("changed", output)

    def test_a_source_pointing_at_nothing(self):
        self.write("product.md", "# Product\n\n`source: gone.md#Idea @deadbeef`\n")
        _code, output = self.run_check()
        self.assertIn("does not exist", output)

    def test_a_source_written_wrong_is_seen_wrong_and_not_missed(self):
        """Three of the four ways this line gets written matched nothing at all, so an entry that
        names its source read exactly like one that names none — for ever, and `--record` never
        filled it in either. The format whose whole job is to notice drift was itself invisible."""
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        for written in ("`source: idea.md#Idea`", "`source: idea.md#Idea @`",
                        "`source: idea.md#Idea @HEAD`"):
            self.write("product.md", f"# Product\n\n{written}\n")
            code, output = self.run_check()
            self.assertEqual(code, 1, f"{written} passed in silence")
            self.assertIn("is not a source line this program can read", output)

    def test_a_source_shown_inside_a_fence_is_not_a_source(self):
        """A fenced block is where a document shows the form rather than uses it. The first file
        this rule met was the one that teaches `source:` to the owner, and it called the
        specification a defect — with an exit code, so every command of the kit stopped."""
        self.write("product.md",
                   "# Product\n\n```markdown\n`source: path#heading @hash`\n```\n")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertNotIn("is not a source line", output)

    def test_a_source_pointing_outside_the_repository_is_said_and_not_judged(self):
        """A live project answered the first draft of this rule the hour it was written: a URL in
        `source:` is where a description came from, said deliberately. Nothing here can fetch a
        page, and a rule demanding a local file would tell a project to stop recording provenance."""
        self.write("product.md",
                   "# Product\n\n`source: https://example.org/corpus`\n")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertIn("point outside this repository", output)
        self.assertNotIn("is not a source line", output)

    def test_a_source_written_right_is_not_named_twice(self):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        self.write("product.md", "# Product\n\n`source: idea.md#Idea @deadbeef`\n")
        _code, output = self.run_check()
        self.assertNotIn("is not a source line", output)

    def test_whitespace_at_the_end_of_a_line_does_not_move_the_hash(self):
        self.assertEqual(check.digest("a\nb\n"), check.digest("a   \nb\t\n"))

    # ---- notes -------------------------------------------------------------------------------

    def test_an_open_assumption_is_named_by_the_entry_it_stands_under(self):
        """A run took the decision and every later run in that entry follows it, so what a command
        needs is which entries carry one — it only settles the blocks where it is about to build.
        One `epic` left seventy-four, and printing each of them before every command buries the
        findings that are real."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Decisions taken without the owner (1) in 1 entry", output)
        self.assertIn("guest.browse_feed", output)
        self.assertNotIn("beside the post", output, "the count and the entry, not every line")

    def test_a_stale_block_is_a_statement_and_not_a_finding(self):
        """The block sits under the entry it corrects, so no run is misled while it stands. Counting
        it as a defect made every command after a batch report the knowledge as broken, and every
        `next` recommend the same command."""
        self.write("actions.md", ACTIONS + "\n> **[stale 2026-08-05 · claude/x]** Says the driver "
                                           "is `log`; mail goes out over SMTP now.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Prose a feature has already outdated (1)", output)
        self.assertIn("SMTP", output)
        self.assertNotIn("Open notes", output)

    def test_an_assumption_stays_a_finding(self):
        """It is a question nobody has answered, which is not the same thing at all."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-05 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, _output = self.run_check()
        self.assertEqual(code, 1)

    def test_an_accepted_block_is_a_statement_and_not_a_finding(self):
        """The owner already said yes, so nothing is outstanding but an interview. Counting it as a
        defect would make every command red between accepting an idea and writing it up."""
        self.write("actions.md", ACTIONS + "\n> **[accepted 2026-08-09 · advise/product]** Импорт "
                                           "каталога одним файлом. Владелец: да, в границы MVP.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Accepted and not yet written up (1)", output)
        self.assertIn("каталога", output)
        self.assertNotIn("Open notes", output)

    def test_an_accepted_block_is_listed_apart_from_a_stale_one(self):
        """Two statements with different closers: one is rewritten prose, the other an interview.
        Merging their sections would send the owner to the wrong command."""
        self.write("actions.md", ACTIONS
                   + "\n> **[stale 2026-08-05 · claude/x]** Says the driver is `log`; SMTP now.\n"
                   + "\n> **[accepted 2026-08-09 · advise/code]** Статусы вынести в перечисление.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Prose a feature has already outdated (1)", output)
        self.assertIn("Accepted and not yet written up (1)", output)

    # ---- the shape of a run file's records ------------------------------------------------------

    def test_prose_in_assumptions_is_named_before_the_run_is_done(self):
        """It used to be judged only at `step: done`, where there is nothing left to do but report
        it — and it drifted twice in one night, while `tasks`, tested before every handoff, held.
        A session hearing it at its first handoff fixes it in a minute."""
        run = self.root / ".agent-kit" / "runs" / "r"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({
            "slug": "r", "command": "ship", "step": "build",
            "assumptions": ["взято: хранить рядом с постом"]}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([str(self.root), "--offline", "--run", str(run)])
        self.assertEqual(code, 1)
        self.assertIn("`assumptions` is written as sentences", out.getvalue())

    def test_an_empty_field_of_records_passes_at_any_step(self):
        """Shape is safe to test early only because absence is not a failure — a run mid-flight has
        not written its assumptions yet, and saying so would fire on every healthy run."""
        run = self.root / ".agent-kit" / "runs" / "r"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({
            "slug": "r", "command": "ship", "step": "build", "assumptions": [], "manual": []}),
            encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([str(self.root), "--offline", "--run", str(run)])
        self.assertEqual(code, 0, out.getvalue())

    # ---- the blocks under the entries a command names --------------------------------------------

    def test_entries_prints_the_blocks_under_the_entry_it_names(self):
        """The summary gives names only, and a gate that has to choose from names chose wrong: it
        read "the entries you are about to build" as the ones with no code yet, and left the built
        entries its scope was about to change unopened. Naming them gets the text itself."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check("--entries", "guest.browse_feed")
        self.assertEqual(code, 1)
        self.assertIn("Open blocks under the 1 entry this command named", output)
        self.assertIn("beside the post", output)

    def test_entries_prints_the_whole_block_and_not_its_first_line(self):
        """The summary keeps 90 characters, which tells two blocks apart and answers neither: what
        was taken, and at what cost, is further down the quote. A block runs until the quoting
        stops."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored, and the entry is silent on how long "
                                           "any of it is kept by anyone at all.\n"
                                           "> Took: beside the post, and deleted with it.\n"
                                           "\nOrdinary prose that is not part of the block.\n")
        _code, output = self.run_check("--entries", "guest.browse_feed")
        self.assertIn("Took: beside the post, and deleted with it.", output)
        self.assertNotIn("Ordinary prose", output)

    def test_entries_says_an_entry_it_named_has_nothing(self):
        """Silence per entry has to be a statement. A section that listed only the entries with
        blocks would leave the caller unable to tell "clear" from "not looked at"."""
        self.write("actions.md", ACTIONS)
        code, output = self.run_check("--entries", "guest.browse_feed")
        self.assertEqual(code, 0)
        self.assertIn("guest.browse_feed: none", output)

    def test_entries_names_a_key_that_matches_no_entry(self):
        """A filter that quietly matches nothing reads exactly like an entry with nothing to
        answer, and the keys come from prose — where a run derives them by hand."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        _code, output = self.run_check("--entries", "guest.browse_feed", "guest.typo")
        self.assertIn("Not an entry in this project's knowledge (1): guest.typo", output)

    def test_entries_answers_even_when_the_report_is_otherwise_clean(self):
        """A `[stale …]` leaves the report clean and returns 0. The one call a gate makes must not
        go silent on the entries it named because nothing else had anything to say."""
        self.write("actions.md", ACTIONS + "\n> **[stale 2026-08-05 · claude/x]** Says the driver "
                                           "is `log`; mail goes out over SMTP now.\n")
        code, output = self.run_check("--entries", "guest.browse_feed")
        self.assertEqual(code, 0)
        self.assertIn("Open blocks under the 1 entry this command named", output)
        self.assertIn("SMTP", output)

    def test_a_decision_under_a_built_entry_is_counted_as_one_nothing_will_reach(self):
        """The kit's answer to an open block is that the next run building there settles it in
        passing. Under a `built` entry with nothing planned in it, that run never comes — 47 of 58
        stood in exactly that position on a measured project, and no count anywhere said so."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("of those, 1 in 1 entries already `built`", output)

    def test_a_decision_under_an_entry_still_to_be_built_is_not_counted_as_stuck(self):
        """A run is coming there, and it settles the block with the owner present. Counting these
        would make the number grow after every batch and stop meaning anything."""
        planned = ACTIONS.replace("`state: built`", "`state: planned`")
        self.write("actions.md", planned + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Decisions taken without the owner (1)", output)
        self.assertNotIn("already `built`", output)

    # ---- promises the product does not keep ----------------------------------------------------

    MARKED = ("// agent-kit:unmet guest.browse_feed\n"
              "it('the feed is newest first')->todo();\n")

    def suite(self, body, form="->todo()", name="tests/FeedTest.php"):
        """A real git repository, because `git grep` is the path that runs in a real project."""
        manifest = MANIFEST + (f"tests:\n  unmet: {form}\n" if form else "")
        (self.root / ".agent-kit" / "project.yml").write_text(manifest, encoding="utf-8")
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "-A")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=False)

    def test_a_marked_test_is_listed_with_its_entry_even_when_everything_else_is_clean(self):
        self.suite(self.MARKED)
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a promise on record is not a defect in the check
        self.assertIn("Promises the product does not keep (1)", output)
        self.assertIn("tests/FeedTest.php:1 guest.browse_feed", output)
        self.assertIn("sprint with no theme", output)

    def test_a_file_named_in_the_project_language_is_read_like_any_other(self):
        self.suite(self.MARKED, name="tests/Лента.php")   # git ls-files would quote this away
        _code, output = self.run_check()
        self.assertIn("tests/Лента.php:1 guest.browse_feed", output)

    def test_the_mark_quoted_in_a_document_is_not_a_promise(self):
        self.suite(self.MARKED)
        (self.root / "docs" / "audits").mkdir(parents=True)
        (self.root / "docs" / "audits" / "tests.md").write_text(
            "- [ ] `guest.browse_feed` — see agent-kit:unmet guest.browse_feed in the suite\n",
            encoding="utf-8")
        self.git("add", "-A")
        _code, output = self.run_check()
        self.assertIn("Promises the product does not keep (1)", output)

    def test_a_mark_naming_an_entry_that_does_not_exist(self):
        self.suite("// agent-kit:unmet guest.gone\nit('x')->todo();\n")
        _code, output = self.run_check()
        self.assertIn("guest.gone — no such entry", output)

    def test_an_entry_key_without_a_dot_is_an_entry_too(self):
        self.suite("# agent-kit:unmet guest\ndef test_x(): ...\n")
        _code, output = self.run_check()
        self.assertIn("guest", output)
        self.assertNotIn("no such entry", output)

    def test_a_mark_without_an_entry_is_still_listed(self):
        self.suite("# agent-kit:unmet\ndef test_newest_first(): ...\n")
        _code, output = self.run_check()
        self.assertIn("no entry named", output)

    def test_several_suites_are_a_map_and_do_not_crash_the_check(self):
        self.suite(self.MARKED, form='\n    php: "->todo()"\n    js: test.failing')
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertIn("tests/FeedTest.php:1 guest.browse_feed", output)

    def test_a_suite_without_the_mark_says_nothing(self):
        self.suite("it('the feed is newest first');\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_mark_with_no_form_recorded_is_said_without_failing_the_check(self):
        self.suite(self.MARKED, form="")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a run must not stop over a missing manifest key
        self.assertIn("no tests.unmet", output)

    def test_a_project_with_no_marks_is_never_nagged_about_the_form(self):
        self.suite("it('the feed is newest first');\n", form="")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_the_unmet_list_is_never_cut(self):
        # ship is told to read the marked test for the entry it is about to touch, so a list cut
        # to a glance can hide exactly the one that run needed.
        body = "".join(f"// agent-kit:unmet guest.browse_feed\nit('{i}')->todo();\n" for i in range(15))
        self.suite(body)
        _code, output = self.run_check()
        self.assertIn("Promises the product does not keep (15)", output)
        self.assertEqual(output.count("guest.browse_feed"), 15)

    def with_merged_pr(self, *args, line="`state: building (pr: 7)`",
                       listing='[{"number": 7, "state": "MERGED"}]', view='{"state":"MERGED"}',
                       extra=""):
        """The check run against a `gh` that says the pull request has merged.

        `listing` is what `gh pr list` answers and `view` what `gh pr view` answers — `None` for a
        call that fails. Everything the fake is asked is appended to `self.asked`, because how many
        times it is asked is itself a rule here.
        """
        self.write("actions.md", ACTIONS.replace("`state: built`", line) + extra)
        fake = self.root / "bin"
        fake.mkdir(exist_ok=True)
        self.asked = fake / "asked.txt"
        answer = "exit 1" if view is None else f"printf '%s\\n' '{view}'"
        (fake / "gh").write_text(
            "#!/bin/sh\n"
            f'echo "$@" >> {self.asked}\n'
            'case "$2" in\n'
            f"  list) printf '%s\\n' '{listing}' ;;\n"
            f"  view) {answer} ;;\n"
            "esac\n", encoding="utf-8")
        (fake / "gh").chmod(0o755)
        was = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}:{was}"
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = check.main([str(self.root), *args])
        finally:
            os.environ["PATH"] = was
        return code, without_shape(out.getvalue())

    def test_a_merged_pull_request_moves_the_state_without_killing_the_run(self):
        """The crash this covers took every command's preflight down the day a feature landed."""
        code, output = self.with_merged_pr("--sync")
        self.assertEqual(code, 0, output)
        self.assertIn("building (pr: 7) → built", output)
        self.assertIn("state: built",
                      (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8"))

    def test_a_state_line_with_other_spacing_is_moved_rather_than_announced(self):
        """The literal replace this replaced carried one space around the `·` and one after `pr:`,
        while the parser reads any spacing at all. A line written `(pr:  7)` was found by every
        other check, matched nothing here, and the report announced a move that never happened."""
        code, output = self.with_merged_pr("--sync", line="`state:  building (pr:  7)`")
        self.assertEqual(code, 0, output)
        self.assertIn("→ built", output)
        # Whatever spacing the line had, it keeps: the substitution is on the match.
        written = (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8")
        self.assertIn("built`", written)
        self.assertNotIn("building", written)

    def test_the_check_writes_nothing_unless_it_is_asked_to(self):
        """Every command runs this before it starts; only `blueprint --check` may leave a change."""
        code, output = self.with_merged_pr()
        self.assertEqual(code, 0, output)
        self.assertNotIn("→ built", output)
        self.assertIn("state: building (pr: 7)",
                      (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8"))

    def test_a_line_behind_its_merged_pull_request_is_said_out_loud(self):
        """Writing is asked for; noticing is not. A merged feature stuck at `building` was invisible
        to every command for one release, which is how it reached a live project."""
        _code, output = self.with_merged_pr()
        self.assertIn("pull request 7 has merged", output)
        self.assertIn("guest.browse_feed", output)

    def test_the_pull_requests_are_asked_about_in_one_call(self):
        """It was one `gh pr view` per entry, before every command. A project with 21 entries in
        flight — a real number — paid 21 network calls for every session of a night."""
        second = ("\n### Guest opens an item\n`key: guest.open_item` · `state: building (pr: 8)`\n\n"
                  "**Who:** guest\n**What happens:** the item is shown\n"
                  "**Can go wrong:** nothing that matters\n")
        _code, output = self.with_merged_pr(
            "--sync", extra=second,
            listing='[{"number": 7, "state": "MERGED"}, {"number": 8, "state": "CLOSED"}]')
        self.assertIn("building (pr: 7) → built", output)
        self.assertIn("building (pr: 8) → planned", output)
        asked = self.asked.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(asked), 1, asked)
        self.assertTrue(asked[0].startswith("pr list"), asked[0])

    def test_a_number_the_listing_does_not_carry_is_asked_about_directly(self):
        """The listing is capped, so a repository with more pull requests than the cap says nothing
        about the oldest of them. A state line moved on that silence would be moved on a guess."""
        _code, output = self.with_merged_pr("--sync", listing="[]")
        self.assertIn("building (pr: 7) → built", output)
        asked = self.asked.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(asked), 2, asked)
        self.assertTrue(asked[1].startswith("pr view 7"), asked[1])

    def test_a_listing_nothing_can_parse_falls_back_rather_than_believing_it(self):
        """An empty listing and one that came back as something else are different answers, and
        reading the second as "this repository has no pull requests" would close every entry."""
        _code, output = self.with_merged_pr("--sync", listing="not json at all")
        self.assertIn("building (pr: 7) → built", output)

    def test_a_pull_request_neither_call_can_read_is_named(self):
        """The listing does not carry it and asking directly fails: nothing here knows what that
        pull request did, and that is said rather than left as `building` in silence."""
        _code, output = self.with_merged_pr(listing="[]", view=None)
        self.assertIn("pull request 7 unreadable", output)

    def test_offline_asks_gh_nothing_at_all(self):
        """Silence was all this asserted, and silence is what a call whose answer is thrown away
        also produces — the name of the test was checked by nothing until the fake kept a log."""
        _code, output = self.with_merged_pr("--offline")
        self.assertEqual(output, "")
        self.assertFalse(self.asked.exists(), "`--offline` reached the network")

    # ---- the debt ledger -----------------------------------------------------------------------

    def test_open_debt_is_listed_without_failing_the_check(self):
        (self.root / "docs" / "technical_debt.md").write_text(
            "# Долг\n\n"
            "- [ ] Закрепить инвариант «аккаунт всегда с паролем» — на нём держится правка · PR #21\n"
            "- [ ] Дописать прозу про передачу аккаунта · PR #21\n",
            encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a project's own memory is not a defect
        self.assertIn("Debt (2)", output)
        self.assertIn("docs/technical_debt.md:3", output)

    def test_a_project_with_no_ledger_says_nothing_about_debt(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertNotIn("Debt", output)

    def test_prose_around_the_items_is_not_counted(self):
        (self.root / "docs" / "technical_debt.md").write_text(
            "# Долг\n\nПишут прогоны, читают команды. Формат:\n\n"
            "```markdown\n- [ ] <что сделать> — <почему> · <прогон>\n```\n\n"
            "- [ ] Один настоящий пункт · PR #21\n",
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("Debt (1)", output)          # the example inside the fence is indented prose

    # ---- the state of the work -----------------------------------------------------------------

    def repo_with_work(self):
        (self.root / "docs" / "audits").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "audits" / "tests.md").write_text(
            "# Тесты — 2026-08-04\n\n- [ ] один пункт\n- [ ] второй\n", encoding="utf-8")
        runs = self.root / ".agent-kit" / "runs" / "2026-08-05-feed"
        runs.mkdir(parents=True)
        (runs / "run.json").write_text(json.dumps({
            "slug": "2026-08-05-feed", "command": "ship", "step": "build",
            "branch": "claude/feed", "waiting_on": None, "blockers": []}), encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        self.git("branch", "claude/feed")

    def test_state_names_an_abandoned_run_and_the_audits(self):
        self.repo_with_work()
        _code, output = self.run_check("--state")
        self.assertIn("run 2026-08-05-feed left at step=build", output)
        self.assertIn("tests 2026-08-04 (2 open)", output)

    def test_a_finished_run_is_not_reported_as_left_behind(self):
        self.repo_with_work()
        path = self.root / ".agent-kit" / "runs" / "2026-08-05-feed" / "run.json"
        path.write_text(json.dumps({"slug": "2026-08-05-feed", "step": "done"}), encoding="utf-8")
        _code, output = self.run_check("--state")
        self.assertNotIn("left at step", output)

    def test_a_project_with_no_audits_says_so_rather_than_staying_silent(self):
        self.suite("it('x');\n")                       # suite() makes it a repository
        _code, output = self.run_check("--state")
        self.assertIn("audits: none has ever run", output)

    def test_state_survives_a_directory_that_is_not_a_repository(self):
        _code, output = self.run_check("--state")
        self.assertIn("no git repository here", output)      # docs still read

    # ---- hashes this program owns --------------------------------------------------------------

    def sourced_project(self, recorded):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        self.write("product.md", f"# Product\n\n`source: idea.md#Idea @{recorded}`\n")

    def test_a_hash_from_before_the_program_is_named_as_such_not_as_a_change(self):
        self.sourced_project("a3f1c9d")            # seven characters: nobody could have computed it
        _code, output = self.run_check()
        self.assertIn("predate this program", output)
        self.assertNotIn("→", output)              # not reported as a value that moved

    def test_record_writes_the_hashes_and_says_what_it_wrote(self):
        self.sourced_project("a3f1c9d")
        _code, output = self.run_check("--record")
        self.assertIn("idea.md#Idea", output)
        code, after = self.run_check()
        self.assertEqual(code, 0, after)            # and the check goes quiet
        self.assertEqual(after, "")

    def test_record_is_idempotent(self):
        self.sourced_project("a3f1c9d")
        self.run_check("--record")
        _code, output = self.run_check("--record")
        self.assertIn("already current", output)

    def test_record_keeps_the_spacing_of_the_line_it_rewrites(self):
        self.sourced_project("a3f1c9d")
        self.run_check("--record")
        line = (self.root / "docs" / "knowledge" / "product.md").read_text(encoding="utf-8")
        self.assertIn("#Idea @", line)              # the space before the @ survived

    # ---- scenarios and their end-to-end tests --------------------------------------------------

    def test_a_scenario_with_no_test_is_counted_as_uncovered(self):
        self.suite("it('x');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna accepts an offer\n\n**Who:** Anna\n")
        _code, output = self.run_check("--state")
        self.assertIn("1 described, 0 with an end-to-end test", output)
        self.assertIn("Anna accepts an offer", output)

    def test_a_test_claiming_the_scenario_by_name_counts(self):
        self.suite("// agent-kit:scenario Anna accepts an offer\nit('walks it');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna accepts an offer\n\n**Who:** Anna\n")
        self.git("add", "-A")
        _code, output = self.run_check("--state")
        self.assertIn("1 described, 1 with an end-to-end test", output)
        self.assertNotIn("uncovered", output)

    def test_a_mark_naming_a_scenario_that_no_longer_exists_is_said_out_loud(self):
        self.suite("// agent-kit:scenario Anna accepts an offer\nit('walks it');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna declines an offer\n\n**Who:** Anna\n")
        self.git("add", "-A")
        _code, output = self.run_check("--state")
        self.assertIn("no scenario by that heading exists", output)

    # ---- dependency manifests nobody recorded ---------------------------------------------------

    def test_a_manifest_the_project_does_not_record(self):
        self.suite("it('x');\n")
        (self.root / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
        self.git("add", "-A")
        _code, output = self.run_check()
        self.assertIn("package.json is a dependency manifest that project.yml does not record",
                      output)

    def test_a_recorded_manifest_is_not_reported_twice(self):
        self.suite("it('x');\n")
        (self.root / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
        current = check.digest('{"name": "x"}\n')
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST + f"checks:\n  deps:\n    package.json: {current}\n", encoding="utf-8")
        self.git("add", "-A")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "")

    # ---- a project with no blueprint at all ----------------------------------------------------

    def test_a_project_without_knowledge_is_not_a_failure(self):
        shutil.rmtree(self.root / "docs" / "knowledge")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    # ---- the gate of an epic ---------------------------------------------------------------------
    #
    # A sprint with a thin blueprint still delivers five features; an epic with one has no stopping
    # condition. These three are what it refuses to start without.

    def ready_for_mvp(self, product=None, scenarios=None, commands=True):
        self.write("product.md", product if product is not None else
                   "# Product\n\n<!-- agent-kit:mvp-bounds -->\n## MVP bounds\n\n"
                   "**In:** sign-in, the composer\n\n**Out:** comments, search\n")
        self.write("scenarios.md", scenarios if scenarios is not None else
                   "# Scenarios\n\n### Anna publishes a story\n\n**Who:** Anna\n")
        if commands:
            (self.root / ".agent-kit" / "project.yml").write_text(
                MANIFEST + "commands:\n  test: make test\n  run: make up\n", encoding="utf-8")
            # A declared command is now judged on whether it starts anything, and this fixture is a
            # project that may start an MVP — so it owns the makefile it says it runs.
            (self.root / "Makefile").write_text("test:\n\techo hi\nup:\n\techo up\n",
                                                encoding="utf-8")
        return self.run_check("--epic")

    def test_a_project_that_may_start_an_mvp(self):
        code, output = self.ready_for_mvp()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_bounds_written_in_another_language_are_still_bounds(self):
        """The bounds are the owner's prose, in the project's own language — the heading is too.

        A Russian heading used to be hard-coded in the program for this, which was the one place a
        project's language reached the payload, and it bought nothing: `Границы MVP` carries the
        letters MVP and the fallback already matched it. The marker is what makes a heading with no
        Latin MVP in it at all readable — and that is the case the hard-coded string never covered.
        """
        code, output = self.ready_for_mvp(
            product="# Продукт\n\n<!-- agent-kit:mvp-bounds -->\n## Что входит в первую версию\n\n"
                    "**Входит:** вход, композер\n\n**Не входит:** комментарии, поиск\n")
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "", "a marked section is read without a word")

    def test_bounds_found_by_their_heading_are_read_in_silence(self):
        """Every project written before the marker existed, and the gate is fatal or silent — its
        own file promises that. A nudge printed here reads as a refusal to the session standing at
        the gate, and it would print on every project at every gate for ever."""
        code, output = self.ready_for_mvp(
            product="# Product\n\n## MVP bounds\n\n**In:** sign-in\n\n**Out:** search\n")
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "")

    def test_a_heading_no_program_can_guess_is_a_gap_and_not_a_defect(self):
        """Without the marker and without the letters MVP, nothing can find the section — and the
        program says the marker is missing rather than claiming the bounds are."""
        code, output = self.ready_for_mvp(
            product="# Продукт\n\n## Что входит в первую версию\n\n**Входит:** вход\n\n"
                    "**Не входит:** поиск\n")
        self.assertEqual(code, 1)
        self.assertIn("agent-kit:mvp-bounds", output)

    def test_no_bounds_at_all(self):
        code, output = self.ready_for_mvp(product="# Product\n\n## What it is for\n\nStories.\n")
        self.assertEqual(code, 1)
        self.assertIn("no MVP bounds section", output)

    def test_bounds_with_only_one_side(self):
        code, output = self.ready_for_mvp(
            product="# Product\n\n## MVP bounds\n\n**In:** sign-in, the composer\n")
        self.assertEqual(code, 1)
        self.assertIn("not two lists", output)

    def test_no_scenarios_to_prove_the_end_against(self):
        code, output = self.ready_for_mvp(scenarios="# Scenarios\n\nNone yet.\n")
        self.assertEqual(code, 1)
        self.assertIn("no scenarios are described", output)

    def test_no_command_that_starts_the_application(self):
        code, output = self.ready_for_mvp(commands=False)
        self.assertEqual(code, 1)
        self.assertIn("commands.run", output)

    def test_a_command_that_is_declared_and_starts_nothing(self):
        """Declared and unable to start is the same fact as not declared, arriving later and
        costing more — mid-run, in a child, with the suite it was told to run unrunnable."""
        self.ready_for_mvp()
        (self.root / "Makefile").unlink()
        code, output = self.run_check("--epic")
        self.assertEqual(code, 1)
        self.assertIn("`commands.test: make test`", output)
        self.assertIn("no makefile", output)

    def test_a_declared_command_that_starts_nothing_is_named_before_every_command(self):
        """Not only at the gate: the gate happens once and every other command meets this too."""
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST + "commands:\n  test: definitely-not-a-tool-here\n", encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("commands.test", output)
        self.assertIn("not on the PATH", output)

    def test_a_command_that_starts_something_says_nothing(self):
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST + "commands:\n  test: python3 -m pytest\n  lint:\n", encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "")

    # ---- what a run may not close with ---------------------------------------------------------
    #
    # These are the two rules that used to hold only if the run remembered them at the end of its
    # longest step. Each is shown firing, and shown silent on the run that did the thing right.

    def close(self, **fields):
        """A run file at `done` with everything filled in, minus whatever the test breaks."""
        state = {"slug": "x", "command": "ship", "step": "done", "suite": "made 41 green, lint ok",
                 "proved_at": "c0ffee1",
                 "review": {"verdict": "ok", "findings": [], "security": None}}
        state.update(fields)
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps(state), encoding="utf-8")
        return self.run_check("--run", str(directory))

    def test_a_finished_run_that_did_everything_says_nothing(self):
        code, output = self.close()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_major_finding_left_open_is_not_done(self):
        code, output = self.close(review={"findings": [
            {"severity": "major", "what": "the token is logged", "closed": False}]})
        self.assertEqual(code, 1)
        self.assertIn("a major review finding is open", output)
        self.assertIn("the token is logged", output)

    def test_a_finding_that_was_closed_is_not_reported(self):
        code, output = self.close(review={"findings": [
            {"severity": "critical", "what": "x", "closed": True},
            {"severity": "minor", "what": "y", "closed": False}]})
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_run_that_says_nothing_about_its_suite(self):
        code, output = self.close(suite=None)
        self.assertEqual(code, 1)
        self.assertIn("`suite` is empty", output)

    def test_a_finding_written_as_a_sentence_is_not_a_finding(self):
        """Five runs of one night wrote `"major — …, closed by …"` instead of a record, so the rule
        about closing with an open critical one was never once applied — the check skipped what it
        could not read, silently."""
        code, output = self.close(review={"findings": [
            "major — assertMissing cannot fail. Closed by reordering the fixtures."]})
        self.assertEqual(code, 1)
        self.assertIn("written as a sentence", output)

    def test_a_record_field_filled_with_prose_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps(
            {"slug": "x", "step": "build", "tasks": ["write the test", "make it pass"]}),
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("fill a field of records with sentences", output)
        self.assertIn("tasks (1)", output)

    def test_records_written_as_sentences_stop_a_run_closing(self):
        for field in ("tasks", "assumptions"):
            code, output = self.close(**{field: ["did the thing", "did the other"]})
            self.assertEqual(code, 1, field)
            self.assertIn(f"`{field}` is written as sentences", output)

    def test_a_run_still_working_is_not_judged(self):
        code, output = self.close(step="build", suite=None, review={"findings": [
            {"severity": "critical", "what": "x", "closed": False}]})
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_blocked_run_is_already_saying_so(self):
        code, output = self.close(step="blocked", suite=None)
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    # ---- the handoff, the other moment a run file has to stand on its own ----------------------

    def handover(self, **fields):
        state = {"slug": "x", "command": "ship", "step": "build", "suite": None,
                 "approach": "the endpoint, then the screen",
                 "tasks": [{"id": 1, "what": "the endpoint", "done": True, "commit": "9c1f0aa"}],
                 "handoff": "stopped after task 1; the queue seam deadlocks under sqlite"}
        state.update(fields)
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps(state), encoding="utf-8")
        return self.run_check("--run", str(directory))

    def test_a_handoff_that_stands_on_its_own_says_nothing(self):
        code, output = self.handover()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_task_closed_with_no_commit_is_a_boundary_nobody_can_find(self):
        """The driver cuts a long run at a task boundary, so a closed task with no SHA leaves both
        the session that continues it and the reviewer to hunt that work in the whole diff."""
        code, output = self.handover(
            tasks=[{"id": 1, "what": "the endpoint", "done": True},
                   {"id": 2, "what": "the screen", "done": False}])
        self.assertEqual(code, 1)
        self.assertIn("name no `commit`", output)
        self.assertIn("task(s) 1", output)          # and never the one still open

    def test_a_task_still_open_is_never_asked_for_a_commit(self):
        code, output = self.handover(
            tasks=[{"id": 1, "what": "the endpoint", "done": False}])
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "")

    def test_a_note_that_outgrew_the_field_is_named(self):
        code, output = self.handover(handoff="x" * (check.HANDOFF_MAX + 1))
        self.assertEqual(code, 1)
        self.assertIn("against a ceiling", output)

    def test_a_handoff_with_no_approach_would_be_designed_twice(self):
        code, output = self.handover(approach="")
        self.assertEqual(code, 1)
        self.assertIn("design this feature a second time", output)

    def test_a_handoff_whose_tasks_are_prose_says_nothing_about_what_is_left(self):
        """The shape is judged for every run now, not only for one being handed over, so this is
        the general message rather than the handoff's own — the finding is what matters."""
        code, output = self.handover(tasks=["the endpoint", "the screen"])
        self.assertEqual(code, 1)
        self.assertIn("`tasks` is written as sentences", output)
        code, output = self.handover(tasks=[])
        self.assertEqual(code, 1)
        self.assertIn("which task the handoff stopped after", output)

    def test_no_note_means_no_handoff_to_judge(self):
        for note in (None, "", "  "):
            code, output = self.handover(handoff=note, approach="", tasks=[])
            self.assertEqual(code, 0, repr(note))
            self.assertEqual(output, "", repr(note))

    def test_the_template_itself_closes_nothing(self):
        """The shipped template carries a placeholder severity; it must not read as a finding."""
        template = json.loads(
            (ROOT / "plugins" / "agent-kit" / "templates" / "run.json").read_text(encoding="utf-8"))
        template["step"] = "done"
        template["suite"] = "green"
        template["proved_at"] = "c0ffee1"
        template["pr"] = 21
        self.assertEqual(check.run_defects(template), [])

    def test_a_run_that_owed_a_pull_request_and_has_no_number(self):
        state = {"deliver": "pr", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "tasks": [], "pr": None}
        self.assertTrue(any("`pr` is empty" in line for line in check.run_defects(state)))

    def test_a_run_that_hit_a_blocker_may_close_without_one(self):
        state = {"deliver": "pr", "step": "done", "suite": "green", "proved_at": "c0ffee1", "pr": None,
                 "blockers": ["the gateway has no sandbox key"]}
        self.assertFalse(any("`pr` is empty" in line for line in check.run_defects(state)))

    def test_a_feature_inside_a_batch_owes_no_pull_request(self):
        """`deliver` decides it, not `command`: a child pushes a branch, and a batch's own file
        carries no `deliver` at all — both fall outside this by construction."""
        child = {"deliver": "branch", "kind": "feature", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "pr": None}
        self.assertEqual(check.run_defects(child), [])
        batch = {"command": "sprint", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "pr": None}
        self.assertFalse(any("`pr` is empty" in line for line in check.run_defects(batch)))

    # ---- the one evidence that a test can fail ------------------------------------------------

    def mutate_declared(self, command="make mutate"):
        path = self.root / ".agent-kit" / "project.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"commands:\n  test: make test\n  mutate: {command}\n", encoding="utf-8")

    def test_a_project_that_can_prove_its_tests_and_a_run_that_did_not(self):
        self.mutate_declared()
        state = {"command": "ship", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "deliver": "branch"}
        defects = check.run_defects(state, self.root)
        self.assertTrue(any("`mutation` is empty" in line for line in defects))

    def test_a_run_that_says_why_it_could_not_is_answered(self):
        """Not the numbers — the field being answered. A tool that would not start is a result;
        silence is what must not read like a pass."""
        self.mutate_declared()
        for mutation in ({"killed": 12, "survived": 1},
                         {"why": "infection exits 127 here", "command": "vendor/bin/infection"}):
            state = {"command": "ship", "step": "done", "suite": "green",
                     "proved_at": "c0ffee1",
                     "deliver": "branch",
                     "mutation": mutation}
            self.assertEqual(check.run_defects(state, self.root), [], repr(mutation))

    def test_an_excuse_with_no_command_behind_it_is_the_cheap_path(self):
        """`why` on its own costs nothing to write and reads like a result. The command that was
        actually run is the smallest artefact not running the tool does not produce."""
        self.mutate_declared()
        state = {"command": "ship", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "deliver": "branch",
                 "mutation": {"why": "the tool would not start"}}
        self.assertTrue(any("`mutation` is empty" in line
                            for line in check.run_defects(state, self.root)))

    def test_the_templates_own_empty_mutation_object_is_not_an_answer(self):
        """What is on disk is the template's four nulls, not a missing key."""
        self.mutate_declared()
        template = json.loads(
            (ROOT / "plugins" / "agent-kit" / "templates" / "run.json").read_text(encoding="utf-8"))
        template.update({"step": "done", "suite": "green",
                         "proved_at": "c0ffee1",
                         "deliver": "branch", "pr": 21})
        self.assertTrue(any("`mutation` is empty" in line
                            for line in check.run_defects(template, self.root)))

    def test_a_child_that_is_not_a_ship_is_asked_for_neither(self):
        """The frame child and an audit between waves have no suite and no code to mutate. Asked
        anyway, every batch of three or more closes with two defects that are not defects.

        Its prompt is prose, so nothing in the file can tell it from a feature — which is said in
        one line rather than guessed at either way. `kind` is the way out, and the test below takes
        it. Until then the silence is the old one: manufacturing two defects per errand is the
        worse of the two mistakes."""
        self.mutate_declared()
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": None,
                 "prompt": "Read .../references/frame.md and follow it"}
        found = check.run_defects(state, self.root)
        self.assertEqual([line for line in found if "kind of run" not in line], [])

    def test_a_child_that_says_what_kind_it_is_is_asked_nothing_at_all(self):
        """One field, and the ambiguity is gone for every reader of this file."""
        self.mutate_declared()
        state = {"command": "ship", "kind": "errand", "step": "done", "deliver": "branch",
                 "suite": None, "prompt": "Read .../references/frame.md and follow it"}
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_a_feature_whose_prompt_was_written_out_is_still_a_feature(self):
        """The live defect. `templates/run.json` offers this very line as the default, and writing
        it out used to turn the run into an errand — no suite asked, no tree, no mutation."""
        self.mutate_declared()
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": None,
                 "prompt": "/agent-kit:ship --run .agent-kit/runs/2026-08-05-feed"}
        found = check.run_defects(state, self.root)
        self.assertTrue(any("`suite` is empty" in line for line in found), found)

    def test_a_manifest_that_cannot_be_read_does_not_take_the_driver_down(self):
        """`run_defects` runs after every child, all night, with no `try` above it."""
        path = self.root / ".agent-kit" / "project.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {"command": "ship", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "deliver": "branch"}
        path.write_bytes(b"commands:\n  mutate: \xff\xfe not utf-8\n")
        self.assertEqual(check.run_defects(state, self.root), [])
        path.write_text("commands: make all\n", encoding="utf-8")   # a scalar where a map is meant
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_a_project_with_no_such_command_is_not_asked_for_one(self):
        path = self.root / ".agent-kit" / "project.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("commands:\n  test: make test\n  mutate:\n", encoding="utf-8")
        state = {"command": "ship", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "deliver": "branch"}
        self.assertEqual(check.run_defects(state, self.root), [])

    # ---- what a pull request puts in front of a reader -----------------------------------------

    def body(self, text):
        path = self.root / "body.md"
        path.write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.pr_body_defects(path)
        return code, out.getvalue()

    def test_a_body_short_enough_to_decide_from(self):
        code, output = self.body("## What & why\n\nIt sends the letter now.\n")
        self.assertEqual(code, 0)
        self.assertIn("characters", output)

    def test_a_body_that_makes_the_reader_walk(self):
        code, output = self.body("# Run\n" + ("Prose nobody asked for. " * 600))
        self.assertEqual(code, 1)
        self.assertIn("stand uncollapsed", output)

    def test_what_is_folded_away_is_not_counted(self):
        """`<details>` is how a body is complete and short at once. Counting it would push a
        writer to delete the evidence rather than fold it."""
        code, _ = self.body("# Run\n\n<details><summary>Every file</summary>\n"
                            + ("Prose nobody asked for. " * 600) + "\n</details>\n")
        self.assertEqual(code, 0)

    def test_a_table_nobody_can_finish_reading(self):
        table = "| Decision | Why |\n|---|---|\n" + "".join(
            f"| decision {n} | because |\n" for n in range(28))
        code, output = self.body("# Run\n\n" + table)
        self.assertEqual(code, 1)
        self.assertIn("28 rows", output)

    def test_the_same_table_folded_is_an_answer(self):
        table = "| Decision | Why |\n|---|---|\n" + "".join(
            f"| decision {n} | because |\n" for n in range(28))
        code, _ = self.body("# Run\n\n<details><summary>28 assumptions</summary>\n\n"
                            + table + "\n</details>\n")
        self.assertEqual(code, 0)

    def test_a_brief_longer_than_the_owner_reads(self):
        """The rule has asked for 2 500 characters at the top since 2.15.0 and nothing counted them:
        the program measured the whole uncollapsed body against one generous number, so a body could
        pass with a wall of prose above its first heading."""
        code, output = self.body(("A paragraph about the work. " * 120) + "\n\n## Proven\n\nGreen.\n")
        self.assertEqual(code, 1)
        self.assertIn("the brief runs to", output)

    def test_the_brief_ends_at_the_first_section(self):
        """Everything above the first `##`, and the writer decides where that is — matching the
        section names would make this program answer differently per project, because they are
        written in the project's own language."""
        _code, output = self.body("Three answers.\n\n## Proven\n\n" + ("Evidence. " * 100))
        self.assertIn("16 of those in the brief", output)      # "Three answers.\n\n"

    def test_a_report_shaped_body_passes(self):
        """The shape the owner asked for: three answers, and the proof folded behind its count."""
        code, _ = self.body(
            "Two features: the letter goes out, and the profile drops the timezone.\n\n"
            "**What is needed from you.** Nothing.\n\n"
            "**What went wrong.** Nothing parked. One promise unkept: `user.set_window`.\n\n"
            "<details><summary>Proven — 1320 tests green on `4c5828d`, 13 mutants killed</summary>\n"
            + ("Evidence nobody has to read. " * 400) + "\n</details>\n")
        self.assertEqual(code, 0)

    def test_a_body_that_is_not_there(self):
        code = check.pr_body_defects(self.root / "nothing.md")
        self.assertEqual(code, 2)

    # ---- what starts a child that is not a ship ------------------------------------------------

    def test_a_prompt_that_briefs_instead_of_invoking(self):
        """Thirteen of sixteen children on one live run were started by two to five kilobytes of
        prose composed on the spot. What the child must know belongs in fields that outlive it."""
        state = {"command": "ship", "step": "queued", "prompt": "You are the second child of the "
                                                                "proving phase. " + "х" * 500}
        self.assertTrue(any("`prompt` is" in line for line in check.run_defects(state)))

    def test_a_prompt_that_is_a_command_and_a_directory(self):
        state = {"command": "ship", "step": "queued",
                 "prompt": "/agent-kit:audit tests --run .agent-kit/runs/2026-08-14-w2-03-tests"}
        self.assertEqual(check.run_defects(state), [])

    def test_a_prompt_pinned_to_the_version_that_wrote_it(self):
        """Three different versions of this kit in one night, so its children read rules three
        weeks apart — and nothing said so."""
        state = {"command": "ship", "step": "queued", "prompt":
                 "Read /home/dev/.claude/plugins/cache/agent-kit/agent-kit/2.9.0/skills/audit/"
                 "SKILL.md and follow it. Lens: tests."}
        defects = check.run_defects(state)
        self.assertTrue(any("pinned to a version" in line for line in defects))
        self.assertTrue(any("2.9.0" in line for line in defects))

    def test_a_short_path_is_still_a_briefing(self):
        """Under the ceiling and with no version in it, so the two other rules stay quiet. A
        prompt that names a file instead of a command is the thing all three exist against."""
        state = {"command": "ship", "step": "queued",
                 "prompt": "Read /home/dev/.claude/plugins/cache/agent-kit/skills/audit/SKILL.md "
                           "and follow it."}
        defects = check.run_defects(state)
        self.assertTrue(any("does not start with a command" in line for line in defects))

    def test_a_child_that_has_already_run_is_not_reported(self):
        """A batch written before this rule existed is what `--resume` carries on with. Judged at
        close, every errand in it would put a defect nobody can now fix into the pull request."""
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": None,
                 "prompt": "Read the old references/frame.md and follow it. " + "x" * 500}
        found = check.run_defects(state)
        self.assertEqual([line for line in found if "kind of run" not in line], [])

    # ---- what a green suite is bound to --------------------------------------------------------

    def test_a_suite_result_bound_to_no_tree_at_all(self):
        """Every other field is the run's own account of itself. This one is the only claim in the
        file that anybody else can check, and unbound it says nothing at all."""
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": "41 green"}
        self.assertTrue(any("`proved_at`" in line for line in check.run_defects(state)))

    def test_a_suite_result_that_names_its_tree_says_nothing(self):
        state = {"command": "ship", "step": "done", "deliver": "branch",
                 "suite": "41 green", "proved_at": "c0ffee1"}
        self.assertEqual(check.run_defects(state), [])

    def test_an_errand_is_not_asked_which_tree_it_proved(self):
        """A child carrying its own prompt has no suite of its own — asked anyway, every batch of
        three or more would close with a defect that is not one."""
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": None,
                 "prompt": "Read .../references/frame.md and follow it"}
        found = check.run_defects(state, self.root)
        self.assertEqual([line for line in found if "kind of run" not in line], [])

    def test_a_tree_that_is_not_in_this_repository(self):
        self.suite("it('x');\n")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                              capture_output=True, text=True).stdout.strip()
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": "41 green",
                 "proved_at": head}
        self.assertEqual(check.run_defects(state, self.root), [])
        state["proved_at"] = "0" * 40
        self.assertTrue(any("not a commit in this repository" in line
                            for line in check.run_defects(state, self.root)))

    def test_a_tree_that_exists_but_is_not_on_the_branch_being_delivered(self):
        """A commit that exists somewhere is not evidence about what is being handed over: a suite
        run on a branch that was then abandoned passes existence and says nothing."""
        self.suite("it('x');\n")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        self.git("checkout", "-q", "-b", "claude/elsewhere")
        (self.root / "other.txt").write_text("two\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "elsewhere")
        stray = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                               capture_output=True, text=True).stdout.strip()
        self.git("checkout", "-q", "-b", "claude/delivered", "HEAD~1")
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": "41 green",
                 "branch": "claude/delivered", "proved_at": stray}
        self.assertTrue(any("is not in claude/delivered" in line
                            for line in check.run_defects(state, self.root)))
        state["proved_at"] = subprocess.run(["git", "rev-parse", "claude/delivered"],
                                            cwd=self.root, capture_output=True,
                                            text=True).stdout.strip()
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_a_batch_is_not_asked_which_tree_it_proved(self):
        """Its `suite` is what the children reported, measured on trees it never stood on. Asked
        for one of its own it would have to invent one."""
        state = {"command": "sprint", "step": "done", "suite": "green", "pr": 21}
        self.assertFalse(any("`proved_at`" in line for line in check.run_defects(state)))

    def test_outside_a_repository_the_tree_is_not_judged(self):
        """A check that cannot reach its input says nothing rather than guessing: the field is
        still asked for, and whether it names a real commit is not askable here."""
        state = {"command": "ship", "step": "done", "deliver": "branch", "suite": "41 green",
                 "proved_at": "whatever-this-is"}
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_state_says_when_nothing_measures_whether_the_tests_can_fail(self):
        self.suite("it('x');\n", form=None)
        _code, output = self.run_check("--state")
        self.assertIn("nothing measures whether they can fail", output)

    def test_state_survives_a_commands_key_that_is_not_a_map(self):
        """`commands: make all` is a scalar where a map is meant, and it took `--state` down
        entirely — which is the gate of an epic, and what `next` and `accept` both run."""
        (self.root / ".agent-kit").mkdir(parents=True, exist_ok=True)
        (self.root / ".agent-kit" / "project.yml").write_text("commands: make all\n",
                                                              encoding="utf-8")
        code, output = self.run_check("--state")
        self.assertNotEqual(code, 2)
        self.assertIn("not a map this program can read", output)
        self.assertNotIn("declares no", output)

    def test_state_does_not_say_a_project_declared_nothing_when_there_is_no_project(self):
        """Two states that must not read alike: a project that answered and a file that is not
        there. Saying the second as the first is the failure this kit has shipped three times."""
        (self.root / ".agent-kit" / "project.yml").unlink()
        code, output = self.run_check("--state")
        self.assertNotEqual(code, 2)
        self.assertIn("no .agent-kit/project.yml here", output)

    def test_a_project_that_declared_the_command_is_not_told_about_it(self):
        (self.root / ".agent-kit").mkdir(parents=True, exist_ok=True)
        (self.root / ".agent-kit" / "project.yml").write_text(
            "commands:\n  test: make test\n  mutate: make mutate\n", encoding="utf-8")
        _code, output = self.run_check("--state")
        self.assertNotIn("nothing measures whether they can fail", output)

    def batch_record(self, slug, **fields):
        """A record in the shape the kit's own template declares, which is what a batch must leave."""
        record = {"slug": slug, "command": "sprint", "pr": 21, "branches": ["claude/b-01"],
                  "spent": {"hours": 6.2, "features": 4, "sessions": 9}}
        record.update(fields)
        runs = self.root / "docs" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        path = runs / f"{slug}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_a_batch_is_not_asked_to_prove_anything_itself(self):
        self.mutate_declared()
        self.batch_record("b")
        state = {"command": "sprint", "slug": "b", "step": "done", "suite": "green",
                 "proved_at": "c0ffee1",
                 "pr": 21}
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_a_batch_that_left_no_durable_record(self):
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        defects = check.run_defects(state, self.root)
        self.assertTrue(any("docs/runs/2026-08-05-offers.json" in line for line in defects))

    def test_a_batch_that_wrote_its_record_says_nothing(self):
        self.batch_record("2026-08-05-offers")
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        self.assertEqual(check.run_defects(state, self.root), [])

    # ---- the entries a run says it is about -----------------------------------------------------

    def building(self, entries):
        return {"command": "ship", "slug": "2026-08-05-feed", "step": "building",
                "entries": entries}

    def test_an_entry_key_no_entry_matches(self):
        """`--entries` has named such a key loudly since it existed; the run file carrying the very
        same key passed in silence, and the child met it alone at three in the morning."""
        defects = check.run_defects(self.building(["guest.browse_fed"]), self.root)
        self.assertTrue(any("guest.browse_fed" in line and "no entry" in line for line in defects),
                        defects)

    def test_the_closest_key_is_named_beside_it(self):
        defects = check.run_defects(self.building(["guest.browse_fed"]), self.root)
        self.assertTrue(any("guest.browse_feed" in line for line in defects), defects)

    def test_a_key_that_matches_says_nothing(self):
        self.assertEqual(check.run_defects(self.building(["guest.browse_feed"]), self.root), [])

    def test_a_project_with_no_knowledge_is_told_rather_than_passed(self):
        """Silence here would mean the same as a key that matches, and they are not the same."""
        empty = Path(tempfile.mkdtemp())
        try:
            defects = check.run_defects(self.building(["guest.browse_feed"]), empty)
            self.assertTrue(any("no docs/knowledge/" in line for line in defects), defects)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_without_a_project_nothing_is_guessed(self):
        self.assertEqual(check.run_defects(self.building(["whatever.at.all"])), [])

    # ---- and what that record may not be written as ---------------------------------------------

    def closing(self, slug="2026-08-05-offers"):
        return {"command": "sprint", "slug": slug, "step": "done", "suite": "green",
                "proved_at": "c0ffee1",
                "pr": 21}

    def test_a_record_that_parses_and_says_nothing_is_not_a_record(self):
        """Existence was all this ever asked for, and existence is what it got: on the one project
        that has run batches for real, eleven of them left one file in a shape nothing reads."""
        (self.root / "docs" / "runs").mkdir(parents=True)
        (self.root / "docs" / "runs" / "2026-08-05-offers.json").write_text("{}", encoding="utf-8")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("no `spent`" in line for line in defects))
        self.assertTrue(any("no `branches`" in line for line in defects))

    def test_spent_written_as_prose_is_named_because_a_gate_prices_from_it(self):
        self.batch_record("2026-08-05-offers", spent="about six hours, four features")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("`spent`" in line and "prose" in line for line in defects))

    def test_spent_missing_one_of_its_three_numbers(self):
        self.batch_record("2026-08-05-offers", spent={"hours": 6.2, "features": 4})
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("does not carry sessions as numbers" in line for line in defects))

    def test_a_batch_that_left_no_branches_writes_an_empty_list(self):
        """`[]` says somebody looked; leaving the field out says nobody did — the same distinction
        the run file already draws on `needs`."""
        self.batch_record("2026-08-05-offers", branches=[])
        self.assertEqual(check.run_defects(self.closing(), self.root), [])

    def test_a_parked_branch_the_record_does_not_otherwise_name(self):
        """`delivered_branches` walks `branches`, so a name only in `parked` protects nothing. The
        way it happens is a slug written where a branch name belongs — and those differ, which is
        the whole reason this field exists instead of `blocked` answering the question."""
        self.batch_record("2026-08-05-offers", branches=["claude/b-01"], parked=["b-02"])
        defects = check.batch_defects(json.loads(
            (self.root / "docs" / "runs" / "2026-08-05-offers.json").read_text(encoding="utf-8")))
        self.assertTrue(any("`branches` does not name" in line for line in defects), defects)

    def test_a_parked_branch_that_is_also_in_branches_is_the_shape_asked_for(self):
        self.batch_record("2026-08-05-offers", branches=["claude/b-01", "claude/b-02"],
                          parked=["claude/b-02"])
        defects = check.batch_defects(json.loads(
            (self.root / "docs" / "runs" / "2026-08-05-offers.json").read_text(encoding="utf-8")))
        self.assertEqual(defects, [])

    def test_branches_written_as_a_sentence_is_named(self):
        self.batch_record("2026-08-05-offers", branches="all four, merged")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("`branches`" in line and "not a list of names" in line
                            for line in defects))

    def test_every_count_is_judged_and_not_only_the_two_a_program_reads(self):
        """A field that may be prose is a field that will be — and `debt`, `review` and
        `per_feature` were passing clean while `spent` and `branches` were held to their shape."""
        self.batch_record("2026-08-05-offers", debt="closed 2, added 3",
                          review={"findings": 37, "open": "none"},
                          per_feature={"2026-08-05-offers-01": "one session"},
                          blocked="none")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("`debt`" in line and "prose" in line for line in defects))
        self.assertTrue(any("`review`" in line and "open" in line for line in defects))
        self.assertTrue(any("`per_feature`" in line for line in defects))
        self.assertTrue(any("`blocked`" in line and "not a list of names" in line
                            for line in defects))

    def test_a_pull_request_number_that_is_not_whole(self):
        """`delivered_branches` matches this against what gh returns, where 21.0 is not 21 — so a
        record that passed here would leave exactly the branches the field exists to retire."""
        self.batch_record("2026-08-05-offers", pr=21.0)
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("not a whole number" in line for line in defects))

    def test_a_count_written_as_a_sentence_is_named(self):
        self.batch_record("2026-08-05-offers", unmet="one, on the offer entry")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("`unmet`" in line and "is not a number" in line for line in defects))

    def test_a_record_nothing_can_parse_is_not_a_batch_that_left_one(self):
        runs = self.root / "docs" / "runs"
        runs.mkdir(parents=True)
        (runs / "2026-08-05-offers.json").write_text("slug: offers\n", encoding="utf-8")
        defects = check.run_defects(self.closing(), self.root)
        self.assertTrue(any("cannot be read as a record" in line for line in defects))

    def test_without_a_project_the_record_rule_is_skipped_rather_than_guessed(self):
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        self.assertEqual(check.run_defects(state), [])

    def test_a_knowledge_file_the_kit_has_no_template_for_is_named(self):
        """Three checks key off the template — fields, shape, verdict — and a file with none slips
        all three at once. The product template itself invites one for an API or a CLI."""
        self.write("endpoints.md", "# Endpoints\n\n### GET /feed\n`key: endpoint.feed`\n")
        _code, output = self.run_check(keep_shape=True)
        self.assertIn("endpoints.md has no template", output)

    def test_a_step_no_reader_knows_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"slug": "x", "step": "polishing"}),
                                            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("step 'polishing'", output)

    def test_the_steps_a_driver_writes_are_not_findings(self):
        directory = self.root / ".agent-kit" / "runs" / "batch"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"slug": "batch", "step": "building"}),
                                            encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        # The one thing a live run does print, and it is a statement about who is working here
        # rather than a finding about the knowledge: the exit code is untouched and nothing else
        # is said.
        self.assertIn("A run is in flight here (1)", output)
        self.assertNotIn("batch · ? · building\n\n", output)

    def test_a_run_nothing_is_building_says_nothing(self):
        """The statement has an end: a run that reached a terminal step is not somebody working
        here, and printing it would make the line noise every command learns to scroll past."""
        directory = self.root / ".agent-kit" / "runs" / "batch"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"slug": "batch", "step": "done"}),
                                            encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_run_directory_with_no_file(self):
        code, _output = self.run_check("--run", str(self.root / ".agent-kit" / "runs" / "gone"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()


class RunBranchCase(unittest.TestCase):
    """Where a run says its work is, and what it says it forked from.

    Both were held to being strings while somebody else read them: the batch record's `branches` is
    composed from one, and the driver chains the next child onto the other. Shape is judged at any
    step, existence only while the run is in flight — a queued child names a branch its sibling has
    not made yet, and a finished run's branch is deleted the moment its pull request merges.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        self.root.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (self.root / "a.txt").write_text("one\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "first")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=False)

    def defects(self, step="building", **fields):
        state = {"command": "ship", "slug": "2026-08-05-feed", "step": step, **fields}
        return check.run_defects(state, self.root)

    def test_a_branch_this_run_says_it_is_on_and_nothing_can_check_out(self):
        found = self.defects(branch="claude/2026-08-05-feed")
        self.assertTrue(any("does not exist here" in line for line in found), found)

    def test_a_branch_that_exists_says_nothing(self):
        self.git("branch", "claude/2026-08-05-feed")
        self.assertEqual(self.defects(branch="claude/2026-08-05-feed"), [])

    def test_a_queued_child_names_a_branch_nobody_has_made_yet(self):
        """Its sibling makes it, and the sibling has not run. Reporting this would be reporting the
        chain working as designed."""
        self.assertEqual(self.defects(step="queued", branch="claude/2026-08-05-feed",
                                      base="claude/2026-08-05-offers", prompt=""), [])

    def test_a_finished_runs_branch_is_allowed_to_be_gone(self):
        """It is deleted the moment its pull request merges, by `next`, on purpose. The other rules
        a finished run meets are not this rule's business, so only this one is asserted about."""
        found = self.defects(step="done", branch="claude/2026-08-05-feed")
        self.assertFalse([line for line in found if "does not exist here" in line], found)

    def test_a_branch_somebody_named_by_hand_and_deleted_is_not_called_a_slug(self):
        """Measured on two real run files carrying `mvp/learning-loop`: the first draft of this
        rule called every unresolvable name outside the kit's own prefixes a slug, and said so about
        a branch that was named by a person and removed after its merge."""
        found = self.defects(step="done", branch="mvp/learning-loop")
        self.assertEqual([line for line in found if "branch" in line.split("—")[0]], [], found)

    def test_a_slug_written_where_a_branch_name_belongs_is_named_at_any_step(self):
        """The mistake `parked` was invented against: the two differ, and a name nothing resolves
        retires nothing, ever."""
        found = self.defects(step="done", branch="2026-08-05-feed")
        self.assertTrue(any("slug written where a branch name belongs" in line for line in found),
                        found)

    def test_a_base_the_chain_cannot_reach(self):
        """The branch exists and the base does not, which is the case: a child chained onto a
        sibling that never got built. Written the other way round — the branch made *after* the
        question was asked — this tested a state where neither existed."""
        self.git("branch", "claude/2026-08-05-feed")
        found = self.defects(branch="claude/2026-08-05-feed", base="claude/2026-08-05-offers")
        self.assertTrue(any("`base` names" in line for line in found), found)
        self.assertFalse([line for line in found if "`branch` names" in line], found)

    def test_a_base_that_resolves_says_nothing(self):
        self.git("branch", "claude/2026-08-05-feed")
        self.assertEqual(self.defects(branch="claude/2026-08-05-feed", base="main"), [])

    def test_outside_a_repository_nothing_is_guessed(self):
        outside = Path(tempfile.mkdtemp())
        try:
            self.assertEqual(
                check.run_defects({"command": "ship", "slug": "x", "step": "building",
                                   "branch": "claude/x", "base": "main"}, outside), [])
        finally:
            shutil.rmtree(outside, ignore_errors=True)


class PlannedListsCase(unittest.TestCase):
    """Which of the owner's lists each planned entry is on.

    `planned: 7` was three questions wearing one number, and on a live project it produced the wrong
    recommendation: one entry inside the bounds, three deferred to a next version, three ruled out
    altogether. The labels are the owner's own prose in their own language, so the program counts and
    never matches a word of them.
    """

    PRODUCT = """# Продукт

## Границы MVP

**Внутри:**

- Вход и профиль: `screen.session` — правка шапки.

**Следующая версия — то, что владелец надиктовал.**

- Материал вместо выдумки: `scheduler.pick_material`, `user.set_model_key`.

**Снаружи:**

- Пересчёт уровня: `scheduler.recalculate_level`.
"""

    ACTIONS = """# Действия

fields: Кто

### Экран задания
`key: screen.session` · `state: planned`

**Кто:** `user`

### Подбор материала
`key: scheduler.pick_material` · `state: planned`

**Кто:** `user`

### Свой ключ
`key: user.set_model_key` · `state: planned`

**Кто:** `user`

### Пересчёт уровня
`key: scheduler.recalculate_level` · `state: planned`

**Кто:** `user`

### Нигде не названа
`key: user.orphan_plan` · `state: planned`

**Кто:** `user`
"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.knowledge = self.tmp / "docs" / "knowledge"
        self.knowledge.mkdir(parents=True)
        (self.knowledge / "product.md").write_text(self.PRODUCT, encoding="utf-8")
        (self.knowledge / "actions.md").write_text(self.ACTIONS, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def split(self):
        docs = [check.Doc(p) for p in sorted(self.knowledge.glob("*.md"))]
        return check.planned_by_list(docs)

    def test_each_list_keeps_its_own_name_and_its_keys(self):
        rows, _unplaced = self.split()
        self.assertEqual([label for label, _keys in rows],
                         ["Внутри", "Следующая версия — то, что владелец надиктовал.", "Снаружи"])
        self.assertEqual([keys for _label, keys in rows],
                         [["screen.session"],
                          # the order is the knowledge's, not the list's — a run reads them from
                          # `actions.md` and the labels are only where each one belongs
                          ["scheduler.pick_material", "user.set_model_key"],
                          ["scheduler.recalculate_level"]])

    def test_an_entry_on_no_list_is_named_rather_than_placed(self):
        _rows, unplaced = self.split()
        self.assertEqual(unplaced, ["user.orphan_plan"])

    def test_the_earlier_list_wins_a_key_named_twice(self):
        """An entry listed as inside and mentioned again while describing a later version is
        inside — the section reads top down and so does this."""
        text = (self.knowledge / "product.md").read_text(encoding="utf-8")
        (self.knowledge / "product.md").write_text(
            text.replace("`scheduler.pick_material`, ", "`scheduler.pick_material`, "
                         "`screen.session`, "), encoding="utf-8")
        rows, _unplaced = self.split()
        self.assertEqual(rows[0], ("Внутри", ["screen.session"]))
        self.assertNotIn("screen.session", rows[1][1])

    def test_no_bounds_section_places_nothing_and_says_so(self):
        """The gate is what reports a missing bounds section; this one may not pretend to place
        entries against a section that is not there."""
        (self.knowledge / "product.md").write_text("# Продукт\n\n## Для чего он\n\nУчить.\n",
                                                   encoding="utf-8")
        rows, unplaced = self.split()
        self.assertEqual(rows, [])
        self.assertEqual(unplaced, [])


class DriftCase(unittest.TestCase):
    """Records that moved on the default branch while a run was building against them.

    The case it was written for: the owner dictates into `blueprint` from a tree of their own while
    a batch runs, which is meant to be allowed. What must not happen is the two meeting silently —
    they usually edit different lines of the same file, so the feature lands against a sentence that
    no longer exists and no diff shows it.
    """

    ENTRY = ("# Actions\n\nfields: Who, What changes\n\n"
             "### The learner updates push settings\n"
             "`key: user.update_push_settings` · `state: {state}`\n\n"
             "**Who:** `user`\n**What changes:** {what}\n\n"
             "### The learner signs out\n`key: user.sign_out` · `state: built`\n\n"
             "**Who:** `user`\n**What changes:** the session ends\n")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "docs" / "knowledge").mkdir(parents=True)
        (self.root / ".agent-kit" / "runs" / "x").mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.knowledge(what="the schedule moves")
        self.commit("first")
        self.git("branch", "claude/x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=False)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def knowledge(self, what, state="built"):
        (self.root / "docs" / "knowledge" / "actions.md").write_text(
            self.ENTRY.format(what=what, state=state), encoding="utf-8")

    def moved(self, **fields):
        docs = [check.Doc(p) for p in sorted((self.root / "docs" / "knowledge").glob("*.md"))]
        state = {"command": "ship", "slug": "x", "branch": "claude/x",
                 "entries": ["user.update_push_settings"], **fields}
        return check.entry_drift(self.root, docs, state, self.root / ".agent-kit" / "runs" / "x")

    def test_an_entry_nobody_touched(self):
        self.assertEqual(self.moved(), [])

    def test_an_entry_rewritten_on_the_default_branch(self):
        self.knowledge(what="the schedule moves, and the timezone is refused")
        self.commit("blueprint")
        found = self.moved()
        self.assertEqual(len(found), 1, found)
        self.assertIn("user.update_push_settings — changed on", found[0])

    def test_the_state_line_the_programs_move_is_not_a_change(self):
        """It steps to `building (pr: n)` and to `built` on every feature that touches the entry,
        written by this kit's own programs. Counting it would report drift on every entry a batch
        delivered."""
        self.knowledge(what="the schedule moves", state="building (pr: 41)")
        self.commit("state line")
        self.assertEqual(self.moved(), [])

    def test_a_record_renamed_is_followed_by_its_key(self):
        """A heading is prose in the project's language and `blueprint` rewrites one whenever the
        owner renames a thing. Cutting by the heading would call every rename a change."""
        text = (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8")
        (self.root / "docs" / "knowledge" / "actions.md").write_text(
            text.replace("The learner updates push settings", "Push settings"), encoding="utf-8")
        self.commit("renamed")
        self.assertEqual(self.moved(), [])

    def test_an_entry_recorded_after_the_run_branched(self):
        self.moved()
        self.git("checkout", "-q", "claude/x")
        self.git("checkout", "-q", "main")
        found = self.moved(entries=["user.sign_out"])
        self.assertEqual(found, [])                # it was there before the branch too

    def test_a_run_that_names_no_entries(self):
        self.assertEqual(self.moved(entries=[]), [])

    def test_a_batch_asks_on_behalf_of_its_children(self):
        child = self.root / ".agent-kit" / "runs" / "x-01"
        child.mkdir(parents=True)
        (child / "run.json").write_text(json.dumps(
            {"slug": "x-01", "step": "done", "branch": "claude/x",
             "entries": ["user.update_push_settings"]}), encoding="utf-8")
        self.knowledge(what="the schedule moves, and the timezone is refused")
        self.commit("blueprint")
        found = self.moved(entries=[], branch=None, children=["x-01"])
        self.assertEqual(len(found), 1, found)

    def test_a_comparison_that_cannot_run_says_so(self):
        """Silence has to mean the entries did not move, and nothing else."""
        found = self.moved(branch="claude/never-made")
        self.assertTrue(any("could not compare" in line for line in found), found)


class StepsCase(unittest.TestCase):
    """The step vocabulary, and its description in the template.

    Two lists of the same thirteen words, one read by programs and one by whoever writes a run file,
    with nothing holding them together — they agreed by luck, exactly as the lens names did until a
    program was told to check those. A step in the template and not in the program is a step the
    check calls unknown; a step in the program and not in the template is a step nobody was told to
    write.
    """

    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "runfile", ROOT / "plugins" / "agent-kit" / "scripts" / "runfile.py")
        self.runfile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runfile)
        self.described = json.loads(
            (ROOT / "plugins" / "agent-kit" / "templates" / "run.json").read_text(encoding="utf-8")
        )["_step"]

    def named_in_the_template(self):
        """Every word the description offers as a choice — the groups written `a | b | c`."""
        words = set()
        for group in re.findall(r"[a-z]+(?:\s*\|\s*[a-z]+)+", self.described):
            words.update(w.strip() for w in group.split("|"))
        return words

    def test_the_template_and_the_program_name_the_same_steps(self):
        self.assertEqual(self.named_in_the_template(), set(self.runfile.STEPS))

    def test_every_terminal_step_is_a_step(self):
        self.assertTrue(set(self.runfile.TERMINAL) <= set(self.runfile.STEPS))

    def test_the_template_says_which_ones_end_a_run(self):
        """A driver stops watching a run that reaches one, so the writer has to know which."""
        self.assertIn("terminal", self.described)


class FlightCase(unittest.TestCase):
    """Where the runs are, and which of them are happening now.

    Both hooks are armed from this, and until 2.21.0 a session standing in a linked worktree read
    *no runs here* — `.agent-kit/` is tracked and `.agent-kit/runs/` is not, so the directory was
    there and empty. A feature that fled to a worktree because its tree was taken therefore ran with
    the merge guard disarmed for the rest of the night.
    """

    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "runfile", ROOT / "plugins" / "agent-kit" / "scripts" / "runfile.py")
        self.runfile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runfile)
        self.tmp = Path(tempfile.mkdtemp())
        self.main = self.tmp / "project"
        (self.main / ".agent-kit" / "runs" / "x").mkdir(parents=True)
        for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                     ["config", "user.name", "t"], ["commit", "-q", "--allow-empty", "-m", "root"]):
            subprocess.run(["git", *args], cwd=self.main, check=False, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, step="build", **fields):
        (self.main / ".agent-kit" / "runs" / "x" / "run.json").write_text(
            json.dumps({"slug": "x", "step": step, **fields}), encoding="utf-8")

    def worktree(self):
        linked = self.tmp / "linked"
        subprocess.run(["git", "worktree", "add", "-q", "-b", "side", str(linked)],
                       cwd=self.main, check=False, capture_output=True)
        # The tracked half travels with the checkout; the runs are gitignored and do not.
        (linked / ".agent-kit").mkdir(parents=True, exist_ok=True)
        return linked

    def test_a_run_in_flight_here(self):
        self.write()
        self.assertEqual(len(self.runfile.in_flight(self.main)), 1)

    def test_a_finished_run_is_not_in_flight(self):
        self.write(step="done")
        self.assertEqual(self.runfile.in_flight(self.main), [])

    def test_a_run_nobody_has_touched_for_a_day(self):
        self.write()
        path = self.main / ".agent-kit" / "runs" / "x" / "run.json"
        old = time.time() - 30 * 3600
        os.utime(path, (old, old))
        self.assertEqual(self.runfile.in_flight(self.main), [])

    def test_a_run_file_nothing_can_parse_counts(self):
        (self.main / ".agent-kit" / "runs" / "x" / "run.json").write_text("{ no", encoding="utf-8")
        self.assertEqual([state for _d, state in self.runfile.in_flight(self.main)], [None])

    def test_a_linked_worktree_finds_the_runs_of_its_project(self):
        self.write()
        linked = self.worktree()
        self.assertEqual(self.runfile.main_worktree(linked).resolve(), self.main.resolve())
        self.assertEqual(len(self.runfile.in_flight(linked)), 1)

    def test_the_main_checkout_is_its_own_main_checkout(self):
        self.assertEqual(self.runfile.main_worktree(self.main).resolve(), self.main.resolve())

    def test_which_command_picks_a_run_up(self):
        """Named by the program because the one place that named it in prose — rung 2 of `next` —
        named a batch and a feature and left the epic out, so a run at `auditing` was offered the
        command that drives a batch."""
        resume = self.runfile.resume_command
        directory = self.main / ".agent-kit" / "runs" / "x"
        self.assertIn("epic --resume", resume({"command": "epic", "step": "auditing"}, directory))
        self.assertIn("epic --resume", resume({"command": "mvp", "step": "proving"}, directory))
        self.assertIn("sprint --resume", resume({"command": "sprint", "step": "building"}, directory))
        self.assertIn("ship --run", resume({"command": "ship", "step": "build"}, directory))

    def test_a_runs_own_prompt_is_what_picks_it_up(self):
        """It is literally what the driver types, and an audit's lens is in it and nowhere else."""
        self.assertEqual(
            self.runfile.resume_command(
                {"command": "audit", "prompt": "/agent-kit:audit tests --run .agent-kit/runs/x"},
                self.main),
            "/agent-kit:audit tests --run .agent-kit/runs/x")

    def test_a_run_nothing_can_place_is_not_handed_to_a_command(self):
        self.assertEqual(self.runfile.resume_command({"step": "build"}, self.main), "")
        self.assertEqual(
            self.runfile.resume_command({"command": "ship", "prompt": "build the feed screen"},
                                        self.main), "")

    def test_a_directory_that_is_no_worktree_at_all(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertEqual(self.runfile.main_worktree(plain), plain)


class KindCase(unittest.TestCase):
    """What a run is, decided in one place instead of eight.

    A feature is built and must prove itself; an errand has no suite of its own; a batch is a queue
    of children and an epic a queue of batches. Every program used to work this out from whatever
    signal was nearest, and the nearest one — *does this file carry a prompt* — was wrong for the
    line the template itself offers as the default.
    """

    def of(self, **fields):
        spec = importlib.util.spec_from_file_location(
            "runfile", ROOT / "plugins" / "agent-kit" / "scripts" / "runfile.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.kind(fields)

    def test_what_the_file_says_wins(self):
        self.assertEqual(self.of(kind="errand", command="ship"), "errand")

    def test_a_kind_no_reader_knows_is_not_a_kind(self):
        self.assertEqual(self.of(kind="chore", command="ship"), "unknown")

    def test_a_prompt_that_invokes_a_command_says_which_kind(self):
        self.assertEqual(self.of(command="ship", prompt="/agent-kit:ship --run .agent-kit/runs/x"),
                         "feature")
        self.assertEqual(self.of(command="ship", prompt="/agent-kit:audit tests --run x"), "errand")

    def test_a_prompt_in_prose_is_not_read_as_anything(self):
        """A frame child written before `kind` existed and a feature whose prompt somebody typed
        out read exactly alike. Guessing either way is what this replaces."""
        self.assertEqual(self.of(command="ship", prompt="Read the frame reference and follow it"),
                         "unknown")

    def test_without_a_prompt_the_command_answers(self):
        for command, expected in (("ship", "feature"), ("fix", "feature"), ("sprint", "batch"),
                                  ("epic", "epic"), ("audit", "errand")):
            self.assertEqual(self.of(command=command), expected, command)

    def test_a_command_no_reader_knows(self):
        self.assertEqual(self.of(command="polish"), "unknown")
        self.assertEqual(self.of(), "unknown")

    def test_the_template_ships_a_kind_that_is_one_of_the_four(self):
        """The template is the specification, and the run that copies it must land on a kind."""
        shape = json.loads((ROOT / "plugins" / "agent-kit" / "templates" / "run.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(self.of(**{k: v for k, v in shape.items() if not k.startswith("_")}),
                         "feature")


class OutsideCase(unittest.TestCase):
    """Everything this program starts, and the two rules that hold for all of it.

    It runs in front of every command of the kit, so a call with no bound stops the project rather
    than the call — one unreachable remote used to be enough. And a call that could not be made is
    not an empty answer: that confusion is the one this whole program is written against, and it
    has been paid for three times.
    """

    SOURCE = (ROOT / "plugins" / "agent-kit" / "scripts" / "check.py").read_text(encoding="utf-8")

    def test_nothing_is_started_without_a_timeout(self):
        """A static rule, because the failure it prevents cannot be provoked in a test: it needs a
        network that hangs rather than refuses."""
        import ast
        tree = ast.parse(self.SOURCE)
        untimed = [node.lineno for node in ast.walk(tree)
                   if isinstance(node, ast.Call)
                   and isinstance(node.func, ast.Attribute) and node.func.attr == "run"
                   and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
                   and not any(kw.arg == "timeout" for kw in node.keywords)]
        self.assertEqual(untimed, [], f"subprocess.run with no timeout at line(s) {untimed}")

    def test_a_command_that_cannot_be_run_is_not_an_empty_answer(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            self.assertIsNone(check.ran(["definitely-not-a-tool-here"], tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_command_that_runs_comes_back_whole(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            done = check.ran(["printf", "hello"], tmp)
            self.assertEqual((done.returncode, done.stdout), (0, "hello"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_offline_never_says_a_pull_request_is_not_merged(self):
        """It cannot know. `merged_prs` answers with an empty set both for *none of them merged*
        and for *nobody here can ask*, and the second was printed as the first."""
        tmp = Path(tempfile.mkdtemp())
        root = tmp / "proj"
        (root / "docs" / "runs").mkdir(parents=True)
        try:
            for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t"),
                         ("config", "user.name", "t")):
                subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True, check=False)
            subprocess.run(["git", "commit", "-qm", "first"], cwd=root, capture_output=True,
                           check=False)
            subprocess.run(["git", "checkout", "-q", "-b", "claude/one"], cwd=root,
                           capture_output=True, check=False)
            (root / "a.txt").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "work"], cwd=root, capture_output=True,
                           check=False)
            subprocess.run(["git", "checkout", "-q", "main"], cwd=root, capture_output=True,
                           check=False)
            (root / "docs" / "runs" / "batch.json").write_text(
                json.dumps({"slug": "batch", "pr": 7, "branches": ["claude/one"]}),
                encoding="utf-8")
            _delivered, unknown = check.delivered_branches(root, "main", check.Offline(root))
            self.assertEqual([name for name, _why in unknown], ["claude/one"])
            self.assertIn("could ask", unknown[0][1])
            self.assertNotIn("is not merged", unknown[0][1])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CommandsCase(unittest.TestCase):
    """A declared command that starts nothing.

    Emptiness was the whole test: `test: make test` on a project with no makefile passed every rule
    this program had, and the run that met it was a child at three in the morning with a suite it
    could not run. Only the first word is judged — the rest is the tool's business — and everything
    this cannot read it says nothing about, because a guess here would block a whole project.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        self.root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def defect(self, command):
        return check.command_defect(self.root, command)

    def test_make_without_a_makefile(self):
        self.assertIn("no makefile", self.defect("make test"))

    def test_make_with_a_makefile_is_silent(self):
        (self.root / "Makefile").write_text("test:\n\techo hi\n", encoding="utf-8")
        self.assertEqual(self.defect("make test"), "")

    def test_a_tool_no_machine_here_has(self):
        self.assertIn("not on the PATH", self.defect("definitely-not-a-tool-here run"))

    def test_the_shell_that_moves_first_is_not_the_tool(self):
        """`cd app && npm test` judged on `cd` would be a finding about the shell, which is not
        what anybody declared."""
        self.assertEqual(self.defect("cd app && python3 -m pytest"), "")
        self.assertIn("nope-tool", self.defect("cd app && nope-tool --ci"))

    def test_the_environment_in_front_of_the_tool_is_not_the_tool(self):
        self.assertEqual(self.defect("APP_ENV=testing python3 -m pytest"), "")
        self.assertEqual(self.defect("env FOO=1 python3 -m pytest"), "")

    def test_a_path_is_judged_against_the_project_and_not_the_path(self):
        """`vendor/bin/phpunit` is installed into the project, so `which` says nothing about it."""
        self.assertIn("nothing is at vendor/bin/phpunit", self.defect("vendor/bin/phpunit --colors"))
        (self.root / "vendor" / "bin").mkdir(parents=True)
        (self.root / "vendor" / "bin" / "phpunit").write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertEqual(self.defect("vendor/bin/phpunit --colors"), "")

    def test_what_it_cannot_read_it_says_nothing_about(self):
        """An unbalanced quote is not a tool to go looking for, and neither is an empty string. The
        alternative is a finding that blocks every command in a project over a guess."""
        self.assertEqual(self.defect('sh -c "echo unbalanced'), "")
        self.assertEqual(self.defect("   "), "")

    def test_a_container_is_judged_on_the_thing_that_starts_it(self):
        self.assertIn("`docker-not-here`", self.defect("docker-not-here compose exec app pytest"))

    def test_a_command_that_runs_somewhere_else_is_not_judged_from_here(self):
        """A monorepo says `cd apps/api && vendor/bin/phpunit`, and that path is relative to a
        directory this program is not standing in. The first version resolved it from the root,
        called a file that exists *nothing is at*, and a finding here stops every command of the
        kit on that project — which is the one thing this rule may not do."""
        (self.root / "apps" / "api" / "vendor" / "bin").mkdir(parents=True)
        (self.root / "apps" / "api" / "vendor" / "bin" / "phpunit").write_text("#!/bin/sh\n",
                                                                              encoding="utf-8")
        self.assertEqual(self.defect("cd apps/api && vendor/bin/phpunit"), "")

    def test_make_with_a_directory_of_its_own(self):
        (self.root / "app").mkdir()
        (self.root / "app" / "Makefile").write_text("test:\n\techo hi\n", encoding="utf-8")
        self.assertEqual(self.defect("make -C app test"), "")
        self.assertEqual(self.defect("make -f app/Makefile test"), "")

    def test_a_subshell_is_punctuation_and_not_a_tool(self):
        self.assertEqual(self.defect("(cd app && python3 -m pytest)"), "")


class ManualCase(unittest.TestCase):
    """What only the owner can do, and the proof that closes it without them saying so.

    These lived in a git-ignored run file and reached the owner through one pull request, so the day
    after the merge nothing held them. The file is the record; the proof being a command rather than
    a sentence is what keeps the list true a month later.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "docs").mkdir(parents=True)
        (self.root / ".agent-kit").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manual(self, text, stage="development"):
        (self.root / "docs" / "manual.md").write_text(text, encoding="utf-8")
        (self.root / ".agent-kit" / "project.yml").write_text(
            f"stage: {stage}\ncommands:\n  test: make test\n", encoding="utf-8")

    def worked_examples(self):
        """The actions `templates/manual.md` teaches by example, lifted out of their fences.

        The template is the specification and a project copies its form out of it, so these are the
        only inputs whose parsing is a promise to somebody. Nothing ran them through the parser
        until 2.19.4, and they did not parse: both wrap the action onto a second line and put
        `· before_release` there, while `when` was read off the first line alone. Inside the
        template the loop skips them, because a fenced block is not an action — so the check was
        silent on exactly the input it publishes, and the test that existed had been written from
        the parser rather than from the file.
        """
        spec = (ROOT / "plugins" / "agent-kit" / "templates" / "manual.md").read_text(
            encoding="utf-8")
        blocks = [b for b in re.findall(r"```markdown\n(.*?)```", spec, re.S)
                  if "- [ ]" in b and "<what to do>" not in b]
        self.assertTrue(blocks, "the template stopped carrying a worked example")
        return "# Manual actions\n\n" + "\n".join(blocks)

    def test_every_form_the_template_teaches_is_read_the_way_it_is_written(self):
        self.manual(self.worked_examples())
        actions = check.read_manual(self.root)
        self.assertEqual(len(actions), 2, actions)
        for action in actions:
            self.assertIn(action["when"], check.STAGES, action)
            self.assertTrue(action["proof"], action)

    def test_a_release_action_written_the_way_the_template_writes_it_waits(self):
        """The whole point of `when`: on a project with no release, those lines are kept and not
        shown. Unreadable, they were shown — which is the failure this mechanism exists against."""
        self.manual(self.worked_examples())
        report = check.Report()
        check.collect_manual(self.root, {"stage": "development"}, report)
        self.assertTrue(any("wait for a release" in line for line in report.manual), report.manual)
        self.assertFalse([line for line in report.manual if "Stripe" in line], report.manual)

    def prove(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check.prove_manual(self.root)
        return out.getvalue(), (self.root / "docs" / "manual.md").read_text(encoding="utf-8")

    ACTIONS = ("- [ ] place the key — payments read it · before_release · PR #21\n"
               "      proof: `test -n \"$NOT_SET_ANYWHERE\"`\n"
               "- [ ] create the moderator — nothing can be reviewed · before_run · PR #21\n"
               "      proof: `true`\n"
               "- [ ] confirm the listing went live · before_merge · PR #21\n"
               "      proof: none — only a person can see it\n")

    def test_a_proof_that_passes_takes_its_line_with_it(self):
        self.manual(self.ACTIONS)
        output, left = self.prove()
        self.assertIn("Done and removed (1)", output)
        self.assertNotIn("create the moderator", left)
        self.assertIn("place the key", left)          # its proof still says not yet
        self.assertIn("confirm the listing", left)    # nothing can prove this one

    def test_a_proof_that_fails_is_the_owner_not_having_done_it_yet(self):
        self.manual(self.ACTIONS)
        output, _left = self.prove()
        self.assertIn("Still waiting on the owner (2)", output)

    def test_an_action_with_no_proof_is_named_as_one_nobody_can_close(self):
        self.manual(self.ACTIONS)
        output, _left = self.prove()
        self.assertIn("only they can see it", output)

    def test_the_line_under_an_action_goes_with_it_and_nothing_else_does(self):
        """The proof rides under its action, so closing one cuts exactly its own lines — a cut that
        took one line too many would leave a stray `proof:` belonging to nothing."""
        self.manual(self.ACTIONS)
        _output, left = self.prove()
        self.assertNotIn("`true`", left)
        self.assertEqual(left.count("proof:"), 2)

    def test_a_release_this_project_has_not_reached_is_kept_and_not_shown(self):
        self.manual(self.ACTIONS)
        report = check.Report()
        check.collect_manual(self.root, {"stage": "development"}, report)
        shown = "\n".join(report.manual)
        self.assertNotIn("place the key", shown)      # before_release, and there is no release
        self.assertIn("create the moderator", shown)
        self.assertIn("1 more wait for a release", shown)

    def test_a_released_project_is_shown_all_of_them(self):
        self.manual(self.ACTIONS, stage="released")
        report = check.Report()
        check.collect_manual(self.root, {"stage": "released"}, report)
        self.assertIn("place the key", "\n".join(report.manual))

    def test_a_fenced_example_is_not_an_action(self):
        """The template explains its own format in a fence, exactly as the ledger's does."""
        self.manual("```markdown\n- [ ] the example — · before_run · PR #1\n      proof: `true`\n"
                    "```\n")
        report = check.Report()
        check.collect_manual(self.root, {}, report)
        self.assertEqual(report.manual, [])

    def test_a_file_that_is_mostly_unprovable_says_so(self):
        self.manual("".join(
            f"- [ ] action {n} · before_run · PR #1\n      proof: none — a person sees it\n"
            for n in range(4)))
        report = check.Report()
        check.collect_manual(self.root, {}, report)
        self.assertTrue(any("nothing here closes itself" in line for line in report.manual))

    def test_no_file_at_all_says_nothing(self):
        report = check.Report()
        check.collect_manual(self.root, {}, report)
        self.assertEqual(report.manual, [])


class MergedPrsCase(unittest.TestCase):
    """The other reader of the listing, which had no test of its own.

    Every test that reaches `merged_prs` goes through `delivered_branches` and replaces it with a
    lambda — so the half of the one-call change that serves batch records was covered by nothing,
    and a drift in what the listing returns would have left every squashed branch unjudged with the
    suite still green.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "bin").mkdir(parents=True)
        self.asked = self.root / "asked.txt"
        gh = self.root / "bin" / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            f'echo "$@" >> {self.asked}\n'
            'case "$2" in\n'
            "  list) printf '%s\\n' "
            "'[{\"number\": 7, \"state\": \"MERGED\"}, {\"number\": 8, \"state\": \"OPEN\"}]' ;;\n"
            "  view) printf '{\"state\":\"MERGED\"}\\n' ;;\n"
            "esac\n", encoding="utf-8")
        gh.chmod(0o755)
        self.was = os.environ["PATH"]
        os.environ["PATH"] = f"{self.root / 'bin'}:{self.was}"

    def tearDown(self):
        os.environ["PATH"] = self.was
        shutil.rmtree(self.tmp, ignore_errors=True)

    def asked_lines(self):
        return self.asked.read_text(encoding="utf-8").splitlines() if self.asked.exists() else []

    def test_the_numbers_a_record_names_are_answered_from_one_listing(self):
        self.assertEqual(check.Github(self.root).merged({7, 8}), {7})
        self.assertEqual(len(self.asked_lines()), 1, self.asked_lines())

    def test_a_number_the_listing_does_not_carry_is_asked_about_directly(self):
        """An old batch record whose branches are still around names a pull request older than one
        page of the listing. Unasked, its branches read as undelivered for ever."""
        self.assertEqual(check.Github(self.root).merged({9}), {9})
        self.assertEqual([line.split(" --json")[0] for line in self.asked_lines()],
                         ["pr list --state all --limit 100", "pr view 9"])

    def test_offline_asks_nothing(self):
        """The offline object is the same object with the answers removed — never an empty result
        standing in for one nobody asked for."""
        self.assertEqual(check.Offline(self.root).merged({7}), set())
        self.assertEqual(check.Offline(self.root).states(), None)
        self.assertEqual(self.asked_lines(), [])


class BranchesCase(unittest.TestCase):
    """Which branches a merged pull request has already delivered.

    The case this exists for is a squash merge: the branch's commits are then nowhere in the base
    and `--merged` says no for ever. One project reached 99 branches that way, of which git could
    answer for 47 — so the record has to answer for the rest, and a branch nothing can judge has to
    be said rather than assumed either way.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "docs" / "runs").mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (self.root / "a.txt").write_text("one\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "first")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=False)

    def branch(self, name, text):
        self.git("checkout", "-q", "-b", name)
        (self.root / "a.txt").write_text(text, encoding="utf-8")
        self.git("commit", "-qam", f"work on {name}")
        self.git("checkout", "-q", "main")

    def record(self, name, number, branches, parked=()):
        (self.root / "docs" / "runs" / f"{name}.json").write_text(
            json.dumps({"slug": name, "pr": number, "branches": branches,
                        "parked": list(parked)}), encoding="utf-8")

    class Answers(check.Github):
        """A GitHub that says exactly what the test says, and is asked the same way the real one is."""

        def __init__(self, root, merged, heads=None):
            super().__init__(root)
            self._merged = {int(n) for n in merged}
            self._answer_heads = dict(heads or {})

        @property
        def available(self):
            return True

        def states(self):
            return {}                              # asked, and this repository has none of its own

        def merged(self, numbers):
            return {int(n) for n in numbers if int(n) in self._merged}

        def merged_heads(self):
            return self._answer_heads

    def judge(self, merged=(), heads=None):
        return check.delivered_branches(self.root, "main",
                                        self.Answers(self.root, merged, heads))

    def tip(self, name):
        return check.git(self.root, "rev-parse", name)

    def test_a_record_that_is_json_but_not_a_record_does_not_take_the_reading_down(self):
        """It parses, so the guard against unreadable files does not catch it, and every command
        runs this. Skipped here and named by the check that may speak."""
        self.branch("claude/one", "two\n")
        self.record("batch", 7, ["claude/one"])
        (self.root / "docs" / "runs" / "broken.json").write_text("[]", encoding="utf-8")
        delivered, _unjudged = self.judge(merged=[7])
        self.assertIn("claude/one", [name for name, _why in delivered])

    def test_a_squashed_branch_is_delivered_by_its_record_and_not_by_git(self):
        self.branch("claude/one", "two\n")
        self.record("batch", 7, ["claude/one"])
        self.git("checkout", "-q", "main")
        (self.root / "a.txt").write_text("two\n", encoding="utf-8")   # the squash
        self.git("commit", "-qam", "squashed (#7)")
        self.assertEqual(check.git(self.root, "branch", "--merged", "main").count("claude/one"), 0,
                         "git cannot see a squashed branch as merged — that is the whole case")
        delivered, unknown = self.judge(merged={7})
        self.assertEqual([name for name, _ in delivered], ["claude/one"])
        self.assertEqual(unknown, [])

    def test_the_batchs_own_delivery_branch_is_retired_too(self):
        """`sprint/<slug>` is what the pull request was opened *from*, so a squash leaves its commits
        nowhere in the base and ancestry can never answer for it. The record has carried it in
        `branch` all along and this reading used to skip that field — so the mechanism built against
        99 unremovable branches went on making one per batch. Measured on a live project: six
        children retired by name, the seventh reported as unjudgeable."""
        self.branch("claude/one", "two\n")
        self.branch("sprint/batch", "three\n")
        (self.root / "docs" / "runs" / "batch.json").write_text(
            json.dumps({"slug": "batch", "pr": 7, "branch": "sprint/batch",
                        "branches": ["claude/one"], "parked": []}), encoding="utf-8")
        delivered, unknown = self.judge(merged={7})
        self.assertEqual(sorted(name for name, _ in delivered), ["claude/one", "sprint/batch"])
        self.assertEqual(unknown, [])

    def test_a_branch_no_record_names_is_answered_by_the_merged_pull_request(self):
        """The last branch in this kit with no fourth answer: a `fix`, a standalone `ship` and
        `blueprint`'s knowledge branch write no record, so once their pull request is squashed
        nothing could ever say they were delivered. Measured on a live project — every `next` asked
        the owner about the same two branches and would have gone on asking."""
        self.branch("claude/fix-the-cache", "two\n")
        delivered, unknown = self.judge(heads={"claude/fix-the-cache":
                                              (19, self.tip("claude/fix-the-cache"))})
        self.assertEqual([name for name, _ in delivered], ["claude/fix-the-cache"])
        self.assertIn("19 merged this branch", delivered[0][1])
        self.assertEqual(unknown, [])

    def test_a_branch_that_moved_after_its_merge_is_not_retired(self):
        """`headRefOid` is what makes the answer a fact. A branch that has moved since carries work
        the pull request did not, and that work is on one machine."""
        self.branch("claude/fix-the-cache", "two\n")
        merged_at = self.tip("claude/fix-the-cache")
        self.git("checkout", "-q", "claude/fix-the-cache")
        (self.root / "a.txt").write_text("three\n", encoding="utf-8")
        self.git("commit", "-qam", "one more, after the merge")
        self.git("checkout", "-q", "main")
        delivered, unknown = self.judge(heads={"claude/fix-the-cache": (19, merged_at)})
        self.assertEqual(delivered, [])
        self.assertIn("commits since", unknown[0][1])
        self.assertIn("this machine only", unknown[0][1])

    def test_nothing_that_could_be_asked_is_never_read_as_an_answer(self):
        """`Offline` says *could not ask* to everything, and a branch is then unjudged with that as
        its reason — never retired, and never reported as unmerged either."""
        self.branch("claude/fix-the-cache", "two\n")
        delivered, unknown = check.delivered_branches(self.root, "main", check.Offline(self.root))
        self.assertEqual(delivered, [])
        self.assertIn("could ask GitHub", unknown[0][1])

    def test_a_parked_own_branch_is_not_retired_by_its_own_record(self):
        """The one case where `branch` must not be trusted: a batch that parked its own delivery."""
        self.branch("sprint/batch", "three\n")
        (self.root / "docs" / "runs" / "batch.json").write_text(
            json.dumps({"slug": "batch", "pr": 7, "branch": "sprint/batch",
                        "branches": [], "parked": ["sprint/batch"]}), encoding="utf-8")
        delivered, unknown = self.judge(merged={7})
        self.assertEqual(delivered, [])
        self.assertEqual([name for name, _ in unknown], ["sprint/batch"])

    def test_a_parked_branch_survives_the_merge_that_did_not_carry_it(self):
        """A child that stopped mid-feature keeps its branch pushed and out of the chain, so the
        batch's pull request merges without it. Both lists were one field until 2.17.0, and a merged
        number therefore retired work that was never delivered — on the remote too, where a branch
        nobody ever had a local copy of has no second one."""
        self.branch("claude/one", "two\n")
        self.branch("claude/parked", "three\n")
        self.record("batch", 7, ["claude/one", "claude/parked"], parked=["claude/parked"])
        delivered, unknown = self.judge(merged={7})
        self.assertEqual([name for name, _ in delivered], ["claude/one"])
        self.assertEqual([name for name, _ in unknown], ["claude/parked"])
        self.assertIn("parked", unknown[0][1])

    def test_a_parked_branch_whose_work_did_reach_the_base_is_still_retired(self):
        """Held out of the record's answer, not out of the reading: ancestry still speaks for it,
        and a branch whose commits are in the base is delivered whatever a record says."""
        self.branch("claude/parked", "three\n")
        self.git("merge", "-q", "--no-ff", "-m", "merged by hand", "claude/parked")
        self.record("batch", 7, ["claude/parked"], parked=["claude/parked"])
        delivered, _unknown = self.judge(merged={7})
        self.assertEqual([name for name, _ in delivered], ["claude/parked"])

    def test_an_unmerged_pull_request_retires_nothing(self):
        self.branch("claude/one", "two\n")
        self.record("batch", 7, ["claude/one"])
        delivered, unknown = self.judge(merged=set())
        self.assertEqual(delivered, [])
        self.assertEqual([name for name, _ in unknown], ["claude/one"])
        self.assertIn("not merged", unknown[0][1])

    def test_a_branch_no_record_names_is_said_rather_than_assumed(self):
        self.branch("claude/orphan", "two\n")
        delivered, unknown = self.judge()
        self.assertEqual(delivered, [])
        # Both halves of *nothing knows about it*: no record, and no merged pull request was ever
        # opened from it. The second half is what stopped this being said about a `fix` branch.
        self.assertEqual(unknown, [("claude/orphan", "no run record names it, and no merged pull "
                                                    "request was opened from it")])

    def test_ancestry_still_answers_where_it_can(self):
        self.branch("claude/one", "two\n")
        self.git("merge", "-q", "--no-ff", "-m", "merge", "claude/one")
        delivered, unknown = self.judge()
        self.assertEqual([name for name, _ in delivered], ["claude/one"])
        self.assertEqual(unknown, [])
