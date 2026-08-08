# Lens: money

**The question: how does this product earn well without making itself worse to use?** What it costs to run, what somebody would happily pay for, and where the two are out of line.

Reference: how the product earns and what it costs to run. Walks: every action and integration that costs money to serve, and then the market.

**On most projects the knowledge records neither**, and that is this lens's first act rather than a reason to skip it. Say plainly that `product.md` names no revenue model and no running costs, put the questions to the owner, and run the half that does not need them. A lens that quietly invents a price list is worse than one that says what it could not read.

## Close half

Walk every action and integration that costs money to serve, and find where money leaves without a reason and where it could come in and does not. What that usually looks like: something given away that costs per use — an outbound call, storage, a paid API behind a free path; a limit the plan already states and the code never enforces; a metered integration called without a bound; something the audience clearly values with no way to pay for it.

**Same rule as `code`, one word different: a proposal without an amount or a rate is not a proposal.** *Move to cheaper hosting* says nothing; *the bill is ~$180 a month, ~$120 of it the free preview path* is something the owner can act on in a minute. No amount available is an `unjudged` row carrying the question.

```
guest.preview_report
  стоит          один вызов платного PDF-сервиса, ~$0.004, без кэша и без лимита
  доступно       анонимным посетителям, Report.php:64
  сейчас         ничто не ограничивает; в тарифе 20 в месяц, в коде эти 20 нигде нет
  предложение    включить лимит тарифа, кэшировать по хешу документа
  сколько это    при 1000 предпросмотрах в день один бесплатный путь — около $120 в месяц
```

**Every action that touches money gets a row** — a proposal, `clean`, or `unjudged` with the reason. Both directions count.

## Wide half

Think about how a product like this earns, and what these particular people would pay for. What the audience is already used to paying for elsewhere; the cheapest thing here somebody would pay for today, which is usually not the hardest feature to build; which running cost will dominate at the volumes `product.md` states, a different question from what dominates now; what could be dropped without anyone noticing.

**One constraint on the whole half: a way to earn that makes the product meaningfully worse to use is not a proposal here.** Say so in the row when the tension is real — the owner is choosing between money and their own users, and hiding that choice inside a pricing suggestion is the way this lens does damage.

**Boundary with the wide half of `product`**, which is close but not the same question: `product` asks who else would *use* it; this asks who would *pay*, and for what. A row that answers both is raised once, here, naming the other lens.

## What research is for here

What products in this space charge and how they package it — tiers, limits, what sits behind the paywall. And the current published prices of the services this project runs on, which move and are the one input that is genuinely checkable. Link and date on every row.

## What is accepted, and where it goes

The same fork as `code`. A price, a tier, a paid feature is a decision about the product and goes into the knowledge as an entry or a line in `product.md`. Enforcing a limit that already exists on paper, caching a metered call, dropping an unused service — that is work, and goes into `docs/technical_debt.md`.
