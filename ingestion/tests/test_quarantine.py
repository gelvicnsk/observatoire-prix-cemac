"""Quarantaine des fichiers refusés, et rejeu (ADR-012)."""

from datetime import date
from pathlib import Path

import pytest

from ingestion.meta import LocalMeta
from ingestion.pipeline import process, quarantine, quarantine_path, raw_from_quarantine_path
from ingestion.replay import replay
from ingestion.sources import RawFile
from ingestion.storage import LocalStore

FIXTURE = (Path(__file__).parent / "fixtures" / "wfp_sample.csv").read_bytes()
VALID = b"\n".join(line for line in FIXTURE.splitlines() if b"abc" not in line and b"not-a-date" not in line)
DAY = date(2026, 11, 15)


def raw(content: bytes) -> RawFile:
    return RawFile(source="wfp", partitions={"country": "COG"}, content=content, extension="csv", url="https://x")


def _refused(store, meta):
    with pytest.raises(Exception) as error:  # noqa: PT011 - le contrat de colonnes refuse le fichier
        process(raw(FIXTURE), store, meta, DAY, "run1")
    return quarantine(raw(FIXTURE), error.value, store, meta, DAY, "run1")


def test_refused_file_is_kept_in_quarantine_and_logged(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    outcome = _refused(store, meta)

    assert outcome.status == "quarantined"
    kept = store.list("_quarantine/")
    assert kept == ["_quarantine/wfp/country=COG/ingest_date=2026-11-15/" + kept[0].rsplit("/", 1)[1]]
    assert store.read_bytes(kept[0]) == FIXTURE
    assert meta.log_entries()[-1]["status"] == "quarantined"
    assert "quarantaine=_quarantine/wfp/" in meta.log_entries()[-1]["message"]
    assert not (tmp_path / "_meta" / "processed_files.jsonl").exists()


def test_path_round_trip():
    path = quarantine_path(raw(VALID), DAY, "a" * 64)
    rebuilt = raw_from_quarantine_path(path, VALID)
    assert (rebuilt.source, rebuilt.partitions, rebuilt.extension) == ("wfp", {"country": "COG"}, "csv")


def test_replay_keeps_a_file_still_refused(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    _refused(store, meta)

    outcomes = replay(store, meta, "replay1", DAY)

    assert [o.status for o in outcomes] == ["quarantined"]
    assert len(store.list("_quarantine/")) == 1


def test_replay_releases_a_file_that_now_passes(tmp_path):
    store, meta = LocalStore(tmp_path), LocalMeta(tmp_path / "_meta")
    store.write_bytes(quarantine_path(raw(VALID), DAY, "b" * 64), VALID, "text/csv")

    outcomes = replay(store, meta, "replay1", date(2026, 12, 5))

    assert [o.status for o in outcomes] == ["success"]
    assert store.list("_quarantine/") == []
    assert len(list((tmp_path / "wfp").rglob("*.parquet"))) == 1
