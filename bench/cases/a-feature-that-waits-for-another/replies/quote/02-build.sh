#!/bin/sh
test "$(git rev-list --count main..kit/rates 2>/dev/null || echo 0)" -ge 1 || {
  echo "kit/rates holds no commit, so rates had not landed when quote started" >&2
  exit 1
}
printf 'QUOTE = 1\n' >> quote.py
