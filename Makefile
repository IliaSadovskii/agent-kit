# The interface every project on this server answers to: up, down, test.
export UID := $(shell id -u)
export GID := $(shell id -g)

COMPOSE := docker compose

.PHONY: up down test bench armed shell install-check clean

up:            ## raise the workshop and install the kit into it
	$(COMPOSE) up -d --build --wait

down:          ## stop it, keeping the caches
	$(COMPOSE) down

test: up       ## the whole suite
	$(COMPOSE) exec -T kit pytest

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
