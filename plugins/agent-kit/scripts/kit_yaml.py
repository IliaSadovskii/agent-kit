"""A reader for the YAML subset the kit's machine-owned files are written in.

Nothing the kit ships may import a third-party module: a hook that dies on `ImportError` on
someone else's machine takes the whole kit down with it. PyYAML is therefore not available, and
this is the reader the kit's scripts share instead.

The subset is defined by what those files actually use — nested maps by indentation, lists of
scalars and lists of maps, plain and quoted scalars, `null` / `true` / `false` / numbers, comments,
literal and folded block scalars (`|`, `>`, `|-`, `>-`), and the empty flow collections `[]` and
`{}`. Anything outside it raises KitYamlError naming the construct and the line, so a caller can
say what it does not understand instead of guessing at a value.
"""
import re

__all__ = ["KitYamlError", "dump", "key", "load", "load_path", "scalar"]

_KEY = re.compile(r"^(?P<key>[A-Za-z0-9_.\-]+|\"[^\"]*\"|'[^']*'):(?:\s+(?P<rest>.*))?$")
_PLAIN_KEY = re.compile(r"^[A-Za-z0-9_.\-]+$")
# No leading zeros, which is JSON's number grammar and the reading a person expects: `007` is a
# string. It also matters mechanically — a section hash is twelve hex characters, and roughly one
# in sixteen hundred is all digits with a leading zero. Read as a number it comes back short, so
# the slot it belongs to could never match its own hash again.
_INT = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
_FLOAT = re.compile(r"^[+-]?(?:(?:0|[1-9][0-9]*)\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
_BLOCK = re.compile(r"^(?P<style>[|>])(?P<chomp>[+-]?)$")


class KitYamlError(Exception):
    """Something outside the subset, reported by name and line rather than guessed at."""

    def __init__(self, message, line):
        super().__init__(f"line {line}: {message}")
        self.message = message
        self.line = line


class _Line:
    __slots__ = ("indent", "content", "number")

    def __init__(self, indent, content, number):
        self.indent = indent
        self.content = content
        self.number = number


def _strip_comment(text):
    """Cut a trailing comment, leaving `#` inside a value alone.

    A `source:` value is `docs/developing.md#What must never end up in the plugin`. A reader that
    treats every `#` as a comment eats the binding, so `#` opens a comment only at the start of a
    line or after whitespace — which is YAML's own rule.

    A quote opens a quoted scalar under that same rule. Mid-word it is just a character, or the
    apostrophe in `criterion: the owner's own rules` would open a quote that never closes and the
    comment after it would be read as part of the value.
    """
    quote = ""
    for i, ch in enumerate(text):
        opens = i == 0 or text[i - 1] in " \t"
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'" and opens:
            quote = ch
        elif ch == "#" and opens:
            return text[:i]
    return text


class _Reader:
    def __init__(self, text):
        self._raw = text.splitlines()
        self._i = 0
        self._pending = None

    # -- line access -------------------------------------------------------------------------
    def _peek(self):
        """The next significant line, or None at end of input. Comments and blanks are skipped."""
        if self._pending is not None:
            return self._pending
        while self._i < len(self._raw):
            raw = self._raw[self._i]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self._i += 1
                continue
            indent = len(raw) - len(raw.lstrip(" \t"))
            if "\t" in raw[:indent]:
                raise KitYamlError("tab used for indentation", self._i + 1)
            if stripped in ("---", "..."):
                raise KitYamlError("multiple documents are outside the subset", self._i + 1)
            content = _strip_comment(raw[indent:]).rstrip()
            if not content:
                self._i += 1
                continue
            return _Line(indent, content, self._i + 1)
        return None

    def _advance(self):
        if self._pending is not None:
            self._pending = None
        else:
            self._i += 1

    def _push(self, line):
        self._pending = line

    # -- blocks ------------------------------------------------------------------------------
    def parse_document(self):
        line = self._peek()
        if line is None:
            return None
        if line.indent != 0:
            raise KitYamlError("the document starts with an indented line", line.number)
        return self._parse_seq(0) if self._is_item(line) else self._parse_map(0)

    @staticmethod
    def _is_item(line):
        return line.content == "-" or line.content.startswith("- ")

    def _parse_nested(self, parent_indent):
        """The block belonging to a key that had no inline value, or None when there is none."""
        line = self._peek()
        if line is None or line.indent <= parent_indent:
            return None
        return self._parse_seq(line.indent) if self._is_item(line) else self._parse_map(line.indent)

    def _parse_map(self, indent):
        result = {}
        while True:
            line = self._peek()
            if line is None or line.indent < indent:
                return result
            if line.indent > indent:
                raise KitYamlError("unexpected indentation", line.number)
            if self._is_item(line):
                raise KitYamlError("a list item where a `key: value` was expected", line.number)
            match = _KEY.match(line.content)
            if not match:
                raise KitYamlError(f"expected `key: value`, found {line.content!r}", line.number)
            key = match.group("key").strip("\"'")
            rest = (match.group("rest") or "").strip()
            self._advance()
            if key in result:
                raise KitYamlError(f"duplicate key {key!r}", line.number)
            result[key] = self._value_after_key(rest, indent, line.number)

    def _value_after_key(self, rest, indent, number):
        block = _BLOCK.match(rest) if rest else None
        if block:
            return self._read_block_scalar(indent, block.group("style"), block.group("chomp"),
                                           number)
        if rest:
            return _scalar(rest, number)
        following = self._peek()
        # A list may sit at its key's own indentation, which is legal YAML and how a hand-edited
        # file often comes back. Anything else has to be indented under the key.
        if following is not None and following.indent == indent and self._is_item(following):
            return self._parse_seq(indent)
        return self._parse_nested(indent)

    def _parse_seq(self, indent):
        items = []
        while True:
            line = self._peek()
            if line is None or line.indent < indent or not self._is_item(line):
                return items
            if line.indent > indent:
                raise KitYamlError("unexpected indentation", line.number)
            rest = line.content[1:].strip()
            self._advance()
            if not rest:
                items.append(self._parse_nested(indent))
                continue
            block = _BLOCK.match(rest)
            if block:
                items.append(self._read_block_scalar(indent, block.group("style"),
                                                     block.group("chomp"), line.number))
                continue
            if _KEY.match(rest):
                # `- key: value` opens a map whose first key is on the dash's own line; the rest of
                # it is indented to where that key starts.
                inner = indent + (len(line.content) - len(line.content[1:].lstrip()))
                self._push(_Line(inner, rest, line.number))
                items.append(self._parse_map(inner))
                continue
            items.append(_scalar(rest, line.number))

    def _read_block_scalar(self, indent, style, chomp, number):
        """Consume the raw lines of a `|` or `>` scalar; comments and blanks inside it are text."""
        if chomp == "+":
            raise KitYamlError("keep chomping (`|+`, `>+`) is outside the subset", number)
        if self._pending is not None:
            raise KitYamlError("a block scalar inside a list item's first key is outside the "
                               "subset", self._pending.number)
        body, content_indent = [], None
        while self._i < len(self._raw):
            raw = self._raw[self._i]
            if raw.strip():
                line_indent = len(raw) - len(raw.lstrip(" "))
                if line_indent <= indent:
                    break
                if content_indent is None:
                    content_indent = line_indent
                # A line indented less than the block's own content but more than the key that
                # owns it is a slip, and swallowing it is the worst possible answer: a `status:`
                # line one space short of its neighbours would disappear into the prose above it
                # and the slot would keep the verdict the owner thought they had changed.
                if line_indent < content_indent:
                    raise KitYamlError("this line is indented less than the block scalar it "
                                       "would belong to", self._i + 1)
                body.append(raw[content_indent:])
            else:
                body.append("")
            self._i += 1
        while body and not body[-1]:
            body.pop()
        if style == "|":
            text = "\n".join(body)
        else:
            folded, previous_blank = [], False
            for piece in body:
                if not piece:
                    folded.append("\n")
                    previous_blank = True
                elif folded and not previous_blank:
                    folded.append(" " + piece)
                else:
                    folded.append(piece)
                    previous_blank = False
            text = "".join(folded)
        if chomp == "-":
            return text
        return text + "\n" if text else text


def _scalar(text, number):
    if text.startswith('"'):
        if len(text) < 2 or not text.endswith('"'):
            raise KitYamlError("unterminated double-quoted scalar", number)
        return _unescape(text[1:-1], number)
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise KitYamlError("unterminated single-quoted scalar", number)
        return text[1:-1].replace("''", "'")
    if text in ("[]", "{}"):
        return [] if text == "[]" else {}
    if text[0] in "[{":
        raise KitYamlError("flow collections are outside the subset (only `[]` and `{}`)", number)
    # `|` and `>` are indicators, never the first character of a plain scalar — so reaching here
    # means a block scalar header the subset does not cover, `|2` and its explicit indentation
    # indicator being the likely one. Reading it as the two-character string `"|2"` is a guess.
    if text[0] in "|>":
        raise KitYamlError(f"block scalar header {text!r} is outside the subset "
                           "(only `|`, `>`, `|-`, `>-`)", number)
    if text[0] in "&*!":
        raise KitYamlError(f"{'anchors' if text[0] == '&' else 'aliases' if text[0] == '*' else 'tags'}"
                           " are outside the subset", number)
    if text in ("null", "Null", "NULL", "~"):
        return None
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if _INT.match(text):
        return int(text)
    if _FLOAT.match(text):
        return float(text)
    return text


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "0": "\0"}


