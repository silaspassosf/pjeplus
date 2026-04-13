"""Triagem/acoes.py
Ações de audiência e processamento de buckets para Triagem Inicial.
"""
import time
import traceback
from typing import Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.core import esperar_elemento, safe_click, preencher_campo
from Fix.headless_helpers import limpar_overlays_headless
from Fix.gigs import criar_gigs
from Fix.abas import trocar_para_nova_aba
from Triagem.citacao import def_citacao


def _abrir_nova_aba(driver: WebDriver, url: str, aba_origem: str, url_fragmento: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                abas = driver.window_handles
                for h in abas:
                    if h == aba_origem:
                        continue
                    driver.switch_to.window(h)
                    if not url_fragmento:
                        return h
                    try:
                        if url_fragmento in (driver.current_url or ""):
                            return h
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ Erro ao abrir nova aba: {e}")
        return None


def desmarcar_100(driver: WebDriver, id_processo: str) -> Optional[str]:
    aba_detalhe = driver.current_window_handle
    url_retificar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            by=By.CSS_SELECTOR,
            timeout=15
        )
        if not step_carac:
            raise Exception("Step 'Características' não encontrado")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        time.sleep(1)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if len(botoes) >= 4:
                    safe_click(driver, botoes[3])
                elif botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital']:not(.mat-checked)",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
        return nova_aba
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ Erro ao desmarcar 100%: {e}")
        return nova_aba


def remarcar_100_pos_aud(driver: WebDriver):
    try:
        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" not in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital'].mat-checked",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ Erro ao remarcar 100%: {e}")


def marcar_aud(driver: WebDriver, numero_processo: str, rito: str, aba_retorno: str):
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        return

    sucesso = False
    try:
        esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15)

        if rito.upper() == 'ATSUM':
            linha = esperar_elemento(
                driver,
                "//tr[.//span[contains(normalize-space(.), 'Una (rito sumaríssimo)')]]",
                by=By.XPATH,
                timeout=10
            )
        else:
            linha = esperar_elemento(
                driver,
                "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.), 'sumar')]) ]",
                by=By.XPATH,
                timeout=10
            )

        if not linha:
            raise Exception("Linha de pauta não encontrada")

        btn_plus = linha.find_element(By.XPATH, ".//button[@aria-label='Designar Audiência'] | .//i[contains(@class,'fa-plus-circle')]/ancestor::button")
        safe_click(driver, btn_plus)

        modal = esperar_elemento(driver, "mat-dialog-container", by=By.CSS_SELECTOR, timeout=10)
        if not modal:
            raise Exception("Modal de audiência não encontrado")

        input_num = modal.find_element(By.CSS_SELECTOR, "input#inputNumeroProcesso")
        valor_atual = (input_num.get_attribute('value') or '').strip()
        if not valor_atual:
            try:
                safe_click(driver, input_num)
                input_num.clear()
                input_num.send_keys(numero_processo)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    input_num
                )
            except Exception:
                preencher_campo(driver, "#inputNumeroProcesso", numero_processo)
        time.sleep(0.8)
        btn_confirmar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]",
            by=By.XPATH,
            timeout=10
        )
        if not btn_confirmar:
            raise Exception("Botão Confirmar não encontrado")
        safe_click(driver, btn_confirmar)
        time.sleep(1)
        modal_confirmado = esperar_elemento(
            driver,
            "//mat-dialog-container//*[self::h4 or self::h3][contains(normalize-space(.), 'Designação Confirmada')]",
            by=By.XPATH,
            timeout=10
        )
        if modal_confirmado:
            btn_fechar = esperar_elemento(
                driver,
                "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]",
                by=By.XPATH,
                timeout=10
            )
            if btn_fechar:
                safe_click(driver, btn_fechar)
                time.sleep(0.5)
        sucesso = True
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ Erro ao marcar audiência: {e}")
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in driver.window_handles:
                    driver.switch_to.window(aba_retorno)
            except Exception:
                pass


