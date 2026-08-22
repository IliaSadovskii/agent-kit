"""The bench: planted traps, and judges that are scripts.

The tests are a clean room and a live night is one sample of a friendly world.
The bench is the third thing — the same run of the kit, but with the branch
occupied, the tree dirty and the suite red on purpose, and with a script saying
which mechanism fired.

Each case makes its own repository and destroys it, which is what lets one
version of the kit be compared against the next. Nothing here reaches the
network and nothing costs a token: every case answers from `providers/fake/`.
"""

from .cases import Case, CaseError, Expect, case_names, cases_root, read_case, read_cases
from .runner import Result, Verdict, run_case, run_named

__all__ = [
    "Case",
    "CaseError",
    "Expect",
    "Result",
    "Verdict",
    "case_names",
    "cases_root",
    "read_case",
    "read_cases",
    "run_case",
    "run_named",
]
