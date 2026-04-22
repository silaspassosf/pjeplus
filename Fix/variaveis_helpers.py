from typing import Optional, Any, Dict, List

import html as _html
import re

from Fix.variaveis_client import PjeApiClient


def obter_gigs_com_fase(client: PjeApiClient, id_processo: str) -> Optional[Dict[str, Any]]:
    """Obtém dados GIGS + FASE (Conhecimento/Liquidação/Execução) do processo em uma única chamada.
    
    Args:
        client: PjeApiClient configurado
        id_processo: ID do processo (pode ser CNJ ou ID interno - será resolvido automaticamente)
        
    Returns:
        Dict com:
        {
            'id_processo': '1001706-10.2024.5.02.0703',  # CNJ
            'id_interno': 6577647,  # ID interno
            'fase': 'Conhecimento',  # ou 'Liquidação' ou 'Execução'
            'atividades_gigs': [  # lista vazia se nenhuma
                {
                    'tipoAtividade': '...',
                    'statusAtividade': '...',
                    'dataPrazo': '...',
                    'observacao': '...'
                }
            ]
        }
        Retorna None se falhar em obter dados do processo
    """
    try:
        # Resolver ID se necessário
        id_para_busca = id_processo
        if '-' in str(id_processo):  # É CNJ, precisa resolver
            id_resolvido = client.id_processo_por_numero(id_processo)
            if not id_resolvido:
                return None
            id_para_busca = str(id_resolvido)
        
        # Obter dados do processo (inclui faseProcessual)
        dados_processo = client.processo_por_id(id_para_busca)
        if not dados_processo:
            return None
        
        # Obter GIGS
        atividades_gigs = client.atividades_gigs(id_para_busca)
        if not atividades_gigs:
            atividades_gigs = []
        
        # Montar resultado com faseProcessual (campo correto da API)
        resultado = {
            'id_processo': dados_processo.get('numero') or id_processo,
            'id_interno': id_para_busca,
            'fase': dados_processo.get('faseProcessual') or 'Desconhecida',  # Campo correto
            'atividades_gigs': atividades_gigs
        }
        
        return resultado
        
    except Exception:
        return None


def obter_texto_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """
    Tenta obter o conteúdo textual/HTML de um documento via API, sem abrir a
    interface do PJe. Esta função implementa a estratégia conservadora (caso A):
    - chama `documento_por_id` e procura por campos que contenham HTML/texto;
    - se não encontrar, tenta alguns endpoints comuns de "conteúdo" e verifica
      se a resposta contém HTML/texto (descarta PDFs/binários neste fluxo).

    Retorna o texto limpo (tags removidas, entidades unescaped) ou `None`.
    """
    try:
        dados = client.documento_por_id(id_processo, id_documento, incluirAssinatura=True, incluirAnexos=True)
        if dados:
            # campos possíveis que podem conter o HTML/texto
            candidates = ['conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento']
            for k in candidates:
                v = dados.get(k)
                if v and isinstance(v, str) and v.strip():
                    text = v
                    # se parecer HTML, remover tags
                    if text.lstrip().startswith('<') or '<p' in text[:200] or '<div' in text[:200]:
                        clean = re.sub(r'<[^>]+>', '', text)
                        clean = _html.unescape(clean)
                        return re.sub(r"\s{2,}", ' ', clean).strip()
                    else:
                        return re.sub(r"\s{2,}", ' ', text).strip()

        # Tentar endpoints alternativos que costumam expor o conteúdo
        possible_paths = [
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudo",
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudoHtml",
            f"/pje-comum-api/api/processos/id/{id_processo}/documento/{id_documento}/conteudo",
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/{id_documento}/conteudo",
        ]
        for path in possible_paths:
            try:
                url = client._url(path)
                r = client.sess.get(url, timeout=15)
            except Exception:
                r = None
            if not r or not getattr(r, 'ok', False):
                continue

            ctype = (r.headers.get('Content-Type') or '').lower()
            text_body = None
            try:
                text_body = r.text
            except Exception:
                text_body = None

            if text_body:
                if 'html' in ctype or text_body.lstrip().startswith('<'):
                    clean = re.sub(r'<[^>]+>', '', text_body)
                    clean = _html.unescape(clean)
                    return re.sub(r"\s{2,}", ' ', clean).strip()
                # json with nested content
                if 'json' in ctype:
                    try:
                        j = r.json()
                        for k in ['conteudo', 'conteudoHtml', 'texto', 'previewModeloDocumento']:
                            v = j.get(k)
                            if v and isinstance(v, str) and v.strip():
                                if v.lstrip().startswith('<'):
                                    clean = re.sub(r'<[^>]+>', '', v)
                                    clean = _html.unescape(clean)
                                    return re.sub(r"\s{2,}", ' ', clean).strip()
                                return re.sub(r"\s{2,}", ' ', v).strip()
                    except Exception:
                        pass

        return None
    except Exception:
        return None


