# -*- coding: utf-8 -*-
"""
adv.py — Fluxo CHIPADV (chip "Advogado impedido de Atuar").

Sequência definida pelo Silas (11/11/2026, ajustada em 12/11/2026):

  0. driver já criado/logado pelo pw.py → navega para meu-painel
  1. API: processos marcados com o chip "Advogado impedido de Atuar"
       GET /pje-administracao-api/api/consultaprocessosadm
           ?idEtiqueta=918&idsOrgaosJulgadores=187&naoValidar=true
     É a mesma consulta administrativa que a tela usa — `idEtiqueta` é o
     chip. Não existe mais a varredura em lote do agrupamento de tarefas
     (`/agrupamentotarefas/processos/todos`) + `/etiquetasprocessos`.
     Uma página por vez, sob demanda: o total vem em `totalRegistros` e os
     processos são processados UM A UM.
     FILTRO = SÓ O CHIP (`idEtiqueta`) no recorte da consulta (OJ 187).
     Nada de fase processual, responsável ou tipo de atividade.
  2. o total é informado no log antes do primeiro processo
  3. partes do processo pela API (/pje-comum-api/api/processos/id/{id}/partes)
     com `comInativas=true` → TODOS os representantes (ADVOGADO/OAB), ativos
     E inativos. Os inativos são a causa clássica do chip "Advogado impedido".
  4. (PENDENTE) OAB live: POST
     /pje-comum-api/api/pessoas/fisicas/{idPessoa}/validacaooab
     ?especializacao=Advogado — o mesmo POST do dialog "Validar na OAB".
     A leitura dos inativos já é feita no passo 3, mas a REGRA DO LAÇO ainda
     não foi fechada; por ora o passo 4/5 usa o primeiro advogado ATIVO e a
     validação antiga.
  5. CPF do advogado escolhido
  6. validar_cadastro(): /pjekz/pessoa-fisica → CPF → Enter → lápis →
     aba "Advogado" → "Validar na OAB" → radio SP (ou 1ª opção) → Gravar →
     fecha a aba. Se o dialog NÃO tiver radio selecionável, o cadastro está
     SUSPENSO na OAB (a tabela traz Situação = Suspenso) — reporta e segue.
  7. laço ÚNICO, escolhido pelo resultado da validação (passo 6):
       'ok'       (achou radio SP ou outra inscrição) → reprocessar chips
       'suspenso' (só cadastro suspenso)              → criar_gigs "Advogado
                                                         suspenso"
     Nos dois casos: consulta por CPF + chip na MESMA API
     (`cpf` + `idEtiqueta` + `idsOrgaosJulgadores`), total informado, cada
     processo aberto direto em /pjekz/processo/{id}/detalhe → ação → fecha
     a aba.

Registro da execução:
     o CPF tratado é anotado (independente do laço) junto com todos os
     processos cobertos pelo lote dele. Se o mesmo CPF — ou um processo já
     coberto pelo lote — reaparecer, o fluxo pula: o lote já resolveu aquele
     advogado e o processo repetido é informação desatualizada.
  → recomeça com o próximo processo da API

Nada aqui abre driver nem faz login: quem chama é o x.py/pw.py.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from Fix import espera
from Fix.core import (
    _executar_js,
    esperar_elemento,
    preencher_campo,
    safe_click_no_scroll,
)
from Fix.browser_suporte import _obter_window_handles, abrir_url_nova_aba
from Fix.log import logger

# =============================================================================
# Constantes
# =============================================================================

URL_PAINEL = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
URL_PESSOA_FISICA = 'https://pje.trt2.jus.br/pjekz/pessoa-fisica'

# Consulta administrativa usada pela tela /administracao/consulta/processo.
# É a chamada que filtra pelo chip: `idEtiqueta` = id do chip.
URL_CONSULTA_API = '/pje-administracao-api/api/consultaprocessosadm'

# Reprocessamento de chips (GET calcula diff; POST aplica o array enviado).
URL_REPROCESSAMENTO_ETIQUETAS_API = '/pje-etiquetas-api/api/reprocessamentoetiquetas/{id}'

# Etiquetas (chips) efetivamente presentes no processo.
URL_ETIQUETAS_PROCESSO_API = '/pje-etiquetas-api/api/processos/{id}/etiquetas'

# Alteração de situação de parte/representante na autuação (PUT: 'A' | 'I' | 'S').
URL_PARTES_SITUACAO_API = '/pje-comum-api/api/processos/id/{id}/partes/situacao'

# Tarefa mais recente do processo (mesmo endpoint usado no P2B / movimentos_fluxo).
URL_TAREFAS_PROCESSO_API = '/pje-comum-api/api/processos/id/{id}/tarefas'

# Validação na OAB (POST consulta/valida; PUT grava inscrição específica).
URL_VALIDACAO_OAB_API = '/pje-comum-api/api/pessoas/fisicas/{id}/validacaooab'
URL_PESSOA_FISICA_CPF_API = '/pje-comum-api/api/pessoas/fisicas/cpf/{cpf}'

# Recorte fixo da consulta (3ª Vara / OJ 187). Sem o `idsOrgaosJulgadores`
# o PJe ignora o `idEtiqueta` e devolve a base inteira.
ORGAO_JULGADOR_CONSULTA = 187

# Aba /detalhe aberta direto pelo id interno devolvido pela consulta.
URL_PROCESSO_DETALHE = 'https://pje.trt2.jus.br/pjekz/processo/{id}/detalhe'

# Id da etiqueta (chip) "Advogado impedido de Atuar".
CHIP_ADVOGADO_IMPEDIDO_ID = 918

# Tarefas / etiquetas consideradas "arquivado" (limpeza direta sem certidão/ato).
TAREFAS_ARQUIVO = (
    'arquivo',
    'arquivado',
    'arquivados',
    'arquivo definitivo',
    'cartas devolvidas',
    'carta devolvida',
)

TAMANHO_PAGINA_API = 100
MAX_WORKERS_REPROC = 6


# =============================================================================
# Exceção de sessão expirada (401)
# =============================================================================

class SessaoExpiradaError(Exception):
    """Lançada quando qualquer chamada API retorna 401 (token expirado)."""


def _eh_erro_401(res: Any) -> bool:
    """True quando resposta do gateway indica HTTP 401 / token expirado."""
    if not isinstance(res, dict) or res.get('ok'):
        return False
    err = res.get('error') or {}
    if isinstance(err, dict):
        if _inteiro(err.get('status'), 0) == 401:
            return True
        msg = str(err.get('message') or '').lower()
    else:
        msg = str(err).lower()
    return (
        'sjt-api-027' in msg
        or 'token enviado está expirado' in msg
        or 'token enviado esta expirado' in msg
        or 'sessao_expirada_401' in msg
    )


def _checar_401(res: Any, contexto: str = '') -> None:
    """Dispara `SessaoExpiradaError` imediatamente se a API devolveu 401."""
    if _eh_erro_401(res):
        raise SessaoExpiradaError(f'API retornou 401 ({contexto})')


# =============================================================================
# Helpers
# =============================================================================

def _somente_digitos(valor: Any) -> str:
    """CPF/CNPJ só com dígitos (a API devolve '123.456.789-00')."""
    return re.sub(r'\D', '', str(valor or ''))


def _inteiro(valor: Any, padrao: int = 0) -> int:
    """Converte contadores da API para int sem explodir com None/string."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _partir_oab(numero_oab: Any) -> tuple:
    """'SP128341' / 'PE22616' / 'AP1551-A' / 'OAB/SP 128.341' -> ('SP', 128341)."""
    texto = re.sub(r'[.\s]+', '', str(numero_oab or ''))
    m = re.match(r'(?:OAB/?)?([A-Za-z]{2})[-/]?(\d+)', texto, re.IGNORECASE)
    if not m:
        return None, None
    return m.group(1).upper(), _inteiro(m.group(2), 0)


def _digitos_oab(numero_oab: Any) -> str:
    """Apenas os dígitos significativos (sem zeros à esquerda) de uma OAB."""
    d = re.sub(r'\D', '', str(numero_oab or ''))
    return d.lstrip('0') or d


def _match_radio_oab(radios_info: List[Dict[str, Any]], oab_alvo: Any) -> Optional[Dict[str, Any]]:
    """Matching puro de uma OAB contra os radios regulares/habilitados do dialog.

    Ordem de aproximação:
      1. Exato: mesma UF + mesmo número.
      2. Aproximação de número: mesmo número (independente de UF/letra/sufixo)
         ou sufixo/prefixo numérico com mesma UF.
      3. Aproximação de letras: mesma UF quando só há 1 inscrição regular nessa UF.
    """
    if not oab_alvo or not radios_info:
        return None
    alvo_uf, alvo_num = _partir_oab(oab_alvo)
    alvo_dig = _digitos_oab(oab_alvo)

    # 1. Match exato (UF + número)
    if alvo_uf and alvo_num:
        for r in radios_info:
            if r['uf'] == alvo_uf and r['num'] == alvo_num:
                return r

    # 2a. Mesmo número (sem zeros à esquerda), mesmo que UF/letra difira
    if alvo_dig and len(alvo_dig) >= 3:
        mesmos_num = [r for r in radios_info if r['dig'] == alvo_dig]
        if mesmos_num:
            if alvo_uf:
                for r in mesmos_num:
                    if r['uf'] == alvo_uf:
                        return r
            return mesmos_num[0]

    # 2b. Número aproximado (contido ou difere por 1 dígito/sufixo) na mesma UF
    if alvo_uf and alvo_dig and len(alvo_dig) >= 3:
        for r in radios_info:
            if r['uf'] == alvo_uf and r['dig'] and (
                alvo_dig in r['dig'] or r['dig'] in alvo_dig
            ):
                return r

    # 3. Mesma UF única entre as regulares
    if alvo_uf:
        da_uf = [r for r in radios_info if r['uf'] == alvo_uf]
        if len(da_uf) == 1:
            return da_uf[0]

    return None


def _representante_ativo(rep: Dict[str, Any]) -> bool:
    """Ativo/inativo do representante no /partes.

    O PJe marca `status` = 'A' para ativo; `situacao` = 'Inativo' aparece nas
    partes inativas (que só vêm com `comInativas=true`).
    """
    status = str(rep.get('status') or '').strip().upper()
    if status:
        return status == 'A'
    situacao = str(rep.get('situacao') or '').strip().lower()
    return situacao in ('', 'ativo')


def _texto_normalizado(valor: Any) -> str:
    """Normaliza texto para comparação (sem acento/caixa/espaço extra)."""
    try:
        from Fix.utils import normalizar_texto
        return normalizar_texto(valor or '')
    except Exception:
        return str(valor or '').strip().lower()


def _elemento_por_texto(driver: Any, seletor: str, texto: str,
                        teto: float = 10.0) -> Optional[Any]:
    """Acha o elemento de `seletor` cujo texto contém `texto`.

    `esperar_elemento(..., texto=)` espera ALGUM elemento casar e devolve o
    PRIMEIRO da lista — que pode não ser o que tem o texto (ex.: `button` numa
    tela com vários botões). Aqui a espera é a mesma (`espera.ate_texto`) e a
    escolha é feita elemento por elemento.
    """
    alvo = _texto_normalizado(texto)
    if not espera.ate_texto(driver, seletor, texto, teto=teto):
        return None
    for el in espera.elementos(driver, seletor, teto=1):
        try:
            if alvo in _texto_normalizado(el.text):
                return el
        except Exception:
            continue
    return None


def _pressionar_enter(driver: Any) -> bool:
    """Enter no teclado do navegador (com fallback no próprio campo)."""
    page = getattr(driver, 'page', None)
    if page is not None:
        try:
            page.keyboard.press('Enter')
            return True
        except Exception:
            pass
    try:
        return bool(_executar_js(
            driver,
            "const el = document.querySelector('input[name=\"cpf\"]');"
            "if (!el) return false;"
            "['keydown','keypress','keyup'].forEach(function(t){"
            "  el.dispatchEvent(new KeyboardEvent(t, {key:'Enter', code:'Enter',"
            "    keyCode:13, which:13, bubbles:true}));"
            "});"
            "return true;",
        ))
    except Exception:
        return False


def _fechar_aba(driver: Any, handle: Optional[str], principal: Optional[str]) -> None:
    """Fecha `handle` (só se houver mais de uma aba) e volta o foco."""
    try:
        handles = list(_obter_window_handles(driver) or [])
        if handle and handle in handles and len(handles) > 1:
            driver.switch_to.window(handle)
            driver.close()
    except Exception as e:
        logger.warning('[CHIPADV] Falha ao fechar aba: %s', e)
    try:
        handles = list(_obter_window_handles(driver) or [])
        if principal in handles:
            driver.switch_to.window(principal)
        elif handles:
            driver.switch_to.window(handles[0])
    except Exception:
        pass


