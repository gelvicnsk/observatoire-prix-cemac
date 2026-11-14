"""Étape 5B — rattache chaque marché du PAM à sa région et à son district (contours officiels COD-AB).

Le PAM donne pour chaque marché un nom et des coordonnées ; CHIRPS donne la pluie par code administratif
(pcode). Ce script fait le pont :

1. lit les marchés distincts de silver.stg_wfp__prices et les pcodes de silver.stg_chirps__rainfall_dekads ;
2. télécharge les contours COD-AB de chaque pays sur HDX (GeoJSON, mis en cache dans data/cod_ab/) ;
3. place chaque point dans son polygone (district puis région) ; à défaut, prend le district le plus proche
   à moins de 10 km ; sans coordonnées, tente le nom de district déclaré par le PAM ;
4. choisit le code pluie : le district s'il existe dans CHIRPS, sinon la région, sinon rien ;
5. met à jour dbt/seeds/market_district.csv (les lignes existantes ne sont pas modifiées, sauf --replace).

Chaque ligne indique la méthode utilisée et les points à relire (statut « a_verifier »).

Usage : python -m scripts.map_markets_to_districts [--project obs-cemac-dev-11259] [--replace]
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from scripts.seed_files import update_seed

SEED_PATH = Path("dbt/seeds/market_district.csv")
CACHE_DIR = Path("data/cod_ab")
MAX_DISTANCE_KM = 10.0
KM_PER_DEGREE = 111.32

COLUMNS = [
    "country_iso3",
    "market_name",
    "wfp_market_id",
    "latitude",
    "longitude",
    "adm1_pcode",
    "adm1_name",
    "adm2_pcode",
    "adm2_name",
    "method",
    "distance_km",
    "wfp_admin2_name",
    "name_matches",
    "shared_coordinates",
    "rainfall_pcode",
    "rainfall_admin_level",
    "status",
]


@dataclass(frozen=True)
class Market:
    country_iso3: str
    market_name: str
    wfp_market_id: str | None
    admin1_name: str | None
    admin2_name: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class Area:
    pcode: str
    name: str
    geometry: BaseGeometry


class Layer:
    """Un niveau administratif d'un pays, indexé pour les recherches spatiales."""

    def __init__(self, areas: list[Area]):
        self.areas = areas
        self._tree = STRtree([a.geometry for a in areas]) if areas else None
        self._by_name = {normalize(a.name): a for a in areas}

    def locate(self, point: Point) -> tuple[Area | None, str, float | None]:
        if self._tree is None:
            return None, "sans_contours", None
        hits = self._tree.query(point, predicate="intersects")
        if len(hits):
            return self.areas[int(sorted(hits)[0])], "point_in_polygon", 0.0
        nearest = int(self._tree.nearest(point))
        area = self.areas[nearest]
        distance = _distance_km(point, area.geometry)
        if distance <= MAX_DISTANCE_KM:
            return area, "nearest_polygon", distance
        return None, "hors_contours", distance

    def by_name(self, name: str | None) -> Area | None:
        return self._by_name.get(normalize(name)) if name else None


def normalize(text: str | None) -> str:
    """Nom comparable : sans accents, sans casse, sans ponctuation (« Pointe-Noire » == « pointe noire »)."""
    if not text:
        return ""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def _distance_km(point: Point, geometry: BaseGeometry) -> float:
    degrees = point.distance(geometry)
    return round(degrees * KM_PER_DEGREE * max(math.cos(math.radians(point.y)), 0.5), 2)


# --------------------------------------------------------------------------------------------------
# Contours COD-AB
# --------------------------------------------------------------------------------------------------


def _property(properties: dict, level: int, kinds: tuple[str, ...]) -> str | None:
    lowered = {k.lower(): v for k, v in properties.items()}
    for kind in kinds:
        value = lowered.get(f"adm{level}_{kind}")
        if value:
            return str(value)
    return None


def layers_from_geojson_zip(content: bytes) -> dict[int, Layer]:
    """Lit les niveaux 1 et 2 d'une archive GeoJSON COD-AB (noms de colonnes tolérés en majuscules)."""
    layers: dict[int, Layer] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for member in archive.namelist():
            name = member.lower()
            if not name.endswith(".geojson"):
                continue
            level = next((lvl for lvl in (1, 2) if re.search(rf"adm(in)?_?{lvl}(?!\d)", name)), None)
            if level is None or level in layers:
                continue
            features = json.loads(archive.read(member))["features"]
            areas = []
            for feature in features:
                props = feature.get("properties") or {}
                pcode = _property(props, level, ("pcode",))
                if pcode and feature.get("geometry"):
                    label = _property(props, level, ("name", "fr", "en", "name1", "ref")) or pcode
                    areas.append(Area(pcode, label, shape(feature["geometry"])))
            layers[level] = Layer(areas)
    return layers


def fetch_cod_ab(iso3: str, cache_dir: Path = CACHE_DIR, client=None) -> dict[int, Layer]:
    cached = cache_dir / f"{iso3.lower()}_admin_boundaries.geojson.zip"
    if not cached.exists():
        from ingestion.hdx import HdxClient

        hdx = client or HdxClient()
        dataset = hdx.package_show(f"cod-ab-{iso3.lower()}")
        if dataset is None:
            return {}
        resource = next((r for r in dataset.get("resources", []) if r.get("name", "").endswith(".geojson.zip")), None)
        if resource is None:
            return {}
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(hdx.fetch_bytes(resource["url"]))
    return layers_from_geojson_zip(cached.read_bytes())


# --------------------------------------------------------------------------------------------------
# Rattachement
# --------------------------------------------------------------------------------------------------


