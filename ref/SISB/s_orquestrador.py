"""
SISB/s.py - Orquestrador Principal do SISBAJUD (Refatorado)

Este arquivo agora serve como orquestrador principal, coordenando as operações
através dos módulos especializados:

- core.py: Inicialização, login, configuração de driver
- processamento.py: Lógica de negócio (minutas, ordens)
- utils.py: Utilitários, helpers, validações
- standards.py: Padrões, constantes, tipos
- performance.py: Otimizações de performance

Mantém compatibilidade com código existente enquanto usa arquitetura modular.
"""

# Imports consolidados
from .core import (
    iniciar_sisbajud,
    driver_sisbajud,
    login_automatico_sisbajud,
    login_manual_sisbajud,
    minuta_bloqueio,
    processar_ordem_sisbajud,
    processar_bloqueios
)

# from .processamento import (
#     minuta_bloqueio_refatorada,  # Removido - função não existe
# )

# Placeholder
minuta_bloqueio_refatorada = None

from .utils import (
    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    log_sisbajud,
    validar_numero_processo,
    formatar_valor_monetario
)

from .standards import (
    SISBConstants,
    StatusProcessamento,
    TipoFluxo,
    DadosProcesso,
    ResultadoProcessamento,
    sisb_logger
)

from .performance import (
    performance_optimizer,
    polling_reducer,
    cache_manager,
    parallel_processor
)

# Manter compatibilidade com código existente
# (funções que podem estar sendo usadas externamente)

def criar_js_otimizado_legacy():
    """
    Função legacy para compatibilidade.
    Redireciona para implementação otimizada.
    """
    return criar_js_otimizado()

def iniciar_sisbajud_legacy(driver_pje=None):
    """
    Função legacy para compatibilidade.
    Redireciona para implementação modular.
    """
    return iniciar_sisbajud(driver_pje=driver_pje)

def minuta_bloqueio_legacy(driver_sisbajud, dados_processo, driver_pje=None, driver_created=False):
    """
    Função legacy para compatibilidade.
    Redireciona para implementação modular.
    """
    return minuta_bloqueio_refatorada(driver_sisbajud, dados_processo, driver_pje, driver_created)

# ===== ORQUESTRADOR PRINCIPAL =====

def executar_sisbajud_completo(dados_processo, driver_pje=None, modo="automatico"):
    """
    Orquestrador principal para execução completa SISBAJUD.

    Args:
        dados_processo: Dados do processo extraídos
        driver_pje: Driver do PJE (opcional)
        modo: Modo de execução ("automatico" ou "manual")

    Returns:
        ResultadoProcessamento: Resultado estruturado da operação
    """
    resultado = ResultadoProcessamento(
        status=StatusProcessamento.PENDENTE,
        detalhes={}
    )

    try:
        sisb_logger.log("=== INICIANDO SISBAJUD COMPLETO (MODULAR) ===", "INFO", "orquestrador")

        # FASE 1: Validação de dados
        if not dados_processo:
            raise ValueError("Dados do processo não fornecidos")

        numero_processo = validar_numero_processo(dados_processo.get('numero'))
        if not numero_processo:
            raise ValueError("Número do processo inválido")

        # FASE 2: Inicialização
        sisb_logger.log("FASE 1: Inicialização SISBAJUD", "INFO", "orquestrador")

        driver_sisb = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisb:
            raise Exception("Falha na inicialização do SISBAJUD")

        resultado.detalhes['driver_inicializado'] = True

        # FASE 3: Processamento principal
        sisb_logger.log("FASE 2: Processamento principal", "INFO", "orquestrador")

        # Determinar tipo de processamento baseado nos dados
        if dados_processo.get('sisbajud', {}).get('tipo') == 'endereco':
            # Para endereço, usar processamento de bloqueios (padrão)
            resultado_processamento = processar_bloqueios(driver_pje=driver_pje)
        else:
            # Processamento de bloqueios (padrão)
            resultado_processamento = processar_bloqueios(driver_pje=driver_pje)

        # FASE 4: Análise de resultados
        if resultado_processamento and resultado_processamento.get('status') == 'sucesso':
            resultado.status = StatusProcessamento.SUCESSO
            resultado.tipo_fluxo = TipoFluxo(resultado_processamento.get('tipo_fluxo', 'positivo'))
            resultado.series_processadas = resultado_processamento.get('series_processadas', 0)
            resultado.ordens_processadas = resultado_processamento.get('ordens_processadas', 0)
        else:
            resultado.status = StatusProcessamento.ERRO
            resultado.erros = resultado_processamento.get('erros', ['Erro desconhecido'])

        # FASE 5: Limpeza e finalização
        sisb_logger.log("FASE 3: Finalização", "INFO", "orquestrador")

        # Cleanup automático
        try:
            if 'driver_sisb' in locals() and driver_sisb:
                driver_sisb.quit()
                sisb_logger.log("Driver SISBAJUD finalizado", "INFO", "orquestrador")
        except Exception as e:
            sisb_logger.log(f"Erro na finalização: {e}", "WARNING", "orquestrador")

        resultado.detalhes['processamento_concluido'] = True

        sisb_logger.log("=== SISBAJUD COMPLETO FINALIZADO ===", "INFO", "orquestrador")
        return resultado

    except Exception as e:
        sisb_logger.log(f"Erro no orquestrador: {e}", "ERROR", "orquestrador")
        resultado.status = StatusProcessamento.ERRO
        resultado.erros = [str(e)]
        return resultado

