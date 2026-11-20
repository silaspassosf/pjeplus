"""SISB Séries — navegação para série, dispensa de dialog e extração de ordens/executado."""

import logging
import time
import urllib.parse

from Fix import espera
from Fix.core import safe_click_no_scroll, wait_for_page_load

logger = logging.getLogger(__name__)


def dispensar_dialog_ordem_pendente(driver, log=True, timeout: float = 0.0):
    """Fecha o dialog 'Ordens de bloqueio sem desdobramento após 5 dias' clicando em 'Não'."""
    js = """
    const dialogs = document.querySelectorAll('sisbajud-dialog-aviso-ordem-pendente, mat-dialog-container, .mat-dialog-container, [role="dialog"]');
    for (const d of dialogs) {
        const btnNao = Array.from(d.querySelectorAll('button')).find(b => {
            const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
            return txt === 'não' || txt === 'nao' || txt.includes('não') || txt.includes('nao');
        });
        if (btnNao) { btnNao.click(); return true; }
    }
    return false;
    """
    inicio = time.time()
    while True:
        try:
            if espera._executar_script(driver, js):
                if log:
                    logger.info('[SISBAJUD] Dialog de ordens pendentes dispensado (clicou "Não")')
                espera.assentar(driver, 0.3)
                return True
        except Exception:
            pass
        if timeout <= 0 or (time.time() - inicio) >= timeout:
            break
        espera.pausa(driver, 0.3)
    return False


def _navegar_e_extrair_ordens_serie(driver, serie, log=True):
    """Navega para uma série específica e extrai suas ordens."""
    try:
        id_serie = serie.get('id_serie')
        if not id_serie:
            return []
        if log:
            logger.info("[SISBAJUD] Navegando para detalhes da serie %s via menu", id_serie)

        linha_index = serie.get('linha_index')
        if linha_index is None:
            if log:
                logger.info("[SISBAJUD] Falha ao abrir serie: linha_index ausente")
            return []

        tabela = espera.elemento(driver, "table.mat-table", teto=10)
        linhas = espera.elementos(tabela, "tbody tr.mat-row, tbody tr[mat-row]", teto=1) if tabela else []
        if linha_index >= len(linhas):
            if log:
                logger.info("[SISBAJUD] Indice %s fora de escopo (%s linhas)", linha_index, len(linhas))
            return []

        linha_el = linhas[linha_index]
        espera._executar_script(driver, "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", linha_el)
        espera.assentar(driver, 0.5)

        aberto = False
        btn_menu = espera.elemento(linha_el, "button.mat-menu-trigger.mat-icon-button", teto=0.5)
        if btn_menu:
            try:
                espera._executar_script(driver, "arguments[0].click();", btn_menu)
                espera.assentar(driver, 0.8)
                itens_menu = espera.elementos(driver, "button[role='menuitem'].mat-menu-item", teto=1)
                alvo = next(
                    (it for it in itens_menu if 'detalh' in (it.text or '').strip().lower()),
                    itens_menu[0] if itens_menu else None,
                )
                if alvo:
                    espera._executar_script(driver, "arguments[0].click();", alvo)
                    aberto = True
            except Exception:
                pass

        if not aberto:
            btn_det = espera.elemento(linha_el, "button.mat-icon-button", teto=0.3)
            if btn_det:
                try:
                    safe_click_no_scroll(driver, btn_det)
                    aberto = True
                except Exception:
                    pass

        if not aberto:
            td = espera.elemento(linha_el, "td", teto=0.3)
            if td:
                try:
                    espera._executar_script(driver, "arguments[0].click();", td)
                    aberto = True
                except Exception:
                    pass

        if not aberto:
            if log:
                logger.info("[SISBAJUD] Nao foi possivel abrir a serie %s", id_serie)
            return []

        try:
            wait_for_page_load(driver, timeout=6)
        except Exception:
            espera.assentar(driver, 1)

        from .ordens_dados import _extrair_ordens_da_serie
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            logger.info("[SISBAJUD] %s ordens extraidas da serie %s", len(ordens), id_serie)
        return ordens
    except Exception as e:
        if log:
            logger.info("[SISBAJUD] Erro na navegacao para serie %s: %s", serie.get('id_serie', 'unknown'), e)
        return []


def _extrair_nome_executado_serie(driver, log=True):
    """Extrai o nome do executado na página de detalhes da série."""
    try:
        el = espera.elemento(driver, "mat-expansion-panel-header .col-reu-dados-nome-pessoa", teto=0.5)
        if el and el.text.strip():
            return el.text.strip()

        hdr = espera.elemento(driver, "div.header-title, .mat-card-title, h1, h2", teto=0.3)
        if hdr and "-" in hdr.text:
            nome = hdr.text.split("-")[-1].strip()
            if len(nome) > 3:
                return nome

        for card in espera.elementos(driver, "mat-card-title, .card-title, .reu-nome", teto=0.3):
            text = card.text.strip()
            if len(text) > 3 and all(p not in text for p in ("Executado", "Ordem", "Serie")):
                return text

        for label in espera.elementos(driver, "//*[contains(text(), 'Reu') or contains(text(), 'Executado')]/following-sibling::*[1]", teto=0.3):
            text = label.text.strip()
            if len(text) > 3:
                return text

        url = driver.current_url or ""
        if "nome=" in url.lower():
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if 'nome' in params:
                return params['nome'][0]

        return "Executado"
    except Exception as e:
        if log:
            logger.info("[SISBAJUD] Erro ao extrair nome do executado: %s", e)
        return "Executado"
