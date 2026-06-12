"""
PEC.anexos.juntador.metodos - Metodos da classe Juntador.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contem os metodos especificos da classe Juntador (_escolher_opcao_gigs, etc.).
"""

from Fix.log import logger

import os
import re
import time
import types
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
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

# Imports dos modulos refatorados
from .anexos_extracao import extrair_numero_processo_da_url
from .anexos_formatacao import formatar_conteudo_ecarta
from .anexos_juntador_helpers import substituir_marcador_por_conteudo


def _escolher_opcao_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa escolherOpcaoTeste do gigs-plugin.js"""
    try:
        driver = self.driver

        # 1. Encontra o campo
        campo = driver.find_element(By.CSS_SELECTOR, seletor)

        # 2. Clica no elemento pai para abrir dropdown (padrao GIGS)
        parent_element = campo.find_element(By.XPATH, '../..')
        driver.execute_script("arguments[0].click();", parent_element)
        aguardar_renderizacao_nativa(driver, "mat-option[role='option']", 'aparecer', 3)

        # 3. Aguarda opcoes aparecerem e clica na desejada
        wait = WebDriverWait(driver, 10)
        opcoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']")))

        for opcao in opcoes:
            if valor.lower() in opcao.text.lower():
                driver.execute_script("arguments[0].click();", opcao)
                logger.debug('[JUNTADA] %s selecionado: %s', nome_campo, valor)
                return True

        logger.error("ERRO em _escolher_opcao_gigs: Opcao \"%s\" nao encontrada em %s", valor, nome_campo)
        return False

    except Exception as e:
        logger.error("ERRO em _escolher_opcao_gigs: Falha ao selecionar %s: %s: %s", nome_campo, type(e).__name__, e)
        return False


def _preencher_input_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa preencherInput do gigs-plugin.js"""
    try:
        driver = self.driver

        # Encontra o elemento
        campo = driver.find_element(By.CSS_SELECTOR, seletor)

        # Implementa exatamente como no gigs-plugin.js usando JavaScript
        resultado = driver.execute_script("""
            const elemento = arguments[0];
            const valor = arguments[1];

            // Focus no elemento (JavaScript, nao WebElement)
            elemento.focus();

            // Define valor usando Object.getOwnPropertyDescriptor (padrao GIGS)
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

            // Simula Enter (padrao GIGS)
            const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
            elemento.dispatchEvent(enterEvent);

            // Blur no elemento
            elemento.blur();

            return true;
        """, campo, valor)

        return True

    except Exception as e:
        logger.error("ERRO em _preencher_input_gigs: Falha ao preencher %s: %s: %s", nome_campo, type(e).__name__, e)
        return False


def _clicar_elemento_gigs(self, seletor: str, nome_elemento: str) -> bool:
    """Implementa clicarBotao do gigs-plugin.js com script JS robusto (sem :contains)."""
    try:
        driver = self.driver
        # Script JS que localiza o botão por aria-label ou pelo texto, clica e retorna True/False
        if 'Salvar' in nome_elemento:
            script = """
                const btn = document.querySelector('button[aria-label="Salvar"], button.mat-raised-button.mat-primary');
                if (btn) { btn.click(); return true; }
                const allBtns = document.querySelectorAll('button');
                for (let b of allBtns) {
                    if (b.textContent.trim() === 'Salvar' || b.getAttribute('aria-label') === 'Salvar') {
                        b.click(); return true;
                    }
                }
                return false;
            """
        elif 'Assinar' in nome_elemento:
            script = """
                const btn = document.querySelector('button[aria-label="Assinar documento e juntar ao processo"], button.mat-fab.mat-accent');
                if (btn) { btn.click(); return true; }
                const allBtns = document.querySelectorAll('button');
                for (let b of allBtns) {
                    const label = b.getAttribute('aria-label') || '';
                    if (label.includes('Assinar') || b.textContent.trim().toLowerCase().includes('assinar')) {
                        b.click(); return true;
                    }
                }
                return false;
            """
        else:
            script = f"""
                const btn = document.querySelector('{seletor.replace("'", "\\'")}');
                if (btn) {{ btn.click(); return true; }}
                const allBtns = document.querySelectorAll('button');
                for (let b of allBtns) {{
                    const label = b.getAttribute('aria-label') || '';
                    if (label.includes('{nome_elemento}') || b.textContent.trim().toLowerCase().includes('{nome_elemento.lower()}')) {{
                        b.click(); return true;
                    }}
                }}
                return false;
            """

        resultado = driver.execute_script(script)
        if resultado:
            logger.debug('[JUNTADA] Clique realizado: %s', nome_elemento)
            return True
        else:
            logger.error("ERRO em _clicar_elemento_gigs: Botao nao encontrado: %s", nome_elemento)
            return False

    except Exception as e:
        logger.error("ERRO em _clicar_elemento_gigs: Falha ao clicar %s: %s: %s", nome_elemento, type(e).__name__, e)
        return False


