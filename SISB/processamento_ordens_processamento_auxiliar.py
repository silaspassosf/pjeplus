import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_ordens_processamento_auxiliar - Parte auxiliar do processamento de ordens SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
Contém scripts JavaScript e lógica de finalização.
"""

import time as time_module
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from Fix.core import safe_click

def _processar_ordem_auxiliar(driver, ordem, tipo_fluxo, juiz_selecionado, acao_selecionada, log=True):
    """
    Parte auxiliar do processamento de ordem - preenchimento e finalização.

    Args:
        driver: WebDriver SISBAJUD
        ordem: Dict com dados da ordem
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        juiz_selecionado: Se juiz foi selecionado
        acao_selecionada: Se ação foi selecionada
        log: Se deve fazer log

    Returns:
        bool: True se processamento bem-sucedido
    """
    _start_geral = time_module.time()
    sequencial = ordem['sequencial']

    try:
        # ===== VERIFICAÇÕES PRÉVIAS =====
        if not juiz_selecionado:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ ALERTA: Juiz não foi selecionado, mas continuando...")

        if not acao_selecionada:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⛔ CRÍTICO: Ação não selecionada - modal não abrirá")
            return False

        # ===== CLICAR BOTÃO SALVAR PARA ABRIR MODAL =====
        time_module.sleep(0.5)
        try:
            btn_salvar = None

            # Seletor 1: por ícone fa-save
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-fab .fa.fa-save")
                btn_salvar = btn_salvar.find_element(By.XPATH, "./ancestor::button")
            except:
                pass

            # Seletor 2: por texto "Salvar"
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.XPATH, "//button[contains(., 'Salvar')]")
                except:
                    pass

            # Seletor 3: button.mat-fab[color='primary']
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-fab[color='primary']")
                except:
                    pass

            if btn_salvar:
                safe_click(driver, btn_salvar, 'click')
                time_module.sleep(1.2)
                if log and tipo_fluxo == "POSITIVO":
                    print(f"[SISBAJUD] [ORDEM] Botão Salvar clicado - abrindo modal de dados...")
                elif log:
                    print(f"[SISBAJUD] [ORDEM] Botão Salvar clicado")
            else:
                if log:
                    print(f"[SISBAJUD] ⚠️ Botão Salvar não encontrado")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ⚠️ Erro ao clicar Salvar: {e}")

        # ===== VERIFICAR SE MODAL ABRIU =====
        if tipo_fluxo == "POSITIVO":
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='tipoCredito']"))
                )
                if log:
                    print(f"[SISBAJUD] [ORDEM] Modal de dados aberto com sucesso")
            except:
                if log:
                    print(f"[SISBAJUD] ⚠️ Modal não detectado após clicar Salvar")

        # ===== PREENCHIMENTO DE DADOS DE TRANSFERÊNCIA =====
        if tipo_fluxo == "POSITIVO":
            time_module.sleep(0.3)

            if log:
                print(f"[SISBAJUD] [ORDEM] Preenchendo dados de transferência (Tipo: Geral, Banco: 00001, Agência: 5905) +{time_module.time()-_start_geral:.1f}s")

            # Tentar usar função do Fix.utils primeiro
            try:
                from Fix.utils import preencher_campos_angular_material
            except ImportError:
                if log:
                    print(f"[SISBAJUD] ⚠️ Fix.utils não disponível, usando fallback")
                preencher_campos_angular_material = None

            if preencher_campos_angular_material:
                resultado = preencher_campos_angular_material(driver, {}, debug=log)
                sucesso = resultado and resultado.get('sucesso', False)
                agencia_final = resultado.get('campos_preenchidos', {}).get('input[formcontrolname="agencia"]', '') if resultado else ''

                if sucesso and agencia_final == '5905':
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Campos preenchidos com sucesso +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ❌ FALHA NO PREENCHIMENTO - NÃO FORAM PREENCHIDOS!")
                        print(f"[SISBAJUD] [ORDEM] Erros: {resultado.get('erros', []) if resultado else []}")
                    return False
            else:
                # Fallback: script direto
                if log:
                    print(f"[SISBAJUD] [ORDEM] Usando fallback de script direto (Fix.utils não disponível)")

                script_preencher = """
                (async function() {
                    const debug = [];

                    function sleep(ms) {
                        return new Promise(r => setTimeout(r, ms));
                    }

                    try {
                        // 1. TIPO DE CRÉDITO: Selecionar "Geral"
                        debug.push('=== INICIANDO PREENCHIMENTO ===');
                        const selectTipoCredito = document.querySelector('mat-select[formcontrolname="tipoCredito"]');
                        debug.push('1. selectTipoCredito encontrado: ' + (!!selectTipoCredito));

                        if (selectTipoCredito) {
                            selectTipoCredito.parentElement.parentElement.click();
                            await sleep(1000);

                            const opcoes = Array.from(document.querySelectorAll('mat-option[role='option']'));
                            debug.push('   - Opções encontradas: ' + opcoes.length);

                            let encontrou = false;
                            for (let opcao of opcoes) {
                                const texto = (opcao.textContent || '').trim().toLowerCase();
                                if (texto.includes('geral')) {
                                    opcao.click();
                                    encontrou = true;
                                    debug.push('   - ✅ Opção "Geral" clicada');
                                    await sleep(500);
                                    break;
                                }
                            }

                            if (!encontrou) {
                                debug.push('   - ❌ Opção "Geral" NÃO encontrada em ' + opcoes.length + ' opções');
                            }
                        }

                        await sleep(300);
                        const selectTipoCreditoValue = document.querySelector('mat-select[formcontrolname="tipoCredito"] .mat-select-value-text');
                        debug.push('   - Valor atual tipoCredito: ' + (selectTipoCreditoValue?.textContent?.trim() || 'VAZIO'));

                        // 2. BANCO: input com autocomplete
                        const inputBanco = document.querySelector('input[formcontrolname="instituicaoFinanceiraPorCategoria"]');
                        debug.push('2. inputBanco encontrado: ' + (!!inputBanco));

                        if (inputBanco) {
                            inputBanco.parentElement.parentElement.click();
                            await sleep(500);

                            inputBanco.focus();
                            await sleep(300);

                            inputBanco.value = 'BRASIL';
                            const evento = new Event('input', { bubbles: true, cancelable: false });
                            inputBanco.dispatchEvent(evento);

                            debug.push('   - Digitado "BRASIL"');
                            debug.push('   - Valor no input: ' + inputBanco.value);

                            await sleep(1200);

                            const opcoesBanco = Array.from(document.querySelectorAll('mat-option[role='option']'));
                            debug.push('   - Opções banco encontradas: ' + opcoesBanco.length);

                            let encontrou = false;
                            for (let opcao of opcoesBanco) {
                                const texto = (opcao.textContent || '').toUpperCase();
                                if (texto.includes('00001') || texto.includes('BRASIL') || texto.includes('BCO')) {
                                    opcao.click();
                                    encontrou = true;
                                    debug.push('   - ✅ Banco selecionado: ' + opcao.textContent.trim().substring(0, 40));
                                    await sleep(500);
                                    break;
                                }
                            }

                            if (!encontrou) {
                                debug.push('   - ⚠️ Banco NÃO encontrado em ' + opcoesBanco.length + ' opções');
                            }

                            debug.push('   - Valor final banco: ' + inputBanco.value);
                        } else {
                            debug.push('   - ❌ Campo Banco NÃO encontrado');
                        }

                        // 3. AGÊNCIA: 5905
                        const inputAgencia = document.querySelector('input[formcontrolname="agencia"]');
                        debug.push('3. inputAgencia encontrado: ' + (!!inputAgencia));

                        if (inputAgencia) {
                            inputAgencia.focus();
                            await sleep(300);

                            inputAgencia.value = '5905';
                            const eventoInput = new Event('input', { bubbles: true, cancelable: false });
                            inputAgencia.dispatchEvent(eventoInput);

                            inputAgencia.blur();

                            debug.push('   - ✅ Agência preenchida: ' + inputAgencia.value);
                            await sleep(500);
                        } else {
                            debug.push('   - ❌ Campo Agência NÃO encontrado');
                        }

                        // Verificações finais
                        debug.push('=== VERIFICAÇÕES FINAIS ===');
                        const tipoFinal = document.querySelector('mat-select[formcontrolname="tipoCredito"] .mat-select-value-text')?.textContent?.trim() || 'VAZIO';
                        const bancoFinal = document.querySelector('input[formcontrolname="instituicaoFinanceiraPorCategoria"]')?.value || 'VAZIO';
                        const agenciaFinal = document.querySelector('input[formcontrolname="agencia"]')?.value || 'VAZIO';

                        debug.push('Tipo Crédito final: ' + tipoFinal);
                        debug.push('Banco final: ' + bancoFinal);
                        debug.push('Agência final: ' + agenciaFinal);

                        return {
                            sucesso: true,
                            tipo: tipoFinal,
                            banco: bancoFinal,
                            agencia: agenciaFinal,
                            debug: debug.join('\\n')
                        };

                    } catch (e) {
                        debug.push('❌ ERRO: ' + e.message + ' em ' + e.stack);
                        return {
                            sucesso: false,
                            erro: e.message,
                            debug: debug.join('\\n')
                        };
                    }
                })();"""

                resultado = driver.execute_script(script_preencher)

                if log:
                    print(f"[SISBAJUD] [ORDEM] === DEBUG DO PREENCHIMENTO ===")
                    if resultado and 'debug' in resultado:
                        for linha in resultado['debug'].split('\n'):
                            print(f"[SISBAJUD] [ORDEM] {linha}")

                if resultado and resultado.get('agencia') == '5905':
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Campos preenchidos com sucesso +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ❌ FALHA NO PREENCHIMENTO - NÃO FORAM PREENCHIDOS!")
                        print(f"[SISBAJUD] [ORDEM] Resultado: Tipo='{resultado.get('tipo') if resultado else 'ERRO'}', Banco='{resultado.get('banco') if resultado else 'ERRO'}', Agência='{resultado.get('agencia') if resultado else 'ERRO'}'")
                    return False

            # ===== CONFIRMAR MODAL =====
            time_module.sleep(0.5)
            try:
                btn_confirmar = None

                # Seletor 1: button.mat-primary[type="submit"]
                try:
                    btn_confirmar = WebDriverWait(driver, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mat-primary[type='submit']"))
                    )
                except:
                    pass

                # Seletor 2: button[color="primary"]
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[color='primary']"))
                        )
                    except:
                        pass

                # Seletor 3: por texto
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirmar')]"))
                        )
                    except:
                        pass

                if btn_confirmar:
                    safe_click(driver, btn_confirmar, 'click')
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Modal confirmado +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Botão Confirmar não encontrado com nenhum seletor")

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao clicar Confirmar: {e}")

        # ===== AGUARDAR FECHAMENTO DO MODAL =====
        time_module.sleep(1.0)

        if log:
            print(f"[SISBAJUD] [ORDEM] ✅ Ordem {sequencial} processada (tipo: {tipo_fluxo}) em {time_module.time()-_start_geral:.1f}s")

        # ===== SALVAR FINAL =====
        salvar_clicado = False
        try:
            btn_salvar = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'mat-fab')]//mat-icon[contains(@class,'fa-save')]//ancestor::button"))
            )
            safe_click(driver, btn_salvar, 'click')
            salvar_clicado = True
            if log:
                print(f"[SISBAJUD] [ORDEM] Salvar clicado +{time_module.time()-_start_geral:.1f}s")
        except:
            if log:
                print(f"[SISBAJUD] ⚠️ Botão Salvar não encontrado (prosseguindo)")

        # ===== AGUARDAR PROCESSAMENTO =====
        time_module.sleep(1.0)

        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']"))
            )
            if log:
                print(f"[SISBAJUD] [ORDEM] ✅ Processada +{time_module.time()-_start_geral:.1f}s TOTAL")
        except:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ Botão Protocolar não detectado (prosseguindo)")

        if log:
            print(f"[SISBAJUD] ✅ Ordem {sequencial} concluída em {time_module.time()-_start_geral:.1f}s")

        return True

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro geral na ordem {sequencial}: {e}")
        return False