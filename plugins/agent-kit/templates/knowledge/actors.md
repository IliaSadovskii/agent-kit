<!--
Actors — everyone and everything that initiates an action.

An actor is not only a user role. An operator of a CLI, an external system calling in, a
schedule, and the product itself acting on its own are all actors. Generalising this is what
keeps the model working on a library or a pipeline.

fields: Comes to exist, Can do, Must never

Key convention: a short lowercase slug — developer, buyer, scheduler, payment_gateway.

Done when: every actor named anywhere in the product description has an entry, and every actor
has at least one action attributed to it in actions.md.
-->

# Actors

<!--
### Developer
`key: developer`

**Comes to exist:** registers and is verified by a moderator
**Can do:** publish lots, answer buyer requests — nobody else may publish a lot
**Must never:** see another developer's offers on the same request
-->
