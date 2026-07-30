"""The knowledge layer's shared machinery: sections, anchors, entries, the index, the cross-checks.

Stage 1 made a project's *slots* checkable. This is what makes its *instances* checkable — the
collections a contract enumerates, each entry bound to a piece of the owner's own prose, each parsed
once and cached against that section's hash, and then compared against each other.

Three callers share it: `blueprint_check.py` reads entries and reports on them without ever calling
a grader, `blueprint_index.py` spends the grader calls and writes the index, and the tests drive
both. Nothing here calls a model, runs a command, or asks a question; a check that a later stage
puts in front of every build command has to stay mechanical to stay cheap.

A binding is stage 1's `path#…` grammar with one addition: a fragment beginning `kit:` names an
anchor — `<!-- kit: <key> -->` on its own line — and anything else is a heading's literal text. The
anchor survives a heading rename, which is the whole reason it exists.
"""
import glob
import hashlib
import os
import re

import kit_yaml

INDEX_PATH = os.path.join(".agent-kit", "knowledge", "index.yml")
MANIFEST_PATH = os.path.join(".agent-kit", "project", "manifest.yml")
DEFAULT_SCREEN_MAP = os.path.join("docs", "screens", "screens.data.js")

COLLECTION_SLOTS = ("actors", "entities", "actions", "screens", "integrations")

# The facts a grader fills, per collection. The cross-checks are key comparisons, so the keys have
# to be fixed; anything else a grader volunteers is kept in the index and ignored, because a check
# that silently depends on a key nobody declared should not exist.
FACTS = {
    "actors": ("kind", "actions"),
    "entities": ("states", "created_by", "closed_by", "relations"),
    "actions": ("actor", "trigger", "entities_written", "statuses_set", "reads", "screens"),
    "screens": ("screen",),
    "integrations": ("direction", "absent"),
}

# Which fact names an instance of which other collection, and how the value reads: a single key,
# a list of keys, or a list of `entity.state` pairs whose first half is the key.
REFERENCES = (
    ("actions", "actor", "actors", "one"),
    ("actions", "entities_written", "entities", "many"),
    ("actions", "reads", "entities", "many"),
    ("actions", "statuses_set", "entities", "qualified"),
    ("actors", "actions", "actions", "many"),
    ("entities", "created_by", "actions", "many"),
    ("entities", "closed_by", "actions", "many"),
)

ANCHOR_PREFIX = "kit:"
_ANCHOR = re.compile(r"^[ \t]*<!--[ \t]*kit:[ \t]*(?P<key>\S+?)[ \t]*-->[ \t]*$")

# A closing run of `#` is only a closing sequence when a space precedes it, so a heading may end in
# one: `## Why C#` is titled "Why C#", and a slot bound to it must resolve.
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
# The whole run, not the first three characters: a document that shows how to write a code fence
# nests a ``` inside a ````, and a closer shorter than its opener does not close it. Reading it as
# one would end the fence early and turn the example's own `#` lines into headings.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")

_SCREEN_ID = re.compile(r"\bid\s*:\s*['\"](S\d+)['\"]")
_SCREEN_STATUS = re.compile(r"\bstatus\s*:\s*['\"](\w+)['\"]")


class SectionError(Exception):
    """A binding that cannot be resolved: the heading or anchor is missing, or it is not unique.

    `structural` separates "this instance drifted" from "this contract cannot be read". A renamed
    heading under one entry of twenty-three leaves the other twenty-two checkable; a document that
    is gone, a binding that reaches outside the project, and a binding that resolves to two places
    do not.
    """

    def __init__(self, message, structural=False):
        super().__init__(message)
        self.structural = structural


# ----------------------------------------------------------------------------------------------
# Sections — the resolver every verdict in the layer is computed from


def inside(root, path):
    """Resolve `path` under `root`, or None when it points outside the project.

    A contract can arrive in a pull request, and a binding is a path out of it. `os.path.join`
    hands the whole result to an absolute path, `..` walks up, and a symlink does it without
    either — so the answer is the resolved path compared against the resolved root, not the string.
    """
    resolved = os.path.realpath(os.path.join(root, path))
    base = os.path.realpath(root)
    return resolved if os.path.commonpath([resolved, base]) == base else None


def _unfenced(text):
    """(line index, line) for every line outside a code fence."""
    fence = None
    for index, line in enumerate(text.splitlines()):
        marker = _FENCE.match(line)
        if marker:
            closer = marker.group(1)
            if fence is None:
                fence = closer
            elif closer[0] == fence[0] and len(closer) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield index, line


