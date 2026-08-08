# Lens: money

**The question: what does this cost to run, and what could it earn?** What is given away that costs
per use. Which limits exist in the plan and nowhere in the code. Which bill will dominate at the
volumes ahead. And what people would pay for that there is currently no way to pay for.

Reference: how the product earns and what it costs to run. Walks: every action and integration that
costs money to serve, and then the market.

**On most projects the knowledge records neither**, and that is this lens's first act rather than a
reason to skip it. Say plainly that `product.md` names no revenue model and no running costs, put the
questions to the owner, and run the half that does not need them. A lens that quietly invents a price
list is worse than one that says what it could not read.

## Close half

What is given away that costs per use — an outbound call, storage, a paid API sitting behind a free
path. Where a limit the plan already states is not enforced anywhere in the code. Which action calls
a metered integration without a bound. What the audience clearly values and there is no way to pay
for.

**Same rule as `code`, one word different: a proposal without an amount or a rate is not a
proposal.** *Move to cheaper hosting* says nothing; *the bill is ~$180 a month, ~$120 of it the free
preview path* is something the owner can act on in a minute. No amount available is an `unjudged`
row carrying the question.

```
guest.preview_report
  стоит          один вызов платного PDF-сервиса, ~$0.004, без кэша и без лимита
  доступно       анонимным посетителям, Report.php:64
  сейчас         ничто не ограничивает; в тарифе 20 в месяц, в коде эти 20 нигде нет
  предложение    включить лимит тарифа, кэшировать по хешу документа
  сколько это    при 1000 предпросмотрах в день один бесплатный путь — около $120 в месяц
```

**Every action that touches money gets a row** — a proposal, `clean`, or `unjudged` with the reason.
Both directions count: what leaks out, and what could come in and does not.

## Wide half

- **How products in this space charge**, and what this audience is already used to paying for.
- **The cheapest thing here somebody would pay for today** — usually not the hardest feature to
  build.
- **Which running cost will dominate** at the volumes `product.md` states, which is a different
  question from what dominates now.
- **What could be dropped to cut the bill** without anyone noticing.

**Boundary with the wide half of `product`**, which is close but not the same question: `product`
asks who else would *use* it; this asks who would *pay*, and for what. A row that answers both is
raised once, here, naming the other lens.

## What research is for here

What products in this space charge and how they package it — tiers, limits, what sits behind the
paywall. And the current published prices of the services this project runs on, which move and are
the one input that is genuinely checkable. Link and date on every row.

## What is accepted, and where it goes

The same fork as `code`. A price, a tier, a paid feature is a decision about the product and goes
into the knowledge as an entry or a line in `product.md`. Enforcing a limit that already exists on
paper, caching a metered call, dropping an unused service — that is work, and goes into
`docs/technical_debt.md`.
