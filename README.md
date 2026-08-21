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
| S2 | the step contract | next |
| S3 … S11 | adapters, the bench, the knowledge, the daemon, parallelism | planned |

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
```

The steps have no executors yet — that is S2, and it is what makes the state worth advancing.
