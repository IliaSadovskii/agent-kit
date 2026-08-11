# Lens: performance

Reference: the anti-patterns of this stack. Walks: every action, against every pattern.

Not "will it hold ten thousand requests" — that needs numbers no project has written down. This
lens finds the code that is slow for a reason anyone would recognise, early, while it is cheap to
change.

**Write the catalogue into the report before using it.** Derive it from `stack.md` and the
framework's own documented pitfalls — a query per row of a loop, a select with no bound, IO inside a
loop, a missing index under a query the code actually makes, work done synchronously that the stack
would queue, a whole table pulled into memory, a hot read with no cache. The kit does not ship a
catalogue: what is an anti-pattern in one stack is the idiom of another, and a list baked in here
would be an opinion about somebody else's project. Writing it down is also what makes the scope of
the check visible — a finding-free report against three patterns is a different thing from one
against nine.

**The query is not where the cost is.** An action can build a perfectly bounded query and the extra
round trips happen in the template it feeds, in a serializer, in an accessor touched during
rendering. So each action carries **two citations: where the data is fetched, and where it is
consumed** — and the verdict is about the pair. Eager loading that covers what the action uses and
misses what the view uses is the normal shape of this defect, not an unusual one.

A method named `withRelations` is not evidence that the relations the view touches are loaded. Read
it, and read what the view touches.

**Name every consumer, not the first one.** An action's data can reach a list, a detail page, a
notification and an export; reading one template and citing it leaves a row that looks checked while
two consumers were never opened. Where you cannot enumerate them, say so — an honest `unjudged` is
worth more than a clean row nobody can trust.

**Every action in scope gets a row** — `covered` where nothing is wrong, `gaps` where something is,
or `unjudged` with the reason. A report that lists only the problems cannot be told apart from one
that stopped looking. Walk them all, past the first finding, and count them in the file's own line
of counters — the catalogue above says what was checked, the counters say against how much.

```
guest.browse_feed
  fetched at    Feed.php:206 — with(['author','tags']), paginate(20)
  consumed at   post-card.blade.php:21 $post->origins->…  — not eager loaded
  pattern       a query per row of a loop
  cost          20 extra queries per page, one per card
  clean for     author, tags
```

**Profiler output is an input, not a verdict.** If the project runs a query counter, a debug bar or
a tracer, quote what it reported and say which path produced it; a number with no path behind it
explains nothing and cannot be rechecked. The kit adds no tooling and runs no benchmark — measuring
is somebody's work, and this lens is reading.
