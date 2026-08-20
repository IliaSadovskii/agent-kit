# Sector: orchestrate (the driver)

File: `/projects/agent-kit/plugins/agent-kit/scripts/orchestrate.py` (1361 lines)
Tests: `/projects/agent-kit/tests/test_orchestrate.py` (1539 lines)
Imports: `check.run_defects` (l.38), `runfile` (l.39), both from the same `scripts/` dir, added to
`sys.path` at l.37. Stdlib only, Python 3.9+.

Module docstring (l.2-14) claims: "It reads run files, watches a transcript's modification time,
knows one HTTP status, and calls git and gh." **Three of those four are wrong today** — it reads
transcript *record timestamps* not mtime (l.304-327, mtime is only a fallback), it knows *two* HTTP
statuses (429 and 529, l.47-48), and it never calls `gh` at all (grep: the only non-tmux, non-helper
subprocess is `git ls-remote`, l.991).

---

## CLI REFERENCE

One command, no subcommands. `orchestrate.py <run-dir> [options]`.
Built in `main()` at l.1296-1314.

| arg/flag | type | default | effect | file:line |
|---|---|---|---|---|
| `run_dir` (positional, required) | `Path` | — | `.agent-kit/runs/<slug>/` of the batch to drive. Resolved to absolute at l.1316. Must contain `run.json` or the program prints `no run file in <dir>` to stderr and returns 1. | l.1298, l.1316-1319 |
| `--poll` | int (seconds) | `60` | Seconds slept at the top of every watch iteration (l.693). Also doubles as (a) the idle threshold for accepting a handoff note (`idle > self.opt.poll`, l.713), (b) the fallback limit-wait when no reset time is parsed (`self.opt.poll * 5`, l.750), (c) the extra sleep after a nudge (l.785). | l.1299 |
| `--hang` | int (minutes) | `30` | Minutes of transcript silence before a live session counts as stuck: `idle < self.opt.hang * 60` is the "healthy" branch (l.718). | l.1300 |
| `--ceiling` | int (thousands of tokens) | `210` | A session whose context passes this is asked, once, to hand its run over. `0` disables the whole handoff mechanism (`ceiling <= 0` → `handoff_due` returns False, l.481-482). Rationale (cost curve, not context window) is 100 lines of docstring at l.424-480. | l.1301-1304 |
| `--room` | int (thousands of tokens) | `40` | The session must also have grown by this much over its opening context (`size - floor >= room * 1000`, l.483). Described as a safety net that binds only where the ceiling is under ~86k. | l.1305-1309 |
| `--max-wait` | float (hours) | `6` | A rate-limit reset further away than this is treated as a weekly limit: `self.stopping = True` and the whole run stops (l.751-754). | l.1310 |
| `--model` | str | `None` | Model typed as `/model <name>` into every session this run starts — **unless** the run file being watched names its own `model`, which wins (`Driver.model_for`, l.613-617; `Launcher.start` l.184). | l.1311-1313 |

There are **no** flags for: worktrees, parallelism, dry-run, resume, log level, or a session limit.
`--resume` exists on the *kit commands* (`/agent-kit:epic --resume`), not on this program; resuming
is simply running the driver again over a run dir whose terminal children are skipped (l.1074).

Exit codes: `0` from `driver.go()` after the closing session ran (l.1124); `1` for missing run file
(l.1319), missing tmux (l.1342), a live sibling session (l.1356), no children (l.1008); `0` after a
successful self-detach into systemd (l.1329).

---

## SESSION MODEL

### Spawning — `Launcher.start` (l.156-187)

1. `self.reclaimed = None` (l.166).
2. If `self.alive(name)` — i.e. `tmux has-session -t <tmux_name>` returns 0 (l.203-204) — then
   `self.stop(name)`, record `self.reclaimed = name`, `time.sleep(1)` (l.167-170). Rationale at
   l.157-165: `claude-new` prints "that name is taken" and **exits 0**, so trusting the exit code
   typed the prompt into a stranger's session. Test: `test_a_taken_name_is_closed_before_anything_is_typed`
   (tests l.1314-1321), `test_a_free_name_is_left_alone` (tests l.1371).
3. If `claude-new` is on the PATH (`shutil.which("claude-new")`, l.142):
   `claude-new <name> <cwd>` (l.172). Non-zero → `start` returns False.
4. Otherwise plain tmux (l.176-180):
   `tmux new-session -d -s <agent-kit-name> -c <cwd> "claude --dangerously-skip-permissions --remote-control"`
   — the claude argv is joined with spaces into a single shell string (l.177-178).
5. `time.sleep(5)` for the session to reach its prompt (l.181).
6. Model: `model or self.model`; if set, `send(name, f"/model {model}")` then `time.sleep(2)`
   (l.184-186). Typed, not passed as a flag, because `claude-new` takes no model (l.182-183).
7. `return self.send(name, prompt)` (l.187).

### Naming

- `Launcher.tmux_name(name)` = `cc-<name>` when the helper exists, else `agent-kit-<name>` (l.153-154).
- `Driver.numbered(name, segment)` (l.573-581): segment 1 → `name[:60]`; segment ≥ 2 → `f"{name[:56]}-{segment}"`.
- Feature child session name: `child.slug[:60]` (l.797).
- Closing session: `f"{self.run.slug}-close"[:60]` (l.1145).
- Epic hand-back session: `f"{above.slug}-advance"[:60]` (l.1184).
- The session killed at the top of `go()`: `f"{parent}-advance"[:60]` (l.1020).

### Identification / tracking

- `run.set(session=self.launcher.tmux_name(current))` immediately after every start (l.648, l.681)
  and after the hand-back start (l.1195, guarded on `started`). Comment l.644-647: **the stop hook
  matches a session to its run on this field and on nothing else** (`docs/design/stop-hook.md`).
  Test: `test_the_session_that_takes_a_handoff_is_numbered_and_the_run_file_follows` (tests l.1034),
  `test_a_session_that_did_not_start_is_not_named` (tests l.1268).
- `Driver.watched` holds the current numbered name (l.570, set at l.637 and l.676) so `build`/`close`
  can stop the *latest* segment (l.804, l.1148).
- The **transcript** is the heartbeat: `newest_transcript(cwd, after, mark)` (l.246-278) globs
  `~/.claude/projects/<slugified-cwd>/*.jsonl`, drops files with `mtime < after`, drops files whose
  *first record timestamp* is more than 60 s before `after` (l.271 — the fix for reading the owner's
  own 370k window), then prefers the file whose first 12 lines contain the run slug (l.275-277),
  else newest by mtime. Tests: `TranscriptPickingCase` (tests l.864-899).

### Detected dead

- `gone = not self.launcher.alive(current)` — `tmux has-session` (l.707).
- `idle = now - (last_spoke(transcript) or transcript.stat().st_mtime)` (l.705-706). `last_spoke`
  (l.304-327) scans the last 200 lines of the tail for ISO `"timestamp"` fields and takes the max;
  the mtime fallback exists only when the tail carries none. Rationale l.306-313: an empty harness
  touch bought 21 minutes of false liveness on a live run. Test: `SilenceCase` (tests l.1439-1467).
- No transcript found within 300 s of launch → give up: `"no transcript — the session cannot be watched"`
  (l.700-703).

### Closing — `Launcher.stop` (l.206-230)

- helper present **and** no `claude-close`: print a one-time stderr warning (`warned_closer`,
  l.216-222) then fall through to `tmux kill-session -t <tmux_name>` (l.230).
- `claude-close` present: run `claude-close <name>`; on non-zero print the refusal to stderr; **return
  without killing** (l.223-229). Rationale l.208-215: a registered session killed without being
  unregistered was restored by a watchdog a minute later.
- neither: `tmux kill-session -t <tmux_name>`, silently (l.230).
- Tests: `LauncherCase` tests l.1339-1370.

### Worktrees

**The driver manages no worktrees.** No `git worktree` call anywhere; the only git call is
`git ls-remote --heads origin <branch>` (l.991). `runfile.main_worktree` exists but is not imported
or used here.

---

## STATE MACHINE

`runfile.TERMINAL = ("done", "blocked", "skipped")` (runfile.py l.39), aliased as `TERMINAL_STEPS`
(l.42). `runfile.STEPS` also lists `queued, design, build, verify, deliver` — the driver never writes
those; the `ship` session does.