def buscar_atividade_gigs_por_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> Optional[Dict[str, Any]]:
    """Busca uma atividade GIGS específica por observação.
    
    Args:
        client: PjeApiClient configurado
        id_processo: ID do processo
        observacao_patterns: Lista de termos/patterns para buscar na observação
                            (ex: ['AJ-JT'], busca por OR - qualquer um)
        prazo_aberto: Se True, filtra apenas atividades com status de prazo aberto
    
    Returns:
        Dict com a atividade encontrada ou None se não houver match
        Campos retornados: tipoAtividade, dataPrazo, statusAtividade, observacao
    
    Exemplo:
        resultado = buscar_atividade_gigs_por_observacao(
            client, 
            id_processo='1234567-89.2024.5.01.0000',
            observacao_patterns=['AJ-JT'],
            prazo_aberto=True
        )
    """
    try:
        # Resolver CNJ -> id interno se necessário
        id_para_busca = id_processo
        if '-' in id_processo:
            id_resolvido = client.id_processo_por_numero(id_processo)
            if id_resolvido:
                id_para_busca = str(id_resolvido)
        
        atividades = client.atividades_gigs(id_para_busca)
        if not atividades:
            return None
        
        # normalizar patterns para lowercase
        patterns_lower = [p.lower() for p in observacao_patterns]

        # Redirecionar busca AVJT para Atbem (Pgto Hon Peric)
        if any('avjt' in p for p in patterns_lower):
            patterns_lower = ['checar pgto hon peric']

        for atividade in atividades:
            status = (atividade.get('statusAtividade') or '').upper()
            observacao = (atividade.get('observacao') or '').lower()
            
            # validar status de prazo aberto se solicitado
            if prazo_aberto:
                if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                    continue
            
            # verificar se observação contém algum dos patterns
            if observacao and any(pattern in observacao for pattern in patterns_lower):
                return atividade
        
        return None
        
    except Exception as e:
        return None


def obter_todas_atividades_gigs_com_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> List[Dict[str, Any]]:
    """Busca TODAS as atividades GIGS que correspondem aos critérios (versão plural).
    
    Args:
        client: PjeApiClient configurado
        id_processo: ID do processo
        observacao_patterns: Lista de termos/patterns para buscar na observação
        prazo_aberto: Se True, filtra apenas atividades com prazo aberto
    
    Returns:
        Lista de dicts com atividades encontradas, ou lista vazia se nenhuma
    """
    atividades = client.atividades_gigs(id_processo)
    if not atividades:
        return []
    
    patterns_lower = [p.lower() for p in observacao_patterns]
    resultado = []
    
    for atividade in atividades:
        if prazo_aberto:
            status = (atividade.get('statusAtividade') or '').upper()
            if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                continue
        
        observacao = (atividade.get('observacao') or '').lower()
        if observacao and any(pattern in observacao for pattern in patterns_lower):
            resultado.append(atividade)
    
    return resultado


