#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 3
TOML

$KIT -C "$REPO" ask plant --slug "$SLUG" --step design \
  --id 2xdhdn --question 'one VAT rate for everything, or one per country?' \
  --default 'one rate for everything' --message 99 --until '2020-01-01T00:00:00+00:00' \
  > "$BENCH/ask-planted" 2>&1 || exit 1
# Человек отвечает реплаем на то сообщение, которое увидит он, а не на чужое.
printf '#1 one per country, and Russia is 20\n' > "$BENCH/owner.in"
