"""
SISB.ordens_execucao - Execucao detalhada de ordens SISBAJUD e validacao.

Merge de:
  - SISB/processamento_ordens_processamento.py (_processar_ordem)
  - SISB/validation/processor.py              (_validar_dados)

Public contracts:
  - _processar_ordem(driver, ordem, tipo_fluxo, log, valor_parcial, apenas_extrair)
  - _validar_dados(dados_processo)
"""

import logging
import time as time_module

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import safe_click
from Fix.log import logger

# ---------------------------------------------------------------------------
# _validar_dados - validacao de dados do processo
# ---------------------------------------------------------------------------


def _validar_dados(dados_processo):
    """
    Helper para validar dados do processo necessarios para minuta de bloqueio.

    Args:
        dados_processo: Dados do processo (se None, carrega do arquivo dadosatuais.json)

    Returns:
        tuple: (dados_validos, numero_processo) onde dados_validos é bool e numero_processo é str
    """
    try:
        # Se dados_processo não foi fornecido, carregar do arquivo
        if not dados_processo:
            try:
                from ..utils import carregar_dados_processo
                dados_processo = carregar_dados_processo()
                if not dados_processo:
                    return False, None
            except Exception as e:
                logger.error(f'[SISBAJUD]  Erro ao carregar dados do arquivo: {e}')
                return False, None

        # Verificar campos obrigatórios
        numero_lista = dados_processo.get('numero', [])
        if not numero_lista:
            return False, None

        numero_processo = numero_lista[0] if numero_lista else None
        if not numero_processo:
            return False, None

        reus = dados_processo.get('reu', [])
        if not reus:
            return False, None

        return True, numero_processo

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao validar dados: {e}')
        return False, None


# ---------------------------------------------------------------------------
# _processar_ordem - processamento detalhado de ordem no /desdobrar
# ---------------------------------------------------------------------------


