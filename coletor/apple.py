"""App Store Connect — Sales Reports (relatório SALES/SUMMARY diário)."""

import csv
import gzip
import io
import time
from collections import defaultdict

import jwt
import requests

from coletor.models import Record

SALES_URL = "https://api.appstoreconnect.apple.com/v1/salesReports"

# Product Type Identifier de primeira instalação (iPhone/universal, iPad, Mac, iOS app no Mac).
DOWNLOAD_TYPES = {"1", "1F", "1T", "F1", "1E", "1EP", "1EU"}
# Product Type Identifier de atualização instalada (iPhone, universal, iPad, Mac).
UPDATE_TYPES = {"7", "7F", "7T", "F7"}

# Falhas passageiras (rede, limite de requisições, erro do servidor): espera e tenta de novo.
RETRY_WAITS = (5, 15, 30, 60, 120)  # segundos antes de cada nova tentativa
RETRY_STATUS = {429, 500, 502, 503, 504}


def make_token(key_id: str, issuer_id: str, private_key: str) -> str:
    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 15 * 60,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(
        payload, private_key, algorithm="ES256", headers={"kid": key_id, "typ": "JWT"}
    )


def fetch_day(token: str, vendor_number: str, day: str) -> str | None:
    """Baixa o TSV do dia. None quando a Apple responde 404 (sem vendas ou ainda não publicado)."""
    params = {
        "filter[frequency]": "DAILY",
        "filter[reportType]": "SALES",
        "filter[reportSubType]": "SUMMARY",
        "filter[vendorNumber]": vendor_number,
        "filter[reportDate]": day,
        "filter[version]": "1_1",
    }
    for wait in (*RETRY_WAITS, None):
        try:
            response = requests.get(
                SALES_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/a-gzip"},
                timeout=60,
            )
        except (requests.ConnectionError, requests.Timeout):
            if wait is None:
                raise
            problem = "falha de rede"
        else:
            if wait is None or response.status_code not in RETRY_STATUS:
                break
            problem = f"HTTP {response.status_code}"
        print(f"Apple: {problem}; nova tentativa em {wait} s.")
        time.sleep(wait)

    if response.status_code == 404:
        return None
    response.raise_for_status()
    return gzip.decompress(response.content).decode("utf-8")


def parse_sales(tsv: str, day: str) -> list[Record]:
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t"))

    # IAP/assinaturas apontam para o SKU do app pai; o título vem das linhas do próprio app.
    titles = {
        row["SKU"]: row["Title"]
        for row in rows
        if not (row.get("Parent Identifier") or "").strip()
    }

    downloads: dict[str, float] = defaultdict(float)
    updates: dict[str, float] = defaultdict(float)
    revenue: dict[tuple[str, str], float] = defaultdict(float)

    for row in rows:
        app_sku = (row.get("Parent Identifier") or "").strip() or row["SKU"]
        app = titles.get(app_sku, app_sku)
        units = float(row["Units"] or 0)
        product_type = row["Product Type Identifier"].strip()

        if product_type in DOWNLOAD_TYPES:
            downloads[app] += units
        elif product_type in UPDATE_TYPES:
            updates[app] += units

        proceeds = units * float(row["Developer Proceeds"] or 0)
        if proceeds:
            revenue[(app, row["Currency of Proceeds"])] += proceeds

    records = [Record(day, "apple", app, "downloads", value) for app, value in downloads.items()]
    records += [Record(day, "apple", app, "atualizacoes", value) for app, value in updates.items()]
    records += [
        Record(day, "apple", app, "receita", round(value, 2), currency)
        for (app, currency), value in revenue.items()
    ]
    return records


def collect(key_id: str, issuer_id: str, private_key: str, vendor_number: str, days: list[str]):
    """Retorna (registros, dias_com_relatório)."""
    records: list[Record] = []
    covered: list[str] = []
    for day in days:
        # Token novo a cada dia: ele vale 15 min, e uma coleta longa com retentativas passa disso.
        token = make_token(key_id, issuer_id, private_key)
        tsv = fetch_day(token, vendor_number, day)
        if tsv is None:
            continue
        records += parse_sales(tsv, day)
        covered.append(day)
    return records, covered
