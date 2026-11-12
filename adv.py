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

# Consulta administrativa usada pela tela /administracao/consulta/processo.
# É a chamada que filtra pelo chip: `idEtiqueta` = id do chip.
URL_CONSULTA_API = '/pje-administracao-api/api/consultaprocessosadm'

# Recorte fixo da consulta (mesmo OJ da URL informada pelo Silas). Sem o
# `idsOrgaosJulgadores` o PJe ignora o `idEtiqueta` e devolve a base inteira.
ORGAO_JULGADOR_CONSULTA = 187

# Aba /detalhe aberta direto pelo id interno devolvido pela consulta.
URL_PROCESSO_DETALHE = 'https://pje.trt2.jus.br/pjekz/processo/{id}/detalhe'

# Id da etiqueta (chip) "Advogado impedido de Atuar" — veio da URL de consulta
# informada pelo Silas (idEtiqueta=918). Se o PJe mudar o id, ajustar aqui.
CHIP_ADVOGADO_IMPEDIDO_ID = 918

TAMANHO_PAGINA_API = 100


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
    """'SP128341' / 'PE22616' / 'AP1551-A' -> ('SP', 128341)."""
    m = re.match(r'\s*([A-Za-z]{2})\s*(\d+)', str(numero_oab or ''))
    if not m:
        return None, None
    return m.group(1).upper(), _inteiro(m.group(2), 0)


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
# 3. Partes → advogados
# =============================================================================

def ler_advogados_do_processo(client: Any, id_processo: Any,
                              com_inativas: bool = True) -> List[Dict[str, Any]]:
    """Todos os advogados (representantes) do processo, pela API de partes.

    `com_inativas=True` inclui as partes/advogados inativos: é o que o PJe usa
    para montar o chip "Advogado impedido" (parte inativa + cadastro inativo).
    Sem esse parâmetro a API devolve só os ativos e o chip fica sem explicação.

    Payload igual ao do hcalc-overlay-partes.js: dict com ATIVO/PASSIVO/
    TERCEIROS, cada parte com `representantes` (nome, documento, numeroOab,
    tipo).
    """
    partes = client.partes(str(id_processo), com_inativas=com_inativas) or {}
    # A variante paginada (`dadosPaginados=true`) devolve {'resultado': {...}}.
    if isinstance(partes, dict) and isinstance(partes.get('resultado'), dict):
        partes = partes['resultado']
    if (com_inativas and isinstance(partes, dict)
            and not any(partes.get(p) for p in ('ATIVO', 'PASSIVO', 'TERCEIROS'))):
        # Se a variante com inativas não vier (ou vier só o envelope), cai
        # para a consulta padrão — melhor ver os ativos do que nenhum.
        partes = client.partes(str(id_processo)) or {}
        if isinstance(partes, dict) and isinstance(partes.get('resultado'), dict):
            partes = partes['resultado']
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
                    'id_pessoa': rep.get('idPessoa') or rep.get('id'),
                    'status': rep.get('status') or '',
                    'situacao': rep.get('situacao') or '',
                    'ativo': _representante_ativo(rep),
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
# 4. Qual advogado do processo entra no laço
# =============================================================================