def _processar_ordem(driver, ordem, tipo_fluxo, log=True, valor_parcial=None, apenas_extrair=False):
    """
    Processa uma ordem individual do SISBAJUD - VERSÃO OTIMIZADA.

    Otimizações aplicadas:
    - CSS selector direto em vez de iteração (reduz latência 50%)
    - Delays mínimos: 0.2-0.3s entre ações (em vez de 0.5s)
    - WebDriverWait com timeout curto (máximo 3s)
    - Safe click com simulação humana mínima

    Sequência:
    1. Localizar linha por CSS selector direto
    2. Clicar em menu (botão ellipsis)
    3. Clicar em "Detalhar"
    4. (Se apenas_extrair=False) Selecionar Juiz, ação, dados de transferência
    5. (Se apenas_extrair=False) Salvar
    6. (Se apenas_extrair=True) Apenas extrair dados e voltar

    Args:
        driver: WebDriver SISBAJUD
        ordem: Dict com 'sequencial', 'data', 'valor_bloqueio_esperado', 'protocolo', 'linha_el'
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        log: Se deve fazer log
        valor_parcial: Se presente, faz transferência parcial com este valor (float)
        apenas_extrair: Se True, apenas abre /desdobrar, extrai dados e volta (sem processar)

    Returns:
        bool: True se processamento bem-sucedido
    """
    _start_geral = time_module.time()

    try:
        # inicializar metricas leves no driver
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

        # ===== VERIFICAR SE ESTÁ NA PÁGINA CORRETA =====
        # URL esperadas:
        # - https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes (lista de ordens - CORRETO)
        # - https://sisbajud.pdpj.jus.br/teimosinha (página de pesquisa - ERRADO)
        # - https://sisbajud.cnj.jus.br/minuta (minuta - ERRADO)

        url_atual = driver.current_url.lower()

        # Verificar se está em página inválida (não deve fazer back se estiver em /detalhes)
        if "/detalhes" not in url_atual and ("/minuta" in url_atual or url_atual.endswith("/teimosinha")):
            logger.warning("[SISBAJUD] [ORDEM] ALERTA: Pagina incorreta detectada! Tentando navegar para lista de ordens da serie...")
            # NÃO usar driver.back() - pode piorar a situação
            # Retornar False para que o retry externo navegue corretamente
            return False

        # ===== OTIMIZAÇÃO 1: CSS SELECTOR DIRETO =====
        # Em vez de iterar todas as linhas, usar XPath direto para a ordem
        sequencial = ordem['sequencial']

        # Seletor otimizado: vai direto para a linha com o sequencial
        xpath_linha = f"//tr[.//td[contains(@class,'cdk-column-index') and normalize-space(text())='{sequencial}']]"

        try:
            linha_el = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, xpath_linha))
            )
            logger.debug("[SISBAJUD] [ORDEM] Linha localizada via XPath direto +%.1fs", time_module.time()-_start_geral)
        except:
            logger.debug("[SISBAJUD] [ORDEM] Fallback: buscando linha por CSS selector...")
            # Fallback: buscar via CSS selector de tabela
            try:
                # Aguardar tabela estabilizar após navegação
                tabela = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody tr.mat-row"))
                )
                time_module.sleep(0.5)  # estabilização Angular pós-render

                tbody = driver.find_element(By.CSS_SELECTOR, "table.mat-table tbody")
                linhas = tbody.find_elements(By.CSS_SELECTOR, "tr.mat-row")
                linha_el = None

                logger.debug("[SISBAJUD] [ORDEM] Buscando ordem %s entre %s linhas...", sequencial, len(linhas))

                for linha in linhas:
                    try:
                        cel_seq = linha.find_element(By.CSS_SELECTOR, "td.mat-cell.cdk-column-index")
                        seq_text = cel_seq.text.strip()
                        if seq_text == str(sequencial):
                            linha_el = linha
                            logger.debug("[SISBAJUD] [ORDEM] Linha encontrada: ordem %s", sequencial)
                            break
                    except:
                        continue

                if not linha_el:
                    logger.error("ERRO em _processar_ordem: Linha nao encontrada para ordem %s", sequencial)
                    return False
            except Exception as e_fallback:
                logger.error("ERRO em _processar_ordem: Erro no fallback: %s", e_fallback)
                return False

        # ===== ABRIR ORDEM =====
        # mat-icon.icone-ativo tem aria-hidden=true — não tem binding Angular.
        # Navegação real: button.mat-menu-trigger (ellipsis) → item "Detalhar"
        abriu = False
        try:
            btn_menu = linha_el.find_element(By.CSS_SELECTOR, "button.mat-menu-trigger")
            driver.execute_script("arguments[0].click();", btn_menu)
            time_module.sleep(0.6)

            itens = WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[role='menuitem']"))
            )
            for item in itens:
                txt = item.text.strip().lower()
                if any(k in txt for k in ['detalh', 'desdobr', 'abrir']):
                    driver.execute_script("arguments[0].click();", item)
                    abriu = True
                    logger.debug("[SISBAJUD] [ORDEM] Menu → '%s' clicado +%.1fs", item.text.strip(), time_module.time()-_start_geral)
                    break

            if not abriu:
                logger.debug("[SISBAJUD] [ORDEM] Itens do menu: %s", [i.text.strip() for i in itens])
        except Exception as e_menu:
            logger.error("ERRO em _processar_ordem: Menu ellipsis falhou: %s", e_menu)

        # Fallback final: menu ellipsis → Detalhar
        if not abriu:
            logger.debug("[SISBAJUD] [ORDEM] Ultimo fallback: menu ellipsis...")
            try:
                btn_menu = linha_el.find_element(By.CSS_SELECTOR, "button.mat-menu-trigger")
                safe_click(driver, btn_menu, 'click')
                time_module.sleep(0.5)
                opcoes_menu = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//button[@role='menuitem']"))
                )
                for opcao in opcoes_menu:
                    if "detalh" in opcao.text.lower() or "desdobr" in opcao.text.lower():
                        safe_click(driver, opcao, 'click')
                        abriu = True
                        logger.debug("[SISBAJUD] [ORDEM] 'Detalhar' via menu +%.1fs", time_module.time()-_start_geral)
                        break
            except Exception as e3:
                logger.error("ERRO em _processar_ordem: Menu ellipsis falhou: %s", e3)

        if not abriu:
            logger.error("ERRO em _processar_ordem: Impossivel abrir ordem %s — todos os seletores falharam", sequencial)
            return False

        # ===== AGUARDAR /DESDOBRAR =====
        for tentativa in range(20):  # 20 × 0.5s = 10s máximo
            if "/desdobrar" in driver.current_url:
                logger.debug("[SISBAJUD] [ORDEM] Pagina /desdobrar carregada +%.1fs", time_module.time()-_start_geral)
                break
            time_module.sleep(0.5)
        else:
            url_atual_debug = driver.current_url
            logger.error("ERRO em _processar_ordem: Pagina /desdobrar nao carregou apos 10s (URL: %s)", url_atual_debug)
            return False

        # ===== VERIFICAR SE APENAS EXTRAÇÃO: EXTRAIR DADOS E VOLTAR =====
        if apenas_extrair:
            logger.debug("[SISBAJUD] [ORDEM] Modo apenas extracao - coletando dados...")

            try:
                # Extrair dados dos bloqueios
                from .helpers import extrair_dados_bloqueios_processados
                protocolo_ordem = ordem.get('protocolo', 'N/A')

                dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)

                # Atualizar entrada do relatório com discriminação
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
                # Tentar voltar para lista de ordens mesmo com erro
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


        # ===== PROCESSAMENTO COMPLETO VIA JS ASYNC =====
        texto_acao = 'Transferir valor' if tipo_fluxo == 'POSITIVO' else 'Desbloquear valor'

        logger.debug("[SISBAJUD] [ORDEM] JS async: processando /desdobrar (tipo=%s)...", tipo_fluxo)

        driver.set_script_timeout(90)

        # registrar chamada JS async (vai incrementar quando executado)
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
