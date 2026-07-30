#!/usr/bin/env python3
"""A reader for the YAML subset the kit's machine-owned files are written in.

Nothing the kit ships may import a third-party module: a hook that dies on `ImportError` on
someone else's machine takes the whole kit down with it. PyYAML is therefore not available, and
this is the reader the kit's scripts share instead.

The subset is defined by what those files actually use — nested maps by indentation, lists of
scalars and lists of maps, plain and quoted scalars, `null` / `true` / `false` / numbers, comments,
block scalars, and the empty flow collections `[]` and `{}`. Anything outside it raises KitYamlError
naming the construct and the line, so a caller can say what it does not understand instead of
guessing at a value.
"""
import re

__all__ = ["KitYamlError", "load", "load_path"]

_KEY = re.compile(r"^(?P<key>[A-Za-z0-9_.\-]+|\"[^\"]*\"|'[^']*'):(?:\s+(?P<rest>.*))?$")
_INT = re.compile(r"^[+-]?[0-9]+$")
_FLOAT = re.compile(r"^[+-]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
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
    """
    quote = ""
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
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
            return self._read_block_scalar(indent, block.group("style"), block.group("chomp"))
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
                items.append(
                    self._read_block_scalar(indent, block.group("style"), block.group("chomp")))
                continue
            if _KEY.match(rest):
                # `- key: value` opens a map whose first key is on the dash's own line; the rest of
                # it is indented to where that key starts.
                inner = indent + (len(line.content) - len(line.content[1:].lstrip()))
                self._push(_Line(inner, rest, line.number))
                items.append(self._parse_map(inner))
                continue
            items.append(_scalar(rest, line.number))

    def _read_block_scalar(self, indent, style, chomp):
        """Consume the raw lines of a `|` or `>` scalar; comments and blanks inside it are text."""
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
                body.append(raw[content_indent:] if line_indent >= content_indent else raw.strip())
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
        return _unescape(text[1:-1])
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise KitYamlError("unterminated single-quoted scalar", number)
        return text[1:-1].replace("''", "'")
    if text in ("[]", "{}"):
        return [] if text == "[]" else {}
    if text[0] in "[{":
        raise KitYamlError("flow collections are outside the subset (only `[]` and `{}`)", number)
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


def _unescape(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            out.append(_ESCAPES.get(text[i + 1], text[i + 1]))
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
