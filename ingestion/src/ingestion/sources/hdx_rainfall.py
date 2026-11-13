"""Pluviométrie CHIRPS agrégée par district (admin2), publiée par le PAM sur HDX.

Un jeu par pays (« <iso3>-rainfall-subnational »), historique complet depuis 1981, par décade
(périodes de 10 jours), avec les moyennes de long terme et les anomalies déjà calculées.
"""

from __future__ import annotations

from ingestion.hdx import HdxClient
from ingestion.sources import RawFile
from ingestion.sources.hdx_wfp import DatasetNotFound


def dataset_name(iso3: str) -> str:
    return f"{iso3.lower()}-rainfall-subnational"


def full_series_resource(dataset: dict) -> dict | None:
    """La ressource « …-adm2-full.csv » (historique complet), pas l'extrait des 5 dernières années."""
    for resource in dataset.get("resources", []):
        name = str(resource.get("name", "")).lower()
        if str(resource.get("format", "")).lower() == "csv" and "full" in name:
            return resource
    return None


def fetch(client: HdxClient, iso3: str) -> RawFile:
    dataset = client.package_show(dataset_name(iso3))
    if not dataset:
        raise DatasetNotFound(f"aucun jeu de pluviométrie CHIRPS sur HDX pour {iso3}")
    resource = full_series_resource(dataset)
    if not resource:
        raise DatasetNotFound(f"jeu {dataset.get('name')} sans série complète en CSV")
    return RawFile(
        source="rainfall",
        partitions={"country": iso3},
        content=client.fetch_bytes(resource["url"]),
        extension="csv",
        url=resource["url"],
        context={"dataset": dataset.get("name", ""), "resource": resource.get("name", "")},
    )
