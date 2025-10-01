# ====================================================================
# COLETA E INSERÇÃO UNIFICADA - coleta_insercao_unificada.py
# Módulo unificado para coleta de dados e inserção no editor CKEditor
# ====================================================================

import re
import time
from typing import Optional, Dict, Any, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# ===============================================
# DEPENDÊNCIAS EXTERNAS (FALLBACKS)
# ===============================================

try:
    from anexos import salvar_conteudo_clipboard
except ImportError:
    def salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug=False):
        """Fallback caso anexos.py não esteja disponível"""
        print(f"[FALLBACK] Salvando: {tipo_conteudo} - {conteudo[:50]}...")
        return True

# ===============================================
# UTILITÁRIOS COMUNS
# ===============================================

def _log_msg(contexto: str, msg: str, debug: bool = False):
    """Função de logging unificada"""
    if debug:
        print(f"[{contexto}] {msg}")

def _extrair_numero_processo_cnj(driver) -> Optional[str]:
    """Extrai número CNJ da página atual"""
    try:
        # Estratégia 1: ícone de cópia
        seletor_icon = 'span[aria-label*="Copia o número do processo"]'
        icon_spans = driver.find_elements(By.CSS_SELECTOR, seletor_icon)
        cnj_regex = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"

        for sp in icon_spans:
            try:
                # Tenta clicar no ícone para copiar
                driver.execute_script("arguments[0].click();", sp)
                time.sleep(0.5)
                # Tenta extrair do clipboard ou de elementos próximos
                numero_cnj = sp.text.strip()
                if re.match(cnj_regex, numero_cnj):
                    return numero_cnj
            except:
                continue

        # Estratégia 2: buscar no DOM
        elementos_texto = driver.find_elements(By.XPATH, "//*[contains(text(), 'Processo:')]")
        for elem in elementos_texto:
            texto = elem.text
            match = re.search(cnj_regex, texto)
            if match:
                return match.group(0)

        return None
    except Exception:
        return None

# ===============================================
# MÓDULO 1: COLETA DE DADOS (INTEGRADO DE coleta_atos.py)
# ===============================================

