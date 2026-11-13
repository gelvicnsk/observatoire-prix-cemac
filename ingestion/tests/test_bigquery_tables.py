"""Définition des tables externes bronze (aucun appel à BigQuery)."""

from ingestion.bigquery_tables import external_table_ddl


def test_wfp_external_table_uses_hive_partitions():
    ddl = external_table_ddl("proj", "bucket", "wfp")
    assert "create or replace external table `proj.bronze.wfp_prices`" in ddl
    assert "country STRING" in ddl and "ingest_date DATE" in ddl
    assert "uris = ['gs://bucket/wfp/*']" in ddl
    assert "hive_partition_uri_prefix = 'gs://bucket/wfp'" in ddl
    # Les originaux (_landing) ne sont jamais lus par la table
    assert "_landing" not in ddl


def test_fx_has_only_the_ingest_date_partition():
    assert "with partition columns (\n  ingest_date DATE\n)" in external_table_ddl("p", "b", "fx")
