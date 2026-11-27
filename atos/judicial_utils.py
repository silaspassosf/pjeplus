"""judicial_utils.py - Utilitrios para atos judiciais"""

import re
import time
from datetime import datetime, timedelta
from typing import Any

from Fix.core import logger, safe_click_no_scroll, preencher_campo
from Fix import espera
from Fix.core import _executar_js

def _aguardar_painel_destinatarios_assentar(driver: Any, teto_linhas: int = 10) -> int:
    """Espera o painel de destinatários terminar de renderizar/hidratar."""
    anterior = -1
    atual = 0
    inicio = time.monotonic()
    limite = inicio + float(teto_linhas)
    while time.monotonic() < limite:
        try:
            atual = len(espera.elementos(driver, 'table.t-class tbody tr.ng-star-inserted', teto=0.1))
        except Exception:
            atual = 0
        if atual > 0 and atual == anterior:
            break
        anterior = atual
        espera.assentar(driver, 0.2, motivo='[PRAZOS] aguardando linhas estabilizar')
    try:
        espera.ate_sumir(
            driver,
            '.cdk-overlay-backdrop, .mat-progress-spinner, '
            'circle.mat-progress-spinner-circle, pje-loader, .loading',
            teto=5,
        )
    except Exception:
        pass
    logger.info('[PRAZOS] painel assentou em %.2fs (%d linha(s))', time.monotonic() - inicio, atual)
    return atual


_SEL_POLO_ATIVO = ('#selecionar-polo-ativo, button[aria-label="Selecionar polo ativo"]')

_JS_CLICAR_POLO_ATIVO = """
    const btn = document.getElementById('selecionar-polo-ativo')
        || document.querySelector('#selecionar-polo-ativo')
        || document.querySelector('button[aria-label="Selecionar polo ativo"]');
    if (!btn) return false;
    btn.click();
    return true;
"""

_JS_ALGUMA_LINHA_MARCADA = (
    "__pjeEls('table.t-class tbody tr.ng-star-inserted input[aria-label=\"Intimar parte\"]')"
    ".some(cb => !!cb.checked)"
)


def _clicar_polo_ativo(driver: Any, tentativas: int = 2) -> bool:
    """Clica em "Selecionar polo ativo" e confirma que alguma linha foi marcada."""
    try:
        espera.ate_aparecer(driver, _SEL_POLO_ATIVO, teto=10)
    except Exception:
        pass

    for tentativa in range(1, tentativas + 1):
        logger.info('[PRAZOS] Clicando no botão #selecionar-polo-ativo (tentativa %d/%d)...',
                    tentativa, tentativas)
        clicado = False
        try:
            clicado = bool(_executar_js(driver, _JS_CLICAR_POLO_ATIVO))
        except Exception as e:
            logger.warning('[PRAZOS] JS de clique no polo ativo falhou: %s', e)

        if not clicado:
            btn = None
            try:
                btn = espera.elemento(driver, _SEL_POLO_ATIVO, teto=2, visivel=False)
            except Exception:
                btn = None
            if btn is not None:
                clicado = bool(safe_click_no_scroll(driver, btn, log=False))

        if not clicado:
            logger.warning('[PRAZOS] Botão #selecionar-polo-ativo não encontrado (tentativa %d/%d)',
                           tentativa, tentativas)
            continue

        if espera.ate_js(driver, _JS_ALGUMA_LINHA_MARCADA, teto=3):
            logger.info('[PRAZOS] Polo ativo selecionado (linha marcada)')
            espera.assentar(driver, 0.3)
            return True

        logger.warning('[PRAZOS] Clique efetuado mas nenhuma linha foi marcada (tentativa %d/%d)',
                       tentativa, tentativas)
        espera.assentar(driver, 0.4)

    return False