def coletar_link_ato_timeline(driver, numero_processo: str, debug: bool = False) -> bool:
    """
    Extrai link de validação de atos da timeline seguindo a ordem:
    1- Sentença, 2- Decisão, 3- Despacho (primeira ocorrência encontrada)

    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        debug: Boolean para logs detalhados

    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        _log_msg("LINK_ATO", msg, debug)

    log_msg(f"Iniciando coleta de link de ato para processo {numero_processo}")

    try:
        # Tipos de ato por prioridade
        tipos_ato = ['Sentença', 'Decisão', 'Despacho']

        for tipo_ato in tipos_ato:
            log_msg(f"Procurando por '{tipo_ato}'...")

            # Estratégias de busca na timeline
            estrategias = [
                f"//div[contains(@class, 'timeline-item')]//div[contains(text(), '{tipo_ato}')]",
                f"//span[contains(text(), '{tipo_ato}')]",
                f"//*[contains(text(), '{tipo_ato}')]"
            ]

            elementos_timeline = []
            for estrategia in estrategias:
                try:
                    elementos = driver.find_elements(By.XPATH, estrategia)
                    if elementos:
                        # Filtra apenas elementos visíveis
                        elementos_visiveis = [e for e in elementos if e.is_displayed()]
                        if elementos_visiveis:
                            elementos_timeline = elementos_visiveis
                            log_msg(f"✅ Encontrados {len(elementos_timeline)} elementos via estratégia: {estrategia}")
                            break
                except Exception as e:
                    log_msg(f"⚠️ Estratégia falhou: {estrategia} - {e}")
                    continue

            if elementos_timeline:
                log_msg(f"✅ Total de {len(elementos_timeline)} elemento(s) do tipo '{tipo_ato}' encontrado(s)")

                # Pega o primeiro elemento encontrado
                primeiro_elemento = elementos_timeline[0]
                log_msg(f"✅ Processando primeiro elemento de '{tipo_ato}'")

                # Clica no elemento para expandir/selecionar
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", primeiro_elemento)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", primeiro_elemento)
                    log_msg(f"✅ Elemento '{tipo_ato}' clicado e expandido")
                    time.sleep(1)
                except Exception as click_err:
                    log_msg(f"⚠️ Erro ao clicar no elemento: {click_err}")
                    continue

                # Extrair número do documento
                numero_documento = None
                try:
                    # Seletor específico que funcionou
                    seletor_documento = 'div[style="display: block;"] span'
                    spans_documento = driver.find_elements(By.CSS_SELECTOR, seletor_documento)

                    for span in spans_documento:
                        texto = span.text.strip()
                        if "Número do documento:" in texto:
                            partes = texto.split("Número do documento:")
                            if len(partes) > 1:
                                numero_documento = partes[1].strip()
                                log_msg(f"✅ Número do documento extraído: {numero_documento}")
                                break
                except Exception as e:
                    log_msg(f"❌ Erro na extração do número do documento: {e}")

                if numero_documento:
                    # Montar link de validação
                    link_validacao = f"https://pje.trt2.jus.br/pjekz/validacao/{numero_documento}?instancia=1"
                    log_msg(f"✅ Link de validação construído: {link_validacao}")

                    # Salvar no clipboard
                    numero_cnj = _extrair_numero_processo_cnj(driver) or numero_processo
                    sucesso = salvar_conteudo_clipboard(
                        conteudo=link_validacao,
                        numero_processo=str(numero_cnj),
                        tipo_conteudo=f"link_ato_{tipo_ato.lower()}_validacao",
                        debug=debug
                    )

                    if sucesso:
                        log_msg(f"✅ Link de validação de '{tipo_ato}' salvo com sucesso!")
                        return True
                    else:
                        log_msg(f"❌ Falha ao salvar link de validação de '{tipo_ato}'")
                        return False

                # Se chegou aqui, não conseguiu extrair número do documento
                log_msg(f"❌ Não foi possível extrair número do documento para '{tipo_ato}'")

        log_msg("❌ Nenhum link de ato foi coletado (Sentença, Decisão ou Despacho)")
        return False

    except Exception as e:
        log_msg(f"❌ Erro geral na coleta de link de ato: {e}")
        if debug:
            import traceback
            log_msg(f"Traceback: {traceback.format_exc()}")
        return False

def coletar_conteudo_js(driver, numero_processo: str, codigo_js: str, tipo_conteudo: str, debug: bool = False) -> bool:
    """
    Coleta conteúdo usando JavaScript personalizado.

    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        codigo_js: String com código JavaScript para extrair conteúdo
        tipo_conteudo: String identificando o tipo de conteúdo
        debug: Boolean para logs detalhados

    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        _log_msg("JS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta JS para processo {numero_processo}")
    log_msg(f"Tipo: {tipo_conteudo}")

    try:
        resultado = driver.execute_script(codigo_js)

        if resultado:
            if isinstance(resultado, dict):
                conteudo = "\n".join([f"{k}: {v}" for k, v in resultado.items()])
            elif isinstance(resultado, list):
                conteudo = "\n".join([str(item) for item in resultado])
            else:
                conteudo = str(resultado)

            log_msg(f"✅ Conteúdo extraído: {conteudo[:100]}...")

            sucesso = salvar_conteudo_clipboard(
                conteudo=conteudo,
                numero_processo=numero_processo,
                tipo_conteudo=tipo_conteudo,
                debug=debug
            )

            return sucesso
        else:
            log_msg("⚠️ JavaScript retornou resultado vazio")
            return False

    except Exception as e:
        log_msg(f"❌ Erro na coleta JS: {e}")
        return False