`Run.terminal()` (l.124-126) = `step in TERMINAL_STEPS` **or** `own_pr()` is truthy.
`Run.own_pr()` (l.101-122) = `state["pr"]`, unless `state["parent"]`'s run file carries the *same*
`pr`, in which case `None` — an inherited epic-wide pull request is not evidence about this batch.
Tests: `InheritedPullRequestCase` (tests l.1182-1226).

### Batch run (`run_dir/run.json`)

| state | stored where | set by | transitions to | condition |
|---|---|---|---|---|
| (whatever the composing session left, usually `queued`) | `run.json.step` | `sprint`/`epic` session | `building` | driver starts and `children` is non-empty (l.1022) |
| — | — | — | *(none — early exit)* | `children` empty → `event("empty")`, `tell`, `hand_back`, return 1 (l.1000-1008). **`step` is never written.** |
| `building` | `run.json.step` | driver l.1022 | `closing` | the child loop drained (l.1120) |
| `closing` | `run.json.step` | driver l.1120 | `done` | after `close()`: closing session's `step` is terminal **or** `own_pr` is truthy (l.1154-1155) |
| `closing` | `run.json.step` | driver l.1120 | `blocked` | otherwise (l.1161) |
| `done` / `blocked` | — | driver | *(terminal)* | both then call `hand_back(state)` (l.1159, l.1165) |

### Child run (`../<slug>/run.json`)

| state | stored where | set by | transitions to | condition |
|---|---|---|---|---|
| `queued` | child `run.json.step` | composing session / template | `skipped` | `self.stopping` is true when its turn comes (l.1070-1072) |
| `queued` | — | — | `skipped` | `slug in self.skip` or any of its `needs` is in `self.skip` (l.1104-1109); the slug is then added to `skip` so its own dependents cascade (l.1106) |
| `queued` | — | — | *(session writes `design`→…→`done`/`blocked`)* | `build()` watches it (l.795-829) |
| any | — | driver | `done` | `build()` found the branch pushed on origin while the file was behind (l.822-825) |
| any | — | driver | `blocked` | `build()` ended with no terminal state and no pushed branch (l.827-828) |
| terminal | — | — | *(skipped by the loop)* | `child.terminal()` at l.1074; if `step == "done"` it still counts as built and `apply_frame` runs (l.1076-1079) |

Other fields the driver writes into run files:
`session` (l.648, 681, 1195), `spent` (child: l.812; batch: l.1139), `blockers` (l.862, l.965),
`needs` (siblings, l.936), `base`/`parent` (l.988), `children` (reordered, l.945).

Fields the driver **reads and never writes**: `children`, `window`, `model`, `parent`, `base`,
`prompt`, `handoff`, `frame`, `assumptions`, `command`, `kind`, `pr`, `branch`.

---

## STEP-BY-STEP per subcommand

There is one entry point. Below is `main()` → `Driver.go()` in order.

### A. `main()` (l.1296-1357)

1. Parse args (l.1297-1314).
2. `run_dir = options.run_dir.resolve()`; if `run_dir/run.json` is not a file → stderr
   `no run file in <dir>`, return 1 (l.1316-1319).
3. **Self-detach** (l.1323-1333). If `os.environ["AGENT_KIT_DRIVER_DETACHED"] != "1"` and
   `dies_with_its_session(own_cgroup())` — `/proc/self/cgroup` contains both `tmux-spawn` and
   `.scope` (l.1249-1251) — then `detach()` builds and runs:

   ```
   systemd-run --user --collect --quiet --unit=agent-kit-<sanitised-slug> \
     --setenv=AGENT_KIT_DRIVER_DETACHED=1 --setenv=PATH=<inherited PATH> \
     --working-directory=<cwd> <sys.executable|python3> <abs path to orchestrate.py> <original argv>
   ```
   (`detach_command`, l.1260-1277; `subprocess.run(..., timeout=30)` at l.1287.)
   On success: print `driver moved out of its session's control group as <unit> — journalctl --user -u <unit> has its output`, log `event("detached", unit)`, **return 0** (l.1325-1329).
   On failure: print the long stderr warning and log `event("detach-failed", why)`, then carry on
   inside the doomed control group (l.1330-1333).
   `unit_name` (l.1254-1257): `re.sub(r"[^A-Za-z0-9-]", "-", slug)[:60].strip("-") or "run"`, prefixed
   `agent-kit-`. Tests: `DetachCase` (tests l.1469-1539).
   The 30-line comment at l.1213-1236 records that `nohup` and `setsid` both fail here — tmux 3.4 puts
   each pane in a systemd scope with `KillMode=control-group`.
4. `shutil.which("tmux")` — absent → the two-line explanation and return 1 (l.1338-1342).
5. `cwd = project_root(run_dir)` — nearest ancestor named `.agent-kit`, take its parent; else
   `Path.cwd()` (l.1206-1210).
6. **Single-driver check** (l.1350-1356): for each slug in the batch's `children`, if the child's
   run file exists, is not terminal, and `launcher.alive(slug[:60])` → stderr
   `<slug> still has a live session — another driver is already on this run`, return 1.
7. `return driver.go()`.

### B. `Driver.go()` (l.997-1124)

1. Read state; if no `children`: `event("empty", ...)`, `tell(...)`, `hand_back(state)`, return 1
   (l.998-1008). Test: `test_a_run_with_no_children_hands_back_instead_of_stopping_in_silence`
   (tests l.797).
2. If `state["parent"]`: `launcher.stop(f"{parent}-advance"[:60])` — kill the epic session that
   started this driver (l.1018-1020). Comment l.1010-1017 explains why the session cannot be trusted
   to close itself.
3. `run.set(step="building")`; `event("start", "<n> features")`; `event("window", <window> or "none — the run will have no narrator")` (l.1022-1025).
4. Snapshot `authored = {slug: <child's authored parent>}` **before** the loop, because `chain()`
   rewrites `parent` as it goes (l.1030-1035).
5. Loop (l.1036-1118), re-reading `children` from disk on **every** iteration (l.1042) so a session
   may reorder/extend the queue mid-run; `seen` prevents rebuilding:
   1. `remaining = [s for s in children if s not in seen]`; empty → break (l.1042-1045).
   2. `slug = remaining[0]`; `seen.add(slug)` (l.1046-1047).
   3. If the child has no `run.json` → `event("missing", ...)`, continue (l.1050-1052).
   4. `take_control(self.run)` (l.546-553): read `run_dir/control`, strip it, **unlink it**, return
      the text.
      - starts with `skip` → target is the word after it, or this slug; add to `self.skip`;
        `event("control", "skip <target>")` (l.1055-1058).
      - `== "stop"` → `event("control", "stop")`, `self.stopping = True` (l.1059-1061).
      - anything else non-empty → `event("control", "not recognised, ignored: <60 chars>")` and
        `tell(...)` naming the two words (l.1062-1068). Test: tests l.819.
   5. `self.stopping` → `child.set(step="skipped")`, continue (l.1070-1072).
   6. `child.terminal()` → `event("already-terminal", slug)`; if `step == "done"`, `built += 1`,
      `last = child`, `apply_frame(child, state)` (l.1074-1080).
   7. `errand = runfile.kind(state_of) != "feature"` (l.1093).
   8. `needs`: the child's own `needs` list if it is a list, else `[authored[slug]]` if that parent
      exists, else `[]` (l.1099-1103).
   9. If `slug in self.skip` or any need is in `self.skip`: add `slug` to `skip`,
      `child.set(step="skipped")`, `event("skipped", ...)`, continue (l.1104-1109).
   10. `chain(child, last, state["base"])` (l.1111 → l.969-988): set `base` to the last built
       feature's `branch`, else the batch's `base`; set `parent` to `last.slug` or `None`. With
       neither, `note_defect(...)` (l.981-985). No-op when both already match (l.986-987).
   11. `tell(f"starting {slug}")` (l.1112).
   12. `build(child)` (l.1113 → below). `"built"` → `built += 1`, `last = child`,
       `apply_frame(child, child.state())`. Otherwise, if it is **not** an errand,
       `self.skip.add(slug)` so its dependents cascade (l.1117-1118).
