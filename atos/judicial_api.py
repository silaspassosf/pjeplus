"""
judicial_api.py - Navegação de tarefas e CLS (Conclusão → Minutar) via API REST
===============================================================================

Substitui os cliques de `abrir_tarefa_processo` → `navegar_para_conclusao` →
`escolher_tipo_conclusao` → `aguardar_transicao_minutar` por chamadas diretas ao
`pje-comum-api`, terminando com um único `driver.get()` na URL da tarefa de minuta.

Roteamento comprovado ao vivo no TRT2 (processo 4945496, 26/11/2026):
  1. Não existe pulo arbitrário por ID de tarefa:
     - `POST /tarefas/{orig}/conclusao` fora de 502 (ex.: de 500, 491, 503) → HTTP 400 `PJE-329`.
     - `POST /tarefas/500/transicoes` com `"Elaborar despacho"` → HTTP 500 `ARQ-516`.
     - `PUT /tarefas/503/` estando em 500 → HTTP 500 `ARQ-509`.
     - `GET/POST /tarefas/{outra}/transicoes` fora da tarefa atual → `PJE-368` / `ARQ-505`.
  2. Regra do grafo jBPM (`Fluxo Geral Principal`):
     - `502 Conclusão ao magistrado` é nó obrigatório antes de `503`/`504`/`505`.
     - `500 Análise` é o hub central: tem transição direta para `502` e para os demais subfluxos.
     - Nós periféricos (`491 Cumprimento de Providências`, `521 Convênios`, `511 Prazos Vencidos`, etc.)
       não saem direto para `502`; saem para `"Análise"` (`500`), de onde se vai a `502`.
  3. Destino da minuta depende exclusivamente de `elementoDominioMovimento`:
     - `DESPACHO` → `503 Elaborar despacho`
     - `DECISAO` → `504 Elaborar decisão`
     - `JULGAMENTO` → `505 Elaborar sentença`
  4. Mínimo de chamadas a partir de `Análise` (`500`):
     `GET tarefas?maisRecente=true` → `PUT tarefas/500/` (checa bloqueio) →
     `POST tarefas/500/transicoes` → `GET tarefas/502/conclusao/magistrados` (já inclui `tipos`!) →
     `POST tarefas/502/conclusao` = **5 chamadas HTTP (~800ms)** + 1 `driver.get(url_minuta)`.

Somente Playwright (`driver.context.request`, mesma autenticação do browser).
Qualquer resposta inesperada devolve `None` → `fluxo_cls` faz fallback automático para o DOM.
"""

import json as _json
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlencode, urlparse

from Fix.log import getmodulelogger

logger = getmodulelogger(__name__)

API = '/pje-comum-api/api'

# ---------------------------------------------------------------------------
# Catálogo de IDs de tarefas do Fluxo Geral Principal (GET /tarefas/{id}, TRT2)
# ---------------------------------------------------------------------------
TAREFA_ANALISE = 500
TAREFA_CONCLUSAO = 502

TAREFAS_MINUTAR: Dict[int, str] = {
    503: 'Elaborar despacho',
    504: 'Elaborar decisão',
    505: 'Elaborar sentença',
    514: 'Elaborar decisão - Dependência',
    519: 'Elaborar Despacho - Desarquivar com Reativação',
}

TAREFAS_ASSINAR: Dict[int, str] = {
    506: 'Assinar despacho',
    507: 'Assinar decisão',
    508: 'Assinar sentença',
    515: 'Assinar decisão - Dependência',
    520: 'Assinar Despacho - Desarquivar com Reativação',
}

# Botões de transição de Análise (500) → idTarefa de destino no TRT2.
MAPA_BOTOES_ANALISE: Dict[str, int] = {
    'Arquivar o processo': 277,          # Escolher tipo de arquivamento (-> 499 Arquivo)
    'Comunicações e expedientes': 492,   # Preparar expedientes e comunicações
    'Conclusão ao magistrado': 502,      # Conclusão ao magistrado (-> 503/504/505)
    'Controle de acordo': 462,           # Aguardando cumprimento de acordo
    'Cumprimento de providências': 491,  # Cumprimento de Providências (saída única: Análise)
    'Encaminhar ao CEJUSC': 497,         # Encaminhar ao CEJUSC
    'Encaminhar ao posto avançado': 495, # Encaminhar posto avançado
    'Redistribuir': 509,                 # Redistribuir
    'Remeter ao 2o Grau': 199,           # Remeter ao 2o Grau
    'Sobrestamento': 332,                # Escolher tipo de sobrestamento-suspensão (-> 333)
    'Trânsito em Julgado': 501,          # Registrar trânsito em julgado
    'Aguardando prazo': 510,             # Aguardando prazo (-> 511 Prazos Vencidos)
    'Aguardando audiência': 291,         # Aguardando audiência
    'Iniciar execução': 77,              # Iniciar Execução
    'Iniciar liquidação': 81,            # Iniciar Liquidação
    'Controle de Parcelamento': 516,     # Controle de parcelamento
    'Convênios': 521,                    # Convênios (saída única: Análise)
}

