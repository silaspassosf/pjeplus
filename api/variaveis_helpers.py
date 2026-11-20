from typing import Optional, Any, Dict, List, Tuple

import html as _html
import re

from api.variaveis_client import PjeApiClient


def _erro_gateway(tipo: str, mensagem: str, path: str, status: Optional[int] = None) -> Dict[str, Any]:
    return {
        'ok': False,
        'status': status,
        'data': None,
        'error': {
            'type': tipo,
            'message': mensagem,
            'method': 'GET',
            'path': path,
            'status': status,
        },
    }


def _extrair_itens_pagina(payload: Any, pagina_atual: int, tamanho_pagina: int) -> Tuple[List[Any], bool]:
    if isinstance(payload, list):
        return payload, len(payload) >= tamanho_pagina

    if not isinstance(payload, dict):
        return [], False

    itens = payload.get('items')
    if itens is None:
        itens = payload.get('itens')
    if itens is None:
        itens = payload.get('content')
    if itens is None:
        itens = payload.get('resultados')
    if itens is None:
        itens = payload.get('resultado')
    if itens is None:
        itens = payload.get('data')

    if not isinstance(itens, list):
        itens = []

    total_paginas = payload.get('totalPaginas')
    if isinstance(total_paginas, int):
        return itens, pagina_atual < total_paginas

    total_paginas = payload.get('totalPages')
    if isinstance(total_paginas, int):
        return itens, pagina_atual < total_paginas

    ultima = payload.get('ultima')
    if isinstance(ultima, bool):
        return itens, not ultima

    return itens, len(itens) >= tamanho_pagina


def buscar_todas_paginas(
    client: PjeApiClient,
    path: str,
    *,
    params_base: Optional[Dict[str, Any]] = None,
    page_param: str = 'pagina',
    size_param: str = 'tamanhoPagina',
    pagina_inicial: int = 1,
    tamanho_pagina: int = 100,
    limite_paginas: int = 100,
    timeout: int = 15,
) -> Dict[str, Any]:
    if limite_paginas < 1:
        return _erro_gateway('pagination_error', 'limite_paginas deve ser >= 1', path)

    itens_total: List[Any] = []
    pagina_atual = pagina_inicial

    for _ in range(limite_paginas):
        params = dict(params_base or {})
        params[page_param] = pagina_atual
        params[size_param] = tamanho_pagina

        resposta = client.gateway_get(path, params=params, timeout=timeout)
        if not resposta.get('ok'):
            erro = resposta.get('error') or {}
            mensagem = erro.get('message') or f'Falha na pagina {pagina_atual}'
            return _erro_gateway(
                erro.get('type') or 'http_error',
                mensagem,
                path,
                resposta.get('status'),
            )

        itens_pagina, tem_mais = _extrair_itens_pagina(
            resposta.get('data'),
            pagina_atual=pagina_atual,
            tamanho_pagina=tamanho_pagina,
        )
        itens_total.extend(itens_pagina)

        if not tem_mais:
            return {
                'ok': True,
                'status': resposta.get('status'),
                'data': itens_total,
                'error': None,
            }

        pagina_atual += 1

    return _erro_gateway(
        'pagination_limit',
        f'Limite de paginas atingido: {limite_paginas}',
        path,
    )


def obter_gigs_com_fase(client: PjeApiClient, id_processo: str) -> Optional[Dict[str, Any]]:
    """Obtém dados GIGS + FASE (Conhecimento/Liquidação/Execução) do processo em uma única chamada."""
    try:
        id_para_busca = id_processo
        if '-' in str(id_processo):
            id_resolvido = client.id_processo_por_numero(id_processo)
            if not id_resolvido:
                return None
            id_para_busca = str(id_resolvido)

        dados_processo = client.processo_por_id(id_para_busca)
        if not dados_processo:
            return None

        atividades_gigs = client.atividades_gigs(id_para_busca)
        if not atividades_gigs:
            atividades_gigs = []

        resultado = {
            'id_processo': dados_processo.get('numero') or id_processo,
            'id_interno': id_para_busca,
            'fase': dados_processo.get('faseProcessual') or 'Desconhecida',
            'atividades_gigs': atividades_gigs
        }

        return resultado

    except Exception:
        return None


def obter_texto_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Tenta obter o conteúdo textual/HTML de um documento via API, sem abrir a"""
    try:
        dados = client.documento_por_id(id_processo, id_documento, incluirAssinatura=True, incluirAnexos=True)
        if dados:
            candidates = ['conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento']
            for k in candidates:
                v = dados.get(k)
                if v and isinstance(v, str) and v.strip():
                    text = v
                    if text.lstrip().startswith('<') or '<p' in text[:200] or '<div' in text[:200]:
                        clean = re.sub(r'<[^>]+>', '', text)
                        clean = _html.unescape(clean)
                        return re.sub(r"\s{2,}", ' ', clean).strip()
                    else:
                        return re.sub(r"\s{2,}", ' ', text).strip()

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
    """Busca uma atividade GIGS específica por observação."""
    try:
        id_para_busca = id_processo
        if '-' in id_processo:
            id_resolvido = client.id_processo_por_numero(id_processo)
            if id_resolvido:
                id_para_busca = str(id_resolvido)

        atividades = client.atividades_gigs(id_para_busca)
        if not atividades:
            return None

        patterns_lower = [p.lower() for p in observacao_patterns]

        for atividade in atividades:
            status = (atividade.get('statusAtividade') or '').upper()
            observacao = (atividade.get('observacao') or '').lower()

            if prazo_aberto:
                if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                    continue

            if observacao and any(pattern in observacao for pattern in patterns_lower):
                return atividade

        return None

    except Exception as e:
        return None


def obter_todas_atividades_gigs_com_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> List[Dict[str, Any]]:
    """Busca TODAS as atividades GIGS que correspondem aos critérios (versão plural)."""
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
    """Função simples para extrair dados de liquidação via API PJe."""
    resultado = {
        'apenas_uma_com_advogado': False,
        'tem_perito': False
    }

    try:
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

        partes = client.partes(id_processo)
        if partes:
            reclamadas_com_advogado = 0

            for parte in partes:
                polo = (parte.get('tipoPolo') or '').upper()

                eh_reclamada = any(s in polo for s in ['RECLAMADO', 'PASSIVO', 'REU', 'EXECUTADO'])

                if eh_reclamada:
                    tem_advogado = bool(
                        parte.get('representante') or
                        parte.get('procuradores') or
                        parte.get('advogado') or
                        parte.get('nomeAdvogado')
                    )

                    if tem_advogado:
                        reclamadas_com_advogado += 1

            resultado['apenas_uma_com_advogado'] = (reclamadas_com_advogado == 1)

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        return resultado


def verificar_bndt(client: PjeApiClient, id_processo: str) -> Dict[str, Any]:
    """Verifica se há partes cadastradas no BNDT e retorna informações formatadas."""
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