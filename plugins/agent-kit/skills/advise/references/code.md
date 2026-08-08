# Lens: code

Reference: `stack.md`, the volumes stated in `product.md`, and what this ecosystem treats as the
standard answer. Walks: every action that reads or writes at volume, and every homegrown mechanism.

**Two boundaries, so this lens does not repeat work that is already done.** `audit performance` finds
code that is slow *now*, for a reason visible in the code; this lens finds an approach that will not
survive a volume that does not exist yet. `audit conventions` checks the code against the rules the
owner wrote in `stack.md`; this lens questions those rules. A proposal here never makes a
`conventions` finding wrong — it proposes a different rule to hold the code to, which is the owner's
to accept.

## Close half

Two rules carry it, and both exist to keep the half from becoming a list of fashionable technology.

**A proposal without a number is not a proposal.** Where it is now, as a file and a line; at what
volume or rate it stops holding; and where that number came from — `product.md`, the data already in
the database, the owner. **No number available means an `unjudged` row carrying the question**, not a
guess. That is how this lens comes to ask *how many listings do you expect in a year* instead of
inventing one.

**Always name the intermediate step** — the cheapest thing that buys time — beside the expensive one.
This is what kills the reflex to reach for a search cluster on a table of four hundred rows.

```
seller.search_offers
  сейчас      LIKE по offers.title, Offer.php:88 — индекса нет
  ломается    ~50 000 записей или больше 2 запросов в секунду
  число из    product.md: «до 1000 продавцов», 50 объявлений на каждого
  дешевле     полнотекстовый индекс постгреса — час работы, новой инфраструктуры нет
  дороже      отдельный поисковый движок — сервис, синхронизация, новый режим отказа
  когда       когда первое перестанет держать
```

On a project with no code yet, the walk runs against the approach `stack.md` describes rather than
against a file and a line. The citation changes; the number rule does not.

**Every action in scope gets a row** — a proposal, `clean`, or `unjudged` with the reason.

## Wide half

Three questions, and they are the developer's, not the architect's.

**Проще.** Where something homegrown has a standard answer in this ecosystem; where one idea is
smeared across the code instead of living in one place. The bar: **name the class of work or bugs
that disappears**, never "it would be cleaner". Statuses as strings all over the code become one
enumeration with the transitions in one place, and the class *"nobody handled the new status"* stops
existing. That sentence is the proposal; without it there is only taste.

**Надёжнее.** Where the product loses data or lies quietly. A background job that failed and nobody
heard. A retried payment that creates a second record. An action with no way back. No trace of who
did what. **None of the six audit lenses asks this** — `security` asks who may do a thing, not what
happens when the doing half-succeeds — and owners never ask it either, until it costs them a day of
reconstructing what happened.

**Быстрее — для пользователя и для разработчика**, and the second matters more because nobody
measures it. How long the suite runs. How long the environment takes to come up. How many steps sit
between *understood what to change* and *saw the result*. A feedback loop measured in minutes costs
more over a month than any query on the page.

### Every structural proposal carries a migration path

How to get there in pieces, without stopping the work. **A proposal with no such path is a rewrite,
and is labelled one, plainly.** Writing *move to a different architecture* takes a second and reading
it takes an hour; the label is what lets the owner spend the hour deliberately.

## What research is for here

Current majors of this stack and what they now recommend. The known traps of the chosen approach.
What the ecosystem treats as the standard answer to the homegrown piece. Link and date on every row.

This does not repeat `blueprint`'s research pass: that one ran once, at interview time, before there
was any code to look at.

## What is accepted, and where it goes

The fork is one question, and the closing round of `advise` needs the answer: **does this change a
rule, or follow one?**

A stance — *money in minor units*, *every outbound call idempotent*, *statuses are an enumeration* —
is knowledge, and goes into `stack.md`. Applying that stance in eleven places is work, and goes into
`docs/technical_debt.md`. Most of what this lens produces is the second.