def _unescape(text, number):
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            if text[i + 1] not in _ESCAPES:
                # Dropping the backslash would turn `"C:\Users"` into `C:Users` without a word.
                # A path with a backslash in it belongs in single quotes or in a plain scalar.
                raise KitYamlError(f"unknown escape {text[i:i + 2]!r} in a double-quoted scalar",
                                   number)
            out.append(_ESCAPES[text[i + 1]])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def load(text):
    """Parse a document written in the subset. Raises KitYamlError on anything outside it."""
    return _Reader(text).parse_document()


def load_path(path):
    with open(path, encoding="utf-8") as handle:
        return load(handle.read())


# ----------------------------------------------------------------------------------------------
# The writer. Only machine-owned files are written this way: the knowledge index is derived and
# regenerable, so it has no comments to preserve. A file a person maintains — the contract, the
# manifest — is edited in place instead, because no dumper keeps the prose around the values.


def _quoted(text, quote):
    """`text` in single or double quotes, escaped as the reader unescapes it."""
    if quote == "'":
        return "'" + text.replace("'", "''") + "'"
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    for raw, code in (("\n", "\\n"), ("\t", "\\t"), ("\r", "\\r"), ("\0", "\\0")):
        escaped = escaped.replace(raw, code)
    return '"' + escaped + '"'


