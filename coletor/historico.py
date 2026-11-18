"""Histórico de métricas guardado cifrado em data/historico.enc.

Conteúdo decifrado: {"atualizado_em": str, "registros": [[data, loja, app, metrica, valor, moeda], ...]}
"""

import json
from pathlib import Path

from coletor import cofre
from coletor.models import Record


def load(path: Path, password: str) -> list[list]:
    if not path.exists():
        return []
    return cofre.decrypt(json.loads(path.read_text("utf-8")), password)["registros"]


def merge(existing: list[list], records: list[Record], replaced: set[tuple[str, str]]) -> list[list]:
    """Remove as linhas (data, loja) recoletadas e insere as novas, em ordem estável."""
    kept = [row for row in existing if (row[0], row[1]) not in replaced]
    fresh = [[r.date, r.store, r.app, r.metric, r.value, r.currency] for r in records]
    return sorted(kept + fresh, key=lambda row: (row[0], row[1], row[2], row[3], row[5]))


def payload(rows: list[list], updated_at: str) -> dict:
    return {"atualizado_em": updated_at, "registros": rows}


def save(path: Path, blob: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob), "utf-8")
