"""The provider that is not real.

Everything up to the first adapter must be testable with no agent CLI installed
and no network — that is why the second version's tests ran at all. This is a
fixture, and it ships with the kit because the bench needs it too.
"""

from .adapter import FakeExecutor

__all__ = ["FakeExecutor"]
