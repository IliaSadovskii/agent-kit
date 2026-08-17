# Two sessions in one checkout, 17 August 2026

The owner ran a batch overnight on a live project and, while it ran, opened a second session in the
same directory and dictated into `blueprint`. The second session kept reporting that it was tripping
over the first. The question was whether that could cost anything — a commit on the wrong branch, a
push somewhere it did not belong — and what mechanism would let the two run side by side on purpose,
because the pairing is the one the owner wants: an epic building while they keep the description
current.

Everything below was measured on that project while it was still running.

## What actually happened

The driver starts every child in the project's own directory — that is `Launcher(cwd)` in
`orchestrate.py`, and `cwd` is the project root. So the run and anybody else who opens a session
there share one working tree and one `HEAD`.

From the reflog, by the minute:

- 03:17 — a feature's session switched the tree to `claude/2026-08-17-profile-screen`.
- 03:18 — the second session switched the same tree to `main` and cut a branch of its own.
- 03:29 — the feature, finding its tree gone, built a `git worktree`, rebased into it, amended,
  reset, and committed the removal of a `node_modules` symlink that existed only because the tree
  had moved under it. Twelve minutes, none of it work.

**Nothing was lost, and no commit went anywhere wrong.** The knowledge branch held only
`docs/knowledge/` commits and the feature branches held only code. What it cost was time, context,
and a run improvising infrastructure at four in the morning.

Three worse things were sitting behind it, and only the first was visible.

**The escape disarmed both hooks.** A linked worktree has `.agent-kit/` — it is tracked — and no
`.agent-kit/runs/`, which every project gitignores. `runs_in_flight` read that as *no run here*, so
for the rest of the night that feature could have merged its own pull request, force-pushed, or
pushed the default branch, and the stop hook could not find the run it was meant to hold open.

**The suite in a worktree proves the wrong tree.** This project's containers mount the project
directory, and `make test` is `docker compose exec` into them. A feature working in a worktree
therefore runs its tests against whatever the *other* session has checked out. Verified by hash: the
file inside the container was byte-for-byte the main checkout's and differed from the worktree's.
The feature noticed and worked around it with a one-off container — noticed, not prevented.

**And the two knowledge branches met at the merge.** `git merge-tree` over the batch's chain and the
default branch reported one conflict in `actions.md`, and it was not a disagreement: the owner had
inserted a new record at the same seam where a child had appended a `[stale …]` block. Both
additions, one anchor, and git cannot tell them apart.

## Two proposals that were dropped

**A lock file saying a run is in progress.** Not built, because it already exists: a run file at a
non-terminal step, written to inside a day, is exactly that signal, and the guard hook has read it
since 0.48.0. What was missing was every other reader. A second record would have been a mechanism
whose first job is to disagree with the one already there.

**A queue for ideas dictated during a run.** This is *a separate `intake` mechanism for new ideas*,
refused on `docs/planned.md` with a reason that is still true: `blueprint` is the intake. The
question the owner was actually asking is not *where do ideas go* but *when may the intake write*,
and that is answered by a tree, not by a journal. A queue becomes worth building only when the
dictation arrives without a session — from a phone, through the transport of item 3 — and then it is
the same `.agent-kit/asks/` directory with the other author.

**A rule naming the records a run holds** was dropped after it was specified. It cannot be computed:
a child leaves blocks under entries that are not in its own `entries` — one did that night, under
`user.update_profile`, because its feature made that record's prose false. A list that is knowably
incomplete makes a poor prohibition. And the prohibition is not needed anyway: a run reads the
knowledge off the branch it forked from, so a second session's writes are invisible to it until they
merge. *Rules the build follows must not change under a run* is satisfied by separate trees.

## What was built

**One checkout, one writer.** The run owns the project directory, because the containers are wired
to it. Everything else takes a tree of its own.

- `runfile.in_flight` — what counts as a run happening now, in the one place every reader asks. Two
  facts: never terminal, and written to inside a day. The staleness half is what gives the signal an
  end.
- `runfile.main_worktree` — run files are read from the checkout they live in, so a session in a
  linked worktree finds them. By reading `.git` and `commondir` rather than by asking `git`: this is
  on the path of a hook that runs on every Bash call.
- `check.py` prints the runs in flight first, always, marking the line that belongs to the session
  reading it. A statement; it never touches the exit code.
- `rules/preflight.md` carries the reaction: `ship`, `fix`, `sprint`, `epic` and `next` do not start
  beside somebody else's run. `blueprint` and `advise` do — they write no code.
- The guard refuses `git checkout` and `git switch` in a held checkout from a session the driver did
  not register, and names `git worktree add` in the refusal. `git checkout -- <path>` restores a file
  and moves no branch, so it is let past.
- `check.py --run` names the records that moved on the default branch since the run branched: by
  key rather than by heading, with the `state:` line ignored, because the kit's own programs move
  that on every entry a batch delivers.

**The four answers**, for the two that are mechanisms rather than programs. The in-flight statement:
written by the driver into run files, read by the preflight and both hooks, closed when the run
reaches a terminal step or a day passes without a write, and without it a second session takes the
tree without knowing. The drift statement: computed on demand and stored nowhere, so it has nothing
to close — which is the cheapest form this could have taken and the reason it was preferred to a
recorded one.

## What is left

**Merge order is prose, not a program.** The batch merges first and the knowledge branch last,
because a chain of branches is expensive to rebase and one branch is not. Nothing enforces it.

**The suite in a worktree still proves whatever the containers mount.** That is a fact about the
project, not about the kit — a project whose compose file mounts a fixed path cannot be tested from
two trees at once. The home for it is the project's own `make test`, beside the asserts it already
has: compare the container's mount against the directory the command was run from, and refuse.
Written down here because the kit cannot fix it and every project it happens on will find it the
expensive way.

**Parallel building is still refused** — `docs/planned.md`, item 7. Nothing here changes that: this
is one lane, plus the owner talking to the description while it runs.
