"""
Andrei/helpers.py - Helpers para checagens especificas de regras em peticoes.

Funcoes:
    _buscar_documento_relevante_timeline, apagar, checar_habilitacao,
    agravo_peticao, def_quesitos, _desp_assist, _extrair_texto_despacho,
    contesta_calc, obter_codigo_validacao_documento,
    obter_chave_ultimo_despacho_decisao_sentenca, configurar_recovery_driver,
    handle_exception_with_recovery
"""

import logging, re, json, unicodedata
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Andrei.utils_selenium import aguardar_renderizacao_nativa
from Andrei.api_client import PjeApiClient, session_from_driver
from Andrei.extracao import (extrair_direto, extrair_documento, criar_gigs, extrair_dados_processo)
from Andrei.pipeline import extrair_texto_peticao_via_api

logger = logging.getLogger(__name__)


# ==============================================================================
# FUNCOES LOCAIS (substituem importacoes de Fix.variaveis)
# ==============================================================================


def obter_codigo_validacao_documento(
    client: PjeApiClient, id_processo: str, id_documento: str
) -> Optional[str]:
    """Replica a construcao de 'chave' de validacao do documento.
    Chave := parte numerica de dataInclusaoBin (posicoes 2..16) + idBin (pad 14).
    """
    dados = client.documento_por_id(
        id_processo, id_documento, incluirAssinatura=False, incluirAnexos=False
    )
    if not dados:
        return None
    data = dados.get("dataInclusaoBin", "")
    idBin = dados.get("idBin")
    if not data or idBin is None:
        return None
    nums = re.sub(r"\D", "", data)
    part = nums[2:17] if len(nums) >= 17 else nums
    chave = part + str(idBin).zfill(14)
    return chave


def obter_chave_ultimo_despacho_decisao_sentenca(
    client: PjeApiClient,
    id_processo: str,
    tipos: Optional[List[str]] = None,
    itens_timeline: Optional[List[Dict]] = None,
    driver: Optional[WebDriver] = None,
) -> Optional[str]:
    """Retorna a chave de validacao do documento mais recente entre
    Despacho, Decisao ou Sentenca.
    - Filtra: pula despachos que contenham 'Comunique-se por edital'.
    """
    if tipos is None:
        tipos = ["Sentenca", "Decisao", "Despacho"]

    dados = itens_timeline or client.timeline(
        id_processo, buscarDocumentos=True, buscarMovimentos=False
    )
    if not dados:
        return None

    flat = []
    for d in dados:
        flat.append(d)
        if d.get("anexos"):
            for a in d.get("anexos"):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get("tipo") or "").strip()
        if not tipo or tipo not in tipos:
            continue
        doc_id = (
            docto.get("id")
            or docto.get("idDocumento")
            or docto.get("idUnicoDocumento")
        )
        if not doc_id:
            continue
        try:
            if driver and tipo == "Despacho":
                try:
                    base = client.trt_host
                    if not base.startswith("http"):
                        base = "https://" + base
                    resultado = extrair_direto(
                        driver, timeout=10, debug=False, formatar=True
                    )
                    if resultado and resultado.get("sucesso"):
                        conteudo = (
                            resultado.get("conteudo")
                            or resultado.get("conteudo_bruto")
                            or ""
                        ).lower()
                        if (
                            "comunique-se por edital" in conteudo
                            or "comunique se por edital" in conteudo
                        ):
                            logger.debug(
                                "[VARIAVEIS] Despacho com 'Comunique-se por edital' "
                                "- pulando"
                            )
                            continue
                except Exception as e_check:
                    logger.warning(
                        "[VARIAVEIS][WARN] Erro ao verificar despacho: "
                        "%s - prosseguindo",
                        e_check,
                    )

            chave = obter_codigo_validacao_documento(client, id_processo, doc_id)
            if not chave:
                continue
            base = client.trt_host
            if not base.startswith("http"):
                base = "https://" + base
            instancia = getattr(client, "grau", 1)
            return f"{base}/pjekz/validacao/{chave}?instancia={instancia}"
        except Exception:
            continue

    return None


# ==============================================================================
# FUNCOES LOCAIS (substituem importacoes de Fix.utils)
# ==============================================================================

