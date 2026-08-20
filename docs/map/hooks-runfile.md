# Sector: hooks and run file

Source of the hook registration: `plugins/agent-kit/hooks/hooks.json`.
```
PreToolUse matcher=Bash -> python3 hooks/guard.py, timeout 10
Stop (no matcher, all)  -> python3 hooks/stop.py,  timeout 30
```
(hooks.json:4-25)

## guard.py

### FIRES WHEN
`PreToolUse`, matcher `"Bash"` only (hooks.json:6). Timeout 10s. Runs before every Bash tool call
in every session of every project that has the plugin installed.

### INPUT
stdin JSON (guard.py:268 `json.load(sys.stdin)`). Fields read:
- `event.get("tool_name")` — must equal `"Bash"` or hook returns immediately (guard.py:273).
- `event["tool_input"]["command"]` — the shell command string (guard.py:275).
- `event.get("cwd")` — resolved to project root via `runfile.project_root` (guard.py:279), falls
  back to `os.getcwd()`.

### OUTPUT CONTRACT
- Malformed stdin (not JSON) → `return 0`, prints nothing (guard.py:268-270). Silent allow.
- Not a Bash call, no command, no project root, or no run in flight → `return 0`, silent (guard.py:273-281).
- Import of `runfile` module fails → prints `{"systemMessage": "...guard could not load..."}`,
  exit 0 — allow, but loud (guard.py:64-68).
- Any other exception inside `main()`'s try → caught, prints
  `{"systemMessage": "agent-kit's guard could not judge this command and allowed it: {exc}"}`,
  exit 0 (guard.py:298-300). Always fails open.
- A refusal → prints
  ```json
  {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
    "permissionDecisionReason": "<why>"},
   "systemMessage": "agent-kit refused this: <why>"}
  ```
  (guard.py:290-297). `permissionDecision: deny` is what makes Claude Code block the tool call;
  exit code is always 0 (the hook process itself never fails — refusal is communicated purely
  through the JSON payload, not the exit status).
- No opinion → exit 0, no stdout.

### DECISION TREE (ordered, with line refs)
In `main()` (guard.py:266-301):
1. Parse stdin JSON; unparsable → allow silently (268-270).
2. `tool_name != "Bash"` → allow (273-274).
3. Empty/missing `command` → allow (275-277).
4. Resolve `root = project_root(cwd)`; `root is None` → allow (279-281).
5. `runs_in_flight(root)` false (no unstale non-terminal run file anywhere in the project) →
   allow (280-281, delegates to `runfile.in_flight`).
6. Compute `building = building_a_feature(root)` (283) — is *this* session a `ship`/`fix`
   (`kind == "feature"`) run of its own, not yet terminal.
7. Compute `verdict(...)` (284-286) passing: command, current branch (`git rev-parse
   --abbrev-ref HEAD`), default branch, declared e2e command (only if `building`), `building`,
   `holds_tree(root)` (held-checkout flag), declared verification commands (only if `building`).
8. Inside `verdict()` (guard.py:213-263), in this exact order:
   a. **held + SWITCH pattern matches command** → refuse (moving-branch-of-shared-tree message)
      (217-221).
   b. **e2e walk**: `e2e` is set, `building` is true, `e2e.strip()` is a non-empty substring of
      `command`, AND no string in `own_checks` is itself a substring of `command` → refuse
      ("walks the whole product...") (243-248).
   c. **MERGE** regex matches → refuse ("Merging is the owner's...") (249-252).
   d. **FORCE** regex matches → refuse ("A force push rewrites history...") (253-255).
   e. **PUSH** regex matches → check `pushes_default`: either the default branch name appears
      as a whole word in the command, OR (`branch == default` AND the push has no explicit
      remote+refspec, i.e. a bare `git push`) → refuse (256-262).
   f. Otherwise → `None`, allowed (263).
9. Back in `main()`: `why is None` → allow (287-288); else print deny JSON (290-297).

### REFUSAL PATTERNS
- **Merge**: `MERGE = re.compile(r"\bgh\s+pr\s+merge\b")` (guard.py:72). Only matches `gh pr
  merge`; does NOT catch merging via `git merge`, GitHub web UI, or API calls outside `gh`.
- **Force push**: `FORCE = re.compile(r"\bgit\s+push\b[^&|;]*?(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\w)")`
  (guard.py:73). Catches `--force`, `--force-with-lease`, `-f`, and the `+branch` refspec form.
  Stops matching at `&`, `|`, or `;` (so it won't reach across compound-command separators looking
  for the flag — it only looks within the same `git push` clause).
- **Push to default branch**: `PUSH = re.compile(r"\bgit\s+push\b")` (guard.py:74), refined by
  `pushes_default` logic (256-259): matches if the default branch name is a whole word anywhere
  in the command, or if standing on the default branch and pushing bare (`git push` with no
  explicit `remote ref` pair). A push naming a different branch while standing on default is not
  refused (test: `test_a_bare_push_while_standing_on_the_default_branch` requires branch==default
  AND a bare push).
- **Switching a held tree**: `SWITCH = re.compile(r"\bgit\s+(?:checkout|switch)\b(?![^&|;]*?\s--\s)")`
  (guard.py:78). Negative lookahead excludes the `--` file-restore form (`git checkout -- path`,
  `git checkout HEAD -- path`); `git restore` is not matched by SWITCH at all (never refused) —
  confirmed by `test_restoring_a_file_moves_no_branch` (test_guard.py:102-105), which also shows
  `git restore` was never intended to be caught (it moves no branch by design, not by the regex).
  Only fires when `holds_tree(root)` is true (a separate session/tree condition, not command-only).
- **The whole-product e2e walk** (only inside a `ship`/`fix` in-progress session): fires when the
  command contains the project's declared `commands.e2e` string and does not contain any of the
  project's declared `verification.*` commands (`own_checks`) as a substring (guard.py:243-248).
  Deliberately narrow — bound to `building` (a feature run, not terminal) so it never fires for
  the scenarios lens, closing session, epic's proving phase, or the owner's own terminal (per
  guard.py:24-38 design comment and tests: `test_the_same_command_where_walking_the_product_is_the_work`).
