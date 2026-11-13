"""Tests du client HDX avec une API simulée (aucun accès réseau)."""

import json

import httpx
import pytest

from ingestion.hdx import HdxClient

DATASET = {
    "name": "wfp-food-prices-for-congo",
    "title": "Congo - Food Prices",
    "resources": [
        {"name": "QuickCharts: Congo - Food Prices", "format": "CSV", "url": "https://x/qc.csv"},
        {"name": "Congo - Food Prices", "format": "CSV", "url": "https://x/main.csv", "last_modified": "2026-10-01"},
    ],
}


def make_client(handler) -> HdxClient:
    transport = httpx.MockTransport(handler)
    return HdxClient(client=httpx.Client(transport=transport, base_url="https://data.humdata.org"), backoff_s=0)


def test_find_dataset_by_expected_slug():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id"] == "wfp-food-prices-for-congo"
        return httpx.Response(200, json={"success": True, "result": DATASET})

    client = make_client(handler)
    assert client.find_dataset("COG", "wfp")["name"] == "wfp-food-prices-for-congo"


def test_fallback_to_search_when_slug_is_unknown():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("package_show"):
            return httpx.Response(404, json={"success": False})
        assert request.url.params["fq"] == "groups:caf"
        results = [{"name": "faostat-food-prices-for-car"}, {"name": "wfp-food-prices-for-car", "resources": []}]
        return httpx.Response(200, json={"success": True, "result": {"results": results}})

    client = make_client(handler)
    assert client.find_dataset("CAF", "wfp")["name"] == "wfp-food-prices-for-car"


def test_nothing_found_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("package_show"):
            return httpx.Response(404, json={"success": False})
        return httpx.Response(200, json={"success": True, "result": {"results": []}})

    assert make_client(handler).find_dataset("GNQ", "wfp") is None


def test_main_resource_skips_quickcharts():
    resource = HdxClient.main_csv_resource(DATASET)
    assert resource.url == "https://x/main.csv"


def test_download_writes_file_and_sha256(tmp_path):
    body = b"date,price\n2025-01-15,600\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    result = make_client(handler).download("https://x/main.csv", tmp_path / "a" / "file.csv")
    assert result.path.read_bytes() == body
    assert result.size_bytes == len(body)
    assert len(result.sha256) == 64
    assert not (tmp_path / "a" / "file.csv.part").exists()


def test_server_errors_are_retried_then_raised():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, content=json.dumps({}).encode())

    client = make_client(handler)
    with pytest.raises(RuntimeError):
        client.package_show("x")
    assert calls["n"] == 3
