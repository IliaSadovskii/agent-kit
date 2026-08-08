# Lens: product

**The question: is this the right product, and who else could it be for?** What a user cannot finish
because a step was never built. What exists and serves nobody. What people like these expect from a
product like this and do not get here. Who is nearly a user already. And what to drop, because a
narrower product is often the better one.

Reference: the scenarios and the actions, and then the domain itself. Walks: every scenario end to
end, then every action — and after that, the people.

## Close half

Three questions per walk, and only three. A fourth is how this half turns into "it would also be
nice if":

1. **What is missing for the scenario to finish** without *and then the user emails support*. A step
   that has no action behind it is the whole defect.
2. **What exists that no scenario touches.** A candidate for removal, not for improvement. This is
   the proposal owners never make themselves and are often relieved to hear.
3. **Which step a real person abandons at** — how many fields, how many waits, how many decisions
   before anything of value comes back.

**Every scenario and every action gets a row**: a proposal, `clean`, or `unjudged` with the reason.
The scenarios were written on real names and numbers, so a row that cannot name the step is not
about this project.

```
scenario 4 «покупатель возвращает товар»
  ломается на   шаг 3 — заявка уходит менеджеру, ни одно действие не отвечает за ответ
  предложение   действие manager.answer_return_request
  трогает       actors: manager (есть) · entities: return_request (нет)
  цена          новая сущность и экран в админке
  без него      покупатель ждёт молча, сценарий не доходит до конца
```

## Wide half

**Write the reading of the domain into the report first, before a single proposal.** Who this is
really for, what they are really buying, what they do *instead* today — how they solve this without
the product at all — where their time and money go, who is standing next to them.

Five to seven lines, and they are not decoration. The performance lens of `audit` writes its
anti-pattern catalogue into the report before using it, for the same reason: an unstated reference
makes the scope of the work invisible. Here it does one thing more — the proposals get judged against
a stated understanding, instead of the understanding being reconstructed afterwards from whatever was
proposed.

Then four questions:

- **What an audience like this expects from a product like this**, and does not find here.
- **Who is standing next to it and is not served.** An adjacent kind of person the machine already
  almost fits — frequently one field and one screen away.
- **What would make it noticeably pleasant** where it currently merely works.
- **Who should stop being served.** Narrowing is sometimes the win, and nobody volunteers it.

### Three lines, or it is not a proposal

The close half cites a file. This half has no file to cite, so the discipline is a shape instead:

> **кому** — a group named in the reading of the domain, not "users"
> **что они делают вместо** — today, without this product
> **что у них меняется**

*"Add a referral programme"* does not survive those three lines. *"Sellers copy their catalogue into
Telegram by hand — a one-file import gives them an evening back"* does, and can be checked by asking
one seller. A proposal that cannot fill all three is not raised; it goes in **considered and
rejected** with the line it failed on.

The cheapest way to produce output that looks like this half's work is a generic feature list —
notifications, referrals, gamification, analytics. It reads as thorough and is written without
opening anything. The three lines are what that path cannot produce.

### The report opens with the small edits

**"Мелкие правки с непропорциональным эффектом"** — cheap to build, large in effect — is the first
section, above everything else. It is what this lens is for. A new direction that takes a month is
worth writing down and it is not what the owner came for.

## What research is for here

Briefed from the reading of the domain, never before it. How this job is done today without you —
the live products in the space. **What people dislike about products like these**, in reviews and
forums, where finished proposals are lying around already written by the people who would use them.
What changed in the space this year. Regulation and seasonality where they apply.

Every such row carries a link and a date, or it is not `from research` — recalling a competitor's
behaviour from memory reads exactly like research, is not, and is a year stale.

## Closing lines of this half

Two, always, and they are what let the owner tell experience from fluent invention:

- **what you know about this domain and where from**;
- **three questions whose answers would change this list**.
