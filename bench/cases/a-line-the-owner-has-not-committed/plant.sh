#!/bin/sh
# After the world's first commit, and that is the whole trap: the ledger is
# written by the evening into the owner's checkout and committed by nobody, so
# a line that stands has never been in any commit — and a run's worktree, cut
# from the branch's base, does not hold it.
mkdir -p docs/knowledge
cat > docs/knowledge/debt.md <<'MD'
# Технический долг

Что уже построено и работает не так.

## Работает плохо

- отчёт по периодам считается вручную · `key: 6kwgcv` · `run: last-night`
MD
