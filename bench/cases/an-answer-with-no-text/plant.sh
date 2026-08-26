#!/bin/sh
mkdir -p "$XDG_CONFIG_HOME/agent-kit"
cat > "$XDG_CONFIG_HOME/agent-kit/config.toml" <<TOML
[owner]
channel = "file"
file = "$BENCH/owner"
wait = 2
TOML
# Реплай на сообщение кита, и в нём нет ни слова: стикер, фотография, голосовое.
# На телефоне это одно движение пальцем, и оно приходит как обычный ответ.
printf '#1 \n' > "$BENCH/owner.in"
