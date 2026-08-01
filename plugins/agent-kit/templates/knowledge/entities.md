<!--
Entities — what lives longer than a single call, and what state it can be in.

States and transitions are the point of this file. An action that sets a status the entity does
not list is a defect, and that cross-check only works if the states are written down.

fields: What it is, States, Transitions, Relations, Invariants

Key convention: a singular lowercase noun — offer, request, lot.

Done when: every entity lists its states, who moves it between them, and the invariants that
must hold whatever happens.
-->

# Entities

<!--
### Offer
`key: offer`

**What it is:** a developer's answer to a buyer's request, tied to one lot
**States:** pending, accepted, rejected, withdrawn, expired
**Transitions:** pending to accepted by the buyer; pending to withdrawn by the developer;
pending to expired by the schedule after 14 days
**Relations:** belongs to one request and one lot; one developer may hold one live offer per request
**Invariants:** an accepted offer closes its request; an expired offer is never revived
-->
