# Point d'entrée unique du projet.
SHELL := /bin/bash
export PATH := $(CURDIR)/.venv/bin:$(PATH)
ENV ?= dev
MONTH ?= $(shell date -d "last month" +%Y-%m)

.PHONY: help install lint test profile tf-bootstrap tf-plan tf-apply run backfill dbt-build

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1

install:            ## environnement Python local
	python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

lint:               ## ruff + sqlfluff + terraform fmt
	ruff check . && ruff format --check .
	sqlfluff lint dbt/models || true
	terraform -chdir=infra fmt -check -recursive

test:               ## tests unitaires
	pytest -q

profile:            ## étape 1 : fiche de profondeur par pays
	python scripts/profile_sources.py

tf-bootstrap:       ## étape 2 : une seule fois, en local
	terraform -chdir=infra/bootstrap init && terraform -chdir=infra/bootstrap apply

tf-plan:
	terraform -chdir=infra/envs/$(ENV) init && terraform -chdir=infra/envs/$(ENV) plan

tf-apply:
	terraform -chdir=infra/envs/$(ENV) apply

run:                ## ingestion + dbt pour un mois (MONTH=2026-10)
	bash scripts/run_local.sh $(MONTH)

backfill:           ## rejouer une période : make backfill FROM=2020-01 TO=2026-10
	bash scripts/backfill.sh $(FROM) $(TO)

dbt-build:
	cd dbt && dbt build --target $(ENV)
