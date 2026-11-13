"""Idempotence du pipeline : même fichier = ignoré ; fichier modifié = nouvel objet ; échec = rien d'enregistré."""

from datetime import date
from pathlib import Path

from ingestion.meta import LocalMeta
from ingestion.pipeline import fail, object_paths, process
from ingestion.sources import RawFile
from ingestion.storage import LocalStore

FIXTURE = (Path(__file__).parent / "fixtures" / "wfp_sample.csv").read_bytes()
VALID = b"\n".join(line for line in FIXTURE.splitlines() if b"abc" not in line and b"not-a-date" not in line)


def raw(content: bytes = VALID) -> RawFile:
    return RawFile(source="wfp", partitions={"country": "COG"}, content=content, extension="csv", url="https://x")


def test_same_file_twice_is_skipped(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    first = process(raw(), store, meta, date(2026, 11, 13), "run1")
    second = process(raw(), store, meta, date(2026, 11, 14), "run2")
    assert first.status == "success" and first.rows == 4
    assert second.status == "skipped"
    assert len(list((tmp_path / "wfp").rglob("*.parquet"))) == 1


def test_changed_file_creates_new_object(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    process(raw(), store, meta, date(2026, 11, 13), "run1")
    changed = VALID.replace(b",600,", b",610,")
    assert process(raw(changed), store, meta, date(2026, 11, 13), "run2").status == "success"
    assert len(list((tmp_path / "wfp").rglob("*.parquet"))) == 2


def test_paths_are_hive_partitions_named_by_hash():
    landing, parquet = object_paths(raw(), date(2026, 11, 13), "f" * 64)
    assert parquet == "wfp/country=COG/ingest_date=2026-11-13/ffffffffffffffff.parquet"
    assert landing == "_landing/wfp/country=COG/ingest_date=2026-11-13/ffffffffffffffff.csv"


def test_invalid_file_is_not_recorded(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    try:
        process(raw(FIXTURE), store, meta, date(2026, 11, 13), "run1")
    except Exception as error:  # noqa: BLE001
        fail("wfp", "country=COG", error, meta, "run1")
    assert not (tmp_path / "_meta" / "processed_files.jsonl").exists()
    assert meta.log_entries()[-1]["status"] == "failed"