_driver_recovery_config: Dict[str, Any] = {
    "enabled": False,
    "criar_driver": None,
    "login_func": None,
}


def configurar_recovery_driver(criar_driver_func, login_func):
    """Configura funcoes globais para recuperacao automatica de driver."""
    _driver_recovery_config["criar_driver"] = criar_driver_func
    _driver_recovery_config["login_func"] = login_func
    _driver_recovery_config["enabled"] = True
    logger.info("Configuracao de recuperacao automatica ativada")


def verificar_e_tratar_acesso_negado_global(driver: WebDriver) -> Optional[WebDriver]:
    """Verifica se driver esta em /acesso-negado e tenta recuperar."""
    if not _driver_recovery_config["enabled"]:
        return None

    try:
        url_atual = driver.current_url
        if "acesso-negado" not in url_atual.lower() and "login.jsp" not in url_atual.lower():
            return None

        logger.warning("[RECOVERY_GLOBAL] Acesso negado detectado: %s", url_atual)
        logger.warning("[RECOVERY_GLOBAL] Iniciando recuperacao automatica...")

        try:
            driver.quit()
            logger.info("Driver anterior fechado")
        except Exception as e:
            logger.warning("[RECOVERY_GLOBAL] Erro ao fechar driver: %s", e)

        criar_func = _driver_recovery_config.get("criar_driver")
        login_func = _driver_recovery_config.get("login_func")
        if not criar_func or not login_func:
            raise RuntimeError(
                "Recovery nao configurado - use configurar_recovery_driver()"
            )

        novo_driver = criar_func(headless=False)
        if not novo_driver:
            raise RuntimeError("Falha ao criar driver na recuperacao")

        logger.info("Novo driver criado")

        if not login_func(novo_driver):
            novo_driver.quit()
            raise RuntimeError("Falha no login durante recuperacao")

        logger.info("Login efetuado com sucesso - recuperacao completa!")
        return novo_driver

    except Exception as e:
        logger.error(
            "[RECOVERY_GLOBAL] Erro na recuperacao: %s: %s",
            type(e).__name__, e,
        )
        raise


def handle_exception_with_recovery(
    e: Exception,
    driver: WebDriver,
    funcao_nome: str = "",
) -> Optional[WebDriver]:
    """Trata excecao verificando se e acesso negado e tentando recuperar driver."""
    prefixo = f"[{funcao_nome}]" if funcao_nome else "[EXCEPTION]"
    try:
        novo_driver = verificar_e_tratar_acesso_negado_global(driver)
        if novo_driver:
            logger.info("%s Driver recuperado apos acesso negado", prefixo)
            return novo_driver
    except Exception as recovery_error:
        logger.warning(
            "%s Falha na recuperacao automatica: %s", prefixo, recovery_error
        )

    logger.error("%s Erro: %s", prefixo, e)
    return None


# ==============================================================================
# FUNCOES PRINCIPAIS (portadas de Peticao/helpers/helpers.py)
# ==============================================================================


def _buscar_documento_relevante_timeline(
    driver: WebDriver,
) -> Tuple[Optional[Any], Optional[Any], str]:
    """Busca documento relevante (sentenca/decisao/despacho) na timeline via DOM.
    Busca APENAS no tipo real do documento (primeiro <span> dentro do link).

    Returns:
        Tupla (doc_encontrado, doc_link, tipo_documento)
    """
    itens = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")

    for item in itens:
        try:
            link = item.find_element(
                By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'
            )
            primeiro_span = link.find_element(
                By.CSS_SELECTOR, "span:not(.sr-only)"
            )
            tipo_real = primeiro_span.text.lower().strip() if primeiro_span else ""

            if tipo_real and re.search(
                r"^(despacho|decisao|sentenca)", tipo_real
            ):
                return item, link, tipo_real.title()

        except Exception:
            continue

    return None, None, ""


