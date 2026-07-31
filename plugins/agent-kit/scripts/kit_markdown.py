"""Section resolution and hashing over a Markdown document, stdlib only.

A section is bound by an ATX heading and ends at the next heading of the same
or higher level (fewer or equal `#` characters) — a deeper section followed by
a shallower one does not swallow the rest of the document. Headings inside
fenced code blocks are not headings.
"""

import hashlib
import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


class MissingSection(Exception):
    def __init__(self, title):
        self.title = title
        super().__init__("no section titled {!r}".format(title))


class AmbiguousSection(Exception):
    def __init__(self, title):
        self.title = title
        super().__init__("more than one section titled {!r}".format(title))


def sections(text):
    """Return an ordered list of (level, title, body) over the document."""
    lines = text.splitlines()
    headings = []
    in_fence = False
    fence_marker = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_fence:
            # A fence closes only on the same character, at least as long as
            # the one that opened it. Comparing a fixed three characters lets
            # a nested ``` example close an outer ```` fence, after which a
            # `#` line inside the example reads as a real heading.
            close = _FENCE_RE.match(stripped)
            if (
                close
                and close.group(1)[0] == fence_marker[0]
                and len(close.group(1)) >= len(fence_marker)
            ):
                in_fence = False
            continue
        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            in_fence = True
            fence_marker = fence_match.group(1)
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            headings.append((len(heading_match.group(1)), heading_match.group(2), i))

    result = []
    for idx, (level, title, line_index) in enumerate(headings):
        end = len(lines)
        for later_level, _title, later_index in headings[idx + 1 :]:
            if later_level <= level:
                end = later_index
                break
        body = "\n".join(lines[line_index + 1 : end])
        result.append((level, title, body))
    return result


def section(text, title):
    """Return the single (level, title, body) matching `title`, or raise."""
    matches = [s for s in sections(text) if s[1] == title]
    if not matches:
        raise MissingSection(title)
    if len(matches) > 1:
        raise AmbiguousSection(title)
    return matches[0]


def rev(body):
    """First 12 hex chars of sha256 over `body`, normalized line-by-line."""
    lines = [line.rstrip() for line in body.splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    normalized = "\n".join(lines)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
