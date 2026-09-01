# S9c — what a machine must already have, said before it installs anything

Written after building it, 1 September 2026. First item of the queue in
`2026-09-01-where-this-stands.md`, and the owner's own words are the whole argument for it:
*right now I am debugging one provider by talking to you — that is not the thing.*

`bubblewrap` was learned from a conversation. Everything else a machine was short of arrived as a
refusal **after** the install command had been run, or worse — as a tool that installed cleanly and
then failed at the hour a night needed it.

## 1 · What it is

One table in a provider's declaration:

```toml
[[provider.requires]]
binary = "node"
why    = "codex это сценарий node — без него он не запустится"
```

A word and a line. The word is asked of PATH; the line says why this tool wants it. `agent-kit
setup` prints the list, each entry marked with what was measured about it, **above** the install
command:

```
  1/3  Установить

       Не найден на этой машине.

       Что должно стоять на этой машине до установки:

           ok  npm   им ставится Codex CLI
           no  node  codex это сценарий node — без него он не запустится

       Чего нет — поставьте сначала: без этого команда ниже либо не
       выполнится, либо поставит инструмент, который потом не заработает.

       Откройте второй терминал — это окно ждёт вашего Enter — и
       выполните там:

           npm install -g @openai/codex
```

## 2 · A word, because a word is the only thing that can be measured

The lesson of the four days before this one is in the standing note and it was earned three times
out of three: **a declaration written from documentation is a claim.** A requirement is exactly the
shape of thing that would otherwise be written from documentation and printed at somebody as
though it had been checked — *you will need Node 20, a Google account and a browser* — with no way
for the reader to tell which halves are true of the machine they are sitting at.

So the table takes what PATH can answer and nothing else. A version bound is not measurable by
presence and is not declarable here; an account is not a file. What cannot be asked of PATH stays
in `notes` and in `login_note`, where nobody reads it as measured.

The marks matter for the same reason the table is narrow. A block that named every requirement
alike would be a list the person has to go and check by hand, which is the afternoon this exists
to stop. `ok` and `no` are the words two other screens already use, so a bench judge reading them
is reading the kit's own vocabulary rather than a sentence somebody may reword.

**How to install the requirement is not declared.** `sudo apt install bubblewrap` is right on one
machine and wrong on the next, and the kit does not know which it is standing on. A command it
cannot be held to is the one shape `provider.toml` refuses everywhere else.

## 3 · Two words the table refuses

The provider's own `binary`, and the first word of its `install`. Both are already derived from
what is declared elsewhere — the first is the ladder's first rung, the second is the check that has
held a command the kit will never run since S9a — and a declaration that named either would put one
thing on the screen twice under two spellings of why. `bad-declaration`, at the hour somebody is
reading the file.

The installer is the first line of the printed list, derived. It is the requirement every
declaration would otherwise repeat, and repeating it is exactly how two lists start to disagree.

## 4 · Three readers, one declaration

- **the walk** — the list above the install command, which is the whole point of the mechanism;
- **`doctor`** — one row per requirement this machine has not got, and none for the ones it has: a
  requirement that is met is not *where anything stands*;
- **the ladder's `cure`** — the other place a person arrives at holding a tool that does not work.
  Until this it was the place that said nothing about requirements at all: it sent people to the
  install command with no way of knowing that running it would not help.

One function measures for all three (`setup.reading.wanted`), on the precedent of `free_rungs`:
two screens print it, one file climbs it, and they cannot answer differently.

## 5 · What ships, and what deliberately does not

`codex` and `gemini_cli` require `node`. Measured on the owner's server on 1 September 2026 by
looking at the files rather than at anybody's reference: both are `#!/usr/bin/env node` scripts that
find and spawn what npm put beside them.

`claude_code` requires nothing. The `claude` standing on that same server is a native ELF binary,
so a node requirement written for it would be a claim about a tool nobody here has installed that
way — which is the class of line this whole layer exists against.

**`bubblewrap` is not in codex's table**, and that is the interesting silence. Codex's own sandbox
needs it; this server has none, and every write failed while the tool reported the workspace as
writable. It is absent because this declaration does not use the sandbox —
`--dangerously-bypass-approvals-and-sandbox` is what `full_access` says. The day somebody declares
`-s workspace-write` there, `bwrap` belongs in this table on the same line as the flag. A
requirement of a flag nobody passes is a requirement that would send people to install something
they do not need.

## 6 · The trap, and the round of breaking it

`bench/cases/a-requirement-the-machine-has-not-met`. The case plants an installer in its own bin
and nothing else, then puts the walk to a PATH that is that bin alone — so what the server outside
happens to carry cannot answer for it. Everything it looks for it asks the kit: the install
command, and the words of the requirements. A judge that checks a string it wrote itself is
measuring its own typing.

It fires on three things together: the installer marked as found, the requirement marked as
missing, and the missing one standing **above** the command.

Broken by hand, three times, each against the whole bench of 144:

| what was broken | what the bench said |
|---|---|
| the block moved back under the install command | *did not fire — the missing requirement stands at line 19, under the command at 14* |
| every mark printed `ok` regardless of what was measured | *did not fire — the walk did not say 'node' is missing* |
| the requirement taken out of codex's declaration | *did not fire — codex declares nothing that has to be standing first* |

143 of 144 each time: exactly one case, and it was this one. Disarmed — plant.sh taken away, so the
installer is gone from the case's own bin — it says *the trap was not planted* and stops firing,
which is the fourth thing measured about it.

## 7 · What this does not do

It does not install anything, and it does not check a version. A machine with node 12 on it reads
`ok node` and gets a tool that will not start; what catches that is the `binary` rung, afterwards,
on the re-measurement the walk already does. A version bound would need the requirement to be run
rather than found, and running somebody else's binary to find out whether it is old enough is a
different mechanism with a different cost — not one to invent before a machine has asked for it.
