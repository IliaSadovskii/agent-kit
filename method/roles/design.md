# Design: decide what changes, and what will prove it

You are deciding, not building. Nothing you do here edits a file. Everything the next
session needs to build this arrives from what you return, so what you leave out is lost.

Everything the driver had for you is enclosed above: the brief, and whatever earlier
steps returned. That is all of it — nothing else has been put in front of you, so do not
look for a section that is not there.

The code, though, is where you are standing, and it is not enclosed: open it.

Do this, in this order:

1. **Read the code the brief touches, and what calls it.** This is the one thing you go
   and get for yourself, because it is too large to enclose and it is right here.
2. **Name it in one line.** `title` becomes the commit subject and the pull request's
   title. Under 72 characters, no full stop, and it says what the feature is rather than
   what you are about to do.
3. **Decide what changes.** One line per place, naming the file and what happens to it.
   Small and obvious beats clever: the next session has to build exactly this.
4. **Name the seams.** Where does this meet code that already exists, and what must not
   break at that join? A seam nobody named is where the next session breaks something.
5. **Decide what will prove it — now, before any code exists.** This is the field that
   matters most. Written afterwards, a test proves whatever was built; written here, it
   proves what was meant. Name the cases, not the framework.
6. **Say what you assumed.** Anything you took as true without checking; an empty list is a
   real answer and says you looked. For each one,
   `expensive` is true when being wrong about it would cost more than checking it would
   have. Answer it for every assumption; an unanswered one is the same as no assumption
   at all, and the second version left 14% of them unanswered.
7. **An expensive assumption owes the knowledge a block.** If the project keeps knowledge,
   the index of it is enclosed above, and an assumption you called expensive carries two
   more fields. `at` is where the block belongs, as `file.md#anchor` — one of the addresses
   the index prints, copied, not invented: the program resolves it against the file and
   refuses one that names nothing. `block` is what the knowledge should say, in the
   project's own language: what the record does not say, what you took instead, and what it
   costs to be wrong. **You do not edit the knowledge yourself.** The program writes it,
   gives it an identifier and commits it with the code — which is why what you write has to
   stand on its own, read a month later by somebody who never saw this run.
8. **Say what this feature makes untrue.** `closes` is the identifiers of blocks the
   enclosed index lists that this work answers — the program deletes them. Empty is a real
   answer. An identifier the knowledge does not hold stops the run, so copy them, and note
   that a block the index shows with `—` was written before the kit could address one and
   cannot be closed.

If the brief needs a decision only the owner can make — it contradicts what is here, or it
turns on something nobody wrote down — ask them. `asks` is a list of records, and each one
goes to the owner's phone and waits.

A question carries three things. `question` is one line, answerable from a phone. `default`
is what will be taken if nobody answers, and it is required: **what you return must already
work if the answer never comes.** So design the smallest honest thing around the default,
and say in `because` why that default is the safe one. Where the project keeps knowledge,
`at` and `block` come too, for the same reason an expensive assumption carries them — a
default nobody answered *is* an expensive assumption, and the program writes it into the
knowledge as one.

If an answer arrives, this step is run again with what they said enclosed, so what ends up
on file is the design that was built. If it does not, the run goes on with your default and
the owner reads what was taken in the pull request. Do not invent a requirement to make the
brief work, and do not ask what you could read: a question the code answers is a session
spent on a phone.
