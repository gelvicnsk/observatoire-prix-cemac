"""Taux de change EUR/USD mensuels de la Banque centrale européenne (moyenne du mois).

Le franc CFA (XAF) est à parité fixe avec l'euro (655,957 XAF = 1 EUR) : seule la série EUR/USD
est téléchargée ; la parité fixe est une constante du modèle dbt.
"""

from __future__ import annotations

import httpx

from ingestion.sources import RawFile

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"


def fetch(http: httpx.Client, start_period: str = "2000-01") -> RawFile:
    response = http.get(ECB_URL, params={"format": "csvdata", "startPeriod": start_period})
    response.raise_for_status()
    return RawFile(source="fx", partitions={}, content=response.content, extension="csv", url=str(response.url))
