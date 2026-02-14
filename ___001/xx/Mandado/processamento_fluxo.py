import time
import unicodedata

from Fix import esperar_elemento, indexar_e_processar_lista
from Fix.log import logger

from .processamento_argos import processar_argos
from .processamento_outros import fluxo_mandados_outros


def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    """
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    def fluxo_callback(driver):
        try:
            # REMOVIDO: Passo 0 de clique na lupa (fa-search lupa-doc-nao-apreciado)
            # Busca o cabeçalho do documento após o carregamento da página
            try:
                # Aguarda um pouco para a interface se estabilizar
                time.sleep(2.0)
                # Busca o cabeçalho usando as funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = esperar_elemento(driver, cabecalho_selector, timeout=15)  # Aumentado de 10 para 15
                if not cabecalho:
                    logger.error('[ERRO] Cabeçalho do documento não encontrado após espera')
                    return
                texto_doc = cabecalho.text
                if not texto_doc:
                    logger.error('[FLUXO][ERRO] Cabeçalho do documento vazio')
                    return
            except Exception as e:
                logger.error(f'[FLUXO][ERRO] Erro ao buscar cabeçalho após carregamento: {e}')
                return
            texto_lower = remover_acentos(texto_doc.lower().strip())
            # Identificação dos fluxos
            if any(remover_acentos(termo) in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao']):
                resultado = processar_argos(driver, log=True)
                if not resultado:
                    return  # Não continua para próximo processo
            elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                fluxo_mandados_outros(driver, log=False)
        except Exception as e:
            logger.error(f'[ERRO] Falha ao processar mandado: {str(e)}')
        # NOTA: Fechamento de abas é gerenciado por forcar_fechamento_abas_extras
        # chamado pela função indexar_e_processar_lista após o callback
        
    indexar_e_processar_lista(driver, fluxo_callback)