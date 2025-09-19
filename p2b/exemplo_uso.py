"""
Exemplo de uso da arquitetura refatorada do P2B
Demonstra como usar os novos componentes modulares
"""

import sys
import os

# Adicionar o diretório pai ao path para importar o módulo p2b
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from p2b.core.p2b_engine import P2BEngine
from p2b.core.config import DEBUG_MODE


def exemplo_analise_timeline(driver):
    """
    Exemplo de como usar o analisador de timeline

    Args:
        driver: Instância do WebDriver (Selenium)
    """
    print("=== EXEMPLO: ANÁLISE DE TIMELINE ===")

    # Criar engine P2B
    engine = P2BEngine(debug=DEBUG_MODE)

    # Analisar timeline
    documentos = engine.analyze_timeline(driver)

    print(f"Documentos encontrados: {len(documentos)}")

    # Mostrar resumo por tipo
    tipos = {}
    for doc in documentos:
        tipo = doc.get('tipo', 'Desconhecido')
        tipos[tipo] = tipos.get(tipo, 0) + 1

    print("Resumo por tipo:")
    for tipo, count in tipos.items():
        print(f"  - {tipo}: {count}")

    return documentos


def exemplo_processamento_prescricao(driver, process_id=None):
    """
    Exemplo de como processar prescrição completa

    Args:
        driver: Instância do WebDriver (Selenium)
        process_id (str): ID do processo (opcional)
    """
    print("=== EXEMPLO: PROCESSAMENTO DE PRESCRIÇÃO ===")

    # Criar engine P2B
    engine = P2BEngine(debug=DEBUG_MODE)

    # Verificar se já foi executado
    if process_id and engine.is_process_already_executed(process_id):
        print(f"Processo {process_id} já foi executado anteriormente")
        return

    # Processar prescrição
    resultado = engine.process_prescription(driver, process_id)

    # Mostrar resultado
    print(f"Sucesso: {resultado['success']}")
    print(f"Documentos encontrados: {len(resultado['timeline_documents'])}")

    if resultado['errors']:
        print(f"Erros encontrados: {len(resultado['errors'])}")
        for error in resultado['errors']:
            print(f"  - {error}")

    return resultado


def exemplo_gestao_estado():
    """
    Exemplo de como usar o gerenciador de estado
    """
    print("=== EXEMPLO: GESTÃO DE ESTADO ===")

    # Criar engine P2B
    engine = P2BEngine(debug=DEBUG_MODE)

    # Obter estatísticas
    stats = engine.get_execution_statistics()
    print(f"Total executados: {stats['total_executados']}")
    print(f"Session ativa: {stats['session_active']}")

    # Listar processos executados
    executados = engine.list_executed_processes()

    return stats


def exemplo_reset_estado():
    """
    Exemplo de como resetar o estado
    """
    print("=== EXEMPLO: RESET DE ESTADO ===")

    # Criar engine P2B
    engine = P2BEngine(debug=DEBUG_MODE)

    # Resetar estado
    sucesso = engine.reset_execution_state()

    if sucesso:
        print("✅ Estado resetado com sucesso")
    else:
        print("❌ Falha ao resetar estado")

    return sucesso


# Função principal para demonstração
def demonstracao_completa():
    """
    Demonstração completa da nova arquitetura
    (Para uso real, descomente as chamadas que usam driver)
    """
    print("🚀 DEMONSTRAÇÃO: ARQUITETURA REFATORADA P2B")
    print("=" * 50)

    # Exemplo 1: Gestão de estado
    exemplo_gestao_estado()

    # Exemplo 2: Reset de estado (descomente se quiser testar)
    # exemplo_reset_estado()

    print("\nPara usar com WebDriver real:")
    print("1. driver = webdriver.Firefox()  # ou Chrome()")
    print("2. exemplo_analise_timeline(driver)")
    print("3. exemplo_processamento_prescricao(driver, 'processo_123')")

    print("\n✅ Demonstração concluída!")


if __name__ == "__main__":
    demonstracao_completa()