# =============================================================================
# 1. API — processos com o chip
# =============================================================================

def _criar_client(driver: Any):
    """PjeApiClient a partir da sessão do driver (mesmo caminho do bianca)."""
    from Fix.variaveis import PjeApiClient, session_from_driver
    sess, base_url = session_from_driver(driver)
    return PjeApiClient(sess, base_url)


def _consultar_processos(client: Any, chip_id: int, *, cpf: Optional[str] = None,
                         pagina: int = 1,
                         tamanho_pagina: int = TAMANHO_PAGINA_API) -> Optional[Dict[str, Any]]:
    """Uma página da consulta administrativa filtrada pelo chip.

    `GET /pje-administracao-api/api/consultaprocessosadm` é a chamada que a
    própria tela de consulta faz; `idEtiqueta` é o chip. `naoValidar=true` é
    o que a tela envia para liberar a busca só com o chip (sem parte, CPF,
    número ou OAB).

    Devolve o payload (`resultado`, `totalRegistros`, `qtdPaginas`) ou None
    em caso de falha.
    """
    params = {
        'pagina': pagina,
        'tamanhoPagina': tamanho_pagina,
        # Libera a consulta só pelo chip, como a tela faz ao paginar.
        'naoValidar': 'true',
        # Ordenação fixa: sem ela o PJe não garante ordem estável entre
        # páginas e um processo poderia aparecer duas vezes (ou sumir).
        'ordenacaoColuna': 'numero',
        'ordenacaoCrescente': 'true',
        'idEtiqueta': int(chip_id),
        # Sem o OJ o PJe ignora o idEtiqueta e devolve a base inteira.
        'idsOrgaosJulgadores': ORGAO_JULGADOR_CONSULTA,
    }
    if cpf:
        params['cpf'] = _somente_digitos(cpf)

    res = client.gateway_get(URL_CONSULTA_API, params=params, timeout=60)
    _checar_401(res, f'consultaprocessosadm p{pagina}')
    if not res.get('ok'):
        logger.error('[CHIPADV][API] consulta chip %s p%d: %s',
                     chip_id, pagina, res.get('error'))
        return None
    dados = res.get('data')
    if not isinstance(dados, dict):
        logger.error('[CHIPADV][API] resposta inesperada na consulta p%d: %r',
                     pagina, dados)
        return None
    return dados


def iniciar_busca_processos_por_chip(client: Any, chip_id: int,
                                     tamanho_pagina: int = TAMANHO_PAGINA_API):
    """Primeira página + total do chip; páginas seguintes sob demanda.

    Devolve `(total, iterador)`. A primeira página já traz `totalRegistros`,
    então o total é informado ANTES de processar o primeiro processo; as
    demais páginas só são buscadas quando o iterador avança. Não há carga
    inicial em lote — cada processo é tratado um por vez.
    """
    dados = _consultar_processos(client, chip_id, pagina=1,
                                 tamanho_pagina=tamanho_pagina)
    if dados is None:
        return 0, iter(())

    itens = dados.get('resultado') or []
    total = _inteiro(dados.get('totalRegistros'), len(itens))
    qtd_paginas = _inteiro(dados.get('qtdPaginas'), 1)
    logger.info('[CHIPADV][API] %d processo(s) com o chip %s (OJ %s) — '
                'processando um por vez', total, chip_id, ORGAO_JULGADOR_CONSULTA)

    def _iterar():
        yield from itens
        for pagina in range(2, qtd_paginas + 1):
            proxima = _consultar_processos(client, chip_id, pagina=pagina,
                                           tamanho_pagina=tamanho_pagina)
            if not proxima:
                return
            lista = proxima.get('resultado') or []
            if not lista:
                return
            logger.info('[CHIPADV][API] p%d/%d: %d processo(s)',
                        pagina, qtd_paginas, len(lista))
            yield from lista

    return total, _iterar()


# =============================================================================
# 3. Partes → advogados (por vínculo parte × representante)
# =============================================================================

def _eh_situacao_regular_ou_ausente(situacao_oab: Any) -> bool:
    """True para REGULAR ou ausente (que tende a se regularizar no tratamento)."""
    s = str(situacao_oab or '').strip().upper()
    return s in ('', 'REGULAR')


def _eh_advogado_com_pendencia_pje(adv: Dict[str, Any]) -> bool:
    """True quando a API de partes não traz `situacaoOab == 'REGULAR'`."""
    s = str(adv.get('situacao_oab') or '').strip().upper()
    return s != 'REGULAR'


def ler_vinculos_advogados(client: Any, id_processo: Any,
                           com_inativas: bool = True) -> List[Dict[str, Any]]:
    """Todos os vínculos (parte × advogado) do processo, pela API de partes.

    Mantém `parte_id`, `parte_ativa`, `id_parte_rep` e `tem_outro_regular`
    (outro advogado ativo na mesma parte com `situacaoOab` REGULAR ou ausente),
    necessários tanto para o PUT `/partes/situacao` quanto para a regra do
    Ramo 3 (certidão `anex_advdelete` vs GIGS + `ato_regadv`).
    """
    try:
        partes = client.partes(str(id_processo), com_inativas=com_inativas) or {}
    except PermissionError as e:
        raise SessaoExpiradaError(f'partes({id_processo}): {e}') from e
    if isinstance(partes, dict) and isinstance(partes.get('resultado'), dict):
        partes = partes['resultado']
    if (com_inativas and isinstance(partes, dict)
            and not any(partes.get(p) for p in ('ATIVO', 'PASSIVO', 'TERCEIROS'))):
        try:
            partes = client.partes(str(id_processo)) or {}
        except PermissionError as e:
            raise SessaoExpiradaError(f'partes({id_processo}): {e}') from e
        if isinstance(partes, dict) and isinstance(partes.get('resultado'), dict):
            partes = partes['resultado']
    if not isinstance(partes, dict):
        logger.warning('[CHIPADV][PARTES] Payload inesperado para o processo %s', id_processo)
        return []

    vinculos: List[Dict[str, Any]] = []
    for polo in ('ATIVO', 'PASSIVO', 'TERCEIROS'):
        for parte in (partes.get(polo) or []):
            if not isinstance(parte, dict):
                continue
            parte_id = parte.get('id')
            parte_id_pessoa = parte.get('idPessoa')
            parte_nome = (parte.get('nome') or '').strip()
            parte_ativa = _representante_ativo(parte)
            parte_domicilio_inline = (
                parte.get('domicilioEletronico') is True
                or parte.get('possuiDomicilioEletronico') is True
            )

            reps_parte: List[Dict[str, Any]] = []
            for rep in (parte.get('representantes') or []):
                if not isinstance(rep, dict):
                    continue
                tipo = str(rep.get('tipo') or '').upper()
                oab = rep.get('numeroOab') or ''
                if 'ADVOGADO' not in tipo and 'OAB' not in tipo and not oab:
                    continue
                cpf = _somente_digitos(rep.get('documento') or rep.get('cpf'))
                if not cpf:
                    continue
                reps_parte.append({
                    'id_parte_rep': rep.get('id'),
                    'parte_id': parte_id,
                    'parte_id_pessoa': parte_id_pessoa,
                    'parte_domicilio_inline': parte_domicilio_inline,
                    'parte': parte_nome,
                    'parte_ativa': parte_ativa,
                    'polo': polo,
                    'nome': (rep.get('nome') or '').strip(),
                    'cpf': cpf,
                    'oab': oab,
                    'id_pessoa': rep.get('idPessoa') or rep.get('id'),
                    'status': rep.get('status') or '',
                    'situacao': rep.get('situacao') or '',
                    'ativo': _representante_ativo(rep),
                    'situacao_oab': (rep.get('situacaoOab') or '').strip().upper(),
                    'tipo': tipo,
                })

            # Para cada representante da parte, marca se há OUTRO advogado ativo
            # na mesma parte com situacaoOab REGULAR ou ausente.
            for r in reps_parte:
                r['tem_outro_regular'] = any(
                    outro['cpf'] != r['cpf']
                    and outro['ativo']
                    and _eh_situacao_regular_ou_ausente(outro['situacao_oab'])
                    for outro in reps_parte
                )
                vinculos.append(r)

    return vinculos


def ler_advogados_do_processo(client: Any, id_processo: Any,
                              com_inativas: bool = True) -> List[Dict[str, Any]]:
    """Lista deduplicada por CPF dos advogados do processo (compatibilidade)."""
    vinculos = ler_vinculos_advogados(client, id_processo, com_inativas=com_inativas)
    advogados: List[Dict[str, Any]] = []
    vistos = set()
    for v in vinculos:
        if v['cpf'] in vistos:
            continue
        vistos.add(v['cpf'])
        advogados.append(v)
    return advogados


# =============================================================================
# 4. Resolução de OAB alvo (timeline) e wrappers de atos/juntada
# =============================================================================

_UFS_VALIDAS = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO',
}

_RE_OAB_NO_TEXTO = re.compile(
    r'\bOAB\s*[/:\-\s]*(?:([A-Z]{2})\s*[/:\-\s]*)?(?:n[º°o.]*\s*)?(\d{1,3}(?:\.\d{3})+|\d{3,7})(?:\s*[-/]\s*([A-Z]{1,2}))?',
    re.IGNORECASE,
)

_RE_OAB_NUM_UF = re.compile(
    r'\bOAB\s*(?:n[º°o.]*\s*)?(\d{1,3}(?:\.\d{3})+|\d{3,7})\s*[/\-]\s*([A-Z]{2})\b',
    re.IGNORECASE,
)

_TIPOS_PECA_PRIORITARIOS = (
    'peticao', 'manifestacao', 'procuracao', 'substabelecimento',
    'contestacao', 'recurso', 'contrarrazoes', 'impugnacao', 'embargos',
    'habilitacao', 'replica',
)


def _ler_texto_documento_api(client: Any, id_processo: Any, id_doc: Any) -> str:
    """Baixa o conteúdo de um documento da timeline via API e devolve texto plano."""
    import base64

    sess = getattr(client, 'sess', None)
    base_url = getattr(client, 'base_url', '') or 'https://pje.trt2.jus.br'
    if not base_url.startswith('http'):
        base_url = f'https://{base_url}'
    if sess is None:
        return ''

    url = (f'{base_url}/pje-comum-api/api/processos/id/{id_processo}'
           f'/documentos/id/{id_doc}/conteudo')
    try:
        r = sess.get(url, params={'incluirAssinatura': 'false', 'grau': '1'}, timeout=25)
        if r.status_code != 200:
            return ''
        raw = r.content or b''
    except Exception:
        return ''

    # Pode vir PDF direto ou JSON com {conteudoBase64} ou HTML/texto
    if raw.startswith(b'%PDF'):
        try:
            from Mandado.apoio_fluxos import _extrair_texto_pdf_bytes
            return _extrair_texto_pdf_bytes(raw, log=False) or ''
        except Exception:
            return ''

    ctype = (r.headers.get('content-type') or '').lower()
    if 'json' in ctype or raw.lstrip().startswith(b'{'):
        try:
            data = r.json()
            b64 = data.get('conteudoBase64') or data.get('conteudo') or ''
            if isinstance(b64, str) and b64:
                dec = base64.b64decode(b64)
                if dec.startswith(b'%PDF'):
                    from Mandado.apoio_fluxos import _extrair_texto_pdf_bytes
                    return _extrair_texto_pdf_bytes(dec, log=False) or ''
                txt = dec.decode('utf-8', errors='ignore')
                return re.sub(r'<[^>]+>', ' ', txt)
        except Exception:
            return ''

    txt = raw.decode('utf-8', errors='ignore')
    return re.sub(r'<[^>]+>', ' ', txt)