def _selecionar_modelo_gigs(self, modelo: str) -> bool:
    """Seleciona e insere o modelo exatamente como em comunicacao_judicial (atos.py)."""
    try:
        driver = self.driver
        wait = WebDriverWait(driver, 15)

        # 1) Preenche filtro como em atos.py (focus + value + eventos + ENTER)
        campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo)
        for ev in ['input', 'change', 'keyup']:
            driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
        campo_filtro_modelo.send_keys(Keys.ENTER)

        # 2) Clica no item destacado .nodo-filtrado (sem fallback para evitar modelo errado)
        seletor_item_filtrado = '.nodo-filtrado'
        nodo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_item_filtrado)))
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', nodo)
        driver.execute_script('arguments[0].click();', nodo)

        # 3) Aguarda preview e localiza botao Inserir (seletor de atos.py)
        seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
        btn_inserir = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn_inserir)))
        aguardar_renderizacao_nativa(driver, seletor_btn_inserir, 'habilitado', 2)

        # 4) Inserir com clique JS (padrao comunicacao_preenchimento.py)
        driver.execute_script("arguments[0].click();", btn_inserir)

        # 5) Aguardar modelo ser aplicado no editor — essencial: valida que o conteúdo
        #    entrou antes de prosseguir para _inserir_conteudo_customizado/substituir_marcador.
        try:
            aguardar_renderizacao_nativa(driver, timeout=2)  # estabiliza Angular
        except Exception:
            pass
        try:
            WebDriverWait(driver, 8, poll_frequency=0.3).until(
                lambda d: bool(d.execute_script(
                    "var ed = document.querySelector('.ck-editor__editable[contenteditable=\"true\"]');"
                    "return ed && ed.innerText && ed.innerText.trim().length > 10;"
                ))
            )
        except Exception:
            logger.warning('[JUNTADA][MODELO] Timeout aguardando conteúdo no editor — prosseguindo assim mesmo')
        return True
    except Exception as e:
        logger.error("ERRO em _selecionar_modelo_gigs: Falha ao selecionar/inserir modelo (modo atos.py): %s: %s", type(e).__name__, e)
        return False


def _executar_coleta_opcional(self, configuracao: Dict[str, Any]) -> bool:
    """Executa coleta de conteudo se configurada."""
    coleta_conteudo = configuracao.get('coleta_conteudo')
    if not coleta_conteudo:
        return True  # Nao e erro nao ter coleta

    numero_processo_atual = extrair_numero_processo_da_url(self.driver)
    if not numero_processo_atual:
        logger.warning('[JUNTADA][COLETA] Numero do processo nao identificado')
        return True  # Nao falha por nao conseguir extrair numero

    try:
        logger.debug('[JUNTADA][COLETA] Iniciando coleta: %s | processo: %s', coleta_conteudo, numero_processo_atual)
        executar_coleta_parametrizavel(self.driver, numero_processo_atual, coleta_conteudo, debug=True)
        return True
    except Exception as e:
        logger.warning('[JUNTADA][COLETA] Falha ao executar coleta opcional: %s', e)
        return True  # Coleta opcional nao deve falhar a juntada


