#!/bin/sh
# A session that tidies up after itself by committing. The branch it leaves is
# not the tree the commands ran over, whatever the record says.
git add -A
git commit -q -m "the reviewer commits what it read"