def _extrair_oabs_proximas_ao_nome(texto: str, nome_adv: str, janela: int = 260) -> List[str]:
    """Extrai OABs mencionadas próximas ao nome do advogado no texto da peça."""
    if not texto or not nome_adv:
        return []
    texto_norm = _texto_normalizado(texto)
    nome_norm = _texto_normalizado(nome_adv)
    partes_nome = [p for p in nome_norm.split() if len(p) > 2]
    if not partes_nome:
        return []

    alvos_busca = [nome_norm]
    if len(partes_nome) >= 2:
        alvos_busca.append(f'{partes_nome[0]} {partes_nome[-1]}')
        alvos_busca.append(partes_nome[-1])

    posicoes: List[int] = []
    for alvo in alvos_busca:
        idx = 0
        while (idx := texto_norm.find(alvo, idx)) != -1:
            posicoes.append(idx)
            idx += len(alvo)
        if posicoes:
            break

    if not posicoes:
        return []

    oabs: List[str] = []
    vistos = set()
    for pos in posicoes:
        ini = max(0, pos - janela)
        fim = min(len(texto), pos + len(nome_norm) + janela)
        trecho = texto[ini:fim]

        for m in _RE_OAB_NUM_UF.finditer(trecho):
            num = re.sub(r'\D', '', m.group(1))
            uf = m.group(2).upper()
            if uf in _UFS_VALIDAS and num:
                chave = f'{uf}{num}'
                if chave not in vistos:
                    vistos.add(chave)
                    oabs.append(chave)

        for m in _RE_OAB_NO_TEXTO.finditer(trecho):
            uf1 = (m.group(1) or '').upper()
            num = re.sub(r'\D', '', m.group(2) or '')
            uf2 = (m.group(3) or '').upper()
            uf = uf1 if uf1 in _UFS_VALIDAS else (uf2 if uf2 in _UFS_VALIDAS else '')
            if num:
                chave = f'{uf}{num}' if uf else num
                if chave not in vistos:
                    vistos.add(chave)
                    oabs.append(chave)
    return oabs


def resolver_oab_alvo(client: Any, advogado: Dict[str, Any],
                      id_processo: Any = None,
                      max_docs: int = 6) -> Optional[str]:
    """Passo 2 da seleção de OAB — busca na timeline as petições da parte alvo
    e extrai a OAB usada pelo advogado na peça.

    Chamada sob demanda apenas quando o Passo 1 (matching puro com a OAB do
    cadastro) não casou no dialog da OAB e o caso NÃO é inativo/arquivado.
    """
    if not id_processo or not advogado:
        return advogado.get('oab') if advogado else None

    try:
        timeline = client.timeline(str(id_processo), buscarDocumentos=True, buscarMovimentos=False) or []
    except Exception as e:
        logger.warning('[CHIPADV][OAB_TL] Falha ao ler timeline de %s: %s', id_processo, e)
        return None

    polo_alvo = str(advogado.get('polo') or '').strip().upper()
    id_pessoa = str(advogado.get('id_pessoa') or '')
    nome_adv = advogado.get('nome') or ''
    nome_adv_norm = _texto_normalizado(nome_adv)

    # Filtra peças externas (usuarioInterno == False) e ordena por relevância:
    # 1º assinadas/protocoladas pelo próprio advogado
    # 2º peças do mesmo polo (petição/manifestação/procuração/recurso...)
    candidatos_doc: List[Tuple[int, Dict[str, Any]]] = []
    for doc in timeline:
        if not isinstance(doc, dict):
            continue
        if doc.get('usuarioInterno') is True:
            continue
        id_doc = doc.get('id') or doc.get('idUnicoDocumento')
        if not id_doc:
            continue

        polo_doc = str(doc.get('tipoPolo') or '').strip().upper()
        if polo_alvo and polo_doc and polo_doc != polo_alvo:
            continue

        tipo_norm = _texto_normalizado(doc.get('tipo') or '')
        titulo_norm = _texto_normalizado(doc.get('titulo') or '')
        sig_norm = _texto_normalizado(doc.get('nomeSignatario') or '')
        resp_norm = _texto_normalizado(doc.get('nomeResponsavel') or '')

        score = 0
        if id_pessoa and (
            str(doc.get('idSignatario') or '') == id_pessoa
            or str(doc.get('idUsuario') or '') == id_pessoa
        ):
            score += 100
        elif nome_adv_norm and (nome_adv_norm in sig_norm or nome_adv_norm in resp_norm):
            score += 80
        if any(k in tipo_norm or k in titulo_norm for k in _TIPOS_PECA_PRIORITARIOS):
            score += 20
        if polo_alvo and polo_doc == polo_alvo:
            score += 10

        if score > 0:
            candidatos_doc.append((score, doc))

    candidatos_doc.sort(key=lambda x: x[0], reverse=True)

    for _, doc in candidatos_doc[:max_docs]:
        id_doc = doc.get('id') or doc.get('idUnicoDocumento')
        texto = _ler_texto_documento_api(client, id_processo, id_doc)
        if not texto:
            continue
        oabs = _extrair_oabs_proximas_ao_nome(texto, nome_adv)
        if oabs:
            logger.info('[CHIPADV][OAB_TL] OAB(s) encontrada(s) na peça %s (%s) para %s: %s',
                        id_doc, doc.get('tipo') or doc.get('titulo'), nome_adv, oabs)
            return oabs[0]

    logger.info('[CHIPADV][OAB_TL] Nenhuma OAB encontrada na timeline de %s para %s',
                id_processo, nome_adv)
    return None


def anex_advdelete(driver: Any, processo_info: Dict[str, Any],
                   advogado_alvo: Dict[str, Any]) -> bool:
    """Junta a certidão `advdelete` preenchendo `--` com empresa/advogado/CPF.

    Chamada no Ramo 3 quando o advogado apagado era ATIVO em parte ATIVA e a
    mesma parte possui outro advogado regular/ausente.
    """
    from atos.wrappers_anex import anex_advdelete as _anex_advdelete_wrapper

    vinculos = list(processo_info.get('vinculos_removidos') or [])
    if not vinculos and advogado_alvo:
        vinculos = [advogado_alvo]
    numero = str(processo_info.get('numero') or processo_info.get('id') or '')
    return bool(_anex_advdelete_wrapper(
        driver,
        numero_processo=numero,
        vinculos=vinculos,
        fechar_aba_apos=False,
    ))


def ato_regadv(driver: Any, processo_info: Dict[str, Any],
               advogado_alvo: Dict[str, Any], **kwargs: Any) -> bool:
    """Executa o despacho `regadv` quando a parte-alvo TEM domicílio eletrônico
    (`destinatario='alvo'`, `Assinar=True`).
    """
    from atos.wrappers_ato import ato_regadv as _ato_regadv_wrapper

    vinculos = list(processo_info.get('vinculos_removidos') or [])
    if not vinculos and advogado_alvo:
        vinculos = [advogado_alvo]
    sem_outro = list(processo_info.get('vinculos_sem_outro') or vinculos)
    alvos = []
    for v in sem_outro:
        if isinstance(v, dict):
            parte = (v.get('parte') or '').strip()
            if parte and parte not in alvos:
                alvos.append(parte)
    if alvos and 'destinatarios_alvo' not in kwargs:
        kwargs['destinatarios_alvo'] = alvos
    res = _ato_regadv_wrapper(driver, vinculos=vinculos, **kwargs)
    if isinstance(res, tuple):
        return bool(res[0])
    return bool(res)


def ato_regadv2(driver: Any, processo_info: Dict[str, Any],
                advogado_alvo: Dict[str, Any], **kwargs: Any) -> bool:
    """Executa o despacho `regadv` quando a parte-alvo NÃO tem domicílio eletrônico
    (`intimar=False`, `Assinar=True`, após GIGS `1,,xs dec adv`).
    """
    from atos.wrappers_ato import ato_regadv2 as _ato_regadv2_wrapper

    vinculos = list(processo_info.get('vinculos_removidos') or [])
    if not vinculos and advogado_alvo:
        vinculos = [advogado_alvo]
    res = _ato_regadv2_wrapper(driver, vinculos=vinculos, **kwargs)
    if isinstance(res, tuple):
        return bool(res[0])
    return bool(res)


# =============================================================================
# 6. Validar cadastro na OAB
# =============================================================================

def _linhas_tabela_oab(driver: Any) -> List[List[str]]:
    """Linhas da tabela de inscrições do dialog OAB, como listas de células.

    Colunas: UF | Inscrição | Tipo de Inscrição | Situação.
    """
    try:
        linhas = _executar_js(driver, """
            const dlg = document.querySelector('mat-dialog-container');
            if (!dlg) return [];
            return Array.from(dlg.querySelectorAll('table.t-class tbody tr')).map(function (tr) {
                return Array.from(tr.querySelectorAll('td')).map(function (td) {
                    return (td.textContent || '').trim();
                });
            });
        """)
    except Exception:
        return []
    return [l for l in (linhas or []) if isinstance(l, list) and l]


def _coletar_radios_regulares(driver: Any, radios: List[Any]) -> List[Dict[str, Any]]:
    """Extrai os radios habilitados/regulares do dialog OAB com UF, número e dígitos."""
    info: List[Dict[str, Any]] = []
    for radio in radios:
        try:
            if not radio.is_enabled():
                continue
        except Exception:
            pass
        try:
            rotulo = (radio.get_attribute('aria-label') or '').strip()
        except Exception:
            rotulo = ''
        uf, num = _partir_oab(rotulo)
        info.append({
            'radio': radio,
            'rotulo': rotulo,
            'uf': uf,
            'num': num,
            'dig': _digitos_oab(rotulo),
        })
    return info


def _tratar_dialog_oab(driver: Any, oab_alvo: Any = None,
                       buscar_oab_timeline: Optional[Any] = None) -> str:
    """Trata o dialog "Validar na OAB" na ordem exata de prioridade:

      1. Matching puro (exato UF+número → aproximação de número/letras) com
         `oab_alvo` (OAB do cadastro).
      2. Busca via timeline (`buscar_oab_timeline`, quando fornecida — apenas
         para advogado ativo em processo não arquivado) e matching com a OAB
         encontrada nas petições da parte alvo.
      3. Primeira regular disponível, preferindo SP se existir e for regular.

    Devolve:
      'ok'       — inscrição regular selecionada e gravada (ou validação direta)
      'suspenso' — dialog SEM radio selecionável (tabela traz Suspenso /
                   Cancelado / Impedido / Licenciado)
      'falha'    — dialog presente mas não foi possível concluir
    """
    dialogo = esperar_elemento(driver, 'mat-dialog-container pje-modal-atualizar-oab',
                               timeout=15)
    if dialogo is None:
        logger.info('[CHIPADV][VALIDAR] Sem dialog de múltiplas inscrições — validação direta')
        return 'ok'

    radios = espera.elementos(driver, 'mat-dialog-container input[type="radio"]', teto=5)
    radios_info = _coletar_radios_regulares(driver, radios) if radios else []
    if not radios_info:
        linhas = _linhas_tabela_oab(driver)
        situacoes = [l[3] for l in linhas if len(l) > 3]
        resumo = '; '.join(' | '.join(l) for l in linhas) or 'tabela vazia'
        if any(
            k in _texto_normalizado(s)
            for s in situacoes
            for k in ('suspens', 'cancel', 'imped', 'licenc', 'exclu')
        ):
            logger.error('[CHIPADV][VALIDAR] CADASTRO IMPEDIDO/SUSPENSO na OAB — %s', resumo)
            return 'suspenso'
        logger.error('[CHIPADV][VALIDAR] Dialog OAB sem inscrição selecionável — %s', resumo)
        return 'falha'

    escolhido_info = None

    # 1. Matching puro com a OAB do cadastro (UF+número / aproximação)
    if oab_alvo:
        escolhido_info = _match_radio_oab(radios_info, oab_alvo)
        if escolhido_info:
            logger.info('[CHIPADV][VALIDAR] [1-matching] Inscrição selecionada (%s -> %s)',
                        oab_alvo, escolhido_info['rotulo'])

    # 2. Busca via timeline (somente se Passo 1 não casou e callback foi fornecida)
    if escolhido_info is None and callable(buscar_oab_timeline):
        try:
            oab_tl = buscar_oab_timeline()
        except Exception as e:
            logger.warning('[CHIPADV][VALIDAR] [2-timeline] Erro ao buscar OAB na timeline: %s', e)
            oab_tl = None
        if oab_tl:
            escolhido_info = _match_radio_oab(radios_info, oab_tl)
            if escolhido_info:
                logger.info('[CHIPADV][VALIDAR] [2-timeline] Inscrição selecionada (%s -> %s)',
                            oab_tl, escolhido_info['rotulo'])
            else:
                logger.info('[CHIPADV][VALIDAR] [2-timeline] OAB da peça (%s) não está regular/selecionável — seguindo para passo 3',
                            oab_tl)

    # 3. Primeira regular disponível, preferindo SP se existir e for regular
    if escolhido_info is None:
        for r in radios_info:
            if r['uf'] == 'SP' or r['rotulo'].upper().startswith('SP'):
                escolhido_info = r
                logger.info('[CHIPADV][VALIDAR] [3-SP] Inscrição SP regular selecionada: %s',
                            r['rotulo'])
                break
    if escolhido_info is None:
        escolhido_info = radios_info[0]
        logger.info('[CHIPADV][VALIDAR] [3-fallback] Primeira inscrição regular selecionada: %s',
                    escolhido_info['rotulo'])

    escolhido = escolhido_info['radio']

    # Angular Material: o clique efetivo é no label do mat-radio-button.
    alvo = escolhido
    try:
        label = _executar_js(
            driver,
            "return arguments[0].closest('mat-radio-button')"
            ".querySelector('label.mat-radio-label');",
            escolhido,
        )
        if label is not None:
            alvo = label
    except Exception:
        pass
    safe_click_no_scroll(driver, alvo)
    espera.assentar(driver, 0.3, motivo='radio OAB')

    gravar = _elemento_por_texto(driver, 'mat-dialog-container button', 'Gravar', teto=10)
    if gravar is None:
        logger.error('[CHIPADV][VALIDAR] Botão "Gravar" do dialog OAB não encontrado')
        return 'falha'
    safe_click_no_scroll(driver, gravar)

    if not espera.ate_sumir(driver, 'mat-dialog-container pje-modal-atualizar-oab', teto=20):
        logger.error('[CHIPADV][VALIDAR] Dialog OAB não fechou após Gravar')
        return 'falha'
    return 'ok'


