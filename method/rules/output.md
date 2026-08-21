# How a step returns its output

Your reply is read by a program, not by a person. Say whatever you need to say, then
end with one fenced block:

```json
{ "field": "value" }
```

Rules the program applies to that block, without exception:

- The last fenced block in your reply is the one that is read. Earlier ones are ignored,
  so thinking out loud above it costs nothing.
- Every field the contract marks *required* must be there. A field you cannot answer is a
  refused step, not an empty string — say so in a field meant for saying things.
- A field the contract does not name is dropped. Adding one is harmless and pointless.
- No prose inside the block, no comments, no trailing commas. It is parsed, not read.

If the block is missing or does not satisfy the contract, the step is refused and you are
asked again with the reason enclosed. Three refusals and the run stops.
