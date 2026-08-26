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
from .deliverable import expensive_of, read, refuse_unless_deliverable

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

        if not knowledge.exists:
            if closing:
                raise ExecutorFailed(
                    "no-knowledge",
                    f"the design closes {', '.join(closing)} and this project keeps no knowledge under "
                    f"{project.knowledge}",
                    retryable=False,
                )
            # Nothing is owed and nothing is written. The expensive assumptions
            # still reach the owner: `deliver` opens the pull request with them.
            return _said([], [], [])

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
                knowledge.find(id)
            for item in owing:
                knowledge.resolve(str(item["at"]))

            closed = [_closed(knowledge, id, touched) for id in closing]
            blocks = [self._write(knowledge, request, item, touched, claimed) for item in owing]
        except KnowledgeError as refused:
            # The address, the identifier — the knowledge said no by name, and
            # the same name reaches the run's own record.
            raise ExecutorFailed(refused.code, refused.detail, retryable=False) from refused

        files = []
        for path in touched:
            relative = str(path.relative_to(where))
            if relative not in files:
                files.append(relative)
        log.info("%s: %s blocks written, %s closed", request.slug, len(blocks), len(closed))
        return _said(blocks, closed, files)

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


def _said(blocks: list[dict], closed: list[str], files: list[str]) -> ExecutorResult:
    return ExecutorResult(
        raw=json.dumps({"blocks": blocks, "closed": closed, "files": files}, indent=2, ensure_ascii=False),
        # No `model`: a program is not a session, and the record must not read
        # as though one did this.
        meta={"blocks": len(blocks), "closed": len(closed)},
    )
