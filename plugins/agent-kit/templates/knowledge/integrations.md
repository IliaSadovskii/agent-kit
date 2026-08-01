<!--
Integrations — the systems outside this product it depends on.

Never record credential values. Names of the environment variables only.

fields: What it is, We send, We receive, When it is down, Credentials

Key convention: integration.<slug>.

Done when: every external system the product talks to has an entry, and each says what happens
when it is unavailable.
-->

# Integrations

<!--
### Payment provider
`key: integration.payments` · `state: planned`

**What it is:** hosted checkout, the buyer pays there and returns
**We send:** an amount, an order id, a return URL
**We receive:** a webhook with the payment result
**When it is down:** the deal stays in `awaiting_payment`; the buyer sees a retry, nothing is
lost, and the webhook is idempotent by order id
**Credentials:** `PAYMENTS_KEY`, `PAYMENTS_WEBHOOK_SECRET`
-->
