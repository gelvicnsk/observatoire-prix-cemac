"""Run complet en mode local avec des sources simulées : premier run chargé, second run ignoré."""

from pathlib import Path

import httpx

from ingestion.hdx import HdxClient
from ingestion.main import main

FIXTURES = Path(__file__).parent / "fixtures"
WFP = b"\n".join(
    line
    for line in (FIXTURES / "wfp_sample.csv").read_bytes().splitlines()
    if b"abc" not in line and b"not-a-date" not in line
)

RAIN = (FIXTURES / "rainfall_sample.csv").read_bytes()


def hdx_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("package_show"):
        name = request.url.params["id"]
        if name == "wfp-food-prices-for-congo":
            dataset = {"name": name, "resources": [{"name": "Congo", "format": "CSV", "url": "https://files/c.csv"}]}
            return httpx.Response(200, json={"success": True, "result": dataset})
        if name in ("cog-rainfall-subnational", "gnq-rainfall-subnational"):
            resources = [
                {"name": f"{name[:3]}-rainfall-adm2-5ytd.csv", "format": "CSV", "url": "https://files/5ytd.csv"},
                {"name": f"{name[:3]}-rainfall-adm2-full.csv", "format": "CSV", "url": f"https://files/{name}.csv"},
            ]
            return httpx.Response(200, json={"success": True, "result": {"name": name, "resources": resources}})
        return httpx.Response(404, json={"success": False})
    if request.url.path.endswith("package_search"):
        return httpx.Response(200, json={"success": True, "result": {"results": []}})
    if "rainfall" in request.url.path:
        return httpx.Response(200, content=RAIN.replace(b"CG01", request.url.path[1:4].upper().encode()))
    if "5ytd" in request.url.path:
        raise AssertionError("seule la série complète doit être téléchargée")
    return httpx.Response(200, content=WFP)


def http_handler(request: httpx.Request) -> httpx.Response:
    if "worldbank" in request.url.host:
        return httpx.Response(200, content=(FIXTURES / "world_bank_sample.json").read_bytes())
    return httpx.Response(200, content=(FIXTURES / "ecb_sample.csv").read_bytes())


def clients():
    hdx = HdxClient(
        client=httpx.Client(transport=httpx.MockTransport(hdx_handler), base_url="https://hdx"), backoff_s=0
    )
    http = httpx.Client(transport=httpx.MockTransport(http_handler))
    return hdx, http


def test_local_run_then_rerun_is_idempotent(tmp_path, capsys):
    args = ["--target", "local", "--local-root", str(tmp_path), "--countries", "COG,GNQ", "--ingest-date", "2026-11-13"]
    hdx, http = clients()
    assert main(args, hdx=hdx, http=http) == 0
    first = capsys.readouterr().out
    assert "success  wfp" in first and "skipped  wfp" in first  # COG chargé, GNQ sans jeu de données
    assert "success  world_bank" in first and "success  fx" in first
    assert first.count("success  rainfall") == 2  # Congo et Guinée équatoriale

    hdx, http = clients()
    assert main(args, hdx=hdx, http=http) == 0
    second = capsys.readouterr().out
    assert "success" not in second
    # prix : 1 pays ; pluie : 2 pays ; Banque mondiale : 2 indicateurs ; change : 1 série
    assert len(list(tmp_path.rglob("*.parquet"))) == 6


def test_unknown_source_is_refused(tmp_path):
    assert main(["--sources", "meteo", "--local-root", str(tmp_path)]) == 2