def match_markets(
    markets: list[Market], layers_by_country: dict[str, dict[int, Layer]], chirps_pcodes: set[tuple[str, str]]
) -> list[dict[str, object]]:
    coords = Counter(
        (m.country_iso3, round(m.latitude, 4), round(m.longitude, 4))
        for m in markets
        if m.latitude is not None and m.longitude is not None
    )
    rows = []
    for market in markets:
        layers = layers_by_country.get(market.country_iso3, {})
        adm1_layer, adm2_layer = layers.get(1, Layer([])), layers.get(2, Layer([]))
        has_coords = market.latitude is not None and market.longitude is not None
        adm1 = adm2 = None
        distance = None

        if not layers:
            method = "sans_contours"
        elif has_coords:
            point = Point(market.longitude, market.latitude)
            adm2, method, distance = adm2_layer.locate(point)
            adm1, _, _ = adm1_layer.locate(point)
        else:
            adm2 = adm2_layer.by_name(market.admin2_name)
            adm1 = adm1_layer.by_name(market.admin1_name)
            method = "nom_admin2" if adm2 else "sans_coordonnees"

        if adm2 is not None and adm1 is None:
            # le district porte le code de sa région en préfixe (CG0101 -> CG01)
            adm1 = next((a for a in adm1_layer.areas if adm2.pcode.startswith(a.pcode)), None)

        if adm2 is not None and (market.country_iso3, adm2.pcode) in chirps_pcodes:
            rainfall_pcode, rainfall_level = adm2.pcode, 2
        elif adm1 is not None and (market.country_iso3, adm1.pcode) in chirps_pcodes:
            rainfall_pcode, rainfall_level = adm1.pcode, 1
        else:
            rainfall_pcode, rainfall_level = None, None

        name_matches = bool(adm2) and normalize(adm2.name) == normalize(market.admin2_name)
        shared = has_coords and coords[(market.country_iso3, round(market.latitude, 4), round(market.longitude, 4))] > 1
        reliable = method == "point_in_polygon" and name_matches and not shared and rainfall_level == 2
        rows.append(
            {
                "country_iso3": market.country_iso3,
                "market_name": market.market_name,
                "wfp_market_id": market.wfp_market_id,
                "latitude": market.latitude,
                "longitude": market.longitude,
                "adm1_pcode": adm1.pcode if adm1 else None,
                "adm1_name": adm1.name if adm1 else None,
                "adm2_pcode": adm2.pcode if adm2 else None,
                "adm2_name": adm2.name if adm2 else None,
                "method": method,
                "distance_km": distance,
                "wfp_admin2_name": market.admin2_name,
                "name_matches": str(name_matches).lower(),
                "shared_coordinates": str(bool(shared)).lower(),
                "rainfall_pcode": rainfall_pcode,
                "rainfall_admin_level": rainfall_level,
                "status": "auto" if reliable else "a_verifier",
            }
        )
    return rows


# --------------------------------------------------------------------------------------------------
# BigQuery
# --------------------------------------------------------------------------------------------------

_MARKETS_SQL = """
select
    country_iso3,
    market_name,
    any_value(cast(wfp_market_id as string)) as wfp_market_id,
    any_value(admin1_name) as admin1_name,
    any_value(admin2_name) as admin2_name,
    array_agg(if(latitude is null or longitude is null, null, struct(latitude, longitude))
              ignore nulls order by price_date desc limit 1)[safe_offset(0)] as position
from silver.stg_wfp__prices
group by 1, 2
"""
_CHIRPS_SQL = "select distinct country_iso3, pcode from silver.stg_chirps__rainfall_dekads"


def read_bigquery(project: str) -> tuple[list[Market], set[tuple[str, str]]]:
    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    markets = [
        Market(
            row.country_iso3,
            row.market_name,
            row.wfp_market_id,
            row.admin1_name,
            row.admin2_name,
            row.position["latitude"] if row.position else None,
            row.position["longitude"] if row.position else None,
        )
        for row in client.query(_MARKETS_SQL).result()
    ]
    pcodes = {(row.country_iso3, row.pcode) for row in client.query(_CHIRPS_SQL).result()}
    return markets, pcodes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID"))
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--replace", action="store_true", help="régénère tout le seed (perd les corrections)")
    args = parser.parse_args(argv)
    if not args.project:
        parser.error("indiquer --project ou GCP_PROJECT_ID")

    markets, pcodes = read_bigquery(args.project)
    countries = sorted({m.country_iso3 for m in markets})
    layers = {iso3: fetch_cod_ab(iso3) for iso3 in countries}
    rows = match_markets(markets, layers, pcodes)

    if args.replace and args.seed.exists():
        args.seed.unlink()
    added = update_seed(args.seed, rows, ("country_iso3", "market_name"), COLUMNS)

    print(f"{len(markets)} marchés, {added} ajoutés au seed {args.seed}")
    headers = ("pays", "marchés", "polygone", "proche", "nom", "autre", "pluie adm2", "pluie adm1", "à relire")
    print(" ".join(f"{h:>10}" for h in headers))
    for iso3 in countries:
        part = [r for r in rows if r["country_iso3"] == iso3]
        methods = Counter(r["method"] for r in part)
        located = methods["point_in_polygon"] + methods["nearest_polygon"] + methods["nom_admin2"]
        levels = Counter(r["rainfall_admin_level"] for r in part)
        to_review = sum(r["status"] == "a_verifier" for r in part)
        values = (
            iso3,
            len(part),
            methods["point_in_polygon"],
            methods["nearest_polygon"],
            methods["nom_admin2"],
            len(part) - located,
            levels[2],
            levels[1],
            to_review,
        )
        print(" ".join(f"{v:>10}" for v in values))
    return 0


if __name__ == "__main__":
    sys.exit(main())
