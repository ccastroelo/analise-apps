from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    """Uma métrica diária agregada por loja/app/moeda."""

    date: str  # ISO yyyy-mm-dd
    store: str  # "apple" | "google"
    app: str
    metric: str  # "downloads" | "receita"
    value: float
    currency: str = ""  # só para receita
