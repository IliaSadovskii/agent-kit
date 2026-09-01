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
from ..manual import Manual, ManualRefused, actions_of, refuse_unless_each_action_is_answered
from ..logs import get_logger
from ..project import require_project
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest
from .deliverable import (
    WORTH_FIXING, expensive_of, read, refuse_unless_deliverable, where as said_where,
)

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

        # Before the knowledge is even looked at, because a chore does not live
        # there: the file is `.agent-kit/v3/manual.md` and every project has
        # one. Named against the owner's own checkout, for the reason the
        # ledger is — nobody commits it, so a line laid last night stands only
        # there, and a key derived against this run's frozen copy would collide
        # with it.
        actions = self._manual(root, design)

        knowledge = Knowledge(project.knowledge_in(where))
        # And the ledger is asked of the owner's own checkout, never of this
        # copy. The blocks a run writes are committed onto its branch, so the
        # tree is the right place for them; the ledger is committed by nobody —
        # the evening lays a line there and the owner reads the diff — so a
        # run's tree holds it frozen at the base of its branch. Asked here, a
        # line laid last night and not yet committed would be a line this run
        # cannot see, and naming it would kill the night at its last step.
        ledger = Knowledge(project.knowledge_dir)
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
            # Nothing is owed and nothing is written — the findings of this
            # review included. A night never *makes* a knowledge directory: the
            # hour with the owner does, because somebody is standing there to be
            # asked. The expensive assumptions and the findings still reach the
            # owner: `deliver` opens the pull request with them.
            return _said([], [], [], [], [], actions)

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
            standing = {line.key for line in ledger.debt()} if fixes else set()
            for key in fixes:
                if key not in standing:
                    raise KnowledgeError(
                        "no-such-debt", f"ни одна строка реестра этого проекта не несёт ключ {key!r}"
                    )

            closed = [_closed(knowledge, id, touched) for id in closing]
            blocks = [self._write(knowledge, request, item, touched, claimed) for item in owing]
            debt = self._debt(ledger, review)
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
            "%s: %s blocks written, %s closed, %s lines of debt named, %s answered, %s by hand",
            request.slug, len(blocks), len(closed), len(debt), len(fixes), len(actions),
        )
        return _said(blocks, closed, files, debt, fixes, actions)

    def _manual(self, root: Path, design: dict) -> list[dict]:
        """What a person must do by hand, named with the key its line will carry.

        Named, and not written: this file has one writer — the evening of a
        batch, once, when there is nothing left to build — for the measurement
        that moved the ledger's writer, which holds here unchanged.

        A run started by hand names its actions and lays none. They reach the
        owner in the pull request, the way a lone run's findings do.
        """
        try:
            refuse_unless_each_action_is_answered(design)
        except ManualRefused as refused:
            # A program, so this is a failure and not an attempt refused: the
            # design is on file and a second attempt reads the same file.
            raise ExecutorFailed(refused.code, refused.detail, retryable=False) from None

        standing = Manual(root)
        claimed: set[str] = set()
        named = []
        for row in actions_of(design):
            what = str(row.get("what") or "").strip()
            # `claimed` and not a set of wordings: two chores worded the same
            # are two chores, which is what the join counts.
            key = standing.free_key(what, claimed)
            claimed.add(key)
            # The one that was not answered is left out rather than written
            # empty: an optional field of a contract is absent or is an answer,
            # and `""` is neither.
            said = {"key": key, "what": what}
            for name in ("proof", "by_hand"):
                value = str(row.get(name) or "").strip()
                if value:
                    said[name] = value
            named.append(said)
        return named

    def _debt(self, ledger: Knowledge, review: dict) -> list[dict]:
        """What the review found and nothing stops, named with the key it will carry.

        Named, and not written. The ledger has one writer — the night of a
        batch, once, when there is nothing left to build — because two features
        of one evening branch from one base and append to one section, and two
        branches that will not merge is what that produces every time: measured,
        200 of 200. So the feature decides the key and the evening lays the
        line, which is the same division `record` already keeps with `deliver`.

        The keys are derived against the owner's own ledger and not this run's
        copy of it, because that is the file the evening will look in.

        A run started by hand writes none at all. Its findings reach the owner
        in the pull request, the way they always have, and that narrowing is
        written down rather than discovered.

        And what a blocking finding costs is said here rather than found out:
        the run stops before this step, so every `worth-fixing` of that same
        review goes with it. The ledger is empty exactly for the night after
        which nothing was left — which is the night whose findings the owner is
        reading in a refusal anyway.
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
            key = ledger.free_key(what, keyed)
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
    blocks: list[dict], closed: list[str], files: list[str], debt: list[dict], fixed: list[str],
    manual: list[dict] | None = None,
) -> ExecutorResult:
    return ExecutorResult(
        raw=json.dumps(
            {"blocks": blocks, "closed": closed, "files": files, "debt": debt, "fixed": fixed,
             "manual": manual or []},
            indent=2, ensure_ascii=False,
        ),
        # No `model`: a program is not a session, and the record must not read
        # as though one did this.
        meta={"blocks": len(blocks), "closed": len(closed)},
    )
