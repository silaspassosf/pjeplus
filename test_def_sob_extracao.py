"""
Debug: Testar extracao de texto para DEF_SOB
Reproduz os tres processos e vê qual extração está falhando
"""
import logging
import sys
from pathlib import Path

# Config logging granular
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Processos problem
PROCESSOS_PROBLEM = [
    "1001216-95.2018.5.02.0703",
    "1001604-23.2023.5.02.0056",
    "1001119-56.2022.5.02.0703",
]

def test_uma_extracao(numero_processo):
    """Testa extração de um processo específico"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testando: {numero_processo}")
    logger.info(f"{'='*60}")
    
    try:
        # Imports aqui para detectar falhas
        logger.info("1. Importando módulos...")
        from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf
        from Fix.selenium_base import esperar_elemento, safe_click
        from Fix.selectors_pje import BTN_TAREFA_PROCESSO
        from selenium.webdriver.common.by import By
        
        logger.info("✅ Módulos importados")
        
        # Seria necessário um driver ativo aqui
        logger.info("2. Verificar se há driver ativo...")
        try:
            # Simulação: sem driver real
            logger.warning("⚠️  Sem driver Selenium ativo - não posso testar extração real")
            logger.info("   Verifique manualmente:")
            logger.info("   - Abra PJe")
            logger.info("   - Acesse processo")
            logger.info("   - Abra tarefa/detalhes")
            logger.info("   - Verifique se há texto em 'Fundamentação', 'Dispositivo', etc")
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar driver: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    logger.info("Iniciando debug de DEF_SOB - Extração de Texto")
    logger.info(f"Processos a testar: {PROCESSOS_PROBLEM}")
    
    for proc in PROCESSOS_PROBLEM:
        test_uma_extracao(proc)
    
    logger.info("\n" + "="*60)
    logger.info("PRÓXIMOS PASSOS:")
    logger.info("1. Abrir manualmente cada processo em PJe")
    logger.info("2. Navegar para Details → Decisão")
    logger.info("3. Verificar conteúdo (tem texto ou está em branco?)")
    logger.info("4. Se tiver texto: verificar se é HTML/PDF/texto plano")
    logger.info("="*60)
