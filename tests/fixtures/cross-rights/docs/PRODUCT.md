# The product this fixture pretends to have

Three actors, one entity and two actions, written the way an owner writes them: prose with
headings, and a kit anchor under each one so a rename cannot break the binding.

## Creating an offer
<!-- kit: developer.create_offer -->

A developer publishes an offer against a buyer request they have a matching lot for. The offer
starts out pending.

## Accepting an offer
<!-- kit: broker.accept_offer -->

A broker accepts a pending offer on the buyer's behalf, which is what ends the offer's life.

## The developer
<!-- kit: developer -->

Sells lots. Publishes offers, and nothing else.

## The broker
<!-- kit: broker -->

Acts for the buyer. Accepts offers, and nothing else.

## The offer
<!-- kit: offer -->

What a developer publishes and a broker accepts. It is pending until it is accepted.
