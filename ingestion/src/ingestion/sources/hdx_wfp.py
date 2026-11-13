"""Prix mensuels par marché du PAM (WFP), publiés sur HDX : un CSV par pays, historique complet."""

from __future__ import annotations

from ingestion.hdx import HdxClient
from ingestion.sources import RawFile


class DatasetNotFound(LookupError):
    pass


def fetch(client: HdxClient, iso3: str) -> RawFile:
    dataset = client.find_dataset(iso3, "wfp")
    if not dataset:
        raise DatasetNotFound(f"aucun jeu de prix du PAM sur HDX pour {iso3}")
    resource = client.main_csv_resource(dataset)
    if not resource:
        raise DatasetNotFound(f"jeu {dataset.get('name')} sans ressource CSV")
    return RawFile(
        source="wfp",
        partitions={"country": iso3},
        content=client.fetch_bytes(resource.url),
        extension="csv",
        url=resource.url,
        context={"dataset": resource.dataset_name, "resource_last_modified": resource.last_modified or ""},
    )
