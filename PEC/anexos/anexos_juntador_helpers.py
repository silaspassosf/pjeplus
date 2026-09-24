"""
PEC.anexos.juntador.helpers - Helpers de decomposição para juntada.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém helpers para executar_juntada_ate_editor e substituir_marcador_por_conteudo.
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import types
from typing import Optional, Dict, Any, Callable, Union, List


def _executar_js(driver: Any, script: str, *args):
    """Executa script JS de forma compatível sem invocar padrão regex."""
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
    esperar_url_conter,
)
from Fix.browser_suporte import aguardar_nova_aba, abrir_url_nova_aba
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)
from Fix import espera
# NOTA: substituir_marcador_por_conteudo NÃO é importado de Fix.utils
# (causaria recursão infinita: Fix.utils → helpers → Fix.utils).
# A implementação real está definida localmente abaixo.


def _abrir_interface_anexacao(self: types.SimpleNamespace) -> bool:
    """Abre a interface de anexação de documentos.

    Estratégia sem corrida:
    1. Se a aba atual já for /anexar, ou se outra aba aberta já for /anexar,
       foca nela diretamente sem abrir abas duplicadas.
    2. Se não estiver aberta, abre via JS (window.open direto para /documento/anexar)
       ou menu hambúrguer, registrando os handles anteriores para detectar
       estritamente o NOVO handle (evitando chavear indevidamente para a aba do Painel).
    3. Aguarda prontidão de input[aria-label="Tipo de Documento"].
    """
    driver = self.driver
    print('[JUNTADA][DEBUG] Abrindo interface de anexação...')

    # 0. Já estamos na página de anexação?
    try:
        if '/anexar' in (driver.current_url or ''):
            print('[JUNTADA][DEBUG] Já na interface de anexação, prosseguindo...')
            espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=4)
            return True
    except Exception:
        pass

    # Verifica se outra aba já aberta no navegador é /anexar
    aba_atual = getattr(driver, 'current_window_handle', None)
    handles = list(getattr(driver, 'window_handles', []))
    for h in handles:
        if h == aba_atual:
            continue
        try:
            driver.switch_to.window(h)
            if '/anexar' in (driver.current_url or ''):
                print(f'[JUNTADA][DEBUG] Aba /anexar já existente detectada: {h}')
                espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=4)
                return True
        except Exception:
            continue

    # Retorna o foco para a aba de origem
    try:
        if aba_atual:
            driver.switch_to.window(aba_atual)
    except Exception:
        pass

    # 1. Obter lista de handles antes de abrir
    handles_antes = set(getattr(driver, 'window_handles', []))
    handle_original = aba_atual

    # 2. Estratégia de Abertura: URL direta para /documento/anexar ou clique no menu
    try:
        url_atual = driver.current_url or ''
        match = re.search(r'/processo/(\d+)', url_atual)
        if match:
            id_processo = match.group(1)
            url_anexar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/documento/anexar"
            print(f'[JUNTADA][DEBUG] ID do processo detectado ({id_processo}). Abrindo /documento/anexar diretamente via JS...')
            abrir_url_nova_aba(driver, url_anexar)
        else:
            print('[JUNTADA][DEBUG] ID não encontrado na URL. Clicando no menu hambúrguer...')
            if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hambúrguer'):
                _executar_js(driver, "document.querySelector('i.fa-bars.icone-botao-menu')?.click();")
            espera.assentar(driver, 0.3)
            if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
                _executar_js(driver, "document.querySelector('button[aria-label=\"Anexar Documentos\"]')?.click();")
    except Exception as e:
        print(f'[JUNTADA][DEBUG] Falha na abertura da interface: {e}')

    # 3. Se ainda não estiver em /anexar, aguarda novo handle aparecer
    if '/anexar' not in (driver.current_url or ''):
        print('[JUNTADA][DEBUG] Mudando para aba de anexação...')
        nova_aba = None
        for _ in range(30):
            novas = set(getattr(driver, 'window_handles', [])) - handles_antes
            if novas:
                nova_aba = list(novas)[0]
                break
            espera.pausa(driver, 0.2)

        if nova_aba:
            driver.switch_to.window(nova_aba)
        else:
            # Fallback de segurança: busca qualquer handle que contenha /anexar
            for h in getattr(driver, 'window_handles', []):
                try:
                    driver.switch_to.window(h)
                    if '/anexar' in (driver.current_url or ''):
                        nova_aba = h
                        break
                except Exception:
                    continue
            if not nova_aba and handle_original:
                driver.switch_to.window(handle_original)
                print('[JUNTADA][AVISO] Nova aba /anexar não detectada, prosseguindo na aba atual...')

    # 4. Confirma URL /anexar e aguarda prontidão do formulário
    espera.ate_url(driver, '/anexar', teto=6)
    espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=8)
    return True


def _preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
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


def _inserir_modelo(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Insere o modelo no editor e verifica se foi carregado."""
    driver = self.driver
    modelo_original = configuracao.get('modelo', '')
    if modelo_original:
        print(f'[JUNTADA][DEBUG] Selecionando e inserindo modelo: {modelo_original}')
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        print('[JUNTADA][DEBUG] Aguardando modelo ser inserido no editor...')
        aguardar_renderizacao_nativa(driver, '[contenteditable="true"]', 'aparecer', 5)

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
            elementos = espera.elementos(driver, seletor, teto=1)
            print(f'[JUNTADA][DEBUG] Seletor {i+1} "{seletor}": {len(elementos)} elementos')
            if elementos:
                editor_encontrado = elementos[0]
                is_displayed = getattr(editor_encontrado, 'is_displayed', None)
                is_enabled = getattr(editor_encontrado, 'is_enabled', None)
                print(f'[JUNTADA][DEBUG] ✓ Editor encontrado com seletor: {seletor}')
                print(f'[JUNTADA][DEBUG] Editor visível: {is_displayed() if callable(is_displayed) else True}')
                print(f'[JUNTADA][DEBUG] Editor habilitado: {is_enabled() if callable(is_enabled) else True}')
                conteudo = _executar_js(driver, "return arguments[0].innerHTML || '';", editor_encontrado) or ''
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


