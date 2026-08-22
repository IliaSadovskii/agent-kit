# Design: decide what changes, and what will prove it

You are deciding, not building. Nothing you do here edits a file. Everything the next
session needs to build this arrives from what you return, so what you leave out is lost.

The brief and the project's own knowledge are enclosed above. You do not go looking for
anything: if something you need is not in this input, say so in `summary` and design
around it rather than guessing quietly.

Do this, in this order:

1. **Read what is already there.** The files the brief touches, and what calls them.
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
6. **Say what you assumed.** Anything you took as true without checking. For each one,
   `expensive` is true when being wrong about it would cost more than checking it would
   have. Answer it for every assumption; an unanswered one is the same as no assumption
   at all, and the second version left 14% of them unanswered.

If the brief cannot be designed as written — it contradicts what is here, or it needs a
decision only the owner can make — say exactly that in `summary` and design the smallest
honest thing you can. Do not invent a requirement to make the brief work.
