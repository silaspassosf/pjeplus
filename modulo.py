import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r'C:/Users/Silas/AppData/Roaming/Mozilla/Firefox/Profiles/bs41tjj2.Selenium'
LOGIN_URL = "https://pje.trt2.jus.br/primeirograu/login.seam"
PAINEL_URL = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"

def login_automatico(driver, usuario, senha):
    driver.get(LOGIN_URL)
    print('[LOGIN] Página de login carregada.')
    def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR):
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                if texto:
                    elementos = driver.find_elements(by, seletor)
                    for el in elementos:
                        if texto.strip().lower() in el.text.strip().lower():
                            return el
                else:
                    el = driver.find_element(by, seletor)
                    if el.is_displayed():
                        return el
            except Exception:
                pass
            time.sleep(0.2)
        print(f"[LOGIN][ERRO] Timeout esperando elemento: {seletor} ({texto if texto else ''})")
        return None
    def safe_click(driver, element):
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            return True
        except Exception as e:
            print(f"[LOGIN][ERRO] Erro ao clicar: {e}")
            return False
    btn_pdpj = esperar_elemento(driver, 'button#btnSsoPdpj > img', timeout=10)
    if btn_pdpj:
        safe_click(driver, btn_pdpj)
        time.sleep(2)
    else:
        print('[LOGIN][ERRO] Botão PDPJ não encontrado.')
        return False
    campo_usuario = esperar_elemento(driver, 'input#username', timeout=10)
    if campo_usuario:
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
    else:
        print('[LOGIN][ERRO] Campo usuário não encontrado.')
        return False
    campo_senha = esperar_elemento(driver, 'input#password', timeout=10)
    if campo_senha:
        campo_senha.clear()
        campo_senha.send_keys(senha)
    else:
        print('[LOGIN][ERRO] Campo senha não encontrado.')
        return False
    btn_entrar = esperar_elemento(driver, 'input#kc-login', timeout=10)
    if btn_entrar:
        safe_click(driver, btn_entrar)
        time.sleep(3)
        print('[LOGIN] Login realizado com sucesso.')
        return True
    else:
        print('[LOGIN][ERRO] Botão Entrar não encontrado.')
        return False

# Função aplicar_filtro_100 local (corrige erro de importação)
def aplicar_filtro_100(driver):
    """
    Seleciona '100' no filtro de itens por página do painel global.
    """
    try:
        # Clica no seletor de itens por página
        seletor = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'mat-select-min-line')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seletor)
        seletor.click()
        time.sleep(0.5)
        # Seleciona a opção '100'
        opcoes = driver.find_elements(By.XPATH, "//mat-option//span[contains(text(), '100')]")
        for opcao in opcoes:
            if opcao.is_displayed():
                opcao.click()
                print('[FILTRO] Selecionado 100 itens por página.')
                time.sleep(1)
                return True
        print('[FILTRO][ERRO] Opção 100 não encontrada.')
        return False
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha ao aplicar filtro 100: {e}')
        return False

