"""Gera site/demo.html com dados fictícios (senha: demo) para ver o painel sem credenciais.

Uso: python -m coletor.demo
"""

import math
import random
from datetime import date, timedelta

from coletor import cofre, historico, painel
from coletor.main import SITE_PATH

# Arquivo separado: site/index.html é o painel real (e pode estar no iCloud).
DEMO_PATH = SITE_PATH.with_name("demo.html")

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
            updates = max(0, round(base * 3 * season * rng.uniform(0.5, 1.5)))
            rows.append([d.isoformat(), store, app, "atualizacoes", updates, ""])
            if rng.random() < 0.45:
                rows.append([d.isoformat(), store, app, "receita", round(rng.uniform(5, 60), 2), "BRL"])
            if store == "apple" and rng.random() < 0.15:
                rows.append([d.isoformat(), store, app, "receita", round(rng.uniform(1, 10), 2), "USD"])
    blob = cofre.encrypt(historico.payload(rows, f"{today.isoformat()}T10:00Z"), "demo")
    painel.build(blob, DEMO_PATH)
    print(f"Demo gerado em {DEMO_PATH} (senha: demo)")


if __name__ == "__main__":
    main()
