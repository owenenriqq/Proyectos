"""Utilidad CLI para generar o actualizar el archivo cifrado credentials.enc."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import sys

from src.config import AppConfig, ConfigError
from src.crypto_creds import (
    CredentialCryptoError,
    load_encrypted_credentials,
    save_encrypted_credentials,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera o actualiza credentials.enc con cifrado AES-256-GCM."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Ruta de salida opcional (por defecto usa local_paths.credentials_enc_file).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = AppConfig.load()
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    output_path: Path = args.output or config.get_default_credentials_enc_path()
    servers = config.get_servers()

    print("=== Gestor de Credenciales Cifradas EzSetup (AES-256-GCM) ===")
    print(f"Archivo destino: {output_path}\n")

    credentials: dict[str, dict[str, str]] = {}
    for server_key, info in servers.items():
        label = str(info.get("label", server_key))
        host = str(info.get("host", ""))
        hint = str(info.get("default_user_hint", "")).strip()

        print(f"--- {label} ({host}) ---")
        prompt_user = f"Usuario [{hint}]: " if hint else "Usuario: "
        entered_user = input(prompt_user).strip()
        username = entered_user or hint
        if not username:
            print("[INFO] Servidor omitido (usuario vacío).\n")
            continue

        password = getpass.getpass("Contraseña del servidor: ")
        if not password:
            print("[ERROR] La contraseña del servidor no puede estar vacía.", file=sys.stderr)
            return 1

        credentials[server_key] = {
            "username": username,
            "password": password,
        }
        print()

    if not credentials:
        print("[ERROR] No se ingresó ningún servidor válido. Operación cancelada.", file=sys.stderr)
        return 1

    master_1 = getpass.getpass("Contraseña Maestra de IT (para cifrar): ")
    master_2 = getpass.getpass("Confirmar Contraseña Maestra de IT: ")
    if not master_1:
        print("[ERROR] La contraseña maestra no puede estar vacía.", file=sys.stderr)
        return 1
    if master_1 != master_2:
        print("[ERROR] Las contraseñas maestras no coinciden.", file=sys.stderr)
        return 1

    try:
        saved_path = save_encrypted_credentials(output_path, credentials, master_1)
        verified = load_encrypted_credentials(saved_path, master_1)
    except CredentialCryptoError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(
        f"\n[OK] Archivo cifrado guardado y verificado: {saved_path} "
        f"({len(verified)} servidor(es) incluidos)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