6. `run.set(step="closing")`; `event("children-done", "<built>/<len(seen)> built")` (l.1120-1121).
7. `record_spend(built)` (l.1122 → l.1126-1141): accumulates
   `spent = {hours: prev + (now - self.began)/3600 rounded to 1, features: prev + built, sessions: prev + self.sessions}`.
8. `close()` (l.1123). Return 0 (l.1124).

### C. `Driver.build(child)` (l.795-829)

1. `name = child.slug[:60]`.
2. `why = self.watch(name, child, self.prompt_for(child), hand_over=runfile.kind(child.state()) == "feature")`
   (l.802-803).
   `prompt_for` (l.831-846): the child's own `prompt` if non-empty, else
   **`/agent-kit:ship --run <child.dir>`** (l.846). Test: tests l.776.
3. `launcher.stop(self.watched or name)` (l.804).
4. `child.set(spent={"sessions": max(before, self.segments)})` (l.811-812).
5. If `child.own_pr(state)` or `step == "done"`: `audit(child, state)`, `costly(child, state)`,
   `child.event("built", branch)`, return `"built"` (l.817-821).
6. Else if `state["branch"]` and `branch_pushed(branch)` — `git ls-remote --heads origin <branch>`
   with `cwd=self.cwd`, truthy stdout (l.990-993) — then `child.set(step="done")`,
   `event("built", "<branch> — found pushed, the run file was behind")`, return `"built"`
   (l.822-826). Test: tests l.296.
7. Else `child.set(step="blocked")`, `event("blocked", why or "no terminal state")`, return
   `"blocked"` (l.827-829).

`audit` (l.848-864): `run_defects(state, self.cwd)` from `check.py`; if any, append to the child's
`blockers` (so the closing session reads them), `event("closed-with-defects", ...)`, `tell(...)`.
`costly` (l.866-887): every `assumptions[i].expensive` truthy → one `tell` line naming the count and
the first `what`, truncated to 120 chars. Explicitly one-way: no `wait`, no way for the owner to
answer (l.874-879). Tests: `WindowNoticeCase` tests l.1417-1437.

### D. `Driver.watch(name, run, prompt, hand_over=True)` (l.619-791)

Setup (l.636-662): `current = numbered(name, 1)`, `self.watched = current`, `self.segments = 1`,
`model = model_for(run.state())`; `launcher.start(...)` — False → return
`"could not start a session"` (l.640-641); `self.sessions += 1`;
`run.set(session=launcher.tmux_name(current))`; `run.event("session-start", "<name>[ on <model>]")`;
`launched = time.time() - 1`. Per-session flags reset: `transcript=None`, `restarts=0`, `segment=1`,
`floor=0`, `nudged=False`, `asked=False`, `blind=False`, `note_before=""`.

Poll loop (l.692-791), each iteration:

1. `time.sleep(self.opt.poll)` (l.693).
2. `run.terminal()` → return `""` (l.695-696).
3. Transcript not yet found → `newest_transcript(self.cwd, launched, run.slug)`; still none and
   `now - launched > 300` → return `"no transcript — the session cannot be watched"`; else continue
   (l.698-703).
4. `spoke = last_spoke(transcript)`; `idle`; `gone`; `tail = read_tail(transcript)` — last 40 lines
   out of the last 400_000 bytes (l.330-348; the 400k window is justified at l.331-339 by a measured
   273k-character record over 186 sessions).
5. **Handoff landed** (l.712-716): `note = run.state()["handoff"].strip()`; if `asked` and `note` and
   `note != note_before` and (`gone` or `idle > poll`) → `fresh("<slug> carried on in a new session", "handed-off")`;
   failure → return `"could not start the session that takes the handoff"`.
   `note_before` exists because nothing ever clears `handoff` (l.658-662). Test: tests l.1090.
6. **Healthy branch** (l.718-744), taken when `idle < hang*60` and not `gone`:
   - `size = context_size(tail)` — the **max** `record_size` over the tail's lines (l.382-397);
     `record_size` (l.354-379) `json.loads` each line and sums `usage.input_tokens +
     usage.cache_creation_input_tokens + usage.cache_read_input_tokens`, **once** (the earlier regex
     double-counted `usage.iterations[]`, l.357-362).
   - `floor = floor or opening_size(transcript)` — first usage record in the first 40 lines
     (l.400-421), 0 when unreadable.
   - `hand_over and not blind and not floor and size` → `blind = True`,
     `event("floor-unreadable", "no opening usage record — `room` cannot apply and the ceiling of <N>k decides this session alone")`
     (l.728-732). Test: tests l.949.
   - `hand_over and not asked and handoff_due(size, floor, ceiling, room)` (l.424-483:
     `size > ceiling*1000 and size - floor >= room*1000`, False when `size` is 0 or `ceiling <= 0`) →
     `launcher.send(current, HANDOFF_LINE)`; on success `asked = True`, `note_before = note`,
     `event("handoff-asked", "context <N>k over a floor of <M>k after <T>m")` (l.733-743).
     `HANDOFF_LINE` is l.43-46 and points the session at "the Handing over section of skills/ship/SKILL.md".
   - `continue`.
7. **Something stopped**: `kind, when = limit_reset(tail)` (l.486-509).
   - `"limit"` (429, l.47): `wait = when - now` if a reset time parsed, else `poll * 5` (l.750).
     - `wait > max_wait*3600` → `self.stopping = True`, `tell("<slug>: a weekly limit, not a session one — stopping the run")`, return `"limit resets in <N>h"` (l.751-754). Test: tests l.213.
     - `wait > 0` → `event("limit", "sleeping <N>m")`, `tell(...)`, `time.sleep(wait + 60)` (l.755-758).
     - Then if the session is still alive and `send(current, "continue")` succeeds →
       `event("resumed", "typed into the live session")`, continue (l.761-763).
     - Else `restart("session was gone after the limit")`, else return `"did not come back after the limit"` (l.764-766).
   - `"overloaded"` (529, l.48) and not gone: `event("overloaded", "retrying shortly")`,
     `time.sleep(120)`, `send(current, "continue")`, continue (l.768-772).
8. `why = "session died" if gone else f"no progress for <N>m"` (l.774).
9. **Nudge before restart** (l.782-786): live, not yet nudged, and `send(current, "continue")` works →
   `nudged = True`, `event("nudged", "<why> — typed into the live session")`, `time.sleep(poll)`,
   continue. Test: tests l.161.
10. `event("stalled", why)`; `restart(why)` → continue; else return `why` (l.788-791).

`fresh(why, event)` (l.664-683): stop the current session, reset transcript/launched/nudged/asked/
blind/floor, `segment += 1`, `current = numbered(name, segment)`, update `self.watched`/`self.segments`,
`launcher.start(...)`, `self.sessions += 1`, `run.set(session=...)`, `run.event(event, "<why> — session <n>")`.
`restart(why)` (l.685-690): `restarts += 1`; **more than one restart per `watch()` call is refused**
(`if restarts > 1: return False`), otherwise `fresh(why, "restarted")`.

### E. `Driver.close()` (l.1143-1165)

1. `name = f"{self.run.slug}-close"[:60]`.
2. `watch(name, self.run, f"/agent-kit:sprint --close {self.run.dir}", hand_over=False)` (l.1146-1147).
   **This is the exact command line.** `hand_over=False` because the closing session has nobody to
   hand to (l.626-630; test tests l.1120).
3. `launcher.stop(self.watched or name)` (l.1148).
4. Re-read state. `step in TERMINAL_STEPS or own_pr(state)` → `set(step="done")`,
   `event("done", "pr=<n>")`, `audit(self.run, ...)`, `tell("the batch is finished, pull request <n>")`,
   `hand_back(state)`, return (l.1154-1160).
5. Else `set(step="blocked")`, `event("close-failed", why or "the closing session left no terminal step")`,
   `tell("the features are built and pushed, but the batch was never closed — its branch, its pull request body and its digest need finishing by hand")`,
   `hand_back(state)` (l.1161-1165). Tests: tests l.242, l.307.

### F. `Driver.hand_back(state)` (l.1167-1200)

1. `parent = state["parent"]`; none → return (l.1176-1178).
2. `above = Run(self.run.dir.parent / parent)`; if `above.state()["command"]` is not `"epic"` or
   `"mvp"` (the pre-2.0.0 name) → return (l.1182).
