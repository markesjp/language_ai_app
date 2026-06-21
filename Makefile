SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

COMPOSE := docker compose
APP_SERVICES := frontend backend worker
SAFE_BUILDER_PRUNE_FILTER := until=24h

.PHONY: up dev-fast down rebuild rebuild-clean clean-docker status up-ollama-docker ollama-host-check ollama-docker-pull

up:
	$(COMPOSE) up --build

dev-fast:
	.\scripts\dev-fast.ps1 -Detached

down:
	$(COMPOSE) down

rebuild:
	$(COMPOSE) build $(APP_SERVICES)
	$(COMPOSE) up -d --force-recreate $(APP_SERVICES) nginx
	docker image prune -f
	docker builder prune -f --filter "$(SAFE_BUILDER_PRUNE_FILTER)"
	docker system df

rebuild-clean:
	$(COMPOSE) build --no-cache $(APP_SERVICES)
	$(COMPOSE) up -d --force-recreate $(APP_SERVICES) nginx
	docker image prune -f
	docker builder prune -f --filter "$(SAFE_BUILDER_PRUNE_FILTER)"
	docker system df

clean-docker:
	docker image prune -f
	docker builder prune -f --filter "$(SAFE_BUILDER_PRUNE_FILTER)"
	docker system df

status:
	$(COMPOSE) ps
	docker system df
	- nvidia-smi
	- Invoke-RestMethod http://localhost:11434/api/tags

ollama-host-check:
	nvidia-smi
	ollama list
	Invoke-RestMethod http://localhost:11434/api/tags

up-ollama-docker:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu up --build

ollama-docker-pull:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu exec ollama ollama pull llama3.2
	$(COMPOSE) -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu exec ollama ollama pull nomic-embed-text