- **Does NOT get an early global exemption for declared checks.** A declared check string
  matching part of a compound command does not stand aside the merge/force/push/held-tree checks
  — this is explicit and tested (`test_a_declared_check_does_not_excuse_the_irreversible_three`,
  `test_a_declared_check_does_not_excuse_taking_a_held_tree`, guard.py comment 238-242).

### NO-OP PATHS
- Not a Bash call (guard.py:273).
- Empty command string (275).
- `project_root` can't be found — the directory has no `.agent-kit/` anywhere above it (279-281,
  via `runfile.project_root`).
- No run in the project is "in flight" (`runfile.in_flight` — none non-terminal and touched
  within `STALE_AFTER` = 24h) (280-281, runfile.py:116-140).
- Not building a feature and no held tree and command matches none of MERGE/FORCE/PUSH — every
  ordinary command (`git commit`, `make test`, `git fetch`, `gh pr checks`, `git log`, `gh pr
  create`) (tested: `test_the_commands_a_run_lives_on`).
- A branch merely *named* like the default (`claude/mainline-fix`) is not treated as the default
  branch — whole-word match only (test: `test_a_branch_named_after_the_default_one_is_not_the_default_one`).
- `held_tree` requires `my_session()` to resolve (needs `TMUX` env var set) — outside tmux, this
  check is silently skipped; the design comment (guard.py:196-201) explicitly says this leaves
  non-tmux sessions unguarded here and defers to prose printed by `check.py` instead.
- No project e2e command declared (`declared_e2e` returns `""`) → the e2e-walk rule can never
  fire (tested: `test_a_project_that_declares_no_such_command_is_never_refused`).

### IO
Reads:
- stdin (event JSON).
- `.agent-kit/project.yml` — `declared_e2e()` (140-156) and `declared_verification()` (159-180),
  parsed by hand (indentation-based mini-YAML reader, not a real YAML parser) for
  `commands.e2e` and the `verification:` block.
- `.agent-kit/runs/*/run.json` via `runfile.runs`/`runfile.in_flight` (called through
  `runs_in_flight`, `building_a_feature`, `holds_tree`).
- `.git` file/dir structure indirectly via `runfile.main_worktree` (for linked-worktree detection).
- subprocess: `git rev-parse --abbrev-ref HEAD`, `git symbolic-ref ...refs/remotes/origin/HEAD`,
  `git rev-parse --verify main|master` (default_branch, git helper, guard.py:95-107), `tmux
  display-message -p "#S"` (my_session, 110-125).
Writes: nothing. Pure read + stdout print.

### PINNED BY TESTS (tests/test_guard.py)
- Merge refused directly and hidden in a compound command (33-37).
- Force push: `--force`, `-f`, `--force-with-lease` (39-42).
- Push to default by name, incl. `HEAD:main` (44-46); bare push while on default branch (48-49);
  push of a feature branch is allowed even from default-looking names (51-53, 60-61).
- Ordinary commands never refused (55-58).
- e2e-walk fires only when `building=True` and string matches, not otherwise (70-84).
- Held-tree SWITCH refusal, the worktree-add escape hatch is itself never refused, restoring a
  file (`checkout --`, `restore`) is never refused, held tree doesn't block ordinary work (93-118).
- Declared own-checks exemption is narrow: allowed only when the command IS the declared check
  (or contains it), not merely mentions the e2e string; still refuses the raw e2e walk even with
  own_checks declared (123-133); declared checks never excuse merge/force/push-default or a held
  checkout (135-149).
- `declared_e2e` manifest parsing: reads `commands.e2e`, ignores comments, ignores same-named key
  under a different top-level section, returns `""` with no manifest (151-179).
- End-to-end via subprocess with real stdin/stdout: run-in-flight refuses merge (202-205);
  finished run (`step: done`) leaves output empty (207-211); an unparsable run.json still counts
  as "in flight" and still refuses — this is the anti-silent-disarm test (213-227); a run file
  stale >24h (`os.utime` back 30h) is not in flight, allowed silently (229-242); non-Bash tool is
  ignored (244-246); a project with no `.agent-kit/` at all is untouched (248-254); garbage stdin
  → exit 0, no crash (256-259).

## stop.py

### FIRES WHEN
`Stop` event, no matcher (fires on every Stop, all sessions) (hooks.json:16-25). Timeout 30s.
Fires whenever a Claude Code turn ends.