3. `name = f"{above.slug}-advance"[:60]`; `event("hand-back", "<parent> decides what follows")`.
4. `started = launcher.start(name, f"/agent-kit:epic --advance {above.dir}", model_for(above.state()))`
   (l.1186-1187). **This is the exact command line.**
5. `started` → `above.set(session=launcher.tmux_name(name))` so the stop hook can close it
   (l.1188-1195). Tests: `HandBackCase` tests l.1262, l.1268.
6. `launcher.reclaimed` → `above.event("reclaimed", "<name> was still up from an earlier batch — closed it first")` (l.1196-1197).
7. Not started → `above.event("stalled", "could not start the session that decides the next batch")`
   and `tell(f"{above.slug} needs /agent-kit:epic --resume — the next batch did not start")` (l.1198-1200).

**It does not wait** for the advance session (docstring l.1168-1174). The driver then returns and the
process exits.

### G. `Driver.apply_frame(child, state)` (l.889-956)

Called after any child that reached `"built"` (l.1079, l.1116) — i.e. for *every* built child, not
only the frame child; it no-ops unless the child's file carries a non-empty `frame` dict.

1. `frame = state["frame"]`; not a non-empty dict → if `state["prompt"]` matches
   `--frame\b|frame\.md`, `note_defect("<slug> left no `frame` map, ...")`; return (l.901-912).
2. `children` re-read from the batch file; `known = set(children)`; `rest = children - {child.slug}`.
3. For each slug in `rest` with a real run file (l.919-923):
   - if the child already carries a list `needs`, keep it filtered to `known` and **do not overwrite**
     (l.925-929; test tests l.628);
   - else `wants = frame[slug]` filtered to `rest` minus itself; `run.set(needs=wants)` (l.930-936).
4. `stray = sorted(named - known)` where `named` is every key and every listed dependency in the map
   (l.941-942).
5. `order, cycle = order_by_needs(rest, needs_of)` (l.516-543): a stable topological sort taking one
   ready slug at a time; on a cycle it returns `(list(children), left)` — i.e. **the original list
   untouched plus the slugs stuck in the cycle** (l.538-539).
6. `self.run.set(children=[child.slug] + order)` (l.945); `child.event("frame", "<n> features ordered")`.
7. `note_defect` for a cycle and for stray names (l.948-956).

`note_defect(line)` (l.958-967): appends to the **batch's** `blockers`, `run.event("frame-defect", line)`,
`tell(line)`.

### H. `Driver.tell(message)` (l.594-609)

`window = self.run.state()["window"]`; must be set **and** `launcher.alive_at(window)`
(`tmux has-session -t <verbatim window name>`, l.203-204) or the call is a no-op (l.603-605).
First call only: `send_to(window, WINDOW_RULE)` (l.589-592, l.606-608). Then
`send_to(window, f"[driver] {message}")`. The window name is the owner's own tmux target, addressed
verbatim, not through `tmux_name` (l.195). Tests: tests l.1393, l.1404.

---

## RETRY / TIMEOUT / FAILURE MODEL

| bound | value | where | what happens past it |
|---|---|---|---|
| poll interval | `--poll`, 60 s | l.693 | — |
| session start settle | 5 s | l.181 | prompt is typed regardless |
| after `/model` | 2 s | l.186 | — |
| after reclaiming a name | 1 s | l.170 | — |
| between two `send-keys` (text then Enter) | 0.5 s | l.200 | — |
| transcript must appear | 300 s from launch | l.701 | `watch` returns `"no transcript — the session cannot be watched"` → child `blocked` |
| silence before "stuck" | `--hang`, 30 min | l.718 | nudge, then one restart, then give up |
| nudges per session | 1 (`nudged`) | l.782-783 | — |
| restarts per `watch()` call | **1** (`restarts > 1` refuses) | l.685-690 | `watch` returns `why`; child → `blocked` |
| handoffs per `watch()` call | **unbounded** — `fresh()` from the handoff path never touches `restarts` | l.713-716 | see UNCERTAIN |
| handoff asks per session | 1 (`asked`) | l.733, 736 | — |
| `floor-unreadable` notice per session | 1 (`blind`) | l.728-729 | — |
| overloaded (529) backoff | fixed 120 s, **unbounded repeats** | l.768-772 | see UNCERTAIN |
| limit (429) with a parsed reset | `sleep(wait + 60)` | l.758 | then `continue`, or restart |
| limit (429) with no parsed reset | `poll * 5` = 300 s | l.750 | same |
| weekly limit | `wait > --max-wait * 3600` (6 h) | l.751-754 | `self.stopping = True`, run stops, every remaining child → `skipped` |
| `systemd-run` | `timeout=30` | l.1287 | `detach` returns `("", why)`, driver runs undetached |
| `git ls-remote` | **no timeout** | l.991-992 | can block the driver indefinitely |
| `claude-new` / `claude-close` / every `tmux` call | **no timeout** | l.149, 172, 224 | can block the driver indefinitely |

Fallbacks, in order of preference, when a child ends without a terminal step:
`own_pr` or `step == "done"` → built; else a pushed remote branch → built (`step` corrected to `done`);
else `blocked` (l.816-829). A `blocked` non-errand child adds itself to `self.skip`, so every child
naming it in `needs` (or, absent `needs`, naming it as its authored `parent`) is set `skipped`
(l.1104-1109, l.1117-1118). An **errand** that fails cascades to nobody (l.1082-1093).

Failure of the closing session leaves the batch `blocked` with a message telling the owner the
branch, PR body and digest need finishing by hand (l.1161-1164).

`tmux` missing at startup → refuse with a message pointing at `/agent-kit:ship` (l.1338-1342).
`FileNotFoundError` on tmux mid-run → a synthetic `CompletedProcess(args, 127, "", "tmux is not installed")` (l.150-151).

---

## IO

### Read

- `<run_dir>/run.json` — the batch (l.74, l.82-85, every `state()`).
- `<run_dir>/../<slug>/run.json` — each child (l.1049, l.919, l.1034).
- `<run_dir>/../<parent>/run.json` — the run above, for `own_pr` (l.120) and `hand_back` (l.1179).
- `<run_dir>/control` — the owner's out-of-band instruction; **read then deleted** (l.548-552).
- `~/.claude/projects/<cwd with every non-alnum replaced by "-">/*.jsonl` — transcripts
  (`transcript_dir`, l.241-243; glob l.264). Head = first 12 lines (l.281-287) or 40 for
  `opening_size` (l.417); tail = last 40 lines out of the last 400_000 bytes (l.330-348), 200 lines
  for `last_spoke` (l.316).
- `/proc/self/cgroup` (l.1241-1246).
- `$PATH` for `claude-new`, `claude-close`, `tmux`, `systemd-run` (l.142-143, l.1282, l.1338).

### Write

- `<run_dir>/run.json` and `<child>/run.json` — via `Run.set` → `write_json`, which writes
  `<path>.json.tmp` then `Path.replace` (l.61-66). `set` is read-modify-write (l.87-91) and creates
  the directory if missing (l.90).
- `<run_dir>/run.log` and `<child>/run.log` — append-only, one line per event:
  `YYYY-MM-DDTHH:MM:SSZ step=driver event=<event> detail=<detail>` (l.93-99). **Every line is also
  printed to stdout** (l.99).
- stdout: the log lines above, the detach notice (l.1326-1327).
- stderr: no-run-file (l.1318), detach-failed (l.1330-1332), no-tmux (l.1339-1341), live-session
  refusal (l.1354-1355), the `claude-close`-missing warning (l.219-222), a `claude-close` refusal
  (l.226-228).
- Under systemd the driver's own stdout/stderr go to the journal — `journalctl --user -u agent-kit-<slug>` (l.1327).

