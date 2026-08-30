"""S9a — the way in, for a machine that has nothing installed.

One reading and two screens over it. `doctor` prints where this machine stands
and stops; `agent-kit setup` prints the same thing and then walks a person
through the commands that change it. Two passes that had to agree is the defect
§5 of the plan names, and there used to be a third — `provider list` printed
these same rows from a pass of its own.

Nothing here spends a session. The control surface never requires a live model,
and this is the control surface: the two free rungs of the ladder cost no quota,
and the rungs above them are `agent-kit provider check <name>`, which the walk
names by name rather than climbing itself.
"""

from .reading import Reading, Standing, read, render
from .walk import walk

__all__ = ["Reading", "Standing", "read", "render", "walk"]
