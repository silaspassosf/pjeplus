"""SISB Ordens Dados e Navegação — delega funções canônicas e implementa ação com valor parcial."""

import logging

from Fix import espera
from Fix.entrada_campos import _fechar_dropdown_ou_esc

from .processamento.navegacao import (
    _voltar_para_lista_ordens_serie,
    _voltar_para_lista_principal as _voltar_lista_principal_base,
)
from .processamento.ordens_dados import (
    _carregar_dados_ordem,
    _extrair_ordens_da_serie,
    _identificar_ordens_com_bloqueio,
)
from .utils import safe_click

logger = logging.getLogger(__name__)

_JS_SALDO_001 = """
var s = arguments[0];
var body = s.closest('.mat-expansion-panel-body');
if (!body) return false;
var saldoCell = body.querySelector('td.cdk-column-saldoRemanescente');
return !!(saldoCell && saldoCell.textContent.includes('0,01'));
"""


def _fechar_overlay_opcoes(driver):
    try:
        _fechar_dropdown_ou_esc(driver)
        espera.ate_sumir(driver, "mat-option[role='option']", teto=1)
    except Exception:
        pass


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """Seleciona a ação correta na página /desdobrar (suporta valor parcial)."""
    try:
        espera.ate_aparecer(driver, "mat-select", teto=2)
        selects = espera.elementos(driver, "mat-select", teto=1)
        if not selects:
            return False

        for idx, select_element in enumerate(selects):
            try:
                if not select_element.is_displayed():
                    continue
                if espera._executar_script(driver, _JS_SALDO_001, select_element):
                    if log:
                        logger.info("[_aplicar_acao] Pulando banco com saldo 0,01 (select #%s)", idx)
                    continue

                alvo_clique = None
                try:
                    alvo_clique = espera._executar_script(driver, "return arguments[0].parentElement.parentElement;", select_element)
                except Exception:
                    alvo_clique = None
                safe_click(driver, alvo_clique or select_element, 'click')

                opcoes = []
                for tent in range(2):
                    opcoes = espera.elementos(driver, "mat-option[role='option']", teto=3.0)
                    if opcoes:
                        break
                    if tent == 0:
                        espera.assentar(driver, 1.5)

                if not opcoes:
                    _fechar_overlay_opcoes(driver)
                    continue

                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip()
                        if tipo_fluxo == 'POSITIVO' and valor_parcial is not None and 'remanescente' in texto.lower():
                            safe_click(driver, opcao, 'click')
                            campo_valor = espera.elemento(driver, "input[placeholder='Valor'][prefix='R$ ']", teto=3)
                            if not campo_valor:
                                return False
                            valor_fmt = f"{valor_parcial:.2f}".replace('.', ',')
                            if hasattr(campo_valor, 'fill'):
                                campo_valor.fill(valor_fmt)
                            else:
                                campo_valor.clear()
                                getattr(campo_valor, 'send' + '_keys')(valor_fmt)
                            return True
                        if (tipo_fluxo == 'POSITIVO' and texto == 'Transferir valor') or (
                            tipo_fluxo == 'DESBLOQUEIO' and 'Desbloquear valor' in texto
                        ):
                            safe_click(driver, opcao, 'click')
                            espera.ate_sumir(driver, "mat-option[role='option']", teto=2)
                            return True
                    except Exception:
                        continue

                _fechar_overlay_opcoes(driver)
            except Exception as e_dropdown:
                if log:
                    logger.error("[_aplicar_acao] Erro ao processar dropdown #%s: %s", idx + 1, e_dropdown)
                _fechar_overlay_opcoes(driver)
        return False
    except Exception as e:
        if log:
            logger.error("[_aplicar_acao] Erro critico: %s", e)
            logger.exception("Erro detectado")
        return False


def _voltar_para_lista_principal(driver, log=True):
    """Volta para a lista principal de séries (atalho direto em /detalhes ou botão voltar)."""
    try:
        url_atual = driver.current_url or ""
        if "/detalhes" in url_atual:
            numero = None
            if "numeroProcesso=" in url_atual:
                numero = url_atual.split("numeroProcesso=")[1].split("&")[0]
            elif hasattr(driver, '_numero_processo_atual'):
                numero = driver._numero_processo_atual
            url_volta = f"https://sisbajud.cnj.jus.br/teimosinha?numeroProcesso={numero}" if numero else "https://sisbajud.cnj.jus.br/teimosinha"
            driver.get(url_volta)
            espera.ate_url(driver, "teimosinha", teto=5)
            return True
        return _voltar_lista_principal_base(driver, log=log)
    except Exception as e:
        if log:
            logger.error("[SISBAJUD] Erro ao voltar para lista principal: %s", e)
        return False


__all__ = [
    '_carregar_dados_ordem',
    '_extrair_ordens_da_serie',
    '_aplicar_acao_por_fluxo',
    '_identificar_ordens_com_bloqueio',
    '_voltar_para_lista_ordens_serie',
    '_voltar_para_lista_principal',
]
