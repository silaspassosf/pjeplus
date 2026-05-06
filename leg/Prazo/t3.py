"""
Teste rápido para `extrair_documento_relevante` (processo 7682583).

Uso:
  py Prazo/t3.py

Observações:
  - Requer `geckodriver`/chromedriver no PATH e uma sessão PJe válida no navegador.
  - O teste tenta abrir um browser interativo (não headless) para permitir login/cookies.
"""
import os
import sys
from pathlib import Path

# Ajustar sys.path para permitir execução do script tanto da raiz quanto da pasta `Prazo`
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from selenium import webdriver
import traceback

from Prazo.p2b_api import processar_processo_por_id_api

# Importar `criar_driver_e_logar` diretamente do arquivo para evitar executar
# `Triagem/__init__.py` que importa módulos pesados.
import importlib.util
triagem_driver_path = os.path.join(ROOT, 'Triagem', 'driver.py')
spec = importlib.util.spec_from_file_location('triagem_driver', triagem_driver_path)
triagem_driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triagem_driver)
criar_driver_e_logar = getattr(triagem_driver, 'criar_driver_e_logar')


def main():
    id_processo = 7682583

    driver = criar_driver_e_logar()
    if not driver:
        print('[TESTE][ERRO] Falha ao criar driver ou ao efetuar login (criar_driver_e_logar)')
        return

    try:
        print(f"Abrindo processo {id_processo} e executando pipeline de extração...")
        resultado = processar_processo_por_id_api(driver, id_processo)
        print("Resultado:")
        print(resultado)
    except Exception:
        print("Erro durante a execução do teste:")
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()
