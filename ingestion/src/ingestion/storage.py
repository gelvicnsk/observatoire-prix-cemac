"""Stockage des fichiers : local (développement, tests) ou Cloud Storage (dev, prod).

Les chemins sont déterministes (source, partition, date d'ingestion, empreinte) :
réécrire le même fichier produit exactement le même objet, ce qui rend l'écriture idempotente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def write_bytes(self, path: str, data: bytes, content_type: str) -> str:
        """Écrit l'objet et renvoie son URI complète."""

    def uri(self, path: str) -> str: ...


class LocalStore:
    def __init__(self, root: Path):
        self.root = root

    def uri(self, path: str) -> str:
        return str(self.root / path)

    def write_bytes(self, path: str, data: bytes, content_type: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".part")
        temporary.write_bytes(data)
        temporary.replace(target)
        return str(target)


class GcsStore:
    def __init__(self, bucket_name: str, project: str | None = None):
        from google.cloud import storage

        self.bucket_name = bucket_name
        self._bucket = storage.Client(project=project).bucket(bucket_name)

    def uri(self, path: str) -> str:
        return f"gs://{self.bucket_name}/{path}"

    def write_bytes(self, path: str, data: bytes, content_type: str) -> str:
        # Un objet Cloud Storage n'est visible qu'une fois entièrement écrit : pas de fichier partiel.
        self._bucket.blob(path).upload_from_string(data, content_type=content_type)
        return self.uri(path)
