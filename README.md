# agent-kit

A console application that drives other people's CLI agents — Claude Code, Codex, Gemini CLI,
OpenCode — through a method that is a program rather than prose.

This branch is the third version, built from a bare tree. The plan, the measurement it rests on
and the build order are in [`docs/design/2026-08-22-the-third-kit.md`](docs/design/2026-08-22-the-third-kit.md).

## Where it stands

| Step | What it is | State |
|---|---|---|
| S0 | the package: the command, the paths, the config, the exit codes | done |
| S1 | the state: what a run is, and the one door that advances it | done |
| S2 | the step contract: composed input, executor, validated output | done |
| S3 | the first adapter, Claude Code, measured at level B | done |
| S4 | one feature end to end: design, build, verify, deliver | next |
| S5 … S11 | the bench, the knowledge, the daemon, parallelism, more adapters | planned |

## Running it

```bash
make up             # the workshop: a container with uv and the kit installed into it
make test           # the suite
make install-check  # `uv tool install` puts a working `agent-kit` on PATH
```

## What works today

```bash
agent-kit doctor                  # the paths, the config, what is missing
agent-kit config show             # the effective configuration
agent-kit run new add-login       # a run on branch kit/add-login
agent-kit run start add-login     # begin the next step
agent-kit run pass add-login      # it satisfied its contract
agent-kit run show add-login      # where it stands

agent-kit provider list           # the providers the kit ships, read from the folder
agent-kit provider check claude_code   # the level it earns, measured rather than claimed
agent-kit step list               # the steps the kit knows
agent-kit step show probe         # its prose and what it must return
agent-kit step input add-login    # exactly what the driver would enclose
agent-kit step run add-login --provider claude_code --option model=sonnet
```

Claude Code is driven headless — one composed input on stdin, one JSON answer back — and measures
at level B: the driver can say how much context a session holds, what it cost, and where its
transcript landed. The fake provider is still there for tests and for anything that has no CLI:
`--provider fake --option reply=answer.md`.

The arguments: [S2, the step contract](docs/design/2026-08-22-s2-the-step-contract.md),
[S3, the first adapter](docs/design/2026-08-22-s3-the-first-adapter.md), and
[what three reviews changed](docs/design/2026-08-22-what-the-plan-review-changed.md).
