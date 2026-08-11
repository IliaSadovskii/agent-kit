# The blocks runs leave, and how each ends

Read when the check names one and you are about to settle it. Four kinds and four endings.

**Who may delete which is not here — it is in `${CLAUDE_PLUGIN_ROOT}/rules/channels.md`**, one row
per block, because three commands can close one between them and a list kept in two places is how
they came to disagree. What you are the sole closer of, and what a build command with the owner
present or the session closing a batch may also close, is settled there.

A run never stops over the knowledge and never asks it to be rewritten. It leaves a block and
carries on. Four kinds, and each has its own ending:

| Block | What it means | What you do with it |
|---|---|---|
| `[assumed …]` under the entry | the knowledge did not say, the run decided | ask it as a yes-or-no — *"I took it that an offer goes to `withdrawn`; right?"* — write the answer into the entry, delete the block |
| `[found …]` under `stack.md` | a ready-made answer the library map does not name | confirm it belongs, add the package and what it covers to the library map, delete the block |
| `[stale …]` under the entry | the feature that shipped made the entry's prose false | nothing to ask: rewrite the prose to what is true now, delete the block |
| `[accepted …]` in the slot it names | `advise` proposed it, the owner said yes, and the fields were left for later | nothing to decide — it is already agreed. Interview the fields the record declares, write the entry, delete the block |

The check prints all four before every command. **Deleting the block is the resolution**; there is
no `resolved` field anywhere.

`[accepted …]` is the one that arrives already answered, so do not re-open it: asking again whether
the owner wants what they accepted last week is how a list stops being read. If they have changed
their mind, they will say so in a sentence and the block goes without an entry.

**And a ledger line whose work you have just done, you delete** — in `docs/technical_debt.md`, in
the same commit, exactly as any run does when it finishes an item. A line asking for prose to be
rewritten has no other closer: `ship` and `fix` may not touch prose, so if you leave it the work is
done and the line stays for ever. Only the ones you actually closed, and nothing else in that file.

**A recorded assumption is the decision of record until the owner changes it.** A later run hitting
the same gap follows it rather than inventing a second reading — that is what keeps features
consistent with each other.

Blueprint's work list is exactly these blocks plus what `--check` flags, so a second run costs
minutes rather than hours.

Blocks are only left where being wrong is expensive — data model, permissions, money, a public
contract — or where the run's own confidence was low. Everything else stays in the run file as
history. Without that filter the documents silt up after one sprint. A `[stale …]` has no such bar:
prose that contradicts the product is always worth a block, because every later run reads it as
true.

