"""
PEC.anexos.juntador.metodos - Métodos da classe Juntador.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém os métodos específicos da classe Juntador (_escolher_opcao_gigs, etc.).
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import time
import types
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix import espera
from Fix.core import (
    safe_click_no_scroll,
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)

# Imports dos módulos refatorados
from .anexos_extracao import extrair_numero_processo_da_url
from .anexos_formatacao import formatar_conteudo_ecarta
from .anexos_juntador_helpers import substituir_marcador_por_conteudo


def _escolher_opcao_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa escolherOpcaoTeste do gigs-plugin.js"""
    try:
        driver = self.driver

        # 1. Encontra o campo (com espera — a aba /anexar recém-aberta é
        #    detectada pelo executar_juntada enquanto o Angular ainda não
        #    habilitou o formulário, e o find_element seco estourava na
        #    1ª tentativa, forçando o reload/retry)
        elementos_campo = espera.elementos(driver, seletor, teto=4)
        if not elementos_campo:
            print(f'[JUNTADA][ERRO] Campo {nome_campo} não apareceu a tempo')
            return False
        campo = elementos_campo[0]

        # 2. Clica no elemento pai para abrir dropdown (padrão GIGS)
        parent_element = campo.find_element(By.XPATH, '../..')
        safe_click_no_scroll(driver, parent_element)

        # 3. Aguarda opções aparecerem e clica na desejada
        espera.ate_aparecer(driver, "mat-option[role='option']", teto=3)
        opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")

        for opcao in opcoes:
            if valor.lower() in opcao.text.lower():
                safe_click_no_scroll(driver, opcao)
                print(f'[JUNTADA][DEBUG] {nome_campo} selecionado: {valor}')
                return True

        print(f'[JUNTADA][ERRO] Opção "{valor}" não encontrada em {nome_campo}')
        return False

    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha ao selecionar {nome_campo}: {e}')
        return False


