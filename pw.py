# -*- coding: utf-8 -*-
"""Ponto de entrada do PJePlus sobre Playwright nativo com medição."""
import os
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = AQUI
PLAY = os.path.join(AQUI, "play")
MEDICOES = os.path.join(PLAY, "medicoes")
CODIGO_SAIR = 88  # pw.bat encerra o laço automático quando pw.py sai com este código
for caminho in (AQUI, PLAY):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)


def _comparar(a, b):
    from pjeplay import medicao
    medicao.comparar(a, b)
    return 0


def _arg_valor(flag):
    argv = sys.argv
    if flag in argv:
        j = argv.index(flag)
        if j + 1 < len(argv):
            return argv[j + 1]
    return None


def _atalho_atualizacao_rapida():
    """Configura env vars para `--atualizacao-rapida <CNJ> [--calculo N] [--data dd/mm/aaaa]`."""
    cnj = _arg_valor("--atualizacao-rapida")
    if not cnj or cnj.startswith("--"):
        print("uso: py pw.py --atualizacao-rapida <CNJ> [--calculo N] [--data dd/mm/aaaa]")
        return 2
    os.environ["PJEPLUS_AR_PROCESSO"] = cnj
    for flag, env in (("--calculo", "PJEPLUS_AR_CALCULO"), ("--data", "PJEPLUS_AR_DATA")):
        val = _arg_valor(flag)
        if val:
            os.environ[env] = val
    os.environ["PJEPLUS_FLUXO"] = "K"
    os.environ.setdefault("PJEPLUS_DRIVER", "PC_HEADLESS")
    return 0


def main():
    if "--comparar" in sys.argv:
        i = sys.argv.index("--comparar")
        return _comparar(sys.argv[i + 1], sys.argv[i + 2])

    if "--atualizacao-rapida" in sys.argv:
        codigo = _atalho_atualizacao_rapida()
        if codigo:
            return codigo

    trace = "--trace" in sys.argv
    backend = "playwright"

    import pjeplay
    pjeplay.iniciar(raiz_projeto=RAIZ, nativo=True)

    # Purga após pjeplay.iniciar(): nenhum import de Fix/* pode preceder o bootstrap Playwright.
    try:
        from Fix.monitoramento_progresso_unificado import limpar_progresso_antigos
        resumo = limpar_progresso_antigos(dias=3)
        if resumo:
            det = ", ".join(f"{k}={v}" for k, v in sorted(resumo.items()))
            print(f"[progresso] purga: {sum(resumo.values())} entrada(s) removida(s) ({det})")
    except Exception as e:
        print(f"[progresso] aviso: purga falhou ({e})")

    os.chdir(RAIZ)

    from pjeplay import medicao
    import x

    os.makedirs(MEDICOES, exist_ok=True)
    rotulo = f"{backend}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

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

    monitor_sel = None
    if "--seletores" in sys.argv or "--monitor" in sys.argv:
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
        medicao.finalizar_trace(driver_visto[0], os.path.join(MEDICOES, f"{rotulo}.zip"))

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