def padrao_liq(client: PjeApiClient, id_processo: str, nome_perito: str = 'ROGERIO') -> Dict[str, bool]:
    """
    Função simples para extrair dados de liquidação via API PJe.
    
    Retorna apenas 2 informações essenciais:
    - apenas_uma_com_advogado: bool (True se APENAS UMA reclamada tem advogado)
    - tem_perito: bool (True se existe perito com o nome procurado)
    
    Args:
        client: PjeApiClient configurado
        id_processo: ID do processo
        nome_perito: Nome do perito a procurar (padrão: 'ROGERIO')
    
    Returns:
        Dict com:
        {
            'apenas_uma_com_advogado': bool,
            'tem_perito': bool,
            'erro': str (opcional, se houver exceção)
        }
    """
    resultado = {
        'apenas_uma_com_advogado': False,
        'tem_perito': False
    }
    
    try:
        # ======= VERIFICAR PERITO =======
        pericias = client.pericias(id_processo)
        if pericias:
            pericias_list = []
            if isinstance(pericias, dict):
                pericias_list = pericias.get('content') or pericias.get('resultado') or pericias.get('pericias') or []
            elif isinstance(pericias, list):
                pericias_list = pericias
            
            for pericia in pericias_list:
                nome_perito_api = (
                    pericia.get('nomePerito') or 
                    pericia.get('perito') or 
                    pericia.get('responsavel') or 
                    ''
                )
                
                if nome_perito.upper() in nome_perito_api.upper():
                    resultado['tem_perito'] = True
                    break
        
        # ======= VERIFICAR APENAS UMA RECLAMADA COM ADVOGADO =======
        partes = client.partes(id_processo)
        if partes:
            reclamadas_com_advogado = 0
            
            for parte in partes:
                polo = (parte.get('tipoPolo') or '').upper()
                
                # Verificar se é reclamada (passivo/reclamado)
                eh_reclamada = any(s in polo for s in ['RECLAMADO', 'PASSIVO', 'REU', 'EXECUTADO'])
                
                if eh_reclamada:
                    # Verificar se tem advogado
                    tem_advogado = bool(
                        parte.get('representante') or 
                        parte.get('procuradores') or 
                        parte.get('advogado') or
                        parte.get('nomeAdvogado')
                    )
                    
                    if tem_advogado:
                        reclamadas_com_advogado += 1
            
            # Resultado: True se EXATAMENTE UMA tem advogado
            resultado['apenas_uma_com_advogado'] = (reclamadas_com_advogado == 1)
        
        return resultado
        
    except Exception as e:
        resultado['erro'] = str(e)
        return resultado


def verificar_bndt(client: PjeApiClient, id_processo: str) -> Dict[str, Any]:
    """Verifica se há partes cadastradas no BNDT e retorna informações formatadas.
    
    Baseado na função JavaScript verificarBNDT() do a.py
    
    Args:
        client: PjeApiClient configurado
        id_processo: ID do processo (numérico interno)
    
    Returns:
        Dict com:
        {
            'tem_partes': bool,  # True se há partes no BNDT
            'quantidade': int,  # Número de partes encontradas
            'partes': List[str],  # Lista com nomes das partes
            'mensagem': str,  # Mensagem formatada para exibição
            'erro': str (opcional)  # Mensagem de erro se houver
        }
    
    Exemplo:
        >>> resultado = verificar_bndt(client, '1234567')
        >>> if resultado['tem_partes']:
        >>>     print(resultado['mensagem'])
        >>>     # Saída: "Partes cadastradas no BNDT:\n\nJOÃO DA SILVA\nMARIA SANTOS"
        >>> else:
        >>>     print("Sem partes cadastradas no BNDT")
    """
    resultado = {
        'tem_partes': False,
        'quantidade': 0,
        'partes': [],
        'mensagem': ''
    }
    
    try:
        partes_bndt = client.debitos_trabalhistas_bndt(id_processo)
        
        if partes_bndt is None:
            resultado['erro'] = 'Erro ao consultar API BNDT'
            resultado['mensagem'] = 'Erro ao consultar BNDT'
            return resultado
        
        if len(partes_bndt) > 0:
            resultado['tem_partes'] = True
            resultado['quantidade'] = len(partes_bndt)
            resultado['partes'] = [parte.get('nomeParte', 'N/A') for parte in partes_bndt]
            
            # Formatar mensagem
            mensagem = 'Partes cadastradas no BNDT:\n\n'
            for parte in partes_bndt:
                nome = parte.get('nomeParte', 'N/A')
                mensagem += f'{nome}\n'
            
            resultado['mensagem'] = mensagem.strip()
        else:
            resultado['mensagem'] = 'Sem partes cadastradas no BNDT.'
        
        return resultado
        
    except Exception as e:
        resultado['erro'] = str(e)
        resultado['mensagem'] = f'Erro ao verificar BNDT: {e}'
        return resultado