# Point d'entrée unique du projet.
SHELL := /bin/bash
export PATH := $(CURDIR)/.venv/bin:$(PATH)
ENV ?= dev
MONTH ?= $(shell date -d "last month" +%Y-%m)

.PHONY: help install lint test profile tf-bootstrap tf-fmt tf-validate tf-init tf-plan tf-apply tf-destroy ingest-local ingest run backfill dbt-build

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

tf-bootstrap:       ## étape 2 : une seule fois, en local (TF_VAR_billing_account requis)
	terraform -chdir=infra/bootstrap init
	terraform -chdir=infra/bootstrap apply

tf-fmt:             ## formate tous les fichiers Terraform
	terraform -chdir=infra fmt -recursive

tf-validate:        ## vérifie la syntaxe de chaque environnement (sans accès au backend)
	for d in bootstrap envs/dev envs/prod; do \
	  terraform -chdir=infra/$$d init -backend=false -input=false >/dev/null && \
	  terraform -chdir=infra/$$d validate || exit 1; \
	done

tf-init:
	terraform -chdir=infra/envs/$(ENV) init -backend-config=backend.hcl -input=false

tf-plan: tf-init    ## make tf-plan ENV=dev
	terraform -chdir=infra/envs/$(ENV) plan -out=tfplan

tf-apply:           ## applique le plan produit par tf-plan
	terraform -chdir=infra/envs/$(ENV) apply tfplan

tf-destroy:         ## dev uniquement : vérifie que tout se recrée depuis zéro
	@test "$(ENV)" = "dev" || (echo "destroy autorisé en dev uniquement" && exit 1)
	terraform -chdir=infra/envs/dev destroy

ingest-local:       ## étape 4 : ingestion en local (data/lake), sans accès GCP
	python -m ingestion.main --target local

ingest:             ## étape 4 : ingestion vers le bucket raw, meta et les tables externes bronze
	python -m ingestion.main --target gcp

run:                ## ingestion + dbt pour un mois (MONTH=2026-10)
	bash scripts/run_local.sh $(MONTH)

backfill:           ## rejouer une période : make backfill FROM=2020-01 TO=2026-10
	bash scripts/backfill.sh $(FROM) $(TO)

dbt-build:
	cd dbt && dbt build --target $(ENV)