### INPUT
stdin JSON (stop.py:176 `json.load(sys.stdin)`). Fields read:
- `event.get("stop_hook_active")` — if truthy, hook stands aside (181-182).
- `event.get("cwd")` — resolved via `project_root` (184).
(No `tool_name`/`tool_input` — Stop events aren't tool calls.)

### OUTPUT CONTRACT
- Unparsable stdin → `return 0`, silent (176-178).
- `stop_hook_active` true → `return 0`, silent — "told once already; the driver owns it from
  here" (181-182).
- No project root or `my_session()` is `None` (not in tmux) → `return 0`, silent (184-187).
- No unfinished run of this session AND no finished-epic-of-this-session to close → `return 0`,
  silent (189-199, the "nothing to do" path when `found` is falsy and `slug` is falsy).
- No unfinished run, but a finished epic of this session exists → attempts `close_myself`; if
  that fails, prints `{"systemMessage": "agent-kit could not close this session after {slug}
  finished: {failed}. Close it by hand."}`; if it succeeds, prints nothing (192-198) — the session
  is simply killed (or the close_myself call is asynchronous/self-terminating per its own docs).
- An unfinished run of this session exists → prints
  ```json
  {"decision": "block",
   "reason": "Your run <slug> is still at step \"<step>\" — ... Then stop."}
  ```
  (202-208). `decision: block` is what makes Claude Code refuse to end the turn.
- Any other exception → caught, prints `{"systemMessage": "agent-kit's stop hook could not judge
  this session and allowed it: {exc}"}`, exit 0 (209-211). Fails open, loud.
- Import of `runfile` fails → same loud-allow pattern as guard.py (stop.py:44-47).
Exit code is always 0.

### DECISION TREE (ordered, with line refs)
`main()` (stop.py:174-212):
1. Parse stdin; fail → allow (176-178).
2. `stop_hook_active` → allow (181-182).
3. `root = project_root(cwd)`; `session = my_session()`; either `None` → allow (184-187).
4. `mine = my_runs(root, session)` — every run directory whose `state["session"] == session`
   (189, function at 70-85). Only matches on `session`, never on `window` (design note 73-75).
5. `found = unfinished(mine)` (190, function at 88-105):
   - iterate `mine` in `runfile.runs` order (sorted by directory name);
   - skip any run whose `kind == "epic"` (94-96) — epics legitimately end turns mid-flight;
   - skip any run with a non-empty-after-strip string in `handoff` (98-101) — deliberate handover;
   - else if `step` is a string and not in `TERMINAL` → return `(directory.name, step)` (102-104);
   - none found → `None` (105).
6. If `found` truthy → print block JSON with that slug/step and return (201-208 — this is
   reached at the bottom of `main`, after step 7 below is skipped because of the `if not found:
   ... return 0` at 191-199 only running when `found` is falsy).

   (Re-reading control flow precisely: 190-199 is `if not found: slug = finished_epic(mine); if
   slug: close...; return 0`. Only when `found` IS truthy does execution fall through to 201-208.)
7. If `found` falsy → compute `slug = finished_epic(mine)` (192, function at 108-130):
   - iterate `mine`; keep only `kind(state) == "epic"` AND `step in TERMINAL` (122);
   - **staleness check**: `time.time() - (directory/"run.json").stat().st_mtime >= STALE_AFTER`
     (24h) → skip this one (124-128) — protects against an old epic's session name being reused;
   - `OSError` on stat → skip (127-128);
   - return first matching `directory.name`, else `None` (129-130).
   - if `slug` truthy → `failed = close_myself(session)` (194); if `failed` non-empty, print the
     "could not close this session" systemMessage (195-198); either way `return 0` (199).

### REFUSAL PATTERNS
Not a command-refusal hook (no Bash matcher); its one "refusal" is refusing to let the *turn*
end (`decision: block`) while this session's own run is mid-step, per the decision tree above.

### NO-OP PATHS
- Malformed stdin (176-178).
- `stop_hook_active` already set — hook fires at most once per stop-cycle in effect (181-182).
- Not in tmux / `TMUX` env unset → `my_session()` returns `None` → whole hook stands aside
  (59-60, 186-187). This is how the owner's own manually-started session and any session
  outside a registered tmux session is left alone "by construction."
- Session name doesn't match any run's `session` field → `my_runs` returns `[]` → `unfinished`
  and `finished_epic` both trivially `None` → silent allow (70-85, tested:
  `test_a_session_the_kit_did_not_start_is_not_judged`).
- A run's `session` field is absent but its `window` field matches this session — NOT matched,
  by design, since only `session` is compared (73-75, tested:
  `test_the_control_window_is_never_matched`).
- A run of `kind == "epic"` mid-flight (`gate`/`building`/`auditing`/`proving`) — never blocked
  and never closed (94-96, 122; tested `test_an_epic_in_flight_is_neither_closed_nor_blocked`).
- A run with a non-empty `handoff` note — treated as an intentional stop, not blocked (98-101).
- A run file that can't be parsed as JSON — `runfile.read` returns `None`, filtered out of
  `runs()`'s `state is not None` check inside `my_runs` (84-85) — "a file nothing can parse is
  not this session's run" (stop.py:78-79). Note this is the *opposite* stance from guard.py's
  `in_flight`, which counts an unreadable file as "in flight" — the two hooks deliberately treat
  unreadable state differently (see UNCERTAIN section).
- A finished (`step` terminal) non-epic run of this session — left alone entirely; nothing closes
  it from here because "every other session the kit starts already has a closer" (stop.py
  110-112, tested `test_a_finished_feature_is_left_to_the_driver_that_is_watching_it`).
- A finished epic whose run file is stale (≥24h untouched) — not closed (124-128, tested).
- A finished epic belonging to a *different* session (`state["session"] != mySession`) — filtered
  out already by `my_runs`, so never closed (tested `test_somebody_else_s_finished_epic_is_not_closed`).
- A finished epic recorded only under `window` (not `session`) — not closed (tested
  `test_the_window_of_a_finished_epic_is_never_closed`).

### IO
Reads: stdin event; `.agent-kit/runs/*/run.json` via `runfile.runs`; `run.json` mtime via
`.stat()` (staleness for `finished_epic`); subprocess `tmux display-message -p "#S"`
(`my_session`, 53-67).
Writes: nothing to disk directly. Side effect: `close_myself()` may run `claude-close` (external
helper found via `shutil.which`) or `tmux kill-session -t <session>` (133-171) — this terminates
the tmux session/process the hook is running in.

### Session-identity logic
Both hooks derive "my session" purely from `tmux display-message -p "#S"` (the tmux session name
the hook process is running inside), requiring `TMUX` env var to be set at all (guard.py:110-125,
stop.py:53-67 — nearly identical code, not shared). A run file's `session` field (written by the
driver when it starts a child, per templates/run.json:22 `_session` doc) is the only thing
compared against it. `window` (the *owner's* narrating session for a batch) is a distinct field
never matched by either hook — this is what keeps the owner's own terminal untouched "by
construction" rather than by an exception list (stop.py:14-15, 73-75; guard.py's `building_a_feature`
likewise only checks `state.get("session")`, guard.py:134).

