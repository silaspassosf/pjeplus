# -*- coding: utf-8 -*-
"""Ponto de entrada do PJePlus, nos dois motores, com medicao comparavel.

Mesmo `x.py`, mesmos fluxos, mesma instrumentacao - so o motor muda. E isso que
permite comparar sem vies: qualquer diferenca no relatorio vem do backend, nao
de o teste ser diferente.

    py pw.py                     # Playwright (nativo ligado)
    py pw.py --selenium          # Selenium, para o baseline
    py pw.py --trace             # + trace.zip navegavel do Playwright
    py pw.py --sem-nativo        # so compatibilidade, sem helpers nativos
    py pw.py --comparar a.json b.json

Cada execucao grava um relatorio em play/medicoes/. Rodando o mesmo lote de
processos nos dois motores, `--comparar` separa o ganho do motor do ganho da
reescrita.
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

    selenium = "--selenium" in sys.argv
    trace = "--trace" in sys.argv
    backend = "selenium" if selenium else "playwright"

    if not selenium:
        import pjeplay
        pjeplay.iniciar(raiz_projeto=RAIZ, nativo="--sem-nativo" not in sys.argv)

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
    if trace and not selenium:
        import Fix.driver_factory as factory
        criar_original = factory.criar_driver_PC

        def criar_com_trace(*a, **kw):
            driver = criar_original(*a, **kw)
            if driver is not None:
                medicao.iniciar_trace(driver, rotulo)
                driver_visto.append(driver)
            return driver

        factory.criar_driver_PC = criar_com_trace

    cancelado = False
    with medicao.sessao(rotulo, backend=backend) as m:
        with m.etapa("execucao completa"):
            try:
                cancelado = x.main() == "cancelado"
            except KeyboardInterrupt:
                print("\ninterrompido - o relatorio parcial ainda vale")

    if trace and driver_visto:
        medicao.finalizar_trace(
            driver_visto[0], os.path.join(MEDICOES, f"{rotulo}.zip"))

    m.imprimir()
    destino = m.salvar(os.path.join(MEDICOES, f"{rotulo}.json"))
    print(f"\nrelatorio: {destino}")
    print(f"comparar:  py pw.py --comparar <baseline.json> {destino}")
    return CODIGO_SAIR if cancelado else 0


if __name__ == "__main__":
    sys.exit(main())