def _filtrar_advogado_do_chip(advogados: List[Dict[str, Any]],
                              processo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Escolhe o advogado que o laço vai considerar neste processo.

    A leitura já traz os inativos (comInativas=true), mas a regra do laço
    ainda não foi fechada — por ora fica o primeiro ATIVO (para não abrir
    validação de um inativo, que nem aparece no painel do /detalhe).
    """
    if not advogados:
        return None
    ativos = [a for a in advogados if a.get('ativo', True)]
    escolhido = (ativos or advogados)[0]
    numero = processo.get('numeroProcesso') or processo.get('numero') or processo.get('id')
    logger.warning(
        '[CHIPADV][PLACEHOLDER] Regra do laço ainda não definida — usando o '
        'primeiro advogado ativo do processo %s: %s (CPF %s, inativo=%s)',
        numero, escolhido.get('nome'), escolhido.get('cpf'),
        not escolhido.get('ativo', True),
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


def _tratar_dialog_oab(driver: Any, oab_alvo: Any = None) -> str:
    """Trata o dialog "Validar na OAB".

    `oab_alvo` (ex.: 'PE22616'/'AP1551') é a inscrição que o processo usa:
    quando informada, a seleção prioriza essa linha (UF + número), e não
    "SP ou a primeira" — o que escolheria a OAB errada num advogado com
    várias inscrições.

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

    alvo_uf, alvo_num = _partir_oab(oab_alvo)

    escolhido = None
    if alvo_uf and alvo_num:
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
            rot_uf, rot_num = _partir_oab(rotulo)
            if rot_uf == alvo_uf and rot_num == alvo_num:
                escolhido = radio
                logger.info('[CHIPADV][VALIDAR] Inscrição do processo selecionada: %s',
                            rotulo)
                break
    if escolhido is None:
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
        logger.info('[CHIPADV][VALIDAR] Nenhuma inscrição do processo/SP — '
                    'usando a primeira: %s', rotulo)

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


def validar_cadastro(driver: Any, cpf: str, oab_alvo: Any = None) -> str:
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

        status = _tratar_dialog_oab(driver, oab_alvo=oab_alvo)
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


def _executar_no_detalhe(driver: Any, id_processo: Any, acao, rotulo: str,
                         numero: Any = '') -> bool:
    """Abre /pjekz/processo/{id}/detalhe em aba nova, roda `acao` e fecha.

    A ida direto pela URL dispensa a tela de consulta e o clique na linha
    (que dependia do índice da `mat-row` e voltava a carregar a lista). O id
    vem da própria consulta da API.
    """
    alvo = numero or id_processo
    principal = driver.current_window_handle
    aba = abrir_url_nova_aba(driver, URL_PROCESSO_DETALHE.format(id=id_processo))
    if not aba:
        logger.warning('[CHIPADV][%s] Não foi possível abrir /detalhe de %s',
                       rotulo, alvo)
        return False

    try:
        if not espera.ate_url(driver, '/detalhe', teto=30):
            logger.warning('[CHIPADV][%s] /detalhe não carregou para %s', rotulo, alvo)
            return False
        # Qualquer um destes confirma que o /detalhe renderizou; as ações
        # usam o menu do processo (chips) ou o botão "Nova Atividade" (GIGS).
        if not espera.ate_aparecer(
                driver,
                'pje-cabecalho-processo, pje-timeline, '
                'button[aria-label="Menu do processo"]',
                teto=30):
            logger.warning('[CHIPADV][%s] /detalhe sem os elementos esperados: %s',
                           rotulo, alvo)
            return False
        return bool(acao(driver))
    except Exception as e:
        logger.warning('[CHIPADV][%s] Processo %s: %s: %s', rotulo, alvo,
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
                                etiqueta_id: int, acao, rotulo: str):
    """Roda `acao(driver)` em cada processo do CPF que tem o chip.

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
        if _executar_no_detalhe(driver, id_processo, acao, rotulo, numero):
            processados += 1

    logger.info('[CHIPADV][%s] %d/%d processo(s) processado(s) para o CPF %s',
                rotulo, processados, total, cpf)
    return processados, ids, True


def reprocessar_chips_do_advogado(driver: Any, cpf: str,
                                  etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                                  client: Any = None) -> int:
    """Reprocessa os chips de todos os processos do advogado (CPF + chip)."""
    client = client or _criar_client(driver)
    qtd, _, _ = _percorrer_processos_do_cpf(
        driver, client, cpf, etiqueta_id, _reprocessar_chips_do_processo, 'CHIPS')
    return qtd


def criar_gigs_do_advogado(driver: Any, cpf: str,
                           etiqueta_id: int = CHIP_ADVOGADO_IMPEDIDO_ID,
                           client: Any = None) -> int:
    """Passo 7 do fluxo — cria GIGS "Advogado suspenso" nos processos do CPF.

    Mesma lógica do reprocessar chips (consulta por CPF + chip, abre cada
    processo em /detalhe), mas a ação é `criar_gigs(..., 'Advogado suspenso')`.
    """
    client = client or _criar_client(driver)
    qtd, _, _ = _percorrer_processos_do_cpf(
        driver, client, cpf, etiqueta_id, _criar_gigs_advogado_suspenso, 'GIGS')
    return qtd


# =============================================================================
# Orquestrador
# =============================================================================

def run_chipadv(driver: Any, limite: Optional[int] = None,
                chip_id: int = CHIP_ADVOGADO_IMPEDIDO_ID) -> Dict[str, Any]:
    """Fluxo CHIPADV completo. Recebe o driver já logado (pw.py/x.py).

    `limite`: teto opcional de processos EXAMINADOS no laço externo (só para
    testes). `None` percorre todos os processos do chip.
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

    # 1 + 2. processos com o chip — uma consulta (página 1) para saber o total;
    #        as demais páginas são buscadas conforme o laço avança.
    try:
        client = _criar_client(driver)
    except Exception as e:
        logger.error('[CHIPADV] Falha ao criar o cliente de API: %s: %s',
                     type(e).__name__, e)
        resultado['erros'].append(f'api: {e}')
        return resultado

    total_chip, processos = iniciar_busca_processos_por_chip(client, chip_id)
    resultado['total'] = total_chip
    if not total_chip:
        logger.warning('[CHIPADV] Nenhum processo com o chip %s — nada a fazer', chip_id)
        resultado['sucesso'] = True
        return resultado

    logger.info('[CHIPADV] Total com o chip %s: %d processo(s) — um por vez',
                chip_id, total_chip)

    # Registro da execução: CPF → ação do lote, e ids que o lote já cobriu.
    cpfs_tratados: Dict[str, Dict[str, Any]] = {}
    ids_tratados: set = set()
    examinados = 0

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

        # Já coberto pelo lote de um CPF anterior: não reabre.
        if id_proc in ids_tratados:
            logger.info('[CHIPADV] Processo %s já tratado no lote de um CPF — pulando',
                        numero)
            resultado['ignorados'] += 1
            continue

        # 3. partes → advogados (com inativos na leitura; o laço usa o 1º ativo)
        advogados = ler_advogados_do_processo(client, id_proc, com_inativas=True)
        inativos = [a for a in advogados if not a.get('ativo')]
        logger.info('[CHIPADV] %d advogado(s) no processo %s (%d inativo(s))',
                    len(advogados), numero, len(inativos))

        # 4 + 5. advogado do laço → CPF
        advogado = _filtrar_advogado_do_chip(advogados, proc)
        if not advogado:
            logger.warning('[CHIPADV] Processo %s sem advogado — pulando', numero)
            resultado['erros'].append(f'{numero}: sem advogado')
            continue
        cpf = advogado['cpf']
        logger.info('[CHIPADV] Advogado %s — CPF %s', advogado.get('nome'), cpf)

        # CPF já tratado (em qualquer um dos dois laços) → o lote dele cobriu
        # todos os processos com o chip; este aqui é informação desatualizada.
        if cpf in cpfs_tratados:
            logger.info('[CHIPADV] CPF %s já tratado (%s) — processo %s pulado',
                        cpf, cpfs_tratados[cpf].get('acao'), numero)
            resultado['ignorados'] += 1
            continue

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
            acao = 'gigs'
            qtd, ids, consulta_ok = _percorrer_processos_do_cpf(
                driver, client, cpf, chip_id, _criar_gigs_advogado_suspenso, 'GIGS')
            logger.info('[CHIPADV] %d processo(s) com GIGS "%s" para %s',
                        qtd, OBS_GIGS_ADV_SUSPENSO, cpf)
        else:
            logger.info('[CHIPADV] Advogado %s (CPF %s) validado na OAB — laço de chips',
                        advogado.get('nome'), cpf)
            acao = 'chips'
            qtd, ids, consulta_ok = _percorrer_processos_do_cpf(
                driver, client, cpf, chip_id, _reprocessar_chips_do_processo, 'CHIPS')
            logger.info('[CHIPADV] %d processo(s) com chips reprocessados para %s', qtd, cpf)

        if not consulta_ok:
            resultado['erros'].append(f'{numero}: consulta do CPF {cpf} falhou')
            continue

        # Registra o CPF tratado (qualquer um dos laços) e os processos que o
        # lote cobriu — o laço externo não volta neles.
        cpfs_tratados[cpf] = {
            'acao': acao,
            'processos': len(ids),
            'ok': qtd,
        }
        ids_tratados.update(ids)
        resultado['cpfs'][cpf] = cpfs_tratados[cpf]
        resultado['processados'] += 1

    resultado['sucesso'] = not resultado['erros']
    logger.info('[CHIPADV] total=%d examinados=%d processados=%d ignorados=%d erros=%d',
                resultado['total'], examinados, resultado['processados'],
                resultado['ignorados'], len(resultado['erros']))
    return resultado
