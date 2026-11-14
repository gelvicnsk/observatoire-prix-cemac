# Image unique du pipeline (étape 7) : ingestion, dbt et rapprochement.
# Deux Cloud Run Jobs l'utilisent, chacun avec son compte de service (ADR-010) :
#   obs-ingestion  ->  pipeline/entrypoint.sh ingest     (sa-ingestion)
#   obs-transform  ->  pipeline/entrypoint.sh transform  (sa-dbt)
FROM python:3.12-slim

# git : nécessaire à « dbt deps » (dbt_utils est pris sur GitHub, version figée dans package-lock.yml)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_PROFILES_DIR=/app/dbt \
    DBT_PROJECT_DIR=/app/dbt \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false

WORKDIR /app

# Dépendances d'abord : la couche est réutilisée tant que pyproject.toml ne change pas
COPY pyproject.toml ./
COPY ingestion/src ./ingestion/src
RUN pip install --no-cache-dir ".[dbt]"

COPY dbt ./dbt
RUN cd dbt && dbt deps

COPY quality ./quality
COPY pipeline ./pipeline
RUN chmod +x pipeline/entrypoint.sh \
    && useradd --create-home --uid 10001 pipeline \
    && chown -R pipeline /app
USER pipeline

ENTRYPOINT ["/app/pipeline/entrypoint.sh"]
