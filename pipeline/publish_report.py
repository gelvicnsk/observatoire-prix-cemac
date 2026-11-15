"""Dépose un rapport HTML dans le bucket des rapports : une copie datée et une copie « latest ».

    gs://<projet>-reports/elementary/2026-12-05/report.html     rapport Elementary
    gs://<projet>-reports/dbt-docs/latest/report.html           documentation et lineage dbt

Usage : python -m pipeline.publish_report <fichier.html> [elementary|dbt-docs]   (variable REPORTS_BUCKET)
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

REPORTS = ("elementary", "dbt-docs")


def destinations(day: date, name: str = "elementary") -> list[str]:
    if name not in REPORTS:
        raise ValueError(f"rapport inconnu : {name}")
    return [f"{name}/{day.isoformat()}/report.html", f"{name}/latest/report.html"]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (1, 2) or (len(args) == 2 and args[1] not in REPORTS):
        print("usage : python -m pipeline.publish_report <rapport.html> [elementary|dbt-docs]", file=sys.stderr)
        return 2
    name = args[1] if len(args) == 2 else "elementary"
    bucket_name = os.environ.get("REPORTS_BUCKET")
    if not bucket_name:
        print("REPORTS_BUCKET manquant", file=sys.stderr)
        return 2

    from google.cloud import storage

    report = Path(args[0]).read_bytes()
    bucket = storage.Client(project=os.environ.get("GCP_PROJECT_ID")).bucket(bucket_name)
    for path in destinations(date.today(), name):
        bucket.blob(path).upload_from_string(report, content_type="text/html")
        print(f"rapport déposé : gs://{bucket_name}/{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
