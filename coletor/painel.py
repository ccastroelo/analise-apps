"""Gera o painel: o template com o blob cifrado embutido (um único HTML autocontido)."""

import json
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "painel" / "template.html"
PLACEHOLDER = "/*__DADOS__*/null"


def build(blob: dict, out_path: Path) -> None:
    html = TEMPLATE.read_text("utf-8")
    if PLACEHOLDER not in html:
        raise ValueError(f"placeholder {PLACEHOLDER!r} ausente em {TEMPLATE}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html.replace(PLACEHOLDER, json.dumps(blob)), "utf-8")
