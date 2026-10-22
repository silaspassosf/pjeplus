#!/usr/bin/env python3
"""tools/check_headless_layer.py — Testes de aceitação da Camada Headless.

Verifica:
1. Headless: Virtual clipboard intercepta cópias de página e supre pyperclip.paste()
   devolvendo o texto copiado e consumindo (sem vazar sentinela do SO);
2. Visível: Isolamento completo (modo visível não importa Play.pjeplay.headless);
3. Recovery: obter_driver_padronizado(headless=False) força headless=True sob a camada.

Uso:
  py tools/check_headless_layer.py
"""
import os
import subprocess
import sys
from pathlib import Path

# Ajustar encoding no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))


def test_1_headless_clipboard() -> bool:
    print("\n[TESTE 1] Headless: Virtual Clipboard Polyfill")
    from Play.pjeplay.launcher import criar_driver, finalizar_driver
    import pyperclip

    # Define sentinela no buffer do SO para garantir que headless NÃO o leia
    sentinela = "SENTINELA_DO_SISTEMA_BLOQUEADA"
    try:
        pyperclip.copy(sentinela)
    except Exception:
        pass

    driver = criar_driver(headless=True)
    if not driver:
        print("  [FALHA] Não foi possível instanciar driver headless.")
        return False

    try:
        html = (
            "data:text/html,"
            "<html><body>"
            "<button id='btn' onclick=\""
            "const t = document.createElement('textarea');"
            "t.value = '1000123-45.2026.5.02.0001';"
            "document.body.appendChild(t);"
            "t.select();"
            "document.execCommand('copy');"
            "document.body.removeChild(t);"
            "\">Copiar Processo</button>"
            "</body></html>"
        )
        driver.page.goto(html)
        driver.page.locator("#btn").click()

        texto_colado = pyperclip.paste()
        print(f"  Resultado pyperclip.paste(): '{texto_colado}'")

        if texto_colado != "1000123-45.2026.5.02.0001":
            print(f"  [FALHA] Esperado '1000123-45.2026.5.02.0001', recebido: '{texto_colado}'")
            return False

        # Segundo paste deve vir vazio (já consumido, sem vazar a sentinela do SO)
        segundo_paste = pyperclip.paste()
        print(f"  Segundo paste (consumo): '{segundo_paste}'")
        if segundo_paste != "":
            print(f"  [FALHA] Esperado vazio após consumo, recebido: '{segundo_paste}'")
            return False

        print("  [OK] Virtual clipboard operando perfeitamente em headless.")
        return True
    finally:
        finalizar_driver(driver)


def test_2_visivel_isolamento() -> bool:
    print("\n[TESTE 2] Modo Visível: Isolamento e Não-Invasão")
    # Executa em processo separado para testar importação limpa sem efeitos residuais
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "from Play.pjeplay import launcher; "
            "assert 'Play.pjeplay.headless' not in sys.modules, 'headless.py importado prematuramente'; "
            "print('ISOLADO_OK')"
        ),
    ]
    res = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
    if res.returncode == 0 and "ISOLADO_OK" in res.stdout:
        print("  [OK] Módulo Play.pjeplay.headless permanece não importado no modo padrão.")
        return True
    print(f"  [FALHA] Isolamento falhou:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
    return False


def test_3_recovery_headless() -> bool:
    print("\n[TESTE 3] Recovery Headless-Aware")
    from Play.pjeplay import headless
    from Play.pjeplay.launcher import criar_driver, finalizar_driver
    import Fix.utils as u

    driver = criar_driver(headless=True)
    if not driver:
        print("  [FALHA] Não foi possível instanciar driver.")
        return False

    drv_recovery = None
    try:
        # Garante camada ativa
        headless.ativar_para_driver(driver)

        # Simula a chamada que o recovery faz com headless=False
        drv_recovery = u.obter_driver_padronizado(headless=False)
        print(f"  Driver criado pelo recovery tem headless={drv_recovery.headless}")

        if not getattr(drv_recovery, "headless", False):
            print("  [FALHA] Driver do recovery não foi forçado para headless=True.")
            return False

        print("  [OK] Recovery interceptado e mantido em modo headless com sucesso.")
        return True
    finally:
        if drv_recovery:
            finalizar_driver(drv_recovery)
        finalizar_driver(driver)
        headless.desinstalar()


def main():
    print("=" * 70)
    print("TESTES DE ACEITAÇÃO: CAMADA HEADLESS PJEPLUS")
    print("=" * 70)

    sucessos = 0
    total = 3

    if test_2_visivel_isolamento():
        sucessos += 1

    if test_1_headless_clipboard():
        sucessos += 1

    if test_3_recovery_headless():
        sucessos += 1

    print("\n" + "=" * 70)
    print(f"RESULTADO: {sucessos}/{total} testes passaram.")
    print("=" * 70)

    if sucessos == total:
        print("[SUCESSO] Todos os critérios de aceitação foram atendidos!")
        sys.exit(0)
    else:
        print("[FALHA] Um ou mais testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
