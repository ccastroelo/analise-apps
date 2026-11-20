"""Google Play — relatórios do bucket do Play Console (pubsite_prod_...)."""

import csv
import io
import zipfile
from collections import defaultdict

from google.api_core.exceptions import NotFound
from google.cloud import storage

from coletor.models import Record

# Nomes de coluna mudaram ao longo dos anos; usa a primeira que existir.
INSTALL_COLUMNS = ("Daily User Installs", "Install events")
UPDATE_COLUMNS = ("Daily Device Upgrades", "Update events")


def decode_report(raw: bytes) -> str:
    # Os CSVs de stats vêm em UTF-16 com BOM; os de vendas, em UTF-8.
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def parse_installs(text: str, package: str, days: set[str]) -> list[Record]:
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    column = next(c for c in INSTALL_COLUMNS if c in fields)
    # Atualizações são opcionais: se o arquivo não tiver a coluna, só os downloads são lidos.
    update_column = next((c for c in UPDATE_COLUMNS if c in fields), None)
    records = []
    for row in reader:
        if row["Date"] not in days:
            continue
        records.append(Record(row["Date"], "google", package, "downloads", float(row[column] or 0)))
        if update_column:
            value = float(row[update_column] or 0)
            records.append(Record(row["Date"], "google", package, "atualizacoes", value))
    return records


def parse_sales(text: str, days: set[str]) -> list[Record]:
    """Valor bruto cobrado do cliente, na moeda da venda (não é o líquido do desenvolvedor)."""
    totals: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in csv.DictReader(io.StringIO(text)):
        day = row["Order Charged Date"]
        if day not in days or row["Financial Status"] != "Charged":
            continue
        amount = float(row["Charged Amount"].replace(",", "") or 0)
        totals[(day, row["Product ID"], row["Currency of Sale"])] += amount
    return [
        Record(day, "google", package, "receita", round(value, 2), currency)
        for (day, package, currency), value in totals.items()
    ]


def _download(bucket, name: str) -> bytes | None:
    try:
        return bucket.blob(name).download_as_bytes()
    except NotFound:
        return None


def collect(credentials, project: str, bucket_name: str, packages: list[str], days: list[str]):
    """Retorna (registros, dias_com_relatório)."""
    bucket = storage.Client(project=project, credentials=credentials).bucket(bucket_name)
    wanted = set(days)
    months = sorted({d[:4] + d[5:7] for d in days})
    records: list[Record] = []

    for month in months:
        for package in packages:
            raw = _download(bucket, f"stats/installs/installs_{package}_{month}_overview.csv")
            if raw is not None:
                records += parse_installs(decode_report(raw), package, wanted)

        raw = _download(bucket, f"sales/salesreport_{month}.zip")
        if raw is not None:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    records += parse_sales(decode_report(archive.read(name)), wanted)

    covered = sorted({r.date for r in records if r.metric == "downloads"})
    return records, covered
