ÿþ"""
judicial_wrappers.py - Factory functions para wrappers de atos
"""
from Fix.core import logger
from .judicial_fluxo import ato_judicial


def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, descricao=None, sigilo=None, perito=False, Assinar=False, coleta_conteudo=None, inserir_conteudo=None, intimar=None):
    """
    Factory function que cria um wrapper para ato_judicial com parâmetros pré-definidos.
    Permite criar funções especializadas como aaDespacho, aaDecisao, etc.
    
    Returns:
        function: Wrapper para ato_judicial com parâmetros fixos
    """
    def wrapper(driver, **kwargs):
        """
        Wrapper para ato_judicial com parâmetros pré-configurados.
        Aceita kwargs para sobrescrever parâmetros padrão.
        """
        # Mescla parâmetros padrão com kwargs
        params = {
            'conclusao_tipo': conclusao_tipo,
            'modelo_nome': modelo_nome,
            'prazo': prazo,
            'marcar_pec': marcar_pec,
            'movimento': movimento,
            'gigs': gigs,
            'marcar_primeiro_destinatario': marcar_primeiro_destinatario,
            'descricao': descricao,
            'sigilo': sigilo,
            'perito': perito,
            'Assinar': Assinar,
            'coleta_conteudo': coleta_conteudo,
            'inserir_conteudo': inserir_conteudo,
            'intimar': intimar
        }
        
        # Sobrescreve com kwargs
        params.update(kwargs)
        
        # Remove parâmetros None para não interferir na lógica
        params = {k: v for k, v in params.items() if v is not None}
        
        logger.info(f'[WRAPPER] Executando ato_judicial com params: {params}')
        return ato_judicial(driver, **params)
    
    # Define nome da função para debug
    wrapper.__name__ = f"ato_{conclusao_tipo}_{modelo_nome.replace(' ', '_').lower()}"
    
    return wrapper
