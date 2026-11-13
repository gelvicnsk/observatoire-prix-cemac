"""Une source = une fonction qui renvoie des fichiers bruts (RawFile), sans rien écrire."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawFile:
    source: str  # wfp, world_bank, fx
    partitions: dict[str, str]  # ex. {"country": "COG"} ; ingest_date est ajouté par le pipeline
    content: bytes
    extension: str  # csv, json
    url: str
    context: dict[str, str] = field(default_factory=dict)

    @property
    def partition_key(self) -> str:
        return "/".join(f"{key}={value}" for key, value in self.partitions.items()) or "all"
