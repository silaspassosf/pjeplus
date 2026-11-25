# -*- coding: utf-8 -*-
r"""Exporta e importa credenciais do PJePlus (Windows Credential Manager) em cofre AES-256-GCM.

Uso:
  py tools/cofre_credenciais.py exportar <caminho\cofre_pjeplus.enc>
      Le PJE_CPF, PJE_SENHA, PJE_TOTP_SECRET, SISB_CPF, SISB_SENHA e SISB_TOTP_SECRET
      do Windows Credential Manager, pede senha-mestra e grava arquivo criptografado (.enc).

  py tools/cofre_credenciais.py importar <caminho\cofre_pjeplus.enc>
      Descriptografa em memoria, grava todas as credenciais no Windows Credential Manager
      da maquina atual e cria automaticamente o atalho PJePlus_CDP_Lab.bat no Desktop.

  py tools/cofre_credenciais.py atalho
      Cria/atualiza apenas o atalho PJePlus_CDP_Lab.bat no Desktop apontando para este repo.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PBKDF2_ITERS = 600_000
COFRE_VERSAO = 1

# (servico_destino, chave_destino, servicos_busca, aliases_busca)
CREDENCIAIS_SPEC = [
    ("pjeplus", "PJE_CPF", ("pjeplus", "pje"), ("PJE_USER", "CPF", "PJE_SILAS", "SILAS")),
    ("pjeplus", "PJE_SENHA", ("pjeplus", "pje"), ("PJE_PASSWORD", "SENHA", "PASSWORD")),
    ("pjeplus", "PJE_TOTP_SECRET", ("pjeplus", "pje"), ("TOTP_SECRET", "PJE_OTP_SECRET", "OTP_SECRET")),
    ("sisbajud", "SISB_CPF", ("sisbajud", "SISB", "pjeplus"), ("BP_SISB",)),
    ("sisbajud", "SISB_SENHA", ("sisbajud", "SISB", "pjeplus"), ("BP_PASS",)),
    ("sisbajud", "SISB_TOTP_SECRET", ("sisbajud", "SISB", "pjeplus"), ("SISB_OTP_SECRET", "BP_TOTP")),
]


def _derivar_chave(senha_mestra: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERS,
    )
    return kdf.derive(senha_mestra.encode("utf-8"))


def _criptografar_payload(dados: dict[str, Any], senha_mestra: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(16)
    nonce = os.urandom(12)
    chave = _derivar_chave(senha_mestra, salt)
    plaintext = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(chave).encrypt(nonce, plaintext, b"pjeplus-cofre-v1")

    envelope = {
        "v": COFRE_VERSAO,
        "kdf": "pbkdf2_sha256",
        "iters": PBKDF2_ITERS,
        "alg": "aes_256_gcm",
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }
    return (json.dumps(envelope, indent=2) + "\n").encode("utf-8")


def _descriptografar_payload(raw: bytes, senha_mestra: str) -> dict[str, Any]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    envelope = json.loads(raw.decode("utf-8"))
    if envelope.get("v") != COFRE_VERSAO:
        raise ValueError(f"Versao de cofre nao suportada: {envelope.get('v')}")
    salt = base64.b64decode(envelope["salt"])
    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ct"])
    chave = _derivar_chave(senha_mestra, salt)
    plaintext = AESGCM(chave).decrypt(nonce, ciphertext, b"pjeplus-cofre-v1")
    return json.loads(plaintext.decode("utf-8"))


def _desktop_path() -> Path:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0 and buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Desktop"


def criar_atalho_desktop() -> Path:
    destino = _desktop_path() / "PJePlus_CDP_Lab.bat"
    conteudo = f"""@echo off
chcp 65001 >nul
title PJePlus - Laboratorio Firefox Dev Edition (porta 9222)
cd /d {RAIZ}

if /I "%~1"=="visivel" (
    echo ==============================================================
    echo   PJePlus - Firefox Dev Edition VISIVEL (+PJe + Tampermonkey)
    echo ==============================================================
    echo.
    py tools/cdp_lab.py abrir
) else (
    echo ==============================================================
    echo   PJePlus - Firefox Dev Edition HEADLESS (+PJe + Tampermonkey)
    echo   CPF/senha + TOTP automaticos (ou digite OTP se solicitado).
    echo ==============================================================
    echo.
    py tools/cdp_lab.py abrir --headless
)
set ERR=%ERRORLEVEL%