Every `event` name written, exhaustively: `detached`, `detach-failed` (l.1328, 1333); `empty`
(l.1005); `start`, `window` (l.1023, 1025); `control` (l.1058, 1060, 1066); `missing` (l.1051);
`already-terminal` (l.1075); `skipped` (l.1108); `frame-defect` (l.966); `session-start` (l.649);
`handed-off` / `restarted` (l.714, 690, via `fresh`); `floor-unreadable` (l.730); `handoff-asked`
(l.741); `limit` (l.756); `resumed` (l.762); `overloaded` (l.769); `nudged` (l.784); `stalled`
(l.788, 1199); `built` (l.820, 825); `blocked` (l.828); `closed-with-defects` (l.863); `frame`
(l.946); `children-done` (l.1121); `done` (l.1156); `close-failed` (l.1162); `hand-back` (l.1185);
`reclaimed` (l.1197).

---

## CONCURRENCY AND LOCKING

- **The driver is strictly serial.** One child at a time (`remaining[0]`, l.1046), one session watched
  at a time, no threads, no `asyncio`, no subprocess left running unwaited except the sessions
  themselves.
- **Parallel only in the sense that a claude session runs while the driver sleeps.** The driver's own
  work is `sleep(poll)` → read files → maybe type one line.
- **There is no lock file.** Mutual exclusion is the liveness probe in `main()` (l.1350-1356): if any
  non-terminal child's session name is alive in tmux, refuse to start. Comment l.1347-1349: the
  previous generation read liveness from a log written only at exit, which could produce two drivers
  over one working tree.
- **Atomicity**: `write_json` is tmp-then-rename (l.62-66), so a reader never sees a torn file. But
  `Run.set` is read-modify-write with no lock (l.87-91), and the *child session* writes the same file
  concurrently — see UNCERTAIN.
- The advance session started by `hand_back` may start a **second driver** while this one is still
  exiting (l.1186); the two drive different run dirs but share one working tree and one git index.

---

## NODES

| id | kind | label | description | source |
|---|---|---|---|---|
| `script:orchestrate` | script | orchestrate.py | The driver: a serial loop that starts one claude session per child, watches its transcript, and closes the batch. | orchestrate.py:1 |
| `cmd:main` | cmd | `main()` | Argument parsing, self-detach, tmux check, single-driver check, then `go()`. | orchestrate.py:1296 |
| `script:detached` | script | the systemd copy of itself | The same program re-executed as a transient user unit so a closing tmux pane cannot kill it. | orchestrate.py:1260 |
| `cmd:go` | cmd | `Driver.go()` | The batch loop: control file, skip cascade, chain, build, frame, close. | orchestrate.py:997 |
| `cmd:build` | cmd | `Driver.build()` | One child: watch a session, then judge built/blocked by run file, PR, or pushed branch. | orchestrate.py:795 |
| `cmd:watch` | cmd | `Driver.watch()` | The poll loop over one session: terminal, handoff, health, limit, overload, nudge, restart. | orchestrate.py:619 |
| `cmd:close` | cmd | `Driver.close()` | Start the closing session and judge whether the batch closed. | orchestrate.py:1143 |
| `cmd:hand_back` | cmd | `Driver.hand_back()` | Start the epic's advance session and exit without waiting. | orchestrate.py:1167 |
| `cmd:apply_frame` | cmd | `Driver.apply_frame()` | Turn a frame child's dependency map into `needs` on siblings and a reordered queue. | orchestrate.py:889 |
| `cmd:launcher` | cmd | `Launcher` | The only thing that knows how a visible session is made and closed. | orchestrate.py:138 |
| `session:child` | session | `<child-slug>` / `<slug[:56]>-N` | One claude session building one feature. | orchestrate.py:797, 573 |
| `session:close` | session | `<batch-slug>-close` | The session that writes the pull request. | orchestrate.py:1145 |
| `session:advance` | session | `<epic-slug>-advance` | The session that decides the next batch of an epic. | orchestrate.py:1184 |
| `session:window` | session | the owner's own window | Named in the batch's `window` field; addressed verbatim; narrates the run. | orchestrate.py:603 |
| `file:batch-run` | file | `<run-dir>/run.json` | The batch's state: children, step, base, window, model, parent, blockers, spent. | orchestrate.py:74 |
| `file:child-run` | file | `<run-dir>/../<slug>/run.json` | One child's state. | orchestrate.py:1049 |
| `file:parent-run` | file | `<run-dir>/../<parent>/run.json` | The epic above, read for `pr`, `command`, `model`; written `session`. | orchestrate.py:1179 |
| `file:control` | file | `<run-dir>/control` | The owner's `skip <slug>` / `stop`, read and deleted between features. | orchestrate.py:548 |
| `file:run-log` | file | `<run-dir>/run.log` | Append-only driver event log, mirrored to stdout. | orchestrate.py:97 |
| `file:transcript` | file | `~/.claude/projects/<slug>/*.jsonl` | The session heartbeat, context size and API-error record. | orchestrate.py:241 |
| `file:cgroup` | file | `/proc/self/cgroup` | Read once to decide whether this process would die with its pane. | orchestrate.py:1241 |
| `ext:tmux` | ext | `tmux` | new-session, send-keys, has-session, kill-session. | orchestrate.py:149 |
| `ext:claude-new` | ext | `claude-new` | Optional host helper that registers and names a session. | orchestrate.py:142 |
| `ext:claude-close` | ext | `claude-close` | Optional host helper that unregisters then kills a session. | orchestrate.py:143 |
| `ext:claude` | ext | `claude --dangerously-skip-permissions --remote-control` | The portable fallback session, run inside a tmux pane. | orchestrate.py:176 |
| `ext:git` | ext | `git ls-remote --heads origin <branch>` | The world's opinion on whether a feature shipped. | orchestrate.py:991 |
| `ext:systemd-run` | ext | `systemd-run --user --collect …` | Moves the driver out of the pane's control group. | orchestrate.py:1274 |
| `cmd:ship` | cmd | `/agent-kit:ship --run <dir>` | The default child prompt. | orchestrate.py:846 |
| `cmd:sprint-close` | cmd | `/agent-kit:sprint --close <dir>` | The closing session's prompt. | orchestrate.py:1146 |
| `cmd:epic-advance` | cmd | `/agent-kit:epic --advance <dir>` | The hand-back prompt. | orchestrate.py:1186 |
| `script:check` | script | `check.run_defects` | What a run may not close with; called on every built child and on the batch. | orchestrate.py:38, 859 |
| `script:runfile` | script | `runfile` | `TERMINAL` and `kind()` — what a run is, for every reader. | orchestrate.py:39, 803 |
| `ext:stop-hook` | ext | the stop hook | Matches a session to its run on the `session` field alone; the only closer of `session:advance`. | orchestrate.py:644-647, 1188-1193 |

---

## EDGES