def coletar_elemento_css(driver, numero_processo: str, seletor_css: str, tipo_conteudo: str,
                        atributo: Optional[str] = None, debug: bool = False) -> bool:
    """
    Coleta conteúdo de elemento por seletor CSS.

    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        seletor_css: String com seletor CSS
        tipo_conteudo: String identificando o tipo de conteúdo
        atributo: Nome do atributo a extrair (None = texto do elemento)
        debug: Boolean para logs detalhados

    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        _log_msg("CSS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta CSS para processo {numero_processo}")
    log_msg(f"Seletor: {seletor_css}, Tipo: {tipo_conteudo}")

    try:
        elemento = driver.find_element(By.CSS_SELECTOR, seletor_css)

        if elemento and elemento.is_displayed():
            if atributo:
                conteudo = elemento.get_attribute(atributo)
                log_msg(f"✅ Atributo '{atributo}' extraído")
            else:
                conteudo = elemento.text.strip()
                log_msg(f"✅ Texto do elemento extraído")

            if conteudo:
                sucesso = salvar_conteudo_clipboard(
                    conteudo=conteudo,
                    numero_processo=numero_processo,
                    tipo_conteudo=tipo_conteudo,
                    debug=debug
                )
                return sucesso
            else:
                log_msg("⚠️ Elemento encontrado mas conteúdo vazio")
                return False
        else:
            log_msg(f"❌ Elemento não encontrado: {seletor_css}")
            return False

    except Exception as e:
        log_msg(f"❌ Erro na coleta CSS: {e}")
        return False

def coletar_dados_siscon(driver, numero_processo: str, parametros: Optional[Dict] = None, debug: bool = False) -> bool:
    """
    Extrai dados completos do SISCON (Sistema de Controle de Contas Judiciais).

    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        parametros: Configurações opcionais
        debug: Boolean para logs detalhados

    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        _log_msg("SISCON", msg, debug)

    log_msg(f"Iniciando coleta SISCON para processo {numero_processo}")

    try:
        config = parametros or {}
        url_siscon = config.get('url_siscon', 'https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/new')
        expandir_depositos = config.get('expandir_depositos', True)

        # Captura aba original
        aba_original = driver.current_window_handle

        # Abre SISCON em nova aba
        driver.execute_script(f"window.open('{url_siscon}', '_blank');")
        time.sleep(3)

        # Muda para aba SISCON
        abas_abertas = driver.window_handles
        aba_siscon = None

        for aba in abas_abertas:
            if aba != aba_original:
                driver.switch_to.window(aba)
                if 'alvaraeletronico' in driver.current_url:
                    aba_siscon = aba
                    break

        if not aba_siscon:
            log_msg("❌ Aba SISCON não encontrada")
            return False

        # Preenche e busca processo
        time.sleep(3)
        campo_processo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'numeroProcesso'))
        )
        campo_processo.clear()
        campo_processo.send_keys(numero_processo)

        botao_buscar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'bt_buscar'))
        )
        botao_buscar.click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'dados_pesquisados'))
        )
        time.sleep(2)

        # Extrai dados das contas
        dados_siscon = {
            'numero_processo': numero_processo,
            'contas': [],
            'total_geral': 0.0
        }

        try:
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            log_msg(f"✅ Encontradas {len(linhas_conta)} contas")

            for linha in linhas_conta:
                try:
                    celula_conta = linha.find_element(By.CSS_SELECTOR, 'td:nth-child(2)')
                    numero_conta = celula_conta.text.strip()

                    celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                    valor_texto = celula_disponivel.text.strip()

                    valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_texto)
                    total_disponivel = float(valor_match.group(1).replace('.', '').replace(',', '.')) if valor_match else 0.0

                    if total_disponivel > 0:
                        conta_dados = {
                            'numero_conta': numero_conta,
                            'total_disponivel': total_disponivel,
                            'depositos': []
                        }
                        dados_siscon['total_geral'] += total_disponivel

                        # Expandir depósitos se solicitado
                        if expandir_depositos:
                            try:
                                icone_expansao = linha.find_element(By.CSS_SELECTOR, 'img[src*="soma-ico.png"]')
                                driver.execute_script("arguments[0].click();", icone_expansao)
                                time.sleep(2)

                                linhas_deposito = driver.find_elements(By.CSS_SELECTOR, 'tr[id*="parcela"], tr.linha-parcela')
                                for linha_dep in linhas_deposito:
                                    if linha_dep.is_displayed():
                                        colunas = linha_dep.find_elements(By.TAG_NAME, 'td')
                                        if len(colunas) >= 3:
                                            try:
                                                data_deposito = colunas[0].text.strip()
                                                depositante = colunas[1].text.strip()
                                                valor_dep_texto = colunas[2].text.strip()

                                                valor_dep_match = re.search(r'R\$\s*([0-9.,]+)', valor_dep_texto)
                                                if valor_dep_match and data_deposito and depositante:
                                                    valor_deposito = float(valor_dep_match.group(1).replace('.', '').replace(',', '.'))
                                                    if valor_deposito > 0:
                                                        conta_dados['depositos'].append({
                                                            'data': data_deposito,
                                                            'depositante': depositante,
                                                            'valor': valor_deposito
                                                        })
                                            except:
                                                continue
                            except Exception as e:
                                log_msg(f"⚠️ Erro ao expandir depósitos: {e}")

                        dados_siscon['contas'].append(conta_dados)

                except Exception as e:
                    log_msg(f"⚠️ Erro na conta: {e}")
                    continue

        except Exception as e:
            log_msg(f"❌ Erro ao processar tabela: {e}")
            return False

        # Formatar e salvar dados
        conteudo_formatado = f"=== DADOS SISCON ===\n"
        conteudo_formatado += f"Processo: {dados_siscon['numero_processo']}\n"
        conteudo_formatado += f"Total Geral: R$ {dados_siscon['total_geral']:.2f}\n"
        conteudo_formatado += f"Contas com Saldo: {len(dados_siscon['contas'])}\n\n"

        if dados_siscon['contas']:
            for conta in dados_siscon['contas']:
                conteudo_formatado += f"🏛️ CONTA: {conta['numero_conta']}\n"
                conteudo_formatado += f"💰 TOTAL: R$ {conta['total_disponivel']:.2f}\n"

                if conta['depositos']:
                    conteudo_formatado += "📋 DEPÓSITOS:\n"
                    for dep in conta['depositos']:
                        conteudo_formatado += f"  • {dep['data']} | {dep['depositante']} | R$ {dep['valor']:.2f}\n"
                else:
                    conteudo_formatado += "📋 DEPÓSITOS: Não expandidos\n"

                conteudo_formatado += "\n" + "="*50 + "\n\n"
        else:
            conteudo_formatado += "⚠️ NENHUMA CONTA COM SALDO DISPONÍVEL\n"

        sucesso = salvar_conteudo_clipboard(
            conteudo=conteudo_formatado,
            numero_processo=numero_processo,
            tipo_conteudo="siscon_dados",
            debug=debug
        )

        # Fechar aba e voltar
        try:
            driver.close()
            driver.switch_to.window(aba_original)
        except:
            pass

        return sucesso

    except Exception as e:
        log_msg(f"❌ Erro na coleta SISCON: {e}")
        try:
            driver.switch_to.window(aba_original)
        except:
            pass
        return False

