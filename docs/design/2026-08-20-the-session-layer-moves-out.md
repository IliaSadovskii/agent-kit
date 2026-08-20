# The session layer moves out, 20 August 2026

The kit raises sessions itself: `orchestrate.py` shells out to `tmux`, types into panes with
`send-keys`, and finds a child's transcript by walking `~/.claude/projects`. That works, and every
line of it was written after a specific failure. It is also the one part of the kit that is bound to
one vendor — and the owner wants two things it cannot give: a web dashboard that shows every running
session on the server, and a second provider (Codex first, then whoever follows).

Both wants have the same answer, and it is not a new mechanism inside the kit. It is
[Agent of Empires](https://github.com/agent-of-empires/agent-of-empires) — MIT, Rust, 3.1k stars,
16 agents, tmux underneath, and an HTTP API written for exactly this: *driving a session as a
subagent*. It was installed on the owner's server on 19 August and measured there. This note is the
plan for what happens next.

Everything below marked **measured** was run on that machine; everything else is a decision to check.

## What was measured on 19 August

| Question | Answer |
|---|---|
| Does AoE's API do what `Launcher` does? | Yes. `POST /api/sessions?wait=ready`, `POST /…/send`, `GET /api/sessions`, `DELETE /…` — full cycle run end to end |
| Does it run the agent in tmux? | Yes, session named `aoe_<title>_<first 8 of id>`, one pane |
| Does the transcript stay where the kit looks? | Yes — it launches `claude --session-id <uuid>`, so `~/.claude/projects/<slug>/<uuid>.jsonl` |
| Permissions | The pane came up in bypass mode; `yolo_mode_default` now set, which passes `--dangerously-skip-permissions` |
| Does it touch agent settings? | Yes: it writes 8 hook groups into `~/.claude/settings.json`. Every one begins `[ -n "$AOE_INSTANCE_ID" ] || exit 0`, so it is inert in sessions AoE did not start — the same shape as the kit's own hooks |
| Can it adopt a live session started elsewhere? | **No.** `aoe session import` scans Claude transcripts and creates a *new* session via `claude --resume`. Nothing can adopt a live pane except Anthropic's own client, which registers the session at launch |
| Directory browser | Hard-limited to `$HOME` in the source, no setting. `/projects` is unreachable through it; the project registry is the way past |

Two things the kit needs that AoE does **not** provide, and which therefore stay in the kit:
waiting out an account limit, and handing a run to a fresh session when its context grows past the
ceiling. Both read the transcript, which is still there, so both keep working unchanged.

## The shape

Three layers, each answering one question, with a narrow seam between them.

| Layer | Owns | Repository |
|---|---|---|
| **Method** — what to build, how it is proved | blueprint, ship, epic, audit, the run files | `agent-kit` |
| **Sessions** — raising one, typing into it, knowing its state | AoE | not ours |
| **Machine** — user, docker, ports, network, autostart | `setup-server.sh`, `setup-dev.sh` | `agent-vps` |

The kit already has the seam: `Launcher` looks for `claude-new` on PATH and falls back to plain
tmux, and the comment above it states the whole contract — *a session whose transcript is
discoverable and which can be typed into*. What changes is that the seam gets a third implementation
and stops being Claude-shaped.

`agent-vps` loses its session layer entirely: twelve `claude-*` helpers, eight `vps-*` skills and
the restore timer, about 850 lines. What it keeps — the machine — AoE does not touch at all. It also
stops being a server for Claude Code and becomes a server for agents, which is the point: helpers
named `claude-new` never scaled to `codex-new`.

## Phase 1 — the kit talks to AoE

One file, `plugins/agent-kit/scripts/orchestrate.py`. `Launcher` becomes an interface with three
implementations, chosen in this order:

1. **AoE**, when `aoe` is on PATH and its daemon answers;
2. **the environment's helper** (`claude-new` / `claude-close`), for machines that still have one;
3. **plain tmux**, which needs nothing.

The interface is what `Launcher` already does, plus one method it currently guesses:

```
start(name, prompt, model) -> bool      POST /api/sessions?wait=ready, then POST /send
send(name, text) -> bool                POST /api/sessions/<id>/send
alive(name) -> bool                     GET /api/sessions, status not in (Stopped, Error)
stop(name)                              DELETE /api/sessions/<id>
tmux_name(name) -> str                  from the create response, not computed
```

**`tmux_name` is the one real change.** Today it is `f"cc-{name}"` or `f"agent-kit-{name}"`, a
guess. The stop hook matches a session to its run on that string and on nothing else, so a guess
that is wrong makes the hook guard a session that does not exist. AoE names its session
`aoe_<title>_<id8>`; the kit must record what it was told.

Two smaller notes for the implementation:

- The kit addresses sessions by *name* everywhere; AoE by *id*. The driver keeps the map, and
  `idempotency_key` (AoE accepts one on create) is what makes a retry after a crash return the same
  session instead of a second one.
- `POST /api/sessions` takes `yolo_mode`, `extra_args`, `extra_env` and `base_branch`. Everything
  the kit passes at launch has a field; nothing needs to go through a shell.

Tests go in `tests/test_orchestrate.py`, against a fake HTTP server — the existing tests already
fake tmux, so the shape is there.

**Acceptance is not "a session appeared."** The run to prove Phase 1 is one `ship` on a small
feature, and these are the things that must be observed, because each is a mechanism that would fail
silently:

- [ ] the child session appears in the dashboard sidebar while it works;
- [ ] the run file's `session` field matches the live tmux session name;
- [ ] the stop hook refuses a turn that ends mid-step (kill a step and watch);
- [ ] a handoff fires at the ceiling and the next session picks the run up;
- [ ] the driver's `send` reaches a session that is sitting at a limit (simulate by typing);
- [ ] `stop` removes both the AoE session and its tmux pane;
- [ ] the closing session opens the pull request and the batch reaches `done`;
- [ ] inside an `epic`, the hand-back starts the next batch.

## Phase 2 — `agent-vps` becomes a server for agents

Order matters here: **nothing is deleted from `agent-vps` until Phase 1 is proven**, because a
running `orchestrate.py` looks for `claude-new` on PATH and would be orphaned mid-night.

- **`step_aoe`** in `setup-dev.sh`, beside `step_dozzle` and `step_proxy`: install the binary,
  write `config.toml` (`yolo_mode_default`, `default_tool`), install the systemd user unit, take the
  port from the project's own block. All of this was done by hand on 19 August; the step is that,
  written down.
- **Project visibility.** The dashboard's directory browser cannot leave `$HOME`, and a
  `mount --bind` of `/projects` into the home directory is the wrong fix: it creates two paths to
  one tree, and Claude names a transcript by its working directory — the kit would then fail to find
  the transcript of a session started through the browser. Instead a small timer syncs `/projects/*`
  into AoE's project registry, the same way `ports-web` already syncs services. Result is the same
  ("every project is in the list"), with one path per project.
- **Delete the session layer**: `claude-new`, `claude-close`, `claude-close-all`,
  `claude-close-everything`, `claude-list`, `claude-ssh`, `claude-cleanup`, `claude-registry`,
  `claude-reload`, `claude-name`, `claude-trust`, `claude-restore`, and the eight `vps-*` skills.
  They existed because Anthropic's client has no button for creating a session. AoE has the button.
- **Keep project creation.** `claude-project` clones a repository, makes the directory and claims
  ports. That is not a session concern and AoE has no equivalent; it stays, rewritten to open the
  session through AoE.
- **Reboot survival is the one thing to check before deleting.** `claude-restore` currently brings
  sessions back after a reboot from a registry. AoE has `auto_resume_on_restart = true` and a wake
  message, but "resumes when asked" and "comes back after a reboot" are different claims. One
  experiment settles it: create a session, reboot, look. Until it is settled, `claude-restore`
  stays.

## Phase 3 — build targets, and Codex is the first

There is more than one target: the kit has to build for Claude Code, Codex, Gemini CLI, Grok Build
and OpenCode — and through them for any model on the market. Codex goes first because the machinery
of building is what gets debugged on it.

The kit's prose is portable; what is not portable is the packaging and four flags. Codex mirrors
Claude Code almost item for item:

| Kit today | Codex |
|---|---|
| `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| `skills/*/SKILL.md` | same file, same format — it is a shared standard now |
| `agents/reviewer.md` | custom agents (`multi_agent`, stable) |
| `hooks.json` — PreToolUse, Stop | same events, eleven of them |
| `CLAUDE.md` | `AGENTS.md` |
| `--dangerously-skip-permissions` | `--dangerously-bypass-approvals-and-sandbox` |

Work, in order:

1. **`${CLAUDE_PLUGIN_ROOT}` → `${AGENT_KIT_ROOT}`** — about 90 occurrences across the prose, plus a
   build step that substitutes the right one per target.
2. **A build that emits two packages** from one source: the Claude Code plugin as today, and a
   Codex plugin. Nothing is duplicated by hand; the source of truth stays `plugins/agent-kit/`.
3. **Branch names.** `claude/<slug>` is written into `ship`, `fix` and `sprint`. Under Codex it is a
   lie. Rename to something neutral and migrate the runs in flight.
4. **`guard.py` leaves the hooks and becomes a git `pre-push` hook.** Refusing a merge, a
   force-push and a push to the default branch is checkable without an agent, and a git hook works
   for every provider at once. This is the kit's own rule about where a rule should live — a rule
   that can move into a program stops being held at all.
5. **The driver takes a provider.** In AoE it is one field: `"tool": "claude"` or `"tool": "codex"`.
   That is the whole of provider support for anything AoE already knows, which is sixteen agents.
6. **Limits are the one thing that does not generalise.** The kit reads `"apiErrorStatus":429` out
   of a Claude transcript and parses "resets at 5pm" out of prose. Codex reports rate limits as
   *data* — `account/rateLimits/read` in its app-server protocol, and `token_count` / `turn.completed`
   usage events. So `limit_reset()` and `context_size()` become per-provider, and the Codex versions
   are better than what exists today.

Acceptance for Phase 3 is the same checklist as Phase 1, run once with `"tool": "codex"`.

## Phase 4 — every provider, in three classes

**The kit does not need to support models. It needs to support agents**, and which model is inside
is the agent's business. That is what turns ten providers into four build targets.

| Class | Who | What the kit has to do |
|---|---|---|
| **1.** a model through somebody else's agent | GLM (Z.ai), DeepSeek, Kimi — all speak the Anthropic protocol | **nothing.** `ANTHROPIC_BASE_URL` and a key in `extra_env` at session creation. The client is still Claude Code, so transcripts, limits, the ceiling, the hooks and the reviewer all work unchanged |
| **2.** its own CLI agent | Claude Code, Codex, Gemini CLI, Grok Build, OpenCode, Cline, Qwen Code, Kimi CLI | one build target each: manifest, hook format, the name of the project instruction file, the root variable |
| **3.** any model through a multi-provider agent | OpenCode, Cline | nothing beyond class 2 — one package opens hundreds of models at once |

**Class 1 is checked before anything else**, because it needs no code at all: create a session
through AoE with the right `extra_env` and run one `ship`. For DeepSeek this is the documented path
rather than a trick — `api.deepseek.com/anthropic` exists for Claude Code. It is the cheapest way to
learn the only thing that matters: whether this kit is portable at all.

**Grok Build looks close to free as a target** — xAI open-sourced it in July, and Grok Skills are
stated to be compatible with Claude Code skills, plugins and `CLAUDE.md`.

Inside class 2, a new agent is exactly one table, readable in a minute:

| Field | Claude Code | Codex |
|---|---|---|
| tool name in AoE | `claude` | `codex` |
| full-access flag | `--dangerously-skip-permissions` | `--dangerously-bypass-approvals-and-sandbox` |
| project instruction file | `CLAUDE.md` | `AGENTS.md` |
| package layout | `.claude-plugin/` | `.codex-plugin/` |
| where the transcript lives | `~/.claude/projects/<slug>/<id>.jsonl` | `~/.codex/sessions/` |
| how a limit is read | `apiErrorStatus` + prose | `account/rateLimits` |
| how context size is read | `usage` records | `token_count` events |

Gemini CLI, OpenCode and Cline all have skills, hooks, subagents and a full-access flag, so each is
that table plus a build target. None of them needs a new mechanism.

### Where the universality stops

**Context is no longer the constraint.** GLM-5.2, Kimi K3 and DeepSeek V4 all carry a million-token
window, the same as Opus. The kit's 210k ceiling was never about the window anyway — it is about
cost: every turn re-sends the whole context, a session's price grows with the square of its turns,
and the curve was fitted over 119 Opus sessions. **On another provider it has to be measured
again**, because it follows the price of a token and whether the cache works, not the size of the
window.

**Two questions remain, and both are harder than context.** Prompt caching, which the whole economy
of a run stands on — re-reading the context costs a tenth. And instruction-following: the kit holds
~50k characters of norms and asks an agent to keep its own run file straight over dozens of turns.
A large window and good work inside that window are different properties; in published comparisons
Kimi K2.6 at 256k beats GLM-5.1 at 204k on long-context recall.

**So the bench stops being a deferred item.** With one provider, a change to the kit was checked by
a live overnight run. A kit for every provider, with no way to compare providers against each other,
is a claim nothing can test — and the first bad night on somebody else's model will be
indistinguishable from a bad night. That is item 1 of `docs/planned.md`, and its turn has come.

## What could go wrong, and what to watch

- **ACP mode has no `send`.** A structured-view session answers `acp_mode_unsupported`. The kit's
  sessions must be terminal ones. Worth a check in the driver rather than a surprise at 3am.
- **`auto_stop_idle_secs` must stay 0.** A run waiting out a limit looks idle for hours; auto-stop
  would kill the night. It is off today, and the `step_aoe` config must keep it off.
- **Don't give AoE its own tmux socket.** `[tmux] socket_name` looks tidy, but the kit's own tmux
  calls would then miss every AoE session.
- **Codex hooks need trust.** An unattended run wants `--dangerously-bypass-hook-trust` or managed
  hooks; otherwise the status hooks silently do not run.
- **Two watchers on one session.** AoE has its own idle handling and rate-limit resume (off by
  default, and it stays off). The kit's driver is the only thing allowed to restart a session.
- **`aoe session import` is not what it looks like.** It creates parallel sessions over the same
  transcripts — 200 of them on this machine. Never run it against a live run.

## The one number worth stating

None of this is expected to make a run cheaper or better. The kit's own measurements say the
ceiling, the reviewer and the reading set are where the tokens are; the session layer is
plumbing. What it buys is a dashboard the owner can open from a phone, and a second provider for the
price of one field in a request. That is the whole claim, and it should not grow in the telling.
