"""Rattachement des marchés aux districts (étape 5B), sur des contours fictifs."""

import io
import json
import zipfile

from scripts.map_markets_to_districts import Market, layers_from_geojson_zip, match_markets, normalize


def _square(x0, y0, size, props):
    ring = [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]
    return {"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring]}}


def _archive() -> bytes:
    admin1 = {
        "type": "FeatureCollection",
        "features": [
            _square(0, 0, 2, {"ADM1_PCODE": "CG01", "ADM1_FR": "Région A"}),
        ],
    }
    admin2 = {
        "type": "FeatureCollection",
        "features": [
            _square(0, 0, 1, {"adm2_pcode": "CG0101", "adm2_name": "Pointe-Noire"}),
            _square(1, 0, 1, {"adm2_pcode": "CG0102", "adm2_name": "Tchiamba"}),
        ],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("cog_admin1.geojson", json.dumps(admin1))
        archive.writestr("cog_admin2.geojson", json.dumps(admin2))
        archive.writestr("cog_admin0.geojson", json.dumps({"type": "FeatureCollection", "features": []}))
    return buffer.getvalue()


def _market(name, lat, lon, admin2="Pointe-Noire"):
    return Market("COG", name, None, "Région A", admin2, lat, lon)


def test_normalize_ignores_accents_case_and_punctuation():
    assert normalize("Pointe-Noire") == normalize("pointe noire") == "pointenoire"
    assert normalize("Bétou") == "betou"


def test_layers_are_read_with_any_column_case():
    layers = layers_from_geojson_zip(_archive())
    assert sorted(layers) == [1, 2]
    assert [a.pcode for a in layers[2].areas] == ["CG0101", "CG0102"]
    assert layers[1].areas[0].name == "Région A"


def test_match_markets_methods_and_rainfall_code():
    layers = {"COG": layers_from_geojson_zip(_archive())}
    markets = [
        _market("Dans le district", 0.5, 0.5),
        _market("Juste à côté", 0.5, -0.05),  # ~5,5 km à l'ouest du premier district
        _market("Très loin", 10.0, 10.0),
        _market("Sans coordonnées", None, None, admin2="Tchiamba"),
        _market("Même point", 0.5, 0.5),
    ]
    chirps = {("COG", "CG0101"), ("COG", "CG01")}

    rows = {r["market_name"]: r for r in match_markets(markets, layers, chirps)}

    inside = rows["Dans le district"]
    assert (inside["method"], inside["adm2_pcode"], inside["adm1_pcode"]) == ("point_in_polygon", "CG0101", "CG01")
    assert inside["rainfall_pcode"] == "CG0101" and inside["rainfall_admin_level"] == 2
    assert inside["name_matches"] == "true"
    assert inside["shared_coordinates"] == "true"  # partagé avec « Même point »
    assert inside["status"] == "a_verifier"

    near = rows["Juste à côté"]
    assert near["method"] == "nearest_polygon" and 0 < near["distance_km"] < 10

    assert rows["Très loin"]["method"] == "hors_contours"
    assert rows["Très loin"]["rainfall_pcode"] is None

    by_name = rows["Sans coordonnées"]
    assert (by_name["method"], by_name["adm2_pcode"]) == ("nom_admin2", "CG0102")
    # CG0102 absent de CHIRPS : on se replie sur la région
    assert by_name["rainfall_pcode"] == "CG01" and by_name["rainfall_admin_level"] == 1


def test_unique_reliable_market_is_auto():
    layers = {"COG": layers_from_geojson_zip(_archive())}
    rows = match_markets([_market("Seul", 0.5, 0.5)], layers, {("COG", "CG0101")})
    assert rows[0]["status"] == "auto"


def test_country_without_boundaries():
    rows = match_markets([Market("GAB", "Libreville", None, None, None, 0.4, 9.4)], {"GAB": {}}, set())
    assert rows[0]["method"] == "sans_contours"
    assert rows[0]["status"] == "a_verifier"


def test_overlapping_polygons_prefer_the_expected_name():
    admin2 = {
        "type": "FeatureCollection",
        "features": [
            _square(0, 0, 2, {"adm2_pcode": "TD0906", "adm2_name": "Monts de Lam"}),
            _square(1, 0, 2, {"adm2_pcode": "TD0801", "adm2_name": "Lac Wey"}),
        ],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("tcd_admin2.geojson", json.dumps(admin2))
    layers = {"TCD": layers_from_geojson_zip(buffer.getvalue())}
    market = Market("TCD", "Moundou", None, None, "Lac Wey", 0.5, 1.5)  # dans les deux carrés

    row = match_markets([market], layers, {("TCD", "TD0801")})[0]

    assert (row["method"], row["adm2_pcode"], row["name_matches"]) == ("polygones_superposes", "TD0801", "true")
    assert row["status"] == "a_verifier"