def _obter_id_pessoa_por_cpf(client: Any, cpf: str) -> Optional[int]:
    """Busca idPessoa via GET /pje-comum-api/api/pessoas/fisicas/cpf/{cpf}."""
    cpf_dig = _somente_digitos(cpf)
    if len(cpf_dig) != 11:
        return None
    res = client.gateway_get(URL_PESSOA_FISICA_CPF_API.format(cpf=cpf_dig), timeout=15)
    _checar_401(res, f'cpf/{cpf_dig}')
    if not res.get('ok'):
        return None
    dados = res.get('data')
    if isinstance(dados, dict) and dados.get('id'):
        return _inteiro(dados.get('id'), 0) or None
    return None


def _inscricao_oab_regular(item: Dict[str, Any]) -> bool:
    """True quando a inscrição retornada em `dadosOab` está REGULAR na OAB."""
    nome_sit = str(item.get('nomeSituacao') or '').strip().upper()
    if nome_sit:
        return nome_sit == 'REGULAR'
    return _inteiro(item.get('codigoSituacao'), 0) == 1


def validar_cadastro_api(client: Any, advogado: Dict[str, Any],
                         *,
                         buscar_oab_timeline: Optional[Any] = None) -> str:
    """Valida e atualiza a inscrição na OAB 100% via API (sem abrir /pessoa-fisica).

    Fluxo:
      1. POST /pje-comum-api/api/pessoas/fisicas/{idPessoa}/validacaooab?especializacao=Advogado
      2. Inspeciona `dadosOab` vindo direto da OAB:
         - Se NÃO há nenhuma inscrição REGULAR → retorna 'suspenso' imediatamente
           (sem perder tempo com matching/timeline/UI).
         - Se há inscrição(ões) REGULAR(ES):
             * Se `multiplasOab` é False e o POST já validou → retorna 'ok'.
             * Caso contrário, escolhe a inscrição regular na ordem exata:
                 1. Matching puro (UF+número / aproximação) com a OAB do cadastro
                 2. Busca via timeline (`buscar_oab_timeline`, quando ativo e não arquivado)
                 3. Primeira regular disponível, preferindo SP
               e grava via PUT /validacaooab/{idInscricao}?especializacao=Advogado.
    Devolve 'ok' | 'suspenso' | 'falha'.
    """
    cpf = _somente_digitos(advogado.get('cpf'))
    id_pessoa = advogado.get('id_pessoa') or _obter_id_pessoa_por_cpf(client, cpf)
    if not id_pessoa:
        logger.warning('[CHIPADV][OAB_API] Sem idPessoa para CPF %s', cpf)
        return 'falha'

    path_post = URL_VALIDACAO_OAB_API.format(id=id_pessoa)
    res_post = client.gateway_post(
        path_post,
        params={'especializacao': 'Advogado'},
        json_data={},
        timeout=25,
    )
    _checar_401(res_post, f'POST validacaooab/{id_pessoa}')
    if not res_post.get('ok'):
        logger.warning('[CHIPADV][OAB_API] POST validacaooab falhou (idPessoa=%s, CPF=%s): %s',
                       id_pessoa, cpf, res_post.get('error'))
        return 'falha'

    dados = res_post.get('data')
    if not isinstance(dados, dict):
        logger.warning('[CHIPADV][OAB_API] Resposta inesperada (idPessoa=%s): %r',
                       id_pessoa, dados)
        return 'falha'

    dados_oab = [d for d in (dados.get('dadosOab') or []) if isinstance(d, dict)]
    if not dados_oab:
        logger.warning('[CHIPADV][OAB_API] dadosOab vazio (idPessoa=%s, CPF=%s)', id_pessoa, cpf)
        return 'falha'

    regulares = [d for d in dados_oab if _inscricao_oab_regular(d)]
    if not regulares:
        situacoes = [
            f"{d.get('uf', '')}{d.get('numInscricao', '')}:{d.get('nomeSituacao', '')}"
            for d in dados_oab
        ]
        logger.info('[CHIPADV][OAB_API] Nenhuma inscrição REGULAR na OAB (CPF %s) — %s → Ramo 3',
                    cpf, ', '.join(situacoes))
        return 'suspenso'

    # Se não há múltiplas OABs e o POST já validou a única regular, está pronto!
    pessoa_oab = dados.get('pessoaOab') or {}
    if not dados.get('multiplasOab') and len(regulares) == 1 and pessoa_oab.get('validado'):
        reg = regulares[0]
        logger.info('[CHIPADV][OAB_API] Validação direta OK (CPF %s → %s%s)',
                    cpf, reg.get('uf', ''), reg.get('numInscricao', ''))
        return 'ok'

    # Monta estrutura compatível com `_match_radio_oab` só com as REGULARES
    candidatas: List[Dict[str, Any]] = []
    for d in regulares:
        uf = str(d.get('uf') or '').strip().upper()
        num_str = str(d.get('numInscricao') or '').strip()
        rotulo = f'{uf}{num_str}'
        candidatas.append({
            'item': d,
            'id': d.get('id'),
            'rotulo': rotulo,
            'uf': uf,
            'num': _inteiro(re.sub(r'\D', '', num_str), 0),
            'dig': _digitos_oab(num_str),
        })

    escolhida = None
    oab_cadastro = advogado.get('oab')

    # 1. Matching puro com a OAB do cadastro
    if oab_cadastro:
        escolhida = _match_radio_oab(candidatas, oab_cadastro)
        if escolhida:
            logger.info('[CHIPADV][OAB_API] [1-matching] %s -> %s (CPF %s)',
                        oab_cadastro, escolhida['rotulo'], cpf)

    # 2. Busca via timeline (somente se Passo 1 não casou e ativo + não arquivado)
    if escolhida is None and callable(buscar_oab_timeline):
        try:
            oab_tl = buscar_oab_timeline()
        except Exception as e:
            logger.warning('[CHIPADV][OAB_API] [2-timeline] Erro: %s', e)
            oab_tl = None
        if oab_tl:
            escolhida = _match_radio_oab(candidatas, oab_tl)
            if escolhida:
                logger.info('[CHIPADV][OAB_API] [2-timeline] %s -> %s (CPF %s)',
                            oab_tl, escolhida['rotulo'], cpf)

    # 3. Primeira regular disponível, preferindo SP
    if escolhida is None:
        for c in candidatas:
            if c['uf'] == 'SP':
                escolhida = c
                logger.info('[CHIPADV][OAB_API] [3-SP] %s selecionada (CPF %s)',
                            c['rotulo'], cpf)
                break
    if escolhida is None:
        escolhida = candidatas[0]
        logger.info('[CHIPADV][OAB_API] [3-fallback] %s selecionada (CPF %s)',
                    escolhida['rotulo'], cpf)

    id_inscricao = escolhida.get('id')
    if not id_inscricao:
        logger.warning('[CHIPADV][OAB_API] Inscrição escolhida sem id (CPF %s): %r', cpf, escolhida)
        return 'falha'

    path_put = f'{path_post}/{id_inscricao}'
    res_put = client.request_gateway(
        'PUT',
        path_put,
        params={'especializacao': 'Advogado'},
        json_data={},
        timeout=25,
    )
    _checar_401(res_put, f'PUT validacaooab/{id_pessoa}/{id_inscricao}')
    if not res_put.get('ok'):
        logger.warning('[CHIPADV][OAB_API] PUT validacaooab/%s falhou (CPF %s): %s',
                       id_inscricao, cpf, res_put.get('error'))
        return 'falha'

    logger.info('[CHIPADV][OAB_API] Inscrição %s gravada via API (CPF %s)',
                escolhida['rotulo'], cpf)
    return 'ok'


def validar_cadastro(driver: Any, cpf: str, oab_alvo: Any = None,
                     buscar_oab_timeline: Optional[Any] = None) -> str:
    """Passo 6 — valida o cadastro do advogado na OAB.

    Abre /pjekz/pessoa-fisica em ABA NOVA, pesquisa o CPF, entra no cadastro
    pelo lápis, abre a aba "Advogado", clica "Validar na OAB", escolhe a
    inscrição regular (1. matching puro → 2. timeline → 3. SP/primeira regular)
    e grava.

    Devolve 'ok' | 'suspenso' | 'falha' (ver `_tratar_dialog_oab`).
    """
    cpf = _somente_digitos(cpf)
    if len(cpf) != 11:
        logger.error('[CHIPADV][VALIDAR] CPF inválido: %r', cpf)
        return 'falha'

    principal = driver.current_window_handle
    aba = abrir_url_nova_aba(driver, URL_PESSOA_FISICA)
    if not aba:
        logger.error('[CHIPADV][VALIDAR] Não foi possível abrir /pjekz/pessoa-fisica')
        return 'falha'

    try:
        if not espera.ate_url(driver, 'pessoa-fisica', teto=30):
            logger.error('[CHIPADV][VALIDAR] Página de pessoa física não carregou')
            return 'falha'

        campo = esperar_elemento(driver, 'input[name="cpf"]', timeout=20)
        if campo is None:
            logger.error('[CHIPADV][VALIDAR] Campo CPF não encontrado')
            return 'falha'
        preencher_campo(driver, 'input[name="cpf"]', cpf, limpar=True)
        espera.assentar(driver, 0.3, motivo='cpf digitado')
        _pressionar_enter(driver)

        if not espera.ate_js(driver, "__pjeEls('table.t-class tbody tr').length > 0", teto=25):
            logger.error('[CHIPADV][VALIDAR] Lista de pessoas físicas não carregou (CPF %s)', cpf)
            return 'falha'

        lapis = esperar_elemento(driver, 'i.fa-pencil-alt', timeout=10)
        if lapis is None:
            logger.error('[CHIPADV][VALIDAR] Ícone de edição (lápis) não encontrado')
            return 'falha'
        safe_click_no_scroll(driver, lapis)

        if _elemento_por_texto(driver, 'h2', 'Pessoa Física - Cadastro', teto=25) is None:
            logger.error('[CHIPADV][VALIDAR] Cadastro da pessoa física não abriu')
            return 'falha'

        aba_adv = _elemento_por_texto(driver, 'div[role="tab"]', 'Advogado', teto=15)
        if aba_adv is None:
            logger.error('[CHIPADV][VALIDAR] Aba "Advogado" não encontrada')
            return 'falha'
        safe_click_no_scroll(driver, aba_adv)
        espera.assentar(driver, 0.5, motivo='aba advogado')

        botao = _elemento_por_texto(driver, 'button', 'Validar na OAB', teto=15)
        if botao is None:
            logger.error('[CHIPADV][VALIDAR] Botão "Validar na OAB" não encontrado')
            return 'falha'
        safe_click_no_scroll(driver, botao)

        status = _tratar_dialog_oab(
            driver, oab_alvo=oab_alvo, buscar_oab_timeline=buscar_oab_timeline
        )
        if status == 'ok':
            logger.info('[CHIPADV][VALIDAR] Cadastro validado na OAB — CPF %s', cpf)
        return status
    except Exception as e:
        logger.error('[CHIPADV][VALIDAR] Erro: %s: %s', type(e).__name__, e)
        return 'falha'
    finally:
        _fechar_aba(driver, aba, principal)


# =============================================================================
# 7. Ações via API (chips, tarefa/arquivo, inativação de parte) e /detalhe
# =============================================================================

# Chip que o reprocessamento lista para exclusão.
CHIP_TEXTO_IMPEDIDO = 'Advogado Impedido de Atuar'

