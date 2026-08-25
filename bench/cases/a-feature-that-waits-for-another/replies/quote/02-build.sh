#!/bin/sh
git log kit/rates --format=%s 2>/dev/null | grep -q . || {
  echo "kit/rates holds no commit, so rates had not landed when quote started" >&2
  exit 1
}
printf 'QUOTE = 1\n' >> quote.py
