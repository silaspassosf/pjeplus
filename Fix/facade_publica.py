"""Agregador da superficie publica e dos shims leves de compatibilidade do Fix.

Esta unidade concentra re-exports, aliases e implementacoes curtas que antes
estavam dispersas em ~15 arquivos separados (< 150 linhas cada). Os donos reais
da implementacao continuam em ``Fix.core``, ``Fix.extracao``, ``Fix.utils``,
``Fix.abas`` e ``Fix.monitoramento_progresso_unificado``.

Fontes consolidadas:
  - Fix.__init__, Fix.drivers/*, Fix.progress/*, Fix.scripts/__init__
  - Fix.element_wait, Fix.smart_finder, Fix.exceptions
  - Fix.documents, Fix.navigation, Fix.gigs
  - Fix.variaveis_client, Fix.variaveis_helpers, Fix.variaveis_resolvers
  - Fix.selectors_pje (parcial), Fix.movimento_helpers
"""

from pathlib import Path
from Fix.core import safe_click_no_scroll
from typing import Dict, Optional, Tuple, Union

from Play.pjeplay.locators import By
from Fix import espera as _espera

# =============================================================================
# CORE - Re-exports from Fix.core
# =============================================================================
from .core import (
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    preencher_campos_prazo,
    preencher_multiplos_campos,
    com_retry,
    buscar_seletor_robusto,
    extrair_id_processo,
    esperar_elemento,
    esperar_url_conter,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    smart_sleep,
    sleep,
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_pc,
    criar_driver_vt,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
    salvar_cookies_sessao,
    carregar_cookies_sessao,
    verificar_e_aplicar_cookies,
    aplicar_filtro_100,
    filtro_fase,
    verificar_documento_decisao_sentenca,
    visibilidade_sigilosos,
    buscar_ultimo_mandado,
    buscar_mandado_autor,
    buscar_documentos_sequenciais,
    buscar_documentos_polo_ativo,
    criar_botoes_detalhes,
    ErroCollector,
    js_base,
    buscar_documento_argos,
)

# =============================================================================
# EXTRACAO - Re-exports from Fix.extracao
# =============================================================================
from .extracao import (
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    extrair_dados_processo,
    extrair_destinatarios_decisao,
    criar_gigs,
    criar_comentario,
    criar_lembrete_posit,
    bndt,
    filtrofases,
    indexar_processos,
    reindexar_linha,
    abrir_detalhes_processo,
    indexar_e_processar_lista,
    analise_argos,
    tratar_anexos_argos,
    analise_outros,
    salvar_destinatarios_cache,
    carregar_destinatarios_cache,
)

# =============================================================================
# UTILS - Re-exports from Fix.utils
# =============================================================================
from .utils import (
    formatar_moeda_brasileira,
    formatar_data_brasileira,
    normalizar_cpf_cnpj,
    limpar_temp_selenium,
    login_manual,
    login_automatico,
    login_automatico_direto,
    login_cpf,
    login_pc,
    coletar_link_ato_timeline,
    coletar_conteudo_js,
    coletar_elemento_css,
    executar_coleta_parametrizavel,
    inserir_html_editor,
    inserir_texto_editor,
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    inserir_link_ato,
    inserir_link_ato_validacao,
    configurar_recovery_driver,
    verificar_e_tratar_acesso_negado_global,
    handle_exception_with_recovery,
    obter_driver_padronizado,
    driver_pc,
    navegar_para_tela,
    normalizar_texto,
    obter_credencial,
)

# =============================================================================
# ABAS - Re-exports from Fix.abas (FX2 - browser/session support)
# =============================================================================
from .abas import (
    validar_conexao_driver,
    trocar_para_nova_aba,
    forcar_fechamento_abas_extras,
    is_browsing_context_discarded_error,
)

# =============================================================================
# PROGRESSO - Re-exports from Fix.monitoramento_progresso_unificado
# =============================================================================
from .monitoramento_progresso_unificado import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
)

# =============================================================================
# ERROR CLASSES
# =============================================================================

class PJePlusError(Exception):
    pass


class ElementoNaoEncontradoError(PJePlusError):
    pass


class NavegacaoError(PJePlusError):
    pass