| from | to | mechanism | trigger/condition | source |
|---|---|---|---|---|
| `cmd:main` | `file:batch-run` | reads | existence check before anything else | :1317 |
| `cmd:main` | `file:cgroup` | reads | unless `AGENT_KIT_DRIVER_DETACHED=1` | :1323 |
| `cmd:main` | `ext:systemd-run` | invokes | cgroup contains `tmux-spawn` + `.scope` | :1287 |
| `ext:systemd-run` | `script:detached` | spawns | success | :1274-1277 |
| `cmd:main` | `file:run-log` | writes | `detached` or `detach-failed` | :1328, 1333 |
| `cmd:main` | — | returns-to | exit 0 after a successful detach — the original process ends here | :1329 |
| `cmd:main` | `ext:tmux` | invokes | `shutil.which("tmux")`; absent → refuse, exit 1 | :1338 |
| `cmd:main` | `ext:tmux` | refuses | any non-terminal child's session is alive → "another driver is already on this run", exit 1 | :1350-1356 |
| `cmd:main` | `cmd:go` | invokes | all checks passed | :1357 |
| `cmd:go` | `session:advance` | refuses | kills `<parent>-advance` at the top, because it never closes itself | :1018-1020 |
| `cmd:go` | `file:batch-run` | writes | `step=building`, later `step=closing`, `children` reorder, `spent`, `blockers` | :1022, 1120, 945, 1139, 965 |
| `cmd:go` | `file:control` | reads | once per child iteration; the file is deleted whatever it says | :1054, 552 |
| `cmd:go` | `session:window` | invokes | `tell(...)` for start, control, defects, expensive decisions, finish | :594-609 |
| `cmd:go` | `file:child-run` | writes | `step=skipped` on stop or on a skipped dependency | :1071, 1107 |
| `cmd:go` | `cmd:build` | invokes | child has a run file, is not terminal, is not skipped | :1113 |
| `cmd:go` | `cmd:apply_frame` | invokes | a child came back `built` or was already `done` | :1079, 1116 |
| `cmd:apply_frame` | `file:child-run` | writes | sibling has a run file and no authored `needs` list | :936 |
| `cmd:apply_frame` | `file:batch-run` | writes | reorders `children` to `[frame-child] + topological order` | :945 |
| `cmd:apply_frame` | `cmd:go` | returns-to | always | :956 |
| `cmd:build` | `cmd:watch` | invokes | prompt = child's `prompt` or `/agent-kit:ship --run <dir>` | :802, 846 |
| `cmd:watch` | `cmd:launcher` | spawns | first session, and one per handoff/restart | :640, 678 |
| `cmd:launcher` | `ext:claude-new` | invokes | `claude-new` on PATH | :172 |
| `cmd:launcher` | `ext:tmux` | spawns | no helper: `tmux new-session -d -s agent-kit-<name> -c <cwd> "claude --dangerously-skip-permissions --remote-control"` | :176-178 |
| `cmd:launcher` | `session:child` | spawns | — | :156-187 |
| `cmd:launcher` | `ext:claude-close` | invokes | `stop()` and a closer exists; its refusal is final, no kill follows | :224-229 |
| `cmd:launcher` | `ext:tmux` | invokes | `stop()` with no closer: `kill-session` | :230 |
| `cmd:watch` | `file:transcript` | reads | every poll: head, tail, mtime | :699, 705, 708 |
| `cmd:watch` | `file:child-run` | writes | `session=<tmux name>` on every start | :648, 681 |
| `cmd:watch` | `file:child-run` | reads | `run.terminal()` every poll; `handoff` every poll | :695, 712 |
| `cmd:watch` | `session:child` | invokes | types `HANDOFF_LINE`, `continue`, `/model <name>` | :735, 761, 771, 782, 185 |
| `cmd:watch` | `cmd:watch` | loops-to | `continue` after every non-terminal branch | :703, 715, 744, 763, 772, 786, 790 |
| `cmd:watch` | `cmd:watch` | blocks | `sleep(poll)` each turn; `sleep(wait + 60)` on a limit; `sleep(120)` on 529 | :693, 758, 770 |
| `cmd:build` | `ext:git` | invokes | run file not terminal but a `branch` is named | :991 |
| `cmd:build` | `script:check` | invokes | child came back built → `run_defects(state, cwd)` | :859 |
| `cmd:build` | `file:child-run` | writes | `spent.sessions`, `blockers`, `step=done`/`blocked` | :812, 862, 824, 827 |
| `cmd:go` | `cmd:close` | invokes | the child queue drained | :1123 |
| `cmd:close` | `cmd:watch` | invokes | `/agent-kit:sprint --close <run-dir>`, `hand_over=False` | :1146 |
| `cmd:watch` | `session:close` | spawns | via the launcher | :640 |
| `cmd:close` | `file:batch-run` | writes | `step=done` or `step=blocked` | :1155, 1161 |
| `cmd:close` | `cmd:hand_back` | invokes | both branches, always | :1159, 1165 |
| `cmd:go` | `cmd:hand_back` | invokes | `children` was empty → hand back and exit 1 | :1007 |
| `cmd:hand_back` | `file:parent-run` | reads | `command` must be `epic` or `mvp` | :1182 |
| `cmd:hand_back` | `session:advance` | spawns | `/agent-kit:epic --advance <parent dir>` | :1186 |
| `cmd:hand_back` | `file:parent-run` | writes | `session=<tmux name>` only when the start succeeded | :1194-1195 |
| `cmd:hand_back` | `session:advance` | hands-off | does not wait; the driver exits | :1168-1174 |
| `session:advance` | `script:orchestrate` | spawns | a new driver for the next batch (outside this file) | :1170-1171 |
| `ext:stop-hook` | `session:child` | refuses | reads `session` from the run file; the only closer of `session:advance` | :644-647, 1188-1193 |

---

## UNCERTAIN / CONTRADICTORY / DEAD

1. **`stop` overwrites a finished child's `done` with `skipped`.** The `self.stopping` branch (l.1070-1072)
   sits **before** the `child.terminal()` branch (l.1074). Once `stopping` is set — by the `stop`
   control word (l.1061) or by a weekly limit (l.752) — every remaining slug in `children` is written
   `step="skipped"`, including one that a previous pass already closed `done`. On `--resume` that is
   silent data loss: the child now reads as never built, and `Run.terminal()` still returns True, so
   nothing rebuilds it and `built` never counts it. Confirmed by reading the source; no test covers
   it (`test_stop_from_the_control_file_is_taken_between_features`, tests l.225, uses two `queued`
   children).

