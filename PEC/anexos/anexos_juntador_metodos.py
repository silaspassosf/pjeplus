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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
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


def _escolher_opcao_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa escolherOpcaoTeste do gigs-plugin.js"""
    try:
        driver = self.driver

        # 1. Encontra o campo
        campo = driver.find_element(By.CSS_SELECTOR, seletor)

        # 2. Clica no elemento pai para abrir dropdown (padrão GIGS)
        parent_element = campo.find_element(By.XPATH, '../..')
        driver.execute_script("arguments[0].click();", parent_element)
        time.sleep(1)

        # 3. Aguarda opções aparecerem e clica na desejada
        wait = WebDriverWait(driver, 10)
        opcoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']")))

        for opcao in opcoes:
            if valor.lower() in opcao.text.lower():
                driver.execute_script("arguments[0].click();", opcao)
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

        # Encontra o elemento
        campo = driver.find_element(By.CSS_SELECTOR, seletor)

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

                    # Múltiplas tentativas de clique
                    for tentativa in range(3):
                        try:
                            # Scroll para o elemento
                            driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                            time.sleep(0.5)

                            # Verifica se elemento é clicável
                            if elemento.is_enabled() and elemento.is_displayed():
                                # Tenta clique JavaScript
                                driver.execute_script("arguments[0].click();", elemento)
                                print(f'[JUNTADA][DEBUG] ✅ Clique realizado: {nome_elemento} (seletor {i+1}, tentativa {tentativa + 1})')
                                return True
                            else:
                                print(f'[JUNTADA][DEBUG] Elemento não clicável (enabled: {elemento.is_enabled()}, visible: {elemento.is_displayed()})')

                        except Exception as e:
                            if tentativa < 2:  # Não é a última tentativa
                                print(f'[JUNTADA][DEBUG] Tentativa {tentativa + 1} falhou para {nome_elemento}: {e}')
                                time.sleep(1)
                            else:
                                print(f'[JUNTADA][AVISO] Todas as tentativas falharam para {nome_elemento} com seletor {sel}: {e}')
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

        # 3) Aguarda preview e localiza botão Inserir (seletor de atos.py)
        seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
        btn_inserir = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn_inserir)))
        time.sleep(0.6)

        # 4) Inserir com tecla ESPAÇO (padrão MaisPje)
        btn_inserir.send_keys(Keys.SPACE)

        # 5) Pequeno aguardo para o editor receber o conteúdo
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Falha ao selecionar/inserir modelo (modo atos.py): {e}')
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

            return ok

        elif substituir_link:
            # Compat: caminho antigo de substituição
            time.sleep(3)
            if not substituir_marcador_por_conteudo(self.driver, debug=True):
                logger.error('[JUNTADA][ERRO] Falha na substituição do link!')
                return False
            time.sleep(2)
            return True

        return True  # Não é erro não ter conteúdo para inserir

    except Exception as e:
        logger.error(f"[JUNTADA][INSERIR][WARN] Erro durante inserção opcional: {e}")
        return False


def _salvar_documento(self) -> bool:
    """Salva documento com retry."""
    print('[JUNTADA] Salvando documento final...')
    if not self._clicar_elemento_gigs('button[aria-label="Salvar"]', 'Salvar documento'):
        print('[JUNTADA][ERRO] Falha no salvamento principal!')
        return False

    # Aguardar processamento
    print('[JUNTADA] Aguardando processamento do salvamento...')
    time.sleep(2)

    # Verificar se salvamento foi efetivo
    try:
        salvar_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
        if salvar_btn.is_enabled():
            print('[JUNTADA][WARN] Documento ainda não salvo, tentando novamente...')
            self.driver.execute_script("arguments[0].click();", salvar_btn)
            time.sleep(2)
    except:
        print('[JUNTADA][INFO] Botão Salvar não disponível - documento já salvo')

    return True


def _assinar_se_necessario(self, configuracao: Dict[str, Any]) -> bool:
    """Assina documento se configurado."""
    if configuracao.get('assinar', 'nao').lower() == 'sim':
        time.sleep(3)
        return self._clicar_elemento_gigs('button[aria-label="Assinar documento e juntar ao processo"]', 'Assinar')
    return True  # Não é erro não assinar