def _preencher_tipo(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Tipo de Documento."""
    tipo = configuracao.get('tipo', 'Certidao')
    seletores = [
        'input[data-placeholder="Tipo de Documento"]',
        'input[aria-label="Tipo de Documento"]',
        'input[formcontrolname="tipoDocumento"]'
    ]
    for sel in seletores:
        try:
            if self.driver.find_elements(By.CSS_SELECTOR, sel):
                if self._escolher_opcao_gigs(sel, tipo, 'Tipo de Documento'):
                    return True
        except Exception:
            continue
    
    # Fallback pro comportamento original se nenhum dos anteriores der match
    return self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento')


def _preencher_descricao(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Descricao."""
    descricao = configuracao.get('descricao', '')
    if not descricao:
        return True  # Descricao opcional

    seletores = [
        'input[aria-label="Descrição"]',
        'input[aria-label="Descricao"]',
    ]
    for seletor in seletores:
        if self.driver.find_elements(By.CSS_SELECTOR, seletor):
            return self._preencher_input_gigs(seletor, descricao, 'Descricao')

    logger.error('[JUNTADA] Campo Descricao nao encontrado para preenchimento automatico')
    return False


def _configurar_sigilo(self, configuracao: Dict[str, Any]) -> bool:
    """Configura sigilo se necessario."""
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        return self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo')
    return True  # Nao e erro nao configurar sigilo


def _selecionar_e_inserir_modelo(self, configuracao: Dict[str, Any]) -> bool:
    """Seleciona e insere modelo no editor."""
    modelo = configuracao.get('modelo', '')
    if not modelo:
        return True  # Modelo opcional
    return self._selecionar_modelo_gigs(modelo)


def _inserir_conteudo_customizado(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """Insere conteudo customizado ou substitui link."""
    try:
        inserir_conteudo = configuracao.get('inserir_conteudo')
        if inserir_conteudo:
            inserir_fn = inserir_conteudo
            if isinstance(inserir_conteudo, str):
                try:
                    if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                        inserir_fn = inserir_link_ato_validacao
                except Exception as _e:
                    logger.warning('[JUNTADA][INSERIR] Nao foi possivel resolver funcao por string: %s -> %s', inserir_conteudo, _e)

            # Numero do processo: priorizar dadosatuais.json (numero CNJ) em vez de ID da URL
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
                logger.error("ERRO em _inserir_conteudo_customizado: Erro ao ler dadosatuais.json: %s: %s", type(e).__name__, e)

            # Fallback: extrair da URL se nao conseguiu do JSON
            if not numero_processo_atual:
                numero_processo_atual = extrair_numero_processo_da_url(self.driver)
                logger.warning('[JUNTADA][INSERIR] Usando ID da URL como fallback: %s', numero_processo_atual)

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
                        logger.error("ERRO em _inserir_conteudo_customizado: Todas as tentativas de chamada falharam: %s: %s", type(e3).__name__, e3)
                        return False

            # Aguarda a modificação no editor (marcador substituído) se for substituir_link
            if ok and substituir_link:
                try:
                    WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                        lambda d: '--' not in (d.execute_script(
                            "return document.querySelector('[contenteditable=true]')?.innerHTML || ''"))
                    )
                except Exception:
                    pass
            return ok

        elif substituir_link:
            # Compat: caminho antigo de substituicao
            try:
                WebDriverWait(self.driver, 5).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            except Exception:
                pass
            if not substituir_marcador_por_conteudo(self.driver, debug=True):
                logger.error("ERRO em _inserir_conteudo_customizado: Falha na substituicao do link")
                return False
            try:
                WebDriverWait(self.driver, 3).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            except Exception:
                pass
            return True

        return True  # Nao e erro nao ter conteudo para inserir

    except Exception as e:
        logger.error("ERRO em _inserir_conteudo_customizado: Erro durante insercao opcional: %s: %s", type(e).__name__, e)
        return False


def _salvar_documento(self) -> bool:
    """Salva documento e aguarda confirmação visual."""
    logger.info('[JUNTADA] Salvando documento final...')
    if not self._clicar_elemento_gigs('button[aria-label="Salvar"]', 'Salvar documento'):
        logger.error("ERRO em _salvar_documento: Falha no clique do botão Salvar")
        return False

    # Aguarda confirmação visual do salvamento (snackbar ou botão desabilitado)
    try:
        WebDriverWait(self.driver, 10, poll_frequency=0.5).until(
            lambda d: d.execute_script("""
                const snack = document.querySelector('simple-snack-bar');
                if (snack && snack.textContent.toLowerCase().includes('salv')) return true;
                const btn = document.querySelector('button[aria-label="Salvar"]');
                return !btn || btn.disabled;
            """)
        )
        logger.info('[JUNTADA] Salvamento confirmado pela interface.')
    except Exception:
        logger.warning('[JUNTADA] Não foi detectada confirmação visual do salvamento, mas prosseguindo')

    return True


def _assinar_se_necessario(self, configuracao: Dict[str, Any]) -> bool:
    """Assina documento se configurado."""
    if configuracao.get('assinar', 'nao').lower() == 'sim':
        try:
            WebDriverWait(self.driver, 5).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            pass
        return self._clicar_elemento_gigs('button[aria-label="Assinar documento e juntar ao processo"]', 'Assinar')
    return True  # Nao e erro nao assinar
