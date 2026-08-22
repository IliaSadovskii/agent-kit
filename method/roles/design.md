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

If the brief cannot be designed as written — it contradicts what is here, or it needs a
decision only the owner can make — put the question in `needs_owner`, one line each. That
field is printed in the open half of the pull request, and until the kit has a channel of
its own it is the only way a question reaches the owner at all; `summary` is not, because
it is folded away. Then design the smallest honest thing you can around the question. Do
not invent a requirement to make the brief work.
