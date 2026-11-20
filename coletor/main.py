"""Coleta diária: Apple + Google Play → histórico cifrado → painel HTML.

Configuração por variáveis de ambiente (carregadas de credenciais/env). Ver README.md.
Uma loja sem variáveis configuradas é simplesmente pulada.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidTag

from coletor import apple, cofre, google_play, historico, painel

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "data" / "historico.enc"
SITE_PATH = ROOT / "site" / "index.html"


def window(days_back: int, today: date) -> list[str]:
    """Os últimos `days_back` dias até ontem, em ISO. Recoletar a janela cobre atrasos e ajustes das lojas."""
    return [(today - timedelta(days=i)).isoformat() for i in range(days_back, 0, -1)]


def _google_credentials(info: dict):
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/devstorage.read_only"]
    )


def main() -> int:
    env = os.environ
    password = env.get("PAINEL_SENHA", "")
    if not password.strip():
        # Sem esta checagem, uma variável vazia cifra tudo com senha vazia: qualquer um abre o arquivo.
        print("PAINEL_SENHA vazia ou ausente: defina uma senha forte em credenciais/env.")
        return 2
    # Confere a senha antes de coletar: senha errada falharia só no fim, depois de minutos de download.
    try:
        existing = historico.load(HISTORY_PATH, password)
    except InvalidTag:
        print(f"PAINEL_SENHA não abre {HISTORY_PATH.name}: a senha é outra.")
        return 2
    days = window(int(env.get("DAYS_BACK") or "7"), date.today())

    records = []
    replaced: set[tuple[str, str]] = set()
    failed: list[str] = []

    def run(label: str, store: str, collect) -> None:
        # Uma loja que falha não impede de salvar o que a outra trouxe; o histórico dela fica como estava.
        nonlocal records, replaced
        try:
            found, covered = collect()
        except Exception as exc:
            failed.append(label)
            print(f"{label}: FALHOU, nada dela foi atualizado. {type(exc).__name__}: {str(exc)[:300]}")
            return
        records += found
        replaced |= {(d, store) for d in covered}
        print(f"{label}: {len(covered)} dia(s) com relatório.")

    if env.get("ASC_KEY_ID"):
        run("Apple", "apple", lambda: apple.collect(
            env["ASC_KEY_ID"],
            env["ASC_ISSUER_ID"],
            env["ASC_PRIVATE_KEY"],
            env["ASC_VENDOR_NUMBER"],
            days,
        ))
    else:
        print("Apple: pulada (ASC_KEY_ID não configurado).")

    if env.get("GPLAY_BUCKET"):
        def google():
            info = json.loads(env["GOOGLE_SERVICE_ACCOUNT_JSON"])
            packages = [p.strip() for p in env["GPLAY_PACKAGES"].split(",") if p.strip()]
            return google_play.collect(
                _google_credentials(info), info["project_id"], env["GPLAY_BUCKET"], packages, days
            )

        run("Google", "google", google)
    else:
        print("Google: pulada (GPLAY_BUCKET não configurado).")

    # Logs de repositório público são públicos: só contagens, nunca valores.
    rows = historico.merge(existing, records, replaced)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    blob = cofre.encrypt(historico.payload(rows, updated_at), password)
    historico.save(HISTORY_PATH, blob)
    painel.build(blob, SITE_PATH)
    print(f"Histórico: {len(rows)} linhas. Painel gerado.")
    if failed:
        print(f"Atenção: {', '.join(failed)} falhou; rode de novo para completar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
