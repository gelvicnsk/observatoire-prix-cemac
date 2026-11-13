"""Indicateurs nationaux annuels de la Banque mondiale (API Indicators v2), pour les 6 pays."""

from __future__ import annotations

import httpx

from ingestion.schemas import SchemaError, json_bytes
from ingestion.sources import RawFile

BASE_URL = "https://api.worldbank.org/v2"

# Inflation (prix à la consommation, % annuel) et population totale
INDICATORS: dict[str, str] = {
    "FP.CPI.TOTL.ZG": "inflation",
    "SP.POP.TOTL": "population",
}


def fetch_records(http: httpx.Client, countries: list[str], indicator: str) -> list[dict]:
    """Toutes les pages de l'indicateur pour ces pays."""
    url = f"{BASE_URL}/country/{';'.join(countries)}/indicator/{indicator}"
    records: list[dict] = []
    page, pages = 1, 1
    while page <= pages:
        response = http.get(url, params={"format": "json", "per_page": "1000", "page": str(page)})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
            raise SchemaError(f"réponse inattendue de la Banque mondiale pour {indicator} : {str(payload)[:200]}")
        pages = int(payload[0].get("pages") or 1)
        records.extend(payload[1] or [])
        page += 1
    return records


def fetch(http: httpx.Client, countries: list[str], indicator: str) -> RawFile:
    records = fetch_records(http, countries, indicator)
    # Tri stable : la même réponse donne toujours les mêmes octets, donc la même empreinte
    records.sort(key=lambda r: (r.get("countryiso3code") or "", r.get("date") or ""))
    return RawFile(
        source="world_bank",
        partitions={"indicator": indicator},
        content=json_bytes(records),
        extension="json",
        url=f"{BASE_URL}/country/{';'.join(countries)}/indicator/{indicator}",
    )
