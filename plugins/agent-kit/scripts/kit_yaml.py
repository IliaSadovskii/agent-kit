"""Stdlib-only reader for the YAML subset the kit's own files use.

Covers nested block maps, block lists of scalars, plain and quoted scalars,
null/true/false/integers, comments, and blank lines. Anything outside that
subset — flow collections, block scalars, anchors, aliases, multiple
documents — raises KitYamlError naming the construct and the line.
"""

import re

_INT_RE = re.compile(r"^-?\d+$")
_KEY_RE = re.compile(r"^([^:\s][^:]*?):(?:\s+(.*)|)$")


class KitYamlError(Exception):
    def __init__(self, message, path, line_no):
        self.path = path
        self.line_no = line_no
        super().__init__("{}:{}: {}".format(path, line_no, message))


def load(text, path="<string>"):
    lines = _tokenize(text, path)
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0], path)
    if index != len(lines):
        raise KitYamlError("unexpected indentation", path, lines[index][2])
    return value


def _tokenize(text, path):
    lines = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped == "":
            continue
        leading = raw[: len(raw) - len(raw.lstrip(" "))]
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise KitYamlError("tab used for indentation", path, line_no)
        if stripped.startswith("#"):
            continue
        if stripped in ("---", "..."):
            raise KitYamlError("multiple documents are not supported", path, line_no)
        indent = len(leading)
        content = raw[indent:].rstrip()
        lines.append((indent, content, line_no))
    return lines


def _parse_block(lines, i, indent, path):
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        return _parse_list(lines, i, indent, path)
    return _parse_map(lines, i, indent, path)


def _parse_map(lines, i, indent, path):
    result = {}
    while i < len(lines) and lines[i][0] == indent:
        ind, content, line_no = lines[i]
        if content.startswith("- "):
            raise KitYamlError("list item where a map key was expected", path, line_no)
        match = _KEY_RE.match(content)
        if not match:
            raise KitYamlError("unrecognized construct: {!r}".format(content), path, line_no)
        key, rest = match.group(1).strip(), match.group(2)
        i += 1
        if rest is None or rest == "":
            if i < len(lines) and lines[i][0] > indent:
                child_indent = lines[i][0]
                value, i = _parse_block(lines, i, child_indent, path)
            else:
                value = None
        else:
            value = _parse_scalar(rest, path, line_no)
        result[key] = value
    return result, i


def _parse_list(lines, i, indent, path):
    result = []
    while i < len(lines) and lines[i][0] == indent and (
        lines[i][1].startswith("- ") or lines[i][1] == "-"
    ):
        ind, content, line_no = lines[i]
        rest = content[1:].lstrip(" ") if content != "-" else ""
        i += 1
        if rest == "":
            if i < len(lines) and lines[i][0] > indent:
                child_indent = lines[i][0]
                value, i = _parse_block(lines, i, child_indent, path)
            else:
                value = None
        else:
            value = _parse_scalar(rest, path, line_no)
        result.append(value)
    return result, i


def _parse_scalar(text, path, line_no):
    text = text.strip()
    if text.startswith('"'):
        m = re.match(r'^"((?:[^"\\]|\\.)*)"\s*(#.*)?$', text)
        if not m:
            raise KitYamlError("unterminated or malformed double-quoted scalar", path, line_no)
        return _unescape_double(m.group(1))
    if text.startswith("'"):
        m = re.match(r"^'((?:[^']|'')*)'\s*(#.*)?$", text)
        if not m:
            raise KitYamlError("unterminated or malformed single-quoted scalar", path, line_no)
        return m.group(1).replace("''", "'")
    if text.startswith("[") or text.startswith("{"):
        raise KitYamlError("flow collections are not supported", path, line_no)
    if text.startswith("|") or text.startswith(">"):
        raise KitYamlError("block scalars are not supported", path, line_no)
    if text.startswith("&") or text.startswith("*"):
        raise KitYamlError("anchors and aliases are not supported", path, line_no)

    comment_at = _find_comment(text)
    if comment_at is not None:
        text = text[:comment_at].rstrip()

    if text in ("null", "~", ""):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if _INT_RE.match(text):
        return int(text)
    return text


def _find_comment(text):
    for idx, ch in enumerate(text):
        if ch == "#" and (idx == 0 or text[idx - 1] in " \t"):
            return idx
    return None


def _unescape_double(text):
    return (
        text.replace('\\"', '"')
        .replace("\\\\", "\\")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
    )