TRANSICAO_CONCLUSAO = 'Conclusão ao magistrado'
TRANSICAO_ANALISE = 'Análise'

# Família do tipo de conclusão (`elementoDominioMovimento`) → tarefa de minuta.
DESTINO_POR_FAMILIA: Dict[str, int] = {
    'DESPACHO': 503,
    'DECISAO': 504,
    'JULGAMENTO': 505,
}

# Todos os 19 tipos de conclusão retornados por `conclusao/magistrados` (`nomeBotao` → idTarefa minuta).
CONCLUSAO_API: Dict[str, int] = {
    'Despacho': 503,                                                   # validado ao vivo
    'Sentença': 505,
    'Sentença Parcial': 505,
    'Extinção da Execução': 505,                                       # validado ao vivo
    'Sentença Geral': 505,
    'Embargos de Declaração': 505,                                     # validado ao vivo
    'Embargos à Execução / Impugnação à Sentença de Liquidação': 505,
    'Homologação de Acordo': 504,
    'Homologação de Cálculos': 504,                                    # validado ao vivo
    'Homologação de Arrematação / Adjudicação': 504,
    'Pedido de Tutela': 504,
    'Admissibilidade de Recursos': 504,                                # validado ao vivo
    'Sobrestamento / Suspensão': 504,                                  # validado ao vivo
    'BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens': 504,   # validado ao vivo
    'IDPJ': 505,                                                       # validado ao vivo
    'Exceção de Incompetência': 504,
    'Prevenção': 504,
    'Decisão Geral': 504,                                              # validado ao vivo
    'Exceção de Pré-executividade': 504,
}

# Aliases curtos usados em `atos/wrappers_ato.py` (normalizados) → `nomeBotao` oficial da API.
# Mantém `wrappers_ato.py` intocado visualmente e garante resolução exata O(1).
ALIASES_WRAPPER_CONCLUSAO: Dict[str, str] = {
    'despacho': 'Despacho',
    'idpj': 'IDPJ',
    'suspensao': 'Sobrestamento / Suspensão',
    'sobrestamento': 'Sobrestamento / Suspensão',
    'homologacao de calculos': 'Homologação de Cálculos',
    'decisao geral': 'Decisão Geral',
    'extincao': 'Extinção da Execução',
    'admissibilidade': 'Admissibilidade de Recursos',
    'bacen': 'BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens',
    'embargos': 'Embargos de Declaração',
}

_RE_ID_PROCESSO = re.compile(r'/processo/(\d+)')


def cls_api_habilitada(via_api: Optional[bool] = None) -> bool:
    """`via_api` explícito vence; senão lê `PJEPLUS_CLS_API` (padrão ligado)."""
    if via_api is not None:
        return bool(via_api)
    return os.environ.get('PJEPLUS_CLS_API', '1').strip().lower() not in ('0', 'false', 'nao', 'não', 'off')


def _norm(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto or '')
    limpo = ''.join(c for c in texto if not unicodedata.combining(c)).casefold()
    return re.sub(r'\s+', ' ', limpo).strip()


def _norm_tarefa_equivalente(texto: str) -> str:
    t = _norm(texto)
    t = t.replace('preparar expedientes e comunicacoes', 'comunicacoes e expedientes')
    t = t.replace('aguardando cumprimento de acordo', 'controle de acordo')
    return t


_RE_ARIA_LABEL = re.compile(r"""aria-label\*?=\s*['"]([^'"]+)['"]""", re.IGNORECASE)


def extrair_destino_de_seletor(seletor: str) -> Optional[str]:
    """Extrai o rótulo de transição de seletores como `button[aria-label='Aguardando prazo']`."""
    if not seletor:
        return None
    m = _RE_ARIA_LABEL.search(seletor)
    if m:
        val = m.group(1).strip()
        if val and 'tarefa' not in _norm(val):
            return val
    return None


