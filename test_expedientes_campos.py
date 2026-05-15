# -*- coding: utf-8 -*-
"""
Diagnóstico: imprime todos os campos retornados pelo endpoint de expedientes.
Uso: py test_expedientes_campos.py <id_processo>
Ex:  py test_expedientes_campos.py 12345678
"""
import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Uso: py test_expedientes_campos.py <id_processo>")
        sys.exit(1)

    id_processo = sys.argv[1]

    try:
        from Fix.variaveis import URL_PJE_BASE
        from Fix.core import criar_driver_PC
        from bianca.api_client import PjeApiClient, session_from_driver

        print(f"[TEST] Abrindo driver para {URL_PJE_BASE}...")
        driver = criar_driver_PC()
        driver.get(f"{URL_PJE_BASE}/processo/{id_processo}/detalhe")

        input("[TEST] Faça login se necessário, depois pressione Enter...")

        sess, base = session_from_driver(driver)
        client = PjeApiClient(sess, base)

        url = f"/pje-comum-api/api/processos/id/{id_processo}/expedientes"
        res = client.gateway_get(url, params={"pagina": 1, "tamanhoPagina": 10, "instancia": 1})

        if not res["ok"]:
            print(f"[TEST] ERRO: {res.get('error')}")
            driver.quit()
            sys.exit(1)

        resultado = (res["data"] or {}).get("resultado") or []
        print(f"\n[TEST] Total retornado na p1: {len(resultado)} itens")

        if resultado:
            print("\n--- TODOS OS CAMPOS DO PRIMEIRO EXPEDIENTE ---")
            for k, v in resultado[0].items():
                print(f"  {k!r}: {v!r}")

            print("\n--- TODOS OS CAMPOS DE CADA EXPEDIENTE (simplificado) ---")
            for i, exp in enumerate(resultado):
                nome = exp.get("nomePessoaParte", "??")
                campos_extra = {k: v for k, v in exp.items()
                                if k not in {"id", "nomePessoaParte", "tipoExpediente",
                                             "meioExpediente", "dataCriacao", "dataCiencia",
                                             "fimDoPrazoLegal", "prazoLegal", "fechado"}}
                print(f"\n  [{i}] {nome}")
                print(f"       meioExpediente={exp.get('meioExpediente')!r}")
                print(f"       fechado={exp.get('fechado')!r}")
                print(f"       dataCiencia={exp.get('dataCiencia')!r}")
                print(f"       CAMPOS EXTRAS: {json.dumps(campos_extra, ensure_ascii=False)}")
        else:
            print("[TEST] Nenhum expediente retornado.")

        driver.quit()

    except Exception as e:
        print(f"[TEST] Exceção: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