def headings(text):
    """Every ATX heading as (level, title, line index), ignoring anything inside a code fence."""
    found = []
    for index, line in _unfenced(text):
        match = _HEADING.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2).strip(), index))
    return found


def anchors(text):
    """Every `<!-- kit: key -->` as {key: [line index, …]}, ignoring anything inside a code fence.

    A document that explains the convention writes the anchor inside a fence; reading that as a
    binding would point an entry at the paragraph describing anchors.
    """
    found = {}
    for index, line in _unfenced(text):
        match = _ANCHOR.match(line)
        if match:
            found.setdefault(match.group("key"), []).append(index)
    return found


def _body(text, all_headings, level, start):
    """The text between the heading at line `start` and the next heading of `level` or shallower.

    Line endings are normalized, so a CRLF checkout does not make every binding stale; nothing else
    is. Whitespace inside the section is part of it — the hash is meant to notice edits, and an edit
    that only moved whitespace is still an edit the owner made.

    Each line keeps its terminator, which is what the file has. Joining without one would make a
    section holding a single blank line and a section holding nothing the same text, and an edit
    between the two would be the one edit the hash could not see.

    An anchor line is dropped: it is the kit's own marker, not the owner's prose. Counting it would
    make the placement flow invalidate every entry it had just bound, so adopting anchors would cost
    a second full parse of the whole corpus for a change that added no information. One inside a
    code fence is prose about anchors and stays.
    """
    lines = text.splitlines()
    end = len(lines)
    for other_level, _, other_start in all_headings:
        if other_start > start and other_level <= level:
            end = other_start
            break
    marked = {line for places in anchors(text).values() for line in places}
    body = [line for number, line in enumerate(lines[start + 1:end], start + 1)
            if number not in marked]
    return "\n".join(body) + "\n" if body else ""


def section_body(text, heading):
    """The section a `path#heading` binding names."""
    all_headings = headings(text)
    matches = [h for h in all_headings if h[1] == heading]
    if not matches:
        raise SectionError(f"no heading {heading!r}")
    if len(matches) > 1:
        lines = ", ".join(f"line {h[2] + 1}" for h in matches)
        raise SectionError(f"heading {heading!r} is not unique ({lines})", structural=True)
    level, _, start = matches[0]
    return _body(text, all_headings, level, start)


def anchor_section(text, key):
    """The section a `path#kit:key` binding names, as (body, heading line index or None).

    The bound section is the one the anchor sits in: the nearest heading at or above it, and the
    body runs to the next heading of that level or shallower. An anchor above the first heading
    binds the document's preamble, which is the only sensible reading of a file whose first entry
    is stated before any heading.
    """
    places = anchors(text).get(key, [])
    if not places:
        raise SectionError(f"no anchor `<!-- {ANCHOR_PREFIX} {key} -->`")
    if len(places) > 1:
        where = ", ".join(f"line {line + 1}" for line in places)
        raise SectionError(f"anchor {key!r} is not unique ({where})", structural=True)
    at = places[0]
    all_headings = headings(text)
    owning = [h for h in all_headings if h[2] < at]
    if not owning:
        end = all_headings[0][2] if all_headings else len(text.splitlines())
        preamble = text.splitlines()[:end]
        return ("\n".join(preamble) + "\n" if preamble else ""), None
    level, _, start = owning[-1]
    return _body(text, all_headings, level, start), start


def section_rev(text, heading):
    return rev_of(section_body(text, heading))


