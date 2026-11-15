"""Traitement d'un fichier brut : empreinte, original conservé, Parquet typé, journal.

Idempotence : un fichier dont l'empreinte est déjà connue pour la même source et la même partition
est ignoré ; et comme les chemins dépendent de l'empreinte, réécrire un fichier produit le même objet.
L'enregistrement dans `processed_files` se fait en dernier : une panne avant lui fait simplement
retraiter le fichier au run suivant, sans doublon.

Quarantaine (ADR-012) : un fichier téléchargé mais refusé (colonnes attendues absentes, valeur impossible à
typer) n'arrête pas le run. Son contenu d'origine est déposé dans `_quarantine/`, et l'échec est journalisé
avec le statut `quarantined`. Comme il n'est pas enregistré dans `processed_files`, il est retraité dès que
le code ou la source est corrigé : au run suivant, ou tout de suite avec `python -m ingestion.replay`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime

import pyarrow as pa

from ingestion.meta import LoadLogEntry, MetaStore, ProcessedFile
from ingestion.profiling import read_csv_as_text
from ingestion.schemas import (
    fx_to_table,
    rainfall_to_table,
    to_parquet_bytes,
    wfp_to_table,
    world_bank_to_table,
)
from ingestion.sources import RawFile

CONTENT_TYPES = {"csv": "text/csv", "json": "application/json"}


@dataclass(frozen=True)
class Outcome:
    source: str
    partition_key: str
    status: str  # success | skipped | quarantined | failed
    rows: int
    message: str


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse(raw: RawFile, sha256: str, ingested_at: datetime, run_id: str) -> pa.Table:
    if raw.source == "wfp":
        frame = read_csv_as_text(raw.content)
        return wfp_to_table(frame, raw.partitions["country"], sha256, ingested_at, run_id)
    if raw.source == "world_bank":
        return world_bank_to_table(json.loads(raw.content), sha256, ingested_at, run_id)
    if raw.source == "rainfall":
        frame = read_csv_as_text(raw.content)
        return rainfall_to_table(frame, raw.partitions["country"], sha256, ingested_at, run_id)
    if raw.source == "fx":
        frame = read_csv_as_text(raw.content)
        return fx_to_table(frame, sha256, ingested_at, run_id)
    raise ValueError(f"source inconnue : {raw.source}")


QUARANTINE_PREFIX = "_quarantine/"


def _prefix(raw: RawFile, ingest_date: date) -> str:
    partitions = "/".join(f"{k}={v}" for k, v in raw.partitions.items())
    return f"{raw.source}/{partitions + '/' if partitions else ''}ingest_date={ingest_date.isoformat()}"


def object_paths(raw: RawFile, ingest_date: date, sha256: str) -> tuple[str, str]:
    """(original, parquet) — partitions au format Hive, lues par les tables externes BigQuery."""
    prefix, name = _prefix(raw, ingest_date), sha256[:16]
    return f"_landing/{prefix}/{name}.{raw.extension}", f"{prefix}/{name}.parquet"


def quarantine_path(raw: RawFile, ingest_date: date, sha256: str) -> str:
    return f"{QUARANTINE_PREFIX}{_prefix(raw, ingest_date)}/{sha256[:16]}.{raw.extension}"


def raw_from_quarantine_path(path: str, content: bytes) -> RawFile:
    """Reconstruit le fichier brut d'origine depuis son chemin de quarantaine (pour le rejouer)."""
    parts = path.removeprefix(QUARANTINE_PREFIX).split("/")
    source, *middle, name = parts
    partitions = dict(p.split("=", 1) for p in middle if not p.startswith("ingest_date="))
    return RawFile(
        source=source,
        partitions=partitions,
        content=content,
        extension=name.rsplit(".", 1)[1],
        url=f"quarantine:{path}",
    )


def process(raw: RawFile, store, meta: MetaStore, ingest_date: date, run_id: str) -> Outcome:
    started = now_utc()
    sha256 = hashlib.sha256(raw.content).hexdigest()

    def finish(status: str, rows: int, message: str) -> Outcome:
        meta.log(
            LoadLogEntry(
                run_id=run_id,
                source=raw.source,
                partition_key=raw.partition_key,
                status=status,
                row_count=rows,
                message=message,
                started_at=started.isoformat(),
                finished_at=now_utc().isoformat(),
            )
        )
        return Outcome(raw.source, raw.partition_key, status, rows, message)

    if meta.is_processed(raw.source, raw.partition_key, sha256):
        return finish("skipped", 0, f"fichier déjà traité (sha256 {sha256[:12]}…)")

    table = parse(raw, sha256, started, run_id)
    landing_path, parquet_path = object_paths(raw, ingest_date, sha256)
    landing_uri = store.write_bytes(landing_path, raw.content, CONTENT_TYPES[raw.extension])
    object_uri = store.write_bytes(parquet_path, to_parquet_bytes(table), "application/octet-stream")
    meta.record_file(
        ProcessedFile(
            source=raw.source,
            partition_key=raw.partition_key,
            sha256=sha256,
            object_uri=object_uri,
            landing_uri=landing_uri,
            row_count=table.num_rows,
            size_bytes=len(raw.content),
            ingested_at=started.isoformat(),
            run_id=run_id,
        )
    )
    return finish("success", table.num_rows, f"{table.num_rows} lignes, sha256 {sha256[:12]}…")


def quarantine(raw: RawFile, error: Exception, store, meta: MetaStore, ingest_date: date, run_id: str) -> Outcome:
    """Fichier reçu mais refusé : on garde son contenu d'origine en quarantaine, et le run continue."""
    moment = now_utc().isoformat()
    sha256 = hashlib.sha256(raw.content).hexdigest()
    path = quarantine_path(raw, ingest_date, sha256)
    store.write_bytes(path, raw.content, CONTENT_TYPES[raw.extension])
    message = f"{type(error).__name__} : {error}"[:900] + f" | quarantaine={path}"
    meta.log(LoadLogEntry(run_id, raw.source, raw.partition_key, "quarantined", 0, message, moment, moment))
    return Outcome(raw.source, raw.partition_key, "quarantined", 0, message)


def fail(raw_source: str, partition_key: str, error: Exception, meta: MetaStore, run_id: str) -> Outcome:
    """Journalise un échec survenu avant ou pendant le traitement (téléchargement, contrat non respecté)."""
    moment = now_utc().isoformat()
    message = f"{type(error).__name__} : {error}"[:1000]
    meta.log(LoadLogEntry(run_id, raw_source, partition_key, "failed", 0, message, moment, moment))
    return Outcome(raw_source, partition_key, "failed", 0, message)
