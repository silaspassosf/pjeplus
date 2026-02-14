"""
PEC.anexos.juntador.helpers - Helpers de decomposição para juntada.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém helpers para executar_juntada_ate_editor e substituir_marcador_por_conteudo.
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


def _abrir_interface_anexacao(self) -> bool:
    """Abre a interface de anexação de documentos."""
    driver = self.driver
    print('[JUNTADA][DEBUG] Abrindo interface de anexação...')

    # 1. Clique no menu (ícone hambúrguer)
    print('[JUNTADA][DEBUG] Clicando no menu hambúrguer...')
    if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hambúrguer'):
        return False
    time.sleep(1)

    # 2. Clique em "Anexar Documentos"
    print('[JUNTADA][DEBUG] Clicando em "Anexar documentos"...')
    if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
        return False
    time.sleep(2)

    # 3. Aguarda nova aba/janela e muda para ela
    print('[JUNTADA][DEBUG] Mudando para aba de anexação...')
    all_windows = driver.window_handles
    if len(all_windows) > 1:
        driver.switch_to.window(all_windows[-1])
        if not wait_for_visible(driver, '/anexar', 'URL de anexação'):
            print('[JUNTADA][AVISO] URL não contém /anexar, mas prosseguindo...')
    else:
        print('[JUNTADA][DEBUG] Nova aba não detectada, prosseguindo na mesma aba...')

    time.sleep(3)
    return True


def _preencher_campos_basicos(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche os campos básicos: tipo, descrição e sigilo."""
    driver = self.driver
    # Tipo de Documento
    tipo = configuracao.get('tipo', 'Certidão')
    if not selecionar_opcao(driver, 'input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
        return False

    # Descrição
    descricao = configuracao.get('descricao', '')
    if descricao:
        if not preencher_campo(driver, 'input[aria-label="Descrição"]', descricao, 'Descrição'):
            return False

    # Sigilo
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        if not aguardar_e_clicar(driver, 'input[name="sigiloso"]', 'Sigilo'):
            return False

    return True


def _inserir_modelo(self, configuracao: Dict[str, Any]) -> bool:
    """Insere o modelo no editor e verifica se foi carregado."""
    driver = self.driver
    modelo_original = configuracao.get('modelo', '')
    if modelo_original:
        print(f'[JUNTADA][DEBUG] Selecionando e inserindo modelo: {modelo_original}')
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        print('[JUNTADA][DEBUG] Aguardando modelo ser inserido no editor...')
        time.sleep(3)

    print('[JUNTADA][DEBUG] Verificando se editor está disponível após inserção do modelo...')

    seletores_editor = [
        'div[aria-label="Conteúdo principal. Alt+F10 para acessar a barra de tarefas"].area-conteudo.ck.ck-content.ck-editor__editable',
        '.area-conteudo.ck.ck-content.ck-editor__editable.ck-rounded-corners.ck-editor__editable_inline',
        '.area-conteudo.ck-editor__editable[contenteditable="true"]',
        '.ck-editor__editable[contenteditable="true"]',
        'div.fr-element[contenteditable="true"]',
        '[contenteditable="true"]'
    ]

    editor_encontrado = None
    for i, seletor in enumerate(seletores_editor):
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            print(f'[JUNTADA][DEBUG] Seletor {i+1} "{seletor}": {len(elementos)} elementos')
            if elementos:
                editor_encontrado = elementos[0]
                print(f'[JUNTADA][DEBUG] ✓ Editor encontrado com seletor: {seletor}')
                print(f'[JUNTADA][DEBUG] Editor visível: {editor_encontrado.is_displayed()}')
                print(f'[JUNTADA][DEBUG] Editor habilitado: {editor_encontrado.is_enabled()}')
                conteudo = editor_encontrado.get_attribute('innerHTML')
                print(f'[JUNTADA][DEBUG] Conteúdo do editor (primeiros 200 chars): {conteudo[:200]}...')
                if 'marker-yellow' in conteudo and 'link' in conteudo:
                    print('[JUNTADA][DEBUG] ✓ Editor contém termo "link" marcado em amarelo!')
                elif conteudo.strip() and len(conteudo) > 100:
                    print('[JUNTADA][DEBUG] ✓ Editor contém conteúdo do modelo inserido')
                else:
                    print('[JUNTADA][AVISO] Editor parece vazio - modelo pode não ter sido inserido')
                break
        except Exception as e:
            print(f'[JUNTADA][DEBUG] Erro com seletor {i+1}: {e}')
            continue

    if not editor_encontrado:
        print('[JUNTADA][ERRO] Nenhum editor encontrado com os seletores disponíveis!')
        return False

    print('[JUNTADA][DEBUG] ✓ Editor disponível para manipulação')
    return True


def substituir_marcador_por_conteudo(driver, conteudo_customizado: Optional[str] = None, debug: bool = True, marcador: str = "--") -> bool:
    """
    Função melhorada para localizar marcador (ex: "--") e colar conteúdo após ele.
    Usa a mesma lógica robusta do editor_insert.py para maior compatibilidade.
    Simula ação manual: clique no final da linha + Ctrl+V
    Args:
        driver: Selenium WebDriver
        debug: Se deve exibir logs
        conteudo_customizado: Conteúdo específico para usar (se None, usa clipboard/arquivo)
        marcador: Texto a ser localizado (padrão: "--")
    """
    if debug:
        print(f"[SUBST_MARCADOR] Iniciando colagem após marcador '{marcador}'...")

    try:
        # 1. Determina qual conteúdo usar
        conteudo_para_usar = None
        fonte_conteudo = ""

        if conteudo_customizado:
            conteudo_para_usar = conteudo_customizado
            fonte_conteudo = "conteudo_customizado"
            if debug:
                print(f"[SUBST_MARCADOR] Usando conteúdo customizado: {len(conteudo_customizado)} chars")
        else:
            # Carrega conteúdo do clipboard/arquivo
            def carregar_clipboard_arquivo():
                try:
                    # Procurar clipboard.txt na pasta PEC
                    clipboard_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipboard.txt")
                    if os.path.exists(clipboard_file):
                        with open(clipboard_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        if debug:
                            print(f"[SUBST_MARCADOR] Carregado do arquivo: {len(content)} chars")
                        return content
                    return None
                except Exception as e:
                    if debug:
                        print(f"[SUBST_MARCADOR] Erro ao carregar arquivo: {e}")
                    return None

            conteudo_para_usar = carregar_clipboard_arquivo()
            fonte_conteudo = "clipboard_arquivo"

        if not conteudo_para_usar:
            print("[SUBST_MARCADOR] ✗ Nenhum conteúdo disponível para colar")
            return False

        # 2. Usar a lógica robusta do editor_insert.py
        # IMPORTANTE: Esta é uma adaptação da função inserir_html_no_editor_apos_marcador
        # que funciona muito melhor que o JavaScript inline anterior

        # Primeiro, encontrar o editor
        sels = [
            '.ck-editor__editable[contenteditable="true"]',
            '.ck-content[contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"]',
        ]

        editable = None
        for sel in sels:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el and el.is_displayed() and el.is_enabled():
                    editable = el
                    if debug:
                        print(f"[SUBST_MARCADOR] Editor encontrado por seletor: {sel}")
                    break
            except Exception:
                continue

        if not editable:
            print("[SUBST_MARCADOR] ✗ Editor CKEditor não encontrado na página")
            return False

        # Foco e rolagem
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        # Limpar caracteres problemáticos e escapar para JavaScript
        html_content_clean = (conteudo_para_usar
                             .replace('\x00', '')  # Remove null bytes
                             .replace('\r', '')    # Remove carriage returns
                             .strip())             # Remove espaços extras

        # Escape mais robusto para JavaScript - evita problemas com innerHTML
        html_escaped = (html_content_clean
                       .replace('\\', '\\\\')      # Escape backslashes primeiro
                       .replace('`', '\\`')        # Escape backticks (template literals)
                       .replace('$', '\\$')        # Escape dollar signs (template literals)
                       .replace('"', '\\"')        # Escape aspas duplas
                       .replace('\n', '\\n')       # Escape quebras de linha
                       .replace('\t', '\\t'))      # Escape tabs

        # Escape do marcador de forma similar
        marcador_escaped = (marcador
                           .replace('\\', '\\\\')
                           .replace('`', '\\`')
                           .replace('$', '\\$')
                           .replace('"', '\\"')
                           .replace('\n', '\\n'))

        # DEPURAÇÃO REAL - verificar HTML antes da execução
        html_antes = driver.execute_script("return arguments[0].innerHTML;", editable)
        texto_antes = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", editable)
        print(f"[DEBUG] HTML ANTES: {html_antes}")
        print(f"[DEBUG] TEXTO ANTES: {texto_antes}")
        print(f"[DEBUG] Contém marcador '{marcador}' no HTML? {marcador in html_antes}")
        print(f"[DEBUG] Contém marcador '{marcador}' no TEXTO? {marcador in texto_antes}")

        # IMPLEMENTAÇÃO ROBUSTA BASEADA NO editor_insert.py
        script_ckeditor = f"""
        console.log('[SUBST_MARCADOR] === USANDO LÓGICA ROBUSTA DO EDITOR_INSERT ===');

        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = arguments[2];
        let fonte = arguments[3];

        try {{
            // 1. Tentar encontrar a instância do CKEditor
            let ckInstance = null;

            // Método 1: Via elemento pai
            if (editor.ckeditorInstance) {{
                ckInstance = editor.ckeditorInstance;
                console.log('[SUBST_MARCADOR] ✓ CKEditor via ckeditorInstance');
            }}

            // Método 2: Via global CKEDITOR
            if (!ckInstance && window.CKEDITOR) {{
                for (let instanceName in window.CKEDITOR.instances) {{
                    let instance = window.CKEDITOR.instances[instanceName];
                    if (instance.element && instance.element.$ === editor) {{
                        ckInstance = instance;
                        console.log('[SUBST_MARCADOR] ✓ CKEditor via CKEDITOR.instances');
                        break;
                    }}
                }}
            }}

            // Método 3: Via CKEditor 5 (novo)
            if (!ckInstance) {{
                let ckEditor = editor.closest('.ck-editor');
                if (ckEditor && ckEditor.ckeditorInstance) {{
                    ckInstance = ckEditor.ckeditorInstance;
                    console.log('[SUBST_MARCADOR] ✓ CKEditor 5 via closest');
                }}
            }}

            if (ckInstance) {{
                console.log('[SUBST_MARCADOR] Usando API CKEditor');
                let htmlOriginal = ckInstance.getData();
                console.log('[SUBST_MARCADOR] HTML via getData:', htmlOriginal.substring(0, 100));

                if (htmlOriginal.includes(marcador)) {{
                    // TENTATIVA: Usar insertHtml se disponível, senão setData
                    if (ckInstance.insertHtml) {{
                        console.log('[SUBST_MARCADOR] Tentando insertHtml para preservar formatação...');
                        // Primeiro posicionar cursor no marcador de forma simples
                        let pos = htmlOriginal.indexOf(marcador);
                        if (pos !== -1) {{
                            // Calcular posição aproximada e tentar inserir
                            ckInstance.insertHtml(htmlContent, 'unfiltered_html');
                            console.log('[SUBST_MARCADOR] ✓ insertHtml usado');
                            return {{ sucesso: true, metodo: 'ckeditor_insertHtml' }};
                        }}
                    }}

                    // Fallback: setData original
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    ckInstance.setData(novoHtml);
                    console.log('[SUBST_MARCADOR] ✓ setData() executado');
                    return {{ sucesso: true, metodo: 'ckeditor_api' }};
                }} else {{
                    console.error('[SUBST_MARCADOR] Marcador não encontrado via API');
                }}
            }} else {{
                console.log('[SUBST_MARCADOR] CKEditor API não encontrada, usando DOM direto');

                // Fallback: DOM direto com foco
                editor.focus();

                let htmlOriginal = editor.innerHTML;
                if (htmlOriginal.includes(marcador)) {{
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    editor.innerHTML = novoHtml;

                    // Forçar eventos de mudança
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('keyup', {{ bubbles: true }}));

                    // Forçar blur/focus para CKEditor detectar
                    editor.blur();
                    setTimeout(() => editor.focus(), 10);

                    console.log('[SUBST_MARCADOR] ✓ DOM direto + eventos');
                    return {{ sucesso: true, metodo: 'dom_direto_com_eventos' }};
                }}
            }}

            return {{ sucesso: false, erro: 'Nenhum método funcionou' }};

        }} catch (e) {{
            console.error('[SUBST_MARCADOR] Erro:', e);
            return {{ sucesso: false, erro: e.message }};
        }}
        """

        # Executar o script com API do CKEditor
        resultado = driver.execute_script(script_ckeditor, editable, html_content_clean, marcador, fonte_conteudo)

        # Em vez de sleeps fixes, aguardar até que o HTML seja atualizado ou o marcador seja removido
        try:
            def _condicao_html(drv):
                try:
                    cur = drv.execute_script("return arguments[0].innerHTML;", editable) or ''
                    # Se o HTML já contém o conteúdo que inserimos, considerar sucesso
                    if html_content_clean in cur:
                        return True
                    # Ou se o marcador foi removido, também considerar sucesso
                    if marcador not in cur:
                        return True
                    return False
                except Exception:
                    return False

            WebDriverWait(driver, 3, poll_frequency=0.2).until(_condicao_html)
        except Exception:
            # Timeout expirado sem detectar alteração significativa
            if debug:
                try:
                    html_depois = driver.execute_script("return arguments[0].innerHTML;", editable)
                    print(f"[DEBUG] HTML DEPOIS (partial): {html_depois[:300]}")
                except Exception:
                    print('[DEBUG] Não foi possível ler HTML DEPOIS')

        if debug:
            print(f"[SUBST_MARCADOR] Resultado do script: {resultado}")

        if resultado and isinstance(resultado, dict) and resultado.get('sucesso'):
            if debug:
                print(f'[SUBST_MARCADOR] ✅ HTML inserido com sucesso via método: {resultado.get("metodo")}')

            # Verificar se marcador foi removido (apenas para log)
            try:
                html_final = driver.execute_script("return arguments[0].innerHTML;", editable)
                marcador_removido = marcador not in (html_final or '')
            except Exception:
                marcador_removido = False

            if debug:
                print(f'[SUBST_MARCADOR] Verificação final: marcador removido = {marcador_removido}')

            return True
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado and isinstance(resultado, dict) else 'Script retornou None ou formato inesperado'
            if debug:
                print(f'[SUBST_MARCADOR] ❌ Falha na inserção: {erro}')
            return False

    except Exception as e:
        if debug:
            print(f"[SUBST_MARCADOR] ✗ Erro geral: {e}")
        return False