def rev_of(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


# ----------------------------------------------------------------------------------------------
# Bindings and entries


def split_binding(at):
    """`path#fragment` as (path, kind, target). Raises SectionError when it names no section."""
    path, sep, fragment = str(at).partition("#")
    if not sep or not fragment:
        raise SectionError(f"binding {at!r} names no section — the form is path#heading "
                           f"or path#{ANCHOR_PREFIX}<key>", structural=True)
    if fragment.startswith(ANCHOR_PREFIX):
        return path, "anchor", fragment[len(ANCHOR_PREFIX):].strip()
    return path, "heading", fragment


def read_document(root, path):
    """The text of a document a binding names. Raises SectionError with the reason it cannot be."""
    full = inside(root, path)
    if full is None:
        raise SectionError("binding points outside the project; it names a document in this "
                           "repository", structural=True)
    if not os.path.isfile(full):
        raise SectionError(f"source file is gone: {path}", structural=True)
    try:
        with open(full, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise SectionError(f"{path}: {exc}", structural=True)


def resolve(root, at, text=None):
    """Resolve a binding to {path, kind, target, line, body, rev}. Raises SectionError."""
    path, kind, target = split_binding(at)
    if text is None:
        text = read_document(root, path)
    if kind == "anchor":
        body, line = anchor_section(text, target)
    else:
        body, line = section_body(text, target), None
        for level, title, start in headings(text):
            if title == target:
                line = start
                break
    return {"path": path, "kind": kind, "target": target,
            "line": None if line is None else line + 1, "body": body, "rev": rev_of(body)}


def entry_bindings(contract):
    """{collection: {key: at}} for every collection the contract records entries for."""
    found = {}
    collections = contract.get("collections") or {}
    if not isinstance(collections, dict):
        return found
    for name in COLLECTION_SLOTS:
        slot = collections.get(name)
        if not isinstance(slot, dict):
            continue
        entries = slot.get("entries")
        if not isinstance(entries, dict) or not entries:
            continue
        bound = {}
        for key, entry in entries.items():
            if isinstance(entry, dict):
                bound[str(key)] = entry.get("at")
            else:
                bound[str(key)] = entry
        found[name] = bound
    return found


# ----------------------------------------------------------------------------------------------
# The derived index


def load_index(root):
    """The committed index, or an empty one. A malformed index raises KitYamlError to its caller."""
    path = os.path.join(root, INDEX_PATH)
    if not os.path.isfile(path):
        return {"version": 1}
    index = kit_yaml.load_path(path)
    if not isinstance(index, dict):
        raise kit_yaml.KitYamlError("the index is not a mapping", 0)
    return index


def write_index(root, index):
    path = os.path.join(root, INDEX_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(INDEX_HEADER)
        handle.write(kit_yaml.dump(index))
    return path


INDEX_HEADER = """\
# Derived by /agent-kit:blueprint --index. Do not edit by hand — the next run rewrites it.
#
# One entry per instance the contract enumerates: where its prose lives, the hash of that section
# when it was last parsed, the structural facts a grader extracted from it, and what the entry does
# not answer. `rev` is the cache: an entry whose section still hashes to it is not parsed again.
#
# Committed on purpose. It is derived, but derived by dozens of grader calls, and a clone, a CI run
# and a headless run should inherit the cache rather than pay for it a second time.

"""


def entry_state(root, contract, index):
    """Every entry the contract records, with what the index knows about it.

    Returns a list of dicts: collection, key, at, and either a resolution (`path`, `line`, `rev`,
    `body`) or `error`, plus `recorded` — the rev in the index — and `stale`.
    """
    state = []
    documents = {}
    for collection, bound in entry_bindings(contract).items():
        recorded_entries = index.get(collection) if isinstance(index.get(collection), dict) else {}
        for key, at in bound.items():
            item = {"collection": collection, "key": key, "at": at, "kind": None, "error": None,
                    "recorded": None, "gaps": [], "stale": True, "resolved": None}
            recorded = recorded_entries.get(key)
            if isinstance(recorded, dict):
                # `str`, because roughly one hash in two hundred is all digits and reads back as an
                # int — which would never equal its own hexdigest.
                item["recorded"] = str(recorded.get("rev") or "") or None
                item["gaps"] = [str(gap) for gap in (recorded.get("gaps") or [])]
            state.append(item)
            if at is None:
                item["error"] = SectionError("no binding recorded — an entry says where its prose "
                                             "lives", structural=True)
                continue
            try:
                path, kind, _ = split_binding(at)
                item["kind"] = kind
                if path not in documents:
                    documents[path] = read_document(root, path)
                item["resolved"] = resolve(root, at, documents[path])
            except SectionError as exc:
                item["error"] = exc
                continue
            item["stale"] = item["recorded"] != item["resolved"]["rev"]
    return state


def plan(root, contract, index):
    """The grader calls that need making: one per document, carrying only its stale sections.

    First parse of a document is one call. Editing one section of it later is one call carrying that
    one section, because the cache is per section and the grouping is per document — one code path,
    both properties.
    """
    groups = {}
    for item in entry_state(root, contract, index):
        if item["error"] or not item["stale"]:
            continue
        resolved = item["resolved"]
        groups.setdefault(resolved["path"], []).append({
            "collection": item["collection"],
            "key": item["key"],
            "at": item["at"],
            "line": resolved["line"],
            "rev": resolved["rev"],
            "text": resolved["body"],
        })
    return [{"document": path, "entries": groups[path]} for path in sorted(groups)]


def apply_results(root, contract, index, results):
    """Merge grader results into the index, and drop entries the contract no longer lists.

    Each result is {collection, key, facts, gaps}. The rev is recomputed from the file here rather
    than taken from the plan: a document edited while the grader was running must come back stale
    on the next check, not be recorded as parsed.
    """
    bound = entry_bindings(contract)
    merged = {"version": index.get("version", 1)}
    by_key = {}
    for result in results:
        collection, key = result.get("collection"), result.get("key")
        if collection not in bound or key not in bound[collection]:
            raise ValueError(f"{collection}/{key} is not an entry this contract records")
        by_key[(collection, key)] = result

    for item in entry_state(root, contract, index):
        collection, key = item["collection"], item["key"]
        result = by_key.get((collection, key))
        recorded = (index.get(collection) or {}).get(key)
        if result is None:
            if isinstance(recorded, dict):
                merged.setdefault(collection, {})[key] = recorded
            continue
        if item["error"]:
            raise ValueError(f"{collection}/{key}: {item['error']}")
        resolved = item["resolved"]
        merged.setdefault(collection, {})[key] = {
            "at": item["at"],
            "line": resolved["line"],
            "rev": resolved["rev"],
            "facts": _clean_facts(result.get("facts")),
            "gaps": [str(gap) for gap in (result.get("gaps") or [])],
        }
    return merged


def _clean_facts(facts):
    """Whatever the grader returned, in a shape the writer and the checks can both read."""
    if not isinstance(facts, dict):
        return {}
    clean = {}
    for key, value in facts.items():
        if isinstance(value, list):
            clean[str(key)] = [str(item) for item in value]
        elif isinstance(value, (dict, type(None))):
            continue
        else:
            clean[str(key)] = value if isinstance(value, (int, float, bool)) else str(value)
    return clean


def refresh(root, contract, grader):
    """plan → grade → apply. Returns (index, calls made).

    The grader is a callable taking one group from `plan` and returning its results. The script
    cannot call a model — it is stdlib Python — so in a real run the agent is the grader and drives
    the two halves through the CLI. Here it is one function, which is what lets a test count the
    calls instead of arguing about them.
    """
    index = load_index(root)
    groups = plan(root, contract, index)
    results = []
    for group in groups:
        results.extend(grader(group) or [])
    return apply_results(root, contract, index, results), len(groups)


# ----------------------------------------------------------------------------------------------
# The screen map — the authority for screens, read rather than duplicated


def screen_map_path(root):
    """Where this project's map is: the manifest's `sources.screens`, or the conventional path."""
    manifest = os.path.join(root, MANIFEST_PATH)
    if os.path.isfile(manifest):
        try:
            recorded = (kit_yaml.load_path(manifest) or {}).get("sources") or {}
        except (kit_yaml.KitYamlError, OSError, UnicodeDecodeError):
            recorded = {}
        named = recorded.get("screens") if isinstance(recorded, dict) else None
        if named and inside(root, str(named)) and os.path.isfile(inside(root, str(named))):
            return str(named)
    if os.path.isfile(os.path.join(root, DEFAULT_SCREEN_MAP)):
        return DEFAULT_SCREEN_MAP
    return None


def screen_ids(root):
    """{id: status} from the screen map, or None when the project has no map.

    The map is JavaScript, and the kit ships no engine to run it. Ids and statuses are read with a
    pattern instead — enough to validate a reference, and it says None rather than an empty answer
    when there is no map, so "no map" never reads as "no screens".
    """
    path = screen_map_path(root)
    if path is None:
        return None
    full = inside(root, path)
    try:
        with open(full, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError, TypeError):
        return None
    found = {}
    matches = list(_SCREEN_ID.finditer(text))
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        status = _SCREEN_STATUS.search(text, match.end(), end)
        found[match.group(1)] = status.group(1) if status else "unknown"
    return found


# ----------------------------------------------------------------------------------------------
# The cross-checks — key comparisons, which is what makes them cheap and exact


def _listed(facts, name, shape):
    """The instance keys a fact refers to."""
    value = facts.get(name)
    if value is None:
        return []
    if shape == "one":
        return [str(value)] if str(value).strip() else []
    if not isinstance(value, list):
        return [str(value)]
    if shape == "qualified":
        return [str(item).partition(".")[0] for item in value if str(item).strip()]
    return [str(item) for item in value if str(item).strip()]


def _facts(index, collection, key):
    entry = (index.get(collection) or {}).get(key)
    return entry.get("facts") or {} if isinstance(entry, dict) else {}


def cross_check(index, screens=None):
    """Every finding the index's own keys can prove, as (where, message).

    Set completeness runs first and the rest skip a key it has already reported: a document that
    never described `deal` should produce one finding, not four.

    A collection with no entries is not an authority. A project whose `actors` slot is
    `not_applicable` has no access model to check against, and reporting every action's actor as
    missing would drown the findings that mean something.
    """
    findings = []
    present = {name: set((index.get(name) or {}) if isinstance(index.get(name), dict) else {})
               for name in COLLECTION_SLOTS}
    unknown = set()

    for collection, fact, target, shape in REFERENCES:
        if not present[target]:
            continue
        for key in sorted(present[collection]):
            for referenced in _listed(_facts(index, collection, key), fact, shape):
                if referenced in present[target]:
                    continue
                unknown.add((target, referenced))
                findings.append((f"{collection}/{key}",
                                 f"names {target}/{referenced}, which no entry describes"))

    findings += _check_statuses(index, present, unknown)
    findings += _check_rights(index, present, unknown)
    findings += _check_screens(index, present, screens)
    findings += _check_lifecycle(index, present, unknown)
    return findings


def _check_statuses(index, present, unknown):
    """A status an action sets exists in that entity's lifecycle."""
    findings = []
    for key in sorted(present["actions"]):
        facts = _facts(index, "actions", key)
        for pair in _listed(facts, "statuses_set", "many"):
            entity, dot, state = pair.partition(".")
            if not dot:
                findings.append((f"actions/{key}",
                                 f"sets {pair!r} — a status reads entity.state, so the entity it "
                                 "belongs to cannot be checked"))
                continue
            if entity not in present["entities"] or ("entities", entity) in unknown:
                continue
            states = _listed(_facts(index, "entities", entity), "states", "many")
            if state not in states:
                listed = ", ".join(states) if states else "none recorded"
                findings.append((f"actions/{key}",
                                 f"sets {entity}.{state} — no `{state}` state in entities/{entity}"
                                 f"\n  (states are: {listed})"))
    return findings


def _check_rights(index, present, unknown):
    """An action available to an actor is one that actor has the right to, and vice versa."""
    findings = []
    if not present["actors"] or not present["actions"]:
        return findings
    attributed = set()
    for key in sorted(present["actions"]):
        actor = (_listed(_facts(index, "actions", key), "actor", "one") or [None])[0]
        if actor is None:
            findings.append((f"actions/{key}", "no actor initiates it — every action has an "
                                               "initiator, even if it is the product itself"))
            continue
        attributed.add(actor)
        if actor not in present["actors"] or ("actors", actor) in unknown:
            continue
        if key not in _listed(_facts(index, "actors", actor), "actions", "many"):
            findings.append((f"actions/{key}",
                             f"attributed to actors/{actor}, which does not list it among the "
                             "actions it may perform"))
    for actor in sorted(present["actors"] - attributed):
        findings.append((f"actors/{actor}", "declared, but no action is attributed to it"))
    return findings


def _check_screens(index, present, screens):
    """A screen an action names is on the map, and a screen on the map is reached by some action."""
    findings = []
    if screens is None:
        return findings
    reached = set()
    for key in sorted(present["actions"]):
        for screen in _listed(_facts(index, "actions", key), "screens", "many"):
            reached.add(screen)
            if screen not in screens:
                findings.append((f"actions/{key}",
                                 f"launches from {screen}, which is not on the screen map"))
    if not present["actions"]:
        return findings
    for screen in sorted(set(screens) - reached):
        # A rejected screen is the owner's own decision not to have it; an idea is not yet a
        # promise. Neither is expected to be reachable.
        if screens[screen] in ("rejected", "idea"):
            continue
        findings.append((f"screens/{screen}",
                         "on the map, and no action is launched from it"))
    return findings


def _check_lifecycle(index, present, unknown):
    """An entity the product writes has an action that creates it and one that closes it."""
    findings = []
    if not present["entities"] or not present["actions"]:
        return findings
    written = set()
    for key in sorted(present["actions"]):
        written.update(_listed(_facts(index, "actions", key), "entities_written", "many"))
    for entity in sorted(present["entities"] & written):
        facts = _facts(index, "entities", entity)
        if not _listed(facts, "created_by", "many"):
            findings.append((f"entities/{entity}",
                             "no action creates it — is it a reference book maintained by hand?"))
        if not _listed(facts, "closed_by", "many"):
            findings.append((f"entities/{entity}",
                             "no action closes it — every state machine needs a way out"))
    return findings


# ----------------------------------------------------------------------------------------------
# Writing anchors, and recording the entries they bind


def place_anchor(text, key, heading):
    """`text` with `<!-- kit: key -->` on its own line under `heading`. Idempotent.

    The script writes the anchor rather than the agent, so "on its own line" is a property of the
    code and not of the agent's care.
    """
    existing = anchors(text).get(key, [])
    if len(existing) > 1:
        where = ", ".join(f"line {line + 1}" for line in existing)
        raise SectionError(f"anchor {key!r} is already in this document twice ({where})")
    matches = [h for h in headings(text) if h[1] == heading]
    if not matches:
        raise SectionError(f"no heading {heading!r}")
    if len(matches) > 1:
        where = ", ".join(f"line {h[2] + 1}" for h in matches)
        raise SectionError(f"heading {heading!r} is not unique ({where})")
    at = matches[0][2]
    if existing:
        if existing[0] == at + 1:
            return text
        raise SectionError(f"anchor {key!r} is already at line {existing[0] + 1}; the kit never "
                           "silently moves one")
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.insert(at + 1, f"<!-- {ANCHOR_PREFIX} {key} -->\n")
    return "".join(lines)


def set_entries(text, collection, entries):
    """`text` with one collection's `entries:` block replaced, and every other byte left alone.

    The contract is a file a person maintains: statuses, reasons and criteria are their verdicts,
    and the comments around them are the reason the file is readable. No dumper preserves either,
    so this is a surgical edit rather than a rewrite — it replaces one block and touches nothing
    else in the file.
    """
    lines = text.splitlines(keepends=True)
    top = _block_start(lines, "collections:", 0)
    if top is None:
        raise SectionError("the contract has no `collections:` block")
    start, end = _block_bounds(lines, top + 1, 2)
    own = _block_start(lines[start:end], f"{collection}:", 2)
    if own is None:
        raise SectionError(f"the contract records no `{collection}` collection")
    own += start
    body_start, body_end = _block_bounds(lines, own + 1, 4)
    existing = _block_start(lines[body_start:body_end], "entries:", 4)
    if existing is not None:
        existing += body_start
        _, drop_to = _block_bounds(lines, existing + 1, 6)
        del lines[existing:drop_to]
        body_end -= drop_to - existing
    rendered = ["    entries:\n"] if entries else []
    for key, at in entries.items():
        rendered.append(f"      {_entry_key(key)}:\n")
        rendered.append(f"        at: {_entry_value(at)}\n")
    lines[body_end:body_end] = rendered
    return "".join(lines)


def _entry_key(key):
    return key if re.match(r"^[A-Za-z0-9_.\-]+$", str(key)) else '"{}"'.format(
        str(key).replace('"', '\\"'))


def _entry_value(at):
    """A binding as the reader takes it back — quoted only where a plain scalar would not do."""
    text = str(at)
    plain = text and text == text.strip() and not text.startswith(("#", "'", '"', "-", "[", "{",
                                                                   "&", "*", "!", "|", ">"))
    return text if plain and " #" not in text else "'{}'".format(text.replace("'", "''"))


def _significant(line):
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _block_start(lines, opener, indent):
    pad = " " * indent
    for number, line in enumerate(lines):
        if line.startswith(pad + opener) and line[indent:].rstrip() == opener:
            return number
    return None


def _block_bounds(lines, start, indent):
    """(start, one past the last significant line) of the block indented at least `indent`.

    Trailing blanks and the comments that introduce whatever comes next are left outside, so an
    inserted block lands under the values it belongs to rather than above someone else's heading.
    """
    end = start
    for number in range(start, len(lines)):
        line = lines[number]
        if not _significant(line):
            continue
        if len(line) - len(line.lstrip(" ")) < indent:
            break
        end = number + 1
    return start, end


def documents_matching(root, patterns):
    """The documents a collection's `sources` globs name, relative to the project root."""
    found = []
    for pattern in patterns or []:
        for match in sorted(glob.glob(os.path.join(root, str(pattern)), recursive=True)):
            if inside(root, match) and os.path.isfile(match):
                relative = os.path.relpath(match, root)
                if relative not in found:
                    found.append(relative)
    return found
