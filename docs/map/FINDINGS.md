# Findings

Harvested from twelve sector reports, deduplicated, and verified against
`/projects/agent-kit` where the claim was checkable. 58 findings ranked.
Verification was done by reading the real source and, where possible, by running
the program. Six report claims were checked and found wrong or already
self-refuted; they are listed at the bottom so the map does not carry them forward.

---

## RANKED

### 1. `stop` overwrites a finished child's `done` with `skipped` — silent loss of a built feature

**What** The `self.stopping` branch sits *before* the `child.terminal()` branch. Once
`stopping` is set — by the `stop` control word or by a weekly limit — every remaining slug in
`children` is written `step="skipped"`, including one a previous pass already closed `done`.
On `--resume` the child now reads as never built; `Run.terminal()` still returns True, so
nothing rebuilds it and `built` never counts it. The feature's branch exists and nothing points at it.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1070-1074`
**Evidence**
```python
1070            if self.stopping:
1071                child.set(step="skipped")
1072                continue
1073
1074            if child.terminal():
```
**Verdict** CONFIRMED — read the source; the order is exactly as reported. No test covers it:
`test_stop_from_the_control_file_is_taken_between_features` uses two `queued` children.
**Type** corrupts-a-record / undefined-behaviour-when-unattended
**Severity** corrupts-a-record
**What closes it** Program: swap the two branches (test `terminal()` first). Three lines, one test.

---

### 2. The guard refuses a legitimate push whenever the default branch name appears anywhere in the command

**What** `pushes_default` is true if the default branch name matches as a whole word *anywhere*
in the command string. `main` matches inside `feature-main-fix` (the `-` is a word boundary), and
inside a commit message. So `git push origin feature-main-fix`, and
`git commit -m "fix main menu" && git push origin claude/x`, are both refused. A build run that
cannot push its own branch stalls with a refusal it cannot act on.
**Where** `plugins/agent-kit/hooks/guard.py:257-259`
**Evidence**
```python
257        pushes_default = re.search(rf"\b{re.escape(default)}\b", command) or (
258            branch == default and not re.search(r"\bgit\s+push\b[^&|;]*\s\S+\s+\S+", command))
```
Run against the real expression:
```
'git push origin feature-main-fix'  branch=feature-main-fix -> blocked: True
'git commit -m "fix main menu" && git push origin claude/x'  branch=claude/x -> blocked: True
```
**Verdict** CONFIRMED — executed the exact regex.
**Type** silent-failure (false positive) / other
**Severity** breaks-a-run
**What closes it** Program: parse the push's refspec instead of scanning the whole command
string — the branch name is already known from `git symbolic-ref`.

---

### 3. The same guard lets a bare `git push -u origin` onto the default branch through

