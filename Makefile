MODEL ?= qwen3:4b
JUDGE_MODEL ?= qwen3:14b

install:
	python -m pip install -e ".[judge]"

pull:
	ollama pull $(MODEL)

record:
	PAYEVAL_MODEL=$(MODEL) python scripts/record.py

record-consistency:
	PAYEVAL_MODEL=$(MODEL) python scripts/record.py --consistency

test:
	PAYEVAL_MODEL=$(MODEL) python -m pytest

judge:
	PAYEVAL_MODEL=$(MODEL) PAYEVAL_JUDGE=1 python -m pytest -m judge

report:
	PAYEVAL_MODEL=$(MODEL) python scripts/report.py


# --- Docker ---
# OLLAMA=docker (по умолчанию): Ollama тоже в контейнере. Для Linux; на Mac только CPU, медленно.
# OLLAMA=host: Ollama запущена на компьютере, в контейнере только тесты. Для Mac.
# GPU=1: отдать Ollama видеокарту NVIDIA (Linux).
OLLAMA ?= docker
GPU ?= 0
DC_FILES = -f compose.yaml $(if $(filter 1,$(GPU)),-f compose.gpu.yaml)
export MODEL JUDGE_MODEL
export DOCKER_UID := $(shell id -u)
export DOCKER_GID := $(shell id -g)

ifeq ($(OLLAMA),host)
DC = docker compose $(DC_FILES)
export DOCKER_OLLAMA_HOST = http://host.docker.internal:11434
PULL = ollama pull
else
DC = docker compose $(DC_FILES) --profile ollama
PULL = $(DC) exec ollama ollama pull
endif

docker-build:
	docker compose build eval

docker-up:
ifneq ($(OLLAMA),host)
	$(DC) up -d --wait ollama
endif

docker-pull: docker-up
	$(PULL) $(MODEL)

docker-record: docker-pull
	$(DC) run --rm eval python scripts/record.py

docker-record-consistency: docker-pull
	$(DC) run --rm eval python scripts/record.py --consistency

docker-test:
	docker compose run --rm --no-deps eval python -m pytest

docker-judge: docker-up
	$(PULL) $(JUDGE_MODEL)
	$(DC) run --rm -e PAYEVAL_JUDGE=1 eval python -m pytest -m judge

docker-report:
	docker compose run --rm --no-deps eval python scripts/report.py

docker-down:
	$(DC) down

.PHONY: install pull record record-consistency test judge report \
	docker-build docker-up docker-pull docker-record docker-record-consistency \
	docker-test docker-judge docker-report docker-down