def _preencher_input_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa preencherInput do gigs-plugin.js"""
    try:
        driver = self.driver

        # Encontra o elemento (com espera — mesma corrida de render da
        # 1ª abertura da aba /anexar que afetava _escolher_opcao_gigs)
        elementos_campo = espera.elementos(driver, seletor, teto=8)
        if not elementos_campo:
            logger.error(f'[JUNTADA][ERRO] Campo {nome_campo} não apareceu a tempo')
            return False
        campo = elementos_campo[0]

        # Implementa exatamente como no gigs-plugin.js usando JavaScript
        resultado = driver.execute_script("""
            const elemento = arguments[0];
            const valor = arguments[1];

            // Focus no elemento (JavaScript, não WebElement)
            elemento.focus();

            // Define valor usando Object.getOwnPropertyDescriptor (padrão GIGS)
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(elemento, valor);

            // Dispara eventos exatos do GIGS
            function triggerEvent(el, eventType) {
                const event = new Event(eventType, {bubbles: true, cancelable: true});
                el.dispatchEvent(event);
            }

            triggerEvent(elemento, 'input');
            triggerEvent(elemento, 'change');
            triggerEvent(elemento, 'dateChange');
            triggerEvent(elemento, 'keyup');

            // Simula Enter (padrão GIGS)
            const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
            elemento.dispatchEvent(enterEvent);

            // Blur no elemento
            elemento.blur();

            return true;
        """, campo, valor)

        return True

    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Falha ao preencher {nome_campo}: {e}')
        return False


def _clicar_elemento_gigs(self, seletor: str, nome_elemento: str) -> bool:
    """Implementa clicarBotao do gigs-plugin.js com múltiplas tentativas"""
    try:
        driver = self.driver

        # Lista de seletores alternativos para botão Salvar
        if 'Salvar' in nome_elemento:
            seletores = [
                'button[aria-label="Salvar"]',
                'button[mat-raised-button][color="primary"][aria-label="Salvar"]',
                'button.mat-raised-button.mat-primary[aria-label="Salvar"]',
                'button.mat-focus-indicator.mat-raised-button.mat-button-base.mat-primary[aria-label="Salvar"]',
                'button:contains("Salvar")',
                '[aria-label="Salvar"]'
            ]
        # Lista de seletores alternativos para botão Assinar
        elif 'Assinar' in nome_elemento:
            seletores = [
                'button[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-focus-indicator.mat-fab.mat-button-base.mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button[mat-fab].mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab .fa-pen-nib',
                'button:contains("Assinar")',
                '[aria-label*="Assinar"]'
            ]
        else:
            seletores = [seletor]

        for i, sel in enumerate(seletores):
            try:
                print(f'[JUNTADA][DEBUG] Tentando seletor {i + 1}: {sel}')

                # Tenta encontrar o elemento
                if ':contains(' in sel:
                    # Para seletores com :contains, usar JavaScript
                    elemento = driver.execute_script("""
                        const buttons = document.querySelectorAll('button');
                        return Array.from(buttons).find(btn =>
                            btn.textContent.trim().toLowerCase().includes('salvar') ||
                            btn.getAttribute('aria-label') === 'Salvar'
                        );
                    """)
                else:
                    elementos = driver.find_elements(By.CSS_SELECTOR, sel)
                    elemento = elementos[0] if elementos else None

                if elemento:
                    print(f'[JUNTADA][DEBUG] Elemento encontrado com seletor {i + 1}: {sel}')

                    # Tentativas de clique
                    for tentativa in range(2):
                        try:
                            # Scroll para o elemento
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)

                            # Verifica se elemento é clicável
                            if elemento.is_enabled() and elemento.is_displayed():
                                # Tenta clique JavaScript
                                safe_click_no_scroll(driver, elemento)
                                print(f'[JUNTADA][DEBUG] ✅ Clique realizado: {nome_elemento} (seletor {i+1}, tentativa {tentativa + 1})')
                                return True
                            else:
                                print(f'[JUNTADA][DEBUG] Elemento não clicável (enabled: {elemento.is_enabled()}, visible: {elemento.is_displayed()})')
                                espera.assentar(driver, 0.2)

                        except Exception as e:
                            if tentativa < 1:
                                print(f'[JUNTADA][DEBUG] Tentativa {tentativa + 1} falhou para {nome_elemento}: {e}')
                                espera.assentar(driver, 0.3)
                            else:
                                print(f'[JUNTADA][AVISO] Tentativas falharam para {nome_elemento} com seletor {sel}: {e}')
                else:
                    print(f'[JUNTADA][DEBUG] Elemento não encontrado com seletor {i + 1}: {sel}')

            except Exception as e:
                if i < len(seletores) - 1:  # Não é o último seletor
                    print(f'[JUNTADA][DEBUG] Seletor {i + 1} "{sel}" falhou: {e}')
                    continue
                else:
                    print(f'[JUNTADA][ERRO] Último seletor "{sel}" falhou: {e}')

        print(f'[JUNTADA][ERRO] Todos os seletores falharam para {nome_elemento}')
        return False

    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha geral ao clicar {nome_elemento}: {e}')
        return False


def _selecionar_modelo_gigs(self, modelo: str) -> bool:
    """Seleciona e insere o modelo exatamente como no aaDespacho e atos/judicial_fluxo.py.
    
    Sequência à prova de corrida:
    1. Preenche #inputFiltro e envia ENTER para expandir/destacar árvore do PJe.
    2. Clica no item .nodo-filtrado destacado.
    3. Aguarda diálogo <pje-dialogo-visualizar-modelo> entrar no DOM.
    4. GUARDA ANTI-CORRIDA (500ms): aguarda preview/teor carregar no diálogo
       (evita inserção de documento em branco).
    5. Clica no botão Inserir e aguarda diálogo sumir.
    6. Verificação REAL no CKEditor: aguarda até que o texto/marcador apareça
       de verdade na área editável antes de liberar o próximo passo.
    """
    try:
        driver = self.driver

        # 1) Preenche filtro via JS + envia ENTER
        campo_filtro_modelo = espera.elemento(driver, '#inputFiltro', teto=10)
        if not campo_filtro_modelo:
            logger.error('[JUNTADA][ERRO] Campo de filtro não encontrado')
            return False

        driver.execute_script('arguments[0].focus(); arguments[0].value = arguments[1];', campo_filtro_modelo, modelo)
        for ev in ['input', 'change', 'keyup']:
            driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
        try:
            campo_filtro_modelo.send_keys(Keys.ENTER)
        except Exception:
            driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));", campo_filtro_modelo)

        # 2) Clica no item destacado .nodo-filtrado
        seletor_item_filtrado = '.nodo-filtrado'
        if not espera.ate_aparecer(driver, seletor_item_filtrado, teto=10):
            logger.warning('[JUNTADA][MODELO] .nodo-filtrado não apareceu a tempo, tentando nodo genérico...')
            seletor_item_filtrado = 'mat-tree-node, .mat-tree-node'
            if not espera.ate_aparecer(driver, seletor_item_filtrado, teto=5):
                logger.error('[JUNTADA][ERRO] Nenhum item de modelo encontrado na árvore')
                return False

        nodos = driver.find_elements(By.CSS_SELECTOR, seletor_item_filtrado)
        if not nodos:
            logger.error('[JUNTADA][ERRO] Elemento do modelo não encontrado')
            return False
        nodo = nodos[0]
        driver.execute_script('arguments[0].scrollIntoView({block:"center"}); arguments[0].click();', nodo)
        logger.info('[JUNTADA][DEBUG] Clique no nodo do modelo realizado')

        # 3) O diálogo DEVE entrar no DOM antes do clique em Inserir (padrão atos/judicial_fluxo.py)
        if not espera.ate_aparecer(driver, 'pje-dialogo-visualizar-modelo', teto=8):
            logger.warning('[JUNTADA][MODELO] Diálogo pje-dialogo-visualizar-modelo não detectado de imediato, verificando botão...')

        # 4) GUARDA ANTI-CORRIDA ESSENCIAL: 500ms após o diálogo entrar no DOM,
        # para o preview/teor do modelo carregar e o botão Inserir ser ligado.
        # Clicar antes disso insere editor VAZIO!
        time.sleep(0.5)

        seletor_btn_inserir_aria = 'button[aria-label="Inserir modelo de documento"]'
        seletor_btn_inserir_css = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
        seletor_btn_inserir_fallback = 'pje-dialogo-visualizar-modelo button'

        btn_inserir = None
        for sel in [seletor_btn_inserir_aria, seletor_btn_inserir_css, seletor_btn_inserir_fallback]:
            btn_inserir = wait_for_clickable(driver, sel, timeout=3, by=By.CSS_SELECTOR)
            if btn_inserir:
                break

        if not btn_inserir:
            logger.error('[JUNTADA][ERRO] Botão Inserir modelo não encontrado!')
            return False

        driver.execute_script('arguments[0].click();', btn_inserir)
        logger.info('[JUNTADA][DEBUG] Clique em Inserir modelo realizado')

        # 5) Aguarda diálogo fechar
        espera.ate_sumir(driver, 'pje-dialogo-visualizar-modelo', teto=6)

        # 6) VERIFICAÇÃO REAL NO EDITOR: confirma que o conteúdo do modelo carregou
        # (texto útil > 20 caracteres ou marcador '--' ou tabela presente)
        js_editor_carregou = """
            var area = document.querySelector('.ck-editor__editable[contenteditable="true"]') ||
                       document.querySelector('div[class*="area-conteudo"][contenteditable="true"]');
            if (!area) return false;
            var txt = (area.innerText || area.textContent || '').replace(/\\s/g, '');
            var html = area.innerHTML || '';
            return html.includes('--') || txt.length > 20 || area.querySelector('table') !== null;
        """
        modelo_carregado = False
        for tentativa in range(15):
            try:
                if driver.execute_script(js_editor_carregou):
                    modelo_carregado = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if modelo_carregado:
            logger.info('[JUNTADA][DEBUG] Modelo inserido com sucesso (conteúdo confirmado no editor)')
            return True
        else:
            logger.error('[JUNTADA][ERRO] Modelo não carregou no editor após espera (editor vazio)')
            return False
    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Falha ao selecionar/inserir modelo: {e}')
        return False


def _executar_coleta_opcional(self, configuracao: Dict[str, Any]) -> bool:
    """Executa coleta de conteúdo se configurada."""
    coleta_conteudo = configuracao.get('coleta_conteudo')
    if not coleta_conteudo:
        return True  # Não é erro não ter coleta

    numero_processo_atual = extrair_numero_processo_da_url(self.driver)
    if not numero_processo_atual:
        print('[JUNTADA][COLETA][WARN] Número do processo não identificado')
        return True  # Não falha por não conseguir extrair número

    try:
        print(f'[JUNTADA][COLETA] Iniciando coleta: {coleta_conteudo} | processo: {numero_processo_atual}')
        executar_coleta_parametrizavel(self.driver, numero_processo_atual, coleta_conteudo, debug=True)
        return True
    except Exception as e:
        print(f'[JUNTADA][COLETA][WARN] Falha ao executar coleta opcional: {e}')
        return True  # Coleta opcional não deve falhar a juntada


def _preencher_tipo(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Tipo de Documento."""
    tipo = configuracao.get('tipo', 'Certidão')
    return self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento')