2. **Handoffs are unbounded; only restarts are capped.** `restart()` refuses a second attempt
   (l.685-690), but the handoff path calls `fresh()` directly (l.714) and never touches `restarts`.
   A session that keeps opening over the ceiling and keeps writing a *new* `handoff` note can be
   replaced forever — `segment` grows without limit and `numbered` happily produces `-2 … -999`
   (l.581). The docstring at l.433-437 records that exactly this happened on a live run ("a session
   handing over eleven times in an hour"), blames a doubled counter, and fixes the counter — not the
   missing bound.

3. **529 (overloaded) retries forever.** l.768-772: `event`, `sleep(120)`, `send("continue")`,
   `continue`. There is no counter, no escalating backoff, and no ceiling. A permanently overloaded
   API keeps the driver in this branch indefinitely; the `--hang` timer cannot fire because the
   overloaded branch is checked before `why` is computed and always `continue`s.

4. **`gh` is documented but never called.** The module docstring (l.11) says the program "calls git
   and gh". `grep` over the file finds exactly four `subprocess.run` call sites: tmux (l.149),
   `claude-new` (l.172), `claude-close` (l.224), `git ls-remote` (l.991), plus `systemd-run` (l.1287).
   Same sentence: "watches a transcript's modification time" — mtime is a fallback only since
   `last_spoke` (l.304-327); and "knows one HTTP status" — it knows 429 and 529 (l.47-48).

5. **`Run.set` is a lock-free read-modify-write against a file the child session also writes.**
   l.87-91 reads `run.json`, merges, writes. The `ship` session inside the child writes the same file
   on its own clock. Every driver write is exposed: `session=` right after a start (l.648, 681),
   `spent=` after the session ends (l.812), `blockers=` (l.862), `step=` (l.824, 827, 1071, 1107).
   `write_json`'s tmp-then-rename (l.62-66) makes the *write* atomic but does nothing about the
   lost-update window. The `session=` write at l.648 lands seconds after the session was told to
   start, which is exactly when the child is writing its own first step.

6. **`child.set(spent=...)` clobbers the whole `spent` object.** l.811-812 reads only
   `spent.sessions` and writes back `{"sessions": ...}` — any `hours`, `features` or other key the
   child wrote is dropped. The batch's own `record_spend` (l.1137-1141) carefully preserves all three;
   the child path does not.

7. **The closing session's cost is never counted.** `record_spend(built)` runs at l.1122, `close()` at
   l.1123. Every `self.sessions += 1` inside the closing `watch()` (l.642, 680) lands after `spent`
   was written and is lost. Same for the seconds spent closing — `spent.hours` stops at l.1138.

8. **The single-driver check only looks at segment-1 names.** l.1353 probes
   `driver.launcher.alive(slug[:60])`. A child whose live session is `<slug[:56]>-3` (after two
   handoffs, l.581) is invisible to it, so a second driver starts over the same working tree — the
   exact failure the check exists to prevent (l.1347-1349). It also never probes `<batch>-close` or
   `<epic>-advance`.

9. **`launcher.alive` and `tmux_name` disagree across machines.** `tmux_name` picks the `cc-` prefix
   purely on whether `claude-new` is on *this* process's PATH (l.153-154). The detached copy carries
   PATH forward explicitly for this reason (l.1264-1272), but a driver started with a different PATH
   from the one that made the sessions would probe `agent-kit-<slug>` for sessions named `cc-<slug>`
   and conclude nothing is running.

10. **`take_control` is skipped for a child with no run file.** l.1050-1052 `continue`s before the
    control read at l.1054. A `stop` written while the queue's head is a missing child is not seen
    until the next child that does have a file.

11. **An unparsed reset time silently becomes a 5-minute wait.** l.750: `wait = ... if when else self.opt.poll * 5`.
    `limit_reset` returns `("limit", None)` when `RESET_RE` (l.49) does not match the 429 text
    (l.490-491). The run then loops through the limit branch every 5 minutes with no log line saying
    the reset time could not be read — the exact "a check that cannot read its input says so" rule
    the project's CLAUDE.md names, unmet here.

12. **`opening_size` returning 0 disables `room` entirely.** l.481-483: with `floor == 0`,
    `size - 0 >= room*1000` is true for any session past the ceiling. This is deliberate and
    documented (l.408-412) and it does log `floor-unreadable` once — but only when `hand_over` is
    true (l.728), so a non-feature child never says it.

13. **`newest_transcript`'s `mark` filter can be defeated by a 12-line head.** l.275 filters on
    `mark in read_head(p)` with `read_head`'s default of 12 lines (l.281). The prompt the driver typed
    is the first user record, so this normally holds; a session whose harness writes more than 12
    preamble records before the prompt falls back to "newest of the fresh ones" (l.278), which is the
    behaviour the 60-second `opened_at` guard (l.271) only partly narrows.

14. **`order_by_needs` on a cycle returns `list(children)` — the *whole* list, including the frame
    child.** l.539. The caller passes `rest` (the frame child excluded, l.915) but receives `children`
    (l.528 parameter name shadows nothing — the parameter *is* `rest` at the call site l.944, so the
    return is `list(rest)`). This is correct, but only because the parameter is named `children`; a
    reader tracing `self.run.set(children=[child.slug] + order)` at l.945 must check the call site to
    see the frame child is not duplicated. `test_a_circle_leaves_the_queue_alone_and_says_so`
    (tests l.500) pins it.

15. **`hand_back` can be reached twice for one run.** `close()` calls it in both branches (l.1159,
    l.1165) — that is one call. But `go()`'s empty-children branch also calls it (l.1007) and returns
    1 without ever setting `step`, so an epic whose next batch was composed with an empty `children`
    array leaves that batch's `step` at whatever it was and hands back anyway — the advance session
    then re-reads a batch it cannot tell apart from an unstarted one.

16. **The `stopping` flag from a weekly limit is set inside `watch()` but `build()` still judges the
    child.** l.752 sets `self.stopping` then returns the reason; `build()` (l.816-829) proceeds to
    mark the child `blocked` (test tests l.213 confirms `blocked` + `skipped`). Then `go()` reaches
    `close()` (l.1123) and **starts a closing session anyway** — during a weekly limit, when no
    session can do anything. Nothing checks `self.stopping` before `close()`.

17. **`self.skip` and `self.stopping` are process-local.** Neither is written to any file. A driver
    restarted by `--resume` after a `skip` re-reads only run-file `step`s, so a slug that was skipped
    without its `step` being written (there is no such path today, but `errand` failures at l.1117
    deliberately do not add to `skip`) has no durable record.

18. **`Launcher._tmux`'s `FileNotFoundError` fallback constructs `CompletedProcess(args, 127, …)` with
    the *inner* `args`, not the full command.** l.151. Harmless, but the returned object's `args`
    field omits `"tmux"`.

19. **`watch()` never stops the session it gives up on.** Every `return` inside the loop (l.702, 716,
    754, 766, 791) leaves `current` running. `build()` (l.804) and `close()` (l.1148) do the stopping
    from outside via `self.watched`. That is correct today, but `self.watched` is instance state
    shared across all `watch()` calls (l.570) — a `watch()` that returns at l.641 (`could not start a
    session`) leaves `self.watched` pointing at the *previous* child's last segment, and `build()`
    then stops that name instead of the one it just failed to start. Line 641 returns before l.637's
    assignment? No — l.636-637 set `self.watched = current` before the start attempt, so this is safe;
    but `close()`'s `self.watched or name` (l.1148) would use a stale value only if `watch` returned
    before l.637, which it cannot. Noted as verified-safe rather than a defect.

20. **`--room`'s help text and `handoff_due`'s behaviour describe an inert guard.** l.1305-1309 says it
    "binds only where the ceiling is under ~86k, which is a ceiling set by mistake" — with the shipped
    defaults (ceiling 210, room 40, floor ~46k) the `room` term can never be the binding one. It is a
    flag that, at its own defaults, does nothing. Kept deliberately as a smoke alarm.

21. **No timeout on any tmux, `claude-new` or `claude-close` call** (l.149, 172, 224) and none on
    `git ls-remote` (l.991). Only `systemd-run` has one (`timeout=30`, l.1287). A hung tmux server or
    a network-stalled `ls-remote` blocks the whole night with no log line.

---

## CALLERS AND DOCUMENTED INTENT

### Who launches the driver — exactly two literal lines in the payload

`plugins/agent-kit/skills/sprint/SKILL.md:232-236` (section "## Start the driver") and
`plugins/agent-kit/skills/epic/SKILL.md:272-276` build the identical line:

```bash
nohup python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" .agent-kit/runs/<batch>/ \
  >> .agent-kit/runs/<batch>/driver.out 2>&1 &
```

**No flags are ever passed by default.** `sprint/SKILL.md:246-253` names all seven knobs
(`--poll`, `--hang`, `--max-wait`, `--model`, `--ceiling`, `--room`; `run_dir` is positional) and
says "Do not pass them by default — every one is a measured number, and `--ceiling` is a live
experiment whose next value waits on a measurement rather than on an opinion."

`sprint/SKILL.md:238-240`: "**The output goes to a file, not to /dev/null.** A driver that died in
its first second and a driver with nothing to say looked identical for a week."

Prose callers that reuse the same line without repeating it: `sprint/SKILL.md:271` (`--resume`:
"Start the driver again over the same directory"), `epic/SKILL.md:313`, `:382`, and the flat
prohibition `epic/SKILL.md:394` — "**Never start a second driver over a live one.**"

There is **no Makefile** and **no `plugins/agent-kit/commands/`** in this repo; commands come from
`SKILL.md` frontmatter.

### The gate that holds the flag surface — `scripts/validate.sh:387-409`

Step "every knob of the driver is named where a person reads". It regex-extracts
`add_argument\("(--[a-z-]+)"` from `orchestrate.py` (`:400`) and fails the build unless each flag
appears **inside backticks** in the concatenated `skills/sprint/SKILL.md` + `skills/epic/SKILL.md`
(`:401-403`). Error text at `:405-406`. This is why the flags are documented in two places.

`scripts/validate.sh:536-543`, step "the driver's own tests": `python3 -m compileall -q
$PLUGIN/scripts $PLUGIN/hooks` then `python3 -m unittest discover -s tests -q`. This is the only
path that runs `tests/test_orchestrate.py`, and `.github/workflows/ci.yml:20-21` runs
`bash scripts/validate.sh`.

### What the design notes say the driver is for

- `docs/design/sprint.md:17` — role table: "**Driver** | `scripts/orchestrate.py`, a loop with no
  model behind it | never [asks questions]".
- `docs/design/sprint.md:29-32` — "**Why no orchestrating agent.** 0.17.0 had one and it was the
  measured failure: an agent holding the queue dies of context, pays tokens for bookkeeping a loop
  does for free, and puts a third headless level between the owner and the work… A loop has no
  context to lose and no opinion to have. Its price is that anything unusual becomes an honest
  [stop]." Rejected again at `:335`.
- `docs/design/the-loop.md:21` — "the driver: starts children, watches them, obeys `control`, never
  judges".
- `docs/design/0.17.0-measurements.md` — the predecessor's numbers: orchestrator cost 34.8M → 3.9M
  (`:24-25`, `:40`); **P2** at `:58-60` is the second-orchestrator-over-a-live-one race, prevented
  only accidentally, which is what `main()`'s liveness probe (`orchestrate.py:1350-1356`) replaces;
  **P3** `:63-66` no stable session id; **P6** `:78-80` three headless levels make progress
  unobservable.
- `docs/design/ship.md:110-113` — why the driver was deferred at first: "it adds five mechanisms
  that exist for one scenario: nobody is watching at 3am".
- `docs/design/2026-08-20-the-driver-died-with-its-session.md` — the incident behind `detach()`.
  `:16-31` names the three things that close the driver's session, the first being the driver
  itself (`go()`'s `self.launcher.stop(f"{parent}-advance")`). `:36-39` "Why `nohup` did not save
  it". `:85-86` "**a process whose output goes nowhere cannot report its own death.**" `:97-98` is
  where `driver.out` comes from. `:101-110` lists what is **still open**: there is no `driver-exit`
  line, so a driver that ended cleanly and one that was killed still look alike.
- `docs/design/2026-08-12-frame.md:17-21` — the known cost of the skip cascade: "`orchestrate.py`
  writes `blocked` when a session ends without reaching a terminal step — the common cause is a
  session that died, stalled or hit a limit. That has nothing to do with the feature, and it cost
  up to N−1 features a night." That is what `needs`/`frame` narrows.
- `docs/design/2026-08-17-two-sessions.md:14-16` — "`cwd` is the project root. So the run and
  anybody else who opens a session there share one working tree and one `HEAD`." Confirms: no
  worktree isolation by design.
- `docs/design/2026-08-20-the-session-layer-moves-out.md:3-6, 55-56, 103-104` — the planned
  refactor: `Launcher` becomes an interface with three implementations (AoE first, when `aoe` is on
  PATH); "a running `orchestrate.py` looks for `claude-new` on PATH and would be orphaned
  mid-night."
- `docs/design/2026-08-14-the-counter-was-doubling.md:33-34, 99` — `--ceiling` 300→280, `--room`
  80→40 after the doubled counter was fixed. `docs/design/2026-08-14-where-the-tokens-burn.md:49-57`
  — `sprint --close` costs 5.0M (5%), `epic --advance` 3.3M (3%); `:148` "**`--room` has been inert
  since the counter was fixed**"; `:174` "`epic --advance` re-does the closing session's work" —
  still open per `docs/design/2026-08-16-what-the-review-refused.md:151`.
- `docs/design/2026-08-14-what-one-night-measured.md:49` — "A project on a 200k-window model must
  set `--ceiling 150`." **Contradicts** the driver's own docstring at `orchestrate.py:477-479`,
  which says "about 130k". Two documented numbers for the same instruction.
- `migrations/2.0.0.md:27` — "The driver still recognises `"command": "mvp"` in a run" — the
  compatibility branch at `orchestrate.py:1182`.
- `docs/planned.md:340-343` — refuses orchestration frameworks: "The kit's driver is a program that
  holds the flow while agents decide at marked points… Replacing it with a framework would be a
  step back."

### Who the driver's children are, from their own side

- `skills/sprint/SKILL.md:21` — `/agent-kit:sprint --frame <run dir>` is "the frame child, started
  by the driver"; `:22` — `/agent-kit:sprint --close <run dir>` is "the closing session, started by
  the driver". The frame child is a `prompt` in the child's run file (example at `:163`), which is
  why `apply_frame` matches `--frame\b|frame\.md` (`orchestrate.py:909`).
- `skills/epic/SKILL.md:23` — `/agent-kit:epic --advance <run dir>` is "started by the driver when
  a batch finished: decide what follows, start it, stop". `:223-225` — "No driver watches this file
  — **the stop hook does**", which is the other half of `orchestrate.py:1188-1195`.
- `skills/ship/SKILL.md:123` — "there may be a `run.log` — **the driver's**, not yours"; `:135` the
  driver measures context and types one line; `:161` `handoff` is read by the driver.
- `skills/audit/SKILL.md:29, 55` — an audit lens is "one lens as a child of a batch, started by a
  driver… The driver watches that field and nothing else."
- `rules/window.md:44-46` — "## When the driver pokes you", the `[driver]` prefix; `:15` "That is
  the property that keeps this session from becoming the orchestrator an earlier version of this
  kit died of."
- `rules/preflight.md:29-30` — "A session the driver started was given a run directory — `--run`,
  `--frame`, `--close`, `--advance`, `--resume`".
- `rules/channels.md:15-20` — `children` written by "the composing session; `--advance` while the
  batch runs", read by "the driver, before every child"; also `needs` and `frame`.
- `scripts/check.py:2516` is the only mention of the driver in `check.py`, documenting
  `Driver.costly` as the **reader** of `assumptions[].expensive`. The import direction is one-way:
  `orchestrate.py:37-38` imports from `check`, never the reverse.

---

## UNCERTAIN (continued) — found by cross-reading the callers

22. **`.agent-kit/runs/<slug>/driver.out` is an IO path the driver never names.** It is created by
    the shell redirect in the launch line (`sprint/SKILL.md:236`, `epic/SKILL.md:276`), so every
    `print` and `Run.event` (`orchestrate.py:99`) lands there — but nothing in `orchestrate.py`
    knows the file exists, and no code cleans it up or rotates it. Add it to the IO list above as
    *written indirectly*.

23. **A stale comment inside the driver contradicts the launch line it describes.** `orchestrate.py:1231-1232`
    still reads "no message anywhere, because the launch line sends the driver's output to
    /dev/null." The launch line has redirected to `driver.out` since 2.28.1
    (`docs/design/2026-08-20-the-driver-died-with-its-session.md:97-98`). The comment is the only
    remaining record of the `/dev/null` behaviour and now describes something that is not true.

24. **After the detach, `driver.out` gets nothing.** `main()` returns 0 at `orchestrate.py:1329`
    having printed one line; the real driver's output goes to the systemd journal
    (`journalctl --user -u agent-kit-<slug>`, l.1327). So on any machine with systemd — which is the
    machine this kit runs on — the file the launch line was added to create stays one line long,
    and the "a driver that died in its first second and a driver with nothing to say looked
    identical" defect (`sprint/SKILL.md:238-240`) is only half fixed. The run log
    (`run.log`) is still written directly by the detached process (l.97) and is the reliable record.

25. **Two documented values for the same instruction.** `orchestrate.py:477-479` says a project on a
    200k-window model "must lower this to about 130k";
    `docs/design/2026-08-14-what-one-night-measured.md:49` says "must set `--ceiling 150`". Neither
    cites the other.

26. **`--room` is documented as inert by the kit's own measurement.**
    `docs/design/2026-08-14-where-the-tokens-burn.md:148` — "**`--room` has been inert since the
    counter was fixed**" — matches the flag's own help text (`orchestrate.py:1305-1309`) and the
    arithmetic in `handoff_due`. It is a live flag with no effect at any shipped configuration, kept
    only because `scripts/validate.sh:387-409` requires every flag to be named in prose, and prose
    is where it is now justified.

27. **The `blocked`-cascade is a known, measured cost that the code still pays.**
    `docs/design/2026-08-12-frame.md:17-21`: the driver writes `blocked` for a session that died,
    stalled or hit a limit — nothing to do with the feature — and `go()` then adds that slug to
    `self.skip` (l.1117-1118), losing up to N−1 features. `frame`/`needs` narrows *which*
    descendants are lost; it does not stop a dead session from being read as a broken feature.

28. **`epic --advance` re-doing the closing session's work is an open defect that the driver
    triggers.** `docs/design/2026-08-16-what-the-review-refused.md:151` and
    `docs/design/2026-08-14-where-the-tokens-burn.md:174`. The driver calls `close()` (5.0M measured)
    and then `hand_back()` (3.3M measured) unconditionally, one after the other
    (`orchestrate.py:1123`, `1159`/`1165`), with no signal passed between them about what the closing
    session already did.

29. **No `driver-exit` line.** `docs/design/2026-08-20-the-driver-died-with-its-session.md:101-110`
    lists this as still open, and the source confirms it: `go()` returns 0 at l.1124 and `main()`
    returns it at l.1357 with no final `event`. A driver that finished and a driver that was killed
    leave the same last line in `run.log`.

30. **The single-driver rule is enforced in two places that disagree in strength.**
    `epic/SKILL.md:394` states it as an absolute — "**Never start a second driver over a live one.**"
    — while the program's only enforcement is the best-effort tmux probe at `orchestrate.py:1350-1356`,
    which finding 8 above shows misses numbered sessions. `docs/design/0.17.0-measurements.md:58-60`
    records that the previous generation's version of this check never fired for accidental reasons.
