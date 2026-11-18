import io
from datetime import date

import pytest
from cryptography.exceptions import InvalidTag

from coletor import apple, cofre, google_play, historico
from coletor.main import window
from coletor.models import Record

APPLE_HEADER = (
    "Provider\tProvider Country\tSKU\tDeveloper\tTitle\tVersion\tProduct Type Identifier\tUnits\t"
    "Developer Proceeds\tBegin Date\tEnd Date\tCustomer Currency\tCountry Code\tCurrency of Proceeds\t"
    "Apple Identifier\tCustomer Price\tPromo Code\tParent Identifier\tSubscription\tPeriod"
)


def apple_row(sku, title, ptype, units, proceeds, currency, parent=""):
    return "\t".join([
        "APPLE", "US", sku, "Eu", title, "1.0", ptype, str(units), str(proceeds),
        "11/17/2026", "11/17/2026", currency, "BR", currency, "123", "0", "", parent, "", "",
    ])


def test_apple_parse_sales_conta_downloads_e_receita_por_app():
    tsv = "\n".join([
        APPLE_HEADER,
        apple_row("app.um", "App Um", "1", 10, 0, "BRL"),
        apple_row("app.um", "App Um", "1F", 2, 0, "BRL"),
        apple_row("app.um", "App Um", "7", 50, 0, "BRL"),  # atualização: não conta
        apple_row("app.um.pro", "Pro", "IA1", 3, 4.5, "BRL", parent="app.um"),
        apple_row("app.um.pro", "Pro", "IA1", 1, 0.99, "USD", parent="app.um"),
    ])
    records = apple.parse_sales(tsv, "2026-11-17")

    assert Record("2026-11-17", "apple", "App Um", "downloads", 12) in records
    assert Record("2026-11-17", "apple", "App Um", "receita", 13.5, "BRL") in records
    assert Record("2026-11-17", "apple", "App Um", "receita", 0.99, "USD") in records
    assert len(records) == 3


def test_google_parse_installs_utf16_filtra_dias():
    csv_text = (
        "Date,Package Name,Daily Device Installs,Daily User Installs\n"
        "2026-11-15,br.app,5,4\n"
        "2026-11-16,br.app,7,6\n"
    )
    raw = csv_text.encode("utf-16")
    records = google_play.parse_installs(google_play.decode_report(raw), "br.app", {"2026-11-16"})
    assert records == [Record("2026-11-16", "google", "br.app", "downloads", 6.0)]


def test_google_parse_installs_aceita_coluna_nova():
    csv_text = "Date,Package Name,Install events\n2026-11-16,br.app,9\n"
    records = google_play.parse_installs(csv_text, "br.app", {"2026-11-16"})
    assert records[0].value == 9.0


def test_google_parse_sales_soma_so_cobrados():
    csv_text = (
        "Order Number,Order Charged Date,Financial Status,Product ID,Currency of Sale,Charged Amount\n"
        "1,2026-11-16,Charged,br.app,BRL,\"1,000.50\"\n"
        "2,2026-11-16,Charged,br.app,BRL,9.50\n"
        "3,2026-11-16,Cancelled,br.app,BRL,9.50\n"
        "4,2026-11-10,Charged,br.app,BRL,5.00\n"
    )
    records = google_play.parse_sales(csv_text, {"2026-11-16"})
    assert records == [Record("2026-11-16", "google", "br.app", "receita", 1010.0, "BRL")]


def test_historico_merge_substitui_so_dias_recoletados():
    existing = [
        ["2026-11-15", "apple", "A", "downloads", 1, ""],
        ["2026-11-16", "apple", "A", "downloads", 2, ""],
        ["2026-11-16", "google", "B", "downloads", 3, ""],
    ]
    new = [Record("2026-11-16", "apple", "A", "downloads", 20)]
    rows = historico.merge(existing, new, {("2026-11-16", "apple")})
    assert rows == [
        ["2026-11-15", "apple", "A", "downloads", 1, ""],
        ["2026-11-16", "apple", "A", "downloads", 20, ""],
        ["2026-11-16", "google", "B", "downloads", 3, ""],
    ]


def test_cofre_ida_e_volta_e_senha_errada():
    blob = cofre.encrypt({"x": [1, "ç"]}, "senha-boa")
    assert cofre.decrypt(blob, "senha-boa") == {"x": [1, "ç"]}
    with pytest.raises(InvalidTag):
        cofre.decrypt(blob, "senha-ruim")


def test_window_termina_ontem():
    assert window(3, date(2026, 11, 18)) == ["2026-11-15", "2026-11-16", "2026-11-17"]