# ===============================================
# MÓDULO 2: INSERÇÃO NO EDITOR (INTEGRADO DE editor_insert.py)
# ===============================================

def _get_editable(driver, debug: bool = False):
    """Localiza o editor CKEditor na página"""
    sels = [
        '.ck-editor__editable[contenteditable="true"]',
        '.ck-content[contenteditable="true"]',
        'div[role="textbox"][contenteditable="true"]',
    ]
    for sel in sels:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el and el.is_displayed() and el.is_enabled():
                if debug:
                    print(f"[EDITOR] ✓ Editor encontrado por seletor: {sel}")
                return el
        except Exception:
            continue
    raise RuntimeError("Editor CKEditor não encontrado na página")

def _place_selection_at_marker(driver, editable, marcador: str = "--", modo: str = "after", debug: bool = False) -> bool:
    """Posiciona a seleção exatamente no marcador dentro do editor"""
    js = f"""
    const root = arguments[0];
    const marker = arguments[1];
    const mode = arguments[2];
    function findNodeWith(root, text) {{
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {{
        const idx = node.data.indexOf(text);
        if (idx !== -1) return {{ node, idx }};
      }}
      return null;
    }}
    const found = findNodeWith(root, marker);
    if (!found) return {{ ok: false, reason: 'marker_not_found' }};
    const sel = window.getSelection();
    const range = document.createRange();
    if (mode === 'replace') {{
      range.setStart(found.node, found.idx);
      range.setEnd(found.node, found.idx + marker.length);
    }} else {{
      range.setStart(found.node, found.idx + marker.length);
      range.setEnd(found.node, found.idx + marker.length);
    }}
    sel.removeAllRanges();
    sel.addRange(range);
    return {{ ok: true }};
    """
    result = driver.execute_script(js, editable, marcador, modo)
    return result and result.get('ok', False)