echo.
if "%ERR%"=="0" (
    echo [OK] Firefox Dev Edition pronto na porta 9222.
    timeout /t 4 >nul
) else (
    echo [AVISO] Encerrado com codigo %ERR%. Veja a mensagem acima.
    pause
)
"""
    destino.write_text(conteudo, encoding="utf-8", newline="\r\n")
    return destino


def cmd_exportar(args: argparse.Namespace) -> int:
    from Fix.sessao import obter_credencial

    coletadas: list[dict[str, str]] = []
    ausentes: list[str] = []
    for servico, chave, servicos_busca, aliases in CREDENCIAIS_SPEC:
        val = obter_credencial(chave, servicos=servicos_busca, aliases=aliases)
        if val:
            coletadas.append({"servico": servico, "chave": chave, "valor": val})
        else:
            ausentes.append(f"{servico}/{chave}")

    if not coletadas:
        print("ERRO: nenhuma credencial encontrada no Windows Credential Manager.")
        return 1

    print(f"[COFRE] Encontradas {len(coletadas)} credencial(is): " + ", ".join(f"{c['servico']}/{c['chave']}" for c in coletadas))
    if ausentes:
        print(f"[COFRE] Ausentes (nao exportadas): {', '.join(ausentes)}")

    s1 = getpass.getpass("Defina uma senha-mestra para o cofre: ")
    if len(s1) < 8:
        print("ERRO: use uma senha-mestra com pelo menos 8 caracteres.")
        return 1
    s2 = getpass.getpass("Confirme a senha-mestra: ")
    if s1 != s2:
        print("ERRO: senhas nao conferem.")
        return 1

    destino = Path(args.arquivo).expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    blob = _criptografar_payload({"credenciais": coletadas}, s1)
    destino.write_bytes(blob)
    print(f"[COFRE] Exportado com AES-256-GCM em: {destino}")
    print("[COFRE] Guarde esse arquivo fora do repo (Drive/pendrive/Bitwarden). Nunca commite no Git.")
    return 0


def cmd_importar(args: argparse.Namespace) -> int:
    import keyring
    from Fix.sessao import obter_totp_pje, obter_totp_sisbajud

    origem = Path(args.arquivo).expanduser().resolve()
    if not origem.is_file():
        print(f"ERRO: arquivo nao encontrado: {origem}")
        return 1

    senha = getpass.getpass("Digite a senha-mestra do cofre: ")
    try:
        dados = _descriptografar_payload(origem.read_bytes(), senha)
    except Exception:
        print("ERRO: senha-mestra incorreta ou arquivo corrompido.")
        return 1

    itens = dados.get("credenciais") or []
    if not itens:
        print("ERRO: cofre vazio.")
        return 1

    for item in itens:
        keyring.set_password(item["servico"], item["chave"], item["valor"])
        print(f"  [OK] {item['servico']}/{item['chave']} restaurado no Windows Credential Manager")

    p_ok = bool(obter_totp_pje())
    s_ok = bool(obter_totp_sisbajud())
    print(f"[COFRE] Verificacao TOTP: PJe={'OK' if p_ok else 'ausente'} | SISBAJUD={'OK' if s_ok else 'ausente'}")

    if not args.sem_atalho:
        atalho = criar_atalho_desktop()
        print(f"[COFRE] Atalho criado no Desktop: {atalho}")
    return 0


def cmd_atalho(args: argparse.Namespace) -> int:
    atalho = criar_atalho_desktop()
    print(f"[COFRE] Atalho criado/atualizado no Desktop: {atalho}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Cofre criptografado AES-256-GCM para migrar credenciais PJePlus")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_exp = sub.add_parser("exportar", help="Exporta credenciais do Windows Credential Manager para arquivo .enc")
    p_exp.add_argument("arquivo", help="Caminho de destino (ex.: C:\\Users\\Silas\\Desktop\\cofre_pjeplus.enc)")
    p_exp.set_defaults(func=cmd_exportar)

    p_imp = sub.add_parser("importar", help="Importa arquivo .enc para Windows Credential Manager + cria atalho Desktop")
    p_imp.add_argument("arquivo", help="Caminho do arquivo .enc")
    p_imp.add_argument("--sem-atalho", action="store_true", help="Nao cria PJePlus_CDP_Lab.bat no Desktop")
    p_imp.set_defaults(func=cmd_importar)

    p_at = sub.add_parser("atalho", help="Cria/atualiza apenas PJePlus_CDP_Lab.bat no Desktop")
    p_at.set_defaults(func=cmd_atalho)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
