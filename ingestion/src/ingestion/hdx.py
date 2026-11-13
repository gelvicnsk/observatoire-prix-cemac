"""Client minimal pour l'API CKAN de HDX (Humanitarian Data Exchange).

Retrouve le jeu de données d'un pays, choisit sa ressource CSV principale et la télécharge
en calculant son empreinte sha256. Réutilisé par l'inventaire (étape 1) et l'ingestion (étape 4).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from ingestion.config import HDX_BASE_URL, HDX_COUNTRY_SLUGS, HTTP_USER_AGENT

Kind = Literal["wfp", "faostat"]

# Pour chaque type de jeu : préfixe de l'identifiant HDX et organisation éditrice attendue
_KIND_SLUG_PREFIX: dict[Kind, str] = {
    "wfp": "wfp-food-prices-for-",
    "faostat": "faostat-food-prices-for-",
}


@dataclass(frozen=True)
class HdxResource:
    dataset_name: str
    dataset_title: str
    resource_name: str
    url: str
    last_modified: str | None


@dataclass(frozen=True)
class Download:
    path: Path
    sha256: str
    size_bytes: int


class HdxClient:
    def __init__(self, client: httpx.Client | None = None, retries: int = 3, backoff_s: float = 2.0):
        self._client = client or httpx.Client(
            base_url=HDX_BASE_URL,
            headers={"User-Agent": HTTP_USER_AGENT},
            timeout=httpx.Timeout(60.0),
            follow_redirects=True,
        )
        self._retries = retries
        self._backoff_s = backoff_s

    # -- appels HTTP -------------------------------------------------------
    def _get(self, url: str, **params: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                response = self._client.get(url, params=params or None)
                if response.status_code == 404:
                    return response
                response.raise_for_status()
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                last_error = error
                if attempt < self._retries:
                    time.sleep(self._backoff_s * attempt)
        raise RuntimeError(f"Échec après {self._retries} tentatives : {url}") from last_error

    def package_show(self, name: str) -> dict | None:
        response = self._get("/api/3/action/package_show", id=name)
        if response.status_code == 404:
            return None
        payload = response.json()
        return payload["result"] if payload.get("success") else None

    def package_search(self, query: str, filter_query: str, rows: int = 20) -> list[dict]:
        response = self._get("/api/3/action/package_search", q=query, fq=filter_query, rows=str(rows))
        if response.status_code == 404:
            return []
        return response.json().get("result", {}).get("results", [])

    # -- logique métier ----------------------------------------------------
    def find_dataset(self, iso3: str, kind: Kind) -> dict | None:
        """Cherche d'abord par identifiant attendu, puis par groupe pays."""
        prefix = _KIND_SLUG_PREFIX[kind]
        slug = HDX_COUNTRY_SLUGS.get(iso3)
        if slug:
            dataset = self.package_show(prefix + slug)
            if dataset:
                return dataset

        candidates = self.package_search(
            query="food prices",
            filter_query=f"groups:{iso3.lower()}",
        )
        for dataset in candidates:
            if str(dataset.get("name", "")).startswith(prefix):
                return dataset
        return None

    @staticmethod
    def main_csv_resource(dataset: dict) -> HdxResource | None:
        """Ressource CSV principale : on écarte les fichiers QuickCharts et les médianes."""
        for resource in dataset.get("resources", []):
            fmt = str(resource.get("format", "")).lower()
            name = str(resource.get("name", ""))
            lowered = name.lower()
            if fmt != "csv" or "quickcharts" in lowered or "median" in lowered:
                continue
            return HdxResource(
                dataset_name=dataset.get("name", ""),
                dataset_title=dataset.get("title", ""),
                resource_name=name,
                url=resource["url"],
                last_modified=resource.get("last_modified"),
            )
        return None

    def download(self, url: str, destination: Path) -> Download:
        """Télécharge vers un fichier temporaire, puis le renomme : jamais de fichier à moitié écrit."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        digest = hashlib.sha256()
        size = 0
        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_bytes():
                    digest.update(chunk)
                    size += len(chunk)
                    handle.write(chunk)
        temporary.replace(destination)
        return Download(path=destination, sha256=digest.hexdigest(), size_bytes=size)

    def close(self) -> None:
        self._client.close()
