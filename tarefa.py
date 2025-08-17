from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def tarefa(driver, timeout=10):
    wait = WebDriverWait(driver, timeout)
    actions = ActionChains(driver)

    cont_processadas = 0
    cont_puladas = 0
    linha_global = 1

    # Ajuste de zoom
    driver.execute_script("document.body.style.zoom='50%';")
    print("[DEPURAÇÃO] Zoom ajustado para 50%")

    # --- Auxiliares ---
    def abrir_primeiro_modal_por_tag(tr, idx_label):
        tag_btn = tr.find_element(By.CSS_SELECTOR, "i.fa-tag.icone-padrao")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tag_btn)
        time.sleep(0.1)
        try:
            tag_btn.click()
            print(f"[{idx_label}] Clique na tag (normal)")
        except Exception:
            driver.execute_script("arguments[0].click();", tag_btn)
            print(f"[{idx_label}] Clique na tag (JS)")
        modal_card = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "mat-card.ficha-processo-card")
        ))
        driver.execute_script("arguments[0].focus();", modal_card)
        print(f"[{idx_label}] Primeiro modal visível")
        return modal_card

    def obter_editar_no_modal(modal_card, idx_label):
        lista_ativ = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div#lista-atividades")
        ))
        tabela = lista_ativ.find_element(By.XPATH, ".//table")
        try:
            tr_modal = tabela.find_element(
                By.XPATH,
                ".//tr[.//i[contains(@class,'danger') and contains(@class,'fa-clock')]]"
            )
            btn_tag = tr_modal.find_element(By.XPATH, ".//button[.//i[contains(@class,'fa-edit')]]")
            edit_btn = btn_tag.find_element(By.XPATH, ".//i[contains(@class,'fa-edit')]/..")
            print(f"[{idx_label}] Botão Editar localizado na TR do modal")
        except Exception:
            try:
                generic_icon = modal_card.find_element(By.CSS_SELECTOR, "i.far.fa-edit.botao-icone-tabela")
                edit_btn = generic_icon.find_element(By.XPATH, "./..")
                print(f"[{idx_label}] Fallback: botão Editar genérico")
            except Exception as e:
                print(f"[{idx_label}] ERRO: nenhum botão Editar visível: {e}")
                return None
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", edit_btn)
        time.sleep(0.1)
        try:
            edit_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", edit_btn)
        print(f"[{idx_label}] Clique no botão Editar")
        dialog = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "mat-dialog-container")))
        driver.execute_script("arguments[0].focus();", dialog)
        return dialog

    def salvar_e_fechar(dialog, idx_label):
        ta = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "textarea[formcontrolname='observacao']")
        ))
        val = ta.get_attribute("value") or ""
        if not val.startswith("."):
            ta.clear()
            ta.send_keys("." + val)
            print(f"[{idx_label}] Ponto inserido na observação")
        else:
            print(f"[{idx_label}] Observação já iniciava com ponto")
        save_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//mat-dialog-container//button[.//span[normalize-space(.)='Salvar']]")
        ))
        try:
            save_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", save_btn)
        print(f"[{idx_label}] Clique no botão Salvar")
        time.sleep(0.25)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "mat-dialog-container")))
        print(f"[{idx_label}] Segundo modal fechado com ESC")
        time.sleep(0.3)

    # --- Loop por páginas ---
    pagina = 1
    while True:
        print(f"\n[DEPURAÇÃO] ===== Página {pagina} =====")
        clocks = driver.find_elements(By.CSS_SELECTOR, "i.danger.fa-clock.far")
        clocks_validos = clocks[1:] if len(clocks) > 1 else []
        total_pag = len(clocks_validos)

        if total_pag == 0:
            print("[DEPURAÇÃO] Nenhuma linha. Fim.")
            break

        for i in range(total_pag):
            idx_label = f"P{pagina}-L{i+1}-G{linha_global}"
            try:
                # Releitura da lista nesta posição (evita stale)
                clocks_now = driver.find_elements(By.CSS_SELECTOR, "i.danger.fa-clock.far")[1:]
                if i >= len(clocks_now):
                    print(f"[{idx_label}] Item desapareceu após re-scan. Pulando.")
                    linha_global += 1
                    continue

                tr = clocks_now[i].find_element(By.XPATH, "./ancestor::tr")

                # Observação antes de abrir modal
                try:
                    obs_text = tr.find_element(By.CSS_SELECTOR, "div.col-descricao span.texto-descricao").text.strip()
                    print(f"[{idx_label}] Observação na lista: '{obs_text}'")
                    if obs_text.startswith("."):
                        print(f"[{idx_label}] Já tem ponto. Pulando.")
                        cont_puladas += 1
                        linha_global += 1
                        continue
                except Exception:
                    print(f"[{idx_label}] Sem observação na lista")

                modal_card = abrir_primeiro_modal_por_tag(tr, idx_label)
                dialog = obter_editar_no_modal(modal_card, idx_label)
                if not dialog:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    print(f"[{idx_label}] Fechou 1º modal sem editar")
                    linha_global += 1
                    continue
                salvar_e_fechar(dialog, idx_label)
                cont_processadas += 1

            except Exception as e:
                print(f"[{idx_label}] ERRO: {e}")
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except:
                    pass
            finally:
                linha_global += 1
                time.sleep(0.4)

        # Avança página se estava "cheia"
        if total_pag == 5:
            try:
                print(f"\n[DEPURAÇÃO] Página {pagina} concluída. Avançando...")
                next_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//pje-paginador//button[@aria-label='Próximo' and not(@disabled)]")
                ))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                next_btn.click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr")))
                pagina += 1
                time.sleep(0.5)
                continue
            except Exception as e:
                print(f"[DEPURAÇÃO] Não conseguiu avançar: {e}")
                break
        else:
            print(f"\n[DEPURAÇÃO] Última página ({pagina}) com menos de 5 linhas.")
            break

    total = cont_processadas + cont_puladas
    print(f"\n[DEPURAÇÃO] Processadas: {cont_processadas} | Puladas: {cont_puladas} | Total linhas vistas: {total}")
    return cont_processadas
