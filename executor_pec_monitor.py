# ====================================================================
# EXECUTOR PEC.PY COM MONITOR DE PERFORMANCE
# Permite executar o pec.py com monitoramento opcional
# ====================================================================

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Executor do pec.py com monitoramento opcional')
    parser.add_argument('--monitor', action='store_true',
                       help='Ativar monitoramento de performance')
    parser.add_argument('--teste-simples', action='store_true',
                       help='Executar apenas teste simples (sem driver)')

    args = parser.parse_args()

    print("="*80)
    print("🚀 EXECUTOR PEC.PY COM MONITOR DE PERFORMANCE")
    print("="*80)

    if args.monitor:
        print("📊 Modo: COM MONITORAMENTO DE PERFORMANCE")
    else:
        print("🔧 Modo: EXECUÇÃO NORMAL")

    if args.teste_simples:
        print("🧪 Tipo: TESTE SIMPLES (sem driver)")
        executar_teste_simples(args.monitor)
    else:
        print("🎯 Tipo: EXECUÇÃO COMPLETA")
        executar_pec_completo(args.monitor)

def executar_teste_simples(monitor_ativo):
    """Executa apenas funções simples do pec.py para teste"""
    print("\n🧪 EXECUTANDO TESTE SIMPLES...")

    try:
        # Importar pec.py
        import pec

        if monitor_ativo and pec.MONITOR_ATIVO:
            print("📊 Iniciando monitoramento...")
            pec.monitor.iniciar_monitoramento()
            pec.monitor.registrar_inicio_etapa("teste_simples")

        # Testar função simples
        observacao_teste = "DEF SOB - Sobreestamento"
        acao = pec.determinar_acao_por_observacao(observacao_teste)

        print(f"✅ Teste concluído!")
        print(f"   Observação: '{observacao_teste}'")
        print(f"   Ação: '{acao}'")

        if monitor_ativo and pec.MONITOR_ATIVO:
            pec.monitor.registrar_log_seletor("pec.py", "#timeline", True, f"Ação detectada: {acao}")
            pec.monitor.registrar_fim_etapa("teste_simples", sucesso=True)
            pec.monitor.finalizar_monitoramento()
            print("📄 Relatório de monitoramento gerado")

    except Exception as e:
        print(f"❌ Erro no teste simples: {e}")
        if monitor_ativo and pec.MONITOR_ATIVO:
            try:
                pec.monitor.registrar_fim_etapa("teste_simples", sucesso=False)
                pec.monitor.finalizar_monitoramento()
            except:
                pass

def executar_pec_completo(monitor_ativo):
    """Executa o pec.py completo"""
    print("\n🎯 EXECUTANDO PEC.PY COMPLETO...")

    try:
        import pec

        # Executar main com monitoramento se solicitado
        resultado = pec.main(monitor_performance=monitor_ativo)

        print("✅ Execução do pec.py concluída!")

    except Exception as e:
        print(f"❌ Erro na execução completa: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()