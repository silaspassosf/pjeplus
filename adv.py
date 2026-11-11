# -*- coding: utf-8 -*-
"""
adv.py — Fluxo CHIPADV (chip "Advogado impedido de Atuar").

Sequência definida pelo Silas (11/11/2026):

  0. driver já criado/logado pelo pw.py → navega para meu-painel
  1. API: processos marcados com o chip "Advogado impedido de Atuar"
     (mesmo padrão do fluxo DOM em bianca/dom_engine.py:
      PATCH /agrupamentotarefas/processos/todos
      POST  /pje-etiquetas-api/api/etiquetas/etiquetasprocessos
      filtro client-side pelo id da etiqueta)
     FILTRO INICIAL = SÓ O CHIP. Nenhum outro filtro (fase, órgão julgador,
     responsável) entra na consulta.
  2. usa apenas os 10 primeiros processos
  3. partes do processo pela API (/pje-comum-api/api/processos/id/{id}/partes),
     mesmo payload do Script/calc/BASE/hcalc-overlay-partes.js → todos os
     advogados (representantes com tipo ADVOGADO/OAB)
  4. PLACEHOLDER: filtrar o advogado marcado pelo chip — a chamada de API que
     identifica o advogado correto ainda está sendo investigada pelo Silas
  5. CPF do advogado
  6. validar_cadastro(): /pjekz/pessoa-fisica → CPF → Enter → lápis →
     aba "Advogado" → "Validar na OAB" → radio SP (ou 1ª opção) → Gravar →
     fecha a aba. Se o dialog NÃO tiver radio selecionável, o cadastro está
     SUSPENSO na OAB (a tabela traz Situação = Suspenso) — reporta e segue.
     PULADO quando o `/partes` já traz `situacaoOab` = SUSPENSO ou CANCELADO:
     a API decide sozinha e o passo 7 vai direto ao laço de GIGS. Ausente (e
     REGULAR) validam normalmente.
  7. laço ÚNICO, escolhido pelo resultado da validação (passo 6):
       'ok'       (achou radio SP ou outra inscrição) → reprocessar chips
       'suspenso' (só cadastro suspenso)              → criar_gigs "Advogado
                                                         suspenso"
     Nos dois casos: consulta por CPF + etiqueta → abre cada processo em
     /detalhe → executa a ação → fecha a aba
  → recomeça com o próximo processo da API

Nada aqui abre driver nem faz login: quem chama é o x.py/pw.py.
"""

import re
from typing import Any, Dict, List, Optional

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
URL_CONSULTA_ADV = (
    'https://pje.trt2.jus.br/administracao/consulta/processo/index'
    '?pagina=1&idsOrgaosJulgadores=187&idEtiqueta={etiqueta}&cpf={cpf}'
)

# Id da etiqueta (chip) "Advogado impedido de Atuar" — veio da URL de consulta
# informada pelo Silas (idEtiqueta=918). Se o PJe mudar o id, ajustar aqui.
CHIP_ADVOGADO_IMPEDIDO_ID = 918

LIMITE_PROCESSOS = 10
TAMANHO_PAGINA_API = 100


# =============================================================================
# Helpers
# =============================================================================

def _somente_digitos(valor: Any) -> str:
    """CPF/CNPJ só com dígitos (a API devolve '123.456.789-00')."""
    return re.sub(r'\D', '', str(valor or ''))


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


def _paginar_processos(client: Any) -> List[Dict[str, Any]]:
    """Pagina o agrupamento de tarefas SEM nenhum filtro além da paginação.

    Diretriz do Silas (11/11/2026): o filtro inicial é APENAS o chip indicado,
    mais nada — nada de fase processual, órgão julgador ou responsável.
    """
    todos: List[Dict[str, Any]] = []
    for pagina in range(1, 201):
        body = {
            'pagina': pagina,
            'tamanhoPagina': TAMANHO_PAGINA_API,
            'subCaixa': None,
            'tipoAtividade': None,
            'processos': None,
            'nomeConclusoMagistrado': None,
            'usuarioResponsavel': None,
            'faseProcessualString': None,
            'numeroProcesso': None,
        }
        res = client.gateway_patch(
            '/pje-comum-api/api/agrupamentotarefas/processos/todos',
            json_data=body, timeout=30,
        )
        if not res.get('ok'):
            logger.error('[CHIPADV][API] p%d: %s', pagina, res.get('error'))
            return []
        lista = (res.get('data') or {}).get('resultado') or []
        todos.extend(lista)
        logger.info('[CHIPADV][API] p%d: %d processo(s) (acumulado %d)',
                    pagina, len(lista), len(todos))
        if len(lista) < TAMANHO_PAGINA_API:
            break
    return todos


