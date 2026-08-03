# How a command ends

Every command in the kit ends the same two ways, whatever it did.

## Say where it is thin, not what you did

The owner can read the files and the pull request. A summary of the work adds nothing they cannot
see, and it sounds equally confident whether the work under it was thorough or shallow — which is
exactly the thing they are trying to judge.

So end with what only you know: what you could not settle, what you assumed, what you left alone,
and where the result is weaker than it looks. A command that names its own soft spots is one whose
confident parts can be trusted; a clean summary teaches the owner to check everything or nothing.

## Then name the next command

One line, last, with the command already filled in and the reason in a clause:

```
дальше: /agent-kit:audit тесты — 50 записей помечены built, ни одна не проверена
дальше: смержи #42, потом /agent-kit:ship guest.report_post — следующее непостроенное в границах MVP
```

One recommendation, not a menu — a list of options hands the decision back to the owner along with
the work of making it. If the honest next step is that nothing needs doing, say that instead.

Written in the project's language, like everything else the owner reads.
