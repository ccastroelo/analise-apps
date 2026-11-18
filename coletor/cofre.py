"""Criptografia compatível com WebCrypto: PBKDF2-SHA256 → AES-256-GCM.

O mesmo formato é lido em Python (histórico) e no navegador (painel).
"""

import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 600_000


def _key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(password.encode("utf-8"))


def encrypt(obj, password: str) -> dict:
    salt, iv = os.urandom(16), os.urandom(12)
    plain = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    data = AESGCM(_key(password, salt, ITERATIONS)).encrypt(iv, plain, None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return {"v": 1, "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "data": b64(data)}


def decrypt(blob: dict, password: str):
    raw = lambda k: base64.b64decode(blob[k])  # noqa: E731
    key = _key(password, raw("salt"), blob["iter"])
    return json.loads(AESGCM(key).decrypt(raw("iv"), raw("data"), None))