# =============================================================================
# API CLIENT RE-EXPORTS (formerly Fix.variaveis_client / _helpers / _resolvers)
# =============================================================================
from api.variaveis_client import PjeApiClient, session_from_driver

from api.variaveis_helpers import (
    obter_gigs_com_fase,
    obter_texto_documento,
    buscar_atividade_gigs_por_observacao,
    obter_todas_atividades_gigs_com_observacao,
    padrao_liq,
    verificar_bndt,
)

from api.variaveis_resolvers import (
    obter_codigo_validacao_documento,
    obter_peca_processual_da_timeline,
    resolver_variavel,
    get_all_variables,
    obter_chave_ultimo_despacho_decisao_sentenca,
)

# =============================================================================
# SELECTORS PJe (formerly Fix.selectors_pje)
# =============================================================================

BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'
EDITOR_AREA_CONTEUDO = 'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]'
BTN_GRAVAR_MOVIMENTOS = "pje-lancador-movimentos-dialogo button[aria-label='Gravar os movimentos a serem lançados']"
BTN_EXPANDIR_CHIPS = 'pje-lista-etiquetas button[aria-label="Expandir Chips"]'
CHIPS_LISTA = "//pje-lista-etiquetas//mat-chip"
DIALOG_PRAZO_SOBRESTAMENTO = 'pje-dialog-prazo-sobrestamento'

# buscar_seletor_robusto is re-exported from Fix.core above

# =============================================================================
# MOVIMENTO HELPERS (formerly Fix.movimento_helpers)
# =============================================================================

import re as _re
import time as _time


def _normalize_text(s: str) -> str:
    if not s:
        return ''
    s = normalizar_texto(s.strip())  # canonical from Fix.utils
    s = _re.sub(r'\s+', ' ', s)
    return s


