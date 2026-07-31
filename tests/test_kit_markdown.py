import os
import random
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "plugins", "agent-kit", "scripts")
sys.path.insert(0, SCRIPTS)

import kit_markdown as km  # noqa: E402


class BoundaryTests(unittest.TestCase):
    def test_section_ends_at_next_heading_of_same_level(self):
        text = "# A\nbody a\n\n# B\nbody b\n"
        _, _, body = km.section(text, "A")
        self.assertEqual(body.strip(), "body a")

    def test_deeper_subsection_is_swallowed_by_its_parent(self):
        text = "## B\nbody b\n### C\nbody c\n## D\nbody d\n"
        _, _, body_b = km.section(text, "B")
        self.assertIn("body b", body_b)
        self.assertIn("### C", body_b)
        self.assertIn("body c", body_b)
        self.assertNotIn("body d", body_b)

    def test_shallower_heading_after_ends_the_deeper_section(self):
        # A deeper section followed by a shallower heading must not swallow the rest of the file —
        # "same level" alone would be wrong here; it ends at same-or-higher level.
        text = "# A\n### C\nbody c\n## B\nbody b\n"
        _, _, body_c = km.section(text, "C")
        self.assertEqual(body_c.strip(), "body c")

    def test_last_section_runs_to_end_of_document(self):
        text = "# A\nbody a\n# B\nbody b\nmore\n"
        _, _, body_b = km.section(text, "B")
        self.assertEqual(body_b.strip(), "body b\nmore")


class FencedCodeTests(unittest.TestCase):
    def test_heading_inside_fence_is_not_a_heading(self):
        text = "# Real\ntext\n```\n## Not a heading\n```\nmore text\n# Next\nx\n"
        secs = km.sections(text)
        titles = [t for _level, t, _body in secs]
        self.assertEqual(titles, ["Real", "Next"])

    def test_tilde_fence_is_also_respected(self):
        text = "# Real\n~~~\n## Not a heading\n~~~\nmore\n"
        secs = km.sections(text)
        titles = [t for _level, t, _body in secs]
        self.assertEqual(titles, ["Real"])


class LookupErrorTests(unittest.TestCase):
    def test_missing_heading_raises(self):
        text = "# A\nbody\n"
        with self.assertRaises(km.MissingSection):
            km.section(text, "Nowhere")

    def test_duplicate_heading_raises_ambiguous(self):
        text = "# A\nfirst\n# A\nsecond\n"
        with self.assertRaises(km.AmbiguousSection):
            km.section(text, "A")


class RevTests(unittest.TestCase):
    def test_trailing_whitespace_does_not_affect_rev(self):
        self.assertEqual(km.rev("line one\nline two"), km.rev("line one \nline two\t"))

    def test_trailing_blank_lines_do_not_affect_rev(self):
        self.assertEqual(km.rev("line one\nline two"), km.rev("line one\nline two\n\n\n"))

    def test_content_change_changes_rev(self):
        self.assertNotEqual(km.rev("line one\nline two"), km.rev("line one\nline TWO"))


def _render(entries):
    lines = []
    for _level, title_line, body_lines in entries:
        lines.append(title_line)
        lines.extend(body_lines)
    return "\n".join(lines) + "\n"


def _gen_entries(rng, count=6):
    # Fixed, flat level: the property under test is sibling independence, not the separate
    # (already covered) nesting/swallowing behavior between parent and child levels.
    entries = []
    for i in range(count):
        level = 2
        title = "Section {}".format(i)
        body_lines = [
            rng.choice(["Some body text.", "More prose here.", "Another line of text.", "Yet more words."])
            for _ in range(rng.randint(1, 4))
        ]
        if rng.random() < 0.3:
            body_lines += ["```", "## not a real heading inside a fence", "```"]
        entries.append([level, "{} {}".format("#" * level, title), body_lines])
    return entries


class PropertyTests(unittest.TestCase):
    """A section's hash changes when and only when that section's own text changes."""

    def test_hash_changes_iff_section_text_changes(self):
        for seed in range(25):
            rng = random.Random(seed)
            entries = _gen_entries(rng)
            titles = ["Section {}".format(i) for i in range(len(entries))]
            text = _render(entries)

            before = {title: km.rev(km.section(text, title)[2]) for title in titles}

            for target_index, target_title in enumerate(titles):
                mutated_entries = [list(e) for e in entries]
                mutated_entries[target_index][2] = mutated_entries[target_index][2] + ["MUTATED_WORD"]
                mutated_text = _render(mutated_entries)

                for title in titles:
                    _, _, body = km.section(mutated_text, title)
                    new_rev = km.rev(body)
                    if title == target_title:
                        self.assertNotEqual(
                            before[title], new_rev, "seed={} title={} did not change".format(seed, title)
                        )
                    else:
                        self.assertEqual(
                            before[title], new_rev, "seed={} title={} changed unexpectedly".format(seed, title)
                        )

    def test_whitespace_only_changes_never_move_the_hash(self):
        for seed in range(10):
            rng = random.Random(seed)
            entries = _gen_entries(rng)
            titles = ["Section {}".format(i) for i in range(len(entries))]
            text = _render(entries)
            before = {title: km.rev(km.section(text, title)[2]) for title in titles}

            padded_entries = [list(e) for e in entries]
            for entry in padded_entries:
                entry[2] = entry[2] + ["   ", "", ""]
                entry[2][0] = entry[2][0] + "   "
            padded_text = _render(padded_entries)

            for title in titles:
                _, _, body = km.section(padded_text, title)
                self.assertEqual(before[title], km.rev(body), "seed={} title={}".format(seed, title))


if __name__ == "__main__":
    unittest.main()
