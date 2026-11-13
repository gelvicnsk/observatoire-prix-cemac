# Image du job dbt (Cloud Run Job). Implémentée à l'étape 7.
FROM python:3.12-slim
WORKDIR /dbt
RUN pip install --no-cache-dir "dbt-bigquery>=1.8,<2"
COPY dbt/ ./
RUN dbt deps
ENTRYPOINT ["dbt"]
CMD ["build", "--target", "prod"]