**What** The second half of `pushes_default` treats "two space-separated tokens after `git push`"
as proof of an explicit remote+ref. `git push -u origin` has two such tokens (`-u`, `origin`) and
no refspec, so on the default branch it is judged explicit and allowed. That is a push to the
branch every run forks from — the one thing this check exists to stop.
**Where** `plugins/agent-kit/hooks/guard.py:258`
**Evidence** same regex as above; executed:
```
'git push -u origin'  branch=main -> blocked: False
```
**Verdict** CONFIRMED — executed.
**Type** silent-failure (false negative)
**Severity** corrupts-a-record (a commit lands on the default branch with nobody's review)
**What closes it** Program: strip flags before counting tokens, or compare against the resolved
push destination. Same fix as #2.

---

### 4. Handoffs are unbounded; only restarts are capped

**What** `restart()` refuses a second attempt (`restarts > 1`). The handoff path calls `fresh()`
directly and never touches `restarts`. A session that keeps opening over the ceiling and keeps
writing a *new* `handoff` note can be replaced forever — `segment` grows without limit and
`numbered` happily produces `-2 … -999`. The docstring records that exactly this happened on a
live run ("a session handing over eleven times in an hour"), blames a doubled counter, fixes the
counter, and does not add the bound.
**Where** `plugins/agent-kit/scripts/orchestrate.py:713-716` (call), `685-690` (the cap that
does not apply)
**Evidence**
```python
713            if asked and note and note != note_before and (gone or idle > self.opt.poll):
714                if fresh(f"{run.slug} carried on in a new session", "handed-off"):
715                    continue
```
**Verdict** CONFIRMED — `fresh()` mutates `segment`, `floor`, `asked`, `blind`; `restarts` is a
closure variable only `restart()` touches.
**Type** unbounded-loop
**Severity** breaks-a-run (a night burned on one feature)
**What closes it** Program: a `handoffs` counter beside `restarts`, with a ceiling and a
`blocked` exit that says why.

---

### 5. A 529 (overloaded) retries forever, with no counter and no escalating backoff

**What** `event`, `sleep(120)`, `send("continue")`, `continue`. No counter, no ceiling. A
permanently overloaded API keeps the driver in this branch indefinitely; `--hang` cannot fire
because the overloaded branch is reached before `why` is computed and always `continue`s.
**Where** `plugins/agent-kit/scripts/orchestrate.py:768-772`
**Evidence**
```python
768            if kind == "overloaded" and not gone:
769                run.event("overloaded", "retrying shortly")
770                time.sleep(120)
771                self.launcher.send(current, "continue")
772                continue
```
**Verdict** CONFIRMED.
**Type** unbounded-loop
**Severity** breaks-a-run
**What closes it** Program: count the 529s per session, escalate the sleep, and treat the
`--max-wait` ceiling the 429 path already has as shared.

---

### 6. A weekly limit stops the children and then starts a closing session anyway

**What** `watch()` sets `self.stopping = True` on a weekly limit and returns. `build()` marks the
child `blocked`, `go()` reaches `close()` and starts a `<slug>-close` session — during a weekly
limit, when no session can do anything. Nothing checks `self.stopping` before `close()`. The
closing session then fails to reach a terminal step, so the batch is written `blocked` with a
"never closed" message that blames the wrong thing.
**Where** `plugins/agent-kit/scripts/orchestrate.py:752` (sets), `1122-1123` (ignores it)
**Evidence**
```python
1122        self.record_spend(built)
1123        self.close()
```
**Verdict** CONFIRMED — no `stopping` test between the loop's exit and `close()`.
**Type** undefined-behaviour-when-unattended
**Severity** breaks-a-run
**What closes it** Program: `if self.stopping: return 1` before `close()`, with a `tell()` saying
the batch is parked at a limit, not blocked.

---

### 7. `child.set(spent=…)` clobbers the whole `spent` object the child wrote

**What** The driver reads only `spent.sessions` and writes back a fresh dict containing only
`sessions` — any `hours`, `features` or other key the child wrote is dropped. The batch's own
`record_spend` carefully preserves all three; the child path does not.
**Where** `plugins/agent-kit/scripts/orchestrate.py:811-812` vs `1137-1141`
**Evidence**
```python
811        before = int((child.state().get("spent") or {}).get("sessions") or 0)
812        child.set(spent={"sessions": max(before, self.segments)})
```
**Verdict** CONFIRMED.
**Type** corrupts-a-record
**Severity** corrupts-a-record (the per-feature cost record the next batch's frame child reads)
**What closes it** Program: merge instead of replace — one line, mirroring `record_spend`.

---

### 8. `driver.out` is a file the kit's own launch line creates and the kit's own check reports as undeclared drift

**What** `sprint/SKILL.md:236` and `epic/SKILL.md:276` redirect the driver's output into
`.agent-kit/runs/<batch>/driver.out`. `check_channels` allows exactly three names in a run
directory and reports everything else as *"a mechanism nothing declared and nothing tracks"*.
`rules/channels.md` has rows for `run.json`, `run.log` and `control` — and none for `driver.out`.
So every sprint and every epic makes the kit's own preflight print a permanent false finding, and
the file has no declared writer, reader or closer — the exact four-answers rule `CLAUDE.md`
states.
**Where** `plugins/agent-kit/scripts/check.py:2216-2224`; `plugins/agent-kit/skills/sprint/SKILL.md:235-236`;
`plugins/agent-kit/skills/epic/SKILL.md:275-276`; `plugins/agent-kit/rules/channels.md:15,26,27`
**Evidence**
```python
2216                if path.name not in ("run.json", "run.log", "control"):
2217                    strays.append(f"{directory.name}/{path.name}")
```
Run against a fixture with `b1/driver.out`:
```
run directories carry files that are not a run's own (1): b1/driver.out — a run keeps
run.json, run.log and control, and anything else there is a mechanism nothing declared
and nothing tracks
```
**Verdict** CONFIRMED — reproduced empirically.
**Type** contradiction-between-files / orphan-record
**Severity** corrupts-a-record (it poisons the drift list every command reads)
**What closes it** Two homes at once: a **shared rule** — add a `driver.out` row to
`rules/channels.md` with its four answers — and a **program** change adding it to the allowed
names in `check_channels`. `run.json.tmp` (left by a crash mid-`write_json`) belongs in the same
decision.

---

### 9. `check.py --epic` returns 0 in complete silence on a project with no `docs/knowledge/`

**What** `main` hits the missing-knowledge early return *before* the `--epic` branch. The gate
with teeth in this program opens for a project that has no blueprint at all — the opposite of
what `check_epic`'s docstring claims it prevents. The message on line 3711 does not print either,
because `--status`/`--state` are not passed on that line. Mitigated only by `epic/SKILL.md`
running a second line (`--status --state`) that does say "no docs/knowledge/ here" — but the gate
itself, which the prose calls *"fatal or silent"*, is silent.
**Where** `plugins/agent-kit/scripts/check.py:3708-3714` vs `3729`; caller
`plugins/agent-kit/skills/epic/SKILL.md:40,44`
**Evidence**
```python
3708    if not knowledge.is_dir():
3709        if options.status or options.state:
3710            print(f"no {KNOWLEDGE}/ — this project has no blueprint yet")
3711        if options.state:
3712            print_state(root, gh)
3713        return 0
```
Run on an empty directory: `check.py . --epic` printed nothing, exit 0.
**Verdict** CONFIRMED — reproduced empirically.
**Type** silent-failure
**Severity** breaks-a-run
**What closes it** Program: move the `--epic`/`--brief`/`--entries`/`--record` branches above the
early return, or make the early return say so on every flag.

---

### 10. `--brief`, `--entries` and `--owed` are silent-and-zero for the same reason

**What** Same early return. `--brief <key>` on a project with no knowledge prints nothing and
returns 0, while inside `brief` an unknown key is a loud exit 2. `--entries <keys>` likewise,
though `print_entry_blocks`'s whole design is that a filter matching nothing must be loud.
`--owed` prints nothing both when a project owes nothing and when nobody has ever been asked.
**Where** `plugins/agent-kit/scripts/check.py:3708-3714` (vs `3720`, `3840`, `1811-1813`);
`print_owed` `2985-3025`. Callers: `skills/ship/SKILL.md:87,216`, `skills/fix/SKILL.md:106`,
`skills/epic/SKILL.md:90`, `skills/sprint/references/frame.md:24`
**Evidence** Run on an empty directory: all three printed nothing, exit 0.
**Verdict** CONFIRMED — reproduced empirically.
**Type** silent-failure
**Severity** breaks-a-run (a `ship` reads an empty brief as "this entry depends on nothing")
**What closes it** Program: same fix as #9, plus one line in `print_owed` distinguishing
"nothing owed" from "nobody was ever asked".

---

### 11. The single-driver check only probes segment-1 session names

**What** `main()` probes `driver.launcher.alive(slug[:60])`. A child whose live session is
`<slug[:56]>-3` — after two handoffs — is invisible to it, so a second driver starts over the
same working tree: the exact failure the check exists to prevent. It also never probes
`<batch>-close` or `<epic>-advance`, and `epic/SKILL.md:394` states the rule as an absolute
("Never start a second driver over a live one") that only this best-effort probe backs.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1350-1356`
**Evidence**
```python
1353        if child.file.is_file() and not child.terminal() and driver.launcher.alive(slug[:60]):
```
**Verdict** CONFIRMED — `numbered()` produces `-2 … -999` suffixes that this probe never forms.
**Type** race / concurrency
**Severity** corrupts-a-record (commits into the wrong branch)
**What closes it** Program: probe every segment name the run could hold (`self.segments` is
already written), plus the close and advance names.

---

### 12. `Run.set` is a lock-free read-modify-write against a file the child session writes concurrently

**What** `set` reads `run.json`, merges, writes. The `ship` session inside the child writes the
same file on its own clock. Every driver write is exposed: `session=` right after a start,
`spent=` after the session ends, `blockers=`, `step=`. `write_json`'s tmp-then-rename makes the
*write* atomic and does nothing about the lost-update window. The `session=` write lands seconds
after the session was told to start — exactly when the child is writing its own first step.
**Where** `plugins/agent-kit/scripts/orchestrate.py:87-91`
**Evidence**
```python
87    def set(self, **fields) -> None:
88        state = self.state()
89        state.update(fields)
90        self.dir.mkdir(parents=True, exist_ok=True)
91        write_json(self.file, state)
```
**Verdict** CONFIRMED.
**Type** race / concurrency
**Severity** corrupts-a-record
**What closes it** Program: an `O_EXCL` lock file or an `fcntl.flock` around read-modify-write.
No template or rule can close this.

---

### 13. No timeout on any `tmux`, `claude-new`, `claude-close` or `git ls-remote` call

**What** Only `systemd-run` has a timeout (30 s). A hung tmux server or a network-stalled
`ls-remote` blocks the whole night with no log line and no `--hang` to catch it — `--hang`
measures transcript silence, not the driver's own block.
**Where** `plugins/agent-kit/scripts/orchestrate.py:149, 172, 224, 991` (vs `1287`)
**Evidence**
```python
149            return subprocess.run(["tmux", *args], capture_output=True, text=True)
991        done = subprocess.run(["git", "ls-remote", "--heads", "origin", branch],
992                              cwd=self.cwd, capture_output=True, text=True)
```
**Verdict** CONFIRMED — grep found exactly five `subprocess.run` sites; only the last has `timeout=`.
**Type** undefined-behaviour-when-unattended
**Severity** breaks-a-run
**What closes it** Program: a `timeout=` on each, and a log line on expiry.

---

### 14. An empty `children` array hands back without ever writing `step`

**What** `go()`'s empty-children branch logs, tells, calls `hand_back()` and returns 1 without
setting `step`. An epic whose next batch was composed with an empty `children` leaves that
batch's `step` at whatever it was; the advance session then re-reads a batch it cannot tell apart
from an unstarted one.
**Where** `plugins/agent-kit/scripts/orchestrate.py:998-1008`
**Evidence**
```python
1005            self.run.event("empty", "no children to build — handing back")
1006            self.tell(f"{self.run.slug} has no children to build")
1007            self.hand_back(state)
1008            return 1
```
**Verdict** CONFIRMED.
**Type** orphan-record / undefined-behaviour-when-unattended
**Severity** corrupts-a-record
**What closes it** Program: `self.run.set(step="blocked")` before the hand-back.

---

### 15. `take_control` is skipped when the queue's head has no run file

**What** `go()` `continue`s on a missing run file before reading `control`. A `stop` the owner
wrote while the head is a missing child is not seen until the next child that does have a file —
and the file is not deleted either, so the owner watching it sit there gets no signal.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1050-1054`
**Evidence**
```python
1050            if not child.file.is_file():
1051                self.run.event("missing", f"{slug} has no run file")
1052                continue
1053
1054            instruction = take_control(self.run)
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** breaks-a-run (the owner's only lever misses)
**What closes it** Program: read `control` before the missing-file check.

---

### 16. An unparsed 429 reset time silently becomes a five-minute wait

**What** `wait = (when - time.time()) if when else self.opt.poll * 5`. `limit_reset` returns
`("limit", None)` when `RESET_RE` does not match the 429 text. The run then loops through the
limit branch every five minutes, logging `limit sleeping 5m` — with no line anywhere saying the
reset time could not be read. This is the kit's own *"a check that cannot read its input says
so"* rule, unmet in the driver.
**Where** `plugins/agent-kit/scripts/orchestrate.py:750`
**Evidence**
```python
750                wait = (when - time.time()) if when else self.opt.poll * 5
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** wastes-tokens (and hides a weekly limit as a session one)
**What closes it** Program: one `run.event("limit-unreadable", …)`, said once per session.

---

### 17. `sync_states` returns without a word when `gh` is not installed

**What** Every entry sitting at `building (pr: N)` is then unreported — indistinguishable from a
project where no entry is mid-flight. `delivered_branches` ten lines away goes out of its way to
say *"nothing here could ask about pull request N"*. Same class of defect, same file.
**Where** `plugins/agent-kit/scripts/check.py:1452-1453`
**Evidence**
```python
1452    if not gh.available:
1453        return
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** corrupts-a-record (a merged feature sits at `building` with nothing saying so — the
exact regression the docstring above it records)
**What closes it** Program: emit the same `unasked` statement `delivered_branches` already has.

---

### 18. `Github.open_requests` returns `[]` on every failure

**What** `gh` absent, unauthenticated, rate-limited, no remote, or JSON it cannot parse — all
produce `[]`. `print_state` then prints no PR lines at all, identical to a repository with no open
pull requests. This is the exact confusion the `Github` docstring says the class exists to end,
and `states()` handles it correctly two methods above.
**Where** `plugins/agent-kit/scripts/check.py:1403-1411`
**Evidence**
```python
1407        if not done or done.returncode != 0:
1408            return []
1409        try:
1410            rows = json.loads(done.stdout or "[]")
1411        except ValueError:
1412            return []
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** breaks-a-run (`next`'s rungs 3-5 are entirely about open PRs)
**What closes it** Program: return `None` on "could not ask" and let `print_state` say so, as
`states()`/`asked` already do.

---

### 19. `prove_manual` treats every non-zero, non-127 exit as "not yet"

**What** A `proof` script that exists and crashes (exit 1, 2, …) is indistinguishable from a
proof correctly reporting the work is not done — despite the docstring promising the two are
separated. Only exit 0 (done) and exit 127 (no such command) are named.
**Where** `plugins/agent-kit/scripts/check.py:1192-1195`
**Evidence**
```python
1192        if proved.returncode == 0:
1193            done.append(action)
1194        elif proved.returncode == 127:             # the command does not exist here
1195            broken.append((action, "no such command on this machine"))
```
**Verdict** CONFIRMED — no `else`.
**Type** silent-failure
**Severity** corrupts-a-record (a manual line never leaves the ledger and nobody learns why)
**What closes it** Program: an `else` that names the exit code and stderr.

---

### 20. A damaged install silently stops judging every run file and every batch record

**What** `run_template` swallows `OSError`/`ValueError` and `check_runs` returns on an empty
`known`; `batch_template`/`check_batches` do the same. A missing or unparseable
`templates/run.json` therefore disarms the whole run-file check without a word — precisely the
dependency-of-the-check failure that `check_epic:905-911` and `check_verification:700-705` were
rewritten to announce for `verification.yml`.
**Where** `plugins/agent-kit/scripts/check.py:1869-1876, 1924-1926, 1980-1987, 2114-2115`
**Evidence** `if not known: return` in `check_runs`.
**Verdict** CONFIRMED (read; matches the reported line numbers).
**Type** silent-failure
**Severity** corrupts-a-record
**What closes it** Program: report the unreadable template as a finding, the way the catalogue
already is.

---

### 21. `check_verification`'s "could not read the catalogue" line is invisible to `ship` and `fix`

**What** Line 700-705 exists so an unreadable `verification.yml` is not silence. It goes into
`report.sight`, and `sight_lines` prints only under `--status`/`--state`. `ship` and `fix` both
run the check **bare**. So the two commands most likely to hit it get nothing. The duplicate of
the same line inside the `--epic` gate is reached, because that gate prints `fatal` directly.
**Where** `plugins/agent-kit/scripts/check.py:700-705`, `3090-3104`, `3834`, `3852`;
callers `skills/ship/SKILL.md:69`, `skills/fix/SKILL.md:41`
**Evidence** ship's preflight is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" .` — no flags.
**Verdict** CONFIRMED — read both call sites.
**Type** silent-failure
**Severity** breaks-a-run
**What closes it** Program: route the cannot-read lines to `report.groups` (always printed)
rather than to `report.sight`.

---

### 22. `check_commands` returns silently when `commands` is not a dict, and delegates to a printer `ship`/`fix` never reach

**What** The comment says the shape is "said by `print_state`, which owns that shape" — but
`print_state` only runs under `--state`, and `ship`/`fix` run bare. On a project whose
`commands:` is a scalar, neither command gets a word about it from any surface.
**Where** `plugins/agent-kit/scripts/check.py:1005-1008`
**Evidence**
```python
1006    if not isinstance(commands, dict):
1007        return                                    # said by `print_state`, which owns that shape
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** breaks-a-run
**What closes it** Program: same fix as #21.

---

### 23. `tracked_manifests` returns `[]` when git is missing or `git ls-files` fails

**What** The "a dependency manifest project.yml does not record" finding then never fires,
silently. There is no distinction between "this project has no manifests" and "git could not be
asked".
**Where** `plugins/agent-kit/scripts/check.py:845-847` (vs the finding at `836-840`)
**Verdict** CONFIRMED (read; matches).
**Type** silent-failure
**Severity** confuses-a-reader
**What closes it** Program: one statement line.

---

### 24. `workflows` skips a file it cannot read, so "nothing runs it on a push" can be said about the repository whose only push workflow was skipped

**What** `except OSError: continue`. The file is then absent from `names`, from `blob`, and from
the `fires` disjunction — so `outside_a_session` and `outside_line` can assert the opposite of
the truth.
**Where** `plugins/agent-kit/scripts/check.py:2891-2893`; consumers `2899-2916`, `3140-3162`
**Verdict** CONFIRMED (read; matches).
**Type** silent-failure
**Severity** confuses-a-reader
**What closes it** Program: a named "could not read" line, which `outside_a_session`'s fourth
answer ("cannot say") already has a slot for.

---

### 25. `where_line` is loud when `CLAUDE.md` is absent and mute when it is present and unreadable

**What** An asymmetry in one function: the missing-file branch prints a full explanation, the
`OSError` branch returns.
**Where** `plugins/agent-kit/scripts/check.py:3126-3129`
**Evidence**
```python
3126    try:
3127        if WHERE_MARK in path.read_text(encoding="utf-8", errors="replace"):
3128            return
3129    except OSError:
3130        return
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** confuses-a-reader
**What closes it** Program: one line.

---

### 26. Seven read sites in `check.py` crash on a non-UTF-8 file, and the caller reads the traceback as "the check found something"

**What** `Doc.__init__` (236), `check_sources` (400), `collect_debt` (1073), `read_manual`
(1095), `check_channels` (2237, 2247), `check_audits` (2285) and the `run_template` callers read
with `read_text(encoding="utf-8")` and no `errors=` and no `try`. A knowledge, debt, manual or
audit file in another encoding raises `UnicodeDecodeError` out of `main()` — a traceback and a
non-zero shell status. Every caller that reads only the exit code (every build command's
preflight) reads that as a finding. Contrast `where_line`/`workflows`/`scenarios`/`audit_lenses`,
which all pass `errors="replace"`.
**Where** `plugins/agent-kit/scripts/check.py:236, 400, 1073, 1095, 2237, 2247, 2285`
**Verdict** CONFIRMED (grep-level; the four contrasting sites do pass `errors="replace"`).
**Type** silent-failure (a crash indistinguishable from a finding)
**Severity** breaks-a-run
**What closes it** Program: `errors="replace"` everywhere, or one shared reader.

---

### 27. `epic --advance` re-does the closing session's work, unconditionally, with no signal passed between them

**What** The driver calls `close()` (5.0M tokens measured) and then `hand_back()` (3.3M measured)
one after the other, with nothing telling the advance session what the closing session already
did. Recorded as an open defect in two design notes; the code still pays it every batch.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1123`, `1159`/`1165`;
`docs/design/2026-08-16-what-the-review-refused.md:151`;
`docs/design/2026-08-14-where-the-tokens-burn.md:174`
**Verdict** CONFIRMED — `close()` calls `hand_back(state)` on both branches, with no argument
about what was written.
**Type** wastes-tokens
**Severity** wastes-tokens (≈3.3M tokens per batch, on the kit's own measurement)
**What closes it** Program: pass what `close()` wrote into `hand_back`, or have the advance
session read `docs/runs/<slug>.json` as proof and skip.

---

### 28. The `blocked`-cascade turns one dead session into up to N−1 lost features

**What** The driver writes `blocked` for a session that died, stalled or hit a limit — nothing to
do with the feature — and `go()` then adds that slug to `self.skip`, skipping everything that
names it in `needs` (or, absent `needs`, names it as authored `parent`). `frame`/`needs` narrows
*which* descendants are lost; it does not stop a dead session being read as a broken feature.
**Where** `plugins/agent-kit/scripts/orchestrate.py:827-828` (writes `blocked`),
`1117-1118` (adds to `skip`), `1104-1109` (cascade); `docs/design/2026-08-12-frame.md:17-21`
**Verdict** CONFIRMED — read; and the design note records it as known and unclosed.
**Type** undefined-behaviour-when-unattended
**Severity** wastes-tokens (a night's queue lost to one stall)
**What closes it** Program: separate "the feature is broken" from "the session died" in what
`build()` writes, and cascade only on the first.

---

### 29. The closing session's cost is never counted

**What** `record_spend(built)` runs *before* `close()`. Every `self.sessions += 1` inside the
closing `watch()` lands after `spent` was written and is lost, and `spent.hours` stops at the
same line. The closing session is the single most expensive session in a batch (5.0M measured),
and the gate that prices the next epic's scope reads `spent` and nothing else.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1122-1123`, `1137-1141`
**Evidence**
```python
1122        self.record_spend(built)
1123        self.close()
```
**Verdict** CONFIRMED.
**Type** corrupts-a-record
**Severity** corrupts-a-record (the one measured number an owner plans against, systematically low)
**What closes it** Program: move `record_spend` after `close()`, or call it twice.

---

### 30. `WHO_RUNS` and `verification.yml`'s `command:` keys are two copies of one list that nothing holds together

**What** `WHO_RUNS` names six commands (`test`, `lint`, `types`, `mutate`, `e2e`, `run`);
`verification.yml` carries five `command:` values (`test`, `e2e`, `mutate`, `types`, `lint`) and
no kind for `run`. Nothing in `check.py` or `validate.sh` compares them. A kind renamed in
`verification.yml` would silently drop out of `print_outside`'s exclusion.
**Where** `plugins/agent-kit/scripts/check.py:2851-2859`; `plugins/agent-kit/verification.yml:29,35,41,47,53`
**Evidence** `grep -n "^  command:" verification.yml` → exactly five; `WHO_RUNS` → six keys.
`grep -rn WHO_RUNS` finds no validate.sh hit.
**Verdict** CONFIRMED.
**Type** contradiction-between-files
**Severity** corrupts-a-record
**What closes it** Program: one assertion in `scripts/validate.sh` — the kit's own rule says a
rule about the kit itself belongs there.

---

### 31. `validate.sh`'s run-file field-coverage check is a word-presence test, and passes vacuously for prose-shaped names

**What** The check requires each non-`_` field name to appear as a word in ≥2 payload files. For
`gate`, `task`, `base`, `approach`, `children` — English words that appear in prose everywhere —
this is satisfied by sentences like *"an epic's gate prices its scope"*. So "no field is
orphaned" is much weaker evidence than it reads as, and the check's own comment admits it ("a
generic name like `task` passes on prose alone") without acting on the admission.
**Where** `scripts/validate.sh:465-500`
**Evidence**
```python
        named = [p for p, text in texts.items() if re.search(rf"\b{re.escape(field)}\b", text)]
        if len(named) < 2:
```
**Verdict** CONFIRMED — read the check and its own comment.
**Type** silent-failure (a check that cannot really read its input and does not say so)
**Severity** confuses-a-reader
**What closes it** Program: match `"<field>"` in JSON/quoted form, or `\bstate.get\("<field>"` /
backticked form, rather than a bare word.

---

### 32. `gate` is a run-file field no program reads, with no `_gate` doc line, and an undefined meaning at batch level

**What** `templates/run.json:13` carries `"gate": "owner"`. `orchestrate.py` never references
`gate`. It is read only by a session, through prose in `rules/preflight.md`. What the field means
on a *batch's* own file (as opposed to a feature's) is stated nowhere. It is also one of thirteen
fields in `templates/run.json` with no `_<name>` doc line (`slug`, `command`, `gate`, `entries`,
`task`, `branch`, `base`, `approach`, `seams`, `deviations`, `blockers`, `pr`, `children`), while
`_records` is a doc line for a field that no longer exists.
**Where** `plugins/agent-kit/templates/run.json:13`; `plugins/agent-kit/skills/sprint/SKILL.md:147`
**Evidence** `grep -n gate scripts/orchestrate.py` returns only prose in comments. Computed:
`fields with no _doc: ['slug','command','gate','entries','task','branch','base','approach','seams','deviations','blockers','pr','children']`, `_docs with no field: ['records']`
**Verdict** CONFIRMED.
**Type** orphan-record
**Severity** confuses-a-reader
**What closes it** Template: a `_gate` line saying who reads it and what it means on a batch;
delete `_records`.

---

### 33. `accept` is on neither preflight list — not the stop list, not the exemption

**What** `rules/preflight.md:35-38` names `ship`, `fix`, `sprint`, `epic` and `next` as commands
that must not start while a run holds the checkout, and names `blueprint` and `advise` as the two
that never stop. `accept` is in neither sentence. Its own boundary ("changes nothing, decides
nothing") suggests it belongs with `blueprint`, but no file says so.
**Where** `plugins/agent-kit/rules/preflight.md:35-38`; `plugins/agent-kit/skills/accept/SKILL.md:14`
**Evidence**
> "That is `ship`, `fix`, `sprint`, `epic` and `next` — everything that writes code or moves a
> branch. `blueprint` and `advise` are not on that list and never stop"
**Verdict** CONFIRMED — read the rule; `accept` appears in neither list.
**Type** missing-rule
**Severity** confuses-a-reader
**What closes it** Shared rule: add `accept` to the exemption sentence in `rules/preflight.md`.
One word.

---

### 34. `audit` never runs a preflight check, unlike every other command

**What** `skills/audit/SKILL.md` contains no `check.py` invocation at all — `grep` over the file
returns nothing. `advise` has an explicit `## Preflight` section; `sprint`, `next`, `ship`, `fix`
and `epic` all show the invocation. The tally format audit must produce is read by
`check_audits`, so audit is a writer for a check it never runs.
**Where** `plugins/agent-kit/skills/audit/SKILL.md` (absence)
**Evidence** `grep -n "check.py" skills/audit/SKILL.md` → no output.
**Verdict** CONFIRMED.
**Type** missing-rule
**Severity** confuses-a-reader
**What closes it** Either a `SKILL.md` line adding the preflight, or one sentence in
`rules/preflight.md` saying `audit` is exempt and why — the kit's own rule prefers the shared
rule, since the same question was already asked of `blueprint` and `advise` there.

---

### 35. A stale comment inside the driver describes behaviour removed in 2.28.1

**What** `orchestrate.py:1231-1232` still reads *"no message anywhere, because the launch line
sends the driver's output to /dev/null."* The launch line has redirected to `driver.out` since
2.28.1. The comment is now the only remaining record of a behaviour that no longer exists.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1231-1232` vs `skills/sprint/SKILL.md:236`
**Evidence**
```
1231 # standing two days later. The night it did remember, the driver wrote two lines and died with it —
1232 # four features queued, nothing started, and no message anywhere, because the launch line sends the
1233 # driver's output to /dev/null.
```
against
```
236   >> .agent-kit/runs/<batch>/driver.out 2>&1 &
```
**Verdict** CONFIRMED — read both.
**Type** contradiction-between-files
**Severity** confuses-a-reader
**What closes it** Prose deletion: three words in the comment.

---

### 36. After the detach, `driver.out` only ever gets one line

**What** `main()` prints the detach notice and returns 0; the real driver runs under systemd and
its output goes to the journal. So on the machine this kit runs on, the file the launch line was
added to create stays one line long, and the defect it was added to fix — *"a driver that died in
its first second and a driver with nothing to say looked identical"* — is only half closed.
`run.log` is still written directly by the detached process and is the reliable record.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1325-1329`; `skills/sprint/SKILL.md:238-240`
**Verdict** CONFIRMED — `detach()` succeeding returns 0 from `main()` after one `print`.
**Type** orphan-record (a file with a writer that writes one line, and no declared reader)
**Severity** confuses-a-reader
**What closes it** Two options, one decision: drop `driver.out` from the launch line and point at
`journalctl` in prose, or keep it and give it a channels row (see #8). Both are cheap; leaving
both half-done is what costs.

---

### 37. No `driver-exit` line: a driver that finished and a driver that was killed leave the same last log line

**What** `go()` returns 0 and `main()` returns it with no final `event`. Listed as still open in
the design note, and the source confirms it.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1124`, `1357`;
`docs/design/2026-08-20-the-driver-died-with-its-session.md:101-110`
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** confuses-a-reader
**What closes it** Program: one `Run.event("driver-exit", …)` line.

---

### 38. `--record` rewrites `project.yml` even when nothing changed

**What** The knowledge-file loop correctly guards with `if text != doc.text`. The manifest half
does not: `manifest_path.write_text(text, …)` is unconditional whenever the file exists. It
touches the mtime of a file the program's own docstring says it writes only when asked to change
something — and mtime is what `stop.py`'s `STALE_AFTER` reasoning is built on elsewhere.
**Where** `plugins/agent-kit/scripts/check.py:1639` (vs the guarded `1617`)
**Evidence**
```python
1616        if text != doc.text:
1617            doc.path.write_text(text, encoding="utf-8")
...
1639        manifest_path.write_text(text, encoding="utf-8")
```
**Verdict** CONFIRMED.
**Type** other
**Severity** cosmetic
**What closes it** Program: one `if`.

---

### 39. `--pr-body`'s table measurement is a heuristic, not a parse

**What** `rows - 2` assumes every run of `|`-leading lines is a table with a header and a
separator. A fenced example, a diagram, or a quoted block of pipes is counted as one and can trip
the `PR_TABLE_MAX` defect. `<details>` stripping is a non-greedy regex, so a nested `<details>`
is closed by the inner `</details>` and every number on that screen is skewed; an unclosed one
is not stripped at all.
**Where** `plugins/agent-kit/scripts/check.py:3560`, `3577`, `3590`
**Evidence**
```python
3560    open_text = re.sub(r"<details\b.*?</details>", "", text, flags=re.S | re.I)
3590    if rows - 2 > PR_TABLE_MAX:
```
**Verdict** CONFIRMED.
**Type** other
**Severity** confuses-a-reader
**What closes it** Program: require a separator row (`|---`) before counting a block as a table;
count `<details>` depth rather than regex-stripping.

---

### 40. `brief`'s "did you mean" and `run_defects`'s entry-key check answer the same question two ways in one file

**What** `brief` uses substring matching (`key.split(".")[-1] in k`); `run_defects` uses
`difflib.get_close_matches` at cutoff 0.8. A typo that one suggests, the other does not.
**Where** `plugins/agent-kit/scripts/check.py:1808` vs `2458`
**Evidence**
```python
1808        near = sorted(k for k in entries if key.split(".")[-1] in k)
2458                        for m in difflib.get_close_matches(u, sorted(known), n=2, cutoff=0.8)]
```
**Verdict** CONFIRMED.
**Type** other
**Severity** cosmetic
**What closes it** Program: one shared helper.

---

### 41. `bounds_section` still carries the hard-coded English string the comment says was removed

**What** `check_epic`'s comment at 866-874 records that a hard-coded heading was removed because
a Russian-language project was told it had no bounds section. The literal `"MVP bounds"` is still
one of `bounds_section`'s three fallbacks — the same language assumption, one layer down. (The
`MVP_MARK` marker path is tried first, so this only bites a project with no marker.)
**Where** `plugins/agent-kit/scripts/check.py:1549`
**Evidence**
```python
1548    return (section_of(text, "MVP bounds")
1549            or (section_of(text, found.group(0).lstrip("# ").strip()) if found else None))
```
**Verdict** CONFIRMED — read; the string is there.
**Type** other
**Severity** confuses-a-reader
**What closes it** Prose deletion in the comment (say the fallback is deliberate) or program
deletion of the fallback. Not both.

---

### 42. `report.add("MVP", line)` is dead code

**What** `check_epic` is called from exactly one place, which prints `fatal` directly and returns
before `report.groups` is ever printed. Nothing anywhere prints the `MVP` group.
**Where** `plugins/agent-kit/scripts/check.py:924`; caller `3730-3735`; printer `3855`
**Evidence**
```python
923    for line in fatal:
924        report.add("MVP", line)
```
`grep -n 'check_epic('` → definition 849, call 3730. `grep -n 'report.groups'` → 3855, 3860 —
both after the `return` at 3735.
**Verdict** CONFIRMED.
**Type** dead-code
**Severity** cosmetic
**What closes it** Program: delete the two lines.

---

### 43. `runfile.MANIFEST` is a dead constant, and the same string is hard-coded in two other files

**What** `runfile.py:28` defines `MANIFEST = ".agent-kit/project.yml"`. `grep -rn
"runfile.MANIFEST"` finds nothing. `check.py:52` defines its own copy; `guard.py:141,167`
hard-codes the path inline. One fact in three places, with the shared one unused.
**Where** `plugins/agent-kit/scripts/runfile.py:28`; `scripts/check.py:52`; `hooks/guard.py:141,167`
**Verdict** CONFIRMED — grep found zero readers of the shared constant.
**Type** dead-code
**Severity** cosmetic
**What closes it** Program: import it in the two readers, or delete it. Either way, one commit.

---

### 44. `runfile.branch_shape()` is a function with no caller anywhere in the repository

**What** Defined at `runfile.py:208`. `grep -rn "branch_shape"` across `plugins/`, `scripts/` and
`tests/` returns exactly one hit — the definition. No caller, no test.
**Where** `plugins/agent-kit/scripts/runfile.py:208-210`
**Evidence**
```python
208 def branch_shape(name: str) -> bool:
209     """Whether a name is one this kit makes. A slug written where a branch belongs has no `/`."""
210     return bool(re.match(r"^[^/]+/.+", name or ""))
```
**Verdict** CONFIRMED — single grep hit.
**Type** dead-code
**Severity** cosmetic
**What closes it** Program: delete it, or wire it into `run_defects`'s branch check where the
docstring implies it belongs.

---

### 45. Two documented values for the same instruction about `--ceiling` on a 200k-window model

**What** `orchestrate.py:477-479` says such a project "must lower this to about 130k";
`docs/design/2026-08-14-what-one-night-measured.md:49` says "must set `--ceiling 150`". Neither
cites the other.
**Where** `plugins/agent-kit/scripts/orchestrate.py:477-479`;
`docs/design/2026-08-14-what-one-night-measured.md:49`
**Verdict** CONFIRMED by the reporting sector's reading of both; I did not re-open the design
note, so the second half is UNVERIFIABLE by me.
**Type** contradiction-between-files
**Severity** confuses-a-reader
**What closes it** Prose: pick one number and make the other cite it.

---

### 46. `--room` is a live flag with no effect at any shipped configuration

**What** With the shipped defaults (ceiling 210, room 40, floor ≈46k) the `room` term can never
be the binding one. Its own help text says so ("binds only where the ceiling is under ~86k, which
is a ceiling set by mistake") and `docs/design/2026-08-14-where-the-tokens-burn.md:148` says
"`--room` has been inert since the counter was fixed". It is kept because `validate.sh` requires
every flag to be named in prose, and prose is where it is now justified.
**Where** `plugins/agent-kit/scripts/orchestrate.py:1305-1309`, `481-483`
**Verdict** CONFIRMED — deliberate and documented in three places.
**Type** dead-code (deliberate)
**Severity** cosmetic
**What closes it** Nothing, if the decision is to keep it. If it goes, the kit's own third answer
applies: a design note that says the smoke alarm is being taken down.

---

### 47. `floor-unreadable` is said only for feature children

**What** `opening_size` returning 0 disables `room` entirely — deliberate and documented — and it
logs `floor-unreadable` once. But only when `hand_over` is true, which is only for
`runfile.kind == "feature"`. A frame, close or audit child never says its floor was unreadable.
Since `hand_over` is false for those, `room` never applies to them either, so the practical cost
is small; the asymmetry is what a full map should carry.
**Where** `plugins/agent-kit/scripts/orchestrate.py:722-731`, `481-483`
**Evidence** `if hand_over and not blind and not floor and size:`
**Verdict** CONFIRMED.
**Type** silent-failure (narrow)
**Severity** cosmetic
**What closes it** Program: drop `hand_over` from that condition, or say in the comment why it
belongs.

---

### 48. `launcher.alive` and `tmux_name` can disagree across two processes on different PATHs

**What** `tmux_name` picks the `cc-` prefix purely on whether `claude-new` is on *this* process's
PATH. The detached copy carries PATH forward explicitly for exactly this reason, but a driver
started by hand with a different PATH would probe `agent-kit-<slug>` for sessions named
`cc-<slug>` and conclude nothing is running — including in the single-driver check (#11).
**Where** `plugins/agent-kit/scripts/orchestrate.py:153-154`; PATH carried at `1275`
**Evidence**
```python
153    def tmux_name(self, name: str) -> str:
154        return f"cc-{name}" if self.helper else f"agent-kit-{name}"
```
**Verdict** CONFIRMED.
**Type** race / concurrency
**Severity** corrupts-a-record (in combination with #11)
**What closes it** Program: probe both prefixes in `alive`.

---

### 49. `newest_transcript`'s slug filter reads only the first 12 lines of a transcript

**What** The prompt the driver typed is normally the first user record, so the filter holds. A
session whose harness writes more than 12 preamble records before the prompt falls back to
"newest of the fresh ones" — a guess narrowed only by the 60-second `opened_at` window. The
fallback is silent.
**Where** `plugins/agent-kit/scripts/orchestrate.py:275`, `278`, `281`
**Verdict** CONFIRMED (read; matches the reported lines).
**Type** silent-failure
**Severity** breaks-a-run (the driver watches the wrong session's transcript)
**What closes it** Program: raise the head, or say when the fallback was taken.

---

### 50. `check_channels`'s three allowed run-directory filenames are hard-coded where `runfile.py` owns everything else about a run directory

**What** `run.json`, `run.log`, `control` are listed inline in `check.py:2216` and nowhere else. A
fourth file the kit starts writing (see #8) is reported by this check alone, and the list cannot
be changed in one place.
**Where** `plugins/agent-kit/scripts/check.py:2216`; ownership `plugins/agent-kit/scripts/runfile.py`
**Verdict** CONFIRMED.
**Type** contradiction-between-files
**Severity** confuses-a-reader
**What closes it** Program: a `runfile.RUN_DIR_FILES` constant, read here. Fixing #8 should fix
this in the same commit.

---

### 51. `guard.py` and `stop.py` read the identical signal — an unparseable run file — in opposite directions

**What** `guard.py`'s `in_flight` (via `runfile.in_flight`) treats a run file nothing can parse
as *in flight*, deliberately, so the merge guard is not silently disarmed. `stop.py`'s `my_runs`
filters with `state is not None`, so an unreadable run file is never this session's run and can
neither block a turn nor be closed as a finished epic. Each is justified in its own docstring;
neither names the other.
**Where** `plugins/agent-kit/hooks/guard.py` (via `runfile.py:138`) vs `plugins/agent-kit/hooks/stop.py:84-85`
**Evidence**
```python
84    return [(directory, state) for directory, state in runfile.runs(root)
85            if state is not None and state.get("session") == session]
```
**Verdict** CONFIRMED — both read, both documented, neither cross-references.
**Type** contradiction-between-files (intentional)
**Severity** confuses-a-reader
**What closes it** Prose: one sentence in each docstring naming the other and why they differ.

---

### 52. `declared_e2e` / `declared_verification` are a hand-rolled YAML subset, and a `#` inside a quoted value truncates it

**What** Both parse `project.yml` line-by-line by indentation, stripping `#` comments with
`raw.split("#", 1)[0]` — which cuts a `#` inside a quoted string. Multi-line strings and
flow-style mappings are also invisible. `declared_e2e` then degrades to `""`, so the e2e-walk and
own-checks exemptions silently fail to fire: a false negative, not a crash. This is by design
("a hook that started interpreting a manifest would be a second opinion about a file that has an
owner") but the degradation is unsaid.
**Where** `plugins/agent-kit/hooks/guard.py:138-178`
**Evidence**
```python
146        line = raw.split("#", 1)[0].rstrip()
```
**Verdict** CONFIRMED.
**Type** silent-failure
**Severity** breaks-a-run (a legitimate e2e run is refused by the guard)
**What closes it** Program: skip `#` inside quotes. Ten lines.

---

### 53. `templates/knowledge/entities.md` states a cross-check no program performs

**What** The header says *"An action that sets a status the entity does not list is a defect, and
that cross-check only works if the states are written down."* No function in `check.py` parses an
entity's `**States:**` line against the status string an action's "What changes" field sets.
`check_references`/`REF_RE` catch backticked `a.b` key references only. `grep -n "States"
check.py` returns exactly one hit, an unrelated PR-state report group.
**Where** `plugins/agent-kit/templates/knowledge/entities.md:4-5`; absence in `scripts/check.py`
**Evidence** `grep -n "States" scripts/check.py` → one hit at line 1463, `report.add("States",
f"… pull request {number} unreadable")` — a different thing entirely.
**Verdict** CONFIRMED.
**Type** missing-rule (a rule with no home)
**Severity** confuses-a-reader
**What closes it** By the kit's own order: a **program** — the check the template promises — or,
if it will not be built, delete the promise from the template.

---

### 54. `--offline` has no payload caller and exists only for tests

**What** Declared with `argparse.SUPPRESS`. `grep -rn "\-\-offline"` across `plugins/` and
`scripts/` finds only the declaration and `skills/next/SKILL.md:107`, which says *never* to use
it. Every caller is a test.
**Where** `plugins/agent-kit/scripts/check.py:3607`; tests at `tests/test_check.py:106, 576, 590, 600, 928`
**Verdict** CONFIRMED, and **intentional** — the comment at 3602-3606 says it is a seam kept out
of `--help` precisely because advertising it invited a run going blind. Recorded so the map does
not read it as dead code.
**Type** other (documented test seam)
**Severity** cosmetic
**What closes it** Nothing.

---

### 55. `sprint` never names `accept`, but `accept` reads what `sprint` writes

**What** `grep -rn accept skills/sprint/` returns only feature slugs containing the word.
`accept/SKILL.md:33` reads `docs/runs/*.json` and `.agent-kit/runs/*/run.json` — both written by
sprint's closing session. The contract is real and documented on the reader's side only.
**Where** `plugins/agent-kit/skills/accept/SKILL.md:33`; absence in `skills/sprint/`
**Verdict** CONFIRMED.
**Type** orphan-record (a promise with a reader the writer does not know about)
**Severity** confuses-a-reader
**What closes it** Shared rule: `rules/channels.md`'s row for `docs/runs/<slug>.json` should name
`accept` among its readers. One cell.

---

### 56. `next` is the only closing command that does not cite `rules/closing.md` by path

**What** `fix/SKILL.md:140` and `accept/SKILL.md:122` both cite
`${CLAUDE_PLUGIN_ROOT}/rules/closing.md`. `next/SKILL.md` writes its own three-block report
structure inline and never cites the shared rule, though the shape mirrors it.
**Where** `plugins/agent-kit/skills/next/SKILL.md:262-286` (absence); vs `skills/fix/SKILL.md:140`,
`skills/accept/SKILL.md:122`
**Evidence** `grep -n "closing.md" skills/next/SKILL.md` → no output.
**Verdict** CONFIRMED.
**Type** contradiction-between-files
**Severity** confuses-a-reader
**What closes it** Rule move: cite the shared rule and delete the inline copy, or say in prose why
`next` diverges.

---

### 57. `prove_manual`'s and `ran`'s `timeout` parameters are never overridden

**What** Both take a `timeout` argument; every caller uses the default. `main:3662` calls
`prove_manual(root)`.
**Where** `plugins/agent-kit/scripts/check.py:1164`, `155`; caller `3662`
**Verdict** CONFIRMED — grep found one call site, no keyword.
**Type** dead-code (a parameter with no user)
**Severity** cosmetic
**What closes it** Program: delete the parameter, or make it a flag.

---

### 58. `Launcher._tmux`'s FileNotFoundError fallback reports the inner args, not the full command

**What** `CompletedProcess(args, 127, "", "tmux is not installed")` is built with `args` — the
tuple *after* `"tmux"` — so the returned object's `args` field omits the program name. Harmless
today; misleading if anything ever logs it.
**Where** `plugins/agent-kit/scripts/orchestrate.py:151`
**Evidence**
```python
151            return subprocess.CompletedProcess(args, 127, "", "tmux is not installed")
```
**Verdict** CONFIRMED.
**Type** cosmetic
**Severity** cosmetic
**What closes it** Program: `["tmux", *args]`.

---

## REFUTED CLAIMS

1. **"`runfile.BRANCH_PREFIXES` is a maybe-dead shared constant."** (hooks-runfile.md #2)
   REFUTED. `check.py:145` re-exports it and uses it twice, at `check.py:1670` (`if not
   name.startswith(BRANCH_PREFIXES): continue`) and `check.py:1700`. It is a live shared
   constant with a real reader; the report was correct only that `guard.py` does not use it,
   which is not the same claim.

2. **"`watch()` may leave `self.watched` pointing at the previous child."** (orchestrate.md #19)
   REFUTED, and self-refuted in the report itself: `self.watched = current` is set before the
   start attempt, so the early return at "could not start a session" cannot leave a stale value.
   Recorded here so nobody re-derives it.

3. **"`runfile.STEPS` includes `closing`, which the template does not mention."**
   (hooks-runfile.md #7) REFUTED, and self-refuted: `templates/run.json:4` does document
   `closing` ("which only a driver writes on a batch's own file"). Verified — the two agree.

4. **"`assumptions[].expensive` is a record with a writer and no reader."** REFUTED as a
   present-tense claim. `orchestrate.py`'s `costly()` reads it and relays the first one via
   `tell()`. The docstring's "read by nothing" describes the state *before* that method existed
   and reads as current.

5. **"The driver manages worktrees."** Not claimed by any report, but worth stating as settled:
   there is no `git worktree` call anywhere in `orchestrate.py`; `runfile.main_worktree` is
   imported and used by `guard.py:210` and by `runfile.runs`, never by the driver.

6. **"`epic`'s gate is fully unprotected on a project with no blueprint."** PARTIALLY REFUTED.
   Finding #9 is real — `--epic` is silent and returns 0 — but `epic/SKILL.md:40-41` runs a
   *second* line, `check.py . --status --state`, which does print `no docs/knowledge/ — this
   project has no blueprint yet`. Verified empirically. The gate opens; the session is told
   anyway. The defect is that the gate the prose calls *"fatal or silent"* is silent in the one
   case it most needs to be fatal.

---

## OPEN QUESTIONS FOR THE OWNER

No file answers these and no program decides them.

1. **Does `driver.out` stay?** (#8, #36) It is created by the launch line, reported as drift by
   the checker, has no channels row, and receives one line on a systemd machine. Keep it with a
   row and an allowlist entry, or delete it from both launch lines and point at `journalctl`.
   Both are cheap; the current half-state is what costs.

2. **Is `accept` allowed to run while a run holds the checkout?** (#33) Its own boundary says it
   changes nothing, which argues for the `blueprint`/`advise` exemption — but only the owner can
   say whether reading run files mid-flight is safe enough to write down as a rule.

3. **Does `audit` get a preflight, or an exemption?** (#34) Every other command has one of the
   two. Which it should be is a judgement about whether a lens may look at a tree a run is
   holding.

4. **What is `gate` on a batch's own run file?** (#32) The per-feature meaning is specified. The
   batch-level field is written by the brief, read by nothing, and documented nowhere.

5. **Does the entity states/transitions cross-check get built, or does the promise come out of
   the template?** (#53) The template asserts a defect class no program detects.

6. **`--ceiling` on a 200k model: 130k or 150k?** (#45) Two files, two numbers, no citation
   between them. Only a measurement or a decision settles it.

7. **Is the `blocked`-cascade acceptable?** (#28) It is measured, documented and unclosed. Losing
   up to N−1 features to one dead session may be the accepted price of a simple queue — but the
   design note reads as an open defect, not as an accepted one, and the kit's own third answer
   (who may close a rule, and where) is missing here.

8. **`--room`: smoke alarm or deletion?** (#46) The kit's own rule says a prose rule is closed by
   a design note that says so. No such note exists for `--room`.

---

## COUNTS BY TYPE AND SEVERITY

### By type

| type | count | findings |
|---|---|---|
| silent-failure | 17 | 2, 3, 9, 10, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 31, 47, 49, 52 (20 incl. narrow) |
| dead-code | 6 | 42, 43, 44, 46, 54, 57 |
| contradiction-between-files | 7 | 8, 30, 35, 45, 50, 51, 56 |
| race / concurrency | 3 | 11, 12, 48 |
| corrupts-a-record | 3 | 1, 7, 29 |
| orphan-record | 4 | 8, 14, 32, 36, 55 |
| unbounded-loop | 2 | 4, 5 |
| undefined-behaviour-when-unattended | 4 | 1, 6, 13, 14, 28 |
| missing-rule | 3 | 33, 34, 53 |
| wastes-tokens | 2 | 27, 28 |
| other / cosmetic | 5 | 38, 39, 40, 41, 58 |
| provider-lock-in | 0 | — |

(Some findings carry two types; the primary is used in each finding's own block.)

### By severity

| severity | count | findings |
|---|---|---|
| breaks-a-run | 14 | 2, 4, 5, 6, 9, 10, 13, 15, 18, 21, 22, 26, 49, 52 |
| corrupts-a-record | 11 | 1, 3, 7, 8, 11, 12, 14, 17, 19, 20, 29, 30, 48 |
| wastes-tokens | 3 | 16, 27, 28 |
| confuses-a-reader | 17 | 23, 24, 25, 31, 32, 33, 34, 35, 36, 37, 39, 41, 45, 50, 51, 53, 55, 56 |
| cosmetic | 10 | 38, 40, 42, 43, 44, 46, 47, 54, 57, 58 |

### By verdict

| verdict | count |
|---|---|
| CONFIRMED | 55 |
| CONFIRMED empirically (program run) | 5 of those (2, 3, 8, 9, 10) |
| PARTIALLY REFUTED | 1 (#45's second half unverified by me; #9 mitigation) |
| REFUTED (report claims) | 4 (see REFUTED CLAIMS 1-4) |
| UNVERIFIABLE | 2 (#45 design-note half, #46's "kept deliberately" intent) |

### Where the findings live

| file | count |
|---|---|
| `plugins/agent-kit/scripts/check.py` | 21 |
| `plugins/agent-kit/scripts/orchestrate.py` | 19 |
| `plugins/agent-kit/hooks/guard.py` | 3 |
| `plugins/agent-kit/scripts/runfile.py` | 2 |
| `plugins/agent-kit/hooks/stop.py` | 1 |
| `scripts/validate.sh` | 1 |
| skills' `SKILL.md` and `rules/` | 8 |
| `templates/` | 2 |
| cross-file (no single home) | 5 |

### What would close them, by home (the kit's own four)

| home | count |
|---|---|
| a program | 43 |
| a template | 2 |
| the reviewer | 0 |
| a shared rule | 4 |
| prose deletion | 3 |
| an owner's decision first | 8 |