def filtrar_fase_processual(driver, fases_alvo=None):
    if fases_alvo is None:
        fases_alvo = ['Liquidação', 'Execução']
    print(f'[ACAO] Filtrando fase processual: {fases_alvo}')
    try:
        # 1. Localizar o mat-select do filtro "Fase processual"
        mat_select = driver.find_element(
            By.XPATH,
            "//mat-select[contains(@aria-label, 'Fase processual') or contains(@name, 'Fase processual')]"
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", mat_select)
        driver.execute_script("""
            const el = arguments[0];
            if (typeof el.focus === 'function') el.focus();
            el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true,cancelable:true,view:window}));
            el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true,cancelable:true,view:window}));
            el.dispatchEvent(new MouseEvent('click', {bubbles:true,cancelable:true,view:window}));
        """, mat_select)
        time.sleep(0.7)

        # 2. Esperar painel abrir e opções aparecerem
        panel = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.mat-select-panel'))
        )
        # Espera ativa pelas opções desejadas
        def opcoes_presentes(driver):
            opts = panel.find_elements(By.CSS_SELECTOR, 'mat-option span.mat-option-text')
            textos = [opt.text.strip().lower() for opt in opts]
            return all(fase.lower() in ' '.join(textos) for fase in fases_alvo)
        WebDriverWait(driver, 10).until(opcoes_presentes)

        # 3. Clicar nas opções corretas
        opts = panel.find_elements(By.CSS_SELECTOR, 'mat-option span.mat-option-text')
        clicked = 0
        for opt in opts:
            texto = opt.text.strip()
            if texto in fases_alvo:
                mat_option = opt.find_element(By.XPATH, './ancestor::mat-option')
                driver.execute_script("""
                    const el = arguments[0];
                    if (typeof el.focus === 'function') el.focus();
                    el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true,cancelable:true,view:window}));
                    el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true,cancelable:true,view:window}));
                    el.dispatchEvent(new MouseEvent('click', {bubbles:true,cancelable:true,view:window}));
                """, mat_option)
                print(f'[ACAO] Opção selecionada: {texto}')
                clicked += 1
                time.sleep(0.4)
        if clicked == 0:
            print('[ACAO][ERRO] Nenhuma opção de fase clicada!')
            return False

        # 4. Envia TAB para garantir aplicação/finalização do filtro
        # driver.switch_to.active_element.send_keys(Keys.TAB)
        # time.sleep(0.5)

        # 5. NÃO clicar em nenhum botão de filtro!
        print('[ACAO] Filtro de fase aplicado. Nenhum clique em botão de filtro.')
        return True
    except Exception as e:
        print(f'[ACAO][ERRO] Falha ao filtrar fases: {e}')
        return False