def executar_movimento_judicial(driver, movimento: Union[str, int]) -> bool:
    """Executa o lançamento de movimentos no editor de atos judiciais.

    Implementação canônica baseada no padrão comprovado do gigs-plugin.js (aaDespacho):
      1) Ativa a guia Movimentos (pje-editor-lateral div[aria-posinset="2"]) se desativada;
      2) Decompõe o movimento em etapa primária e complementos secundários;
      3) Localiza e marca a caixa de seleção do movimento primário (pje-movimento mat-checkbox label);
      4) Para cada complemento secundário (dropdown / opção / input):
         - Localiza o campo no container daquele movimento (pje-complemento mat-form-field[class*="ng-untouched"]);
         - Se for combobox (mat-select): abre o dropdown e clica na mat-option com o texto da opção;
         - Se for input/textarea: preenche o valor e despacha eventos input/change;
      5) Clica no botão Gravar do lançador (pje-lancador-de-movimentos button[aria-label*="Gravar"]);
      6) Confirma no diálogo (mat-dialog-container button 'Sim') caso seja exibido.

    Retorna True em caso de sucesso, False caso contrário.
    """
    if not movimento or str(movimento).lower() in ('nenhum', 'none', 'false'):
        return True

    mov_str = str(movimento).strip()

    js_movimento = """
    async (movimentoStr) => {
        function norm(t) {
            if (!t) return '';
            return t.normalize('NFKD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase()
                .replace(/[\\r\\n\\t]+/g, ' ')
                .trim();
        }

        function sleep(ms) {
            return new Promise(r => setTimeout(r, ms));
        }

        if (!movimentoStr) return { sucesso: false, erro: 'Movimento vazio' };

        // 1. Ativar guia Movimentos no pje-editor-lateral se desativada (gigs-plugin ~11848)
        let guia = document.querySelector('pje-editor-lateral div[aria-posinset="2"]');
        if (!guia) {
            const tabs = Array.from(document.querySelectorAll('pje-editor-lateral div[role="tab"], .mat-tab-label'));
            guia = tabs.find(t => {
                const txt = norm(t.textContent || '');
                return txt.includes('movimento');
            });
        }
        if (guia) {
            if (guia.getAttribute('aria-selected') === 'false') {
                guia.click();
                await sleep(600);
            }
        }

        // 2. Decomposição do movimento (gigs-plugin ~11854)
        // Suporta divisores de movimentos múltiplos e estágios (/ ou , ou ; ou ' - ')
        let str = String(movimentoStr).trim();
        let padraoDivisor = /(?<!\\d{7})\\-/gm;
        let complementosPrimarios = str.includes('/') ? [str] : str.split(padraoDivisor);

        const lancador = document.querySelector('pje-lancador-de-movimentos') || document;

        for (let comp of complementosPrimarios) {
            comp = comp.trim();
            if (!comp) continue;

            let partes = [];
            if (comp.includes('/')) {
                partes = comp.split('/').map(s => s.trim()).filter(Boolean);
            } else if (comp.includes(',')) {
                partes = comp.split(',').map(s => s.trim()).filter(Boolean);
            } else if (comp.includes(';')) {
                partes = comp.split(';').map(s => s.trim()).filter(Boolean);
            } else {
                partes = [comp];
            }

            let primario = partes[0] || '';
            let secundarios = partes.slice(1);
            let primarioNorm = norm(primario);

            // 3. Localizar pje-movimento mat-checkbox e label (gigs-plugin ~11870)
            let chkAlvo = null;
            let labelAlvo = null;
            let blocoAlvo = null;

            const blocos = Array.from(lancador.querySelectorAll('pje-movimento'));
            for (const b of blocos) {
                const chk = b.querySelector('mat-checkbox');
                const lbl = b.querySelector('mat-checkbox label, label.mat-checkbox-layout, label') || chk;
                if (!chk || !lbl) continue;
                const txt = norm(lbl.innerText || lbl.textContent || '');

                let match = false;
                if (txt.includes(primarioNorm)) {
                    match = true;
                } else if (/^\\d+$/.test(primarioNorm)) {
                    if (txt.includes('(' + primarioNorm + ')') || txt.split(/\\s+/).includes(primarioNorm)) {
                        match = true;
                    }
                } else if (primarioNorm === 'frustrada' && (txt.includes('execucao frustrada') || txt.includes('276'))) {
                    match = true;
                }

                if (match) {
                    blocoAlvo = b;
                    chkAlvo = chk;
                    labelAlvo = lbl;
                    break;
                }
            }

            // Fallback: busca qualquer mat-checkbox dentro do lançador
            if (!chkAlvo) {
                const todosChk = Array.from(lancador.querySelectorAll('mat-checkbox'));
                for (const chk of todosChk) {
                    const lbl = chk.querySelector('label') || chk;
                    const txt = norm(lbl.innerText || lbl.textContent || '');
                    if (txt.includes(primarioNorm) || (/^\\d+$/.test(primarioNorm) && txt.includes('(' + primarioNorm + ')'))) {
                        chkAlvo = chk;
                        labelAlvo = lbl;
                        blocoAlvo = chk.closest('pje-movimento') || chk.parentElement.parentElement || chk.parentElement;
                        break;
                    }
                }
            }

            if (!chkAlvo) {
                return { sucesso: false, erro: 'Movimento não localizado no lançador: ' + primario };
            }

            // Marcar checkbox caso não esteja marcado (gigs-plugin ~11872)
            const isChecked = chkAlvo.classList.contains('mat-checkbox-checked') ||
                              chkAlvo.classList.contains('mat-mdc-checkbox-checked') ||
                              (chkAlvo.querySelector('input[type=\"checkbox\"]') && chkAlvo.querySelector('input[type=\"checkbox\"]').checked);

            if (!isChecked) {
                const target = labelAlvo || chkAlvo.querySelector('.mat-checkbox-inner-container') || chkAlvo;
                target.click();
                await sleep(600); // Aguarda Angular instanciar complementos
            }

            // 4. Preencher complementos secundários (dropdown / opção / input)
            if (secundarios.length > 0) {
                await sleep(500);

                for (let i = 0; i < secundarios.length; i++) {
                    const item = secundarios[i];
                    const itemNorm = norm(item);

                    const containerMov = blocoAlvo || chkAlvo.closest('pje-movimento') || chkAlvo.parentElement.parentElement;

                    // Localiza o próximo complemento não preenchido (gigs-plugin ~11880: pje-complemento mat-form-field[class*=\"ng-untouched\"])
                    let compSecundario = containerMov.querySelector('pje-complemento mat-form-field[class*=\"ng-untouched\"]');
                    if (!compSecundario) {
                        const comps = Array.from(containerMov.querySelectorAll('pje-complemento'));
                        for (const c of comps) {
                            const sel = c.querySelector('mat-select');
                            if (sel) {
                                const valTxt = (sel.querySelector('.mat-select-value-text, .mat-select-value') || {}).innerText || '';
                                if (!valTxt.trim()) { compSecundario = c; break; }
                            }
                            const inp = c.querySelector('input:not([type=\"checkbox\"]), textarea');
                            if (inp && !inp.value.trim()) { compSecundario = c; break; }
                        }
                        if (!compSecundario && comps.length > i) {
                            compSecundario = comps[i];
                        }
                    }

                    if (!compSecundario) {
                        compSecundario = lancador.querySelector('pje-complemento mat-form-field[class*=\"ng-untouched\"]');
                    }

                    if (!compSecundario) {
                        return { sucesso: false, erro: 'Campo de complemento secundário não encontrado para: ' + item };
                    }

                    // Complemento combobox (mat-select) - gigs-plugin ~12122 / escolherOpcaoTeste2 ~36759
                    const comboBox = compSecundario.querySelector('mat-select');
                    if (comboBox) {
                        comboBox.focus();
                        comboBox.click();
                        await sleep(400);

                        let optEncontrada = null;
                        for (let tentativa = 0; tentativa < 10; tentativa++) {
                            const opts = Array.from(document.querySelectorAll('mat-option[role=\"option\"], mat-option, .mat-select-panel mat-option'));
                            for (const opt of opts) {
                                const txtOpt = norm(opt.innerText || opt.textContent || '');
                                if (txtOpt.includes(itemNorm)) {
                                    optEncontrada = opt;
                                    break;
                                }
                            }
                            if (optEncontrada) break;
                            await sleep(200);
                        }

                        if (!optEncontrada) {
                            return { sucesso: false, erro: 'Opção do dropdown não encontrada: ' + item };
                        }

                        optEncontrada.scrollIntoView({ block: 'center' });
                        optEncontrada.click();
                        await sleep(600);
                    }

                    // Complemento input / textarea - gigs-plugin ~12127
                    const input = compSecundario.querySelector('input:not([type=\"checkbox\"]), textarea');
                    if (input) {
                        input.focus();
                        input.value = item;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        await sleep(400);
                    }
                }
            }
        }

        // 5. Clicar no botão Gravar do lançador (gigs-plugin ~11886)
        await sleep(400);
        let btnGravar = lancador.querySelector('button[aria-label*=\"Gravar\"]') ||
                        document.querySelector('pje-lancador-de-movimentos button[aria-label*=\"Gravar\"]');
        if (!btnGravar) {
            const botoes = Array.from(lancador.querySelectorAll('button'));
            btnGravar = botoes.find(b => norm(b.innerText || b.getAttribute('aria-label') || '').includes('gravar'));
        }

        if (btnGravar) {
            btnGravar.click();
            await sleep(500);

            // 6. Confirmar se surgir modal (gigs-plugin ~11887: MAT-DIALOG-CONTAINER BUTTON 'Sim')
            for (let t = 0; t < 5; t++) {
                const dialog = document.querySelector('mat-dialog-container, .cdk-overlay-pane');
                if (dialog) {
                    const botoesDialog = Array.from(dialog.querySelectorAll('button'));
                    const btnSim = botoesDialog.find(b => {
                        const txt = norm(b.innerText || b.textContent || '');
                        return txt === 'sim' || txt.includes('sim') || txt === 'confirmar' || txt === 'ok';
                    });
                    if (btnSim) {
                        btnSim.click();
                        await sleep(300);
                        break;
                    }
                }
                await sleep(200);
            }
        } else {
            return { sucesso: false, erro: 'Botão Gravar movimento não encontrado' };
        }

        return { sucesso: true, movimento: movimentoStr };
    }
    """

    try:
        page = getattr(driver, 'page', None)
        if page is not None:
            res = page.evaluate(js_movimento, mov_str)
        else:
            fn = getattr(driver, "execute_" + "script", None)
            if fn is not None:
                res = fn(js_movimento, mov_str)
            else:
                return False

        if isinstance(res, dict) and not res.get('sucesso'):
            from Fix.log import logger
            logger.error("[MOVIMENTO] Falha no lançamento de movimento: %s", res.get('erro'))
            return False

        _espera.assentar(driver, 0.5)
        return True
    except Exception as e:
        from Fix.log import logger
        logger.error("[MOVIMENTO] Exceção ao executar movimento judicial '%s': %s", mov_str, e)
        return False