def resolver_tipo_conclusao(
    tipos: List[Dict[str, Any]],
    conclusao_tipo: str,
    conclusao_api: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve `conclusao_api` (explícito) ou `conclusao_tipo` (wrapper) para o item habilitado da API.

    Ordem de prioridade:
      1. `conclusao_api` explícito (quando fornecido pelo wrapper/chamador);
      2. Mapa canônico `ALIASES_WRAPPER_CONCLUSAO` (todos os wrappers registrados);
      3. Casamento igual > prefixo > substring na ordem oficial dos botões.
    """
    habilitados = [t for t in (tipos or []) if t.get('habilitado') and t.get('nomeBotao')]
    if not habilitados:
        return None

    candidatos: List[str] = []
    if conclusao_api:
        candidatos.append(_norm(conclusao_api))
    chave_wrapper = _norm(conclusao_tipo)
    if chave_wrapper in ALIASES_WRAPPER_CONCLUSAO:
        candidatos.append(_norm(ALIASES_WRAPPER_CONCLUSAO[chave_wrapper]))
    if chave_wrapper:
        candidatos.append(chave_wrapper)

    for alvo in candidatos:
        if not alvo:
            continue
        for criterio in (lambda n: n == alvo, lambda n: n.startswith(alvo), lambda n: alvo in n):
            for t in habilitados:
                if criterio(_norm(t['nomeBotao'])):
                    return t
    return None


def destino_do_tipo(tipo: Dict[str, Any]) -> Optional[int]:
    """Tarefa de minuta esperada (`503`, `504` ou `505`) para um tipo de conclusão."""
    return CONCLUSAO_API.get(tipo.get('nomeBotao', '')) or DESTINO_POR_FAMILIA.get(
        str(tipo.get('elementoDominioMovimento') or '').upper())


class _ApiTarefas:
    """Cliente mínimo sobre `driver.context.request` (cookies do browser + X-XSRF-TOKEN)."""

    def __init__(self, driver: Any, id_processo: int):
        self.driver = driver
        self.id = id_processo
        parsed = urlparse(driver.current_url or '')
        self.base = f'{parsed.scheme or "https"}://{parsed.netloc or "pje.trt2.jus.br"}'
        self.req = driver.context.request
        self.chamadas = 0

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        xsrf = ''
        try:
            for c in self.driver.context.cookies(self.base):
                if c.get('name', '').upper() in ('XSRF-TOKEN', 'XSRF_TOKEN'):
                    xsrf = unquote(c.get('value', ''))
                    break
        except Exception:
            pass
        h = {'Accept': 'application/json, text/plain, */*', 'X-Grau-Instancia': '1'}
        if xsrf:
            h['X-XSRF-TOKEN'] = xsrf
        if content_type:
            h['Content-Type'] = content_type
        return h

    def _chamar(self, metodo: str, caminho: str, corpo: Optional[str] = None,
                content_type: Optional[str] = None) -> Optional[Any]:
        url = f'{self.base}{API}/processos/id/{self.id}{caminho}'
        self.chamadas += 1
        kwargs: Dict[str, Any] = {'headers': self._headers(content_type), 'timeout': 20000}
        if corpo is not None:
            kwargs['data'] = corpo
        resp = getattr(self.req, metodo.lower())(url, **kwargs)
        status = getattr(resp, 'status', None)
        if not isinstance(status, int):
            return None
        if not getattr(resp, 'ok', False):
            try:
                msg = resp.text()[:200]
            except Exception:
                msg = ''
            logger.warning('[CLS-API] %s %s -> HTTP %s %s', metodo, caminho, status, msg)
            return None
        try:
            return resp.json()
        except Exception:
            return True

    def tarefa_atual(self) -> Optional[Dict[str, Any]]:
        dados = self._chamar('GET', '/tarefas?maisRecente=true')
        return dados[0] if isinstance(dados, list) and dados and isinstance(dados[0], dict) else None

    def verificar_bloqueio(self, id_tarefa: int) -> bool:
        """Checa bloqueio na entrada (1 PUT). Evita atropelar processo bloqueado por outro usuário."""
        res = self._chamar('PUT', f'/tarefas/{id_tarefa}/', f'{{"idProcesso": {self.id}}}', 'application/json')
        if isinstance(res, dict) and res.get('bloqueado') and not res.get('permiteDesbloqueio'):
            logger.warning('[CLS-API] Processo bloqueado por outro usuário: %s', res.get('mensagemBloqueio'))
            return False
        return isinstance(res, dict)

    def transicoes(self, id_tarefa: int) -> List[Dict[str, Any]]:
        dados = self._chamar('GET', f'/tarefas/{id_tarefa}/transicoes')
        return dados if isinstance(dados, list) else []

    def transitar_direto(self, id_tarefa: int, destino: str) -> Optional[Dict[str, Any]]:
        """Executa `POST /transicoes` sem `PUT` redundante (validado ao vivo em 175ms)."""
        corpo = _json.dumps({'idProcesso': self.id, 'idTarefaOrigem': id_tarefa,
                             'nomeTransicaoDestino': destino}, ensure_ascii=False)
        res = self._chamar('POST', f'/tarefas/{id_tarefa}/transicoes', corpo, 'application/json')
        return res if isinstance(res, dict) and res.get('idTarefa') else None

    def encerrar_sobrestamento(self, id_tarefa: int = 333) -> Optional[Dict[str, Any]]:
        """Encerra todos os motivos de sobrestamento via POST /sobrestamentos/tarefa/333/ → Análise (500)."""
        res = self._chamar('POST', f'/sobrestamentos/tarefa/{id_tarefa}/', '{}', 'application/json')
        return res if isinstance(res, dict) and res.get('idTarefa') else None

    def dados_conclusao(self) -> Optional[Dict[str, Any]]:
        """Retorna `idMagistradoSugerido` e `tipos` em uma única chamada GET."""
        mags = self._chamar('GET', f'/tarefas/{TAREFA_CONCLUSAO}/conclusao/magistrados')
        if not isinstance(mags, dict):
            return None
        if not isinstance(mags.get('tipos'), list) or not mags.get('tipos'):
            tipos = self._chamar('GET', f'/tarefas/{TAREFA_CONCLUSAO}/conclusao/tipos')
            if isinstance(tipos, list):
                mags['tipos'] = tipos
        return mags

    def concluir_direto(self, titulo: str, id_mag: Any) -> Optional[Dict[str, Any]]:
        """Executa `POST /tarefas/502/conclusao` sem `PUT` redundante."""
        corpo = urlencode({'tituloConclusao': titulo, 'idMagistrado': str(id_mag)})
        res = self._chamar('POST', f'/tarefas/{TAREFA_CONCLUSAO}/conclusao', corpo,
                           'application/x-www-form-urlencoded;charset=UTF-8')
        return res if isinstance(res, dict) and res.get('idTarefa') else None

    def url_tarefa(self, tarefa: Dict[str, Any], sufixo_padrao: str = '/minutar') -> str:
        caminho = tarefa.get('caminhoRecursoTarefa') or f'/processo/{{id}}/tarefa/{{idTarefa}}{sufixo_padrao}'
        caminho = caminho.replace('{id}', str(self.id)).replace('{idTarefa}', str(tarefa['idTarefa']))
        return f'{self.base}/pjekz{caminho}'


def _achar_transicao(transicoes: List[Dict[str, Any]], nome: str) -> Optional[str]:
    alvo = _norm(nome)
    if not alvo:
        return None
    disponiveis = [t for t in transicoes if t.get('transicaoDisponivel') and t.get('nomeTransicaoDestino')]
    for criterio in (lambda n: n == alvo, lambda n: n.startswith(alvo), lambda n: alvo in n):
        for t in disponiveis:
            if criterio(_norm(t['nomeTransicaoDestino'])):
                return t['nomeTransicaoDestino']
    return None


def _atualizar_estado_driver(driver: Any, id_proc: int, tarefa: Dict[str, Any]) -> None:
    import time as _time
    try:
        nome = tarefa.get('nomeTarefa') or ''
        driver.pje_tarefa_atual = nome
        driver.pje_tarefa_pronta = None
        if tarefa.get('idTarefa'):
            driver._pje_cache_tarefa_api = (str(id_proc), tarefa['idTarefa'], nome, _time.monotonic())
    except Exception:
        pass


def navegar_cls_api(
    driver: Any,
    conclusao_tipo: str,
    conclusao_api: Optional[str] = None,
    max_saltos: int = 3,
    abrir_se_elaborar: bool = False,
) -> Optional[str]:
    """Leva o processo até a minuta do `conclusao_tipo`/`conclusao_api` com o mínimo de chamadas HTTP.

    Retorna:
      'minutar'  — processo concluso e navegador posicionado na URL da minuta;
      'assinar'  — processo já em Assinar (ato cumprido);
      'elaborar' — processo já estava em Elaborar (minuta pré-existente, não sobrescreve);
      None       — não foi possível (o chamador deve seguir pelo fluxo DOM).
    """
    if not (hasattr(driver, 'context') and hasattr(driver, 'page')):
        return None
    m = _RE_ID_PROCESSO.search(driver.current_url or '')
    if not m:
        return None
    api = _ApiTarefas(driver, int(m.group(1)))

    tarefa = api.tarefa_atual()
    if not tarefa or not isinstance(tarefa.get('idTarefa'), int):
        return None
    id_t = tarefa['idTarefa']
    logger.info('[CLS-API] Tarefa inicial: %s %s', id_t, tarefa.get('nomeTarefa'))

    if id_t in TAREFAS_ASSINAR:
        return 'assinar'
    if id_t in TAREFAS_MINUTAR:
        if '/minutar' in (driver.current_url or '').lower():
            return 'minutar'
        if abrir_se_elaborar:
            _atualizar_estado_driver(driver, api.id, tarefa)
            driver.get(api.url_tarefa(tarefa, sufixo_padrao='/minutar'))
            return 'minutar'
        return 'elaborar'

    if not api.verificar_bloqueio(id_t):
        return None

    # Roteamento jBPM até 502 (Conclusão ao magistrado):
    # - De Análise (500), dispara POST direto sem GET /transicoes (economiza 1 RTT).
    # - De outros nós (ex.: 491, 511, 521), consulta GET /transicoes e vai direto a 502 ou via 500.
    for _ in range(max_saltos):
        if id_t == TAREFA_CONCLUSAO:
            break
        if id_t == 333:
            nova = api.encerrar_sobrestamento(id_t)
            if not nova:
                logger.warning('[CLS-API] Falha ao encerrar sobrestamento (tarefa %s) — fallback DOM', id_t)
                return None
            logger.info('[CLS-API] Sobrestamento encerrado: %s → %s %s', id_t, nova['idTarefa'], nova.get('nomeTarefa'))
            id_t = nova['idTarefa']
            continue
        if id_t == TAREFA_ANALISE:
            nova = api.transitar_direto(id_t, TRANSICAO_CONCLUSAO)
            if nova:
                logger.info('[CLS-API] %s → %s %s', id_t, nova['idTarefa'], nova.get('nomeTarefa'))
                id_t = nova['idTarefa']
                continue
        trs = api.transicoes(id_t)
        destino = _achar_transicao(trs, TRANSICAO_CONCLUSAO) or _achar_transicao(trs, TRANSICAO_ANALISE)
        if not destino:
            logger.info('[CLS-API] Tarefa %s sem rota para conclusão/análise — fallback DOM', id_t)
            return None
        nova = api.transitar_direto(id_t, destino)
        if not nova:
            return None
        logger.info('[CLS-API] %s → %s %s', id_t, nova['idTarefa'], nova.get('nomeTarefa'))
        id_t = nova['idTarefa']

    if id_t != TAREFA_CONCLUSAO:
        return None

    dados_conc = api.dados_conclusao()
    if not dados_conc:
        return None
    id_mag = dados_conc.get('idMagistradoSugerido')
    if not id_mag:
        logger.warning('[CLS-API] Sem magistrado sugerido para a conclusão')
        return None

    tipo = resolver_tipo_conclusao(dados_conc.get('tipos') or [], conclusao_tipo, conclusao_api=conclusao_api)
    if not tipo:
        logger.warning('[CLS-API] Tipo "%s" (api=%r) não encontrado/habilitado', conclusao_tipo, conclusao_api)
        return None

    esperado = destino_do_tipo(tipo)
    minuta = api.concluir_direto(tipo['nomeBotao'], id_mag)
    if not minuta:
        return None
    if esperado and minuta['idTarefa'] != esperado:
        logger.warning('[CLS-API] Destino divergente do mapa: %s (esperado %s)', minuta['idTarefa'], esperado)
    logger.info('[CLS-API] Concluso "%s" → %s %s (%d chamadas HTTP)',
                tipo['nomeBotao'], minuta['idTarefa'], minuta.get('nomeTarefa'), api.chamadas)

    _atualizar_estado_driver(driver, api.id, minuta)
    driver.get(api.url_tarefa(minuta, sufixo_padrao='/minutar'))
    return 'minutar'


def transitar_tarefa_api(
    driver: Any,
    destino_transicao: str,
    abrir_url: bool = True,
    max_saltos: int = 2,
) -> Optional[Dict[str, Any]]:
    """Transita via API para qualquer botão de tarefa (ex.: 'Comunicações e expedientes', 'Sobrestamento').

    Se o nó atual não tiver `destino_transicao` direto, roteia por `Análise` (`500`) automaticamente.
    Retorna:
      - `dict` da tarefa final (com chave extra `_status_api` em `{'transitada', 'ja_no_destino',
        'prazo_ja_em_analise', 'bloqueado_regra'}`);
      - `None` se o driver não suportar API ou se a rota exigir fallback para o DOM.
    """
    if not destino_transicao or '?' in destino_transicao:
        return None
    if not (hasattr(driver, 'context') and hasattr(driver, 'page')):
        return None
    m = _RE_ID_PROCESSO.search(driver.current_url or '')
    if not m:
        return None
    api = _ApiTarefas(driver, int(m.group(1)))
    tarefa = api.tarefa_atual()
    if not tarefa or not isinstance(tarefa.get('idTarefa'), int):
        return None

    nome_atual_norm = _norm_tarefa_equivalente(tarefa.get('nomeTarefa', ''))
    destino_norm = _norm_tarefa_equivalente(destino_transicao)
    if not destino_norm:
        return None

    if destino_norm in nome_atual_norm:
        res = dict(tarefa, _status_api='ja_no_destino')
        _atualizar_estado_driver(driver, api.id, res)
        if abrir_url and f"/tarefa/{tarefa['idTarefa']}" not in (driver.current_url or ''):
            driver.get(api.url_tarefa(tarefa, sufixo_padrao=''))
        logger.info('[MOV-API] Processo já em "%s" (id=%s)', tarefa.get('nomeTarefa'), tarefa['idTarefa'])
        return res

    # Regras de segurança inegociáveis (paridade com movimentar_inteligente / _deve_interromper_movimento):
    if (
        tarefa['idTarefa'] in TAREFAS_MINUTAR
        or tarefa['idTarefa'] in TAREFAS_ASSINAR
        or 'elaborar' in nome_atual_norm
        or 'assinar' in nome_atual_norm
        or 'controle de acordo' in nome_atual_norm
    ):
        logger.warning('[MOV-API] Movimento bloqueado por regra de segurança na tarefa "%s"', tarefa.get('nomeTarefa'))
        return dict(tarefa, _status_api='bloqueado_regra')

    if not api.verificar_bloqueio(tarefa['idTarefa']):
        return None

    eh_destino_prazo = 'aguardando prazo' in destino_norm or destino_norm == 'prazo'
    atual = tarefa
    for _ in range(max_saltos):
        id_t = atual['idTarefa']
        trs = api.transicoes(id_t)
        passo = _achar_transicao(trs, destino_transicao)
        if not passo:
            if id_t == TAREFA_ANALISE and eh_destino_prazo:
                logger.info('[MOV-API] Em Análise e "Aguardando prazo" indisponível — mantendo em Análise (LEGADO L4869)')
                res = dict(atual, _status_api='prazo_ja_em_analise')
                _atualizar_estado_driver(driver, api.id, res)
                return res
            if id_t == TAREFA_ANALISE:
                return None
            passo = _achar_transicao(trs, TRANSICAO_ANALISE)
            if not passo:
                return None

        nova = api.transitar_direto(id_t, passo)
        if not nova:
            return None
        logger.info('[MOV-API] %s → %s %s', id_t, nova['idTarefa'], nova.get('nomeTarefa'))
        atual = nova

        passo_norm = _norm_tarefa_equivalente(passo)
        nome_novo_norm = _norm_tarefa_equivalente(atual.get('nomeTarefa', ''))
        if destino_norm in passo_norm or destino_norm in nome_novo_norm:
            res = dict(atual, _status_api='transitada')
            _atualizar_estado_driver(driver, api.id, res)
            if abrir_url:
                driver.get(api.url_tarefa(atual, sufixo_padrao=''))
            return res
    return None


__all__ = [
    'CONCLUSAO_API',
    'ALIASES_WRAPPER_CONCLUSAO',
    'MAPA_BOTOES_ANALISE',
    'DESTINO_POR_FAMILIA',
    'TAREFAS_MINUTAR',
    'TAREFAS_ASSINAR',
    'cls_api_habilitada',
    'extrair_destino_de_seletor',
    'resolver_tipo_conclusao',
    'destino_do_tipo',
    'navegar_cls_api',
    'transitar_tarefa_api',
]