### Epic-session-closing behaviour (stop.py)
- Only fires for a run of `kind == "epic"` whose `step` is terminal (`done`/`blocked`/`skipped`)
  and whose `session` matches this hook's session, and whose run file was touched within the last
  24h (`STALE_AFTER`) (108-130).
- Guards, all of which must hold before a close is attempted: session resolves via tmux (186-187);
  this session has no *other* unfinished (non-epic, non-handed-off) run — an unfinished feature
  beside a finished epic blocks the turn instead of closing anything, closing nothing
  (188-199/201-208, tested `test_a_finished_epic_beside_a_feature_mid_step_closes_nothing`); the
  epic run is not stale; the match is on `session`, never `window`.
- Closing mechanism (`close_myself`, 133-171): prefers an external `claude-close` helper found via
  `shutil.which`, called with no arguments (meaning "the session I am in"); tmux `kill-session` is
  used only when no such helper exists on the machine — "the two never both run" (139-141). The
  helper's non-zero exit is treated as an authoritative refusal (e.g. protecting control sessions)
  and is reported via systemMessage rather than overridden (154-163). A `TimeoutExpired`/`OSError`
  is reported as "did not finish" (150-153, 167-168).
- What a zero exit from the helper proves is only "it accepted the job," not that the session's
  registration is actually gone (142-146) — an explicitly acknowledged weak guarantee.

### PINNED BY TESTS (tests/test_stop_hook.py)
Mid-step block with slug+step in the reason (67-72); every terminal step allowed (74-77); session
mismatch not judged (81-85); no-tmux session not judged (87-90); `window` never matched (92-96);
handed-off run allowed to stop (98-103); empty/whitespace handoff string is NOT a handoff, still
blocks (105-108); no runs at all / not a project directory → not judged (110-114); fires once via
`stop_hook_active` then stands aside (118-123); an unreadable/no-step run file is not blocked on
(125-130); finished epic closes its own session for all three terminal steps (134-141); epic
in-flight steps (`gate/building/auditing/proving`) neither block nor close (143-151); a feature of
the same session as an epic is still judged/blocked (153-157); stale (>24h) finished epic closes
nothing (159-167); finished non-epic feature is left alone, not closed (169-174); another
session's finished epic not closed (176-179); epic's `window` never closed (181-186); finished
epic beside an in-progress feature blocks and closes nothing (188-194); loop doesn't short-circuit
alphabetically — a handed-off run doesn't hide a later unfinished one of the same session
(196-204); a close failure is reported via systemMessage with no `decision` key (206-212); an
internal exception is reported via systemMessage, no `decision` key (214-218). `ClosingCase`
(221-282) pins `close_myself`'s helper-first/no-second-opinion behaviour exhaustively (fully
covered above).

## runfile.py

### PUBLIC API (function-by-function)

**`read(path: Path) -> dict | None`** (58-64)
Reads a run file. Returns `None` on `OSError`/`ValueError` (missing file or invalid JSON) or when
the parsed JSON is not a `dict`; otherwise returns the parsed dict as-is. Invariant stated in the
module docstring: "A read that fails returns `None`, never `{}`" — callers must distinguish "no
run" from "unreadable run" (17-18).