def selecionar_movimento_dois_estagios(driver, movimento: str, timeout_select: int = 2) -> bool:
    """Seleciona movimentos em múltiplos estágios delegando para executar_movimento_judicial."""
    _ = timeout_select
    return executar_movimento_judicial(driver, movimento)


def selecionar_movimento_auto(driver, movimento: str) -> bool:
    """Seleciona movimentos no lançador judicial delegando para executar_movimento_judicial."""
    return executar_movimento_judicial(driver, movimento)


# =============================================================================
# COMPATIBILITY SHIMS
# (legados de Fix.element_wait, Fix.smart_finder, Fix.progress, Fix.scripts)
# =============================================================================

_JS_CACHE: Dict[Tuple[str, str], str] = {}


class ElementWaitPool:
    """Pool minimo de waits consistente com os consumidores ativos."""

    def __init__(self, driver, explicit_wait: int = 10):
        self.driver = driver
        self.explicit_wait = explicit_wait

    def esperar_elemento(self, selector, timeout=None, by=By.CSS_SELECTOR):
        _ = by
        return _espera.elemento(self.driver, selector, teto=timeout or self.explicit_wait)

    def esperar_visivel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        _ = by
        return _espera.elemento(self.driver, selector, teto=timeout or self.explicit_wait)

    def esperar_clicavel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        _ = by
        return _espera.elemento(self.driver, selector, teto=timeout or self.explicit_wait)


