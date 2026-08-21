# The interface every project on this server answers to: up, down, test.
export UID := $(shell id -u)
export GID := $(shell id -g)

COMPOSE := docker compose

.PHONY: up down test shell install-check clean

up:            ## raise the workshop and install the kit into it
	$(COMPOSE) up -d --build --wait

down:          ## stop it, keeping the caches
	$(COMPOSE) down

test:          ## the whole suite
	$(COMPOSE) exec -T kit pytest

shell:         ## a prompt inside the workshop
	$(COMPOSE) exec kit bash

install-check: ## S0's proof: `uv tool install` puts a working command on PATH
	$(COMPOSE) exec -T kit sh -c 'uv tool install --force --reinstall . && "$$HOME/.local/bin/agent-kit" --version'

clean:         ## stop and remove the caches too
	$(COMPOSE) down -v
