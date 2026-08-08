# -*- coding: utf-8 -*-
"""Ponto de entrada do PJePlus, nos dois motores, com medição comparável.

Mesmo `x.py`, mesmos fluxos, mesma instrumentação — só o motor muda. É isso que
permite comparar sem viés: qualquer diferença no relatório vem do backend, não
de o teste ser diferente.

    py pw.py                     # Playwright (nativo ligado)
    py pw.py --selenium          # Selenium, para o baseline
    py pw.py --trace             # + trace.zip navegável do Playwright
    py pw.py --sem-nativo        # só compatibilidade, sem helpers nativos
    py pw.py --comparar a.json b.json

Cada execução grava um relatório em play/medicoes/. Rodando o mesmo lote de
processos nos dois motores, `--comparar` separa o ganho do motor do ganho da
reescrita.
"""
import os
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = AQUI  # pw.py está na raiz do projeto
PLAY = os.path.join(AQUI, "play")  # motor pjeplay/ vive dentro de Play/
MEDICOES = os.path.join(PLAY, "medicoes")
for caminho in (AQUI, PLAY):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)


def _comparar(a, b):
    from pjeplay import medicao

    medicao.comparar(a, b)
    return 0


def main():
    if "--comparar" in sys.argv:
        i = sys.argv.index("--comparar")
        return _comparar(sys.argv[i + 1], sys.argv[i + 2])

    selenium = "--selenium" in sys.argv
    trace = "--trace" in sys.argv
    backend = "selenium" if selenium else "playwright"

    if not selenium:
        import pjeplay
        pjeplay.iniciar(raiz_projeto=RAIZ, nativo="--sem-nativo" not in sys.argv)

    os.chdir(RAIZ)  # x.py resolve caminhos relativos à raiz

    from pjeplay import medicao

    import x

    os.makedirs(MEDICOES, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    rotulo = f"{backend}-{marca}"

    driver_visto = []
    if trace and not selenium:
        import Fix.core as core
        criar_original = core.criar_driver_PC

        def criar_com_trace(*a, **kw):
            driver = criar_original(*a, **kw)
            if driver is not None:
                medicao.iniciar_trace(driver, rotulo)
                driver_visto.append(driver)
            return driver

        core.criar_driver_PC = criar_com_trace

    with medicao.sessao(rotulo, backend=backend) as m:
        with m.etapa("execucao completa"):
            try:
                x.main()
            except KeyboardInterrupt:
                print("\ninterrompido — o relatório parcial ainda vale")

    if trace and driver_visto:
        medicao.finalizar_trace(
            driver_visto[0], os.path.join(MEDICOES, f"{rotulo}.zip"))

    m.imprimir()
    destino = m.salvar(os.path.join(MEDICOES, f"{rotulo}.json"))
    print(f"\nrelatório: {destino}")
    print(f"comparar:  py pw.py --comparar <baseline.json> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
