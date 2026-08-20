# Sector: provider and session seams

Scope: every place `agent-kit` is bound to **Claude Code** as an agent CLI, and every place it is
bound to the **local machine / session layer** (tmux, systemd, host helper scripts, `~/.claude`).
Swept: `plugins/`, `scripts/`, `tests/`, `.github/`, `migrations/`, and `docs/` only where a design
note is the *only* written statement of a behaviour. `CHANGELOG.md` is excluded except where it is
the only record of a decision (noted inline).

Every hit below was opened and read. Counts are exact.

---

## 1. `${CLAUDE_PLUGIN_ROOT}` and other Claude-Code-provided variables / path conventions

**`${CLAUDE_PLUGIN_ROOT}` — 127 occurrences in 23 files** (excluding `CHANGELOG.md`'s 2 and
`docs/design/2026-08-20-…`'s 1). It is expanded by the Claude Code plugin loader; every one is a
path into the installed plugin.

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` ×2 — **executable**, the only mechanical use | `plugins/agent-kit/hooks/hooks.json:10,21` | `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/guard.py"` and `…/hooks/stop.py` — the hook command lines the harness runs | Both hooks stop loading on any CLI that does not export this variable. `validate.sh:212-228` asserts both are registered; the assertion passes while the variable is unset, so failure is silent at run time |
| `${CLAUDE_PLUGIN_ROOT}` ×17 | `skills/blueprint/SKILL.md:13,34,35,37,53,109,122,141,188,192,201,267,370,469,492,551,554` | prose paths: rules, templates, `check.py` invocations, `verification.yml` | The model reads a literal `${CLAUDE_PLUGIN_ROOT}/…` string and either fails the `Read` or invents a path |
| ×16 | `skills/ship/SKILL.md:18,61,70,73,82,87,105,148,216,267,298,381,400,418,425,450` | same | same |
| ×15 | `skills/epic/SKILL.md:40,41,46,90,95,169,191,210,252,275,283,284,298,314,340` | same; `:275` is the `nohup … orchestrate.py` launch line | the driver cannot be started |
| ×13 | `skills/sprint/SKILL.md:21,22,23,43,46,77,105,142,167,173,235,261,267` | same; `:235` is the `nohup … orchestrate.py` launch line | the driver cannot be started |
| ×9 | `skills/sprint/references/close.md:3,67,114,124,132,178,210,229,270` | rules, templates, `check.py --run` | |
| ×8 | `skills/fix/SKILL.md:41,44,47,55,120,125,137,140` | | |
| ×6 | `skills/next/SKILL.md:24,34,46,53,94,209` | | |
| ×6 | `skills/advise/SKILL.md:34,47,171,179,237,275` | | |
| ×4 | `skills/accept/SKILL.md:30,56,113,122` | | |
| ×4 | `skills/epic/references/finish.md:32,83,96,148` | | |
| ×3 | `skills/audit/SKILL.md:68,179,242` | | |
| ×3 | `rules/pull-requests.md:35,42,193` | `check.py --pr-body`, `--pr-base` | |
| ×3 | `rules/knowledge-writing.md:15,53,80` | templates dir, `check.py --record`, `--status` | |
| ×2 | `rules/preflight.md:19,73` | | |
| ×2 | `skills/sprint/references/frame.md:9,24` | | |
| ×2 — **inside emitted diagnostic text** | `scripts/check.py:2745,2749` | the program *prints* `${CLAUDE_PLUGIN_ROOT}/templates/batch.json` at a session | a Python file emitting a Claude-Code variable name; must move with the rename |
| ×1 | `rules/window.md:79` | | |
| ×1 | `skills/blueprint/references/blocks.md:5` | | |
| ×1 | `templates/manual.md:32` | `check.py --manual` line copied into the project's own `docs/manual.md` — **escapes the plugin into user repositories** | a stale variable name lands in every adopting project's docs |
| ×1 | `templates/where-things-are.md:23` | the block written into a project's `CLAUDE.md` — also escapes into user repos | same |
| ×4 — **the checker for the above** | `scripts/validate.sh:195,197,198,199` | greps `\$\{CLAUDE_PLUGIN_ROOT\}/…` out of the payload and asserts each path exists | the rename must land here too or the check goes blind |

Other Claude-Code-provided variables/conventions:

| what | where | how used | breaks |
|---|---|---|---|
| `$TMUX` (harness-independent, but the session-identity signal) | `hooks/stop.py:59`, `hooks/guard.py:118`, `scripts/check.py:3322` | gate before asking tmux who we are | see §6 |
| `~/.claude/projects/<slug>/*.jsonl` | `scripts/orchestrate.py:241-243`, `scripts/measure.py:49-54`, `skills/ship/SKILL.md:169` | transcript location convention | see §5 |
| `~/.claude/plugins/cache/<plugin>/<version>/…` — the *pinned plugin cache* path | `scripts/check.py:107` (`PINNED_PLUGIN` regex), used at `:2412`; fixtures `tests/test_check.py:1555,1565` | a run-file `prompt` pointing into the versioned plugin cache is reported as a defect | the regex shape (`plugins/…/N.N.N/…`) is Claude Code's cache layout |
| `CLAUDE.md` as the free-context project instruction file | `scripts/check.py:3113,3120,3122,3134` (`where_line`), `templates/where-things-are.md:1,7`, `skills/blueprint/SKILL.md:191`, `tests/test_formats.py:92`, `tests/test_check.py:2110-2129` | `check.py` prints a finding when `CLAUDE.md` is absent or lacks `<!-- agent-kit:where -->`; `blueprint` writes that block | Codex/Gemini use `AGENTS.md`. The kit would report a false finding on every project and write its map into a file nobody loads |
| `/agent-kit:<command>` slash-command namespace — **288 occurrences**, top files: `scripts/check.py` (24), `skills/next/SKILL.md` (15), `tests/test_orchestrate.py` (9), `skills/sprint/SKILL.md` (9), `plugins/agent-kit/README.md` (9), `scripts/validate.sh` (6), `scripts/orchestrate.py` (6), `rules/preflight.md` (6) | see also `scripts/runfile.py:51` `COMMAND_PREFIX = "/agent-kit:"` | it is what the driver **types into a session** (`orchestrate.py:846,1146,1186`) and what `runfile.resume_command` derives | the `plugin:skill` namespacing form is Claude Code's; a different CLI needs a different invocation string, and it is baked into run files on disk |
| `agent-kit:reviewer` — plugin-namespaced subagent | `skills/ship/SKILL.md:423,455`, `skills/fix/SKILL.md:118`, `skills/accept/SKILL.md:97`, `rules/channels.md:15,31`, `templates/run.json:28` | the review pass | subagent addressing scheme is per-CLI |
| `/security-review` — a Claude Code built-in skill | `skills/ship/SKILL.md` (Review step, "On a trigger: `/security-review`") | conditional security pass | does not exist on another CLI |
| `/code-review` — Claude Code built-in, explicitly named as un-invokable by a model | `skills/ship/SKILL.md:446-450`, `rules/pull-requests.md:177,190`, `skills/sprint/references/close.md:177` | offered to the owner as a line to type | the whole paragraph is about a Claude Code feature |
| `/model <alias>` typed into a live session | `scripts/orchestrate.py:183-186`, `templates/run.json:51` | how the driver sets a child's model | see §10 |
| `/plugin marketplace add` / `/plugin install`, `.claude/settings.json` `extraKnownMarketplaces` / `enabledPlugins` | `README.md:17,18,21,28`; `README.ru.md:16,17,20,27` | the documented install path | see §2 |

---

## 2. Claude Code plugin packaging

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `.claude-plugin/marketplace.json` (repo root) | `.claude-plugin/marketplace.json:1-18` | fields: `name`, `owner{name,url}`, `metadata{description,version}`, `plugins[]{name,source,description}` — all Claude-Code marketplace schema | the whole install path |
| `allowCrossMarketplaceDependenciesOn` (schema field, absent but validated for) | `scripts/validate.sh:84-93` | a `plugin.json` `dependencies[]` entry naming another marketplace must be allowlisted here | Claude-Code-only concept |
| `plugins/agent-kit/.claude-plugin/plugin.json` | `plugins/agent-kit/.claude-plugin/plugin.json:1-21` | `$schema: https://json.schemastore.org/claude-code-plugin-manifest.json` (**line 2 — names Claude Code outright**), `name`, `displayName`, `version`, `description`, `author{name,url}`, `homepage`, `repository`, `license`, `keywords[]` (`:17` is the string `code-review`, a keyword not a dependency) | `version` is what pins an install — see `scripts/release.sh:7-8`, which states Claude Code treats a plugin without one as changing every commit |
| version agreement across three files | `scripts/validate.sh:68-82`; `scripts/release.sh:29-47,51` | `VERSION` ↔ `plugin.json.version` ↔ `marketplace.json.metadata.version`; descriptions must be byte-identical | a second build target needs a second manifest and a second bump target |
| `skills/*/SKILL.md` frontmatter — 9 skills | `accept:1-6`, `advise:1-6`, `audit:1-6`, `blueprint:1-6`, `epic:1-6`, `fix:1-6`, `next:1-6`, `ship:1-6`, `sprint:1-6` | fields used: `name`, `description`, `argument-hint`, **`disable-model-invocation: true`** (all nine) | `argument-hint` and `disable-model-invocation` are Claude Code frontmatter. `disable-model-invocation` is load-bearing: it is what stops a model auto-firing a build command. A CLI without it changes the kit's safety posture |
| frontmatter validation | `scripts/validate.sh:96-136` | parses `---`-fenced YAML, asserts `name` == directory, `description` length 40–1024 ("the listing cap"), body ≥400 chars unless "Not written yet." | the 1024 cap is Claude Code's skill-listing limit |
| `agents/reviewer.md` frontmatter | `plugins/agent-kit/agents/reviewer.md:1-5` | `name: reviewer`, `description: …`, **`tools: Read, Grep, Glob, Bash`** | the `tools:` allowlist names Claude Code tool identifiers |
| `hooks/hooks.json` | `plugins/agent-kit/hooks/hooks.json:1-28` | `description`; `hooks.PreToolUse[].matcher: "Bash"`; `hooks[].type: "command"`, `.command`, `.timeout` (10s guard / 30s stop); `hooks.Stop[]` with no matcher | schema, event names, matcher semantics and the timeout field are all Claude Code's |
| hook-registration check | `scripts/validate.sh:217-228` | asserts `PreToolUse` and `Stop` keys exist and every `hooks/*.py` appears in the JSON | hard-codes the two Claude Code event names |
| plugin layout doc | `docs/developing.md:8,16` | `.claude-plugin/plugin.json`, `agents/` "the subagents a command may start" | |
| `skills/*/references/` sub-files | e.g. `skills/audit/references/*.md`, `skills/sprint/references/{frame,close}.md` | read on demand by the model | the *progressive-disclosure* convention is Claude Code skill behaviour; `validate.sh:435-448` enforces every reference file is named in backticks by its SKILL.md |
| `docs/design/2026-08-20-…:140,142,143,144,195` | | records the intended Codex mapping: `.codex-plugin/plugin.json`, custom agents, same `hooks.json` events, `AGENTS.md` | the migration plan already exists in prose |

---

## 3. The hook contract

Two hooks, both `python3` scripts reading JSON on stdin and writing JSON on stdout, always exiting 0.

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| **Event: `PreToolUse`**, matcher `Bash`, timeout 10s | `hooks/hooks.json:4-14`; handler `hooks/guard.py` | refuse `gh pr merge`, force-push, push to default branch, `commands.e2e` inside a registered `ship`, and `git checkout/switch` in a tree a foreign run holds | |
| stdin fields read by the guard | `hooks/guard.py:268` (`json.load(sys.stdin)`), `:273` `tool_name`, `:275` `tool_input.command`, `:279` `cwd` | four fields, no others | `tool_name`/`tool_input`/`cwd` are Claude Code's PreToolUse payload keys |
| stdout protocol of the guard | `hooks/guard.py:290-297` | `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": <why>}, "systemMessage": <…>}` | every key is Claude-Code-specific |
| guard fail-open | `hooks/guard.py:56-68` (import failure), `:298-300` (any exception) | prints `{"systemMessage": …}` and `sys.exit(0)` | |
| **Event: `Stop`**, no matcher, timeout 30s | `hooks/hooks.json:16-26`; handler `hooks/stop.py` | refuse to end a turn while this session's run is mid-step; close a finished `epic`'s hand-back session | |
| stdin fields read by the stop hook | `hooks/stop.py:176`, `:181` `stop_hook_active`, `:184` `cwd` | two fields | `stop_hook_active` is the Claude Code loop-breaker flag |
| stdout protocol of the stop hook | `hooks/stop.py:202-208` | `{"decision": "block", "reason": <text>}` — the *legacy/short* Stop form, not `hookSpecificOutput` | |
| stop-hook fail-open | `hooks/stop.py:41-47`, `:177-178`, `:209-211` | `{"systemMessage": …}` + exit 0 | |
| **exit code 2 is the deny code and is never used** | asserted at `scripts/validate.sh:243-255` | both hooks are run with `scripts/` deleted; the test fails if either exits 2, and fails if either is silent | "2 denies" is Claude Code's convention |
| smoke inputs used in CI | `scripts/validate.sh:231-234` | `{"tool_name":"Bash","tool_input":{"command":"echo hi"},"cwd":"/"}` and `{"hook_event_name":"Stop","cwd":"/"}` | note `hook_event_name` on the Stop input, which `stop.py` never reads |
| test harness for the contract | `tests/test_guard.py:203,209,222,239,245,252` (full stdin/stdout round trips); `tests/test_stop_hook.py` whole file | | |
| planned move | `docs/design/2026-08-20-…:155-158` | `guard.py` is to leave the hook system and become a git `pre-push` hook, provider-independent | the e2e refusal and the tree-holding refusal have **no** git equivalent and are not covered by that plan |

Everything the hooks decide *about* is host state, not harness state — `TMUX`, tmux session name,
run files. So the hook **bodies** port; the **envelope** (event names, payload keys, decision keys,
exit codes, registration file) does not.

---

## 4. Every invocation of the `claude` CLI

Exactly **one** in shipped code.

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `["claude", "--dangerously-skip-permissions", "--remote-control"]` | `plugins/agent-kit/scripts/orchestrate.py:176` | the **fallback** launcher: `tmux new-session -d -s <name> -c <cwd> "<that command>"`, used only when `claude-new` is not on PATH | the binary name, the bypass flag and `--remote-control` are all Claude-Code-specific. Codex's equivalent bypass flag is `--dangerously-bypass-approvals-and-sandbox` (`docs/design/2026-08-20-…:145,193`) |
| `--dangerously-skip-permissions` when the helper *is* present | not passed by the kit — `claude-new` supplies it (`orchestrate.py:172` calls `[helper, name, cwd]` only) | the kit does not control permissions in the helper path | permission posture is delegated to a host script the kit does not own |
| model is **not** a flag | `orchestrate.py:182-186` | deliberately typed as `/model <alias>` into the live session, because `claude-new` takes no model argument | see §10 |
| no `--session-id`, no `--resume`, no `-p` | — | the kit abandoned headless children; `CHANGELOG.md:3497-3498` records that `--session-id` was used before, and `docs/design/sprint.md:35` and `docs/planned.md:468` record the refusal of headless/SDK children | a future daemon (AoE) launches `claude --session-id <uuid>` on the kit's behalf — `docs/design/2026-08-20-…:23` |
| documented prerequisites | `README.md:32-33`, `README.ru.md:32`, `plugins/agent-kit/README.md:237-247` | `git`, `python3`, `gh`, `tmux`; "`claude-new` is used when it happens to be on the PATH" | |

---

## 5. Transcript reading

All transcript reading assumes Claude Code's JSONL transcript format and directory layout.

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| transcript directory | `orchestrate.py:241-243` — `re.sub(r"[^A-Za-z0-9]", "-", str(cwd))` then `Path.home()/".claude"/"projects"/slug` | locates a session's transcript | the cwd→slug mangling is Claude Code's naming rule. **`docs/design/2026-08-20-…:110-115` records that a `mount --bind` of `/projects` would break it**, so two paths to one tree are forbidden |
| same, in the measurement tool | `scripts/measure.py:49-54` — `"-" + project_dir.strip("/").replace("/", "-")`, `os.path.expanduser("~/.claude/projects/{slug}")` | **a second, slightly different implementation of the same rule** | two copies to change |
| picking *this* session's file | `orchestrate.py:246-278` (`newest_transcript`) | `directory.glob("*.jsonl")`; drop files whose `st_mtime < after`; drop files whose first timestamp is `< after - 60`; among the rest prefer one whose first 12 lines contain the run slug; else newest mtime | the "run slug appears in the opening records" trick depends on the harness echoing the typed prompt into the transcript |
| head read | `orchestrate.py:281-287` (`read_head`) | first 12 (or 40) lines | |
| session open time | `orchestrate.py:290-301` (`opened_at`) | regex `"timestamp"\s*:\s*"(\d{4}-\d\d-\d\dT[\d:.]+)Z"`, parsed `%Y-%m-%dT%H:%M:%S` from the first 19 chars, treated as UTC | field name and Z-suffix are format assumptions |
| liveness / last spoke | `orchestrate.py:304-327` (`last_spoke`) | same regex over the last 200 lines of the tail; **max** timestamp; falls back to file mtime when absent | the docstring records a measured 44-min-silent child read as 24 min by mtime alone |
| tail read | `orchestrate.py:330-348` (`read_tail`) | last **400 000 bytes**, then last N lines. Window chosen because the longest observed single record over 186 sessions was 273k chars | a provider with larger records silently blinds every reader below |
| **context size** | `orchestrate.py:351-397` — `USAGE_FIELDS = ("input_tokens","cache_creation_input_tokens","cache_read_input_tokens")`; `record_size` does `json.loads(line)` → `record["message"]["usage"]` → sum of the three; `context_size` takes the **max** over the tail | drives the handoff ceiling | `message.usage.*` is the Anthropic/Claude Code record shape. The docstring records the defect where a regex summed `usage.iterations[]` copies too and **doubled** every reading |
| **opening size (the floor)** | `orchestrate.py:400-421` (`opening_size`) | first usage record in the first 40 lines; 0 → `room` stops applying and `floor-unreadable` is logged once | |
| handoff decision | `orchestrate.py:424-483` (`handoff_due`) | `size > ceiling*1000 and size - floor >= room*1000` | ceiling fitted over 119 **Opus** sessions; `docs/design/2026-08-20-…:206-210` states it must be re-measured per provider |
| **rate limit** | `orchestrate.py:47` `LIMIT_MARKER = '"apiErrorStatus":429'`; `:48` `OVERLOADED_MARKER = '"apiErrorStatus":529'`; `:49` `RESET_RE = r"resets\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am\|pm)?\s*(?:\(([^)]+)\))?"`; classified at `:486-509` (`limit_reset`) | 429 → parse a **prose** reset time (12-hour clock, optional am/pm, optional parenthesised IANA zone via `zoneinfo`), roll to tomorrow if past, sleep until then; 529 → sleep 120s and type `continue` | **The single most provider-specific parse in the kit.** `docs/design/2026-08-20-…:161-165` notes Codex reports limits as data (`account/rateLimits`), so this becomes per-provider |
| consumers of the above | `orchestrate.py:705-791` (the watch loop): `last_spoke`, `read_tail`, `context_size`, `opening_size`, `limit_reset` all called per poll | | |
| cost measurement | `scripts/measure.py:35-36` `PRICE` (Anthropic's four token kinds and their relative prices), `:37` `CONTEXT`, `:57-90` `scan` reads `timestamp`, `gitBranch`, `type in ("user","queue-operation")`, `message.usage`, dedupes on `message.id` | prices a run | `gitBranch` and `queue-operation` are Claude Code record fields |
| subagent transcripts | `scripts/measure.py:93-100` | `<root>/<session-id>/subagents/*.jsonl` | Claude Code's subagent transcript layout |
| the *prohibition* on reading a transcript | `skills/ship/SKILL.md:168-174` ("under `~/.claude/projects/`"), `rules/window.md:25` | prose telling a session never to open its predecessor's transcript | names the Claude path in payload prose |
| design record | `docs/design/sprint.md:156` (`~/.claude/projects/<cwd-slug>/<id>.jsonl`), `docs/design/2026-08-14-what-one-night-measured.md:17` | | |

---

## 6. tmux / session-name conventions

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| **the name guess** | `orchestrate.py:153-154` — `tmux_name(name) = f"cc-{name}" if self.helper else f"agent-kit-{name}"` | every `send`, `alive`, `stop` and the value written into `run.json.session` | The `cc-` prefix is a convention of the *host helper* `claude-new`, guessed rather than reported. `docs/design/2026-08-20-…:72-75` names this the one real change for a daemon |
| tmux subprocess wrapper | `orchestrate.py:147-151` (`_tmux`) | `subprocess.run(["tmux", *args])`, `FileNotFoundError` → return code 127 | |
| `tmux new-session -d -s <tmux_name> -c <cwd> "<claude …>"` | `orchestrate.py:177-178` | the no-helper launch | |
| `tmux send-keys -t <target> -l <text>` then `send-keys -t <target> Enter` | `orchestrate.py:197-201` (`send_to`) | **the only channel into a session** — prompts, `/model`, `continue`, the handoff line, `[driver]` news | |
| `tmux has-session -t <target>` | `orchestrate.py:203-204` (`alive_at`) | liveness | |
| `tmux kill-session -t <tmux_name>` | `orchestrate.py:230` | fallback close | |
| session-name length caps | `orchestrate.py:573-581` (`numbered`: `name[:60]`, `f"{name[:56]}-{segment}"`), `:796` `child.slug[:60]`, `:1020` `f"{parent}-advance"[:60]`, `:1145` `f"{slug}-close"[:60]`, `:1184` `f"{above.slug}-advance"[:60]` | derived names for handoff segments, the closing session and the hand-back session | the 60-char cap and the letters/digits/dashes rule come from `claude-new` (`orchestrate.py:578`) |
| name→run registration | `orchestrate.py:648`, `:681`, `:1195` — `run.set(session=self.launcher.tmux_name(current))` | writes the guessed name into `run.json.session` | this field is the **sole** join key between a session and its run |
| the owner's window, addressed verbatim | `orchestrate.py:195`, `:603-609` (`tell`), `:1024-1025` | reads `run.json.window`, checks `alive_at`, `send_to` | the owner names it themselves; the kit does not derive it |
| `tmux display-message -p '#S'` — **three independent copies** | `hooks/stop.py:59-67` (`my_session`), `hooks/guard.py:110-125` (`my_session`), `scripts/check.py:3315-3325` (`this_session`) | each gates on `os.environ["TMUX"]` first, then asks tmux; `None`/`""` means "not a session the kit registered" | three call sites to change; all three are the identity mechanism |
| consumers of the name | `hooks/stop.py:84-85` (`my_runs`: `state.get("session") == session`), `:189-199`; `hooks/guard.py:133-137` (`building_a_feature`), `:202-210` (`holds_tree`); `check.py:3343,3354` (`print_flight` prints "this session") | five distinct decisions keyed on the string | |
| prose telling a session to record its own name | `skills/sprint/SKILL.md:155` (`tmux display-message -p '#{session_name}'`), `rules/window.md:11`, `skills/epic/SKILL.md:212` | the `window` field | |
| tmux presence checks | `orchestrate.py:1338-1342` (`shutil.which("tmux")` → refuse to start, tell the user to use `/agent-kit:ship`); `skills/sprint/SKILL.md:136` and `skills/epic/SKILL.md:35` both instruct `command -v tmux` before writing anything | | |
| documented dependency | `README.md:33`, `README.ru.md:32`, `plugins/agent-kit/README.md:239` | | |
| test fakes | `tests/test_orchestrate.py:50-51` (`tmux_name` → `f"cc-{name}"`), `:262,277,1266,1310,1330,1368`; `tests/test_stop_hook.py:37,68,76,84,89,101,107,121,129,139,149` (all `cc-…`) | the tests encode the `cc-` prefix | |

---

## 7. Environment-helper dependency (`claude-new` / `claude-close`)

| what | where (file:line) | how it is used | fallback when absent |
|---|---|---|---|
| `shutil.which("claude-new")` | `orchestrate.py:142` | `self.helper` | falls through to `claude --dangerously-skip-permissions --remote-control` under plain `tmux new-session` (`:175-180`) |
| `shutil.which("claude-close")` | `orchestrate.py:143` | `self.closer` | `tmux kill-session` (`:230`) |
| helper launch | `orchestrate.py:171-174` — `subprocess.run([helper, name, str(cwd)])` | two positional args, no model, no permission flag | |
| **exit-0-on-name-taken defect** | `orchestrate.py:156-170` | `claude-new` prints "that name is taken" and exits 0, so the launcher pre-emptively kills a live name, sleeps 1s, and records `self.reclaimed` | recorded in `CHANGELOG.md:2163` and `tests/test_orchestrate.py:1286` |
| helper-without-closer warning, said once | `orchestrate.py:216-222` | prints to stderr that a tmux kill may leave the session registered and a watchdog will restore it | |
| closer refusal is final | `orchestrate.py:223-229` | non-zero from `claude-close` → print and **return**; tmux is never a second opinion | |
| same rule, second copy, in the stop hook | `hooks/stop.py:133-171` (`close_myself`) | `shutil.which("claude-close")`; with the helper it calls it bare (meaning "the session I am in"); without it, `tmux kill-session -t <session>` | the two never both run |
| the fixed 5s / 2s / 1s waits around a helper launch | `orchestrate.py:170,181,186` | "the session has to reach its prompt before it can be typed into" | pure timing assumption about a host CLI reaching its REPL |
| PATH carried into the systemd unit **because of the helper** | `orchestrate.py:1266-1275` — `--setenv=PATH={os.environ['PATH']}` | the first detaching driver lost `~/.local/bin`, `claude-new` vanished, four features went to `blocked` in 20 seconds | `CHANGELOG.md:11`; `tests/test_orchestrate.py:1518-1528` |
| documented as optional | `plugins/agent-kit/README.md:244-247`; design record `docs/design/sprint.md:345`, `docs/design/stop-hook.md:107,111` | | |
| the full helper set to be deleted | `docs/design/2026-08-20-…:116-118` names twelve: `claude-new`, `claude-close`, `claude-close-all`, `claude-close-everything`, `claude-list`, `claude-ssh`, `claude-cleanup`, `claude-registry`, `claude-reload`, `claude-name`, `claude-trust`, `claude-restore` | **only three of the twelve are referenced by this repository** (`claude-new`, `claude-close`, and `claude-registry` in a comment at `hooks/stop.py:144`) | `claude-list` is **not** referenced anywhere in this repo |

**Local-machine seams that are neither Claude nor tmux** (same category of risk):

| what | where | how used |
|---|---|---|
| systemd / cgroup self-detach | `orchestrate.py:1238` `DETACHED = "AGENT_KIT_DRIVER_DETACHED"`; `:1241-1246` reads `/proc/self/cgroup`; `:1249-1251` `dies_with_its_session` tests for `tmux-spawn` + `.scope`; `:1254-1257` `unit_name` → `agent-kit-<slug>`; `:1260-1277` `detach_command` builds `systemd-run --user --collect --quiet --unit=… --setenv=… --working-directory=… <python> <script> <argv>`; `:1280-1293` `detach`; invoked `:1323-1333` | tmux 3.4 puts each pane in a systemd scope with `KillMode=control-group`; `nohup` and `setsid` both fail. Where systemd is absent it says so and carries on |
| `nohup … >> driver.out 2>&1 &` launch lines | `skills/sprint/SKILL.md:235-236`, `skills/epic/SKILL.md:275-276` | typed by a session into a shell |
| `journalctl --user -u <unit>` named in output | `orchestrate.py:1327` | how to read the driver's output |
| the **Claude mobile app** as the notification channel | `orchestrate.py:134,183,634,796,872`; `rules/window.md:37,41,51,74`; `rules/asking.md:12,23`; `skills/sprint/SKILL.md:155`; `templates/run.json:57` | a `[driver]` line typed into the owner's tmux session becomes a phone notification, and a child's session is "visible in the app" for the owner to type into. **This is an undeclared product dependency on Anthropic's client** |

---

## 8. Branch and ref naming

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `BRANCH_PREFIXES = ("claude/", "sprint/", "epic/")` | `plugins/agent-kit/scripts/runfile.py:44` | the one declaration | |
| re-export | `scripts/check.py:145` | `BRANCH_PREFIXES = runfile.BRANCH_PREFIXES` | |
| consumers | `check.py:1670` (`work_branches` skips anything not prefixed), `:1700` (same over `refs/remotes/origin`) | "branches a run would have made" | a Codex run's branches would be invisible to `--state`, `next`, and delivered/undelivered accounting |
| **second, independent hard-coding of two of the three** | `check.py:3511-3513` — `git for-each-ref … refs/heads/epic refs/heads/sprint refs/remotes/origin/epic refs/remotes/origin/sprint` | `--pr-base`: refuses a pull request that drags a whole integration branch | not derived from `BRANCH_PREFIXES`; a rename must touch both |
| `branch_shape(name)` | `runfile.py:208-210` — `^[^/]+/.+` | "a name this kit makes has a slash" | prefix-agnostic, so it survives a rename |
| where the name is **built** (prose) | `skills/ship/SKILL.md:100` (`claude/<slug>` from a freshly pulled default branch), `skills/fix/SKILL.md:52` (`claude/fix-<slug>`), `skills/sprint/SKILL.md:162,194` (`claude/<feature-slug>`, `claude/<batch>-frame`) | the three commands that cut branches | `docs/design/2026-08-20-…:153-154`: "Under Codex it is a lie. Rename to something neutral and migrate the runs in flight" |
| in the assumption-note format | `skills/ship/SKILL.md:287` — `> **[assumed 2026-08-02 · claude/<branch>]**`; asserted by `tests/test_formats.py:62` | the branch name is embedded in a durable knowledge-file annotation | notes already written into user repos carry `claude/` for ever |
| in shipped examples | `templates/run.json:18` `"branch": "claude/developer-create-offer"`; `templates/batch.json:14` `["claude/2026-08-05-…", …]`; `rules/closing.md:17` (Russian example) | | |
| **in the CI template copied into user repos** | `templates/workflow.yml:30` — `branches: ["main", "claude/**", "sprint/**", "epic/**"]` | a GitHub Actions push trigger | a rename silently stops CI firing on every adopting project |
| test fixtures | `tests/test_check.py` ~70 occurrences of `claude/…`; `tests/test_orchestrate.py` ~25; `tests/test_guard.py:30,40,41,52,56,61,71,76,80,83,94,98,113,114,117,126,131,143,147` | | |

---

## 9. Git / `gh` dependency

**`gh` subcommands actually executed — three, all in `check.py`:**

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `gh pr list --state all --limit <PR_LIST_MAX> --json number,state,headRefName,headRefOid` | `check.py:1339-1340` | one call per process; builds number→state and merged-branch→(pr, headRefOid) | `headRefOid` is what makes a squash-merged branch provably delivered (`:1359-1375`) |
| `gh pr view <n> --json state` | `check.py:1390` | one number not on the first page | |
| `gh pr list --state open --json number,title,headRefName,isDraft,mergeable,statusCheckRollup,updatedAt` | `check.py:1405-1407` | `open_requests()`; `statusCheckRollup` conclusions mapped to none/failing/pending/green at `:1416-1425` | the CI-verdict vocabulary (`FAILURE`,`TIMED_OUT`,`CANCELLED`,`ERROR`,`PENDING`,`IN_PROGRESS`,`QUEUED`) is GitHub's |
| availability gate | `check.py:1325-1327` — `shutil.which("gh")`; `Offline(Github)` at `:1432-1437` returns "could not ask" for everything | `--offline` is `argparse.SUPPRESS`ed (`:3607`) and the docstring says every real caller is a test | |
| the `Github` object itself | `check.py:1304-1429`, constructed `:3653` | "everything this program asks GitHub, in one object" — **already an abstraction seam** | |
| `sync_states` — merged PR is the only thing that moves an entry to `built` | `check.py:1440-1470` | `--sync` | |

**`gh` named in payload prose (a model is told to run it):**
`skills/accept/SKILL.md:29` (`gh pr view <n> --json title,body,mergeable,statusCheckRollup`);
`skills/ship/SKILL.md:391` (`gh pr checks`); `skills/sprint/references/close.md:140`
(`gh pr create --base … --head …`), `:181` (`gh pr checks`); `rules/pull-requests.md:187`
(`gh pr create …`); `skills/next/SKILL.md:213` (`gh pr checks`).

**`gh pr merge` as a *pattern to refuse*:** `hooks/guard.py:72` `MERGE = re.compile(r"\bgh\s+pr\s+merge\b")`, used `:249`. Tests: `tests/test_guard.py:34,37,56,140,203,209,222,239,245,252`. `docs/planned.md:232` records that the hook cannot tell an owner's merge from an agent's.

**Git operations assuming a GitHub-shaped remote:**

| what | where (file:line) |
|---|---|
| `git symbolic-ref --quiet refs/remotes/origin/HEAD`, then `origin/main`/`origin/master`/`main`/`master` | `check.py:1655-1661` (`default_branch`) |
| same fallback ladder, second copy | `hooks/guard.py:100-107` (`default_branch`, local names only) |
| `git for-each-ref … refs/heads` (+upstream), `refs/remotes/origin` | `check.py:1667`, `:1697` |
| `git rev-list --left-right --count <base>...<branch>`, `git log -1 --format=%cs` | `check.py:1672,1676` |
| `git merge-base --is-ancestor` | `check.py:1753`, `:2630`, `:3502` |
| `git rev-parse --verify --quiet`, `--abbrev-ref HEAD`, `--git-dir` | `check.py:1659,1764,2480,2482,2568,2619,2629,3489,3494,3517,3518`; `guard.py:105,284` |
| `git cat-file -t` (task commits, `proved_at`) | `check.py:2571,2621` |
| `git show <ref>:<path>`, `git merge-base` | `check.py:2793,2804,2810` |
| `git status --porcelain`, `git rev-list --count`, `git diff --name-only` | `check.py:3206,3505,3506,3521` |
| `git ls-files`, `git grep -n -I --no-color -F` (both with `-c core.quotePath=false`) | `check.py:843`, `:1225` |
| `git ls-remote --heads origin <branch>` — the driver's "was it pushed after all" test | `orchestrate.py:990-993` (`branch_pushed`), called `:823` |
| `git worktree` as the offered escape hatch | `guard.py:36,78,218-221`; `check.py:3363-3364`; `runfile.py:67-103` (`main_worktree` reads `.git` file + `commondir` **without** shelling out, because it is on a hook's hot path) |
| release/CI git | `scripts/release.sh:20,23,51,54,55,57`; `.github/workflows/ci.yml:1-31` (GitHub Actions, `actions/checkout@v4`, `GITHUB_REF` tag check) |

**GitHub Actions assumed as *the* CI:** `check.py:2882-2896` (`workflows()` reads `.github/workflows/*.yml|yaml`), consumed at `:2899-2915` (`outside_a_session`), `:2962`, `:3045`, `:3154-3161` (`outside_line`). `templates/workflow.yml` is a GitHub Actions file whose header (lines 9-13) says "Who reads it: GitHub, on every push… Who may remove it: the owner, on the day the project stops using GitHub". `rules/pull-requests.md:166-167` assumes GitHub renders Mermaid and `<details>/<summary>`; `check.py:3547,3589` counts uncollapsed body length on that assumption.

---

## 10. Model names and model selection

| what | where (file:line) | how it is used | what breaks elsewhere |
|---|---|---|---|
| `--model` (driver flag) | `orchestrate.py:1311-1313`, stored `:139`, defaulted `:184` | the whole run's fallback model | the value is passed through untouched, so the *flag* is portable; its **delivery** is not |
| **delivery is `/model <alias>` typed into the session** | `orchestrate.py:182-186` | `if model and self.send(name, f"/model {model}"): time.sleep(2)` | `/model` is a Claude Code slash command. Rationale at `:182-183`: `claude-new` takes no model argument, and passing `--model` would cost the session its registration and its name in the app |
| per-run model | `orchestrate.py:613-617` (`model_for`), read at `:639`, `:678`, `:1187`; field declared `templates/run.json:51-52` | `run.json.model` — "an alias like `opus` or `sonnet`, or a full name" | the alias vocabulary is Anthropic's |
| **the only model alias in shipped payload** | `skills/sprint/SKILL.md:148` — `"model": "opus"` in the example batch run file | | |
| `templates/run.json:51` names `opus` and `sonnet` | | prose in a template copied by every batch author | |
| Opus named as the sizing basis | `orchestrate.py:443-447` ("Claude Opus 5 carries a 1M token window"), `:477-479` ("A project on a 200k-window model must lower this to about 130k") | justifies the 210k ceiling | the curve was fitted over 119 Opus sessions — `docs/design/2026-08-20-…:206-210` |
| token prices | `scripts/measure.py:35-36` — input 1.0, cache-write 1.25, cache-read 0.1, output 5.0 | the weighting used by every cost figure in the kit | Anthropic's price ratios, hard-coded, no provider dimension |
| no hard-coded model **ids** anywhere | verified by grep for `claude-3`/`claude-4`/`claude-5`/`us.anthropic.*` | only aliases | this is the one thing already portable |
| tests | `tests/test_orchestrate.py:1232,1235` | `model_for` | |

---

## 11. Anything else that breaks if the agent CLI were not Claude Code

| what | where (file:line) | why it breaks |
|---|---|---|
| **Session identity has no provider-independent definition.** The only answer to "which session am I" is a tmux session name compared against a string the driver guessed. | `orchestrate.py:153-154,648` ↔ `stop.py:59-67,84-85` ↔ `guard.py:110-125,133-137,202-210` ↔ `check.py:3315-3325,3343-3355` | any launcher that names sessions itself (AoE names them `aoe_<title>_<id8>`) breaks the join silently — the hook then guards a session that does not exist |
| **A session is driven only by simulated keystrokes.** There is no API. | `orchestrate.py:197-201`, and every caller: prompts `:187`, `/model` `:185`, `continue` `:761,771,782`, the handoff line `:735`, window news `:608-609` | any CLI without an interactive REPL in a pane, or with a structured-only mode, cannot be driven. `docs/design/2026-08-20-…:225-226` records exactly this for AoE's ACP mode (`acp_mode_unsupported`) |
| **The "nudge" recovery assumes the agent ends turns short of finishing.** | `orchestrate.py:774-786` | typing `continue` at a stalled session is a Claude Code behavioural assumption |
| **The stop hook exists because "ending a turn" and "finishing a run" are separate events in this harness.** | `hooks/stop.py:1-24`, `docs/design/stop-hook.md` | a CLI without a Stop hook loses the whole mechanism; a CLI where a turn *is* a run makes it pointless |
| `disable-model-invocation: true` on all nine skills | `skills/*/SKILL.md:5` | without it, a model can auto-fire `epic`/`sprint` — a safety property with no replacement named |
| The reading-set floor (~45.7k) and the handoff economics | `orchestrate.py:400-483` | measured against Claude Code's system prompt + this plugin; a different CLI has a different floor and the `room` guard mis-binds |
| **Two independent implementations of the cwd→transcript-slug rule** | `orchestrate.py:242` vs `measure.py:50` | they differ (`re.sub` on all non-alphanumerics vs `replace("/","-")` with a leading dash); only one is on the run path, so the other can rot unnoticed |
| **Two independent implementations of `default_branch`** | `check.py:1652-1661` (prefers `origin/…`) vs `guard.py:100-107` (local names) | they answer differently; the guard's answer decides a refusal |
| `PROMPT_MAX` / pinned-plugin-cache check | `check.py:107,2412-2417`, `:2407-2411` | the defect it catches — a run file pointing at `~/.claude/plugins/cache/<name>/<version>/…` — is a Claude Code cache path |
| `python3` assumed on PATH and invoked by name in every payload command line | ~40 command lines across `skills/`, `rules/`, `templates/manual.md:32`, `hooks/hooks.json:10,21` | not Claude-specific, but it is a host assumption with no fallback |
| `zoneinfo` optional import | `orchestrate.py:30-33` | reset-time parsing degrades to naive local time where it is missing |
| `/proc/self/cgroup` | `orchestrate.py:1241-1246` | Linux-only; returns `""` on macOS and the detach is skipped with a printed warning |
| `systemd-run --user` | `orchestrate.py:1274,1282` | Linux+systemd only; absence is announced, not fatal |
| The kit's self-description names the vendor | `README.md:5` ("A Claude Code plugin"), `plugin.json:6` and `marketplace.json:8,15` ("long-running Claude Code sessions") | storefront copy, checked byte-identical by `validate.sh:79-82` |

---

## THE SEAM INVENTORY

| seam | blast radius (files/lines touched) | already abstracted? | evidence |
|---|---|---|---|
| **S1 `${CLAUDE_PLUGIN_ROOT}`** | 127 refs / 23 files: 21 payload files + `check.py:2745,2749` + `validate.sh:195-199`. 2 of the 23 (`templates/manual.md:32`, `templates/where-things-are.md:23`) leak into user repositories | **no** — a raw string, expanded by the loader | grep; `docs/design/2026-08-20-…:149-151` plans `${AGENT_KIT_ROOT}` + a per-target build step |
| **S2 plugin packaging** | `.claude-plugin/marketplace.json` (18 lines), `plugins/agent-kit/.claude-plugin/plugin.json` (21), 9 × `SKILL.md` frontmatter (5 lines each), `agents/reviewer.md:1-5`, `hooks/hooks.json` (28), plus `validate.sh:44-154,212-228` and `release.sh:29-51` | **no** — one hard-coded layout, one hard-coded schema URL | `plugin.json:2` names the Claude Code manifest schema |
| **S3 hook contract** | `hooks/hooks.json` (2 event names, 1 matcher, 2 timeouts), `guard.py:268-297`, `stop.py:174-212`, `validate.sh:212-255`, `tests/test_guard.py`, `tests/test_stop_hook.py` | **no** — payload keys inlined at the call sites | the two hooks use *different* output shapes (`hookSpecificOutput` vs `decision`) |
| **S4 `claude` CLI invocation** | 1 line: `orchestrate.py:176` | **partly** — it is the fallback branch of a two-branch launcher | the helper branch (`:171-174`) delegates the binary name and flags entirely to the host |
| **S5 transcript reading** | `orchestrate.py:47-49,241-509` (~270 lines), `measure.py:35-100`, plus prose at `ship/SKILL.md:168-174`, `window.md:25` | **no** — format knowledge is spread across five functions and three module constants | `docs/design/2026-08-20-…:161-165`: `limit_reset()` and `context_size()` must become per-provider |
| **S6 rate-limit / overload detection** (the sharpest sub-seam of S5) | `orchestrate.py:47,48,49,486-509,747-772` | **no** — one JSON substring + one English-prose regex | the reset time is parsed out of a sentence; Codex reports it as data |
| **S7 session naming (`cc-` / `agent-kit-`)** | built `orchestrate.py:153-154`; length caps `:573-581,796,1020,1145,1184`; written `:648,681,1195`; read `stop.py:84`, `guard.py:136,208`, `check.py:3354`; tests `test_orchestrate.py:50`, all of `test_stop_hook.py` | **partly** — one builder, but the value is a *guess* the readers trust | `docs/design/2026-08-20-…:72-75` names it "the one real change" |
| **S8 tmux as the transport** | `orchestrate.py:147-231` (Launcher, ~85 lines), `stop.py:59-67,164-171`, `guard.py:110-125`, `check.py:3315-3325`, prose in `sprint/SKILL.md:136,155`, `epic/SKILL.md:35,212`, `window.md:11`, both READMEs | **partly** — `Launcher` is a class and its docstring (`:132-135`) states the contract: "a session whose transcript is discoverable and which can be typed into" | that docstring is the closest thing to a written interface in the kit |
| **S9 host helpers (`claude-new`/`claude-close`)** | `orchestrate.py:142,143,171-174,216-229,1266-1275`; `stop.py:133-171`; tests `test_orchestrate.py:1342-1368,1518-1528`, `test_stop_hook.py:237-275` | **partly** — `shutil.which` guards every use and there is a working fallback on both sides | `plugins/agent-kit/README.md:244-247` states the kit ships no dependency on any particular machine. `claude-list` is not referenced at all |
| **S10 systemd / cgroup self-detach** | `orchestrate.py:1213-1293,1323-1333` (~85 lines) | **partly** — absence is detected and announced, run continues | `docs/design/2026-08-20-the-driver-died-with-its-session.md` |
| **S11 branch prefix `claude/`** | declared `runfile.py:44`; consumed `check.py:145,1670,1700` and **separately hard-coded** `check.py:3511-3513`; written by prose in `ship:100`, `fix:52`, `sprint:162,194`; embedded in the assumed-note format `ship:287` + `test_formats.py:62`; shipped in `templates/workflow.yml:30`, `templates/run.json:18`, `templates/batch.json:14`; ~95 test fixtures | **partly** — one constant, two consumers bypass it | `docs/design/2026-08-20-…:153-154` |
| **S12 `gh` / GitHub** | 3 `gh` call sites (`check.py:1339,1390,1405`) behind the `Github` class (`:1304-1429`), 6 prose call sites, `MERGE` regex `guard.py:72`, `.github/workflows` reader `check.py:2882-2896` + 4 consumers, `templates/workflow.yml`, `.github/workflows/ci.yml` | **yes, for the API** — `Github`/`Offline` is a real seam with a stated rule ("a question that could not be asked is not an empty answer"). **No** for the prose call sites, the merge regex, or the Actions assumption | `check.py:1304-1317` |
| **S13 model selection** | `orchestrate.py:139,182-186,613-617,1311-1313`; `run.json:51-52`; one alias in `sprint/SKILL.md:148`; prices `measure.py:35-36` | **partly** — the value is opaque; the *delivery* (`/model` keystroke) is not | `orchestrate.py:182-183` explains why the flag was rejected |
| **S14 `CLAUDE.md` as the free-context file** | `check.py:3106-3137`, `templates/where-things-are.md` (48 lines, written into user repos), `blueprint/SKILL.md:191-193`, `test_formats.py:92`, `test_check.py:2110-2129` | **no** — the filename is a literal in four places | `docs/design/2026-08-20-…:144,194` maps it to `AGENTS.md` |
| **S15 the mobile app as the owner's channel** | `orchestrate.py:134,183,594-609,796`; `window.md` (whole file, 114 lines); `asking.md:12,23`; `run.json:57` | **no** — and it is not even named as a dependency | `window.md:41` "visible in the app"; `sprint/SKILL.md:155` "reaches the owner as a notification" |
| **S16 slash-command namespace `/agent-kit:`** | `runfile.py:51-55,170,200-205`; typed by the driver `orchestrate.py:846,1146,1186`; 288 prose occurrences; **persisted into run files on disk** as `prompt` | **partly** — one constant in `runfile.py`, but 288 prose copies | `runfile.py:51` |
| **S17 subagent + built-in-skill addressing** (`agent-kit:reviewer`, `/security-review`, `/code-review`) | `ship:423,446-455`, `fix:118`, `accept:97`, `channels.md:15,31`, `pull-requests.md:177,190`, `close.md:177`, `run.json:28`, `agents/reviewer.md:4` (`tools:` list) | **no** | |

---

## LOAD-BEARING ASSUMPTIONS

Things the kit relies on that are written nowhere as an interface.

1. **A session is a tmux session, and its name is derivable from a slug.** The driver computes
   `cc-<slug>` or `agent-kit-<slug>` and writes it into the run file; three other programs compare
   against that string. Nothing ever asks the launcher what the session is actually called.
2. **A session can be driven by typed text alone**, and text typed into a pane reaches the agent as
   a user turn. There is no other channel — not for the prompt, not for the model, not for
   "continue", not for the handoff instruction, not for news to the owner.
3. **A session, once launched, reaches its prompt within 5 seconds** (`orchestrate.py:181`) and
   accepts a `/model` line 2 seconds later (`:186`).
4. **Every session writes a JSONL transcript, under `~/.claude/projects/<mangled-cwd>/`, one record
   per line, each carrying an ISO `timestamp`**, and assistant records carry
   `message.usage.{input_tokens,cache_creation_input_tokens,cache_read_input_tokens}`.
5. **A rate limit appears in that transcript as the literal `"apiErrorStatus":429`, followed
   somewhere in the same 400KB tail by an English sentence naming the reset hour.** An overload is
   `529`. Nothing else in the kit can detect either.
6. **A rate-limited session stays alive with its context intact**, so one typed word resumes it.
7. **A session's context size is knowable only from outside it** — the session cannot report its
   own size, so the driver measures and the session judges.
8. **Ending a turn and finishing a run are different events**, and the harness offers a hook at the
   first that can refuse it.
9. **A hook can deny a tool call**, is given `tool_name` / `tool_input` / `cwd` on stdin, and treats
   exit code 2 as denial — so exiting 0 with JSON is the safe fail-open.
10. **A plugin's own files are addressable at run time through one variable the harness exports.**
11. **A slash command resolves to whatever version of the kit is installed**, whereas a path
    resolves to a version-pinned cache — this is why every run-file `prompt` must be a command
    (`templates/run.json:87`, enforced `check.py:2412`).
12. **`CLAUDE.md` is loaded into every session in a directory for free**, which is why it is the one
    place the knowledge map is written (`check.py:3113`).
13. **The owner watches through Anthropic's client**: a child session is "visible in the app" and
    typeable into, and a line typed at the owner's session becomes a phone notification.
14. **`skills/*/SKILL.md` frontmatter is honoured** — in particular `disable-model-invocation`,
    which is the only thing preventing a model from auto-starting an overnight run.
15. **A branch made by this kit starts with `claude/`, `sprint/` or `epic/`** — including in a CI
    workflow file copied into every adopting project, and in knowledge-file annotations that outlive
    the run.
16. **The forge is GitHub**: pull requests are `gh pr`, CI is `.github/workflows`, and the pull
    request body will be rendered with Mermaid and `<details>`.
17. **The host is Linux with tmux ≥3.4 under systemd**, so a background driver must move itself into
    its own transient unit or die with the pane that started it.
18. **`python3`, `git`, `tmux` and `gh` are on PATH**, and a systemd transient unit needs PATH
    explicitly copied across or the host helpers vanish.
19. **The cost curve, the 45.7k reading-set floor, the 210k ceiling and the 8-turn re-orientation
    figure are all properties of Claude Opus 5 under Claude Code**, quoted as constants with no
    provider dimension.

---

## NODES

| id | kind | label | description | file:line |
|---|---|---|---|---|
| `file:marketplace` | file | `.claude-plugin/marketplace.json` | Claude Code marketplace manifest; the repo is its own marketplace | `.claude-plugin/marketplace.json:1` |
| `file:plugin-manifest` | file | `plugin.json` | Claude Code plugin manifest; `$schema` names Claude Code | `plugins/agent-kit/.claude-plugin/plugin.json:1-21` |
| `file:hooks-json` | file | `hooks/hooks.json` | registers both hooks with `${CLAUDE_PLUGIN_ROOT}` command lines | `plugins/agent-kit/hooks/hooks.json:1-28` |
| `hook:guard` | hook | PreToolUse(Bash) guard | five refusals; fails open, loudly | `plugins/agent-kit/hooks/guard.py:1-305` |
| `hook:stop` | hook | Stop hook | blocks a mid-step turn; closes a finished epic's session | `plugins/agent-kit/hooks/stop.py:1-216` |
| `script:orchestrate` | script | the driver | the whole session layer lives here | `plugins/agent-kit/scripts/orchestrate.py:1-1362` |
| `script:launcher` | script | `Launcher` | helper-or-tmux session creation; the stated seam | `plugins/agent-kit/scripts/orchestrate.py:138-231` |
| `script:transcript` | script | transcript readers | `transcript_dir`, `newest_transcript`, `read_head/tail`, `opened_at`, `last_spoke`, `record_size`, `context_size`, `opening_size`, `limit_reset` | `plugins/agent-kit/scripts/orchestrate.py:241-509` |
| `script:detach` | script | systemd self-detach | `own_cgroup`, `dies_with_its_session`, `unit_name`, `detach_command`, `detach` | `plugins/agent-kit/scripts/orchestrate.py:1238-1293` |
| `script:check` | script | `check.py` | 3901 lines; owns `Github`, git reads, `CLAUDE.md` check, `this_session`, `print_flight` | `plugins/agent-kit/scripts/check.py:1-3901` |
| `script:github` | script | `Github` / `Offline` | the only forge abstraction in the kit | `plugins/agent-kit/scripts/check.py:1304-1437` |
| `script:runfile` | script | `runfile.py` | what a run is: `TERMINAL`, `STEPS`, `BRANCH_PREFIXES`, `KINDS`, `COMMAND_PREFIX`, `main_worktree`, `in_flight`, `kind`, `resume_command` | `plugins/agent-kit/scripts/runfile.py:1-210` |
| `script:measure` | script | `measure.py` | dev-only cost tool; second copy of the transcript-path rule and the price table | `scripts/measure.py:1-275` |
| `script:validate` | script | `validate.sh` | enforces manifests, frontmatter, hook registration, `${CLAUDE_PLUGIN_ROOT}` resolution | `scripts/validate.sh:1-569` |
| `script:release` | script | `release.sh` | bumps the three version markers, tags | `scripts/release.sh:1-59` |
| `file:ci` | file | `.github/workflows/ci.yml` | GitHub Actions; runs `validate.sh`, checks tag == VERSION | `.github/workflows/ci.yml:1-31` |
| `file:workflow-template` | file | `templates/workflow.yml` | GitHub Actions template copied into user repos; hard-codes `claude/**` | `plugins/agent-kit/templates/workflow.yml:30` |
| `file:where-things-are` | file | `templates/where-things-are.md` | the block written into a project's `CLAUDE.md`; carries `${CLAUDE_PLUGIN_ROOT}` | `plugins/agent-kit/templates/where-things-are.md:23,27` |
| `file:run-json` | file | `templates/run.json` | declares `session`, `window`, `model`, `prompt`, `branch` | `plugins/agent-kit/templates/run.json:18,22,51,54,87` |
| `file:runfile-state` | file | `.agent-kit/runs/<slug>/run.json` | the live join between a session and its run | `plugins/agent-kit/scripts/runfile.py:27` |
| `cmd:sprint` | cmd | `/agent-kit:sprint` | composes a batch, checks tmux, launches the driver, becomes the window | `plugins/agent-kit/skills/sprint/SKILL.md:136,148,155,235` |
| `cmd:epic` | cmd | `/agent-kit:epic` | checks tmux, launches the driver, becomes the window | `plugins/agent-kit/skills/epic/SKILL.md:35,212,275` |
| `cmd:ship` | cmd | `/agent-kit:ship` | cuts `claude/<slug>`; forbidden to read `~/.claude/projects/` | `plugins/agent-kit/skills/ship/SKILL.md:100,169` |
| `cmd:fix` | cmd | `/agent-kit:fix` | cuts `claude/fix-<slug>` | `plugins/agent-kit/skills/fix/SKILL.md:52` |
| `cmd:accept` | cmd | `/agent-kit:accept` | runs `gh pr view` | `plugins/agent-kit/skills/accept/SKILL.md:29` |
| `cmd:next` | cmd | `/agent-kit:next` | ranks open PRs and CI; forbidden `--offline` | `plugins/agent-kit/skills/next/SKILL.md:107,213` |
| `session:window` | session | the control window | the owner's own tmux session, named in `run.json.window` | `plugins/agent-kit/rules/window.md:1-114` |
| `session:child` | session | a feature child | one `claude` session per feature, named `cc-<slug>` | `plugins/agent-kit/scripts/orchestrate.py:636-648` |
| `session:close` | session | the closing session | `<batch>-close`, never asked to hand over | `plugins/agent-kit/scripts/orchestrate.py:1143-1148` |
| `session:advance` | session | the hand-back session | `<epic>-advance`; the one session only the stop hook can close | `plugins/agent-kit/scripts/orchestrate.py:1184-1195` |
| `ext:claude-cli` | ext | the `claude` binary | launched only in the no-helper path | `plugins/agent-kit/scripts/orchestrate.py:176` |
| `ext:claude-new` | ext | host helper | registers and names a session for the app | `plugins/agent-kit/scripts/orchestrate.py:142,172` |
| `ext:claude-close` | ext | host helper | unregisters then kills | `plugins/agent-kit/scripts/orchestrate.py:143,224`; `plugins/agent-kit/hooks/stop.py:148,151` |
| `ext:tmux` | ext | tmux | session creation, keystrokes, liveness, identity, kill | `plugins/agent-kit/scripts/orchestrate.py:149` |
| `ext:transcripts` | ext | `~/.claude/projects/**/*.jsonl` | liveness, context size, limits, session identity | `plugins/agent-kit/scripts/orchestrate.py:243` |
| `ext:systemd` | ext | `systemd-run --user` | keeps the driver alive past its pane | `plugins/agent-kit/scripts/orchestrate.py:1282` |
| `ext:gh` | ext | GitHub CLI | 3 subcommands executed, 6 more typed by sessions | `plugins/agent-kit/scripts/check.py:1327` |
| `ext:git` | ext | git | ~35 read-only call sites plus the guard's refusals | `plugins/agent-kit/scripts/check.py:1647` |
| `ext:github-actions` | ext | `.github/workflows` | the only CI the kit can see | `plugins/agent-kit/scripts/check.py:2884` |
| `ext:mobile-app` | ext | Anthropic's client | how the owner sees sessions and receives news | `plugins/agent-kit/rules/window.md:41,51` |
| `ext:aoe` | ext | Agent of Empires | the planned replacement for the session layer | `docs/design/2026-08-20-the-session-layer-moves-out.md:53-99` |

## EDGES

| from -> to | mechanism | condition | file:line |
|---|---|---|---|
| `cmd:sprint -> script:orchestrate` | `nohup python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py" <dir> >> driver.out 2>&1 &` | after the run files are written and `command -v tmux` succeeded | `plugins/agent-kit/skills/sprint/SKILL.md:235-236`, `:136` |
| `cmd:epic -> script:orchestrate` | same launch line | at the end of the gate | `plugins/agent-kit/skills/epic/SKILL.md:275-276` |
| `script:orchestrate -> ext:systemd` | `systemd-run --user --collect --unit=agent-kit-<slug> --setenv=PATH=… <python> <self> <argv>` | `$AGENT_KIT_DRIVER_DETACHED != 1` and `/proc/self/cgroup` contains `tmux-spawn…scope` | `plugins/agent-kit/scripts/orchestrate.py:1323-1333,1260-1277` |
| `script:orchestrate -> ext:tmux` | `shutil.which("tmux")`, else refuse | always, before anything | `plugins/agent-kit/scripts/orchestrate.py:1338-1342` |
| `script:launcher -> ext:claude-new` | `subprocess.run([helper, name, cwd])` | `shutil.which("claude-new")` | `plugins/agent-kit/scripts/orchestrate.py:171-174` |
| `script:launcher -> ext:claude-cli` | `tmux new-session -d -s <tmux_name> -c <cwd> "claude --dangerously-skip-permissions --remote-control"` | no `claude-new` on PATH | `plugins/agent-kit/scripts/orchestrate.py:175-180` |
| `script:launcher -> session:child` | `tmux send-keys -t <name> -l "/model <alias>"` then `-l "<prompt>"` + Enter | after a 5s wait; `/model` only when a model is named | `plugins/agent-kit/scripts/orchestrate.py:182-201` |
| `script:launcher -> ext:claude-close` | `subprocess.run([closer, name])`; tmux is not a second opinion | `shutil.which("claude-close")` | `plugins/agent-kit/scripts/orchestrate.py:223-229` |
| `script:launcher -> ext:tmux` | `tmux kill-session -t cc-<name>` | no closer on PATH | `plugins/agent-kit/scripts/orchestrate.py:230` |
| `script:orchestrate -> file:runfile-state` | `run.set(session=launcher.tmux_name(current))` | on every session start and every handoff | `plugins/agent-kit/scripts/orchestrate.py:648,681,1195` |
| `script:orchestrate -> ext:transcripts` | glob `~/.claude/projects/<slug>/*.jsonl`, filter by mtime and first timestamp, prefer one whose head contains the run slug | every poll until one is found; give up after 300s | `plugins/agent-kit/scripts/orchestrate.py:246-278,698-703` |
| `script:transcript -> session:child` | `send(current, HANDOFF_LINE)` | `size > ceiling*1000 and size - floor >= room*1000`, session healthy, `hand_over` true | `plugins/agent-kit/scripts/orchestrate.py:733-743,424-483` |
| `script:transcript -> script:orchestrate` | `limit_reset(tail)` → `("limit", when)` | tail contains `"apiErrorStatus":429` | `plugins/agent-kit/scripts/orchestrate.py:486-506,747-766` |
| `script:orchestrate -> session:child` | `send(current, "continue")` | after a limit reset, on 529, or as the one nudge before a restart | `plugins/agent-kit/scripts/orchestrate.py:761,771,782` |
| `script:orchestrate -> session:window` | `send_to(window, "[driver] …")`, preceded once by `WINDOW_RULE` | `run.json.window` is set and `tmux has-session` succeeds | `plugins/agent-kit/scripts/orchestrate.py:594-609,589-592` |
| `session:window -> script:orchestrate` | a line written into `<batch>/control`, read and deleted at a feature boundary | words `skip <slug>` or `stop`; anything else is logged as unrecognised | `plugins/agent-kit/rules/window.md:89-111`; `plugins/agent-kit/scripts/orchestrate.py:546-553,1054-1068` |
| `script:orchestrate -> session:close` | `send` `/agent-kit:sprint --close <dir>`, `hand_over=False` | all children terminal | `plugins/agent-kit/scripts/orchestrate.py:1143-1148` |
| `script:orchestrate -> session:advance` | `start(f"{epic}-advance", "/agent-kit:epic --advance <dir>", model)` then `above.set(session=…)` | the batch's `parent` is an `epic` (or legacy `mvp`) | `plugins/agent-kit/scripts/orchestrate.py:1167-1200` |
| `script:orchestrate -> session:advance` | `launcher.stop(f"{parent}-advance"[:60])` | at the top of the next driver's `go()` | `plugins/agent-kit/scripts/orchestrate.py:1018-1020` |
| `hook:stop -> session:advance` | `close_myself()` — `claude-close` bare, else `tmux kill-session -t <session>` | this session's `epic` run is terminal **and** its `run.json` was written within `STALE_AFTER` (24h) | `plugins/agent-kit/hooks/stop.py:108-171,192-198` |
| `hook:stop -> session:child` | stdout `{"decision":"block","reason":…}` | `run.json.session == tmux #S`, `step` non-terminal, kind ≠ epic, `handoff` empty, `stop_hook_active` false | `plugins/agent-kit/hooks/stop.py:88-105,181,201-208` |
| `hook:guard -> ext:git` | stdout `{"hookSpecificOutput":{"permissionDecision":"deny",…}}` | a run is in flight (`runfile.in_flight`) **and** the command matches `MERGE`/`FORCE`/`PUSH`-to-default/`SWITCH`-while-held/declared-e2e-while-building | `plugins/agent-kit/hooks/guard.py:213-263,280-297` |
| `hook:guard -> file:runfile-state` | `runfile.in_flight(main_worktree(root))` | every Bash call in every session | `plugins/agent-kit/hooks/guard.py:81-89`; `plugins/agent-kit/scripts/runfile.py:116-140,67-103` |
| `script:check -> ext:gh` | `gh pr list --state all --json number,state,headRefName,headRefOid` | `shutil.which("gh")`, once per process | `plugins/agent-kit/scripts/check.py:1338-1340` |
| `script:check -> ext:gh` | `gh pr view <n> --json state` | the number is not on the first page | `plugins/agent-kit/scripts/check.py:1388-1396` |
| `script:check -> ext:gh` | `gh pr list --state open --json …statusCheckRollup…` | `--state` / `next` | `plugins/agent-kit/scripts/check.py:1403-1429` |
| `script:check -> ext:github-actions` | reads `.github/workflows/*.yml|yaml`, tests whether any fires on push | `--tests`, `--status`, `--state` | `plugins/agent-kit/scripts/check.py:2882-2915,3154-3161` |
| `script:check -> ext:tmux` | `tmux display-message -p '#S'` | `$TMUX` set | `plugins/agent-kit/scripts/check.py:3322-3325` |
| `script:check -> file:where-things-are` | prints a finding naming `/agent-kit:blueprint` | `CLAUDE.md` absent, or present without `<!-- agent-kit:where -->` | `plugins/agent-kit/scripts/check.py:3109-3137` |
| `script:orchestrate -> ext:git` | `git ls-remote --heads origin <branch>` | a child ended non-terminal but names a branch | `plugins/agent-kit/scripts/orchestrate.py:823,990-993` |
| `script:validate -> file:hooks-json` | asserts `PreToolUse` and `Stop` exist and every `hooks/*.py` is wired | every CI run and every release | `scripts/validate.sh:217-228` |
| `script:validate -> hook:guard` / `hook:stop` | feeds each a synthetic stdin payload, twice (normal, and with `scripts/` deleted); asserts exit ≠ 2 and a `systemMessage` on failure | | `scripts/validate.sh:231-255` |
| `script:validate -> file:plugin-manifest` | version/name/description agreement; cross-marketplace dependency allowlist | | `scripts/validate.sh:58-93` |
| `script:validate -> S1` | greps `${CLAUDE_PLUGIN_ROOT}/…` out of the payload; every path must exist | | `scripts/validate.sh:195-199` |
| `script:release -> file:plugin-manifest` | rewrites `version` in `plugin.json` and `metadata.version` in `marketplace.json`, then runs `validate.sh`, commits, tags | `scripts/release.sh <semver>` | `scripts/release.sh:29-57` |
| `file:ci -> script:validate` | `bash scripts/validate.sh` on ubuntu-latest | push to main, tags `v*`, any PR | `.github/workflows/ci.yml:20-21` |
| `script:measure -> ext:transcripts` | `~/.claude/projects/<slug>/*.jsonl` plus `<session>/subagents/*.jsonl` | dev tool only, never ships | `scripts/measure.py:49-54,93-100` |

---

## UNCERTAIN

1. **Whether `--remote-control` (`orchestrate.py:176`) is still a supported Claude Code flag.** It
   appears once, in the fallback path, with no test covering it (`tests/test_orchestrate.py:1` says
   the suite runs "with no tmux, no claude and no network"). The only other mention is
   `docs/design/ship.md:104`. On this machine the helper path is the one taken, so this line may
   never have run in anger.
2. **Which Stop-hook output shape is current.** `stop.py:202-208` emits the flat
   `{"decision":"block","reason":…}` while `guard.py:290-297` emits the newer
   `hookSpecificOutput` envelope. I could not determine from the repository whether the flat form is
   still honoured or merely still tolerated.
3. **Whether `--offline` has any live caller.** `check.py:3607` suppresses it from help and the
   `Github` docstring (`:1314-1316`) says every real caller is a test, but `skills/next/SKILL.md:107`
   explicitly forbids it — implying somebody could pass it. Nothing in the payload does.
4. **The exact contract of `claude-new`/`claude-close`.** Neither script is in this repository; the
   kit's knowledge of them is entirely in comments (`orchestrate.py:132-135,156-165,206-215`,
   `stop.py:133-146`). Whether `claude-new` accepts more than `(name, cwd)`, and what its exit codes
   mean beyond "0 does not imply success", is not determinable from here.
5. **Whether the `claude/` prefix appears in any *committed* project artefact besides
   `templates/workflow.yml:30` and the `[assumed … · claude/<branch>]` note format.** Those two are
   the ones I confirmed escape into user repositories; a full sweep of what `blueprint` and the
   closing session write was outside this sector.
6. **Whether the kit's `--pr-base` epic/sprint scan (`check.py:3511-3513`) was ever meant to include
   `claude/`.** It names only two of the three prefixes and does not read `BRANCH_PREFIXES`; I could
   not tell from the docstring whether the omission is deliberate (a feature branch legitimately
   carries another feature branch in a chain) or an oversight.

---

## A PLANNED DEPENDENCY, NOT YET BUILT

`docs/planned.md:44-63` proposes that the kit's evaluation bench be built on **`claude plugin eval`**
— a Claude Code CLI subcommand — with its `--ablation with-without`, `--runs`, `--threshold`,
`--max-cost-usd`, `--json`, `--report`, `--scaffold` and `--allow-tools` flags, reading
`evals/**/case.yaml` and graders from `graders/*.md`. None of it exists in the repository today
(no `evals/`, no `graders/`, no reference outside `planned.md`), but it is item 1 of that file and
`docs/design/2026-08-20-…:218-221` declares its turn has come. Built as proposed, it would add a
**new and deep** Claude Code binding — to the kit's own CI — at the exact moment the rest of the kit
is being unbound from that vendor. Worth flagging before the migration, not after.