def _selecionar_destinatarios_alvo(driver: Any, destinatarios_alvo: Any) -> bool:
    """Seleciona na tabela de intimações apenas os destinatários-alvo (ex.: parte com Domicílio Eletrônico)."""
    alvos = []
    if isinstance(destinatarios_alvo, str):
        destinatarios_alvo = [destinatarios_alvo]
    for item in (destinatarios_alvo or []):
        nome = ''
        if isinstance(item, dict):
            nome = (item.get('parte') or item.get('nome') or '').strip()
        else:
            nome = str(item or '').strip()
        if nome and nome not in alvos:
            alvos.append(nome)

    if not alvos:
        logger.warning('[PRAZOS][ALVO] Nenhum destinatário-alvo informado para seleção')
        return False

    js_selecionar = """
    var alvosBrutos = arguments[0] || [];
    function norm(s) {
        return String(s || '')
            .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
            .toUpperCase()
            .replace(/[^A-Z0-9\\s]/g, ' ')
            .replace(/\\s+/g, ' ')
            .trim();
    }
    var alvos = alvosBrutos.map(norm).filter(Boolean);
    var linhas = Array.prototype.slice.call(
        document.querySelectorAll('table.t-class tbody tr.ng-star-inserted')
    );
    var selecionadas = [];
    var desabilitadas = [];
    var encontradas = [];
    var todasLinhas = [];
    linhas.forEach(function (tr) {
        var txtBruto = (tr.innerText || tr.textContent || '').replace(/\\s+/g, ' ').trim();
        var txt = norm(txtBruto);
        todasLinhas.push(txtBruto.slice(0, 120));
        var cb = tr.querySelector('input[aria-label="Intimar parte"]') || tr.querySelector('input[type="checkbox"]');
        var bateAlvo = alvos.some(function (a) {
            return a && txt.indexOf(a) !== -1;
        });
        if (bateAlvo) {
            encontradas.push(txtBruto.slice(0, 120));
            if (cb) {
                var desab = !!cb.disabled || cb.getAttribute('aria-disabled') === 'true';
                if (desab) {
                    desabilitadas.push(txtBruto.slice(0, 120));
                } else {
                    if (!cb.checked) {
                        cb.click();
                    }
                    if (cb.checked) {
                        selecionadas.push(txtBruto.slice(0, 120));
                    }
                }
            }
        } else if (cb && cb.checked && !cb.disabled) {
            cb.click();
        }
    });
    return {
        selecionadas: selecionadas,
        desabilitadas: desabilitadas,
        encontradas: encontradas,
        totalLinhas: linhas.length,
        todasLinhas: todasLinhas
    };
    """
    res = _executar_js(driver, js_selecionar, alvos)
    if not isinstance(res, dict):
        logger.warning('[PRAZOS][ALVO] Retorno inesperado ao selecionar alvos: %r', res)
        return False

    selecionadas = res.get('selecionadas') or []
    desabilitadas = res.get('desabilitadas') or []
    encontradas = res.get('encontradas') or []
    logger.info(
        '[PRAZOS][ALVO] alvos=%s | encontradas=%d | selecionadas=%d | desabilitadas=%d',
        alvos, len(encontradas), len(selecionadas), len(desabilitadas)
    )
    if not selecionadas:
        logger.warning(
            '[PRAZOS][ALVO] Nenhuma linha selecionada. Linhas na tabela: %s',
            res.get('todasLinhas') or []
        )
        return False
    espera.assentar(driver, 0.3)
    return True


