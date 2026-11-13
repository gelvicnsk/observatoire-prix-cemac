"""Test de bout en bout de l'inventaire, avec une API HDX simulée."""

from datetime import date
from pathlib import Path

import httpx

from ingestion.hdx import HdxClient
from scripts.profile_sources import main

FIXTURE = (Path(__file__).parent / "fixtures" / "wfp_sample.csv").read_bytes()


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("package_show"):
        name = request.url.params["id"]
        if name == "wfp-food-prices-for-congo":
            dataset = {
                "name": name,
                "title": "Congo - Food Prices",
                "resources": [{"name": "Congo - Food Prices", "format": "CSV", "url": "https://files/congo.csv"}],
            }
            return httpx.Response(200, json={"success": True, "result": dataset})
        return httpx.Response(404, json={"success": False})
    if request.url.path.endswith("package_search"):
        return httpx.Response(200, json={"success": True, "result": {"results": []}})
    return httpx.Response(200, content=FIXTURE)


def test_inventory_writes_profile_files(tmp_path):
    client = HdxClient(client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://hdx"), backoff_s=0)
    code = main(["--countries", "COG,GNQ", "--root", str(tmp_path)], client=client, today=date(2025, 6, 1))
    assert code == 0

    markdown = (tmp_path / "docs" / "data_profile.md").read_text(encoding="utf-8")
    assert "République du Congo (COG)" in markdown
    assert "Guinée équatoriale (GNQ)" in markdown
    assert "Aucun jeu de prix du PAM trouvé" in markdown
    assert (tmp_path / "data" / "profile" / "units.csv").read_text().startswith("unit,rows,countries")
    assert (tmp_path / "data" / "raw" / "inventory" / "COG" / "wfp" / "Congo_-_Food_Prices.csv").exists()


def test_unknown_country_code_is_refused(tmp_path):
    assert main(["--countries", "FRA", "--root", str(tmp_path)]) == 2
