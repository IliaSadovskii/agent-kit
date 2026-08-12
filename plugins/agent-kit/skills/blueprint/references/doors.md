# Reading it back, and what the owner found by using it

Two things that are not the five steps of `SKILL.md`, and each is read only when you are in it.
`--recall` is its own invocation. The second is not a door at all any more — it is what step 3 does
with a contradiction the owner found by clicking through the product, and the table is here because
no run that meets none needs to carry it.

## `--recall` — reading it back

The owner works through a session, not through a text editor. So when they have forgotten what a
part says, or doubt it, or want to rework it, **the answer is not "open `docs/knowledge/actions.md`"**
— it is you, retelling it.

`--recall` with nothing names the parts, one line each, and asks which to open. `--recall <part>`
tells that one:

- what it is for, in a sentence;
- who does what in it, and what the person sees;
- what happens when it does not work;
- what is **not** built yet — `planned` entries, open blocks, promises the product does not keep;
- and what is thin: fields nobody filled, and whether the owner ever walked this part or it was
  derived.

**A retelling, never the file.** Reading the entries out is the same wall of text they came here to
avoid, and it is what makes them stop asking. One screenful per part; if it will not fit, the part
is too big and say so.

Then one round of choices: *right as it stands* · *change this* · *rework the part*. The first ends
the session. The second and third are the ordinary interview, on that part alone, and everything
about how it is written and committed is unchanged.

**It decides nothing and writes nothing on its own.** That is what separates it from `--check`,
which is mechanical and silent when clean: this one always speaks, in prose, and is for a person.

## After the owner has used it

The first run of anything is wrong somewhere, and the owner finds out by clicking through it rather
than by reading. That is a different input from an interview: not what they imagine, what they saw.
It arrives as a list of complaints, in their words, in no order.

**Every complaint is one fork, and it is a fork the kit already knows** — the same one a build hits
when an entry promises what the code does not:

| What is wrong | Where it goes |
|---|---|
| **the description** — the product behaves correctly and is described wrongly | yours: rewrite the prose, which nothing else may |
| **the product** — the description is right and the build is not | a line in `docs/technical_debt.md`, marked `owner`, written by you as they say it. An entry that was never built at all goes back to `state: planned` instead |

Put that fork up per complaint, with your reading first. Do not resolve it by rewriting the entry to
match the code — that is how a product decision gets made by whoever typed last, and the entry stops
being something the build can be held to.

**The right-hand row is not "tell them to run `fix`".** A complaint answered with the name of
another command is a complaint that dies when this session closes: they are describing nine things
and will not run nine commands. The line is what survives, and everything downstream already reads
it — the check counts it, `sprint` with no theme offers the pile, `epic` takes it as work the
project owes, `next` names it at rung 9. Whether it becomes a `fix` or a batch is decided later, by
whoever is choosing work, which is not this session.

This is where `accept` hands over: it says what to open and what to click, and this takes what was
seen there.

