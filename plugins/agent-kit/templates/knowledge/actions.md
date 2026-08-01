<!--
Actions — what actors do. This is the unit of work: a feature is a small coherent group of
actions and the screens they are reached from.

Every entry carries a state, and it is the only place implementation progress is recorded:
  planned              nothing built yet
  building (pr: N)     a run opened a pull request for it
  built                that pull request merged

`built` means the code for this exists — not that it works. Whether it works is what the scenarios
answer, against a running application, and on a project the kit adopted they have never been run.
A build command sets `building`; `--check` moves it to `built` or back to `planned` by reading
the pull request. Nothing else writes this line.

fields: Who, Trigger, Preconditions, What happens, What changes, Initiator sees, Others see, Can go wrong, Reached from

Key convention: actor.verb_object — developer.create_offer, scheduler.expire_offers.

Done when: every action an actor can take is listed, all fields are answered, and every key it
names — actor, entity, status, screen — exists in its own file.
-->

# Actions

<!--
### Developer creates an offer
`key: developer.create_offer` · `state: planned`

**Who:** developer
**Trigger:** sees a buyer request matching one of their lots
**Preconditions:** the request is active; the developer has no live offer on it
**What happens:** picks a lot, states a price and a term, sends
**What changes:** an offer is created in `pending`; the request's offer count rises
**Initiator sees:** the offer in their own list, marked as awaiting an answer
**Others see:** the buyer is notified and sees the offer on the request
**Can go wrong:** the request was cancelled between opening the form and sending
**Reached from:** `screen.request_detail`
-->
