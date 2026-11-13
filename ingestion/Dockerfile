# Image du job d'ingestion (Cloud Run Job). Implémentée à l'étape 4.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY ingestion/src ./ingestion/src
RUN pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "ingestion.main"]
