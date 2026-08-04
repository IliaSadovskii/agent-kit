# Asking the owner

Every command that puts a question to the owner follows this. Read it before you ask; the rule is
short because there is only one thing to get right.

## Ask with choices, not with prose

A question is asked with the interactive question tool — `AskUserQuestion` — with the options
written out and the one you recommend first, marked as the recommendation. Not as a paragraph
ending in a question mark.

The owner reads from a phone. A tappable choice is answered in two seconds from anywhere; a wall of
text has to be read, understood, and replied to in words, so it waits for a desk — and a question
that waits for a desk stops a run that would otherwise be finished.

It also forces the question to be answerable. Writing three options is what reveals that the answers
all lead to the same work, and a question whose answers do not differ is one you should not be
asking. Options give the owner something to disagree with; open prose gives them homework.

**One question, two to four options.** If you have several, ask the one that blocks you — the rest
usually resolve themselves once it is answered, and a queue of questions is how a five-minute gate
becomes an evening.

## Say what you would do, and why it is a fork

The recommended option comes first and says what you would take. Below it, one line on what makes
this expensive to get wrong — stored data, a contract outside this codebase, a permission boundary,
money. Without that the owner cannot tell a real fork from a courtesy, and after a few courtesies
they answer without reading.

## Prose is for things that need no answer

Report in text: what you did, what you assumed, where you are, what is thin. Those are statements,
and dressing one as a question invites an answer that nothing will consume.

**Never ask a question nobody can act on.** Before asking, name the thing that will change if the
answer comes back — a task in this run, a branch, an entry rewritten. If nothing will, it is not a
question: record it and let it reach the owner where such things are decided, which is the pull
request.

## When nobody is present

`gate: none` in the run file means there is no one to ask. Then the fork becomes a recorded
assumption and the run carries on — see the rule each build command carries. Do not ask anyway, and
do not wait: an unanswered question in an unattended run is a night spent on nothing.
