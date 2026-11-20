"""Cifrado y descifrado AES-256-GCM de credenciales con derivación PBKDF2HMAC-SHA256."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
MAGIC_HEADER = b"EZCRED01"


class CredentialCryptoError(Exception):
    """Error base al cifrar, descifrar o validar el almacén de credenciales."""


class CredentialIOError(CredentialCryptoError):
    """Error de entrada/salida o ruta inexistente al acceder al almacén cifrado."""


class CredentialIntegrityError(CredentialCryptoError):
    """Error de autenticación GCM (contraseña incorrecta) o formato/datos inválidos."""


def _derive_key(master_password: str, salt: bytes) -> bytes:
    if not master_password:
        raise CredentialCryptoError("La contraseña maestra no puede estar vacía.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(master_password.encode("utf-8"))


def encrypt_credentials(
    credentials: dict[str, dict[str, str]],
    master_password: str,
) -> bytes:
    """Cifra un diccionario de credenciales de servidores usando AES-256-GCM."""
    if not isinstance(credentials, dict) or not credentials:
        raise CredentialCryptoError("No hay credenciales válidas para cifrar.")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _derive_key(master_password, salt)
    payload = json.dumps(credentials, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, payload, MAGIC_HEADER)
    return MAGIC_HEADER + salt + nonce + ciphertext


def decrypt_credentials(
    blob: bytes,
    master_password: str,
) -> dict[str, dict[str, str]]:
    """Descifra y valida un payload binario generado por encrypt_credentials."""
    min_len = len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE + 16
    if len(blob) < min_len or not blob.startswith(MAGIC_HEADER):
        raise CredentialIntegrityError("Formato inválido o archivo credentials.enc corrupto.")

    offset = len(MAGIC_HEADER)
    salt = blob[offset : offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = blob[offset : offset + NONCE_SIZE]
    offset += NONCE_SIZE
    ciphertext = blob[offset:]

    key = _derive_key(master_password, salt)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, MAGIC_HEADER)
    except InvalidTag as exc:
        raise CredentialIntegrityError("Contraseña maestra incorrecta o archivo modificado.") from exc

    try:
        parsed: Any = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialIntegrityError("El contenido descifrado no es JSON válido.") from exc

    if not isinstance(parsed, dict):
        raise CredentialIntegrityError("Estructura de credenciales inválida.")

    normalized: dict[str, dict[str, str]] = {}
    for server_key, entry in parsed.items():
        if not isinstance(entry, dict):
            continue
        user = str(entry.get("username", "")).strip()
        pwd = str(entry.get("password", ""))
        if user and pwd:
            normalized[str(server_key)] = {"username": user, "password": pwd}

    if not normalized:
        raise CredentialIntegrityError("El archivo descifrado no contiene credenciales válidas.")

    return normalized


def save_encrypted_credentials(
    file_path: Path,
    credentials: dict[str, dict[str, str]],
    master_password: str,
) -> Path:
    """Cifra las credenciales y las guarda de forma segura en disco."""
    blob = encrypt_credentials(credentials, master_password)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    temp_path.write_bytes(blob)
    temp_path.replace(file_path)
    return file_path


def load_encrypted_credentials(
    file_path: Path | str,
    master_password: str,
) -> dict[str, dict[str, str]]:
    """Lee y descifra credentials.enc desde disco validando existencia previa."""
    resolved = Path(file_path)
    if not os.path.isfile(resolved):
        raise CredentialIOError(
            f"No se encontró el archivo cifrado: {resolved}"
        ) from FileNotFoundError(str(resolved))
    try:
        blob = resolved.read_bytes()
    except OSError as exc:
        raise CredentialIOError(f"Error de lectura/acceso en {resolved}: {exc}") from exc
    return decrypt_credentials(blob, master_password)
