# The interface every project on this server answers to: up, down, test.
export UID := $(shell id -u)
export GID := $(shell id -g)

COMPOSE := docker compose

.PHONY: up down test round bench armed shell install-check clean

up:            ## raise the workshop and install the kit into it
	$(COMPOSE) up -d --build --wait

down:          ## stop it, keeping the caches
	$(COMPOSE) down

# Four questions, and each is asked once. `test` is the kit's own code; `bench`
# is the mechanisms, planted; `armed` is whether the traps are traps at all.
# `round` is all three, which is the verification round in one word — the suite
# used to run the bench twice and the disarm once inside itself, so a round
# measured 142 worlds five times over.

test: up       ## the kit's own code; it names what it left to `bench` and `armed`
	$(COMPOSE) exec -T kit pytest

round: test bench armed  ## all three, in order: the whole verification round
	@echo "the suite, the bench and the disarm have all answered"

bench: up      ## the planted traps: which mechanisms fired and which did not
	$(COMPOSE) exec -T kit python -m agent_kit bench run

armed: up      ## the same traps taken away: every case must stop firing without one
	$(COMPOSE) exec -T kit python -m agent_kit bench disarm

shell:         ## a prompt inside the workshop
	$(COMPOSE) exec kit bash

install-check: up  ## S0's proof: `uv tool install` puts a working command on PATH
	$(COMPOSE) exec -T kit sh -c 'uv tool install --force --reinstall . \
	  && "$$HOME/.local/bin/agent-kit" --version \
	  && "$$HOME/.local/bin/agent-kit" step show probe' 

clean:         ## stop and remove the caches too
	$(COMPOSE) down -v
