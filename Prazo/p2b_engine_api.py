# -*- coding: utf-8 -*-
"""P2B — camada API-first (experimental, paralela ao fluxo canônico).

O P2B já nasce de uma atividade GIGS específica (`xs1`). Com a lista de processos
em mãos ANTES de abrir qualquer página, dá para:

1. ler a ÚLTIMA decisão/despacho/sentença de cada processo pela API
   (`timeline` + `documentos/id/{id}` — o mesmo caminho que ARGOS/PEC já usam,
   incluindo a exceção de "comunique-se por edital" / "de forma concomitante");
2. casar a tabela de regras do P2B (`_casas_regra`) SEM executar nenhuma ação;
3. abrir e processar SOMENTE os processos em que há regra com ação aplicável.

Ganho esperado: nenhuma navegação para processo que não tem ação a executar.

Ativação: `PJE_P2B_ENGINE=api` (lida em `x.py::executar_p2b`). Sem a variável o
fluxo canônico continua valendo — nada muda para quem não setar.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# `condensar_conteudo_documento` (Fix/variaveis.py) envolve o texto neste cabeçalho.
_PADRAO_TRANSCRICAO = re.compile(
    r'^Transcri[cç][aã]o do\(a\)[^:]*:\s*\n?"(.*)"\s*$', re.S
)


def _client(driver: Any):
    """PjeApiClient a partir do driver (mesma fábrica do fluxo P2B)."""
    from .p2b_gateway import _criar_api_client
    return _criar_api_client(driver)


def texto_ultima_decisao(client, id_processo) -> Optional[str]:
    """Texto da última decisão/despacho/sentença, via API, sem abrir o processo.

    Usa `obter_chave_ultimo_despacho_decisao_sentenca(..., incluir_conteudo_condensado=True)`,
    que já descarta despacho de "comunique-se por edital" + "de forma concomitante".
    """
    try:
        from Fix.variaveis import obter_chave_ultimo_despacho_decisao_sentenca
        _link, conteudo = obter_chave_ultimo_despacho_decisao_sentenca(
            client, str(id_processo), incluir_conteudo_condensado=True
        )
        if not conteudo:
            return None
        casado = _PADRAO_TRANSCRICAO.match(conteudo.strip())
        return (casado.group(1) if casado else conteudo).strip()
    except Exception as e:
        logger.warning('[P2B_API] falha ao ler a ultima decisao do processo %s (%s: %s)',
                       id_processo, type(e).__name__, e)
        return None


def classificar_processo(client, id_processo) -> Dict[str, Any]:
    """Diz se o processo tem regra com ação aplicável — sem abrir a página.

    Returns:
        {'acionavel': True|False|None, 'motivo': str, 'trecho': str|None}
        `None` = não deu para ler o texto pela API (o processo deve ser aberto
        como fallback, para o caminho DOM decidir).
    """
    from Fix.utils import normalizar_texto
    from .p2b_documentos import _casas_regra

    texto = texto_ultima_decisao(client, id_processo)
    if not texto:
        return {'acionavel': None, 'motivo': 'sem texto da decisao via API', 'trecho': None}

    casada = _casas_regra(normalizar_texto(texto))
    if not casada:
        return {'acionavel': False, 'motivo': 'nenhuma regra casou', 'trecho': None}

    _trechos, _tipo_acao, match = casada
    return {
        'acionavel': True,
        'motivo': 'regra casou',
        'trecho': getattr(getattr(match, 're', None), 'pattern', '')[:80],
    }


def filtrar_processos(driver: Any, atividades: List[dict]) -> Tuple[List[dict], List[dict]]:
    """Separa (a abrir, pulados) aplicando a classificação por regra.

    Item sem id de processo é mantido na lista de abertura (o fluxo normal
    resolve o id na navegação).
    """
    client = _client(driver)
    selecionados: List[dict] = []
    pulados: List[dict] = []

    for item in atividades:
        processo = item.get('processo') or {}
        id_processo = (processo.get('id') or processo.get('idProcesso')
                       or item.get('idProcesso') or item.get('id'))
        numero = (processo.get('numero') or processo.get('numeroProcesso')
                  or item.get('numeroProcesso') or item.get('numero'))

        if not id_processo:
            logger.warning('[P2B_API] item sem id de processo (numero=%s) — mantido para o fluxo normal', numero)
            selecionados.append(item)
            continue

        info = classificar_processo(client, id_processo)
        alvo = numero or id_processo

        if info['acionavel'] is False:
            logger.info('[P2B_API][PULADO] %s — %s', alvo, info['motivo'])
            pulados.append({'numero': numero, 'id': id_processo, 'motivo': info['motivo']})
            continue

        if info['acionavel'] is None:
            logger.info('[P2B_API][ABRIR] %s — %s (decide no DOM)', alvo, info['motivo'])
        else:
            logger.info('[P2B_API][ABRIR] %s — regra: %s', alvo, info['trecho'])
        selecionados.append(item)

    return selecionados, pulados


def processar_p2b_api(driver: Any, tamanho_pagina: int = 100, max_processos: int = 0):
    """Executa o P2B pelo motor API-first: filtra por regra ANTES de abrir.

    Mesma saída de `processar_gigs_sem_prazo_p2b`, acrescida de:
      - `total_xs1`: quantas atividades xs1 a API devolveu;
      - `pulados_sem_regra`: processos que não foram abertos e o motivo.
    """
    from .p2b_gateway import processar_gigs_sem_prazo_p2b, testar_gigs_xs1

    atividades = testar_gigs_xs1(driver, tamanho_pagina=tamanho_pagina)
    total = len(atividades)
    logger.info('[P2B_API] GIGS xs1 encontrados: %d', total)
    if not total:
        return {'sucesso': True, 'total': 0, 'processados': 0, 'total_xs1': 0, 'pulados_sem_regra': []}

    selecionados, pulados = filtrar_processos(driver, atividades)
    logger.info('[P2B_API] %d/%d processos com regra acionavel; %d pulados sem abrir',
                len(selecionados), total, len(pulados))

    resultado = processar_gigs_sem_prazo_p2b(
        driver,
        tamanho_pagina=tamanho_pagina,
        max_processos=max_processos,
        atividades=selecionados,
    )

    if isinstance(resultado, dict):
        resultado['total_xs1'] = total
        resultado['pulados_sem_regra'] = pulados
    return resultado