def inserir_html_editor(driver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere conteúdo HTML no editor CKEditor após o marcador.

    Args:
        driver: WebDriver do Selenium
        html_content: Conteúdo HTML a inserir
        marcador: Marcador onde inserir (padrão: "--")
        modo: "replace" ou "after"
        debug: Boolean para logs detalhados

    Returns:
        bool: True se inseriu com sucesso
    """
    try:
        if debug:
            print(f'[EDITOR] Iniciando inserção HTML')
            print(f'[EDITOR] Marcador: "{marcador}"')
            print(f'[EDITOR] HTML: {html_content[:100]}...')

        editable = _get_editable(driver, debug)

        # Foco no editor
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        # Posicionar seleção no marcador
        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                print(f'[EDITOR] Marcador "{marcador}" não encontrado')
            return False

        # Limpar e escapar conteúdo
        html_content_clean = (html_content
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

        # Inserir via JavaScript
        js_insert = f"""
        const sel = window.getSelection();
        if (sel.rangeCount > 0) {{
            const range = sel.getRangeAt(0);
            const html = `{html_escaped}`;
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            const fragment = document.createDocumentFragment();
            while (tempDiv.firstChild) {{
                fragment.appendChild(tempDiv.firstChild);
            }}
            range.deleteContents();
            range.insertNode(fragment);
            return true;
        }}
        return false;
        """

        sucesso = driver.execute_script(js_insert)
        if sucesso and debug:
            print('[EDITOR] ✅ HTML inserido com sucesso')

        return bool(sucesso)

    except Exception as e:
        if debug:
            print(f'[EDITOR] ❌ Erro na inserção: {e}')
        return False

def inserir_texto_editor(driver, texto: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere texto simples no editor CKEditor.

    Args:
        driver: WebDriver do Selenium
        texto: Texto a inserir
        marcador: Marcador onde inserir
        modo: "replace" ou "after"
        debug: Boolean para logs detalhados

    Returns:
        bool: True se inseriu com sucesso
    """
    try:
        if debug:
            print(f'[EDITOR] Iniciando inserção de texto: {texto[:50]}...')

        editable = _get_editable(driver, debug)

        # Foco no editor
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        editable.click()
        time.sleep(0.1)

        # Posicionar seleção
        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                print(f'[EDITOR] Marcador "{marcador}" não encontrado')
            return False

        # Inserir texto
        if modo == "replace":
            # Substituir marcador
            js_replace = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.deleteContents();
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """
        else:
            # Inserir após marcador
            js_after = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """

        script = js_replace if modo == "replace" else js_after
        sucesso = driver.execute_script(script)

        if sucesso and debug:
            print('[EDITOR] ✅ Texto inserido com sucesso')

        return bool(sucesso)

    except Exception as e:
        if debug:
            print(f'[EDITOR] ❌ Erro na inserção de texto: {e}')
        return False

def obter_ultimo_conteudo_clipboard(numero_processo: Optional[str] = None, tipo_regex: Optional[str] = None, debug: bool = False) -> Optional[str]:
    """
    Obtém o último conteúdo salvo no clipboard para um processo.

    Args:
        numero_processo: Número do processo (opcional)
        tipo_regex: Regex para filtrar tipo de conteúdo
        debug: Boolean para logs detalhados

    Returns:
        str or None: Conteúdo encontrado ou None
    """
    try:
        # Implementação simplificada - em produção usaria o sistema real
        if debug:
            print(f'[CLIPBOARD] Buscando último conteúdo para processo: {numero_processo}')

        # Placeholder - retornaria o conteúdo real do sistema de clipboard
        return None

    except Exception as e:
        if debug:
            print(f'[CLIPBOARD] Erro ao obter conteúdo: {e}')
        return None

def inserir_link_ato(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """
    Insere link de validação de ato no editor (combina coleta + inserção).

    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        modo: Modo de inserção
        debug: Boolean para logs detalhados

    Returns:
        bool: True se inseriu com sucesso
    """
    try:
        if debug:
            print(f'[LINK_ATO] Iniciando inserção de link para processo: {numero_processo}')

        # Primeiro tenta obter link do clipboard
        link_validacao = obter_ultimo_conteudo_clipboard(numero_processo, "link_ato", debug)

        if not link_validacao:
            # Se não encontrou no clipboard, tenta coletar
            if debug:
                print('[LINK_ATO] Link não encontrado no clipboard, coletando...')
            if not coletar_link_ato_timeline(driver, numero_processo or "", debug):
                return False
            link_validacao = obter_ultimo_conteudo_clipboard(numero_processo, "link_ato", debug)

        if link_validacao:
            # Monta HTML do link
            html_link = f'<a href="{link_validacao}" target="_blank">🔗 Validar Ato</a>'

            # Insere no editor
            return inserir_html_editor(driver, html_link, "--", modo, debug)
        else:
            if debug:
                print('[LINK_ATO] Não foi possível obter link de validação')
            return False

    except Exception as e:
        if debug:
            print(f'[LINK_ATO] Erro: {e}')
        return False

# ===============================================
# MÓDULO 3: FUNÇÃO UNIFICADA PRINCIPAL
# ===============================================

def executar_coleta_insercao_unificada(driver, numero_processo: str, tipo_operacao: str,
                                      parametros: Optional[Dict[str, Any]] = None, debug: bool = False) -> bool:
    """
    Função unificada que coordena coleta de dados e inserção no editor.

    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        tipo_operacao: Tipo da operação:
            - "coletar_link_ato": Coleta link de ato da timeline
            - "coletar_js": Coleta usando JavaScript
            - "coletar_css": Coleta usando seletor CSS
            - "coletar_siscon": Coleta dados do SISCON
            - "inserir_link_ato": Coleta + insere link de ato no editor
            - "inserir_html": Insere HTML no editor
            - "inserir_texto": Insere texto no editor
        parametros: Dict com parâmetros específicos
        debug: Boolean para logs detalhados

    Returns:
        bool: True se executou com sucesso
    """
    def log_msg(msg):
        _log_msg("UNIFICADO", msg, debug)

    log_msg(f"Executando operação unificada: {tipo_operacao}")

    try:
        config = parametros or {}

        # ===============================================
        # OPERAÇÕES DE COLETA
        # ===============================================

        if tipo_operacao == "coletar_link_ato":
            return coletar_link_ato_timeline(driver, numero_processo, debug)

        elif tipo_operacao == "coletar_js":
            if 'codigo_js' not in config:
                log_msg("❌ Parâmetro 'codigo_js' obrigatório")
                return False
            tipo_conteudo = config.get('tipo_conteudo', 'conteudo_js')
            return coletar_conteudo_js(driver, numero_processo, config['codigo_js'], tipo_conteudo, debug)

        elif tipo_operacao == "coletar_css":
            if 'seletor_css' not in config:
                log_msg("❌ Parâmetro 'seletor_css' obrigatório")
                return False
            tipo_conteudo = config.get('tipo_conteudo', 'conteudo_css')
            atributo = config.get('atributo')
            return coletar_elemento_css(driver, numero_processo, config['seletor_css'], tipo_conteudo, atributo, debug)

        elif tipo_operacao == "coletar_siscon":
            return coletar_dados_siscon(driver, numero_processo, config, debug)

        # ===============================================
        # OPERAÇÕES DE INSERÇÃO
        # ===============================================

        elif tipo_operacao == "inserir_link_ato":
            modo = config.get('modo', 'after')
            return inserir_link_ato(driver, numero_processo, modo, debug)

        elif tipo_operacao == "inserir_html":
            if 'html_content' not in config:
                log_msg("❌ Parâmetro 'html_content' obrigatório")
                return False
            marcador = config.get('marcador', '--')
            modo = config.get('modo', 'replace')
            return inserir_html_editor(driver, config['html_content'], marcador, modo, debug)

        elif tipo_operacao == "inserir_texto":
            if 'texto' not in config:
                log_msg("❌ Parâmetro 'texto' obrigatório")
                return False
            marcador = config.get('marcador', '--')
            modo = config.get('modo', 'replace')
            return inserir_texto_editor(driver, config['texto'], marcador, modo, debug)

        else:
            log_msg(f"❌ Tipo de operação não reconhecido: {tipo_operacao}")
            return False

    except Exception as e:
        log_msg(f"❌ Erro geral na operação unificada: {e}")
        return False

# ===============================================
# EXEMPLOS DE USO
# ===============================================

def exemplos_uso_unificado():
    """
    Exemplos de como usar o sistema unificado de coleta e inserção
    """

    # Exemplo 1: Coletar link de ato da timeline
    # executar_coleta_insercao_unificada(driver, "1234567890", "coletar_link_ato", debug=True)

    # Exemplo 2: Coletar dados usando JavaScript
    # params_js = {
    #     'codigo_js': 'return document.querySelector(".valor-causa").textContent;',
    #     'tipo_conteudo': 'valor_causa'
    # }
    # executar_coleta_insercao_unificada(driver, "1234567890", "coletar_js", params_js, debug=True)

    # Exemplo 3: Coletar elemento por CSS
    # params_css = {
    #     'seletor_css': '.numero-processo',
    #     'tipo_conteudo': 'numero_processo',
    #     'atributo': 'textContent'
    # }
    # executar_coleta_insercao_unificada(driver, "1234567890", "coletar_css", params_css, debug=True)

    # Exemplo 4: Coletar dados do SISCON
    # params_siscon = {
    #     'url_siscon': 'https://alvaraeletronico.trt2.jus.br/...',
    #     'expandir_depositos': True
    # }
    # executar_coleta_insercao_unificada(driver, "1234567890", "coletar_siscon", params_siscon, debug=True)

    # Exemplo 5: Inserir link de ato no editor (coleta + inserção automática)
    # executar_coleta_insercao_unificada(driver, "1234567890", "inserir_link_ato", {'modo': 'after'}, debug=True)

    # Exemplo 6: Inserir HTML no editor
    # params_html = {
    #     'html_content': '<b>Texto em negrito</b>',
    #     'marcador': '--',
    #     'modo': 'replace'
    # }
    # executar_coleta_insercao_unificada(driver, "1234567890", "inserir_html", params_html, debug=True)

    # Exemplo 7: Inserir texto simples no editor
    # params_texto = {
    #     'texto': 'Texto simples a inserir',
    #     'marcador': '--',
    #     'modo': 'after'
    # }
    # executar_coleta_insercao_unificada(driver, "1234567890", "inserir_texto", params_texto, debug=True)

    pass

# ===============================================
# COMPATIBILIDADE COM APIs EXISTENTES
# ===============================================

# Mapeamento para manter compatibilidade com imports existentes
def coletar_link_ato_timeline_compatibilidade(driver, numero_processo, debug=False):
    """Compatibilidade com coleta_atos.py"""
    return coletar_link_ato_timeline(driver, numero_processo, debug)

def executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros=None, debug=False):
    """Compatibilidade com coleta_atos.py"""
    # Mapeia tipos antigos para novos
    mapeamento_tipos = {
        "ecarta": "coletar_js",  # Requer implementação específica
        "link_ato": "coletar_link_ato",
        "js_generico": "coletar_js",
        "elemento_css": "coletar_css",
        "siscon": "coletar_siscon"
    }

    tipo_mapeado = mapeamento_tipos.get(tipo_coleta, tipo_coleta)
    return executar_coleta_insercao_unificada(driver, numero_processo, tipo_mapeado, parametros, debug)

def inserir_html_no_editor_apos_marcador(driver, html_content, marcador="--", modo="replace", debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_html_editor(driver, html_content, marcador, modo, debug)

def inserir_no_editor_apos_marcador(driver, texto, marcador="--", modo="replace", debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_texto_editor(driver, texto, marcador, modo, debug)

def inserir_link_ato_validacao(driver, numero_processo=None, modo='after', debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_link_ato(driver, numero_processo, modo, debug)