def _normalizar_delete_processes(delete_processes: dict) -> dict:
    """Normaliza estrutura de delete_processes para {numero: [ids]}."""
    normalizado = {}
    for numero_processo, entradas in delete_processes.items():
        ids_documento = []
        if isinstance(entradas, list):
            for entrada in entradas:
                if isinstance(entrada, dict):
                    id_doc = str(
                        entrada.get("id_doc") or entrada.get("id") or ""
                    ).strip()
                else:
                    id_doc = str(entrada).strip()
                if id_doc and id_doc not in ids_documento:
                    ids_documento.append(id_doc)
        else:
            id_doc = str(entradas).strip()
            if id_doc:
                ids_documento.append(id_doc)
        if ids_documento:
            normalizado[numero_processo] = ids_documento
    return normalizado


def apagar(numero_processo: str, id_documento: str):
    """Registra processo no arquivo delete.js para nao ser processado."""
    try:
        delete_file = Path(__file__).parent / "delete.js"

        delete_processes = {}
        if delete_file.exists():
            try:
                content = delete_file.read_text(encoding="utf-8")
                match = re.search(
                    r"const\s+delete_processes\s*=\s*(\{.*?\})\s*;",
                    content,
                    re.S,
                )
                if match:
                    delete_processes = _normalizar_delete_processes(
                        json.loads(match.group(1))
                    )
            except Exception:
                pass

        novo_id_doc = str(id_documento).strip()
        if not novo_id_doc:
            return

        existente = delete_processes.get(numero_processo)
        if existente is None:
            delete_processes[numero_processo] = [novo_id_doc]
        elif isinstance(existente, list):
            ids = [
                str(e.get("id_doc") or e).strip()
                if isinstance(e, dict)
                else str(e).strip()
                for e in existente
            ]
            if novo_id_doc not in ids:
                existente.append(novo_id_doc)
        else:
            id_legado = str(existente).strip()
            if id_legado == novo_id_doc:
                delete_processes[numero_processo] = [id_legado]
            else:
                delete_processes[numero_processo] = [id_legado, novo_id_doc]

        with open(delete_file, "w", encoding="utf-8") as f:
            f.write(
                "// Arquivo para registrar processos que devem "
                'ser "apagados" (nao processados)\n'
            )
            f.write("// Formato: {numero_processo: [id_doc]}\n\n")
            f.write("const delete_processes = ")
            json.dump(delete_processes, f, indent=2, ensure_ascii=False)
            f.write(";\n\nmodule.exports = delete_processes;\n")

    except Exception as e:
        logger.error(
            "ERRO em apagar: Erro ao registrar processo no delete.js: "
            "%s: %s",
            type(e).__name__,
            e,
        )