def acao_bucket_a(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('digital', processo_info.get('tem_100', False)))

        numero_formatado = processo_info.get('numero')
        id_processo = str(processo_info.get('id_processo') or '')
        if not numero_formatado or not id_processo:
            print(f"[TRIAGEM/A] ❌ Falha ao extrair número/ID do processo {numero_processo}")
            return False

        rito = 'ATSum' if tipo == 'ATSUM' else 'ATOrd'

        if not tem_100:
            print(f"[TRIAGEM/A] Processo {numero_processo} sem 100% digital. Criando GIGS e marcando audiência.")
            try:
                criar_gigs(driver, "", "", "xs triagem")
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao criar GIGS triagem: {e}")

            limpar_overlays_headless(driver)

            citacao_a = def_citacao(driver, processo_info)
            if not citacao_a.get('sucesso', True):
                print(f"[TRIAGEM/A] 🛑 Polo passivo vazio — abortando execução de GIGS para {numero_processo}")
                return False
            for obs in citacao_a['gigs_obs']:
                try:
                    criar_gigs(driver, "1", "", obs)
                except Exception as e:
                    print(f"[TRIAGEM/A] ⚠ Erro ao criar GIGS ({obs}): {e}")

            marcar_aud(driver, numero_formatado, rito, driver.current_window_handle)
            limpar_overlays_headless(driver)

            try:
                from atos import ato_unap
                return bool(ato_unap(driver, debug=True))
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_unap: {e}")
                return False

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            print(f"[TRIAGEM/A] Processo {numero_processo} não atende critérios de rito. Pulando.")
            return True

        aba_retificar = desmarcar_100(driver, id_processo)
        if not aba_retificar:
            print(f"[TRIAGEM/A] ❌ Não foi possível abrir/usar aba retificar")
            return False

        marcar_aud(driver, numero_formatado, rito, aba_retificar)

        try:
            if aba_retificar in driver.window_handles:
                driver.switch_to.window(aba_retificar)
                remarcar_100_pos_aud(driver)
                driver.close()
        except Exception as e:
            print(f"[TRIAGEM/A] ⚠ Erro ao finalizar retificar: {e}")

        try:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if '/detalhe' in driver.current_url:
                    break
        except Exception:
            pass

        limpar_overlays_headless(driver)
        try:
            criar_gigs(driver, "", "", "xs triagem")
        except Exception as e:
            print(f"[TRIAGEM/A] ⚠ Erro ao criar GIGS triagem: {e}")

        citacao_a2 = def_citacao(driver, processo_info)
        if not citacao_a2.get('sucesso', True):
            print(f"[TRIAGEM/A] 🛑 Polo passivo vazio após triagem — abortando GIGS para {numero_processo}")
            return False
        for obs in citacao_a2['gigs_obs']:
            try:
                criar_gigs(driver, "1", "", obs)
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao criar GIGS ({obs}): {e}")

        try:
            from atos import ato_100
            ato_100(driver, debug=True)
        except Exception as e:
            print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_100: {e}")

        return True
    except Exception as e:
        print(f"[TRIAGEM/A] Erro ao executar ações: {e}")
        traceback.print_exc()
        return False


def acao_bucket_b(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        try:
            criar_gigs(driver, "", "", "xs triagem")
        except Exception as e:
            print(f"[TRIAGEM/B] ⚠ Erro ao criar GIGS triagem: {e}")

        limpar_overlays_headless(driver)

        citacao_b = def_citacao(driver, processo_info)
        if not citacao_b.get('sucesso', True):
            print(f"[TRIAGEM/B] 🛑 Polo passivo vazio — abortando GIGS para {numero_processo}")
            return False

        for obs in citacao_b['gigs_obs']:
            print(f"[TRIAGEM/B] Criando GIGS para {numero_processo} (prazo: 1, observacao: {obs})")
            criar_gigs(driver, "1", "", obs)

        try:
            from atos import ato_100
            ato_100(driver, debug=True)
        except Exception as e:
            print(f"[TRIAGEM/B] ⚠ Erro ao executar ato_100: {e}")

        return True
    except Exception as e:
        print(f"[TRIAGEM/B] Erro ao criar GIGS: {e}")
        traceback.print_exc()
        return False


def acao_bucket_c(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        from atos import mov_aud
        from atos.wrappers_pec import pec_ord, pec_sum, pec_ordc, pec_sumc
        _PEC_MAP = {'pec_ord': pec_ord, 'pec_sum': pec_sum,
                    'pec_ordc': pec_ordc, 'pec_sumc': pec_sumc}

        citacao_c = def_citacao(driver, processo_info)
        if not citacao_c.get('sucesso', True):
            print(f"[TRIAGEM/C] 🛑 Polo passivo vazio — abortando PEC para {numero_processo}")
            return False

        ok = False
        for pec_nome in citacao_c['pec_wrappers']:
            pec_fn = _PEC_MAP.get(pec_nome)
            if pec_fn:
                print(f"[TRIAGEM/C] Executando {pec_nome} para {numero_processo}")
                try:
                    ok = bool(pec_fn(driver, debug=True)) or ok
                except Exception as e:
                    print(f"[TRIAGEM/C] ⚠ Erro em {pec_nome}: {e}")

        if ok:
            print(f"[TRIAGEM/C] Executando mov_aud para {numero_processo}")
            return bool(mov_aud(driver, debug=True))
        return ok
    except Exception as e:
        print(f"[TRIAGEM/C] Erro na ação: {e}")
        traceback.print_exc()
        return False


def acao_bucket_d(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        try:
            criar_gigs(driver, "", "", "xs triagem")
        except Exception as e:
            print(f"[TRIAGEM/D] ⚠ Erro ao criar GIGS triagem: {e}")

        try:
            from atos import ato_ratif
        except ImportError:
            print(f"[TRIAGEM/D] ato_ratif não disponível")
            return False

        try:
            print(f"[TRIAGEM/D] Executando ato_ratif para {numero_processo}")
            return bool(ato_ratif(driver, debug=True))
        except Exception as e:
            print(f"[TRIAGEM/D] Erro ao executar ato_ratif: {e}")
            return False
    except Exception as e:
        print(f"[TRIAGEM/D] Erro geral na ação: {e}")
        traceback.print_exc()
        return False


__all__ = ['acao_bucket_a', 'acao_bucket_b', 'acao_bucket_c', 'acao_bucket_d']
