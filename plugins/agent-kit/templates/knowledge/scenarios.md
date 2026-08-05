<!--
Scenarios — eight to ten concrete walks end to end, on real names and real numbers.

This is how completeness is tested. Where the honest answer during a walk is "well, we would
add another field", the knowledge is wrong, and it shows in five minutes rather than five weeks.
Walking is cheaper and finds more than a longer questionnaire.

They are also what `mvp` proves against the running application: every scenario inside the MVP
bounds has to pass.

An end-to-end test claims a scenario by carrying `agent-kit:scenario <this heading>` in a comment;
that is how the kit counts which of them are still proved by nothing but a reading of the code.

fields: Who, Starting point, Steps, Ends with

Steps name action keys, so a scenario that mentions an action nobody wrote is a finding.

Done when: the main paths through the product are walked, including at least one where
something goes wrong.
-->

# Scenarios

<!--
### Anna gets an offer and accepts it

**Who:** Anna, a buyer
**Starting point:** she has published a request for a two-room flat under 12M
**Steps:**
1. `developer.create_offer` — Sever LLC offers a flat in Sosny at 11.4M
2. `buyer.open_offer` — Anna opens it from the request screen
3. `buyer.accept_offer` — she accepts; the offer goes to `accepted`
4. the request closes, the two other pending offers go to `rejected`
**Ends with:** a deal in `draft`, both sides notified
-->
