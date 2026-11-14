from datetime import date

from pipeline.publish_report import destinations, main


def test_destinations_keep_a_dated_copy_and_latest():
    assert destinations(date(2026, 12, 5)) == ["elementary/2026-12-05/report.html", "elementary/latest/report.html"]


def test_main_refuses_without_bucket(monkeypatch, tmp_path):
    monkeypatch.delenv("REPORTS_BUCKET", raising=False)
    report = tmp_path / "r.html"
    report.write_text("<html></html>")
    assert main([str(report)]) == 2
    assert main([]) == 2