def _render_scalar(value, where):
    """One line's worth of value. Plain where that reads back unchanged, quoted where it would not.

    Plain is tried first because these files are read by people. The candidates are ordered by how
    much they cost the reader, and `dump` proves the choice by parsing the result — so a value that
    would come back as something else is a loud error rather than a quiet corruption.
    """
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        rendered = repr(value)
        if not _FLOAT.match(rendered):
            raise KitYamlError(f"{where}: {value!r} has no plain form in the subset", 0)
        return rendered
    if isinstance(value, str):
        if value and "\n" not in value and value == value.strip():
            try:
                if _strip_comment(value).rstrip() == value and _scalar(value, 0) == value:
                    return value
            except KitYamlError:
                pass
        # A `#` after a `"` inside a double-quoted scalar reads as a comment, because the reader
        # cannot tell the escaped quote from a closing one. Single quotes have no escapes to be
        # confused by, so they are tried before double.
        if "\n" not in value and "\r" not in value and "\t" not in value:
            return _quoted(value, "'")
        return _quoted(value, '"')
    raise KitYamlError(f"{where}: {type(value).__name__} is outside the subset", 0)


def _render_key(key, where):
    if not isinstance(key, str):
        raise KitYamlError(f"{where}: a key must be a string, not {type(key).__name__}", 0)
    return key if _PLAIN_KEY.match(key) else _quoted(key, '"')


def _render_map(mapping, indent, lines, where):
    pad = " " * indent
    for key, value in mapping.items():
        rendered = _render_key(key, where)
        _render_value(f"{pad}{rendered}:", value, indent, lines, f"{where}/{key}")


def _render_seq(items, indent, lines, where):
    pad = " " * indent
    for position, item in enumerate(items):
        _render_value(f"{pad}-", item, indent, lines, f"{where}[{position}]")


def _render_value(opening, value, indent, lines, where):
    """Emit `opening` — a key or a dash — followed by `value`, inline or as an indented block."""
    if isinstance(value, dict):
        if not value:
            lines.append(f"{opening} {{}}")
            return
        lines.append(opening)
        _render_map(value, indent + 2, lines, where)
    elif isinstance(value, list):
        if not value:
            lines.append(f"{opening} []")
            return
        lines.append(opening)
        _render_seq(value, indent + 2, lines, where)
    else:
        lines.append(f"{opening} {_render_scalar(value, where)}".rstrip())


def key(name):
    """One mapping key, quoted only where a plain one would not read back as itself.

    Proved by re-reading, because the reader takes a key back differently from a value: it strips
    the surrounding quotes and stops there, with no unescaping. A key holding a backslash or a tab
    would come back as the escape sequence rather than the character — silently, and the entry it
    identifies would be permanently unbound. A key the subset cannot hold is an error with a name.
    """
    rendered = _render_key(name, "")
    if load(f"{rendered}: 0") != {name: 0}:
        raise KitYamlError(f"{name!r} has no form the reader takes back as itself; a key is plain "
                           "text without a backslash, a tab, or a quote", 0)
    return rendered


def scalar(value):
    """One value, quoted only where a plain one would not read back as itself.

    Exported because the index is not the only file the kit writes: the contract's `entries:` block
    is edited in place, line by line, and a second quoting rule written beside this one would be a
    second set of bugs. `_strip_comment`'s reading of `#` after a tab is the kind of detail the
    duplicate got wrong.
    """
    return _render_scalar(value, "")


def dump(data):
    """Render a mapping in the subset `load` reads, and prove it by reading the result back.

    The proof is the point. A writer that renders a value the reader then takes for something else
    is the exact failure the whole contract exists to prevent — a hash that comes back as a number,
    a `#` eaten as a comment — and it is invisible until a check reports a file it wrote as wrong.
    """
    if not isinstance(data, dict):
        raise KitYamlError("a kit document is a mapping at the top level", 0)
    if not data:
        # An empty file reads back as None, not as an empty mapping, so there is nothing to write
        # that would round-trip. Every file the kit writes carries `version:` anyway.
        raise KitYamlError("an empty mapping has no form in the subset — a kit document carries at "
                           "least `version`", 0)
    lines = []
    _render_map(data, 0, lines, "")
    text = "".join(line + "\n" for line in lines)
    if load(text) != data:
        raise KitYamlError("this structure does not survive a round trip through the subset", 0)
    return text