def main():
    options = Options()
    options.profile = PROFILE_PATH
    driver = webdriver.Firefox(options=options)
    # Ajusta o zoom para 90% para o login
    try:
        driver.execute_script("document.body.style.zoom='90%'")
        print('[VISUAL] Zoom ajustado para 90% (login).')
    except Exception as e:
        print(f'[VISUAL][WARN] Não foi possível ajustar zoom: {e}')
    driver.get(LOGIN_URL)
    usuario = os.environ.get('PJE_USUARIO')
    senha = os.environ.get('PJE_SENHA')
    if not usuario:
        usuario = input('Usuário PJe: ')
    if not senha:
        senha = input('Senha PJe: ')
    print('[LOGIN] Iniciando login...')
    if not login_automatico(driver, usuario, senha):
        print('[LOGIN][ERRO] Falha no login automático. Encerrando script.')
        driver.quit()
        exit(1)
    print('[NAV] Indo para painel global de processos...')
    # Maximiza a janela após login, antes de acessar o painel global
    try:
        driver.maximize_window()
        print('[VISUAL] Janela maximizada após login.')
    except Exception as e:
        print(f'[VISUAL][WARN] Não foi possível maximizar a janela: {e}')
    # Se necessário, reforce o zoom após maximizar
    try:
        driver.execute_script("document.body.style.zoom='90%'")
    except Exception:
        pass
    driver.get(PAINEL_URL)
    # Aguarda o span de itens por página estar presente
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'mat-select-min-line')]"))
    )
    time.sleep(2)
    print('[FLUXO] Iniciando filtro de 100 processos por página...')
    aplicar_filtro_100(driver)
    time.sleep(2)
    print('[FLUXO] Filtro de 100 aplicado. Agora filtrando fases (Liquidação/Execução)...')
    filtrar_fase_processual(driver)
    time.sleep(1)
    print('[FLUXO] Filtro de fases aplicado. Fechando filtro de fase (fa-filter) e executando seleção+atividade em lote via MutationObserver JS...')
    try:
        js_mutation = '''
        (function() {
            var icon = document.querySelector('i.fas.fa-filter');
            var btn = icon.closest('button,div');
            btn.click();
            var observer = new MutationObserver(async function(mutations, obs) {
                var linhas = document.querySelectorAll('tr.cdk-drag');
                if (linhas.length > 0) {
                    // Seleciona todos os processos livres conforme a lógica já existente
                    let selecionados = 0;
                    linhas.forEach(linha => {
                        const tds = linha.querySelectorAll('td.td-class');
                        let prazoPreenchido = false;
                        if (tds.length >= 9) {
                            const tdPrazo = tds[8];
                            if (tdPrazo.querySelector('time') && tdPrazo.querySelector('time').textContent.trim() !== '') {
                                prazoPreenchido = true;
                            }
                        }
                        const temComentario = linha.querySelector('i.fa-comment') !== null;
                        const tdBusca = tds.length >= 3 ? tds[2] : null;
                        let temBuscaAtiva = false;
                        if (tdBusca) {
                            const iconeBusca = tdBusca.querySelector('i.fa-search');
                            if (iconeBusca) {
                                const textoColuna = tdBusca.textContent || '';
                                const title = iconeBusca.getAttribute('title') || '';
                                if (textoColuna.toLowerCase().includes('petição') || title.toLowerCase().includes('petição')) {
                                    temBuscaAtiva = true;
                                }
                            }
                        }
                        if (!prazoPreenchido && !temComentario && !temBuscaAtiva) {
                            const checkbox = linha.querySelector('mat-checkbox input[type=checkbox]');
                            if (checkbox && !checkbox.checked) {
                                checkbox.click();
                                linha.style.backgroundColor = '#ffccd2';
                                selecionados++;
                            }
                        }
                    });
                    // Clique no tag verde para aplicar atividade em lote
                    const tagVerdeLote = document.querySelector('i.fa.fa-tag.icone.texto-verde');
                    if (tagVerdeLote) {
                        tagVerdeLote.click();
                        await new Promise(r => setTimeout(r, 800));
                        // Clicar em "Atividade" no menu
                        const spanAtividade = Array.from(document.querySelectorAll('span')).find(
                            el => el.textContent.trim() === 'Atividade'
                        );
                        if (spanAtividade) {
                            spanAtividade.click();
                            await new Promise(r => setTimeout(r, 800));
                        }
                        // Preencher e salvar atividade
                        function esperarElemento(seletor, timeout = 8000) {
                            return new Promise((resolve, reject) => {
                                const start = Date.now();
                                function check() {
                                    const el = document.querySelector(seletor);
                                    if (el && el.offsetParent !== null) return resolve(el);
                                    if (Date.now() - start > timeout) return reject('Timeout: ' + seletor);
                                    setTimeout(check, 200);
                                }
                                check();
                            });
                        }
                        try {
                            const inputDias = await esperarElemento('pje-gigs-cadastro-atividades input[formcontrolname="dias"]');
                            inputDias.focus();
                            inputDias.value = "0";
                            inputDias.dispatchEvent(new Event('input', {bubbles:true}));
                            const textareaObs = await esperarElemento('pje-gigs-cadastro-atividades textarea[formcontrolname="observacao"]');
                            textareaObs.focus();
                            textareaObs.value = "xs";
                            textareaObs.dispatchEvent(new Event('input', {bubbles:true}));
                            const btnSalvar = await esperarElemento('pje-gigs-cadastro-atividades button[type="submit"].mat-primary');
                            btnSalvar.click();
                            await new Promise(r => setTimeout(r, 1200));
                        } catch (e) {}
                    }
                    window._seletor_result = selecionados;
                    obs.disconnect();
                }
            });
            var tbody = document.querySelector('tbody');
            if (tbody) {
                observer.observe(tbody, {childList: true, subtree: true});
            }
        })();
        '''
        driver.execute_script(js_mutation)
        print('[FLUXO][JS] Seleção e aplicação de atividade em lote disparadas via tag verde (MutationObserver). Aguarde a conclusão automática!')
    except Exception as e:
        print(f'[WARN] Falha ao executar filtro/seletor/atividade em lote via MutationObserver: {e}')
    print('[FLUXO] Fim do fluxo automatizado. Feche manualmente para inspecionar.')
    input('Pressione Enter para encerrar...')
    driver.quit()

if __name__ == '__main__':
    main()