# ═══════════════════════════════════════════════════════════════
# substituir_marcador_por_conteudo — IMPLEMENTAÇÃO REAL
# (NÃO importar de Fix.utils — causaria recursão infinita)
# ═══════════════════════════════════════════════════════════════

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

        # 2. Encontrar o editor CKEditor
        sels = [
            'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]',
            '.ck-editor__editable[contenteditable="true"]',
            '.ck-content[contenteditable="true"]',
        ]

        editable = None
        for sel in sels:
            try:
                el = espera.elemento(driver, sel, teto=2)
                if el:
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
        _executar_js(driver, 'arguments[0].scrollIntoView({block:"center"});', editable)
        espera.assentar(driver, 0.2)
        try:
            editable.click()
        except Exception:
            _executar_js(driver, 'arguments[0].focus();', editable)
        espera.assentar(driver, 0.1)

        # Limpar caracteres problemáticos e escapar para JavaScript
        html_content_clean = (conteudo_para_usar
                             .replace('\x00', '')
                             .replace('\r', '')
                             .strip())

        html_escaped = (html_content_clean
                       .replace('\\', '\\\\')
                       .replace('`', '\\`')
                       .replace('$', '\\$')
                       .replace('"', '\\"')
                       .replace('\n', '\\n')
                       .replace('\t', '\\t'))

        marcador_escaped = (marcador
                           .replace('\\', '\\\\')
                           .replace('`', '\\`')
                           .replace('$', '\\$')
                           .replace('"', '\\"')
                           .replace('\n', '\\n'))

        # DEPURAÇÃO - verificar HTML antes da execução
        html_antes = _executar_js(driver, "return arguments[0].innerHTML || '';", editable) or ''
        texto_antes = _executar_js(driver, "return arguments[0].innerText || arguments[0].textContent || '';", editable) or ''

        # Se o marcador não estiver de imediato, aguarda até 6s pelo carregamento do modelo no CKEditor
        if marcador not in html_antes and marcador not in texto_antes:
            if debug:
                print(f"[SUBST_MARCADOR] Marcador '{marcador}' não detectado de imediato, aguardando carga do editor...")
            for _ in range(12):
                espera.assentar(driver, 0.5)
                html_antes = _executar_js(driver, "return arguments[0].innerHTML || '';", editable) or ''
                texto_antes = _executar_js(driver, "return arguments[0].innerText || arguments[0].textContent || '';", editable) or ''
                if marcador in html_antes or marcador in texto_antes:
                    if debug:
                        print(f"[SUBST_MARCADOR] ✓ Marcador '{marcador}' detectado após espera!")
                    break

        if debug:
            print(f"[DEBUG] HTML ANTES: {html_antes[:300]}")
            print(f"[DEBUG] TEXTO ANTES: {texto_antes[:300]}")
            print(f"[DEBUG] Contém marcador '{marcador}' no HTML? {marcador in html_antes}")
            print(f"[DEBUG] Contém marcador '{marcador}' no TEXTO? {marcador in texto_antes}")

        script_ckeditor = f"""
        console.log('[SUBST_MARCADOR] === USANDO LÓGICA ROBUSTA DO EDITOR_INSERT ===');

        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = arguments[2];
        let fonte = arguments[3];

        try {{
            let ckInstance = null;

            if (editor.ckeditorInstance) {{
                ckInstance = editor.ckeditorInstance;
                console.log('[SUBST_MARCADOR] ✓ CKEditor via ckeditorInstance');
            }}

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

                if (htmlOriginal.includes(marcador)) {{
                    if (ckInstance.insertHtml) {{
                        console.log('[SUBST_MARCADOR] Tentando insertHtml...');
                        ckInstance.insertHtml(htmlContent, 'unfiltered_html');
                        console.log('[SUBST_MARCADOR] ✓ insertHtml usado');
                        return {{ sucesso: true, metodo: 'ckeditor_insertHtml' }};
                    }}

                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    ckInstance.setData(novoHtml);
                    console.log('[SUBST_MARCADOR] ✓ setData() executado');
                    return {{ sucesso: true, metodo: 'ckeditor_api' }};
                }} else if (htmlOriginal.trim().length > 20) {{
                    // Fallback: modelo tem texto mas não tem o marcador exato -> concatena
                    let novoHtml = htmlOriginal + '<br>' + htmlContent;
                    ckInstance.setData(novoHtml);
                    console.log('[SUBST_MARCADOR] ✓ setData() anexado ao final');
                    return {{ sucesso: true, metodo: 'ckeditor_api_append' }};
                }} else {{
                    console.error('[SUBST_MARCADOR] Editor vazio ou marcador não encontrado via API');
                }}
            }} else {{
                console.log('[SUBST_MARCADOR] CKEditor API não encontrada, usando DOM direto');

                editor.focus();
                let htmlOriginal = editor.innerHTML;
                if (htmlOriginal.includes(marcador)) {{
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    editor.innerHTML = novoHtml;

                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('keyup', {{ bubbles: true }}));

                    editor.blur();
                    setTimeout(() => editor.focus(), 10);

                    console.log('[SUBST_MARCADOR] ✓ DOM direto + eventos');
                    return {{ sucesso: true, metodo: 'dom_direto_com_eventos' }};
                }} else if (htmlOriginal.trim().length > 20) {{
                    editor.innerHTML = htmlOriginal + '<br>' + htmlContent;
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return {{ sucesso: true, metodo: 'dom_direto_append' }};
                }}
            }}

            return {{ sucesso: false, erro: 'Nenhum método funcionou' }};

        }} catch (e) {{
            console.error('[SUBST_MARCADOR] Erro:', e);
            return {{ sucesso: false, erro: e.message }};
        }}
        """

        resultado = _executar_js(driver, script_ckeditor, editable, html_content_clean, marcador, fonte_conteudo)

        # Aguardar até que o HTML seja atualizado
        try:
            def _condicao_html():
                try:
                    cur = _executar_js(driver, "return arguments[0].innerHTML;", editable) or ''
                    if html_content_clean[:100] in cur:
                        return True
                    if marcador not in cur:
                        return True
                    return False
                except Exception:
                    return False

            for _ in range(15):
                if _condicao_html():
                    break
                espera.pausa(driver, 0.2)
        except Exception:
            if debug:
                try:
                    html_depois = _executar_js(driver, "return arguments[0].innerHTML;", editable) or ''
                    print(f"[DEBUG] HTML DEPOIS (partial): {html_depois[:300]}")
                except Exception:
                    print('[DEBUG] Não foi possível ler HTML DEPOIS')

        if debug:
            print(f"[SUBST_MARCADOR] Resultado do script: {resultado}")

        if resultado and isinstance(resultado, dict) and resultado.get('sucesso'):
            if debug:
                print(f'[SUBST_MARCADOR] ✅ HTML inserido com sucesso via método: {resultado.get("metodo")}')

            try:
                html_final = _executar_js(driver, "return arguments[0].innerHTML;", editable) or ''
                marcador_removido = marcador not in html_final
            except Exception:
                marcador_removido = False

            if debug:
                print(f'[SUBST_MARCADOR] Verificação final: marcador removido = {marcador_removido}')

            return True
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado and isinstance(resultado, dict) else 'Script retornou None'
            if debug:
                print(f'[SUBST_MARCADOR] ❌ Falha na inserção: {erro}')
            return False

    except Exception as e:
        if debug:
            print(f"[SUBST_MARCADOR] ✗ Erro geral: {e}")
        return False