# GIGS criado no Ramo 3 quando a parte ativa fica sem outro advogado regular
# e não possui domicílio eletrônico (sem opção na lista de destinatários do ato):
# → prazo '1', observação 'xs dec adv'
PRAZO_GIGS_DEC_ADV = '1'
OBS_GIGS_DEC_ADV = 'xs dec adv'


def _eh_erro_transitorio_gateway(res: Any) -> bool:
    """True para timeout de rede ou erro HTTP transitório (500/502/503/504/429)."""
    if not isinstance(res, dict) or res.get('ok'):
        return False
    err = res.get('error')
    if not isinstance(err, dict):
        return False
    status = _inteiro(err.get('status'), 0)
    if status in (429, 500, 502, 503, 504):
        return True
    tipo = str(err.get('type') or '').lower()
    msg = str(err.get('message') or '').lower()
    return any(k in tipo or k in msg for k in ('timeout', 'readtimeout', 'connecttimeout', 'connection', '502', '503', '504'))


def _esperar_retry_api(segundos: float) -> None:
    """Espera curta para backoff de retry HTTP sem usar time.sleep."""
    import threading
    threading.Event().wait(segundos)


def _listar_etiquetas_processo_api(client: Any, id_processo: Any) -> Optional[List[Dict[str, Any]]]:
    """GET rápido /pje-etiquetas-api/api/processos/{id}/etiquetas (não recalcula regras).

    Devolve lista normalizada com `idEtiqueta`, `idEtiquetaInstancia`, `idProcessoEtiqueta`
    e `nome` (usada para checar arquivamento, presença do chip e exclusão direta via POST).
    """
    path = URL_ETIQUETAS_PROCESSO_API.format(id=id_processo)
    res = client.gateway_get(path, timeout=20)
    _checar_401(res, f'GET processos/{id_processo}/etiquetas')
    if not res.get('ok'):
        return None
    dados = res.get('data')
    if not isinstance(dados, list):
        return None
    saida: List[Dict[str, Any]] = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        inst = item.get('etiquetaInstancia') or {}
        etq = inst.get('etiqueta') or {}
        eid = _inteiro(etq.get('id'), -1)
        nome = str(etq.get('nome') or '').strip()
        if eid >= 0 or nome:
            saida.append({
                'idEtiqueta': eid,
                'idEtiquetaInstancia': _inteiro(inst.get('id'), 0) or None,
                'idProcessoEtiqueta': _inteiro(item.get('id'), 0) or None,
                'nome': nome,
                'manter': True,
                'excluir': False,
            })
    return saida


