import gzip
import io
import json
from datetime import date

import pytest
import requests
from cryptography.exceptions import InvalidTag

from coletor import apple, cofre, google_play, historico, main
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
        apple_row("app.um", "App Um", "7", 50, 0, "BRL"),  # atualização: não é download
        apple_row("app.um", "App Um", "7T", 5, 0, "BRL"),
        apple_row("app.um.pro", "Pro", "IA1", 3, 4.5, "BRL", parent="app.um"),
        apple_row("app.um.pro", "Pro", "IA1", 1, 0.99, "USD", parent="app.um"),
    ])
    records = apple.parse_sales(tsv, "2026-11-17")

    assert Record("2026-11-17", "apple", "App Um", "downloads", 12) in records
    assert Record("2026-11-17", "apple", "App Um", "receita", 13.5, "BRL") in records
    assert Record("2026-11-17", "apple", "App Um", "receita", 0.99, "USD") in records
    assert Record("2026-11-17", "apple", "App Um", "atualizacoes", 55) in records
    assert len(records) == 4


def test_google_parse_installs_utf16_filtra_dias():
    csv_text = (
        "Date,Package Name,Daily Device Installs,Daily User Installs\n"
        "2026-11-15,br.app,5,4\n"
        "2026-11-16,br.app,7,6\n"
    )
    raw = csv_text.encode("utf-16")
    records = google_play.parse_installs(google_play.decode_report(raw), "br.app", {"2026-11-16"})
    assert records == [Record("2026-11-16", "google", "br.app", "downloads", 6.0)]  # sem coluna de atualização


def test_google_parse_installs_aceita_coluna_nova():
    csv_text = "Date,Package Name,Install events\n2026-11-16,br.app,9\n"
    records = google_play.parse_installs(csv_text, "br.app", {"2026-11-16"})
    assert records[0].value == 9.0


@pytest.mark.parametrize("column", ["Daily Device Upgrades", "Update events"])
def test_google_parse_installs_le_atualizacoes(column):
    csv_text = f"Date,Package Name,Daily User Installs,{column}\n2026-11-16,br.app,4,30\n"
    records = google_play.parse_installs(csv_text, "br.app", {"2026-11-16"})
    assert records == [
        Record("2026-11-16", "google", "br.app", "downloads", 4.0),
        Record("2026-11-16", "google", "br.app", "atualizacoes", 30.0),
    ]


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


class FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def fake_get(outcomes):
    """requests.get que devolve (ou lança) cada item de `outcomes`, em ordem."""
    calls = []

    def get(*args, **kwargs):
        outcome = outcomes[len(calls)]
        calls.append(outcome)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return get, calls


def test_apple_fetch_day_tenta_de_novo_em_falha_passageira(monkeypatch):
    get, calls = fake_get([
        requests.ConnectTimeout("timed out"),
        FakeResponse(429),
        FakeResponse(200, gzip.compress(b"ok")),
    ])
    monkeypatch.setattr(apple.requests, "get", get)
    monkeypatch.setattr(apple.time, "sleep", lambda s: None)
    assert apple.fetch_day("t", "v", "2026-11-17") == "ok"
    assert len(calls) == 3


def test_apple_fetch_day_desiste_depois_das_retentativas(monkeypatch):
    attempts = len(apple.RETRY_WAITS) + 1
    get, calls = fake_get([requests.ConnectTimeout("timed out")] * attempts)
    monkeypatch.setattr(apple.requests, "get", get)
    monkeypatch.setattr(apple.time, "sleep", lambda s: None)
    with pytest.raises(requests.ConnectTimeout):
        apple.fetch_day("t", "v", "2026-11-17")
    assert len(calls) == attempts


def test_apple_fetch_day_nao_repete_404_nem_403(monkeypatch):
    get, calls = fake_get([FakeResponse(404)])
    monkeypatch.setattr(apple.requests, "get", get)
    assert apple.fetch_day("t", "v", "2026-11-17") is None
    get, calls = fake_get([FakeResponse(403)])
    monkeypatch.setattr(apple.requests, "get", get)
    with pytest.raises(requests.HTTPError):
        apple.fetch_day("t", "v", "2026-11-17")
    assert len(calls) == 1


def test_main_salva_apple_mesmo_com_google_falhando(monkeypatch, tmp_path):
    env = {
        "PAINEL_SENHA": "s", "DAYS_BACK": "1",
        "ASC_KEY_ID": "k", "ASC_ISSUER_ID": "i", "ASC_PRIVATE_KEY": "p", "ASC_VENDOR_NUMBER": "v",
        "GPLAY_BUCKET": "b", "GPLAY_PACKAGES": "br.app",
        "GOOGLE_SERVICE_ACCOUNT_JSON": json.dumps({"project_id": "x"}),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(main, "HISTORY_PATH", tmp_path / "historico.enc")
    monkeypatch.setattr(main, "SITE_PATH", tmp_path / "index.html")
    monkeypatch.setattr(main, "_google_credentials", lambda info: None)

    day = window(1, date.today())[0]
    monkeypatch.setattr(apple, "collect", lambda *a: ([Record(day, "apple", "A", "downloads", 3)], [day]))

    def google_403(*args):
        raise RuntimeError("403 sem permissão")

    monkeypatch.setattr(google_play, "collect", google_403)

    assert main.main() == 1
    rows = historico.load(tmp_path / "historico.enc", "s")
    assert rows == [[day, "apple", "A", "downloads", 3, ""]]
    assert (tmp_path / "index.html").exists()


def _collect_must_not_run(*args):
    raise AssertionError("não devia coletar")


@pytest.mark.parametrize("password", ["", "   "])
def test_main_recusa_senha_vazia_antes_de_coletar(monkeypatch, tmp_path, password):
    monkeypatch.setenv("PAINEL_SENHA", password)
    monkeypatch.setenv("ASC_KEY_ID", "k")
    monkeypatch.setattr(main, "HISTORY_PATH", tmp_path / "historico.enc")
    monkeypatch.setattr(main, "SITE_PATH", tmp_path / "index.html")
    monkeypatch.setattr(apple, "collect", _collect_must_not_run)
    assert main.main() == 2
    assert not (tmp_path / "historico.enc").exists()


def test_main_recusa_senha_errada_antes_de_coletar(monkeypatch, tmp_path):
    path = tmp_path / "historico.enc"
    historico.save(path, cofre.encrypt(historico.payload([], "x"), "senha-certa"))
    monkeypatch.setenv("PAINEL_SENHA", "senha-errada")
    monkeypatch.setenv("ASC_KEY_ID", "k")
    monkeypatch.setattr(main, "HISTORY_PATH", path)
    monkeypatch.setattr(main, "SITE_PATH", tmp_path / "index.html")
    monkeypatch.setattr(apple, "collect", _collect_must_not_run)
    assert main.main() == 2