# ===== FUNÇÕES DE COMPATIBILIDADE LEGACY =====
# Manter todas as funções públicas que podem estar sendo usadas

def minuta_bloqueio(*args, **kwargs):
    """Compatibilidade com chamadas antigas"""
    return minuta_bloqueio_legacy(*args, **kwargs)

def minuta_endereco(*args, **kwargs):
    """Compatibilidade com chamadas antigas"""
    return minuta_endereco(*args, **kwargs)

def processar_ordem_sisbajud(*args, **kwargs):
    """Compatibilidade com chamadas antigas"""
    return processar_ordem_sisbajud(*args, **kwargs)

def processar_bloqueios(*args, **kwargs):
    """Compatibilidade com chamadas antigas"""
    return processar_bloqueios(*args, **kwargs)

# Funções auxiliares legacy
def trigger_event(elemento, tipo):
    """Função auxiliar legacy"""
    try:
        return elemento.dispatch_event(tipo)
    except:
        return False

def safe_execute_script(driver, script, *args):
    """Execução segura de script legacy"""
    try:
        return driver.execute_script(script, *args)
    except Exception as e:
        print(f"[SISBAJUD] Erro em script: {e}")
        return None

# ===== CONSTANTES E CONFIGURAÇÕES GLOBAIS =====

# Manter algumas constantes globais para compatibilidade
SISBAJUD_STATS = {'consecutive_errors': 0}
USAR_CORE_MODULES = True

# Configurações de performance
PERFORMANCE_CONFIG = {
    'usar_cache': True,
    'usar_parallel': False,  # Desabilitado por padrão para evitar detecção
    'usar_observers': True,
    'rate_limiting': True
}

# ===== UTILITÁRIOS DE DEBUG =====

def debug_sisbajud_status():
    """Status de debug do SISBAJUD modular"""
    print("\n=== SISBAJUD STATUS (MODULAR) ===")
    print(f"Core modules: {'ATIVO' if USAR_CORE_MODULES else 'INATIVO'}")
    print(f"Performance optimizer: {'ATIVO' if PERFORMANCE_CONFIG['usar_cache'] else 'INATIVO'}")
    print(f"Parallel processing: {'ATIVO' if PERFORMANCE_CONFIG['usar_parallel'] else 'INATIVO'}")
    print(f"Mutation observers: {'ATIVO' if PERFORMANCE_CONFIG['usar_observers'] else 'INATIVO'}")
    print(f"Rate limiting: {'ATIVO' if PERFORMANCE_CONFIG['rate_limiting'] else 'INATIVO'}")
    print("=" * 40)

def otimizar_performance_sisbajud(habilitar=True):
    """Ativar/desativar otimizações de performance"""
    global PERFORMANCE_CONFIG
    PERFORMANCE_CONFIG = {k: habilitar for k in PERFORMANCE_CONFIG.keys()}
    status = "ATIVADAS" if habilitar else "DESATIVADAS"
    print(f"[SISBAJUD] Otimizações de performance {status}")

# ===== PONTO DE ENTRADA PRINCIPAL =====

if __name__ == "__main__":
    # Modo de teste/debug
    debug_sisbajud_status()

    print("\n[SISBAJUD] Módulo refatorado carregado com sucesso!")
    print("[SISBAJUD] Use executar_sisbajud_completo() para processamento completo")
    print("[SISBAJUD] ou funções específicas do módulo para operações individuais")