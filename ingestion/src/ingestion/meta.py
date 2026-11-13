"""Journal technique : fichiers déjà traités (empreinte sha256) et journal de chargement.

Deux implémentations : fichiers JSON Lines en local, tables du dataset BigQuery `meta` en cloud.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProcessedFile:
    source: str
    partition_key: str
    sha256: str
    object_uri: str
    landing_uri: str
    rows: int
    size_bytes: int
    ingested_at: str
    run_id: str


@dataclass(frozen=True)
class LoadLogEntry:
    run_id: str
    source: str
    partition_key: str
    status: str  # success | skipped | failed
    rows: int
    message: str
    started_at: str
    finished_at: str


class MetaStore(Protocol):
    def is_processed(self, source: str, partition_key: str, sha256: str) -> bool: ...
    def record_file(self, entry: ProcessedFile) -> None: ...
    def log(self, entry: LoadLogEntry) -> None: ...


class LocalMeta:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._files = self.root / "processed_files.jsonl"
        self._log = self.root / "load_log.jsonl"

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def _append(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def is_processed(self, source: str, partition_key: str, sha256: str) -> bool:
        return any(
            r["source"] == source and r["partition_key"] == partition_key and r["sha256"] == sha256
            for r in self._read(self._files)
        )

    def record_file(self, entry: ProcessedFile) -> None:
        self._append(self._files, asdict(entry))

    def log(self, entry: LoadLogEntry) -> None:
        self._append(self._log, asdict(entry))

    def log_entries(self) -> list[dict]:
        return self._read(self._log)


class BigQueryMeta:
    """Tables meta.processed_files et meta.load_log, créées si besoin avec un schéma explicite."""

    def __init__(self, project: str, location: str, dataset: str = "meta"):
        from google.cloud import bigquery

        self._bq = bigquery
        self.client = bigquery.Client(project=project, location=location)
        self.dataset = f"{project}.{dataset}"
        S = bigquery.SchemaField
        self.files_schema = [
            S("source", "STRING", "REQUIRED"),
            S("partition_key", "STRING", "REQUIRED"),
            S("sha256", "STRING", "REQUIRED"),
            S("object_uri", "STRING", "REQUIRED"),
            S("landing_uri", "STRING", "REQUIRED"),
            S("rows", "INT64", "REQUIRED"),
            S("size_bytes", "INT64", "REQUIRED"),
            S("ingested_at", "TIMESTAMP", "REQUIRED"),
            S("run_id", "STRING", "REQUIRED"),
        ]
        self.log_schema = [
            S("run_id", "STRING", "REQUIRED"),
            S("source", "STRING", "REQUIRED"),
            S("partition_key", "STRING", "REQUIRED"),
            S("status", "STRING", "REQUIRED"),
            S("rows", "INT64", "REQUIRED"),
            S("message", "STRING", "NULLABLE"),
            S("started_at", "TIMESTAMP", "REQUIRED"),
            S("finished_at", "TIMESTAMP", "REQUIRED"),
        ]
        for name, schema in (("processed_files", self.files_schema), ("load_log", self.log_schema)):
            self.client.create_table(self._bq.Table(f"{self.dataset}.{name}", schema=schema), exists_ok=True)

    def is_processed(self, source: str, partition_key: str, sha256: str) -> bool:
        P = self._bq.ScalarQueryParameter
        job = self.client.query(
            f"select count(*) as n from `{self.dataset}.processed_files` "
            "where source = @source and partition_key = @key and sha256 = @sha",
            job_config=self._bq.QueryJobConfig(
                query_parameters=[
                    P("source", "STRING", source),
                    P("key", "STRING", partition_key),
                    P("sha", "STRING", sha256),
                ]
            ),
        )
        return next(iter(job.result())).n > 0

    def _append(self, table: str, schema: list, record: dict) -> None:
        # Chargement (et non insertion en flux) : la ligne est immédiatement lisible et sans coût de streaming.
        config = self._bq.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND")
        self.client.load_table_from_json([record], f"{self.dataset}.{table}", job_config=config).result()

    def record_file(self, entry: ProcessedFile) -> None:
        self._append("processed_files", self.files_schema, asdict(entry))

    def log(self, entry: LoadLogEntry) -> None:
        self._append("load_log", self.log_schema, asdict(entry))