def buscar_processos_por_chip(client: Any, chip_ids, limite: int = LIMITE_PROCESSOS,
                              tamanho_pagina: int = TAMANHO_PAGINA_API) -> List[Dict[str, Any]]:
    """Processos marcados com um dos chips (`chip_ids`), limitados a `limite`.

    Mesma estratégia do fluxo DOM do bianca (confirmada pelo API Spy): pagina o
    agrupamento de tarefas sem filtro e cruza com as etiquetas de cada processo.
    O ÚNICO filtro é o chip — nada de fase processual.
    """
    ids_alvo = set(int(i) for i in chip_ids)

    todos = _paginar_processos(client)
    if not todos:
        logger.error('[CHIPADV][API] Nenhum processo retornado pelo agrupamento de tarefas')
        return []

    mapa: Dict[Any, List[int]] = {}
    total_lotes = (len(todos) + tamanho_pagina - 1) // tamanho_pagina
    for i in range(0, len(todos), tamanho_pagina):
        lote = todos[i:i + tamanho_pagina]
        ids_proc = [p['id'] for p in lote if p.get('id')]
        if not ids_proc:
            continue
        logger.info('[CHIPADV][API] etiquetas lote %d/%d (%d processo(s))',
                    i // tamanho_pagina + 1, total_lotes, len(ids_proc))
        res_et = client.gateway_post(
            '/pje-etiquetas-api/api/etiquetas/etiquetasprocessos',
            json_data={'idsProcesso': ids_proc}, timeout=20,
        )
        if not res_et.get('ok'):
            logger.warning('[CHIPADV][API] etiquetas lote %d: %s',
                           i // tamanho_pagina + 1, res_et.get('error'))
            continue
        for item in (res_et.get('data') or []):
            pid = item.get('idProcesso')
            etiquetas = [e.get('id') for e in (item.get('etiquetas') or []) if e.get('id')]
            if pid is not None:
                mapa[pid] = etiquetas

    filtrados = [p for p in todos if ids_alvo.intersection(mapa.get(p.get('id'), []))]
    logger.info('[CHIPADV][API] %d/%d processo(s) com o chip %s',
                len(filtrados), len(todos), sorted(ids_alvo))
    return filtrados[:limite]


# =============================================================================
# 3. Partes → advogados
# =============================================================================

def ler_advogados_do_processo(client: Any, id_processo: Any) -> List[Dict[str, Any]]:
    """Todos os advogados (representantes) do processo, pela API de partes.

    Payload igual ao do hcalc-overlay-partes.js: dict com ATIVO/PASSIVO/
    TERCEIROS, cada parte com `representantes` (nome, documento, numeroOab,
    tipo).
    """
    partes = client.partes(str(id_processo)) or {}
    if not isinstance(partes, dict):
        logger.warning('[CHIPADV][PARTES] Payload inesperado para o processo %s', id_processo)
        return []

    advogados: List[Dict[str, Any]] = []
    vistos = set()
    for polo in ('ATIVO', 'PASSIVO', 'TERCEIROS'):
        for parte in (partes.get(polo) or []):
            if not isinstance(parte, dict):
                continue
            for rep in (parte.get('representantes') or []):
                if not isinstance(rep, dict):
                    continue
                tipo = str(rep.get('tipo') or '').upper()
                oab = rep.get('numeroOab') or ''
                if 'ADVOGADO' not in tipo and 'OAB' not in tipo and not oab:
                    continue
                cpf = _somente_digitos(rep.get('documento'))
                if not cpf or cpf in vistos:
                    continue
                vistos.add(cpf)
                advogados.append({
                    'nome': (rep.get('nome') or '').strip(),
                    'cpf': cpf,
                    'oab': oab,
                    # Situação da inscrição na OAB vinda da API de partes:
                    # 'REGULAR', 'CANCELADO', 'SUSPENSO'… ou ausente (o PJe
                    # omite o campo quando não encontra a inscrição).
                    'situacao_oab': rep.get('situacaoOab') or '',
                    'tipo': tipo,
                    'parte': (parte.get('nome') or '').strip(),
                    'polo': polo,
                })
    return advogados


# =============================================================================
# 4. PLACEHOLDER — qual advogado está marcado pelo chip
# =============================================================================

def _filtrar_advogado_do_chip(advogados: List[Dict[str, Any]],
                              processo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """PLACEHOLDER do passo 4.

    A regra de qual advogado está marcado pelo chip "Advogado impedido de
    Atuar" ainda não está definida (o Silas vai explicar como o PJe marca).
    Por ora devolve o PRIMEIRO advogado do processo e loga o aviso — quando a
    regra existir, é só trocar o corpo desta função.
    """
    if not advogados:
        return None
    numero = processo.get('numeroProcesso') or processo.get('numero') or processo.get('id')
    escolhido = advogados[0]
    logger.warning(
        '[CHIPADV][PLACEHOLDER] Regra do chip ainda não definida — usando o '
        'primeiro advogado do processo %s: %s (CPF %s)',
        numero, escolhido.get('nome'), escolhido.get('cpf'),
    )
    return escolhido


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


def _tratar_dialog_oab(driver: Any) -> str:
    """Trata o dialog "Validar na OAB".

    Devolve:
      'ok'       — inscrição selecionada e gravada (ou validação direta, sem dialog)
      'suspenso' — dialog SEM radio selecionável: a tabela traz Situação
                   "Suspenso" → cadastro suspenso na OAB (não é bug, é o dado)
      'falha'    — dialog presente mas não foi possível concluir
    """
    dialogo = esperar_elemento(driver, 'mat-dialog-container pje-modal-atualizar-oab',
                               timeout=15)
    if dialogo is None:
        # Sem múltiplas inscrições o PJe valida direto, sem dialog.
        logger.info('[CHIPADV][VALIDAR] Sem dialog de múltiplas inscrições — validação direta')
        return 'ok'

    radios = espera.elementos(driver, 'mat-dialog-container input[type="radio"]', teto=5)
    if not radios:
        # Sem radio = nenhuma inscrição selecionável. O PJe lista as inscrições
        # numa tabela e marca a Situação; "Suspenso" é o caso que interessa.
        linhas = _linhas_tabela_oab(driver)
        situacoes = [l[3] for l in linhas if len(l) > 3]
        resumo = '; '.join(' | '.join(l) for l in linhas) or 'tabela vazia'
        if any('suspens' in _texto_normalizado(s) for s in situacoes):
            logger.error('[CHIPADV][VALIDAR] CADASTRO SUSPENSO na OAB — %s', resumo)
            return 'suspenso'
        logger.error('[CHIPADV][VALIDAR] Dialog OAB sem inscrição selecionável — %s', resumo)
        return 'falha'

    escolhido = None
    for radio in radios:
        try:
            rotulo = (radio.get_attribute('aria-label') or '').strip()
        except Exception:
            rotulo = ''
        if rotulo.upper().startswith('SP'):
            escolhido = radio
            logger.info('[CHIPADV][VALIDAR] Inscrição SP selecionada: %s', rotulo)
            break
    if escolhido is None:
        escolhido = radios[0]
        try:
            rotulo = (escolhido.get_attribute('aria-label') or '').strip()
        except Exception:
            rotulo = ''
        logger.info('[CHIPADV][VALIDAR] Nenhuma inscrição SP — usando a primeira: %s', rotulo)

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


def validar_cadastro(driver: Any, cpf: str) -> str:
    """Passo 6 — valida o cadastro do advogado na OAB.

    Abre /pjekz/pessoa-fisica em ABA NOVA (o passo K manda fechar esta aba),
    pesquisa o CPF, entra no cadastro pelo lápis, abre a aba "Advogado",
    clica "Validar na OAB", escolhe a inscrição SP (ou a primeira) e grava.

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

        status = _tratar_dialog_oab(driver)
        if status == 'ok':
            logger.info('[CHIPADV][VALIDAR] Cadastro validado na OAB — CPF %s', cpf)
        return status
    except Exception as e:
        logger.error('[CHIPADV][VALIDAR] Erro: %s: %s', type(e).__name__, e)
        return 'falha'
    finally:
        _fechar_aba(driver, aba, principal)


# =============================================================================
# 7. Ação por processo do advogado (GIGS "Advogado suspenso" / reprocessar chips)
# =============================================================================

# Chip que o dialog de reprocessamento lista em "Chips a serem excluídos".
CHIP_TEXTO_IMPEDIDO = 'Advogado Impedido de Atuar'

# Observação da atividade GIGS criada no /detalhe (passo 7 do fluxo).
OBS_GIGS_ADV_SUSPENSO = 'Advogado suspenso'


def _reprocessar_chips_do_processo(driver: Any) -> bool:
    """Aciona "Reprocessar chips do processo" e FINALIZA o dialog.

    O clique no menu só abre o dialog "Chips a serem excluídos"; sem o Salvar
    ele fica aberto e a função nunca termina (era o defeito relatado pelo
    Silas em 11/11/2026). Sequência completa:

      1. menu do processo → "Reprocessar chips do processo"
      2. espera `#matChipAccordionExcluir` com o chip "Advogado Impedido de
         Atuar" na lista a excluir
      3. clica "Salvar" no dialog e espera o dialog fechar
    """
    menu = esperar_elemento(driver, 'button[aria-label="Menu do processo"]', timeout=15)
    if menu is None:
        logger.warning('[CHIPADV][CHIPS] Menu do processo não encontrado')
        return False
    safe_click_no_scroll(driver, menu)

    botao = esperar_elemento(driver, 'button[aria-label="Reprocessar chips do processo"]',
                             timeout=10)
    if botao is None:
        logger.warning('[CHIPADV][CHIPS] Botão "Reprocessar chips do processo" não apareceu')
        return False
    safe_click_no_scroll(driver, botao)

    # 1. o accordion "Chips a serem excluídos" precisa aparecer
    if not espera.ate_aparecer(driver, '#matChipAccordionExcluir', teto=20):
        logger.warning('[CHIPADV][CHIPS] Dialog de reprocessamento não abriu '
                       '(#matChipAccordionExcluir ausente)')
        return False

    # 2. e o chip alvo precisa estar na lista a excluir
    if not espera.ate_js(driver, """
        (function () {
            var acc = document.querySelector('#matChipAccordionExcluir');
            if (!acc) return false;
            var chips = acc.querySelectorAll('mat-chip');
            for (var i = 0; i < chips.length; i++) {
                var t = (chips[i].getAttribute('aria-label') || '') + ' ' +
                        (chips[i].textContent || '');
                if (t.indexOf('%s') !== -1) return true;
            }
            return false;
        })()
    """ % CHIP_TEXTO_IMPEDIDO, teto=10):
        logger.warning('[CHIPADV][CHIPS] Chip "%s" não está na lista a excluir — '
                       'não vou salvar', CHIP_TEXTO_IMPEDIDO)
        return False

    # 3. Salvar finaliza o reprocessamento
    salvar = _elemento_por_texto(driver, 'mat-dialog-container button', 'Salvar', teto=10)
    if salvar is None:
        salvar = _elemento_por_texto(driver, 'button', 'Salvar', teto=5)
    if salvar is None:
        logger.warning('[CHIPADV][CHIPS] Botão "Salvar" do dialog não encontrado')
        return False
    safe_click_no_scroll(driver, salvar)

    if not espera.ate_sumir(driver, '#matChipAccordionExcluir', teto=20):
        logger.warning('[CHIPADV][CHIPS] Dialog de reprocessamento não fechou após Salvar')
        return False

    logger.info('[CHIPADV][CHIPS] Chips reprocessados (dialog salvo)')
    return True


def _criar_gigs_advogado_suspenso(driver: Any) -> bool:
    """Cria a atividade GIGS "Advogado suspenso" no /detalhe (passo 7 do fluxo)."""
    from Fix.extracao import criar_gigs

    ok = bool(criar_gigs(driver, '', '', OBS_GIGS_ADV_SUSPENSO))
    if ok:
        logger.info('[CHIPADV][GIGS] Atividade "%s" criada', OBS_GIGS_ADV_SUSPENSO)
    else:
        logger.warning('[CHIPADV][GIGS] Falha ao criar a atividade "%s"',
                       OBS_GIGS_ADV_SUSPENSO)
    return ok


def _executar_na_linha(driver: Any, indice: int, aba_lista: str, url_lista: str,
                       acao, rotulo: str) -> bool:
    """Abre o processo da linha `indice`, roda `acao(driver)` e fecha a aba."""
    botoes = espera.elementos(
        driver, 'mat-row button[aria-label^="Detalhes do Processo"]', teto=5)
    if indice >= len(botoes):
        logger.warning('[CHIPADV][%s] Linha %d sem botão de detalhes', rotulo, indice + 1)
        return False

    antes = set(_obter_window_handles(driver) or [])
    safe_click_no_scroll(driver, botoes[indice])

    nova = None
    if espera.ate_abas(driver, len(antes) + 1, teto=15):
        for h in (_obter_window_handles(driver) or []):
            if h not in antes:
                driver.switch_to.window(h)
                nova = h
                break

    mesma_aba = nova is None
    if mesma_aba:
        # O clique navegou a própria aba da lista para o /detalhe.
        if '/detalhe' not in (driver.current_url or ''):
            logger.warning('[CHIPADV][%s] Linha %d não abriu /detalhe', rotulo, indice + 1)
            return False
        nova = aba_lista

    ok = False
    try:
        espera.ate_url(driver, '/detalhe', teto=25)
        ok = bool(acao(driver))
    except Exception as e:
        logger.warning('[CHIPADV][%s] Linha %d: %s: %s', rotulo, indice + 1,
                       type(e).__name__, e)
    finally:
        if mesma_aba:
            # A lista foi substituída pelo detalhe: volta para a consulta.
            try:
                driver.get(url_lista)
                espera.ate_js(driver, "__pjeEls('mat-row').length > 0", teto=30)
            except Exception:
                pass
        else:
            _fechar_aba(driver, nova, aba_lista)
    return ok


def _percorrer_processos_do_cpf(driver: Any, cpf: str, etiqueta_id: int,
                                acao, rotulo: str) -> int:
    """Consulta os processos do CPF e roda `acao(driver)` em cada /detalhe.

    Navega para a consulta administrativa filtrada por CPF + etiqueta, abre
    cada processo em /detalhe, executa a ação e fecha a aba. Devolve quantos
    processos foram processados com sucesso.
    """
    cpf = _somente_digitos(cpf)
    url_lista = URL_CONSULTA_ADV.format(etiqueta=etiqueta_id, cpf=cpf)
    principal = driver.current_window_handle

    aba_lista = abrir_url_nova_aba(driver, url_lista)
    if not aba_lista:
        logger.error('[CHIPADV][%s] Não foi possível abrir a consulta do CPF %s',
                     rotulo, cpf)
        return 0

    processados = 0
    total = 0
    try:
        if not espera.ate_url(driver, 'administracao/consulta/processo', teto=30):
            logger.warning('[CHIPADV][%s] Consulta não carregou (CPF %s)', rotulo, cpf)
        if not espera.ate_js(driver, "__pjeEls('mat-row').length > 0", teto=30):
            logger.info('[CHIPADV][%s] Nenhum processo na consulta do CPF %s', rotulo, cpf)
            return 0

        total = len(espera.elementos(driver, 'mat-row', teto=2))
        logger.info('[CHIPADV][%s] %d processo(s) na consulta do CPF %s', rotulo, total, cpf)

        for indice in range(total):
            if _executar_na_linha(driver, indice, aba_lista, url_lista, acao, rotulo):
                processados += 1
    except Exception as e:
        logger.error('[CHIPADV][%s] Erro: %s: %s', rotulo, type(e).__name__, e)
    finally:
        _fechar_aba(driver, aba_lista, principal)

    logger.info('[CHIPADV][%s] %d/%d processo(s) processado(s) para o CPF %s',
                rotulo, processados, total, cpf)
    return processados


def reprocessar_chips_do_advogado(driver: Any, cpf: str,
                                  etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> int:
    """Reprocessa os chips de todos os processos do advogado (CPF + etiqueta)."""
    return _percorrer_processos_do_cpf(
        driver, cpf, etiqueta_id, _reprocessar_chips_do_processo, 'CHIPS')


def criar_gigs_do_advogado(driver: Any, cpf: str,
                           etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> int:
    """Passo 7 do fluxo — cria GIGS "Advogado suspenso" nos processos do CPF.

    Mesma lógica do reprocessar chips (consulta por CPF + etiqueta, abre cada
    processo em /detalhe), mas a ação é `criar_gigs(..., 'Advogado suspenso')`.
    """
    return _percorrer_processos_do_cpf(
        driver, cpf, etiqueta_id, _criar_gigs_advogado_suspenso, 'GIGS')


# =============================================================================
# Orquestrador
# =============================================================================

def run_chipadv(driver: Any, limite: int = LIMITE_PROCESSOS,
                chip_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> Dict[str, Any]:
    """Fluxo CHIPADV completo. Recebe o driver já logado (pw.py/x.py)."""
    logger.info('[CHIPADV] === INICIANDO FLUXO CHIP ADVOGADO IMPEDIDO ===')
    resultado: Dict[str, Any] = {
        'sucesso': False,
        'total': 0,
        'processados': 0,
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

    # 1 + 2. processos com o chip (só os 10 primeiros)
    try:
        client = _criar_client(driver)
    except Exception as e:
        logger.error('[CHIPADV] Falha ao criar o cliente de API: %s: %s',
                     type(e).__name__, e)
        resultado['erros'].append(f'api: {e}')
        return resultado

    processos = buscar_processos_por_chip(client, (chip_id,), limite=limite)
    resultado['total'] = len(processos)
    if not processos:
        logger.warning('[CHIPADV] Nenhum processo com o chip %s — nada a fazer', chip_id)
        resultado['sucesso'] = True
        return resultado

    for proc in processos:
        numero = (proc.get('numeroProcesso') or proc.get('numero')
                  or str(proc.get('id')))
        logger.info('[CHIPADV] Processo %s (id=%s)', numero, proc.get('id'))

        # 3. partes → advogados
        advogados = ler_advogados_do_processo(client, proc.get('id'))
        logger.info('[CHIPADV] %d advogado(s) no processo %s', len(advogados), numero)

        # 4 + 5. advogado marcado pelo chip → CPF
        advogado = _filtrar_advogado_do_chip(advogados, proc)
        if not advogado:
            logger.warning('[CHIPADV] Processo %s sem advogado — pulando', numero)
            resultado['erros'].append(f'{numero}: sem advogado')
            continue
        cpf = advogado['cpf']
        logger.info('[CHIPADV] Advogado %s — CPF %s', advogado.get('nome'), cpf)

        # 6. validar cadastro — o RESULTADO define qual laço roda no passo 7.
        #    Exceção: quando a API de partes JÁ diz SUSPENSO ou CANCELADO, não
        #    há o que validar — vai direto ao laço de GIGS, sem abrir
        #    /pessoa-fisica nem o dialog. Ausente (e REGULAR) validam normal.
        situacao_oab = (advogado.get('situacao_oab') or '').strip().upper()
        if situacao_oab in ('SUSPENSO', 'CANCELADO'):
            logger.warning('[CHIPADV] Advogado %s (CPF %s) — situacaoOab=%r na API '
                           '— pulando validação, laço de GIGS',
                           advogado.get('nome'), cpf, situacao_oab)
            status_oab = 'suspenso'
        else:
            status_oab = validar_cadastro(driver, cpf)

        if status_oab == 'falha':
            resultado['erros'].append(f'{numero}: validar cadastro falhou ({cpf})')
            continue

        # 7. laço único, escolhido pela validação:
        #    'ok'       (achou radio SP ou outra inscrição) → reprocessar chips
        #    'suspenso' (só cadastro suspenso)              → GIGS "Advogado suspenso"
        if status_oab == 'suspenso':
            logger.warning('[CHIPADV] Advogado %s (CPF %s) com cadastro SUSPENSO na OAB '
                           '— laço de GIGS', advogado.get('nome'), cpf)
            resultado.setdefault('suspensos', []).append(cpf)
            qtd = criar_gigs_do_advogado(driver, cpf, chip_id)
            logger.info('[CHIPADV] %d processo(s) com GIGS "%s" para %s',
                        qtd, OBS_GIGS_ADV_SUSPENSO, cpf)
        else:
            logger.info('[CHIPADV] Advogado %s (CPF %s) validado na OAB — laço de chips',
                        advogado.get('nome'), cpf)
            qtd = reprocessar_chips_do_advogado(driver, cpf, chip_id)
            logger.info('[CHIPADV] %d processo(s) com chips reprocessados para %s', qtd, cpf)
        resultado['processados'] += 1

    resultado['sucesso'] = not resultado['erros']
    logger.info('[CHIPADV] total=%d processados=%d erros=%d',
                resultado['total'], resultado['processados'], len(resultado['erros']))
    return resultado