**`main_worktree(root: Path) -> Path`** (67-103)
Resolves the *main* checkout for a possibly-linked git worktree, since `.agent-kit/runs/` is
gitignored and only exists in the main tree. Logic: if `root/.git` is not a regular file (i.e.
this is already the main repo, or not a repo at all) → return `root` unchanged (82-84). If it is a
file, read it as `gitdir: <path>` (86-90); if it doesn't start with `gitdir:` → return `root`
(89-90). Resolve `admin` dir (the linked worktree's private git-dir), read `admin/commondir` to
find the real `.git` directory, and take its parent as `main` (91-102). Returns `main` only if
`main/.agent-kit/runs` is a directory or `main/.agent-kit` is a directory; else falls back to
`root` (103). All file I/O, no `git` subprocess calls — explicitly for performance since this
sits on the hot path of "every Bash call in every session" (76-79).
Errors: any `OSError` reading the marker file or `commondir` → falls back to returning `root`
(87-88, 96-97, 99-102 via nested try).

**`runs(root: Path) -> generator[(Path, dict|None)]`** (106-113)
Yields `(directory, state)` for every `*/run.json` glob match under
`main_worktree(root)/.agent-kit/runs/`, sorted by path. Unreadable files are yielded too, with
`state=None` — "every caller has something to say about them" (109-110).

**`in_flight(root: Path) -> list[(Path, dict|None)]`** (116-140)
The runs "happening here now." For each `(directory, state)` from `runs(root)`: skip if
`run.json`'s mtime can't be stat'd (`OSError` → `continue`, 132-135); skip if
`age >= STALE_AFTER` (24h) (136-137); otherwise include if `state is None` OR
`state.get("step") not in TERMINAL` (138-139). **An unreadable-but-fresh file counts as in
flight** — explicit design choice, documented and tested (125-127; guard test
`test_a_run_file_nothing_can_parse_does_not_disarm_the_guard`).

**`kind(state: dict) -> str`** (143-173)
Returns one of `KINDS` (`feature|errand|batch|epic`) or `"unknown"`. Precedence:
1. `state["kind"]` if present and non-empty after strip — returned as-is if it's in `KINDS`, else
   `"unknown"` (164-166) (a bogus `kind` value is NOT silently coerced).
2. Else `state["prompt"]` if non-empty: first whitespace-token must start with `COMMAND_PREFIX`
   (`/agent-kit:`) or → `"unknown"` (167-171); if it does, `"feature"` when that first token is in
   `FEATURE_COMMANDS` (`/agent-kit:ship`, `/agent-kit:fix`), else `"errand"` (172).
3. Else fall back to `BY_COMMAND.get(state["command"], "unknown")` — a small dict mapping bare
   command names (`ship→feature, fix→feature, sprint→batch, epic→epic, mvp→epic, audit→errand,
   advise→errand, blueprint→errand, accept→errand, next→errand`) (53-55, 173).
Note: `kind` is the winning field and is deliberately never re-derived once written — "the only
signal that cannot be wrong by accident" (146).

**`project_root(start: Path) -> Path | None`** (176-182)
Walks `start` and its parents (after `.resolve()`) looking for the nearest directory containing
`.agent-kit/`. Returns `None` if none found.

**`resume_command(state: dict, directory) -> str`** (185-205)
The command to pick a stopped run back up. If `state["prompt"]` starts with `COMMAND_PREFIX` and
is ≤200 chars → return it verbatim (199-201) (it's literally what the driver would type). Else
look up by `kind(state)` in a small dict: `epic → "/agent-kit:epic --resume <directory>"`,
`batch → "/agent-kit:sprint --resume <directory>"`, `feature → "/agent-kit:ship --run <directory>"`
(202-205). `errand`/`unknown` → `""` (no entry in the dict, `.get` default).

**`branch_shape(name: str) -> bool`** (208-210)
Whether a string looks like a branch this kit made — matches `^[^/]+/.+` (has a `/` not at
position 0). A bare slug (no `/`) returns `False`. Not called anywhere within this sector's files
(guard.py/stop.py never call it) — see UNCERTAIN.

### Module constants (schema-adjacent)
- `RUNS = ".agent-kit/runs"` (27), `MANIFEST = ".agent-kit/project.yml"` (28) — `MANIFEST` is
  defined but not used anywhere in `runfile.py` itself (guard.py/check.py re-derive the manifest
  path themselves rather than importing this constant) — see UNCERTAIN.
- `STALE_AFTER = 24 * 3600` seconds (35) — the "run in flight" freshness window, applied in
  `in_flight` and (independently, via direct `mtime` check) in stop.py's `finished_epic`.
- `TERMINAL = ("done", "blocked", "skipped")` (39).
- `STEPS = ("queued", "design", "build", "verify", "deliver", "done", "blocked", "skipped",
  "building", "closing", "gate", "auditing", "proving")` (40-42) — the full closed set across all
  run kinds; `"closing"` appears in this list but templates/run.json's `_step` doc (line 4) never
  mentions "closing" as a batch-driver step (batch steps mentioned there are only
  building/closing... actually template does list "building | closing" for the driver — confirmed
  consistent).
- `BRANCH_PREFIXES = ("claude/", "sprint/", "epic/")` (44) — not referenced anywhere in
  guard.py/stop.py (guard.py's own `SWITCH`/branch logic doesn't use this constant) — see
  UNCERTAIN.
- `KINDS = ("feature", "errand", "batch", "epic")` (50).
- `COMMAND_PREFIX = "/agent-kit:"` (51).
- `FEATURE_COMMANDS = ("/agent-kit:ship", "/agent-kit:fix")` (52).
- `BY_COMMAND` dict (53-55).

### RUN FILE SCHEMA (field-by-field, per templates/run.json cross-checked against runfile.py/check.py/orchestrate.py usage)

| Field | Type | Allowed values | Writer | Reader |
|---|---|---|---|---|
| `slug` | string | free (kit-generated) | composing session | everywhere (display, resume) |
| `command` | string | `ship\|fix\|sprint\|epic\|mvp\|audit\|advise\|blueprint\|accept\|next` | the run itself | `runfile.kind` fallback (BY_COMMAND), check.py open_runs display |
| `kind` | string | `feature\|errand\|batch\|epic` (else treated "unknown") | the composing session / driver, ideally at design time | `runfile.kind` — wins over all inference |
| `gate` | string | e.g. `"owner"` | — | not read by this sector |
| `entries` | list[str] | knowledge-doc keys | run | check.py (entry-drift comparison) |
| `task` | string\|null | free | run | — |
| `branch` | string\|null | git branch name | run | guard.py (current branch compare — actually guard reads live `git rev-parse`, not this field), check.py (batch branch resolution) |
| `base` | string\|null | git branch name | run | — |
| `parent` | string\|null | slug of prior run in chain | driver (batch chaining) | — |
| `needs` | list[str]\|null | slugs within the same batch | composing session / driver (frame child map) | driver (skip logic) |
| `session` | string\|null | tmux session name | **the driver, when it starts a session** (template comment line 22) | **both hooks** — the sole session-identity signal (guard.py:134, stop.py:85) |
| `deliver` | string | `pr\|branch` | run/driver | — |
| `approach`, `seams` | string / list[str] | free prose | run at Design step | reviewer |
| `tasks` | list[{id,what,done,commit}] | records | run | check.py, reviewer |
| `step` | string | one of `runfile.STEPS`; terminal = `done\|blocked\|skipped` | the run itself, and the driver on batch/epic files (`building`,`closing`,`gate`,`auditing`,`proving`) | **both hooks** (guard: `in_flight`/`building_a_feature`; stop: `unfinished`/`finished_epic`), check.py, orchestrate.py |
| `assumptions` | list[{what,why,entry,expensive}] | records | run | driver (reports expensive ones), check.py |
| `deviations` | list | records | run | — |
| `unmet` | list | records | run | closing session |
| `deferred` | list | records | run | closing session (ledger) |
| `closed_debt` | list | records | run | closing session |
| `blockers` | list | records | run | check.py open_runs display |
| `finish` | object\|null | epic's own plan (`scope`,`lenses`,`waves`,`built`) | epic at gate (+`lenses` at `--advance`) | epic resume |
| `model` | string\|null | model alias/name | brief / epic gate | driver (`/model` on session start) |
| `window` | string\|null | tmux session name of the **owner's** narrating session | driver (batch only) | **never matched by either hook** — deliberately excluded from `session`-matching (stop.py:73-75; guard.py's `building_a_feature`/`holds_tree` also only compare `session`) |
| `waiting_on` | string\|null | free prose | run | driver, window, `next` |
| `answers` | list[{asked,answered,when}] | records | owner via driver | resuming run |
| `review` | {verdict,findings[],security} | object | `agent-kit:reviewer` | check.py (closing gate) |
| `suite` | object\|null | tests/types/lint result | run at Verify | check.py |
| `proved_at` | string\|null | commit SHA | run, whenever `suite` written | check.py (freshness check) |
| `mutation` | {command,killed,survived,why} | object | run at Verify | check.py, reviewer |
| `verified` | list[{kind,command,result,why}] | records | opened at Design from project.yml/verification.yml, completed at Verify | check.py |
| `pr` | string\|null | PR URL/number | run at Deliver | closing session |
| `children` | list | slugs | driver (batch) | driver, check.py |
| `frame` | object\|null | `{child slug: [needs]}` | the batch's frame child | driver (applies once) |
| `prompt` | string\|null | a slash command (or, discouraged, prose) | composing session / driver | **`runfile.kind`** (2nd-priority signal), **`runfile.resume_command`** (1st-priority signal), orchestrate.py `prompt_for` |
| `spent` | object\|null | `{hours,features,sessions}` | driver only | reports |
| `handoff` | string\|null | free prose, <2000 chars | a session handing over | **stop.py `unfinished`** — non-empty handoff exempts a run from the mid-step block (stop.py:98-101); next session resuming |
| `manual` | list[{what,where,proof,when}] | records | run that found it | closing session, `accept` |
| `notes` | string\|null | free prose | run | people, closing session |

Cross-check template vs. code: the template's `_step` doc line (templates/run.json:4) lists
exactly the same step vocabulary as `runfile.STEPS`/`TERMINAL` — consistent. `_kind` doc (line 5)
matches `runfile.KINDS` exactly. `_session` doc (line 22) matches exactly what both hooks actually
do (matches on `session`, not `window`; driver overwrites on every session started; a run with no
session gets no hook opinion). `_handoff` doc (line 93) matches stop.py's handling exactly
(non-empty after strip = exempt).

### RUN DIR LAYOUT
`<project-root>/.agent-kit/runs/<slug>/run.json` — one directory per run, named by slug
(runfile.py:27 `RUNS`, glob pattern `*/run.json` in `runs()` line 112). `.agent-kit/runs/` is
gitignored (stated at runfile.py:71-72) — only exists in the *main* worktree checkout, never in a
linked `git worktree`, which is exactly why `main_worktree()` exists (67-103) and why both hooks
resolve through it rather than trusting `cwd` directly. Nothing else is documented in this sector
as living beside `run.json` within a run directory (comments mention `stack.md` as a *project*-level
doc that `[frame …]` blocks go into, not per-run-directory — templates/run.json:84).

### CONCURRENCY
No file locking, no atomic-write pattern (no temp-file+rename) is present anywhere in
`runfile.py`. `read()` is a plain `Path.read_text()` + `json.loads()`, so a reader can in
principle observe a partial write if a writer is mid-write, but that would raise `ValueError`
(invalid JSON) and be reported as `None`, not silently corrupt — the "fails loud" invariant
extends to catch this case, though it's not a locking mechanism, just an effect of `None`-on-parse-error.
Concurrency between the two hooks and the driver/check.py is handled entirely by convention
(the `session` field + staleness window), not by any OS-level lock. `STALE_AFTER` is explicitly
the kit's mechanism for bounding how long a crashed/abandoned run can keep asserting itself
(runfile.py:31-35).

### IMPORTERS
Four files import `runfile` (confirmed via grep across `plugins/` and `scripts/`):
1. **`plugins/agent-kit/hooks/guard.py`** (line 57) — uses `TERMINAL`, `in_flight`,
   `project_root`, `runs`, `kind`, `main_worktree`.
2. **`plugins/agent-kit/hooks/stop.py`** (line 42) — uses `TERMINAL`, `project_root`, `runs`,
   `kind`, `STALE_AFTER`.
3. **`plugins/agent-kit/scripts/orchestrate.py`** (line 39, the driver) — uses `TERMINAL`
   (aliased `TERMINAL_STEPS`) and `kind`: at line 803, decides whether to `hand_over` a child
   session based on `runfile.kind(child.state()) == "feature"`; at line 1093, decides whether a
   batch child is an `errand` (`runfile.kind(state_of) != "feature"`) to decide whether its
   failure cascades to dependents.
4. **`plugins/agent-kit/scripts/check.py`** (line 48) — re-exports `TERMINAL`, `BRANCH_PREFIXES`,
   `STEPS` as its own module constants (144-146); uses `runfile.kind` (line 2371) to decide
   feature-vs-errand for what a run file is held to (suite/proved_at/mutation required only for
   features); flags a run whose `kind` is genuinely unknowable while still `queued` (2379-2388);
   uses `runfile.read` (2779) to read a batch child's file when comparing entries; uses
   `runfile.resume_command` (2842) to populate `open_runs()`'s resume suggestion; uses
   `runfile.runs` (2927) to list directories with proved_at/mutation evidence; uses
   `runfile.in_flight` (3340) to print the preflight "a run is in progress" statement before every
   command (per its own docstring, rules/preflight.md).

## NODES
```
hook:guard        | hook    | guard.py (PreToolUse/Bash)        | Refuses merge/force-push/push-to-default/branch-switch-of-held-tree/whole-product-walk while a kit run is in flight | plugins/agent-kit/hooks/guard.py:1
hook:stop          | hook    | stop.py (Stop, all)               | Blocks turn-end while this session's own run is mid-step; closes the session of a finished `epic` | plugins/agent-kit/hooks/stop.py:1
script:runfile     | script  | scripts/runfile.py                | Shared "what a run is" module: schema constants, read/runs/in_flight/kind/project_root/resume_command | plugins/agent-kit/scripts/runfile.py:1
script:orchestrate | script  | scripts/orchestrate.py (driver)   | Starts/watches child sessions, writes `session`/`window`/`spent`/`frame`, hands over features | plugins/agent-kit/scripts/orchestrate.py:39
script:check       | script  | scripts/check.py                  | Validates run files against the schema; prints preflight in-flight statement | plugins/agent-kit/scripts/check.py:48
file:run.json      | file    | .agent-kit/runs/<slug>/run.json   | One run's state, per templates/run.json shape | plugins/agent-kit/templates/run.json:1
file:project.yml   | file    | .agent-kit/project.yml            | Project manifest: commands.e2e, verification.* — read by guard for the e2e-walk rule | plugins/agent-kit/hooks/guard.py:143
cmd:gh-pr-merge    | cmd     | `gh pr merge`                     | Refused unconditionally while a run is in flight | plugins/agent-kit/hooks/guard.py:72
cmd:git-push-force | cmd     | `git push --force\|-f\|--force-with-lease\|+refspec` | Refused unconditionally while a run is in flight | plugins/agent-kit/hooks/guard.py:73
cmd:git-push-default | cmd   | `git push` to the default branch  | Refused while a run is in flight | plugins/agent-kit/hooks/guard.py:74,256-262
cmd:git-checkout-switch | cmd | `git checkout`/`git switch` (not `-- path`) | Refused when this checkout is shared and held by another session's run | plugins/agent-kit/hooks/guard.py:78,217-221
cmd:e2e-walk       | cmd     | project's declared `commands.e2e` | Refused inside a `ship`/`fix` session mid-flight, unless it matches the feature's own declared verification | plugins/agent-kit/hooks/guard.py:243-248
session:owner      | session | the owner's own terminal/window   | Never matched by either hook (no `session`/`window` field points at it while it's driving) | plugins/agent-kit/hooks/stop.py:14-15
session:feature    | session | a `ship`/`fix` child session       | Registered via `run.json.session`; blocked by stop.py mid-step; refused e2e-walk/merge/force/push by guard.py | plugins/agent-kit/templates/run.json:22-23
session:epic       | session | an `epic`'s gate/hand-back session | Registered via `session`; stop.py never blocks its own in-flight steps but closes it once terminal & fresh | plugins/agent-kit/hooks/stop.py:108-130
ext:tmux           | ext     | tmux                              | Session-identity source (`display-message -p "#S"`) for both hooks; kill mechanism in stop.py fallback | plugins/agent-kit/hooks/guard.py:121, stop.py:62,165
ext:claude-close   | ext     | claude-close helper binary        | Preferred session-close mechanism in stop.py, found via `shutil.which` | plugins/agent-kit/hooks/stop.py:148
ext:git            | ext     | git subprocess                    | guard.py: current branch, default branch, HEAD checks; runfile.py avoids it on the hot path (`main_worktree` reads files instead) | plugins/agent-kit/hooks/guard.py:95-107
```

## EDGES
```
hook:guard        -> file:run.json        | reads (runfile.runs/in_flight)         | every Bash call                          | plugins/agent-kit/hooks/guard.py:279-281
hook:guard        -> file:project.yml     | reads (declared_e2e/declared_verification) | only while building_a_feature is true | plugins/agent-kit/hooks/guard.py:283-286
hook:guard        -> ext:git              | subprocess (rev-parse, symbolic-ref)   | every in-flight Bash call                | plugins/agent-kit/hooks/guard.py:95-107,284
hook:guard        -> ext:tmux             | subprocess (display-message)           | my_session() / building_a_feature/holds_tree | plugins/agent-kit/hooks/guard.py:121-125
hook:guard        -> cmd:gh-pr-merge      | deny                                    | MERGE regex matches, run in flight       | plugins/agent-kit/hooks/guard.py:249-252
hook:guard        -> cmd:git-push-force   | deny                                    | FORCE regex matches, run in flight       | plugins/agent-kit/hooks/guard.py:253-255
hook:guard        -> cmd:git-push-default | deny                                    | PUSH regex + pushes_default, run in flight | plugins/agent-kit/hooks/guard.py:256-262
hook:guard        -> cmd:git-checkout-switch | deny                                 | SWITCH regex + holds_tree(root)          | plugins/agent-kit/hooks/guard.py:217-221
hook:guard        -> cmd:e2e-walk         | deny                                    | building_a_feature + e2e substring + no own_checks match | plugins/agent-kit/hooks/guard.py:243-248
session:feature    -> hook:guard          | PreToolUse fires before its Bash calls  | every Bash tool call in that session      | plugins/agent-kit/hooks/hooks.json:4-15
session:owner      -> hook:guard          | PreToolUse fires, but never refuses (no run keyed on it) | every Bash call, no-op outside a run | plugins/agent-kit/hooks/guard.py:280-281
script:orchestrate -> file:run.json       | writes `session`, `window`, `step`, `spent`, `frame`, `needs` | starting/watching a child, applying frame map | plugins/agent-kit/templates/run.json:22,55,90,84
script:orchestrate -> session:feature     | starts and types prompt into            | building a batch child                    | plugins/agent-kit/scripts/orchestrate.py:794-803
script:check       -> file:run.json       | reads (validates schema, entries, kind) | check.py --run / preflight               | plugins/agent-kit/scripts/check.py:2371,2779,2927,3340
hook:stop          -> file:run.json       | reads (runfile.runs, mtime)             | every Stop event in a tmux session        | plugins/agent-kit/hooks/stop.py:84-85,125
hook:stop          -> ext:tmux            | subprocess (display-message; kill-session fallback) | my_session(); close_myself() when no claude-close | plugins/agent-kit/hooks/stop.py:62,165
hook:stop          -> ext:claude-close    | subprocess, no args                     | close_myself() when helper present        | plugins/agent-kit/hooks/stop.py:148-151
hook:stop          -> session:feature     | decision:block (refuses to end turn)     | this session's own run mid-step, not epic, no handoff | plugins/agent-kit/hooks/stop.py:201-208
hook:stop          -> session:epic        | closes (via close_myself)                | this session's own epic run is terminal & fresh, and no other unfinished run of this session | plugins/agent-kit/hooks/stop.py:192-199
session:epic       -> hook:stop           | Stop fires, but stands aside on its own in-flight steps | gate/building/auditing/proving | plugins/agent-kit/hooks/stop.py:94-96
session:owner      -> hook:stop           | Stop fires, but no-ops (no session match, or matched only via window which is ignored) | every turn end in owner's window | plugins/agent-kit/hooks/stop.py:73-75,186-187
script:runfile     -> file:project.yml    | (constant only, not enforced)            | MANIFEST constant defined but unused      | plugins/agent-kit/scripts/runfile.py:28
hook:guard         -> script:runfile      | imports                                  | module load, sys.path insert              | plugins/agent-kit/hooks/guard.py:55-57
hook:stop          -> script:runfile      | imports                                  | module load, sys.path insert              | plugins/agent-kit/hooks/stop.py:40-42
script:orchestrate -> script:runfile      | imports                                  | module load                                | plugins/agent-kit/scripts/orchestrate.py:39
script:check       -> script:runfile      | imports                                  | module load                                | plugins/agent-kit/scripts/check.py:48
```

## UNCERTAIN / CONTRADICTORY

1. **`runfile.MANIFEST` constant is defined but never used.** `runfile.py:28` defines
   `MANIFEST = ".agent-kit/project.yml"`, but no function in `runfile.py` reads it, and neither
   `guard.py` (which reads the same path by hardcoding `root / ".agent-kit" / "project.yml"` at
   guard.py:143,167) nor `check.py` imports/uses `runfile.MANIFEST` (confirmed by grep — no hit
   for `runfile.MANIFEST` anywhere). Dead constant, or a signal the manifest path constant should
   have been shared but wasn't wired up.

2. **`runfile.BRANCH_PREFIXES` is defined but not used by guard.py's own branch logic.**
   `runfile.py:44` — `("claude/", "sprint/", "epic/")`. `check.py` re-exports it as its own module
   constant (`check.py:145`) but grep shows no use of `BRANCH_PREFIXES` inside guard.py at all;
   guard.py's default-branch/push checks work off `git symbolic-ref`/whole-word matching, not this
   prefix list. Whether `check.py` itself uses it beyond re-export wasn't traced (out of this
   sector's required files) — worth flagging as a maybe-dead shared constant from this sector's
   point of view.

3. **`branch_shape()` is unused within this sector.** `runfile.py:208-210` defines it but neither
   `guard.py` nor `stop.py` call it (confirmed by grep — no `branch_shape` hit in either file).
   It may be used by `check.py` or `orchestrate.py` outside what was grepped for "runfile." — not
   confirmed either way from this pass; flagging as a function with no reader found in this
   sector's search space.

4. **Divergent treatment of an unreadable run file between the two hooks.** `guard.py`'s
   `in_flight()` (via `runfile.in_flight`) treats a run file nothing can parse as *in flight*
   (state is None → still counted, runfile.py:138) — deliberately, to avoid silently disarming the
   merge guard. `stop.py`'s `my_runs()` does the opposite: it filters with `state is not None`
   (stop.py:85), so an unreadable run file is *never* "this session's run" and can neither block
   the turn nor be treated as a finished epic. Both are individually justified in their own
   docstrings (guard.py:14-18 "fails wrong the safe way"; stop.py:78-79 "cannot be shown to be
   this session's run") but the two hooks read the identical signal (`runfile.read` returning
   `None`) in opposite directions. Not a bug per the tests (each hook's test suite pins its own
   behavior), but a real asymmetry a full kit map should surface.

5. **Guard's `verdict()` push-to-default detection has a subtlety not fully spelled out in
   prose.** `pushes_default` (guard.py:257-259) is true if the default branch name appears as a
   whole word ANYWHERE in the command (so `git push origin feature-branch --tags && echo main`
   would technically match `main` as a stray word) OR (branch==default AND the push has no
   explicit `remote+refspec` pair, detected by a regex checking for *any* two space-separated
   tokens after `git push` with no flags stripped out — `re.search(r"\bgit\s+push\b[^&|;]*\s\S+\s+\S+", command)`
   at line 258). This second sub-check is a heuristic ("no explicit remote and ref") rather than a
   proper flag parse — e.g. `git push -u origin` (missing explicit ref, 2 tokens after flags) could
   misparse. Not contradicted by any test found, but the regex is looser than the prose ("a bare
   push") suggests; flagging as a place accuracy depends on a regex heuristic rather than a real
   command parse.

6. **`declared_e2e`/`declared_verification` are a hand-rolled YAML subset reader, not real YAML.**
   guard.py:140-180 parses `.agent-kit/project.yml` line-by-line looking for top-level
   `commands:`/`verification:` blocks by indentation alone, stripping `#`-comments naively (does
   not handle a `#` inside a quoted string, for instance). This is explicitly by design ("a hook
   that started interpreting a manifest would be a second opinion about a file that has an owner,"
   guard.py:163-165) but it means unusual YAML (multi-line strings, flow-style mappings) in
   `project.yml` could silently fail to be detected, and the e2e-walk / own-checks exemption would
   not fire as expected — a false negative, not a crash, since `declared_e2e` degrades to `""`.

7. **`STEPS` in runfile.py includes `"closing"` which templates/run.json's `_step` doc string
   does mention** (`"building | closing, which only a driver writes on a batch's own file"` —
   templates/run.json:4) — this one is actually consistent on closer read, not a contradiction;
   noted here only because it looked suspicious on first pass and was verified against the
   template text directly.

8. **No file/dir is documented as living beside `run.json` inside a run directory**, in either
   `runfile.py` or `templates/run.json`. The `_frame` field's docstring (templates/run.json:84)
   references `stack.md` and `[frame …]` blocks, but as a *project-level* document, not something
   under `.agent-kit/runs/<slug>/`. Within this sector's reading, a run directory appears to
   contain exactly one file, `run.json`, and nothing else — worth the full map confirming whether
   any other sector's code writes additional files into a run directory.
```