def _preencher_descricao(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Descrição."""
    descricao = configuracao.get('descricao', '')
    if not descricao:
        return True  # Descrição opcional
    return self._preencher_input_gigs('input[aria-label="Descrição"]', descricao, 'Descrição')


def _configurar_sigilo(self, configuracao: Dict[str, Any]) -> bool:
    """Configura sigilo se necessário."""
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        return self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo')
    return True  # Não é erro não configurar sigilo


def _selecionar_e_inserir_modelo(self, configuracao: Dict[str, Any]) -> bool:
    """Seleciona e insere modelo no editor."""
    modelo = configuracao.get('modelo', '')
    if not modelo:
        return True  # Modelo opcional
    return self._selecionar_modelo_gigs(modelo)


def _inserir_conteudo_customizado(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """Insere conteúdo customizado ou substitui link."""
    try:
        inserir_conteudo = configuracao.get('inserir_conteudo')
        if inserir_conteudo:
            inserir_fn = inserir_conteudo
            if isinstance(inserir_conteudo, str):
                try:
                    if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                        inserir_fn = inserir_link_ato_validacao
                except Exception as _e:
                    logger.warning(f"[JUNTADA][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")

            # Número do processo: priorizar dadosatuais.json (número CNJ) em vez de ID da URL
            numero_processo_atual = None
            try:
                import json
                from pathlib import Path
                dados_path = Path('dadosatuais.json')
                if dados_path.exists():
                    dados = json.loads(dados_path.read_text(encoding='utf-8'))
                    numero = dados.get('numero')
                    if isinstance(numero, list) and numero:
                        numero_processo_atual = numero[0]
                    elif isinstance(numero, str) and numero.strip():
                        numero_processo_atual = numero.strip()
            except Exception as e:
                logger.error(f'[JUNTADA][INSERIR][WARN] Erro ao ler dadosatuais.json: {e}')

            # Fallback: extrair da URL se não conseguiu do JSON
            if not numero_processo_atual:
                numero_processo_atual = extrair_numero_processo_da_url(self.driver)
                logger.warning(f'[JUNTADA][INSERIR][WARN] Usando ID da URL como fallback: {numero_processo_atual}')

            # Gate anti-atropelo: se já existe editor na página, só cola quando
            # o modelo estiver realmente presente no editor.
            editor_presente = espera.ate_aparecer(
                self.driver, '.ck-editor__editable[contenteditable=true]', teto=4
            )
            if editor_presente:
                conteudo_no_editor = (
                    "__pjeEls('.ck-editor__editable[contenteditable=true]').some("
                    "el => (el.innerHTML || '').includes('--') || ((el.textContent || '').trim().length > 20))"
                )
                if not espera.ate_js(self.driver, conteudo_no_editor, teto=10):
                    logger.error(
                        "[JUNTADA][INSERIR][ERRO] Conteúdo do modelo não chegou ao editor em 10s — "
                        "colagem abortada para não salvar documento incompleto."
                    )
                    return False

            ok = False
            try:
                ok = inserir_fn(driver=self.driver, numero_processo=numero_processo_atual, debug=True)
            except TypeError as te:
                try:
                    ok = inserir_fn(self.driver, numero_processo_atual)
                except Exception as e2:
                    try:
                        ok = inserir_fn(self.driver)
                    except Exception as e3:
                        logger.error(f"[JUNTADA][INSERIR][ERRO] Todas as tentativas de chamada falharam: {e3}")
                        return False

            if ok:
                espera.assentar(self.driver, 0.5, 'assentamento pos-insercao')
            return ok

        elif substituir_link:
            # Compat: caminho antigo de substituição
            espera.ate_js(
                self.driver,
                "typeof CKEDITOR !== 'undefined'"
                " && Object.keys(CKEDITOR.instances || {}).length > 0",
                teto=3,
            )
            if not substituir_marcador_por_conteudo(self.driver, debug=True):
                logger.error('[JUNTADA][ERRO] Falha na substituição do link!')
                return False
            espera.pausa(self.driver, 2, 'assentamento pos-substituicao no editor')
            return True

        return True  # Não é erro não ter conteúdo para inserir

    except Exception as e:
        logger.error(f"[JUNTADA][INSERIR][WARN] Erro durante inserção opcional: {e}")
        return False


def _salvar_documento(self) -> bool:
    """Salva documento com confirmação efetiva no PJe."""
    print('[JUNTADA] Salvando documento final...')
    if not self._clicar_elemento_gigs('button[aria-label="Salvar"]', 'Salvar documento'):
        print('[JUNTADA][ERRO] Falha no salvamento principal!')
        return False

    print('[JUNTADA] Aguardando processamento do salvamento...')
    # Confirmação via desabilitação temporária do botão ou snackbar do PJe
    desabilitou = espera.ate_desabilitar(self.driver, 'button[aria-label="Salvar"]', teto=5)

    js_snack_salvo = """
        var snack = document.querySelector('simple-snack-bar, snack-bar-container');
        if (snack) {
            var t = (snack.innerText || snack.textContent || '').toLowerCase();
            return t.includes('salv') || t.includes('sucesso');
        }
        return false;
    """
    snack_detectado = False
    for _ in range(8):
        try:
            if self.driver.execute_script(js_snack_salvo):
                snack_detectado = True
                break
        except Exception:
            pass
        time.sleep(0.3)

    if not snack_detectado and desabilitou:
        # Re-habilitação do botão após processamento
        espera.ate_habilitar(self.driver, 'button[aria-label="Salvar"]', teto=6)

    espera.assentar(self.driver, 0.8, 'pos-salvar juntada')
    print('[JUNTADA] Salvamento confirmado com sucesso.')
    return True


def _assinar_se_necessario(self, configuracao: Dict[str, Any]) -> bool:
    """Assina documento se configurado."""
    if configuracao.get('assinar', 'nao').lower() == 'sim':
        seletor_assinar = 'button[aria-label="Assinar documento e juntar ao processo"]'
        espera.ate_habilitar(self.driver, seletor_assinar, teto=3)
        return self._clicar_elemento_gigs(seletor_assinar, 'Assinar')
    return True  # Não é erro não assinar
