"""record — what the run decided, written into the project's knowledge by the program.

The plan's whole sentence for S6: *the model returns fields, the driver writes
the file and the mark.* The reason it is a program rather than a role is the
reason `verify` is one — an agent that writes the file itself can always claim
it did, and the join this step exists for has to be checkable.

The join: **an expensive assumption owes a block.** It binds a project that
keeps knowledge; a project that keeps none is not made to invent one, and its
expensive assumptions still reach the owner in the open half of the pull
request, which is the channel that exists.

Nothing here is written until the work is known to be deliverable. A blocking
finding, a red suite or a build that never finished stops the run before the
owner's knowledge is touched.
"""

from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path

from ..knowledge import Knowledge, KnowledgeError
from ..logs import get_logger
from ..project import require_project
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest
from .deliverable import expensive_of, read, refuse_unless_deliverable, where as said_where

#: A finding that is real and does not stop delivery. `blocking` never reaches
#: this step — the run is over before it — and a `note` costs nothing and blocks
#: nothing, which is exactly what a line in somebody's ledger does not.
WORTH_FIXING = "worth-fixing"

log = get_logger("programs.record")


class Record:
    name = "program:record"

    def __init__(self, root: Path, today: str = "") -> None:
        self.root = Path(root)
        self.today = today or _date.today().isoformat()

    def execute(self, request: StepRequest) -> ExecutorResult:
        root = Path(request.project) if request.project else self.root
        project = require_project(root)
        # Two places, and they are two: the declaration is the project's own
        # paperwork, and the knowledge is repository content — so it is written
        # where the code is, this run's own worktree, and `deliver` commits it
        # onto the branch. Written into the project's checkout instead, a block
        # reaches nobody: not the branch, and not the owner, who is left with an
        # edit they never made on whatever they had checked out.
        where = request.where
        design, build, verify, review = read(request.prior)

        # Before anything is written, and this is the whole reason the step
        # stands in front of `deliver` rather than inside it.
        refuse_unless_deliverable(build, verify, review)

        knowledge = Knowledge(project.knowledge_in(where))
        owing = expensive_of(design)
        # Named twice means named once. Without this the pre-check below passes
        # twice — the block is still there when it is asked — and the second
        # delete refuses, having already rewritten the owner's file.
        closing = list(dict.fromkeys(str(item).strip() for item in (design.get("closes") or []) if str(item).strip()))

        fixes = list(dict.fromkeys(str(one).strip() for one in (design.get("fixes") or []) if str(one).strip()))

        if not knowledge.exists:
            if closing or fixes:
                named = ", ".join(closing + fixes)
                raise ExecutorFailed(
                    "no-knowledge",
                    f"the design names {named} and this project keeps no knowledge under {project.knowledge}",
                    retryable=False,
                )
            # Nothing is owed and nothing is written. The expensive assumptions
            # still reach the owner: `deliver` opens the pull request with them.
            return _said([], [], [], [], [])

        naked = [item for item in owing if not (item.get("block") and item.get("at"))]
        if naked:
            raise ExecutorFailed(
                "assumption-with-no-block",
                "this project keeps knowledge, so an expensive assumption owes a block, and these have "
                "none: " + "; ".join(str(item.get("what")) for item in naked),
                retryable=False,
            )

        touched: list[Path] = []
        claimed: set[str] = set()
        try:
            # Every address resolves before anything is written. A run that
            # half-wrote the owner's knowledge and then failed leaves a working
            # copy nobody will look at again, and that is worse than a run that
            # wrote nothing at all.
            for id in closing:
                knowledge.closable(id)
            for item in owing:
                knowledge.resolve(str(item["at"]))

            # A line the work says it answers has to be a line somebody wrote.
            # Asked here, with the addresses, because this step resolves
            # everything before it edits anything — and asked only where the run
            # has something to do with the ledger, so a night is not failed at
            # its last step over a file it never touched.
            standing = {line.key for line in knowledge.debt()} if fixes else set()
            for key in fixes:
                if key not in standing:
                    raise KnowledgeError(
                        "no-such-debt", f"no line of this project's ledger carries the key {key!r}"
                    )

            closed = [_closed(knowledge, id, touched) for id in closing]
            blocks = [self._write(knowledge, request, item, touched, claimed) for item in owing]
            debt = self._debt(knowledge, request, review)
        except KnowledgeError as refused:
            # The address, the identifier — the knowledge said no by name, and
            # the same name reaches the run's own record.
            raise ExecutorFailed(refused.code, refused.detail, retryable=False) from refused

        files = []
        for path in touched:
            relative = str(path.relative_to(where))
            if relative not in files:
                files.append(relative)
        log.info(
            "%s: %s blocks written, %s closed, %s lines of debt named, %s answered",
            request.slug, len(blocks), len(closed), len(debt), len(fixes),
        )
        return _said(blocks, closed, files, debt, fixes)

    def _debt(self, knowledge: Knowledge, request: StepRequest, review: dict) -> list[dict]:
        """What the review found and nothing stops, named with the key it will carry.

        Named, and not written. The ledger has one writer — the night of a
        batch, once, when there is nothing left to build — because two features
        of one evening branch from one base and append to one section, and two
        branches that will not merge is what that produces every time: measured,
        200 of 200. So the feature decides the key and the evening lays the
        line, which is the same division `record` already keeps with `deliver`.

        A run started by hand writes none at all. Its findings reach the owner
        in the pull request, the way they always have, and that narrowing is
        written down rather than discovered.
        """
        keyed: set[str] = set()
        said = []
        for finding in review.get("findings") or []:
            if finding.get("severity") != WORTH_FIXING:
                continue
            what = said_where(finding)
            # `keyed` and not a set of wordings: two findings worded the same
            # are two findings, and one line answering for both is the shape of
            # the blocker S6 paid for.
            key = knowledge.free_key(what, keyed)
            keyed.add(key)
            said.append({"key": key, "what": what})
        return said

    def _write(
        self, knowledge: Knowledge, request: StepRequest, item: dict, touched: list[Path], claimed: set[str]
    ) -> dict:
        what = str(item["what"])
        # `claimed` is what keeps two assumptions worded the same from being one
        # block: the second cannot be handed the name the first is already using.
        id = knowledge.free_id(request.slug, what, request.branch, claimed)
        claimed.add(id)
        touched.extend(
            knowledge.write(
                at=str(item["at"]), run=request.branch, body=str(item["block"]), id=id, date=self.today
            )
        )
        return {"id": id, "at": str(item["at"]), "what": what}


def _closed(knowledge: Knowledge, id: str, touched: list[Path]) -> str:
    touched.append(knowledge.close(id))
    return id


def _said(
    blocks: list[dict], closed: list[str], files: list[str], debt: list[dict], fixed: list[str]
) -> ExecutorResult:
    return ExecutorResult(
        raw=json.dumps(
            {"blocks": blocks, "closed": closed, "files": files, "debt": debt, "fixed": fixed},
            indent=2, ensure_ascii=False,
        ),
        # No `model`: a program is not a session, and the record must not read
        # as though one did this.
        meta={"blocks": len(blocks), "closed": len(closed)},
    )