def aguardar_pos_clique_assinar(
    driver: Any,
    contexto: str = 'ATO',
    seletor_assinar: str = 'button#assinar',
    teto_sem_dialog: int = 25,
    teto_com_dialog: int = 180,
) -> bool:
    """Aguarda confirmação da assinatura (snackbar, fechamento de diálogo móvel/PJeOffice ou saída da minuta)."""
    _js_check = """
    var selAssinar = arguments[0];
    var snacks = Array.prototype.slice.call(
        document.querySelectorAll('simple-snack-bar, snack-bar-container')
    );
    var snackTxt = '';
    for (var i = 0; i < snacks.length; i++) {
        var t = (snacks[i].innerText || snacks[i].textContent || '').trim();
        if (t) { snackTxt = t; break; }
    }
    var low = snackTxt.toLowerCase();
    var dialog = document.querySelector('mat-dialog-container');
    var otp = document.querySelector('input.codigo-otp');
    var spinner = document.querySelector('mat-progress-spinner, .mat-progress-spinner, pje-loader');
    var btn = selAssinar ? document.querySelector(selAssinar) : null;
    var url = String(window.location.href || '');
    return {
        snack: snackTxt,
        erro: low.includes('erro') || low.includes('falha') || low.includes('cancelad'),
        sucesso: low.includes('assinad') || low.includes('juntad') || low.includes('sucesso'),
        dialog: !!dialog,
        otp: !!otp,
        spinner: !!spinner,
        btnPresente: !!btn,
        btnDesabilitado: !!(btn && (btn.disabled || btn.getAttribute('aria-disabled') === 'true')),
        url: url
    };
    """

    url_inicial = ''
    try:
        url_inicial = str(getattr(driver, 'current_url', '') or '')
    except Exception:
        url_inicial = ''

    teve_dialog = False
    try:
        teve_dialog = bool(espera.ate_aparecer(driver, 'mat-dialog-container, input.codigo-otp', teto=3))
    except Exception:
        teve_dialog = False

    if teve_dialog:
        logger.info('[%s][ASSINAR] Diálogo de assinatura/validação detectado — aguardando conclusão...', contexto)
        limite_dialog = time.monotonic() + float(teto_com_dialog)
        dialog_fechou = False
        while time.monotonic() < limite_dialog:
            st = _executar_js(driver, _js_check, seletor_assinar) or {}
            if not st.get('dialog'):
                dialog_fechou = True
                break
            espera.pausa(driver, 0.5, motivo=f'[{contexto}] aguardando dialogo de assinatura fechar')
        if not dialog_fechou:
            logger.error('[%s][ASSINAR][ERRO] Timeout de %ss aguardando diálogo de assinatura fechar',
                         contexto, teto_com_dialog)
            return False
        try:
            from Fix.sessao import salvar_cookies_sessao
            salvar_cookies_sessao(driver, info_extra='apos_assinatura')
        except Exception:
            pass

    limite = time.monotonic() + float(teto_sem_dialog)
    while time.monotonic() < limite:
        st = _executar_js(driver, _js_check, seletor_assinar) or {}
        if st.get('erro'):
            logger.error('[%s][ASSINAR][ERRO] Assinatura rejeitada: "%s"', contexto, st.get('snack'))
            return False
        if st.get('sucesso') and not st.get('spinner') and not st.get('dialog'):
            logger.info('[%s][ASSINAR] Assinatura confirmada via snackbar: "%s"', contexto, st.get('snack'))
            try:
                from Fix.sessao import salvar_cookies_sessao
                salvar_cookies_sessao(driver, info_extra='apos_assinatura')
            except Exception:
                pass
            return True
        url_atual = st.get('url') or ''
        if url_inicial and url_atual and url_atual != url_inicial and '/minutar' not in url_atual and '/anexar' not in url_atual and not st.get('spinner') and not st.get('dialog'):
            logger.info('[%s][ASSINAR] Assinatura/envio confirmado via transição de rota (%s)', contexto, url_atual)
            try:
                from Fix.sessao import salvar_cookies_sessao
                salvar_cookies_sessao(driver, info_extra='apos_assinatura')
            except Exception:
                pass
            return True
        if not st.get('btnPresente') and not st.get('dialog') and not st.get('spinner'):
            logger.info('[%s][ASSINAR] Botão de assinatura ausente pós-clique e sem spinner (tela atualizada)', contexto)
            try:
                from Fix.sessao import salvar_cookies_sessao
                salvar_cookies_sessao(driver, info_extra='apos_assinatura')
            except Exception:
                pass
            return True
        espera.pausa(driver, 0.5, motivo=f'[{contexto}] aguardando confirmação de assinatura')

    logger.warning('[%s][ASSINAR][WARN] Confirmação explícita de assinatura não detectada em %ss — verificando estado final',
                   contexto, teto_sem_dialog)
    st_final = _executar_js(driver, _js_check, seletor_assinar) or {}
    return not st_final.get('erro') and not st_final.get('dialog')


