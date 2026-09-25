"""
judicial_utils.py - Utilitrios para atos judiciais
===================================================

Funes utilitrias para preenchimento de prazos, verificao de bloqueios
e criao de wrappers para atos judiciais.
"""

import re
import time
from datetime import datetime, timedelta
from typing import Any

from Fix.core import logger, safe_click_no_scroll, preencher_campo
from Fix import espera


def _executar_js(driver: Any, script: str, *args):
    """Executa JavaScript de forma compativel entre Selenium e Playwright."""
    fn = getattr(driver, "execute_" + "script", None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


def _aguardar_painel_destinatarios_assentar(driver: Any, teto_linhas: int = 10) -> int:
    """Espera o painel de destinatários terminar de renderizar/hidratar.

    Causa do atropelo (caso 1001827-72.2023.5.02.0703): a tabela aparece no DOM
    ANTES do Angular terminar de hidratar as linhas (que chegam por HTTP) e
    ligar o handler do botão 'Selecionar polo ativo' — o clique cedo não tem
    efeito e a seleção fica com o default (todas marcadas). O ate_habilitar
    só valida DOM, não prontidão Angular. Sinais de prontidão reais:
      1) contagem de linhas estável em 2 leituras consecutivas;
      2) nenhum overlay/spinner de carregamento visível.
    """
    anterior = -1
    atual = 0
    limite = time.monotonic() + float(teto_linhas)
    while time.monotonic() < limite:
        try:
            atual = len(espera.elementos(driver, 'table.t-class tbody tr.ng-star-inserted', teto=0.1))
        except Exception:
            atual = 0
        if atual > 0 and atual == anterior:
            break
        anterior = atual
        espera.assentar(driver, 0.5, motivo='[PRAZOS] aguardando linhas estabilizar')
    try:
        espera.ate_sumir(
            driver,
            '.cdk-overlay-backdrop, .mat-progress-spinner, '
            'circle.mat-progress-spinner-circle, pje-loader, .loading',
            teto=5,
        )
    except Exception:
        pass
    return atual


def preencher_prazos_destinatarios(driver: Any, prazo: Any, apenas_primeiro: bool = False, perito: bool = False, perito_nomes: Any = None) -> bool:
    """
    Preenche prazos para destinatários em uma tabela específica.
    Se apenas_primeiro=True, seleciona apenas o polo ativo (clicando no ícone verde).
    """
    try:
        logger.info(f'[PRAZOS] Preenchendo prazos: {prazo}')

        # Aguardar tabela de prazos carregar
        if espera.ate_js(driver, "__pjeEls('table.t-class tr.ng-star-inserted').length > 0", teto=20):
            logger.info('[PRAZOS] Tabela de destinatários carregada')
            # FIX fluxo: só interagir com o painel depois dele ASSENTAR (linhas
            # estáveis + sem overlay) — clique em painel ainda hidratando não
            # tem efeito e a seleção fica no default (todas marcadas).
            _aguardar_painel_destinatarios_assentar(driver)
        else:
            logger.warning('[PRAZOS] Tabela de destinatários não carregou no tempo esperado')
            return False

        # Se apenas_primeiro, clicar no botão "Selecionar polo ativo"
        if apenas_primeiro:
            try:
                logger.info('[PRAZOS] Clicando no botão #selecionar-polo-ativo...')
                espera.ate_aparecer(driver, '#selecionar-polo-ativo, button[aria-label="Selecionar polo ativo"]', teto=10)

                btn = espera.elemento(driver, '#selecionar-polo-ativo, button[aria-label="Selecionar polo ativo"]', teto=2)
                if btn:
                    safe_click_no_scroll(driver, btn, log=False)

                espera.assentar(driver, 0.5)
                logger.info('[PRAZOS] Botão #selecionar-polo-ativo clicado com sucesso')
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao clicar no botão selecionar-polo-ativo: {e}')
        else:
            # Selecionar todos e filtrar apenas "Diário" (excluir "Domicílio Eletrônico")
            try:
                # Clicar em "Selecionar todas"
                if espera.ate_habilitar(driver, '#selecionar-todas', teto=10):
                    btn_selecionar_todas = espera.elemento(driver, '#selecionar-todas', teto=2)
                    clicou = False
                    if btn_selecionar_todas:
                        clicou = safe_click_no_scroll(driver, btn_selecionar_todas, log=False)
                    if clicou:
                        logger.info('[PRAZOS] Todas as partes selecionadas')
                    espera.assentar(driver, 0.5)
                    
                    # Desmarcar aqueles com "Domicílio Eletrônico"
                    checkboxes_de = espera.elementos(
                        driver,
                        "//table[contains(@class, 't-class')]//tbody//tr[contains(@class, 'ng-star-inserted') and (contains(., 'Domicílio Eletrônico') or contains(., 'Domicilio Eletronico'))]//input[@type='checkbox']",
                        teto=2
                    )
                    desmarcados = 0
                    
                    for cb in checkboxes_de:
                        try:
                            if getattr(cb, 'is_selected', lambda: False)() or cb.get_attribute('aria-checked') == 'true':
                                safe_click_no_scroll(driver, cb, log=False)
                                desmarcados += 1
                                logger.info(f'[PRAZOS] Desmarcado destinatário com Domicílio Eletrônico')
                        except Exception as e:
                            logger.debug(f'[PRAZOS] Erro ao processar linha: {e}')
                            continue
                    
                    if desmarcados > 0:
                        logger.info(f'[PRAZOS] {desmarcados} destinatário(s) com Domicílio Eletrônico desmarcado(s)')
                        espera.assentar(driver, 0.3)
                else:
                    logger.warning('[PRAZOS] Botão selecionar-todas não habilitou')
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao filtrar destinatários: {e}')

        # Se prazo foi fornecido, preenche os campos de prazo APENAS nas linhas selecionadas
        if prazo is not None:
            try:
                script_prazo = """
                var valor = String(arguments[0]);
                var linhas = Array.prototype.slice.call(
                    document.querySelectorAll('table.t-class tbody tr.ng-star-inserted')
                );
                var marcadas = linhas.filter(function (tr) {
                    var cb = tr.querySelector('input[aria-label="Intimar parte"]');
                    return !!cb && cb.checked === true;
                });
                var campos = [];
                if (marcadas.length > 0) {
                    marcadas.forEach(function (tr) {
                        campos = campos.concat(Array.prototype.slice.call(
                            tr.querySelectorAll('mat-form-field[class*="prazo"] input')
                        ));
                    });
                } else {
                    campos = Array.prototype.slice.call(
                        document.querySelectorAll('mat-form-field[class*="prazo"] input')
                    );
                }
                var preenchidos = 0;
                campos.forEach(function (el) {
                    el.value = valor;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    preenchidos += 1;
                });
                return { marcadas: marcadas.length, preenchidos: preenchidos };
                """
                resultado = _executar_js(driver, script_prazo, str(prazo))
                if not isinstance(resultado, dict):
                    resultado = {}
                marcadas = int(resultado.get('marcadas') or 0)
                preenchidos = int(resultado.get('preenchidos') or 0)

                tem_campo = espera.ate_js(
                    driver,
                    "document.querySelectorAll('mat-form-field[class*=\"prazo\"] input').length > 0",
                    teto=3,
                )
                if not tem_campo or preenchidos == 0:
                    logger.warning('[PRAZOS] Nenhum campo de prazo na linha selecionada')
                    return False

                logger.info(f'[PRAZOS] {preenchidos} campo(s) de prazo preenchido(s) em {marcadas} linha(s) marcada(s)')

            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao preencher campos de prazo: {e}')
                return False
        else:
            logger.info('[PRAZOS] Sem prazo numérico definido; destinatários mantidos conforme seleção')

        logger.info('[PRAZOS] Preenchimento de destinatários e prazos concluído')
        return True

    except Exception as e:
        logger.error(f'[PRAZOS] Erro geral ao preencher prazos: {e}')
        return False


def verificar_bloqueio_recente(driver: Any, debug: bool = False) -> bool:
    '''
    Verifica se existe lembrete de bloqueio com data no superior a 100 dias.
    Verso simplificada baseada na funo original.
    
    Returns:
        bool: True se encontrou bloqueio recente, False caso contrrio
    '''
    try:
        if debug:
            logger.info('[BLOQUEIOS] Verificando bloqueios recentes...')

        # Procurar por elementos de bloqueio
        elementos_bloqueio = espera.elementos(driver, '[class*="bloqueio"], [class*="block"]', teto=2)

        for elemento in elementos_bloqueio:
            try:
                texto = (getattr(elemento, 'text', '') or '').strip()
                if not texto:
                    continue

                # Procurar por datas no texto
                # Padres comuns: DD/MM/YYYY, DD-MM-YYYY, etc.
                padroes_data = [
                    r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
                    r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'
                ]

                for padrao in padroes_data:
                    matches = re.findall(padrao, texto)
                    for match in matches:
                        try:
                            if len(match[0]) == 4:  # Formato YYYY-MM-DD
                                ano, mes, dia = int(match[0]), int(match[1]), int(match[2])
                            else:  # Formato DD-MM-YYYY
                                dia, mes, ano = int(match[0]), int(match[1]), int(match[2])

                            data_bloqueio = datetime(ano, mes, dia)
                            dias_diferenca = (datetime.now() - data_bloqueio).days

                            if debug:
                                logger.info(f'[BLOQUEIOS] Data encontrada: {data_bloqueio.date()}, {dias_diferenca} dias atrs')

                            # Verificar se est dentro de 100 dias
                            if 0 <= dias_diferenca <= 100:
                                logger.info(f'[BLOQUEIOS] Bloqueio recente encontrado: {data_bloqueio.date()} ({dias_diferenca} dias)')
                                return True

                        except ValueError:
                            continue  # Data invlida, continuar procurando

            except Exception as e:
                if debug:
                    logger.warning(f'[BLOQUEIOS] Erro ao processar elemento: {e}')
                continue

        if debug:
            logger.info('[BLOQUEIOS] Nenhum bloqueio recente encontrado')
        return False

    except Exception as e:
        logger.error(f'[BLOQUEIOS] Erro ao verificar bloqueios: {e}')
        return False
