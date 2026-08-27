#!/bin/sh
# The project keeps everything it had except the one thing that says how it is
# checked. The second version refused to start an epic without this, and that
# refusal was fatal by design.
printf '[project]\ndefault_branch = "main"\ncommand_timeout = 20\n' > .agent-kit/v3/project.toml
