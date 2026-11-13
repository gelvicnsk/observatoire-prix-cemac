"""Tables externes du dataset bronze, posées sur les Parquet du bucket raw (partitions Hive).

Les fichiers restent la seule copie des données brutes : bronze ne fait que les rendre interrogeables.
Recréer la définition à chaque run est sans risque (instruction idempotente, aucune donnée déplacée).
"""

from __future__ import annotations

# source -> colonnes de partition (dans l'ordre des dossiers)
PARTITIONS: dict[str, list[tuple[str, str]]] = {
    "wfp": [("country", "STRING"), ("ingest_date", "DATE")],
    "world_bank": [("indicator", "STRING"), ("ingest_date", "DATE")],
    "rainfall": [("country", "STRING"), ("ingest_date", "DATE")],
    "fx": [("ingest_date", "DATE")],
}

TABLE_NAMES = {
    "wfp": "wfp_prices",
    "world_bank": "world_bank_indicators",
    "rainfall": "rainfall_adm2",
    "fx": "fx_eur_usd",
}


def external_table_ddl(project: str, bucket: str, source: str, dataset: str = "bronze") -> str:
    columns = ",\n  ".join(f"{name} {kind}" for name, kind in PARTITIONS[source])
    return (
        f"create or replace external table `{project}.{dataset}.{TABLE_NAMES[source]}`\n"
        f"with partition columns (\n  {columns}\n)\n"
        "options (\n"
        "  format = 'PARQUET',\n"
        f"  uris = ['gs://{bucket}/{source}/*'],\n"
        f"  hive_partition_uri_prefix = 'gs://{bucket}/{source}'\n"
        ")"
    )


def ensure_external_tables(project: str, location: str, bucket: str, sources: list[str]) -> list[str]:
    from google.cloud import bigquery

    client = bigquery.Client(project=project, location=location)
    created = []
    for source in sources:
        client.query(external_table_ddl(project, bucket, source)).result()
        created.append(f"bronze.{TABLE_NAMES[source]}")
    return created