def checar_habilitacao(item, driver: WebDriver) -> bool:
    """Checagem completa para regra de direitos-habilitacao.
    Inclui verificacao de advogado + verificacoes de audiencia para ato_ceju.

    Returns:
        bool: True se deve executar ato_ceju, False caso contrario.
    """
    try:
        numero_processo = str(getattr(item, "numero_processo", "") or "")
        if not numero_processo:
            return False

        # 0. Extrair dados do processo (dadosatuais.json)
        try:
            extrair_dados_processo(
                driver, caminho_json="Andrei/dadosatuais.json", debug=False
            )
        except Exception as e:
            logger.warning("[HABILITACAO] Erro ao extrair dados: %s", e)
            return False

        # 1. VERIFICACAO DE ADVOGADO

        def _extrair_nome_assinante(texto_pdf):
            linhas = texto_pdf.split("\n")
            for linha in reversed(linhas):
                linha = linha.strip()
                if "Documento assinado eletronicamente por" in linha:
                    match = re.search(
                        r"Documento assinado eletronicamente por (.+)", linha
                    )
                    if match:
                        nome = match.group(1).strip()
                        return re.sub(r"[.,;:!?]+$", "", nome)
            return None

        def _extrair_id_doc_peticao():
            try:
                sel = driver.find_element(
                    By.CSS_SELECTOR,
                    'li.tl-item-container[style*="background-color"]',
                )
                li_id = sel.get_attribute("id") or ""
                m = re.match(r"doc_(\d+)", li_id)
                return m.group(1) if m else ""
            except Exception:
                return ""

        def _obter_lista_advogados():
            try:
                dados_path = Path("Andrei/dadosatuais.json")
                if not dados_path.exists():
                    return []
                with open(dados_path, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                advogados = []
                for autor in dados.get("autor", []):
                    if "advogado" in autor and "nome" in autor["advogado"]:
                        advogados.append(autor["advogado"]["nome"])
                for reu in dados.get("reu", []):
                    if "advogado" in reu and "nome" in reu["advogado"]:
                        advogados.append(reu["advogado"]["nome"])
                return advogados
            except Exception as e:
                logger.warning(
                    "[HABILITACAO] Erro ao obter advogados: %s", e
                )
                return []

        tem_ata_audiencia = False
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            id_processo = client.id_processo_por_numero(numero_processo)
            if not id_processo:
                id_processo = str(
                    getattr(item, "id_processo", numero_processo) or ""
                )
            if id_processo:
                timeline = client.timeline(
                    id_processo, buscarDocumentos=True, buscarMovimentos=False
                )
                if timeline:
                    for doc in timeline:
                        titulo = (doc.get("titulo") or "").lower()
                        if "ata" in titulo and "audiencia" in titulo:
                            tem_ata_audiencia = True
                            logger.debug(
                                "[HABILITACAO] Processo %s - tem ata", numero_processo
                            )
                            break
        except Exception as e:
            logger.warning(
                "[HABILITACAO] Aviso: Erro ao verificar audiencia via API: %s", e
            )

        executar_ato_ceju = tem_ata_audiencia

        # 2. Verificar advogado
        id_doc_peticao = _extrair_id_doc_peticao()
        fez_gigs = False
        texto_pdf = extrair_texto_peticao_via_api(driver, item)
        if texto_pdf:
            texto_lower = texto_pdf.lower()
            contem_exclusao = (
                "excluir" in texto_lower or "exclusao" in texto_lower
            )
            nome_assinante = _extrair_nome_assinante(texto_pdf)
            adv_diverso = False
            if nome_assinante:
                advogados = _obter_lista_advogados()
                if advogados:
                    assinante_eh_advogado = any(
                        nome_assinante.lower() in adv.lower()
                        or adv.lower() in nome_assinante.lower()
                        for adv in advogados
                    )
                    if not assinante_eh_advogado:
                        adv_diverso = True

            if adv_diverso and contem_exclusao:
                tipo_gigs = "hab adv diverso + exclusao"
            elif adv_diverso:
                tipo_gigs = "hab adv diverso"
            elif contem_exclusao:
                tipo_gigs = "hab pede exclusao"
            else:
                tipo_gigs = None

            if tipo_gigs:
                try:
                    criar_gigs(driver, "-1", "", tipo_gigs)
                    fez_gigs = True
                    logger.debug(
                        "[HABILITACAO] GIGS: %s para %s", tipo_gigs, numero_processo
                    )
                except Exception as e:
                    logger.warning(
                        "[HABILITACAO] Erro ao criar GIGS: %s", e
                    )

        # 3. Decisao final
        if executar_ato_ceju:
            logger.debug(
                "[HABILITACAO] Processo %s - ato_ceju=True", numero_processo
            )
            return True

        if not fez_gigs:
            apagar(numero_processo, id_doc_peticao)
            logger.debug(
                "[HABILITACAO] Processo %s - registrado para apagar",
                numero_processo,
            )
        else:
            logger.debug(
                "[HABILITACAO] Processo %s - GIGS feito, nao apagar",
                numero_processo,
            )
        return False

    except Exception as e:
        logger.error(
            "ERRO em checar_habilitacao: %s: %s", type(e).__name__, e
        )
        return False


def agravo_peticao(item, driver: WebDriver) -> bool:
    """Processa Agravo de Peticao: busca documento relevante na timeline
    e executa ato apropriado baseado no conteudo.
    """
    logger.info(
        "[AGPET] Iniciando processamento de agravo de peticao: %s",
        item.numero_processo,
    )

    doc_encontrado, doc_link, tipo_documento = _buscar_documento_relevante_timeline(
        driver
    )

    if not doc_encontrado or not doc_link:
        logger.warning("[AGPET] Nenhum documento relevante encontrado na timeline")
        return False

    logger.info("[AGPET] Documento relevante encontrado: %s", tipo_documento)

    if tipo_documento.lower() == "sentenca":
        doc_link.click()
        try:
            aguardar_renderizacao_nativa(
                driver,
                ".timeline, .document-viewer, div.tl-item-container",
                timeout=2,
            )
        except Exception:
            import time

            time.sleep(2)

        texto = None
        try:
            resultado_direto = extrair_direto(
                driver, timeout=10, debug=False, formatar=True
            )
            if resultado_direto and resultado_direto.get("sucesso"):
                texto = (
                    resultado_direto.get("conteudo")
                    or resultado_direto.get("conteudo_bruto")
                    or ""
                ).lower()
        except Exception as e:
            logger.warning("[AGPET] Erro na extracao direta: %s", e)

        if not texto:
            try:
                texto_str = extrair_documento(
                    driver, regras_analise=None, timeout=10, log=False
                )
                if texto_str:
                    texto = texto_str.lower()
            except Exception as e:
                logger.warning("[AGPET] Erro na extracao documento: %s", e)

        if not texto:
            logger.error(
                "ERRO em agravo_peticao: Nao foi possivel extrair texto da sentenca"
            )
            return False

        texto_normalizado = texto.lower()

        if "desconsideracao" in texto_normalizado:
            if "defiro" in texto_normalizado or "indefiro" in texto_normalizado:
                logger.info(
                    "[AGPET] Sentenca contem decisao sobre "
                    "desconsideracao - executando ato_agpetidpj"
                )
                try:
                    from Andrei.atos_wrappers import ato_agpetidpj

                    ato_agpetidpj(driver)
                    logger.info("[AGPET] ato_agpetidpj executado com sucesso")
                    return True
                except ImportError:
                    logger.error(
                        "ERRO em agravo_peticao: ato_agpetidpj nao disponivel "
                        "(Andrei.atos_wrappers)"
                    )
                    return False
                except Exception as inner_e:
                    logger.error(
                        "ERRO em agravo_peticao: Erro ao executar "
                        "ato_agpetidpj: %s: %s",
                        type(inner_e).__name__,
                        inner_e,
                    )
                    return False
            else:
                logger.info(
                    "[AGPET] Sentenca menciona desconsideracao "
                    "mas sem decisao clara"
                )

        logger.info(
            "[AGPET] Sentenca sem decisao especifica sobre "
            "desconsideracao - executando ato_agpet"
        )
        try:
            from Andrei.atos_wrappers import ato_agpet

            ato_agpet(driver)
            logger.info("[AGPET] ato_agpet executado com sucesso")
            return True
        except ImportError:
            logger.error(
                "[AGPET] ato_agpet nao disponivel (Andrei.atos_wrappers)"
            )
            return False
        except Exception as inner_e:
            logger.error(
                "ERRO em agravo_peticao: Erro ao executar ato_agpet: "
                "%s: %s",
                type(inner_e).__name__,
                inner_e,
            )
            return False

    else:
        logger.info(
            "[AGPET] Documento e %s - executando ato_agpinter", tipo_documento
        )
        try:
            from Andrei.atos_wrappers import ato_agpinter

            ato_agpinter(driver)
            logger.info("[AGPET] ato_agpinter executado com sucesso")
            return True
        except ImportError:
            logger.error(
                "[AGPET] ato_agpinter nao disponivel (Andrei.atos_wrappers)"
            )
            return False
        except Exception as inner_e:
            logger.error(
                "ERRO em agravo_peticao: Erro ao executar ato_agpinter: "
                "%s: %s",
                type(inner_e).__name__,
                inner_e,
            )
            return False


def def_quesitos(item, driver: WebDriver) -> bool:
    """Processa peticoes com quesitos: analisa se deve admitir
    assistente tecnico ou apagar.

    Returns:
        bool: True se deve executar ato_assistente, False se deve apagar.
    """
    try:
        numero_processo = str(getattr(item, "numero_processo", "") or "")
        if not numero_processo:
            return False

        link_peticao = None
        itens = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")
        for item_tl in itens:
            try:
                link = item_tl.find_element(
                    By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'
                )
                span_texto = link.find_element(
                    By.CSS_SELECTOR, "span:not(.sr-only)"
                )
                texto_link = span_texto.text.lower()
                if "quesitos" in texto_link or "apresentacao de quesitos" in texto_link:
                    link_peticao = link
                    break
            except Exception:
                continue

        if not link_peticao:
            logger.warning(
                "[QUESITOS] Nenhuma peticao com quesitos para %s",
                numero_processo,
            )
            return False

        link_peticao.click()
        try:
            aguardar_renderizacao_nativa(
                driver,
                ".timeline, .document-viewer, div.tl-item-container",
                timeout=2,
            )
        except Exception:
            pass

        texto_peticao = None
        try:
            resultado = extrair_direto(
                driver, timeout=10, debug=False, formatar=True
            )
            if resultado and resultado.get("sucesso"):
                texto_peticao = resultado.get("conteudo") or resultado.get(
                    "conteudo_bruto"
                )
        except Exception as e:
            logger.warning("[QUESITOS] Erro ao extrair texto: %s", e)

        if not texto_peticao:
            logger.warning(
                "[QUESITOS] Nao foi possivel extrair texto para %s",
                numero_processo,
            )
            return False

        texto_lower = texto_peticao.lower()

        if (
            "indicar assistente" in texto_lower
            or "indicar assistentes" in texto_lower
            or "assistente tecnico" in texto_lower
            or "assistentes tecnicos" in texto_lower
        ):
            return _desp_assist(driver, numero_processo)
        else:
            logger.info(
                "[QUESITOS] Peticao sem indicacao de assistente - "
                "apagando %s",
                numero_processo,
            )
            apagar(numero_processo, str(getattr(item, "id_item", "") or ""))
            return False

    except Exception as e:
        logger.error("ERRO em def_quesitos: %s: %s", type(e).__name__, e)
        return False


def _desp_assist(driver: WebDriver, numero_processo: str) -> bool:
    """Analisa despachos subsequentes a peticao de quesitos para decidir
    admissao de assistente.

    Returns:
        bool: True se deve executar ato_assistente, False se deve apagar.
    """
    try:
        itens = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")
        despachos = []

        for item_tl in itens:
            try:
                link = item_tl.find_element(
                    By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'
                )
                span_texto = link.find_element(
                    By.CSS_SELECTOR, "span:not(.sr-only)"
                )
                tipo_doc = span_texto.text.lower().strip()
                if tipo_doc == "despacho":
                    despachos.append(link)
            except Exception:
                continue

        if len(despachos) < 1:
            logger.warning(
                "[DESP_ASSIST] Nenhum despacho encontrado para %s",
                numero_processo,
            )
            return False

        texto_primeiro = _extrair_texto_despacho(driver, despachos[0])
        if texto_primeiro and "venham a ser nomeados futuramente" in texto_primeiro.lower():
            logger.info(
                "[DESP_ASSIST] Primeiro despacho contem "
                "'venham a ser nomeados futuramente' - apagando %s",
                numero_processo,
            )
            return False

        if len(despachos) > 1:
            texto_segundo = _extrair_texto_despacho(driver, despachos[1])
            if texto_segundo and "venham a ser nomeados futuramente" in texto_segundo.lower():
                logger.info(
                    "[DESP_ASSIST] Segundo despacho contem "
                    "'venham a ser nomeados futuramente' - apagando %s",
                    numero_processo,
                )
                return False

        logger.info(
            "[DESP_ASSIST] Nenhum despacho com frase de adiamento - "
            "executando ato_assistente para %s",
            numero_processo,
        )
        try:
            from Andrei.atos_wrappers import ato_assistente

            if ato_assistente:
                ato_assistente(driver)
                logger.info(
                    "[DESP_ASSIST] ato_assistente executado para %s",
                    numero_processo,
                )
                return True
            return False
        except ImportError:
            logger.warning(
                "[DESP_ASSIST] ato_assistente nao disponivel "
                "(Andrei.atos_wrappers)"
            )
            return False
        except Exception as inner_e:
            logger.error(
                "ERRO em _desp_assist: Erro ao executar ato_assistente: "
                "%s: %s",
                type(inner_e).__name__,
                inner_e,
            )
            return False

    except Exception as e:
        logger.error("ERRO em _desp_assist: %s: %s", type(e).__name__, e)
        return False


def _extrair_texto_despacho(
    driver: WebDriver, link_despacho
) -> Optional[str]:
    """Extrai texto de um despacho clicando no link."""
    try:
        link_despacho.click()
        try:
            aguardar_renderizacao_nativa(
                driver,
                ".timeline, .document-viewer, div.tl-item-container",
                timeout=2,
            )
        except Exception:
            pass

        resultado = extrair_direto(
            driver, timeout=10, debug=False, formatar=True
        )
        if resultado and resultado.get("sucesso"):
            return resultado.get("conteudo") or resultado.get("conteudo_bruto")
        return None
    except Exception as e:
        logger.warning("[EXTRACAO_DESPACHO] Erro ao extrair texto: %s", e)
        return None


def contesta_calc(item, driver: WebDriver) -> bool:
    """Processa peticao de calculos de liquidacao:
    1. Busca despacho na timeline
    2. Extrai texto do despacho
    3. Verifica se contem frase de intimacao para calculos de liquidacao
    4. Se sim: verifica advogado da reclamada em dadosatuais.json
       - com advogado -> ato_contestar
       - sem advogado -> ato_revel
    """
    numero_processo = str(getattr(item, "numero_processo", "") or "")
    logger.info("[CONTESTA_CALC] Iniciando para %s", numero_processo)

    itens_tl = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")
    link_despacho = None
    for item_tl in itens_tl:
        try:
            link = item_tl.find_element(
                By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'
            )
            span = link.find_element(By.CSS_SELECTOR, "span:not(.sr-only)")
            tipo_doc = span.text.lower().strip()
            if tipo_doc == "despacho":
                link_despacho = link
                break
        except Exception:
            continue

    if not link_despacho:
        logger.info("[CONTESTA_CALC] Nenhum despacho encontrado - sem acao")
        return False

    try:
        extrair_dados_processo(
            driver, caminho_json="Andrei/dadosatuais.json", debug=False
        )
    except Exception as e:
        logger.warning("[CONTESTA_CALC] Falha ao extrair dados: %s", e)

    texto = _extrair_texto_despacho(driver, link_despacho)
    if not texto:
        logger.warning(
            "[CONTESTA_CALC] Nao foi possivel extrair texto do despacho"
        )
        return False

    FRASE = "para apresentar calculos de liquidacao"
    texto_norm = texto.lower()
    texto_norm = unicodedata.normalize("NFD", texto_norm)
    texto_norm = "".join(
        c for c in texto_norm if unicodedata.category(c) != "Mn"
    )

    if FRASE not in texto_norm:
        logger.info(
            "[CONTESTA_CALC] Despacho sem frase de calculos - sem acao"
        )
        return False

    logger.info(
        "[CONTESTA_CALC] Frase encontrada - verificando advogado da reclamada"
    )

    tem_advogado_reclamada = False
    try:
        dados_path = Path("Andrei/dadosatuais.json")
        if dados_path.exists():
            with open(dados_path, encoding="utf-8") as f:
                dados = json.load(f)
            partes = dados.get("partes", [])
            for parte in partes:
                polo = str(parte.get("polo") or "").lower()
                if "passiv" in polo or "reclama" in polo:
                    advogados = parte.get("advogados", [])
                    if advogados:
                        tem_advogado_reclamada = True
                        break
    except Exception as e:
        logger.warning(
            "[CONTESTA_CALC] Erro ao ler dadosatuais.json: %s", e
        )

    try:
        if tem_advogado_reclamada:
            logger.info(
                "[CONTESTA_CALC] Reclamada tem advogado - executando ato_contestar"
            )
            from Andrei.atos_wrappers import ato_contestar

            return bool(ato_contestar(driver))
        else:
            logger.info(
                "[CONTESTA_CALC] Reclamada sem advogado - executando ato_revel"
            )
            from Andrei.atos_wrappers import ato_revel

            return bool(ato_revel(driver))
    except ImportError:
        logger.error(
            "[CONTESTA_CALC] ato_contestar/ato_revel nao disponiveis "
            "(Andrei.atos_wrappers)"
        )
        return False
    except Exception as e:
        logger.error(
            "ERRO em contesta_calc: Erro ao executar ato: %s: %s",
            type(e).__name__,
            e,
        )
        return False
