"""Fachada pública para el almacén cifrado de credenciales (AES-256-GCM)."""

from __future__ import annotations

from src.crypto_creds import (
    KEY_SIZE,
    MAGIC_HEADER,
    NONCE_SIZE,
    PBKDF2_ITERATIONS,
    SALT_SIZE,
    CredentialCryptoError,
    CredentialIntegrityError,
    CredentialIOError,
    decrypt_credentials,
    encrypt_credentials,
    load_encrypted_credentials,
    save_encrypted_credentials,
)

__all__ = [
    "CredentialCryptoError",
    "CredentialIOError",
    "CredentialIntegrityError",
    "KEY_SIZE",
    "MAGIC_HEADER",
    "NONCE_SIZE",
    "PBKDF2_ITERATIONS",
    "SALT_SIZE",
    "decrypt_credentials",
    "encrypt_credentials",
    "load_encrypted_credentials",
    "save_encrypted_credentials",
]
