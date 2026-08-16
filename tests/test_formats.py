"""Every format this kit writes into a document and reads back out of one.

    python3 -m unittest discover -s tests

The kit invents small markdown formats — a key line, a source reference, a block under an entry, a
mark beside a test, a counter in an audit — writes them with prose and reads them with a regular
expression somewhere else. **Nothing connected the two.** The specification is a sentence in a
template or a command, the parser is a pattern in `check.py`, and each was checked against the
other by whoever last touched one.

That gap shipped twice, and both were found by reading rather than by running. `docs/manual.md`
taught an action wrapped onto a second line and its parser read only the first, so a release action
printed on a project that has no release. A `source:` line written without its hash matched nothing
at all, so an entry that named its source read exactly like one that named none.

So each row below carries **the example as the payload writes it**, and asserts two things: the
example still appears in the file that teaches it, and the parser still reads it as it must. Change
the prose and this fails; change the pattern and this fails. `scripts/validate.sh` closes the loop
from the other side — a pattern in `check.py` that no row covers has to be declared as not a format,
with a reason, so a fourteenth one cannot be added in silence.
"""

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "agent-kit"
SPEC = importlib.util.spec_from_file_location("check", PLUGIN / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


def first(pattern, text):
    found = pattern.search(text)
    return found.groups() if found else None


# name → the file that teaches it, the example exactly as that file writes it, and what the parser
# must make of it. The example is looked for verbatim, so a spec that changes its own form fails
# here rather than at three in the morning on somebody's project.
FORMATS = [
    ("KEY_RE", "templates/knowledge/entities.md",
     "`key: offer`",
     lambda text: first(check.KEY_RE, text) == ("offer", None)),

    ("STATE_LINE_RE", "templates/knowledge/actions.md",
     "`key: developer.create_offer` · `state: planned`",
     lambda text: first(check.KEY_RE, text) == ("developer.create_offer", "planned")),

    ("FIELDS_RE", "templates/knowledge/entities.md",
     "fields: What it is, States, Transitions, Relations, Invariants",
     lambda text: first(check.FIELDS_RE, text)
     == ("What it is, States, Transitions, Relations, Invariants",)),

    ("SOURCE_RE", "rules/knowledge-writing.md",
     "`source: docs/DEVELOPER.md#offers @a3f1c9d1`",
     lambda text: first(check.SOURCE_RE, text) == ("docs/DEVELOPER.md", "offers", "a3f1c9d1")),

    ("NOTE_RE", "skills/ship/SKILL.md",
     "> **[assumed 2026-08-02 · claude/<branch>]** <what the knowledge does not say>.",
     lambda text: (first(check.NOTE_RE, text) or ("",))[0] == "assumed"),

    ("SCENARIO_MARK", "templates/knowledge/scenarios.md",
     "`agent-kit:scenario <this heading>`",
     lambda text: check.SCENARIO_MARK in text),

    ("MARK", "templates/project.yml",
     "`agent-kit:unmet <entry key>`",
     lambda text: check.MARK in text
     and check.MARK_RE.search(f"// {check.MARK} guest.browse_feed").group(1) == "guest.browse_feed"),

    ("TALLY_RE", "skills/audit/SKILL.md",
     "<!-- agent-kit:audit lens=tests walked=49 covered=33 gaps=8 unjudged=1 deferred=7 declined=0 -->",
     lambda text: dict(check.TALLY_PAIR_RE.findall(check.TALLY_RE.search(text).group(1)))
     .get("walked") == "49"),

    ("WALKED_RE", "templates/knowledge/product.md",
     "`walked: 2026-08-09`",
     lambda text: check.WALKED_RE.search(f"- часть — {text}") is not None),

    ("PROOF_RE", "templates/manual.md",
     "      proof: `test -n \"$STRIPE_SECRET_KEY\"`",
     lambda text: (check.PROOF_RE.match(text) or [None, None])[1] == 'test -n "$STRIPE_SECRET_KEY"'),

    ("MVP_MARK", "templates/knowledge/product.md",
     "<!-- agent-kit:mvp-bounds -->",
     lambda text: check.section_after(f"{text}\n## Bounds\n\n**In:** one\n", check.MVP_MARK)
     is not None),
]


class FormatCase(unittest.TestCase):
    """Each format, against the file that teaches it."""

    def test_every_example_is_still_in_the_file_that_teaches_it(self):
        for name, path, example, _reads in FORMATS:
            with self.subTest(name):
                text = (PLUGIN / path).read_text(encoding="utf-8")
                self.assertIn(example.strip(), text,
                              f"{path} no longer writes {name} the way this test reads it")

    def test_every_example_parses_the_way_the_program_needs(self):
        for name, _path, example, reads in FORMATS:
            with self.subTest(name):
                self.assertTrue(reads(example), f"{name} does not read its own documented example")

    def test_the_registry_covers_every_pattern_the_program_declares(self):
        """The same rule `validate.sh` enforces, kept here so it fails in the suite too — the two
        cost nothing and a new format slips past neither."""
        declared = set(re.findall(r"^([A-Z][A-Z_]*(?:_RE|_MARK)) = ", check_source(), re.M))
        covered = {name for name, *_ in FORMATS}
        parked = set(NOT_A_FORMAT)
        self.assertEqual(declared - covered - parked, set(),
                         "a pattern with no documented example and no reason to be without one")
        self.assertEqual(parked & covered, set(), "a pattern both covered and parked")


def check_source():
    return (PLUGIN / "scripts" / "check.py").read_text(encoding="utf-8")


# Patterns that are not formats of this kit, and why. Kept beside the registry rather than in a
# comment, because this is what lets the check above be exact: anything not here and not covered is
# a format somebody added without an example.
NOT_A_FORMAT = {
    "HEADING_RE": "markdown's own heading, not a format this kit invented",
    "SOURCE_LOOSE_RE": "the loose reading of SOURCE_RE, whose whole job is to catch what that misses",
    "TALLY_PAIR_RE": "one pair inside TALLY_RE, exercised through it",
    "REF_RE": "an entry key mentioned in prose — the key format is KEY_RE",
    "MARK_RE": "built from MARK, and exercised through its row above",
    "DERIVED_RE": "the other half of WALKED_RE, one word with no shape to get wrong",
    "DECLINED_RE": "one backticked word",
    "ENTRY_POINT_RE": "one backticked word",
    "PINNED_PLUGIN": "a path shape this kit refuses, not one it writes",
    "PROMPT_RE": "a command line the driver types, judged by its own rule",
}


if __name__ == "__main__":
    unittest.main()
