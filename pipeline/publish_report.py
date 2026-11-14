"""Dépose le rapport Elementary dans le bucket des rapports : une copie datée et une copie « latest ».

    gs://<projet>-reports/elementary/2026-12-05/report.html
    gs://<projet>-reports/elementary/latest/report.html

Usage : python -m pipeline.publish_report /tmp/elementary_report.html   (variable REPORTS_BUCKET)
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path


def destinations(day: date) -> list[str]:
    return [f"elementary/{day.isoformat()}/report.html", "elementary/latest/report.html"]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage : python -m pipeline.publish_report <rapport.html>", file=sys.stderr)
        return 2
    bucket_name = os.environ.get("REPORTS_BUCKET")
    if not bucket_name:
        print("REPORTS_BUCKET manquant", file=sys.stderr)
        return 2

    from google.cloud import storage

    report = Path(args[0]).read_bytes()
    bucket = storage.Client(project=os.environ.get("GCP_PROJECT_ID")).bucket(bucket_name)
    for name in destinations(date.today()):
        bucket.blob(name).upload_from_string(report, content_type="text/html")
        print(f"rapport déposé : gs://{bucket_name}/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
