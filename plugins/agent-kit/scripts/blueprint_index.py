#!/usr/bin/env python3
"""The derived half of the knowledge contract: `/agent-kit:blueprint --index`.

`--check` never calls a grader — it compares hashes and reports. This is the other mode, the one
that spends the calls, and it is deliberately three separate invocations rather than one:

    blueprint_index.py --plan              → JSON: the grader calls that need making
    blueprint_index.py --apply <file>      ← JSON: what the graders extracted
    blueprint_index.py --anchors <file>    ← JSON: where the anchors go, after the owner's yes

The split is not ceremony. The kit ships stdlib Python and installs nothing, so a script cannot
call a model; the agent is the grader and drives the two halves. Keeping the mechanical work in the
script is what puts the cache — one call per document, only for sections whose hash moved — inside
reach of a test that counts calls rather than an argument that they are made.

Exit codes match `--check`: 0 clean, 2 structural. There are no findings here; findings are what
`--check` reports about the result.
"""
import json
import os
import sys

import kit_knowledge
import kit_yaml
from blueprint_check import CONTRACT_PATH


class IndexRunError(Exception):
    """Something the run cannot proceed past, reported rather than raised at the owner."""


def read_contract(root):
    path = os.path.join(root, CONTRACT_PATH)
    if not os.path.isfile(path):
        raise IndexRunError(f"no knowledge contract at {CONTRACT_PATH}")
    try:
        contract = kit_yaml.load_path(path)
    except kit_yaml.KitYamlError as exc:
        raise IndexRunError(f"{CONTRACT_PATH}: {exc} — the kit reads a YAML subset and will "
                            "not guess")
    except (OSError, UnicodeDecodeError) as exc:
        raise IndexRunError(f"{CONTRACT_PATH}: {exc}")
    if not isinstance(contract, dict):
        raise IndexRunError(f"{CONTRACT_PATH} is not a mapping")
    return contract


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError) as exc:
        raise IndexRunError(str(exc))
    except json.JSONDecodeError as exc:
        raise IndexRunError(f"{path}: {exc}")


def do_plan(root):
    """The work list, as JSON on stdout. Nothing to do is an empty list and exit 0."""
    contract = read_contract(root)
    try:
        index = kit_knowledge.load_index(root)
    except kit_yaml.KitYamlError as exc:
        raise IndexRunError(f"{kit_knowledge.INDEX_PATH}: {exc}")
    groups = kit_knowledge.plan(root, contract, index)
    entries = sum(len(group["entries"]) for group in groups)
    print(json.dumps(groups, ensure_ascii=False, indent=2))
    print(f"{len(groups)} grader call(s) for {entries} entr{'ies' if entries != 1 else 'y'}",
          file=sys.stderr)
    return 0


def do_apply(root, path):
    """Merge grader results into the index. The rev is recomputed here, from the file on disk."""
    contract = read_contract(root)
    results = read_json(path)
    if isinstance(results, dict):
        results = results.get("entries") or results.get("results") or []
    if not isinstance(results, list):
        raise IndexRunError(f"{path}: expected a list of {{collection, key, facts, gaps}}")
    try:
        index = kit_knowledge.load_index(root)
        merged = kit_knowledge.apply_results(root, contract, index, results)
    except (kit_yaml.KitYamlError, ValueError) as exc:
        raise IndexRunError(str(exc))
    written = kit_knowledge.write_index(root, merged)
    total = sum(len(block) for name, block in merged.items() if isinstance(block, dict))
    print(f"{os.path.relpath(written, root)}: {len(results)} entr"
          f"{'ies' if len(results) != 1 else 'y'} parsed, {total} in the index")
    return 0


def do_anchors(root, path):
    """Write the proposed anchors, and record the entries they bind. Never a partial write.

    Every proposal is validated and applied in memory first. A run that fails halfway would leave
    anchors in the owner's documents that the contract does not know about, which is the one state
    this flow must not be able to produce.
    """
    contract_path = os.path.join(root, CONTRACT_PATH)
    read_contract(root)
    proposals = read_json(path)
    if not isinstance(proposals, list) or not proposals:
        raise IndexRunError(f"{path}: expected a non-empty list of "
                            "{collection, key, path, heading}")

    documents, entries, seen = {}, {}, set()
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise IndexRunError(f"{proposal!r} is not a proposal")
        collection = proposal.get("collection")
        key = str(proposal.get("key") or "")
        document = str(proposal.get("path") or "")
        heading = proposal.get("heading")
        if collection not in kit_knowledge.COLLECTION_SLOTS:
            raise IndexRunError(f"{collection!r} is not a collection this kit version knows")
        if not key or not heading or not document:
            raise IndexRunError(f"{proposal!r}: a proposal needs collection, key, path "
                                "and heading")
        if (collection, key) in seen:
            raise IndexRunError(f"{collection}/{key} is proposed twice")
        seen.add((collection, key))
        full = kit_knowledge.inside(root, document)
        if full is None or not os.path.isfile(full):
            raise IndexRunError(f"{document} is not a document in this project")
        if document not in documents:
            with open(full, encoding="utf-8") as handle:
                documents[document] = handle.read()
        try:
            documents[document] = kit_knowledge.place_anchor(documents[document], key, heading)
        except kit_knowledge.SectionError as exc:
            raise IndexRunError(f"{document}: {exc}")
        entries.setdefault(collection, {})[key] = (
            f"{document}#{kit_knowledge.ANCHOR_PREFIX}{key}")

    with open(contract_path, encoding="utf-8") as handle:
        text = handle.read()
    recorded = kit_knowledge.entry_bindings(read_contract(root))
    try:
        for collection, bindings in entries.items():
            merged = dict(recorded.get(collection) or {})
            merged.update(bindings)
            text = kit_knowledge.set_entries(text, collection, merged)
    except kit_knowledge.SectionError as exc:
        raise IndexRunError(f"{CONTRACT_PATH}: {exc}")

    for document, updated in documents.items():
        with open(kit_knowledge.inside(root, document), "w", encoding="utf-8") as handle:
            handle.write(updated)
    with open(contract_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"{len(seen)} anchor(s) written across {len(documents)} document(s); "
          f"{CONTRACT_PATH} records them")
    return 0


USAGE = "usage: blueprint_index.py --plan | --apply <results.json> | --anchors <proposal.json>"


def main(argv):
    root = os.getcwd()
    args = argv[1:]
    try:
        if args == ["--plan"]:
            return do_plan(root)
        if len(args) == 2 and args[0] == "--apply":
            return do_apply(root, args[1])
        if len(args) == 2 and args[0] == "--anchors":
            return do_anchors(root, args[1])
    except IndexRunError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
