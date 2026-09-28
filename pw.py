# -*- coding: utf-8 -*-
"""Ponto de entrada do PJePlus sobre Playwright nativo com medição.

    py pw.py                     # Playwright nativo
    py pw.py --seletores         # + monitor de assertividade de seletores e fallbacks
    py pw.py --trace             # + trace.zip navegavel do Playwright
    py pw.py --comparar a.json b.json

Cada execucao grava um relatorio em play/medicoes/.
"""
import os
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = AQUI  # pw.py esta na raiz do projeto
PLAY = os.path.join(AQUI, "play")  # motor pjeplay/ vive dentro de Play/
MEDICOES = os.path.join(PLAY, "medicoes")
CODIGO_SAIR = 88  # pw.bat encerra o laco automatico quando pw.py sai com este codigo
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

    trace = "--trace" in sys.argv
    backend = "playwright"

    import pjeplay
    pjeplay.iniciar(raiz_projeto=RAIZ, nativo=True)

    # Purga de progresso: remove de todos os fluxos os processos executados
    # ou com erro ha mais de 2 dias (ou sem data registrada). Nao bloqueia.
    # APOS pjeplay.iniciar(): nenhum import de Fix/* pode preceder o shim.
    try:
        from Fix.monitoramento_progresso_unificado import limpar_progresso_antigos
        resumo = limpar_progresso_antigos(dias=2)
        if resumo:
            total = sum(resumo.values())
            print(f"[progresso] purga: {total} entrada(s) antigas(s) removida(s) "
                  f"({', '.join(f'{k}={v}' for k, v in sorted(resumo.items()))})")
    except Exception as e:
        print(f"[progresso] aviso: purga falhou ({e})")

    os.chdir(RAIZ)  # x.py resolve caminhos relativos a raiz

    from pjeplay import medicao

    import x

    os.makedirs(MEDICOES, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    rotulo = f"{backend}-{marca}"

    driver_visto = []
    if trace:
        import Fix.driver_factory as factory
        criar_original = factory.criar_driver_PC

        def criar_com_trace(*a, **kw):
            driver = criar_original(*a, **kw)
            if driver is not None:
                medicao.iniciar_trace(driver, rotulo)
                driver_visto.append(driver)
            return driver

        factory.criar_driver_PC = criar_com_trace

    seletores = "--seletores" in sys.argv or "--monitor" in sys.argv
    monitor_sel = None
    if seletores:
        from pjeplay.monitor_seletores import MonitorSeletores
        monitor_sel = MonitorSeletores(raiz_projeto=RAIZ, verbose=True)
        monitor_sel.ativar()

    cancelado = False
    try:
        with medicao.sessao(rotulo, backend=backend) as m:
            with m.etapa("execucao completa"):
                try:
                    cancelado = x.main() == "cancelado"
                except KeyboardInterrupt:
                    print("\ninterrompido - o relatorio parcial ainda vale")
    finally:
        if monitor_sel:
            monitor_sel.desativar()

    if trace and driver_visto:
        medicao.finalizar_trace(
            driver_visto[0], os.path.join(MEDICOES, f"{rotulo}.zip"))

    m.imprimir()
    destino = m.salvar(os.path.join(MEDICOES, f"{rotulo}.json"))
    print(f"\nrelatorio: {destino}")
    if monitor_sel:
        monitor_sel.imprimir_resumo()
        destino_sel = monitor_sel.salvar(os.path.join(MEDICOES, f"seletores-{rotulo}.json"))
        print(f"relatorio seletores: {destino_sel}")
    print(f"comparar:  py pw.py --comparar <baseline.json> {destino}")
    return CODIGO_SAIR if cancelado else 0


if __name__ == "__main__":
    sys.exit(main())
