# ====================================================================
# TESTE PEC.PY COM MONITOR ATIVO - VERSÃO SIMPLES
# Executa apenas funções específicas do pec.py com monitoramento
# ====================================================================

import sys
import os
import time
from datetime import datetime

# Adicionar o diretório atual ao path para importar pec.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar o monitor de performance
from monitor import monitor

def executar_pec_funcao_simples_com_monitor():
    """
    Executa apenas uma função simples do pec.py com monitoramento
    """

    print("="*80)
    print("📊 TESTE SIMPLES: PEC.PY COM MONITOR DE PERFORMANCE")
    print("="*80)

    # 1. INICIAR MONITORAMENTO
    print("\n📈 Iniciando monitoramento de performance...")
    monitor.iniciar_monitoramento()

    try:
        # 2. IMPORTAR PEC.PY
        print("🔧 Importando pec.py...")
        monitor.registrar_inicio_etapa("import_pec")

        import pec
        monitor.registrar_fim_etapa("import_pec", sucesso=True)

        # 3. TESTAR FUNÇÃO SIMPLES (sem driver)
        print("🧪 Testando função determinar_acao_por_observacao...")
        monitor.registrar_inicio_etapa("teste_funcao_simples")

        # Testar função que não precisa de driver
        observacao_teste = "DEF SOB - Sobreestamento"
        acao = pec.determinar_acao_por_observacao(observacao_teste)

        print(f"   Observação: '{observacao_teste}'")
        print(f"   Ação determinada: '{acao}'")

        monitor.registrar_fim_etapa("teste_funcao_simples", sucesso=True)

        # 4. REGISTRAR LOGS DE EXEMPLO
        print("📝 Registrando logs de exemplo...")
        monitor.registrar_log_seletor("pec.py", "#btn-sob", True, f"Ação SOB detectada: {acao}")
        monitor.registrar_log_seletor("pec.py", "#timeline", True, "Timeline analisada com sucesso")
        monitor.registrar_log_seletor("pec.py", "#btn-invalido", False, "Botão não encontrado (teste)")

        # 5. FINALIZAR MONITORAMENTO
        print("🔚 Finalizando monitoramento...")
        monitor.finalizar_monitoramento()

        print("\n✅ Teste concluído com sucesso!")
        print("📄 Verifique o relatório EXECUCAO_TOTAL gerado")

    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

        # Registrar falha no monitor
        try:
            monitor.registrar_fim_etapa("teste_funcao_simples", sucesso=False)
            monitor.finalizar_monitoramento()
        except:
            pass

        raise

if __name__ == "__main__":
    executar_pec_funcao_simples_com_monitor()