import requests
from urllib.parse import urlencode
from typing import Any, Dict, List, Optional, Union

def buscar_peticoes_escaninho_direto(
    session: requests.Session,
    base_url: str,
    xsrf_token: Optional[str] = None,
    pagina_inicial: int = 1,
    tamanho_pagina: int = 50,
    max_paginas: int = 100,
    ordenacao_crescente: bool = True,
    debug: bool = True,
    log_limite: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Busca diretamente as petições juntadas no escaninho do PJe via API.

    Args:
        session: Sessão requests já autenticada (cookies da aplicação).
        base_url: URL base da instância do PJe (ex: 'https://pje.example.com').
        xsrf_token: Token XSRF (se já disponível, senão será lido do cookie).
        pagina_inicial: Página inicial.
        tamanho_pagina: Quantidade de itens por página.
        max_paginas: Máximo de páginas a percorrer.
        ordenacao_crescente: Ordenação crescente (True) ou decrescente (False).
        debug: Exibe logs detalhados.
        log_limite: Número máximo de itens a exibir no debug (None = todos).

    Returns:
        Dicionário com metadados da busca e lista de petições normalizadas.
    """

    # --- helpers internos -------------------------------------------------
    def _to_query(params: Dict[str, Any]) -> str:
        return urlencode({k: str(v) for k, v in params.items() if v is not None})

    def _as_array(payload: Any) -> List[Any]:
        if not payload:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            # tenta chaves comuns que podem conter a lista
            for key in ('resultado', 'dados', 'conteudo', 'items'):
                val = payload.get(key)
                if isinstance(val, list):
                    return val
                if isinstance(val, dict) and isinstance(val.get('conteudo'), list):
                    return val['conteudo']
        return []

    def _clean_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        # reduz múltiplos espaços internos
        return ' '.join(s.split())

    def _is_numeric_like(value: Any) -> bool:
        s = _clean_text(value)
        return bool(s and s.isdigit())

    def _pick(*args) -> Any:
        for v in args:
            if v is not None and v != '':
                return v
        return None

    def _pick_textual(*args) -> Optional[str]:
        for v in args:
            text = _clean_text(v)
            if text and not _is_numeric_like(text):
                return text
        return None

    def _deep_find_by_keys(source: Any, variants: List[str], max_depth: int = 6) -> Optional[str]:
        """Busca em profundidade (BFS) qualquer valor associado a uma das chaves 'variants'."""
        from collections import deque

        if not source or not variants:
            return None

        queue = deque([(source, 0)])
        visited = set()
        variants_lower = [v.lower() for v in variants]

        while queue:
            node, depth = queue.popleft()
            if depth > max_depth:
                continue
            if node is None or not isinstance(node, (dict, list)):
                continue
            if id(node) in visited:
                continue
            visited.add(id(node))

            if isinstance(node, list):
                for item in node:
                    queue.append((item, depth + 1))
                continue

            # node é dict
            for key, val in node.items():
                key_low = key.lower()
                if any(v == key_low or v in key_low for v in variants_lower):
                    if val is None:
                        continue
                    if isinstance(val, str) and val.strip():
                        return val.strip()
                    if isinstance(val, (int, float, bool)):
                        return str(val)
                    if isinstance(val, dict):
                        # se o valor é um objeto, tenta subcampos comuns de descrição
                        for sub in ('descricao', 'nome', 'label', 'rotulo', 'texto', 'descricaoCompleta'):
                            sub_val = val.get(sub)
                            if isinstance(sub_val, str) and sub_val.strip():
                                return sub_val.strip()

            # enfileira todos os valores para continuar a busca
            for val in node.values():
                queue.append((val, depth + 1))

        return None

    def _extract_numero_processo(text: str) -> Optional[str]:
        import re
        match = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', text)
        return match.group(0) if match else None

    def _normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
        # campos auxiliares
        proc = raw.get('processo') or raw.get('processoJudicial') or raw.get('dadosProcesso') or {}
        tarefa_obj = raw.get('tarefa') or raw.get('tarefaAtual') or raw.get('atividade') or {}
        parte_obj = raw.get('parte') or raw.get('peticionante') or raw.get('poloPeticionante') or {}

        # busca profunda
        numero_profundo = _deep_find_by_keys(raw, ['numeroProcesso', 'nrProcesso', 'processoNumero', 'numero'])
        tipo_profundo = _deep_find_by_keys(raw, [
            'descricaoTipoPeticao', 'nomeTipoPeticao', 'tipoPeticaoDescricao',
            'descricaoTipoDocumento', 'nomeTipoDocumento', 'tipoDocumentoDescricao',
            'classeDocumentoDescricao', 'nomeTipo', 'labelTipoPeticao', 'labelTipoDocumento',
            'tipoPeticao', 'tipoDocumento', 'tipo', 'classeDocumento'
        ])
        descricao_profunda = _deep_find_by_keys(raw, [
            'descricaoPeticao', 'descricaoDocumento', 'documentoDescricao',
            'descricao', 'nomeDocumento', 'assunto', 'resumo'
        ])
        parte_profunda = _deep_find_by_keys(raw, ['nomePeticionante', 'nomeParte', 'nomePessoa'])
        tarefa_profunda = _deep_find_by_keys(raw, ['nomeTarefa', 'tarefa', 'descricaoTarefa', 'atividade'])
        fase_profunda = _deep_find_by_keys(raw, ['nomeFase', 'fase', 'descricaoFase'])
        data_profunda = _deep_find_by_keys(raw, ['dataJuntada', 'dataCadastro', 'dataCriacao', 'dataInclusao', 'instanteCriacao', 'data'])

        numero = _pick(
            proc.get('numero'), proc.get('numeroProcesso'),
            raw.get('numeroProcesso'), raw.get('nrProcesso'), raw.get('processoNumero'),
            numero_profundo
        )
        if numero and '-' not in str(numero):
            extraido = _extract_numero_processo(str(numero))
            if extraido:
                numero = extraido

        # parte: polo + papel
        polo_label = None
        polo = raw.get('poloPeticionante')
        if isinstance(polo, str):
            polo_low = polo.strip().lower()
            if 'ativo' in polo_low:
                polo_label = 'Ativo'
            elif 'passivo' in polo_low:
                polo_label = 'Passivo'
            elif 'terceiro' in polo_low:
                polo_label = 'Terceiro'
            else:
                polo_label = polo.strip()
        papel_label = _clean_text(raw.get('nomePapelUsuarioDocumento'))
        parte = None
        if polo_label and papel_label:
            parte = f"{polo_label} ({papel_label})"
        else:
            parte = polo_label or papel_label or None

        tipo_peticao = _pick_textual(
            raw.get('nomeTipoProcessoDocumento'),
            raw.get('nomeTipoPeticao'),
            raw.get('descricaoTipoPeticao'),
            raw.get('tipoDocumentoDescricao'),
            raw.get('tipoOrigemDocumento'),
            raw.get('tipoPeticao'),
            tipo_profundo
        )

        return {
            'numeroProcesso': numero,
            'tipoPeticao': tipo_peticao,
            'descricao': _pick(raw.get('descricao'), raw.get('descricaoPeticao'), raw.get('tipoPeticao'),
                               raw.get('assunto'), raw.get('nomeDocumento'), raw.get('documentoDescricao'),
                               descricao_profunda),
            'parte': parte,
            'tarefa': _pick(tarefa_obj.get('nome'), tarefa_obj.get('descricao'),
                            raw.get('tarefa'), raw.get('nomeTarefa'), tarefa_profunda),
            'fase': _pick(raw.get('faseProcessual'), raw.get('fase'), raw.get('nomeFase'),
                          proc.get('fase'), proc.get('nomeFase'), fase_profunda),
            'dataJuntada': _pick(raw.get('dataJuntada'), raw.get('dataCadastro'), raw.get('dataCriacao'),
                                 raw.get('dataInclusao'), raw.get('instanteCriacao'), data_profunda),
            'idProcesso': _pick(proc.get('id'), proc.get('idProcesso'), raw.get('idProcesso')),
            'idItem': _pick(raw.get('id'), raw.get('idPeticao'), raw.get('idDocumento')),
            'bruto': raw
        }

    def _do_fetch(url: str) -> requests.Response:
        headers = {'Accept': 'application/json'}
        if xsrf_token:
            headers['X-XSRF-TOKEN'] = xsrf_token
        return session.get(url, headers=headers)

    def _read_total_pages(payload: Any, current_page: int, page_size: int, current_length: int) -> int:
        if not isinstance(payload, dict):
            return current_page + 1
        # tenta chaves comuns
        for key in ('totalPaginas', 'quantidadePaginas', 'totalPaginasResultado'):
            val = payload.get(key)
            if isinstance(val, int) and val > 0:
                return val
        # dentro de resultado ou dados
        for wrapper in ('resultado', 'dados', 'paginacao', 'meta'):
            sub = payload.get(wrapper)
            if isinstance(sub, dict):
                val = sub.get('totalPaginas')
                if isinstance(val, int) and val > 0:
                    return val
        # fallback
        if current_length < page_size:
            return current_page
        return current_page + 1

    def _build_candidates() -> List[Dict[str, Any]]:
        candidates = [
            ('escaninhos_peticoesjuntadas', '/pje-comum-api/api/escaninhos/peticoesjuntadas', {}),
            ('escaninhos_peticoes_juntadas', '/pje-comum-api/api/escaninhos/peticoes-juntadas', {}),
            ('escaninhos_peticoes', '/pje-comum-api/api/escaninhos/peticoes', {}),
            ('escaninhos_documentosinternos_flag_peticoesjuntadas',
             '/pje-comum-api/api/escaninhos/documentosinternos',
             {'peticoesJuntadas': True}),
            ('escaninhos_documentosinternos_flag_peticoesnaoapreciadas',
             '/pje-comum-api/api/escaninhos/documentosinternos',
             {'peticoesNaoApreciadas': True}),
        ]
        return [
            {
                'nome': nome,
                'base_url': base_url.rstrip('/') + path,
                'extra_params': extra
            }
            for nome, path, extra in candidates
        ]

    async def _try_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
        page = pagina_inicial
        all_raw = []
        trace = []

        for _ in range(max_paginas):
            params = {
                **candidate['extra_params'],
                'pagina': page,
                'tamanhoPagina': tamanho_pagina,
                'ordenacaoCrescente': str(ordenacao_crescente).lower(),
            }
            url = f"{candidate['base_url']}?{_to_query(params)}"
            resp = _do_fetch(url)

            list_data = _as_array(resp.json()) if resp.ok else []
            trace.append({
                'pagina': page,
                'status': resp.status_code,
                'ok': resp.ok,
                'quantidade': len(list_data),
                'url': url
            })

            if not resp.ok:
                return {
                    'sucesso': False,
                    'candidato': candidate['nome'],
                    'erro': f'HTTP_{resp.status_code}',
                    'trace': trace,
                    'totalBruto': len(all_raw),
                    'dados': []
                }

            if not list_data:
                break

            all_raw.extend(list_data)

            total_pages = _read_total_pages(resp.json(), page, tamanho_pagina, len(list_data))
            if page >= total_pages:
                break
            page += 1

        normalized = [_normalize_item(item) for item in all_raw]
        return {
            'sucesso': len(normalized) > 0,
            'candidato': candidate['nome'],
            'erro': None if normalized else 'SEM_DADOS',
            'trace': trace,
            'totalBruto': len(all_raw),
            'dados': normalized
        }

    # --- execução principal ------------------------------------------------
    if xsrf_token is None:
        # tenta ler do cookie da sessão
        xsrf_token = session.cookies.get('XSRF-TOKEN')

    candidates = _build_candidates()
    tentativas = []

    for candidate in candidates:
        result = _try_candidate(candidate)
        tentativas.append(result)
        if result['sucesso']:
            output = {
                'sucesso': True,
                'endpointUsado': result['candidato'],
                'total': len(result['dados']),
                'parametros': {
                    'paginaInicial': pagina_inicial,
                    'tamanhoPagina': tamanho_pagina,
                    'maxPaginas': max_paginas,
                    'ordenacaoCrescente': ordenacao_crescente,
                    'logLimite': log_limite,
                },
                'trace': result['trace'],
                'dados': result['dados'],
                'tentativas': [
                    {
                        'candidato': t['candidato'],
                        'sucesso': t['sucesso'],
                        'erro': t['erro'],
                        'totalBruto': t['totalBruto'],
                    }
                    for t in tentativas
                ],
            }

            if debug:
                print(f"[pje_peticoes] endpoint usado: {output['endpointUsado']}")
                print(f"[pje_peticoes] total: {output['total']}")
                limit = output['total'] if log_limite is None else min(log_limite, output['total'])
                if limit > 0:
                    # exibe tabela simplificada
                    print(f"{'Numero Processo':<30} {'Tipo Petição':<30} {'Descrição':<40} {'Parte':<30} {'Tarefa':<20} {'Fase':<20} {'Data Juntada':<20}")
                    print('-' * 170)
                    for item in output['dados'][:limit]:
                        print(f"{item['numeroProcesso'] or '':<30} "
                              f"{item['tipoPeticao'] or '':<30} "
                              f"{item['descricao'] or '':<40} "
                              f"{item['parte'] or '':<30} "
                              f"{item['tarefa'] or '':<20} "
                              f"{item['fase'] or '':<20} "
                              f"{item['dataJuntada'] or '':<20}")
            return output

    # nenhum endpoint deu dados
    return {
        'sucesso': False,
        'erro': 'NENHUM_ENDPOINT_RETORNOU_DADOS',
        'parametros': {
            'paginaInicial': pagina_inicial,
            'tamanhoPagina': tamanho_pagina,
            'maxPaginas': max_paginas,
            'ordenacaoCrescente': ordenacao_crescente,
        },
        'tentativas': [
            {
                'candidato': t['candidato'],
                'sucesso': t['sucesso'],
                'erro': t['erro'],
                'totalBruto': t['totalBruto'],
            }
            for t in tentativas
        ],
        'sugestao': 'Abra a tela de petições juntadas e confirme se a sessão/autorização está ativa.',
    }