"""Gera site/index.html com dados fictícios (senha: demo) para ver o painel sem credenciais.

Uso: python -m coletor.demo
"""

import math
import random
from datetime import date, timedelta

from coletor import cofre, historico, painel
from coletor.main import SITE_PATH

APPS = {
    ("apple", "Meu App"): 40,
    ("google", "br.com.exemplo.meuapp"): 90,
    ("apple", "Outro App"): 8,
    ("google", "br.com.exemplo.outro"): 15,
}


def main() -> None:
    rng = random.Random(42)
    rows = []
    today = date.today()
    for back in range(400, 0, -1):
        d = today - timedelta(days=back)
        season = 1 + 0.25 * math.sin(back / 9) + (0.3 if d.weekday() >= 5 else 0)
        for (store, app), base in APPS.items():
            downloads = max(0, round(base * season * rng.uniform(0.7, 1.3)))
            rows.append([d.isoformat(), store, app, "downloads", downloads, ""])
            if rng.random() < 0.45:
                rows.append([d.isoformat(), store, app, "receita", round(rng.uniform(5, 60), 2), "BRL"])
            if store == "apple" and rng.random() < 0.15:
                rows.append([d.isoformat(), store, app, "receita", round(rng.uniform(1, 10), 2), "USD"])
    blob = cofre.encrypt(historico.payload(rows, f"{today.isoformat()}T10:00Z"), "demo")
    painel.build(blob, SITE_PATH)
    print(f"Demo gerado em {SITE_PATH} (senha: demo)")


if __name__ == "__main__":
    main()
