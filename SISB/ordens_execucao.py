"""SISB.ordens_execucao - Execucao detalhada de ordens SISBAJUD e validacao."""

import logging
import time as time_module

from Fix import espera
from Fix.core import safe_click, safe_click_no_scroll
from Fix.log import logger


from .processamento.validacao import _validar_dados  # noqa: F401


# _processar_ordem - processamento detalhado de ordem no /desdobrar


def _processar_ordem(driver, ordem, tipo_fluxo, log=True, valor_parcial=None, apenas_extrair=False):
    """Processa uma ordem individual do SISBAJUD - VERSÃO OTIMIZADA."""
    _start_geral = time_module.time()

    try:
        try:
            if not hasattr(driver, '_sisb_metrics') or driver._sisb_metrics is None:
                driver._sisb_metrics = {
                    'start_time': time_module.time(),
                    'last_action_time': time_module.time(),
                    'actions': 0,
                    'transfers': 0,
                    'desbloqueios': 0,
                    'js_calls': 0,
                    'errors': 0
                }
        except Exception:
            pass
        logger.debug("[SISBAJUD] [ORDEM] Processando ordem %s (tipo: %s) +0.0s", ordem['sequencial'], tipo_fluxo)
        logger.debug("[SISBAJUD] [ORDEM] URL atual: %s", driver.current_url)

        # - https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes (lista de ordens - CORRETO)
        # - https://sisbajud.pdpj.jus.br/teimosinha (página de pesquisa - ERRADO)
        # - https://sisbajud.cnj.jus.br/minuta (minuta - ERRADO)

        url_atual = driver.current_url.lower()

        if "/detalhes" not in url_atual and ("/minuta" in url_atual or url_atual.endswith("/teimosinha")):
            logger.warning("[SISBAJUD] [ORDEM] ALERTA: Pagina incorreta detectada! Tentando navegar para lista de ordens da serie...")
            return False

        sequencial = ordem['sequencial']
        xpath_linha = f"//tr[.//td[contains(@class,'cdk-column-index') and normalize-space(text())='{sequencial}']]"

        linha_el = espera.elemento(driver, xpath_linha, teto=3)
        if not linha_el:
            logger.debug("[SISBAJUD] [ORDEM] Fallback: buscando linha por CSS selector...")
            if not espera.ate_aparecer(driver, "table.mat-table tbody tr.mat-row", teto=10):
                logger.error("ERRO em _processar_ordem: Tabela nao apareceu para ordem %s", sequencial)
                return False
            espera.assentar(driver, 0.5)
            tbody = espera.elemento(driver, "table.mat-table tbody", teto=2)
            linhas = espera.elementos(tbody, "tr.mat-row", teto=1) if tbody else []
            for linha in linhas:
                try:
                    cel_seq = espera.elemento(linha, "td.mat-cell.cdk-column-index", teto=0.2)
                    if cel_seq and cel_seq.text.strip() == str(sequencial):
                        linha_el = linha
                        break
                except Exception:
                    continue
            if not linha_el:
                logger.error("ERRO em _processar_ordem: Linha nao encontrada para ordem %s", sequencial)
                return False

        # mat-icon.icone-ativo tem aria-hidden=true — não tem binding Angular.
        abriu = False
        for estrategia_click in (safe_click_no_scroll, lambda d, el: safe_click(d, el, 'click')):
            try:
                btn_menu = espera.elemento(linha_el, "button.mat-menu-trigger", teto=1)
                if not btn_menu:
                    continue
                estrategia_click(driver, btn_menu)
                espera.assentar(driver, 0.5)
                itens = espera.elementos(driver, "button[role='menuitem']", teto=3)
                for item in itens:
                    txt = (item.text or '').strip().lower()
                    if any(k in txt for k in ('detalh', 'desdobr', 'abrir')):
                        estrategia_click(driver, item)
                        abriu = True
                        break
                if abriu:
                    break
            except Exception as e_menu:
                logger.error("ERRO em _processar_ordem: Menu ellipsis falhou: %s", e_menu)

        if not abriu:
            logger.error("ERRO em _processar_ordem: Impossivel abrir ordem %s — todos os seletores falharam", sequencial)
            return False

        if not espera.ate_url(driver, "/desdobrar", teto=10):
            logger.error("ERRO em _processar_ordem: Pagina /desdobrar nao carregou apos 10s (URL: %s)", driver.current_url)
            return False

        if apenas_extrair:
            logger.debug("[SISBAJUD] [ORDEM] Modo apenas extracao - coletando dados...")

            try:
                from .helpers import extrair_dados_bloqueios_processados
                protocolo_ordem = ordem.get('protocolo', 'N/A')

                dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)

                if '_relatorio' in ordem and dados_ordem:
                    ordem['_relatorio']['status'] = 'processado'
                    ordem['_relatorio']['discriminacao'] = dados_ordem

                logger.debug("[SISBAJUD] [ORDEM] Dados extraidos e registrados no relatorio")

                # Voltar para lista de ordens usando navegação interna (evita reload completo)
                try:
                    from .navegacao import _voltar_para_lista_ordens_serie
                    _voltar_para_lista_ordens_serie(driver, log)
                except Exception:
                    try:
                        driver.back()
                    except Exception:
                        pass
                time_module.sleep(0.5)

                return True

            except Exception as e_ext:
                logger.error("ERRO em _processar_ordem: Erro ao extrair dados: %s", e_ext)
                try:
                    from .navegacao import _voltar_para_lista_ordens_serie
                    _voltar_para_lista_ordens_serie(driver, log)
                except Exception:
                    try:
                        driver.back()
                    except Exception:
                        pass
                time_module.sleep(0.5)
                return False

        texto_acao = 'Transferir valor' if tipo_fluxo == 'POSITIVO' else 'Desbloquear valor'

        logger.debug("[SISBAJUD] [ORDEM] JS async: processando /desdobrar (tipo=%s)...", tipo_fluxo)

        driver.set_script_timeout(90)

        try:
            driver._sisb_metrics['js_calls'] += 1
        except Exception:
            pass

        JS_DESDOBRAR = """
	var texto_acao = arguments[0];
	var eh_positivo = arguments[1];
	var done = arguments[2];
	var sleep = function(ms) { return new Promise(function(r) { setTimeout(r, ms); }); };
	var waitFor = async function(selector, timeoutMs, intervalMs) {
	    timeoutMs = timeoutMs || 3000;
	    intervalMs = intervalMs || 80;
	    var inicio = Date.now();
	    while (Date.now() - inicio < timeoutMs) {
	        var el = document.querySelector(selector);
	        if (el) return el;
	        await sleep(intervalMs);
	    }
	    return null;
	};

	(async function() {
	    var log = [];
	    var _t0 = Date.now();
	    var t = function(label) {
	        var ms = Date.now() - _t0;
	        var s = (ms / 1000).toFixed(2);
	        log.push('[+' + s + 's] ' + label);
	    };
	    var _concluido = false;
	    var finalizar = function(payload) {
	        if (_concluido) return;
	        _concluido = true;
	        done(payload);
	    };
	    var vigia = setInterval(function() {
	        if (_concluido) { clearInterval(vigia); return; }
	        log.push('⚠️ timeout interno (80s)');
	        clearInterval(vigia);
	        finalizar({ok: false, log: log, erro: 'timeout interno (80s) - JS travado'});
	    }, 80000);

	    try {
	        // 1. Cancelar Nao Respostas
	        var btnCnr = document.querySelector('button[title="Cancelar Não Respostas"]');
	        if (btnCnr) { btnCnr.click(); log.push('✅ Cancelar Não Respostas'); }
	        await sleep(300);

	        // 2. Juiz
	        var juizInp = document.querySelector('input[data-placeholder*="Juiz"]') ||
	                      document.querySelector('input[placeholder*="Juiz"]') ||
	                      document.querySelector('input[aria-label*="Juiz"]');

	        if (!juizInp) return finalizar({ok: false, log: log, erro: 'campo juiz nao encontrado'});

	        juizInp.click();
	        juizInp.focus();
	        await sleep(200);

	        juizInp.value = '';
	        juizInp.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 40, bubbles: true}));
	        await sleep(100);

	        juizInp.value = 'to ma';
	        juizInp.dispatchEvent(new Event('input', {bubbles: true}));
	        log.push('Juiz: "to ma" digitado');

	        await sleep(800);
	        var opcJuiz = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	        if (opcJuiz.length === 0) {
	             juizInp.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', keyCode: 40, bubbles: true}));
	             await sleep(800);
	             opcJuiz = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	        }

	        var juizOpt = opcJuiz.find(function(o) { return o.textContent.toUpperCase().includes('OTAVIO'); });
	        if (!juizOpt) return finalizar({
	            ok: false,
	            log: log,
	            erro: 'OTAVIO nao encontrado'
	        });

	        juizOpt.click();
	        log.push('✅ Juiz: ' + juizOpt.textContent.trim().substring(0, 40));
	        await sleep(500);

	        // 3. Dropdowns com-saldo
	        var getSels = function() {
	            return Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
	                var panel = s.closest('.mat-expansion-panel-content');
	                if (panel) {
	                    var st = window.getComputedStyle(panel);
	                    if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
	                }
	                var body = s.closest('.mat-expansion-panel-body');
	                if (!body) return false;
	                
	                var saldoCell = body.querySelector('td.cdk-column-saldoRemanescente');
	                if (saldoCell && saldoCell.textContent.includes('0,01')) {
	                    return false;
	                }
	                
	                return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
	            });
	        };

	        var sels = getSels();
	        log.push(sels.length + ' selects com-saldo');

	        for (var i = 0; i < sels.length; i++) {
	            var sAtual = sels[i];
	            var trigger = sAtual.querySelector('.mat-select-trigger');
	            (trigger || sAtual).click();
	            await sleep(800);

	            var opts = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	            if (!opts.length) {
	                 var alvoClick = trigger || sAtual;
	                 alvoClick.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
	                 alvoClick.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
	                 await sleep(800);
	                 opts = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	            }

	            var norm = function(s) { return s.replace(/\\s+/g, ' ').trim(); };
	            var alvo = opts.find(function(o) { return norm(o.textContent) === texto_acao; }) ||
	                       opts.find(function(o) { return norm(o.textContent).indexOf('Transferir') !== -1; });

	            if (alvo) {
	                alvo.click();
	                log.push('✅ select #' + i + ': ' + norm(alvo.textContent));
	            } else {
	                log.push('⚠️ select #' + i + ': "' + texto_acao + '" nao encontrado.');
	                document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27, bubbles: true}));
	            }
	            await sleep(300);
	        }

	        // 4. Salvar
	        var btnSalvar = document.querySelector('button.mat-fab[color="primary"]');
	        if (!btnSalvar) return finalizar({ok: false, log: log, erro: 'Salvar nao encontrado'});
	        btnSalvar.click(); log.push('✅ Salvar clicado'); await sleep(800);

	        // 5-8: Modal (apenas POSITIVO)
	        if (eh_positivo) {
	            var selTipo = await waitFor('mat-select[formcontrolname="tipoCredito"]', 5000);
	            if (!selTipo) return finalizar({ok: false, log: log, erro: 'tipoCredito nao encontrado'});

	            selTipo.parentElement.parentElement.click();
	            await sleep(500);

	            var opcTipo = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	            var geral = opcTipo.find(function(o) { return o.textContent.trim().toLowerCase().includes('geral'); });
	            if (geral) {
	                geral.click();
	                log.push('✅ tipoCredito: Geral');
	            } else {
	                return finalizar({ok: false, log: log, erro: 'Geral nao encontrado'});
	            }
	            await sleep(300);

	            var inpBanco = await waitFor('input[formcontrolname="instituicaoFinanceiraPorCategoria"]', 3000);
	            if (inpBanco) {
	                inpBanco.parentElement.parentElement.click(); inpBanco.focus();
	                inpBanco.value = 'BRASIL'; inpBanco.dispatchEvent(new Event('input', {bubbles: true}));
	                await sleep(800);

	                var opcBanco = Array.from(document.querySelectorAll('mat-option[role="option"]'));
	                var banco = opcBanco.find(function(o) {
	                    var t = o.textContent.toUpperCase();
	                    return t.includes('00001') || (t.includes('BRASIL') && !t.includes('BRADESCO'));
	                });
	                if (banco) {
	                    banco.click();
	                    log.push('✅ banco: ' + banco.textContent.trim().substring(0, 35));
	                } else {
	                     return finalizar({ok: false, log: log, erro: 'banco 00001 nao encontrado'});
	                }
	            }
	            await sleep(300);

	            var inpAg = await waitFor('input[formcontrolname="agencia"]', 2000);
	            if (inpAg) {
	                inpAg.focus(); inpAg.value = '5905';
	                inpAg.dispatchEvent(new Event('input', {bubbles: true})); inpAg.blur();
	                log.push('✅ agencia: 5905');
	            }
	            await sleep(400);

	            var btnConf = Array.from(document.querySelectorAll('button')).find(function(b) { return b.textContent.trim() === 'Confirmar'; });
	            if (btnConf && !btnConf.disabled) {
	                btnConf.click();
	                log.push('✅ Confirmar modal clicado');
	            }
	        }

	        log.push('✅ Finalizado apos salvar (sem protocolar/senha)');
	        clearInterval(vigia);
	        finalizar({ok: true, log: log});

	    } catch(e) {
	        clearInterval(vigia);
	        finalizar({ok: false, log: log, erro: e.toString()});
	    }
	})();
	"""

        try:
            resultado = driver.execute_async_script(JS_DESDOBRAR, texto_acao, tipo_fluxo == 'POSITIVO')
        except TimeoutException:
            logger.error("ERRO em _processar_ordem: JS async timeout (90s) em /desdobrar")
            return False

        if isinstance(resultado, dict):
            for passo in (resultado.get('log') or []):
                logger.debug("[SISBAJUD] [ORDEM]    %s", passo)
            if not resultado.get('ok'):
                logger.error("ERRO em _processar_ordem: JS async falhou: %s", resultado.get('erro', '?'))
                return False

        logger.debug("[SISBAJUD] Ordem %s concluida em %.1fs", sequencial, time_module.time()-_start_geral)
        # pequena pausa reativa para evitar bursts imediatos de requisicoes
        time_module.sleep(0.5)
        return True

    except Exception as e:
        logger.error("ERRO em _processar_ordem: Erro geral na ordem %s: %s", ordem['sequencial'], e)
        return False
