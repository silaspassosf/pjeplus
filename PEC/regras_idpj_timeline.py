import time
from typing import Optional

def verificar_timeline_idpj_mandado_edital(driver, id_processo: str, id_documento_sentenca: Optional[str] = None) -> bool:
    """
    Verifica a timeline após a sentença IDPJ para a seguinte regra:
    - Há mandado e edital?
      Não -> Não executa nada (retorna False)
      Sim:
        A. Em apenas uma data? -> Não executa (retorna False)
        B. Em pelo menos 2 datas (seja apenas mandado em mais de uma data ou edital em mais de uma data, não ambos) -> Executa (retorna True)

    A leitura da timeline é feita via API REST de forma otimizada.

    Args:
        driver: Instância do WebDriver contendo a sessão ativa do PJe.
        id_processo: ID interno do processo no PJe (numérico).
        id_documento_sentenca: ID do documento da sentença IDPJ para usar como marco temporal.
                               Apenas documentos protocolados DEPOIS dessa sentença serão analisados.
                               
    Returns:
        bool: True se deve Executar, False se Não deve Executar.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from api.variaveis_client import session_from_driver
    except ImportError:
        logger.error("Falha ao importar session_from_driver.")
        return False

    try:
        sess, host = session_from_driver(driver)
        base = f'https://{host}'
        
        url_timeline = (
            f'{base}/pje-comum-api/api/processos/id/{id_processo}/timeline'
            '?buscarDocumentos=true&buscarMovimentos=false&somenteDocumentosAssinados=false'
        )
        
        timeline = None
        for _ in range(3):
            try:
                r = sess.get(url_timeline, timeout=30)
                if r.status_code == 200:
                    timeline = r.json()
                    break
                elif r.status_code == 401:
                    logger.error("Sessão expirada (401) ao buscar timeline.")
                    break
            except Exception as e:
                logger.warning(f"Erro ao buscar timeline (retry...): {e}")
                time.sleep(1)
                
        if not timeline:
            logger.error("Timeline retornou vazia ou ocorreu erro na requisição.")
            return False

        # Localizar a data da sentença na timeline, caso tenha sido passado o id_documento
        data_sentenca = None
        if id_documento_sentenca:
            for item in timeline:
                if str(item.get('idDocumento')) == str(id_documento_sentenca):
                    data_sentenca = item.get('dataJuntada')
                    break
                # Também checar anexos
                for anexo in item.get('anexos', []):
                    if str(anexo.get('idDocumento')) == str(id_documento_sentenca):
                        data_sentenca = item.get('dataJuntada')
                        break
                if data_sentenca:
                    break

        datas_relevantes = set()
        
        # Analisar os itens da timeline
        for item in timeline:
            data_juntada = item.get('dataJuntada')
            if not data_juntada:
                continue
                
            # Queremos apenas os documentos posteriores à sentença
            if data_sentenca and data_juntada <= data_sentenca:
                continue
                
            descricao = item.get('descricaoDocumento', '') or ''
            tipo = item.get('tipoDocumento', '') or ''
            texto_item = f"{descricao} {tipo}".lower()
                
            if 'mandado' in texto_item or 'edital' in texto_item:
                # Extrai apenas o dia (YYYY-MM-DD)
                data_str = data_juntada[:10]
                datas_relevantes.add(data_str)
                
        # Validação da Regra:
        quantidade_datas = len(datas_relevantes)
        
        logger.info(f"[IDPJ] {quantidade_datas} datas distintas encontradas para Mandados/Editais após a sentença: {datas_relevantes}")
        
        if quantidade_datas == 0:
            # Não há mandado e edital -> Não executa
            return False
        elif quantidade_datas == 1:
            # Em apenas uma data -> Não executa
            return False
        else:
            # Em pelo menos 2 datas -> Executa
            return True

    except Exception as e:
        logger.error(f"Erro na verificação da timeline para IDPJ: {e}")
        return False
