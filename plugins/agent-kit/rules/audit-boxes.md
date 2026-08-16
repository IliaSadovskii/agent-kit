# Ticking a box in an audit's work list

`docs/audits/<lens>.md` belongs to the lens that wrote it, which rewrites it whole on its next run.
Between those two runs the only thing anyone may change in it is a box, and **three sessions may
change one**: the session that closes a batch, `next`, and `accept`. Each ticks only what it has
itself verified is done, and nothing else ticks a box at all.

It is one file rather than a paragraph in each of the three because it was a paragraph in each of the
three, in three different sets of words — one of them said the commit rule, one said the form, none
said both.

## What a tick has to rest on

One of two facts, read rather than inferred:

- **the item's own work is in a merged pull request** — that number is what goes in the line; or
- **the entry it names is `built`, and the change is in that pull request's diff.** An entry moving
  to `built` says a feature shipped, not that this item's work was part of it.

**Never a guess, and the two mistakes are not symmetrical.** An item left open costs the next reader
ten seconds. A box ticked on a guess takes the work off every future list: the lens rewrites this
file only on its own next run, which may be months out, and until then `next` ranks it as finished
and `sprint` composes its batches from what is left unticked. Nobody looks for it again.

An item you cannot settle in the minute it deserves is left alone and said in your report.

## The form

```
- [x] закрыто PR #<n>
```

The sentence is in the project's language, like everything else in that file; the box and the number
are not. A refusal is not this kind of tick — no pull request will ever close one — and it belongs to
the lens, which writes it as `` - [x] `declined`: … ``.

## The commit

**Its own `docs(audits): …` commit, with nothing else in it.** A tick is bookkeeping catching up with
work that already happened, and a bookkeeping line inside a commit of work is one nobody can find
afterwards or revert on its own.

**Untouched items stay untouched.** Not a line rewritten, not an item reordered, not one dropped
because it reads stale — all of that is the lens's on its next run, and a work list edited by its
readers is one that no longer says what any lens found.