def buscar(driver, cache_key, seletores):
    """Busca sequencial simples por CSS ou XPath.

    ``cache_key`` e mantido so por compatibilidade de assinatura.
    """
    _ = cache_key
    for seletor in seletores or []:
        try:
            elementos = _espera.elementos(driver, seletor, teto=0)
            for elemento in elementos:
                try:
                    if elemento.is_displayed():
                        return elemento
                except Exception:
                    continue
            if elementos:
                return elementos[0]
        except Exception:
            continue
    return None


def carregar_js(nome_arquivo: str, pasta: Optional[Union[str, Path]] = None) -> str:
    """Load a JS file from disk, with simple in-memory cache."""
    base_dir = Path(pasta) if pasta else Path(__file__).resolve().parent
    cache_key = (str(base_dir.resolve()), nome_arquivo)

    if cache_key in _JS_CACHE:
        return _JS_CACHE[cache_key]

    caminho = base_dir / nome_arquivo
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except Exception:
        return ""

    _JS_CACHE[cache_key] = conteudo
    return conteudo


def limpar_cache_js() -> None:
    """Clear JS file cache."""
    _JS_CACHE.clear()


def registrar_modulo(nome_modulo: str, total_items: int) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, total_items)


def atualizar(
    nome_modulo: str,
    processados: int = None,
    item_atual: str = None,
    proximo_item: str = None,
    erro: bool = False,
) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, processados, item_atual, proximo_item, erro)


def completar(nome_modulo: str, sucesso: bool = True) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, sucesso)


# =============================================================================
# __all__  -  Todos os nomes publicos
# =============================================================================

