# selectors_pje.py
# Centralização dos seletores usados no projeto de automação PJe TRT2
# Organização inspirada em Fix.py para facilitar manutenção e leitura
# Autor: (Seu nome ou equipe)

# =========================
# 1. SELETORES GERAIS E ÍCONES
# =========================
FA_TAGS_ICON = ".fa-tags"
MENU_FA_BARS = ".fa-bars"
BTN_LEMBRETE = ".lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)"
DIALOG_LEMBRETE = ".mat-dialog-content"
INPUT_TITULO_POSTIT = "#tituloPostit"
INPUT_CONTEUDO_POSTIT = "#conteudoPostit"
BTN_SALVAR_POSTIT = "button.mat-raised-button:nth-child(1)"

# =========================
# 2. TELAS, CONTAINERS E TABELAS
# =========================
TELA_ATIVIDADES_GIGS = ".classe-unica-da-tela-atividades"
LOADING_SPINNER = ".loading-spinner, .mat-progress-spinner"
TABELA_PROCESSOS = "mat-table.mat-table"
LINHAS_PROCESSOS = "tr.cdk-drag"
LINK_PROCESSO = "a"

# =========================
# 3. PEC, ATOS E CAMPOS DE FORMULÁRIO
# =========================
BTN_PEC = "#cke_16"
BTN_INCLUIR_PEC = 'a[title="Incluir processo eletrônico colaborativo"]'
BTN_OK_PEC = "#btnOk"
TEXTAREA_OBSERVACOES_PEC = "textarea[id*='observacoes']"
SELECT_TIPO_EXPEDIENTE = "select#tipoExpediente"  # Exemplo, ajustar conforme real
MAT_CHIP_REMOVE = ".mat-chip-remove"
BTN_ATIVIDADES_SEM_PRAZO = "i.fa-pen:nth-child(1)"
CAMPO_DESCRICAO_ATIVIDADE = "mat-form-field.ng-tns-c82-209 input"

# =========================
# 4. ANEXOS E DIALOGS
# =========================
BTN_ANEXOS = "pje-timeline-anexos > div > div"
ANEXOS_LIST = ".tl-item-anexo"
BTN_SIGILO = "i.fa-wpexplorer"
BTN_VISIBILIDADE = "i.fa-plus"
BTN_CONFIRMAR_DIALOG = ".mat-dialog-actions > button:nth-child(1) > span"

# =========================
# 5. BOTÕES GERAIS
# =========================
BTN_SALVAR_GIGS = "button.mat-raised-button"
BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'

# =========================
# 6. FUNÇÕES PARA SELETORES DINÂMICOS
# =========================
def seletor_processo_por_numero(numero):
    """Retorna seletor CSS para linha de processo pelo número."""
    return f"tr.cdk-drag[data-numero='{numero}']"

def seletor_pec_por_numero(numero):
    """Retorna seletor CSS para PEC pelo número."""
    return f"a[title*='{numero}']"

def buscar_seletor_robusto(driver, textos, timeout=10, log=True):
    """
    Busca robusta de elementos por texto, aria-label, mattooltip, alt, src, class, etc.
    Retorna o primeiro elemento encontrado que contenha o texto em qualquer desses atributos.
    """
    from selenium.webdriver.common.by import By
    import time
    # 1. Busca por aria-label, placeholder, name, title
    for texto in textos:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR,
                f'*[aria-label*="{texto}"], *[placeholder*="{texto}"], *[name*="{texto}"], *[title*="{texto}"]')
            for el in elementos:
                if el.is_displayed():
                    if log:
                        print(f'[SELECTOR] Found by aria-label/placeholder/title: {texto}')
                    return el
        except Exception:
            continue
    # 2. Busca por texto visível
    for texto in textos:
        try:
            xpath = f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')]"
            elementos = driver.find_elements(By.XPATH, xpath)
            for el in elementos:
                if el.is_displayed():
                    if log:
                        print(f'[SELECTOR] Found by visible text: {texto}')
                    return el
        except Exception:
            continue
    # 3. Fallback: busca por ícones (img/button) com mattooltip, alt, src, class
    for texto in textos:
        try:
            img = driver.find_elements(By.CSS_SELECTOR, f'img[mattooltip*="{texto}"]')
            if img:
                if log:
                    print(f'[SELECTOR] Found by img[mattooltip]: {texto}')
                return img[0]
            img_alt = driver.find_elements(By.CSS_SELECTOR, f'img[alt*="{texto}"]')
            if img_alt:
                if log:
                    print(f'[SELECTOR] Found by img[alt]: {texto}')
                return img_alt[0]
            img_src = driver.find_elements(By.CSS_SELECTOR, f'img[src*="{texto}"]')
            if img_src:
                if log:
                    print(f'[SELECTOR] Found by img[src]: {texto}')
                return img_src[0]
            btn = driver.find_elements(By.CSS_SELECTOR, f'button[mattooltip*="{texto}"]')
            if btn:
                if log:
                    print(f'[SELECTOR] Found by button[mattooltip]: {texto}')
                return btn[0]
        except Exception:
            continue
    if log:
        print(f'[SELECTOR] No element found for: {textos}')
    return None