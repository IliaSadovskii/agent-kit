<!--
Screens — the surface a person reaches an action through. Prose and keys, no map file and no
viewer: transitions name action keys, and the cross-checks work off those.

Screens carry a state of their own, like actions: a screen can be built with no new action
behind it.

fields: For whom, Purpose, On the screen, Arrived from, Leads to

Key convention: screen.<slug>.

A screen the product opens on is arrived from nowhere: write `entry_point` in "Arrived from", and
the check stops counting it as a screen nothing leads to.

Not applicable when the product has no user interface. Say so in project.yml with the reason
rather than inventing entries.

Done when: every screen a person can reach is listed, each names where people arrive from and
where they leave to, and every action key in a transition exists in actions.md.
-->

# Screens

<!--
### Offer list
`key: screen.offers_list` · `state: planned`

**For whom:** developer, buyer
**Purpose:** see the offers on a request
**On the screen:** offer cards, a status filter, an empty state
**Arrived from:** `screen.requests`, by opening a request
**Leads to:** `screen.offer_detail` through `developer.open_offer`; back to `screen.requests`
-->