def _remover_chip_direto_api(client: Any, id_processo: Any,
                             etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                             numero: Any = '',
                             *,
                             etiquetas_processo: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Remove o chip alvo enviando POST direto em /reprocessamentoetiquetas/{id}
    sem depender do GET pesado de recálculo de regras (~0.07s vs ReadTimeout 30s+).

    Só deve ser chamada quando o fluxo já confirmou que não há advogado ativo impedido.
    """
    alvo_log = numero or id_processo
    etiquetas = (etiquetas_processo if etiquetas_processo is not None
                 else _listar_etiquetas_processo_api(client, id_processo))
    if etiquetas is None:
        return False

    nome_alvo = _texto_normalizado(CHIP_TEXTO_IMPEDIDO)
    item_chip = None
    for e in etiquetas:
        if not isinstance(e, dict):
            continue
        if (_inteiro(e.get('idEtiqueta'), -1) == int(etiqueta_id)
                or (nome_alvo and nome_alvo in _texto_normalizado(e.get('nome')))):
            item_chip = e
            break

    if item_chip is None:
        logger.info('[CHIPADV][CHIPS] Chip %s já ausente em %s (removido automaticamente)',
                    etiqueta_id, alvo_log)
        return True

    payload_item: Dict[str, Any] = {
        'idEtiqueta': _inteiro(item_chip.get('idEtiqueta'), int(etiqueta_id)),
        'nome': item_chip.get('nome') or CHIP_TEXTO_IMPEDIDO,
        'incluir': False,
        'excluir': True,
        'manter': False,
    }
    if item_chip.get('idEtiquetaInstancia'):
        payload_item['idEtiquetaInstancia'] = item_chip['idEtiquetaInstancia']
    if item_chip.get('idProcessoEtiqueta'):
        payload_item['idProcessoEtiqueta'] = item_chip['idProcessoEtiqueta']

    path = URL_REPROCESSAMENTO_ETIQUETAS_API.format(id=id_processo)
    for tentativa in range(1, 3):
        res_post = client.gateway_post(path, json_data={'etiquetas': [payload_item]}, timeout=30)
        _checar_401(res_post, f'POST reprocessamentoetiquetas/{id_processo}')
        if res_post.get('ok'):
            logger.info('[CHIPADV][CHIPS] Chip %s removido via API (POST direto) em %s',
                        etiqueta_id, alvo_log)
            return True
        if _eh_erro_transitorio_gateway(res_post):
            if _processo_tem_chip(client, id_processo, etiqueta_id) is False:
                logger.info('[CHIPADV][CHIPS] Chip %s removido via API em %s (confirmado após erro transitório)',
                            etiqueta_id, alvo_log)
                return True
            if tentativa < 2:
                _esperar_retry_api(1.5)
                continue
        logger.warning('[CHIPADV][CHIPS] POST direto %s falhou: %s',
                       alvo_log, res_post.get('error'))
        return False
    return False


def _etiquetas_contem_chip(etiquetas: Optional[List[Dict[str, Any]]],
                           etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> bool:
    """True se a lista de etiquetas contém o chip `etiqueta_id` (por id ou nome)."""
    if not etiquetas:
        return False
    nome_alvo = _texto_normalizado(CHIP_TEXTO_IMPEDIDO)
    for e in etiquetas:
        if not isinstance(e, dict):
            continue
        if _inteiro(e.get('idEtiqueta'), -1) == int(etiqueta_id):
            return True
        if nome_alvo and nome_alvo in _texto_normalizado(e.get('nome')):
            return True
    return False


def _consultar_etiquetas_reprocessamento(client: Any, id_processo: Any,
                                         numero: Any = '',
                                         *,
                                         tentativas: int = 2,
                                         etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> Optional[List[Dict[str, Any]]]:
    """GET /pje-etiquetas-api/api/reprocessamentoetiquetas/{id} com retry curto e checagem rápida."""
    alvo_log = numero or id_processo
    path = URL_REPROCESSAMENTO_ETIQUETAS_API.format(id=id_processo)
    res_get: Dict[str, Any] = {}
    for tentativa in range(1, max(1, tentativas) + 1):
        res_get = client.gateway_get(path, timeout=30)
        _checar_401(res_get, f'GET reprocessamentoetiquetas/{id_processo}')
        if res_get.get('ok'):
            break
        if _eh_erro_transitorio_gateway(res_get):
            # Antes de insistir no GET pesado, checa em 0.3s se o chip já sumiu.
            if _processo_tem_chip(client, id_processo, etiqueta_id) is False:
                logger.info(
                    '[CHIPADV][CHIPS] Chip %s já ausente em %s (confirmado após timeout/5xx no GET)',
                    etiqueta_id, alvo_log,
                )
                return []
            if tentativa < tentativas:
                logger.warning(
                    '[CHIPADV][CHIPS] GET reprocessamento %s falhou (tentativa %d/%d, retry): %s',
                    alvo_log, tentativa, tentativas, res_get.get('error'),
                )
                _esperar_retry_api(1.5)
                continue
        break
    if not res_get.get('ok'):
        logger.warning('[CHIPADV][CHIPS] GET reprocessamento %s falhou: %s',
                       alvo_log, res_get.get('error'))
        return None
    etiquetas = res_get.get('data')
    if not isinstance(etiquetas, list):
        logger.warning('[CHIPADV][CHIPS] Resposta inesperada no GET de %s: %r',
                       alvo_log, etiquetas)
        return None
    return etiquetas


def _chip_alvo_para_excluir(etiquetas: Optional[List[Dict[str, Any]]],
                            etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> List[Dict[str, Any]]:
    """Extrai o item do chip alvo marcado com `excluir=True`."""
    if not etiquetas:
        return []
    nome_alvo = _texto_normalizado(CHIP_TEXTO_IMPEDIDO)
    return [
        e for e in etiquetas
        if isinstance(e, dict) and e.get('excluir') is True and (
            _inteiro(e.get('idEtiqueta'), -1) == int(etiqueta_id)
            or nome_alvo in _texto_normalizado(e.get('nome'))
        )
    ]


def _processo_tem_chip(client: Any, id_processo: Any,
                       etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> Optional[bool]:
    """Confirma via GET /pje-etiquetas-api/api/processos/{id}/etiquetas se o
    chip `etiqueta_id` ainda existe no processo. Devolve True/False ou None em erro.
    """
    path = URL_ETIQUETAS_PROCESSO_API.format(id=id_processo)
    res = client.gateway_get(path, timeout=20)
    _checar_401(res, f'GET processos/{id_processo}/etiquetas')
    if not res.get('ok'):
        return None
    dados = res.get('data')
    if not isinstance(dados, list):
        return None
    nome_alvo = _texto_normalizado(CHIP_TEXTO_IMPEDIDO)
    for item in dados:
        if not isinstance(item, dict):
            continue
        etq = (item.get('etiquetaInstancia') or {}).get('etiqueta') or {}
        if _inteiro(etq.get('id'), -1) == int(etiqueta_id):
            return True
        if nome_alvo and nome_alvo in _texto_normalizado(etq.get('nome')):
            return True
    return False


def _reprocessar_chips_do_processo(client: Any, id_processo: Any,
                                   etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                   numero: Any = '',
                                   *,
                                   etiquetas_precarregadas: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Reprocessa o chip alvo diretamente pela API de etiquetas (sem abrir /detalhe).

    1. Confere se o chip ainda existe (`_processo_tem_chip` quando não está em
       `excluir=True`) — ex.: após inativar o advogado via PUT, o próprio PJe
       pode já ter removido o chip automaticamente.
    2. Se veio com `excluir=True`, envia no POST apenas o chip alvo (`918`),
       preservando todos os demais chips do processo.
    """
    alvo_log = numero or id_processo
    etiquetas = (etiquetas_precarregadas if etiquetas_precarregadas is not None
                 else _consultar_etiquetas_reprocessamento(client, id_processo, numero, etiqueta_id=etiqueta_id))
    if etiquetas is None:
        # Fallback quando o GET pesado de reprocessamento dá ReadTimeout:
        # se não há nenhum advogado ativo impedido no processo, remove via POST direto (~0.07s).
        advs_check = ler_advogados_do_processo(client, id_processo, com_inativas=False)
        ativos_impedidos = [
            a for a in advs_check
            if a.get('ativo') and a.get('parte_ativa', True) and _eh_advogado_com_pendencia_pje(a)
        ]
        if not ativos_impedidos:
            return _remover_chip_direto_api(client, id_processo, etiqueta_id, numero)
        return False

    a_excluir = _chip_alvo_para_excluir(etiquetas, etiqueta_id)
    if not a_excluir:
        tem_chip = _processo_tem_chip(client, id_processo, etiqueta_id)
        if tem_chip is False:
            logger.info('[CHIPADV][CHIPS] Chip %s já ausente em %s (removido automaticamente)',
                        etiqueta_id, alvo_log)
            return True
        logger.info('[CHIPADV][CHIPS] Chip %s ainda ativo (manter=True) em %s — nada salvo',
                    etiqueta_id, alvo_log)
        return False

    path = URL_REPROCESSAMENTO_ETIQUETAS_API.format(id=id_processo)
    tentativas_post = 3
    res_post: Dict[str, Any] = {}
    for tentativa in range(1, tentativas_post + 1):
        res_post = client.gateway_post(path, json_data={'etiquetas': a_excluir}, timeout=45)
        _checar_401(res_post, f'POST reprocessamentoetiquetas/{id_processo}')
        if res_post.get('ok'):
            break
        if _eh_erro_transitorio_gateway(res_post):
            # O proxy (502/504/ReadTimeout) pode ter expirado mesmo após o backend concluir.
            if _processo_tem_chip(client, id_processo, etiqueta_id) is False:
                logger.info(
                    '[CHIPADV][CHIPS] Chip %s removido via API em %s (confirmado após erro transitório no POST)',
                    etiqueta_id, alvo_log,
                )
                return True
            if tentativa < tentativas_post:
                logger.warning(
                    '[CHIPADV][CHIPS] POST reprocessamento %s falhou (tentativa %d/%d, retry): %s',
                    alvo_log, tentativa, tentativas_post, res_post.get('error'),
                )
                _esperar_retry_api(2.0 * tentativa)
                continue
        break

    if not res_post.get('ok'):
        logger.warning('[CHIPADV][CHIPS] POST reprocessamento %s falhou: %s',
                       alvo_log, res_post.get('error'))
        return False

    logger.info('[CHIPADV][CHIPS] Chip %s removido via API em %s',
                etiqueta_id, alvo_log)
    return True


def _consultar_tarefa_atual(client: Any, id_processo: Any) -> str:
    """Nome da tarefa mais recente do processo via API (mesmo endpoint do P2B)."""
    path = URL_TAREFAS_PROCESSO_API.format(id=id_processo)
    res = client.gateway_get(path, params={'maisRecente': 'true'}, timeout=15)
    _checar_401(res, f'GET processos/{id_processo}/tarefas')
    if not res.get('ok'):
        return ''
    dados = res.get('data')
    if isinstance(dados, list) and dados and isinstance(dados[0], dict):
        return str(dados[0].get('nomeTarefa') or '').strip()
    if isinstance(dados, dict):
        return str(dados.get('nomeTarefa') or '').strip()
    return ''


def _processo_arquivado(client: Any, id_processo: Any,
                        etiquetas: Optional[List[Dict[str, Any]]] = None) -> bool:
    """True se a tarefa atual for Arquivo/Arquivados/Arquivo definitivo OU
    se o processo possuir etiqueta/chip com 'Arquivado' (inclui 'Desarquivado Sem Reativação').

    Processos arquivados recebem apenas limpeza do chip (sem certidão/GIGS/ato).
    """
    if etiquetas:
        for e in etiquetas:
            if not isinstance(e, dict):
                continue
            if e.get('manter') or e.get('excluir'):
                nome = _texto_normalizado(e.get('nome'))
                if 'arquivado' in nome:
                    return True
    tarefa = _texto_normalizado(_consultar_tarefa_atual(client, id_processo))
    if 'desarquivar' in tarefa or 'desarquivado' in tarefa:
        return False
    return any(re.search(rf'\b{re.escape(t)}\b', tarefa) for t in TAREFAS_ARQUIVO)


def _alterar_situacao_representante_api(client: Any, id_processo: Any,
                                        id_parte_rep: Any,
                                        id_parte_representada: Any,
                                        situacao: str,
                                        numero: Any = '') -> bool:
    """PUT /pje-comum-api/api/processos/id/{id}/partes/situacao ('A' | 'I' | 'S')."""
    if not id_parte_rep:
        return False
    payload: Dict[str, Any] = {
        'idProcesso': _inteiro(id_processo, id_processo),
        'idParte': _inteiro(id_parte_rep, id_parte_rep),
        'situacao': situacao,
    }
    if id_parte_representada:
        payload['idParteRepresentada'] = _inteiro(id_parte_representada, id_parte_representada)
    path = URL_PARTES_SITUACAO_API.format(id=id_processo)
    res = client.request_gateway('PUT', path, json_data=payload, timeout=20)
    _checar_401(res, f'PUT partes/situacao/{id_processo}')
    if not res.get('ok'):
        logger.warning(
            '[CHIPADV][PARTE] PUT situacao=%s falhou em %s (rep=%s parte=%s): %s',
            situacao, numero or id_processo, id_parte_rep, id_parte_representada,
            res.get('error'),
        )
        return False
    return True


def _inativar_advogado_no_processo(client: Any, id_processo: Any,
                                   vinculos_cpf: List[Dict[str, Any]],
                                   numero: Any = '') -> bool:
    """Inativa os vínculos do advogado na autuação via API.

    - Parte inativa (`parte_ativa=False`): o PJe rejeita alteração do representante
      com `PJE-193`; pula o PUT e deixa apenas o reprocessamento do chip limpar.
    - Vínculo ativo em parte ativa: PUT situacao='I'.
    - Vínculo já inativo em parte ativa: cicla A → I para forçar atualização.
    """
    ok_algum = False
    for v in vinculos_cpf:
        if not v.get('parte_ativa', True):
            logger.info(
                '[CHIPADV][PARTE] Parte %s inativa em %s — pulando PUT situacao (apenas reprocessar chip)',
                v.get('parte') or v.get('parte_id'), numero or id_processo,
            )
            continue
        rep_id = v.get('id_parte_rep')
        parte_id = v.get('parte_id')
        if v.get('ativo'):
            if _alterar_situacao_representante_api(client, id_processo, rep_id, parte_id, 'I', numero):
                ok_algum = True
        else:
            # Advogado já inativo em parte ativa: cicla A → I apenas nele para forçar atualização
            _alterar_situacao_representante_api(client, id_processo, rep_id, parte_id, 'A', numero)
            if _alterar_situacao_representante_api(client, id_processo, rep_id, parte_id, 'I', numero):
                ok_algum = True
    return ok_algum


def _parte_tem_domicilio_eletronico(client: Any, vinculo: Dict[str, Any]) -> bool:
    """Verifica domicílio eletrônico da parte alvo (mesma lógica de bianca/triagem/citacao.py)."""
    if vinculo.get('parte_domicilio_inline') is True:
        return True
    id_parte = str(vinculo.get('parte_id') or '')
    id_pessoa = str(vinculo.get('parte_id_pessoa') or '')

    dom_flag = None
    if id_parte:
        try:
            dom_flag = client.domicilio_eletronico(id_parte)
        except Exception as e:
            logger.debug('[CHIPADV][DOM] Erro domicilio_eletronico(parte=%s): %s', id_parte, e)
    if dom_flag is not True and id_pessoa and id_pessoa != id_parte:
        try:
            dom_flag_pessoa = client.domicilio_eletronico(id_pessoa)
            if dom_flag_pessoa is not None:
                dom_flag = dom_flag_pessoa
        except Exception as e:
            logger.debug('[CHIPADV][DOM] Erro domicilio_eletronico(pessoa=%s): %s', id_pessoa, e)
    return dom_flag is True


def _eh_tarefa_instancia_superior(tarefa_nome: Any) -> bool:
    """True para tarefa 197 ('Aguardando apreciação pela instância superior')."""
    t = _texto_normalizado(tarefa_nome)
    return 'instancia superior' in t


def _formatar_obs_gigs_197(vinculos: Optional[List[Dict[str, Any]]],
                           advogado_alvo: Optional[Dict[str, Any]] = None) -> str:
    """Formata a observação do GIGS sem prazo para processos na tarefa 197."""
    itens = list(vinculos or [])
    if not itens and advogado_alvo:
        itens = [advogado_alvo]
    linhas = ['Advogado impedido de atuar excluído:']
    vistos = set()
    for v in itens:
        if not isinstance(v, dict):
            continue
        empresa = (v.get('parte') or '').strip()
        nome = (v.get('nome') or (advogado_alvo or {}).get('nome') or '').strip()
        cpf_dig = _somente_digitos(v.get('cpf') or (advogado_alvo or {}).get('cpf') or '')
        if len(cpf_dig) == 11:
            cpf_fmt = f'{cpf_dig[:3]}.{cpf_dig[3:6]}.{cpf_dig[6:9]}-{cpf_dig[9:]}'
        else:
            cpf_fmt = cpf_dig or str(v.get('cpf') or '').strip()
        linha = f'{empresa} : {nome} - {cpf_fmt}' if empresa else f'{nome} - {cpf_fmt}'
        if linha not in vistos:
            vistos.add(linha)
            linhas.append(linha)
    linhas.append('Intimar para regularizar no retorno, se não houver outro habilitado.')
    return '\n'.join(linhas)


def _executar_acao_pos_exclusao_detalhe(driver: Any, processo_info: Dict[str, Any],
                                        advogado_alvo: Dict[str, Any],
                                        tem_outro_regular: bool,
                                        tem_domicilio: bool = False) -> bool:
    """Ramo 3 (advogado ativo em parte ativa, processo não arquivado):
      - tarefa 197 (Aguardando apreciação pela instância superior) → apenas GIGS sem prazo
      - tem outro advogado regular/ausente → anex_advdelete (assinar='sim')
      - ficou sem advogado:
          * empresa com domicílio eletrônico → ato_regadv (destinatario='alvo', Assinar=True)
          * empresa sem domicílio eletrônico → criar_gigs('1', '', 'xs dec adv') + ato_regadv2 (intimar=False, Assinar=True)
    """
    from Fix.extracao import criar_gigs
    alvo_log = processo_info.get('numero') or processo_info.get('id')

    if processo_info.get('instancia_superior'):
        obs_197 = _formatar_obs_gigs_197(processo_info.get('vinculos_removidos'), advogado_alvo)
        ok_gigs = bool(criar_gigs(driver, '', '', obs_197))
        if ok_gigs:
            logger.info('[CHIPADV][GIGS][197] Observação criada em %s', alvo_log)
        else:
            logger.warning('[CHIPADV][GIGS][197] Falha ao criar GIGS em %s', alvo_log)
        return ok_gigs

    if tem_outro_regular:
        return bool(anex_advdelete(driver, processo_info, advogado_alvo))

    if tem_domicilio:
        return bool(ato_regadv(driver, processo_info, advogado_alvo))

    ok_gigs = bool(criar_gigs(driver, PRAZO_GIGS_DEC_ADV, '', OBS_GIGS_DEC_ADV))
    if ok_gigs:
        logger.info('[CHIPADV][GIGS] Atividade "%s" (prazo=%r, domicilio=%s) criada em %s',
                    OBS_GIGS_DEC_ADV, PRAZO_GIGS_DEC_ADV, tem_domicilio, alvo_log)
    else:
        logger.warning('[CHIPADV][GIGS] Falha ao criar GIGS "%s" em %s',
                       OBS_GIGS_DEC_ADV, alvo_log)
    ok_ato = bool(ato_regadv2(driver, processo_info, advogado_alvo))
    return ok_gigs and ok_ato


def _reprocessar_lote_cpf_paralelo(client: Any, cpf: str,
                                   etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                   max_workers: int = MAX_WORKERS_REPROC) -> Tuple[int, List[Any], bool]:
    """Ramo 1 — reprocessa via API (em paralelo) todos os processos do CPF + chip + OJ 187.

    Devolve `(qtd_removidos, ids_removidos, consulta_ok)`. Apenas os processos
    cujo chip `918` foi de fato removido entram em `ids_removidos` — se algum
    ficar preso por outro advogado impedido no mesmo processo, permanece livre
    para ser tratado na vez do outro advogado.
    """
    cpf = _somente_digitos(cpf)
    total, itens, consulta_ok = _processos_do_cpf(client, cpf, etiqueta_id)
    if not consulta_ok:
        logger.error('[CHIPADV][CHIPS] Falha na consulta do CPF %s', cpf)
        return 0, [], False
    if not itens:
        logger.info('[CHIPADV][CHIPS] Nenhum processo restante com o chip para o CPF %s', cpf)
        return 0, [], True

    logger.info('[CHIPADV][CHIPS] Reprocessando em paralelo %d processo(s) do CPF %s',
                total, cpf)

    def _rodar(item: Dict[str, Any]):
        pid = item.get('id')
        num = item.get('numero') or item.get('numeroProcesso') or pid
        if not pid:
            return pid, False
        return pid, _reprocessar_chips_do_processo(client, pid, etiqueta_id, num)

    ids_removidos: List[Any] = []
    workers = max(1, min(max_workers, len(itens)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for pid, ok in ex.map(_rodar, itens):
            if ok and pid is not None:
                ids_removidos.append(pid)

    logger.info('[CHIPADV][CHIPS] %d/%d processo(s) limpo(s) para o CPF %s',
                len(ids_removidos), total, cpf)
    return len(ids_removidos), ids_removidos, True


def _tratar_advogado_suspenso_no_processo(driver: Any, client: Any,
                                          id_processo: Any, numero: Any,
                                          advogado_alvo: Dict[str, Any],
                                          etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                          *,
                                          estado_sessao: Optional[Dict[str, Any]] = None) -> bool:
    """Ramo 3 em um único processo:
      1. Inativa o advogado na autuação via API (`PUT /partes/situacao`)
      2. Passo 0: reprocessar chip via API
      3. Se processo arquivado (tarefa Arquivo* ou chip Arquivado*) → encerra
      4. Se advogado inativo ou de parte inativa → encerra (só reprocessar chip)
      5. Se advogado ativo em parte ativa:
           - tem outro advogado regular/ausente na mesma parte → anex_advdelete
           - ficou sem advogado → criar_gigs('1', '', 'xs dec adv') + ato_regadv
    Retorna True se o chip `etiqueta_id` foi removido do processo.
    """
    cpf = _somente_digitos(advogado_alvo.get('cpf'))
    vinculos = ler_vinculos_advogados(client, id_processo, com_inativas=True)
    vinculos_cpf = [v for v in vinculos if v['cpf'] == cpf]

    if vinculos_cpf:
        inativou = _inativar_advogado_no_processo(client, id_processo, vinculos_cpf, numero)
        if inativou:
            # Pequeno intervalo para o PJe concluir a remoção assíncrona do chip 918
            _esperar_retry_api(0.8)

    # Passo 0: confere primeiro pelo GET rápido de etiquetas (o PUT de inativação
    # costuma remover o chip 918 automaticamente, evitando o GET pesado de reprocessamento).
    etiquetas_atuais = _listar_etiquetas_processo_api(client, id_processo)
    if etiquetas_atuais is not None and not _etiquetas_contem_chip(etiquetas_atuais, etiqueta_id):
        logger.info('[CHIPADV][CHIPS] Chip %s já ausente em %s (removido automaticamente)',
                    etiqueta_id, numero)
        etiquetas = etiquetas_atuais
        chip_limpo = True
    else:
        etiquetas = _consultar_etiquetas_reprocessamento(client, id_processo, numero, etiqueta_id=etiqueta_id)
        chip_limpo = _reprocessar_chips_do_processo(
            client, id_processo, etiqueta_id, numero, etiquetas_precarregadas=etiquetas
        )
        if etiquetas is None or not etiquetas:
            etiquetas = etiquetas_atuais

    # Processo arquivado → só limpeza do chip, sem certidão/GIGS/ato
    if _processo_arquivado(client, id_processo, etiquetas=etiquetas):
        logger.info('[CHIPADV][SUSP] Processo %s arquivado — sem ação posterior', numero)
        return chip_limpo

    # Vínculos onde o advogado era ATIVO em parte ATIVA
    ativos_em_parte_ativa = [
        v for v in vinculos_cpf if v.get('ativo') and v.get('parte_ativa')
    ]
    if not ativos_em_parte_ativa:
        logger.info('[CHIPADV][SUSP] Advogado %s inativo/parte inativa em %s — '
                    'sem ação posterior', advogado_alvo.get('nome'), numero)
        return chip_limpo

    # Tarefa 197 (Aguardando apreciação pela instância superior): apenas GIGS sem prazo
    tarefa_atual = _consultar_tarefa_atual(client, id_processo)
    em_instancia_superior = _eh_tarefa_instancia_superior(tarefa_atual)
    if em_instancia_superior:
        logger.info('[CHIPADV][SUSP] Processo %s na tarefa "%s" — criando apenas GIGS sem prazo',
                    numero, tarefa_atual)

    # Se alguma parte ativa ficou sem advogado regular, prioriza a regra mais
    # gravosa (GIGS + ato_regadv); se todas têm colega regular/ausente, certidão.
    sem_outro_adv = [v for v in ativos_em_parte_ativa if not v.get('tem_outro_regular')]
    todas_tem_outro = not sem_outro_adv
    tem_domicilio = False
    if not em_instancia_superior and not todas_tem_outro:
        tem_domicilio = all(_parte_tem_domicilio_eletronico(client, v) for v in sem_outro_adv)
        logger.info('[CHIPADV][SUSP] Processo %s sem outro advogado — domicilio_eletronico=%s',
                    numero, tem_domicilio)

    processo_info = {
        'id': id_processo,
        'numero': numero,
        'vinculos_removidos': ativos_em_parte_ativa,
        'vinculos_sem_outro': sem_outro_adv,
        'instancia_superior': em_instancia_superior,
    }
    ok_acao = False
    for tent_det in range(2):
        drv_atual = estado_sessao['driver'] if estado_sessao else driver
        try:
            ok_acao = _executar_no_detalhe(
                drv_atual,
                id_processo,
                lambda drv: _executar_acao_pos_exclusao_detalhe(
                    drv, processo_info, advogado_alvo, todas_tem_outro, tem_domicilio=tem_domicilio
                ),
                'SUSP',
                numero,
            )
            break
        except SessaoExpiradaError as e:
            if tent_det == 0 and _recuperar_sessao_401(
                estado_sessao, f'sessão/driver inválido no /detalhe de {numero}: {e}'
            ):
                logger.info('[CHIPADV][SUSP] Retentando ação pós-exclusão em %s com novo driver...', numero)
                continue
            logger.error('[CHIPADV][SUSP][ACAO_FALHOU] Sessão/driver falhou em %s após recuperação: %s', numero, e)
            return False

    if not ok_acao:
        logger.error(
            '[CHIPADV][SUSP][ACAO_FALHOU] Ação pós-exclusão (despacho/juntada) NÃO concluída em %s '
            '(tem_outro=%s, domicilio=%s) — requer conferência!',
            numero, todas_tem_outro, tem_domicilio,
        )
        return False
    return chip_limpo


def _recuperar_sessao_401(estado: Optional[Dict[str, Any]], motivo: str) -> bool:
    """Recria o driver + PjeApiClient após HTTP 401 para não perder nenhum processo."""
    if not estado or not callable(estado.get('recriar_driver')):
        return False
    logger.warning('[CHIPADV][401] %s — recriando driver para renovar token...', motivo)
    novo_driver = estado['recriar_driver'](estado.get('driver'), motivo)
    if not novo_driver:
        logger.error('[CHIPADV][401] Falha ao recriar driver (%s)', motivo)
        return False
    try:
        novo_driver.get(URL_PAINEL)
        espera.ate_url(novo_driver, 'meu-painel', teto=30)
        estado['driver'] = novo_driver
        estado['client'] = _criar_client(novo_driver)
        estado['recriacoes'] = estado.get('recriacoes', 0) + 1
        logger.info('[CHIPADV][401] Driver e cliente API renovados com sucesso (#%d)',
                    estado['recriacoes'])
        return True
    except Exception as e:
        logger.error('[CHIPADV][401] Falha ao inicializar novo driver/API: %s: %s',
                     type(e).__name__, e)
        return False


def _tratar_lote_advogado_suspenso(driver: Any, client: Any,
                                   advogado_alvo: Dict[str, Any],
                                   etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                   *,
                                   estado_sessao: Optional[Dict[str, Any]] = None) -> Tuple[int, List[Any], bool]:
    """Ramo 3 — trata todos os processos do CPF suspenso/cancelado/impedido (chip + CPF + OJ 187)."""
    cpf = _somente_digitos(advogado_alvo.get('cpf'))
    total, itens, consulta_ok = _processos_do_cpf(client, cpf, etiqueta_id)
    if not consulta_ok:
        logger.error('[CHIPADV][SUSP] Falha na consulta do CPF %s', cpf)
        return 0, [], False
    if not itens:
        logger.info('[CHIPADV][SUSP] Nenhum processo com o chip para o CPF %s', cpf)
        return 0, [], True

    logger.info('[CHIPADV][SUSP] %d processo(s) para o advogado %s (CPF %s)',
                total, advogado_alvo.get('nome'), cpf)

    ids_limpos: List[Any] = []
    for idx, item in enumerate(itens, 1):
        pid = item.get('id')
        num = item.get('numero') or item.get('numeroProcesso') or pid
        logger.info('[CHIPADV][SUSP] [%d/%d] %s (id=%s)', idx, total, num, pid)
        if not pid:
            continue
        for tentativa in range(3):
            drv_cur = estado_sessao['driver'] if estado_sessao else driver
            cli_cur = estado_sessao['client'] if estado_sessao else client
            try:
                if _tratar_advogado_suspenso_no_processo(
                    drv_cur, cli_cur, pid, num, advogado_alvo, etiqueta_id,
                    estado_sessao=estado_sessao,
                ):
                    ids_limpos.append(pid)
                break
            except SessaoExpiradaError as e:
                if tentativa < 2 and _recuperar_sessao_401(
                    estado_sessao, f'401 no lote do CPF {cpf} ({num}): {e}'
                ):
                    continue
                raise

    logger.info('[CHIPADV][SUSP] %d/%d processo(s) limpo(s) para o CPF %s',
                len(ids_limpos), total, cpf)
    return len(ids_limpos), ids_limpos, True


def _driver_em_sessao_invalida(driver: Any) -> Optional[str]:
    """Detecta acesso-negado, tela de login ou sessão/página quebrada no driver."""
    try:
        url = str(getattr(driver, 'current_url', '') or '')
    except Exception as e:
        return f'driver inacessível ({type(e).__name__}: {e})'
    url_low = url.lower()
    if any(k in url_low for k in ('acesso-negado', '/login', 'erro-acesso', 'sso.cloud.pje')):
        return f'url={url}'
    if not ('pje' in url_low and 'jus.br' in url_low):
        return f'url_fora_pje={url!r}'
    try:
        txt = _executar_js(
            driver,
            "return (document.body && document.body.innerText ? document.body.innerText.slice(0, 600) : '').toLowerCase();",
        ) or ''
        if any(k in txt for k in ('acesso negado', 'sessão expirada', 'sessao expirada', 'não autorizado')):
            return f'texto_pagina={txt[:120]!r}'
    except Exception:
        pass
    return None


def _executar_no_detalhe(driver: Any, id_processo: Any, acao, rotulo: str,
                         numero: Any = '') -> bool:
    """Abre /pjekz/processo/{id}/detalhe em aba nova, roda `acao` e fecha.

    Se detectar acesso-negado, sessão expirada, página sem elementos ou driver
    quebrado, levanta `SessaoExpiradaError` para o orquestrador recriar o driver
    e retentar a ação (nunca engole silenciosamente).
    """
    alvo = numero or id_processo
    try:
        principal = driver.current_window_handle
        aba = abrir_url_nova_aba(driver, URL_PROCESSO_DETALHE.format(id=id_processo))
    except Exception as e:
        raise SessaoExpiradaError(f'driver quebrado ao abrir /detalhe de {alvo}: {type(e).__name__}: {e}') from e

    if not aba:
        logger.error('[CHIPADV][%s] Não foi possível abrir /detalhe de %s — disparando recuperação',
                     rotulo, alvo)
        raise SessaoExpiradaError(f'falha ao abrir nova aba /detalhe de {alvo}')

    try:
        if not espera.ate_url(driver, '/detalhe', teto=30):
            motivo = _driver_em_sessao_invalida(driver) or f"url={getattr(driver, 'current_url', '')!r}"
            logger.error('[CHIPADV][%s] /detalhe não carregou para %s (%s)', rotulo, alvo, motivo)
            raise SessaoExpiradaError(f'/detalhe não carregou em {alvo}: {motivo}')

        motivo_sessao = _driver_em_sessao_invalida(driver)
        if motivo_sessao:
            logger.error('[CHIPADV][%s] Acesso negado/sessão inválida em %s (%s)', rotulo, alvo, motivo_sessao)
            raise SessaoExpiradaError(f'sessão inválida em {alvo}: {motivo_sessao}')

        # Qualquer um destes confirma que o /detalhe renderizou; as ações
        # usam o menu do processo (chips) ou o botão "Nova Atividade" (GIGS).
        if not espera.ate_aparecer(
                driver,
                'pje-cabecalho-processo, pje-timeline, '
                'button[aria-label="Menu do processo"]',
                teto=30):
            motivo = _driver_em_sessao_invalida(driver) or f"url={getattr(driver, 'current_url', '')!r}"
            logger.error('[CHIPADV][%s] /detalhe sem os elementos esperados em %s (%s) — disparando recuperação',
                         rotulo, alvo, motivo)
            raise SessaoExpiradaError(f'/detalhe sem elementos em {alvo}: {motivo}')

        return bool(acao(driver))
    except SessaoExpiradaError:
        raise
    except Exception as e:
        msg_low = f'{type(e).__name__}: {e}'.lower()
        if any(k in msg_low for k in ('target closed', 'browser has been closed', 'connection refused', 'disconnected', 'page closed')):
            raise SessaoExpiradaError(f'driver encerrado em {alvo}: {type(e).__name__}: {e}') from e
        logger.error('[CHIPADV][%s] Erro na ação em %s: %s: %s', rotulo, alvo,
                     type(e).__name__, e)
        return False
    finally:
        _fechar_aba(driver, aba, principal)


def _processos_do_cpf(client: Any, cpf: str, etiqueta_id: int,
                      tamanho_pagina: int = TAMANHO_PAGINA_API):
    """Consulta (API) todos os processos do CPF marcados com o chip.

    Usa a mesma chamada do passo 1, agora com `cpf`: `idEtiqueta` +
    `idsOrgaosJulgadores` + `cpf`. Pagina até esgotar `qtdPaginas` (na
    prática o advogado tem poucos processos com o chip).

    Devolve `(total, itens, consulta_ok)` — `consulta_ok=False` quando a
    primeira página falhou (para o chamador não registrar o CPF como tratado
    sem ter consultado nada).
    """
    cpf = _somente_digitos(cpf)
    itens: List[Dict[str, Any]] = []
    total = 0
    pagina = 1
    consulta_ok = False
    while True:
        dados = _consultar_processos(client, etiqueta_id, cpf=cpf,
                                     pagina=pagina,
                                     tamanho_pagina=tamanho_pagina)
        if dados is None:
            break
        consulta_ok = True
        total = _inteiro(dados.get('totalRegistros'), total)
        lista = dados.get('resultado') or []
        itens.extend(lista)
        qtd_paginas = _inteiro(dados.get('qtdPaginas'), 1)
        if pagina >= qtd_paginas or len(lista) < tamanho_pagina:
            break
        pagina += 1
    return total or len(itens), itens, consulta_ok


def _percorrer_processos_do_cpf(driver: Any, client: Any, cpf: str,
                                etiqueta_id: int, acao, rotulo: str,
                                *, via_api: bool = False):
    """Roda `acao` em cada processo do CPF que tem o chip.

    Quando `via_api=True`, executa `acao(client, id_processo, etiqueta_id, numero)`
    diretamente sem abrir aba `/detalhe`. Quando `via_api=False` (ex.: GIGS),
    abre `/pjekz/processo/{id}/detalhe` em aba nova e chama `acao(driver)`.

    Devolve `(processados, ids_processados, consulta_ok)`. Os ids são os
    processos que o lote cobriu — o orquestrador usa essa lista para não
    reabrir, no laço externo, um processo que já foi visto aqui.
    """
    cpf = _somente_digitos(cpf)
    total, itens, consulta_ok = _processos_do_cpf(client, cpf, etiqueta_id)
    ids = [item.get('id') for item in itens if item.get('id')]

    if not consulta_ok:
        logger.error('[CHIPADV][%s] Falha na consulta do CPF %s', rotulo, cpf)
        return 0, ids, False

    logger.info('[CHIPADV][%s] %d processo(s) na consulta do CPF %s',
                rotulo, total, cpf)
    if not itens:
        logger.info('[CHIPADV][%s] Nenhum processo com o chip para o CPF %s',
                    rotulo, cpf)
        return 0, ids, True

    processados = 0
    for indice, item in enumerate(itens, 1):
        id_processo = item.get('id')
        numero = item.get('numero') or item.get('numeroProcesso') or id_processo
        logger.info('[CHIPADV][%s] [%d/%d] %s (id=%s)',
                    rotulo, indice, total, numero, id_processo)
        if not id_processo:
            logger.warning('[CHIPADV][%s] Processo sem id na consulta — pulando',
                           rotulo)
            continue
        if via_api:
            ok = bool(acao(client, id_processo, etiqueta_id, numero))
        else:
            ok = _executar_no_detalhe(driver, id_processo, acao, rotulo, numero)
        if ok:
            processados += 1

    logger.info('[CHIPADV][%s] %d/%d processo(s) processado(s) para o CPF %s',
                rotulo, processados, total, cpf)
    return processados, ids, True


def reprocessar_chips_do_advogado(driver: Any, cpf: str,
                                  etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                  client: Any = None) -> int:
    """Reprocessa o chip alvo em todos os processos do advogado (via API em paralelo)."""
    client = client or _criar_client(driver)
    qtd, _, _ = _reprocessar_lote_cpf_paralelo(client, cpf, etiqueta_id)
    return qtd


# =============================================================================
# Orquestrador
# =============================================================================

def run_chipadv(driver: Any, limite: Optional[int] = None,
                chip_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                *,
                recriar_driver: Optional[Any] = None) -> Dict[str, Any]:
    """Fluxo CHIPADV completo. Recebe o driver já logado (pw.py/x.py).

    `limite`: teto opcional de processos EXAMINADOS no laço externo (só para
    testes). `None` percorre todos os processos do chip.
    `recriar_driver`: callback `(driver_atual, motivo) -> novo_driver` usada
    para recriar o driver e renovar o token em caso de HTTP 401 sem perder
    nenhum processo.
    """
    logger.info('[CHIPADV] === INICIANDO FLUXO CHIP ADVOGADO IMPEDIDO ===')
    resultado: Dict[str, Any] = {
        'sucesso': False,
        'total': 0,
        'processados': 0,
        'ignorados': 0,
        'cpfs': {},
        'erros': [],
    }

    # 0. driver normal até meu-painel
    try:
        driver.get(URL_PAINEL)
        espera.ate_url(driver, 'meu-painel', teto=30)
    except Exception as e:
        logger.error('[CHIPADV] Falha ao navegar para meu-painel: %s: %s',
                     type(e).__name__, e)
        resultado['erros'].append(f'meu-painel: {e}')
        return resultado

    try:
        client = _criar_client(driver)
    except Exception as e:
        logger.error('[CHIPADV] Falha ao criar o cliente de API: %s: %s',
                     type(e).__name__, e)
        resultado['erros'].append(f'api: {e}')
        return resultado

    estado: Dict[str, Any] = {
        'driver': driver,
        'client': client,
        'recriar_driver': recriar_driver,
        'recriacoes': 0,
    }

    try:
        total_chip, processos = iniciar_busca_processos_por_chip(estado['client'], chip_id)
    except SessaoExpiradaError as e:
        if _recuperar_sessao_401(estado, f'401 na consulta inicial: {e}'):
            total_chip, processos = iniciar_busca_processos_por_chip(estado['client'], chip_id)
        else:
            resultado['critical_stop'] = True
            resultado['critical_reason'] = 'sessao_expirada_401'
            resultado['erros'].append(str(e))
            return resultado

    resultado['total'] = total_chip
    if not total_chip:
        logger.warning('[CHIPADV] Nenhum processo com o chip %s — nada a fazer', chip_id)
        resultado['sucesso'] = True
        return resultado

    logger.info('[CHIPADV] Total com o chip %s: %d processo(s) — um por vez',
                chip_id, total_chip)

    # Memória da execução:
    # - cpfs_tratados: CPF → {"acao", "nome", "cpf", "ok"}
    # - ids_limpos: apenas processos cujo chip 918 foi efetivamente removido
    #   (processos com 2+ advogados impedidos permanecem elegíveis até limpar)
    cpfs_tratados: Dict[str, Dict[str, Any]] = {}
    ids_limpos: set = set()
    examinados = 0

    def _tratar_um_processo(id_proc: Any, numero: Any) -> None:
        drv = estado['driver']
        cli = estado['client']

        # Leitura rápida das etiquetas atuais (~0.2s) e de todos os advogados (~0.2s),
        # sem acionar o GET pesado /reprocessamentoetiquetas antes de saber se há pendência.
        etiquetas = _listar_etiquetas_processo_api(cli, id_proc)
        if etiquetas is not None and not _etiquetas_contem_chip(etiquetas, chip_id):
            logger.info('[CHIPADV][CHIPS] Chip %s já ausente em %s', chip_id, numero)
            ids_limpos.add(id_proc)
            resultado['processados'] += 1
            return

        advogados = ler_advogados_do_processo(cli, id_proc, com_inativas=True)
        candidatos = [a for a in advogados if _eh_advogado_com_pendencia_pje(a)]

        # Ramo 2: nenhum advogado marcado fora de REGULAR (nem ativos nem inativos)
        # → remove chip 918 via POST direto (~0.07s), sem depender do GET pesado.
        if not candidatos:
            logger.info('[CHIPADV] Processo %s sem advogado marcado como impedido — '
                        'removendo chip via API (POST direto)', numero)
            if _remover_chip_direto_api(cli, id_proc, chip_id, numero, etiquetas_processo=etiquetas):
                ids_limpos.add(id_proc)
                resultado['processados'] += 1
            return

        # Trata sequencialmente os advogados suspeitos deste processo
        for advogado in candidatos:
            if id_proc in ids_limpos:
                break
            drv = estado['driver']
            cli = estado['client']
            cpf = advogado['cpf']
            nome_adv = advogado.get('nome') or ''
            logger.info('[CHIPADV] Advogado %s (CPF %s, OAB=%s, sitPJe=%s, ativo=%s)',
                        nome_adv, cpf, advogado.get('oab'),
                        advogado.get('situacao_oab') or 'ausente',
                        advogado.get('ativo'))

            if cpf in cpfs_tratados:
                logger.info('[CHIPADV] CPF %s já tratado (%s) — pulando repetição',
                            cpf, cpfs_tratados[cpf].get('acao'))
                continue

            eh_inativo = (not advogado.get('ativo')) or (not advogado.get('parte_ativa', True))
            eh_arq = _processo_arquivado(cli, id_proc, etiquetas=etiquetas)
            buscar_tl = (
                None
                if (eh_inativo or eh_arq)
                else (lambda adv=advogado, pid=id_proc: resolver_oab_alvo(estado['client'], adv, id_processo=pid))
            )
            status_oab = validar_cadastro_api(
                cli,
                advogado,
                buscar_oab_timeline=buscar_tl,
            )
            if status_oab == 'falha':
                logger.warning('[CHIPADV] API OAB falhou para CPF %s — tentando fallback UI', cpf)
                status_oab = validar_cadastro(
                    drv,
                    cpf,
                    oab_alvo=advogado.get('oab'),
                    buscar_oab_timeline=buscar_tl,
                )
            if status_oab == 'falha':
                resultado['erros'].append(f'{numero}: validar cadastro falhou ({cpf})')
                continue

            if status_oab == 'ok':
                acao = 'chips'
                qtd, limpos, consulta_ok = _reprocessar_lote_cpf_paralelo(
                    estado['client'], cpf, chip_id
                )
            else:
                acao = 'suspenso_excluir'
                advogado_alvo = {'nome': nome_adv, 'cpf': cpf, 'oab': advogado.get('oab') or ''}
                resultado.setdefault('suspensos', []).append(advogado_alvo)
                qtd, limpos, consulta_ok = _tratar_lote_advogado_suspenso(
                    estado['driver'], estado['client'], advogado_alvo, chip_id,
                    estado_sessao=estado,
                )

            if not consulta_ok:
                resultado['erros'].append(f'{numero}: consulta do CPF {cpf} falhou')
                continue

            cpfs_tratados[cpf] = {
                'acao': acao,
                'nome': nome_adv,
                'cpf': cpf,
                'ok': qtd,
            }
            ids_limpos.update(limpos)
            resultado['cpfs'][cpf] = cpfs_tratados[cpf]
            resultado['processados'] += 1

        if id_proc not in ids_limpos and len(candidatos) > 1:
            if _reprocessar_chips_do_processo(estado['client'], id_proc, chip_id, numero):
                ids_limpos.add(id_proc)

    abortado_401 = False
    for indice, proc in enumerate(processos, 1):
        if limite is not None and examinados >= limite:
            logger.info('[CHIPADV] Teto de %d processo(s) examinado(s) — parando',
                        limite)
            break
        examinados += 1

        id_proc = proc.get('id')
        numero = proc.get('numeroProcesso') or proc.get('numero') or str(id_proc)
        logger.info('[CHIPADV] [%d/%d] Processo %s (id=%s)',
                    indice, total_chip, numero, id_proc)

        if id_proc in ids_limpos:
            logger.info('[CHIPADV] Processo %s já teve o chip removido em lote anterior — pulando',
                        numero)
            resultado['ignorados'] += 1
            continue

        for tentativa_401 in range(3):
            try:
                _tratar_um_processo(id_proc, numero)
                break
            except SessaoExpiradaError as e:
                if tentativa_401 < 2 and _recuperar_sessao_401(
                    estado, f'401 no processo {numero}: {e}'
                ):
                    continue
                logger.error('[CHIPADV][401] Sessão expirada sem recuperação possível em %s: %s',
                             numero, e)
                resultado['critical_stop'] = True
                resultado['critical_reason'] = 'sessao_expirada_401'
                resultado['erros'].append(f'{numero}: sessao_expirada_401')
                abortado_401 = True
                break
        if abortado_401:
            break

    if estado.get('recriacoes', 0) > 0:
        resultado['_driver'] = estado['driver']
        resultado['recriacoes_driver'] = estado['recriacoes']

    resultado['sucesso'] = (not resultado['erros']) and (not abortado_401)
    logger.info('[CHIPADV] total=%d examinados=%d processados=%d ignorados=%d erros=%d recriacoes=%d',
                resultado['total'], examinados, resultado['processados'],
                resultado['ignorados'], len(resultado['erros']), estado.get('recriacoes', 0))
    return resultado