def preencher_prazos_destinatarios(driver: Any, prazo: Any, apenas_primeiro: bool = False, perito: bool = False, perito_nomes: Any = None, destinatario: Any = None, destinatarios_alvo: Any = None) -> bool:
    """Preenche prazos para destinatários em uma tabela específica."""
    try:
        logger.info(f'[PRAZOS] Preenchendo prazos: {prazo}')

        if espera.ate_js(driver, "__pjeEls('table.t-class tr.ng-star-inserted').length > 0", teto=20):
            logger.info('[PRAZOS] Tabela de destinatários carregada')
            _aguardar_painel_destinatarios_assentar(driver)
        else:
            logger.warning('[PRAZOS] Tabela de destinatários não carregou no tempo esperado')
            return False

        destinatario_norm = str(destinatario or '').strip().lower()
        if destinatario_norm == 'alvo':
            if not _selecionar_destinatarios_alvo(driver, destinatarios_alvo):
                return False
        elif apenas_primeiro:
            if not _clicar_polo_ativo(driver):
                logger.warning('[PRAZOS] Clique em #selecionar-polo-ativo não marcou nenhuma linha '
                               '— seguindo sem seleção de polo')
        else:
            try:
                t0_selecionar = time.monotonic()
                if espera.ate_habilitar(driver, '#selecionar-todas', teto=10):
                    logger.info('[PRAZOS] #selecionar-todas habilitado em %.2fs', time.monotonic() - t0_selecionar)
                    btn_selecionar_todas = espera.elemento(driver, '#selecionar-todas', teto=2)
                    clicou = False
                    if btn_selecionar_todas:
                        clicou = safe_click_no_scroll(driver, btn_selecionar_todas, log=False)
                    if clicou:
                        logger.info('[PRAZOS] Todas as partes selecionadas')
                    espera.assentar(driver, 0.5)

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
    """Verifica se existe lembrete de bloqueio com data no superior a 100 dias."""
    try:
        if debug:
            logger.info('[BLOQUEIOS] Verificando bloqueios recentes...')

        elementos_bloqueio = espera.elementos(driver, '[class*="bloqueio"], [class*="block"]', teto=2)

        for elemento in elementos_bloqueio:
            try:
                texto = (getattr(elemento, 'text', '') or '').strip()
                if not texto:
                    continue

                padroes_data = [
                    r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
                    r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'
                ]

                for padrao in padroes_data:
                    matches = re.findall(padrao, texto)
                    for match in matches:
                        try:
                            if len(match[0]) == 4:
                                ano, mes, dia = int(match[0]), int(match[1]), int(match[2])
                            else:
                                dia, mes, ano = int(match[0]), int(match[1]), int(match[2])

                            data_bloqueio = datetime(ano, mes, dia)
                            dias_diferenca = (datetime.now() - data_bloqueio).days

                            if debug:
                                logger.info(f'[BLOQUEIOS] Data encontrada: {data_bloqueio.date()}, {dias_diferenca} dias atrs')

                            if 0 <= dias_diferenca <= 100:
                                logger.info(f'[BLOQUEIOS] Bloqueio recente encontrado: {data_bloqueio.date()} ({dias_diferenca} dias)')
                                return True

                        except ValueError:
                            continue

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