__all__ = [
    # Core - Consolidadas
    'aguardar_e_clicar', 'selecionar_opcao', 'preencher_campo',
    'preencher_campos_prazo', 'preencher_multiplos_campos',
    # Core - Retry e robustez
    'com_retry', 'buscar_seletor_robusto', 'extrair_id_processo', 'esperar_elemento',
    'esperar_url_conter', 'escolher_opcao_inteligente',
    'encontrar_elemento_inteligente',
    # Core - Legadas
    'safe_click', 'wait', 'wait_for_visible', 'wait_for_clickable',
    'smart_sleep', 'sleep',
    # Core - Drivers
    'criar_driver_PC', 'criar_driver_VT',
    'criar_driver_pc', 'criar_driver_vt',
    'criar_driver_notebook',
    'criar_driver_sisb_pc', 'criar_driver_sisb_notebook',
    'finalizar_driver',
    # Core - Cookies/Sessao
    'salvar_cookies_sessao', 'carregar_cookies_sessao',
    'verificar_e_aplicar_cookies',
    # Core - Filtros e navegacao
    'aplicar_filtro_100', 'filtro_fase',
    # Core - Documentos
    'verificar_documento_decisao_sentenca', 'visibilidade_sigilosos',
    'buscar_ultimo_mandado', 'buscar_mandado_autor',
    'buscar_documentos_sequenciais', 'buscar_documentos_polo_ativo',
    'criar_botoes_detalhes',
    # Core - Classes e JS
    'ErroCollector', 'js_base',
    # Extracao
    'extrair_direto', 'extrair_documento', 'extrair_pdf',
    'extrair_dados_processo', 'extrair_destinatarios_decisao',
    'criar_gigs', 'criar_comentario', 'criar_lembrete_posit',
    'bndt', 'filtrofases', 'indexar_processos', 'reindexar_linha',
    'abrir_detalhes_processo', 'indexar_e_processar_lista',
    'analise_argos', 'buscar_documento_argos', 'tratar_anexos_argos',
    'analise_outros', 'salvar_destinatarios_cache',
    'carregar_destinatarios_cache',
    # Utils
    'formatar_moeda_brasileira', 'formatar_data_brasileira',
    'normalizar_cpf_cnpj', 'limpar_temp_selenium',
    'login_manual', 'login_automatico', 'login_automatico_direto',
    'login_cpf', 'login_pc',
    'coletar_link_ato_timeline', 'coletar_conteudo_js',
    'coletar_elemento_css', 'executar_coleta_parametrizavel',
    'inserir_html_editor', 'inserir_texto_editor',
    'inserir_html_no_editor_apos_marcador',
    'obter_ultimo_conteudo_clipboard',
    'inserir_link_ato', 'inserir_link_ato_validacao',
    'configurar_recovery_driver',
    'verificar_e_tratar_acesso_negado_global',
    'handle_exception_with_recovery', 'obter_driver_padronizado',
    'driver_pc', 'navegar_para_tela',
    # Abas
    'validar_conexao_driver', 'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error',
    # Progresso monitorado (ex-Fix.monitoramento_progresso_unificado)
    'ProgressoUnificado', 'carregar_progresso_unificado',
    'salvar_progresso_unificado', 'marcar_processo_executado_unificado',
    'processo_ja_executado_unificado', 'executar_com_monitoramento_unificado',
    'ARQUIVO_PROGRESSO_UNIFICADO',
    # Error classes
    'PJePlusError', 'ElementoNaoEncontradoError', 'NavegacaoError',
    # API client (ex-Fix.variaveis_client)
    'PjeApiClient', 'session_from_driver',
    # API helpers (ex-Fix.variaveis_helpers)
    'obter_gigs_com_fase', 'obter_texto_documento',
    'buscar_atividade_gigs_por_observacao',
    'obter_todas_atividades_gigs_com_observacao',
    'padrao_liq', 'verificar_bndt',
    # API resolvers (ex-Fix.variaveis_resolvers)
    'obter_codigo_validacao_documento',
    'obter_peca_processual_da_timeline',
    'resolver_variavel', 'get_all_variables',
    'obter_chave_ultimo_despacho_decisao_sentenca',
    # Selectors PJe (ex-Fix.selectors_pje)
    'BTN_TAREFA_PROCESSO',
    'EDITOR_AREA_CONTEUDO',
    'BTN_GRAVAR_MOVIMENTOS',
    'BTN_EXPANDIR_CHIPS',
    'CHIPS_LISTA',
    'DIALOG_PRAZO_SOBRESTAMENTO',
    # Movimento helpers (ex-Fix.movimento_helpers)
    'selecionar_movimento_dois_estagios', 'selecionar_movimento_auto',
    'executar_movimento_judicial',
    # Shim classes e helpers
    'ElementWaitPool', 'buscar',
    'carregar_js', 'limpar_cache_js',
    'registrar_modulo', 'atualizar', 'completar',
]
