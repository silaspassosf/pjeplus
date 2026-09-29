import time
import re
from typing import Any
from Fix.log import logger
from Fix.core import (
    aguardar_e_clicar,
    safe_click,
    wait_for_page_load,
    safe_click_no_scroll,
    esperar_elemento,
    aguardar_renderizacao_nativa,
)
from Fix.browser_suporte import aguardar_nova_aba
from Fix.utils import normalizar_texto
from Fix.extracao import extrair_direto
from Peticao.core.extracao.extracao import criar_gigs
from Fix import espera


def ativar_filtro_mandados_devolvidos(driver: Any) -> bool:
    """Ativa o filtro 'Mandados devolvidos' caso nao esteja ativo."""
    logger.info('[MANDADOS_UI] Verificando/ativando filtro de mandados devolvidos...')
    try:
        icones_mandados = espera.elementos(driver, 'i[aria-label*="Mandados devolvidos"]', teto=2)
        if not icones_mandados:
            logger.warning('[MANDADOS_UI] Ícone de mandados devolvidos não encontrado')
            return False

        icone = icones_mandados[0]
        aria_pressed = icone.get_attribute('aria-pressed')

        if aria_pressed == 'true':
            logger.info('[MANDADOS_UI] Filtro já ativo.')
            return True
        else:
            logger.info('[MANDADOS_UI] Clicando para ativar filtro...')
            aguardar_e_clicar(driver, 'i[aria-label*="Mandados devolvidos"]', timeout=10)
            espera.assentar(driver, 2)
            return True
    except Exception as e:
        logger.error(f'[MANDADOS_UI] Erro ao ativar filtro: {e}')
        return False


def processar_mandados_escaninho_ui(driver: Any) -> bool:
    """
    Fluxo que itera pela interface do escaninho mantendo a aba aberta.
    Prioriza processos com documento "Certidão de Oficial de Justiça".
    """
    logger.info('[MANDADOS_UI] Iniciando fluxo de UI no Escaninho...')

    url_escaninho = "https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos"
    if "escaninho/documentos-internos" not in (driver.current_url or ''):
        driver.get(url_escaninho)
        wait_for_page_load(driver, timeout=15)

    ativar_filtro_mandados_devolvidos(driver)

    # Aguarda a tabela renderizar
    if not espera.elemento(driver, "table[name='Tabela de Documentos'] tbody tr", teto=15, visivel=False):
        logger.warning('[MANDADOS_UI] Tabela de documentos não carregou ou está vazia.')
        return False

    escaninho_handle = driver.current_window_handle

    while True:
        try:
            linhas = espera.elementos(driver, "table[name='Tabela de Documentos'] tbody tr.cdk-drag", teto=2)
            if not linhas:
                logger.info('[MANDADOS_UI] Nenhuma linha encontrada na tabela.')
                break

            processou_algum = False

            for idx in range(len(linhas)):
                try:
                    tds = espera.elementos(driver, f"table[name='Tabela de Documentos'] tbody tr.cdk-drag:nth-of-type({idx+1}) td", teto=1)
                    if len(tds) < 13:
                        continue

                    descricao = (getattr(tds[5], 'text', '') or '').lower()
                    numero_processo = (getattr(tds[1], 'text', '') or '').strip()

                    if "certidão de oficial" in descricao or "certidao de oficial" in descricao:
                        logger.info(f'[MANDADOS_UI] Processando #{numero_processo} - {tds[5].text}')

                        botao_kz = espera.elemento(driver, f"table[name='Tabela de Documentos'] tbody tr.cdk-drag:nth-of-type({idx+1}) td:nth-child(1) button[aria-label*='Detalhes do Processo']", teto=1)
                        if not botao_kz:
                            continue

                        safe_click_no_scroll(driver, botao_kz)

                        # Aguarda nova aba abrir
                        try:
                            novo_handle = aguardar_nova_aba(driver, escaninho_handle, timeout=10)
                        except Exception:
                            logger.error(f"[MANDADOS_UI] Nova aba não abriu para {numero_processo}")
                            continue

                        driver.switch_to.window(novo_handle)

                        # Processamento na nova aba
                        try:
                            wait_for_page_load(driver, timeout=8)
                            aguardar_renderizacao_nativa(driver, "li.tl-item-container", timeout=5)

                            # Clica no doc mais recente que seja certidao
                            from Mandado.entrada_api import _selecionar_doc_via_timeline
                            tipo_doc = _selecionar_doc_via_timeline(driver, log=True)

                            if tipo_doc == 'outros':
                                texto_result = extrair_direto(driver, timeout=6, debug=True, formatar=True)
                                texto = texto_result.get('conteudo', '') if texto_result and texto_result.get('sucesso') else ''
                                texto_norm = normalizar_texto(texto).lower()

                                if "procedi a intimacao" in texto_norm or "procedi à intimação" in texto_norm:
                                    logger.info(f"[MANDADOS_UI] #{numero_processo}: Regra 'procedi à intimação' detectada. Executando ação Apagar.")
                                    criar_gigs(driver, dias_uteis="1", responsavel="", observacao="xs2", log=True)
                                    espera.assentar(driver, 1)

                                    driver.close()
                                    driver.switch_to.window(escaninho_handle)

                                    lixeira = espera.elemento(driver, f"table[name='Tabela de Documentos'] tbody tr.cdk-drag:nth-of-type({idx+1}) button[aria-label*='Remover documento']", teto=1)
                                    if lixeira:
                                        safe_click_no_scroll(driver, lixeira)
                                        logger.info(f"[MANDADOS_UI] Lixeira clicada para #{numero_processo}.")
                                        espera.ate_aparecer(driver, "//button[contains(., 'Sim') or contains(., 'Confirmar') or contains(., 'Remover')]", teto=2)
                                        try:
                                            botoes_confirmacao = espera.elementos(driver, "//button[contains(., 'Sim') or contains(., 'Confirmar') or contains(., 'Remover')]", teto=1)
                                            for btn in botoes_confirmacao:
                                                if getattr(btn, 'is_displayed', lambda: True)():
                                                    safe_click_no_scroll(driver, btn)
                                                    logger.info(f"[MANDADOS_UI] Confirmação de lixeira aceita para #{numero_processo}.")
                                                    espera.assentar(driver, 1)
                                                    break
                                        except Exception:
                                            pass

                                    processou_algum = True
                                    break
                                else:
                                    logger.info(f"[MANDADOS_UI] #{numero_processo}: Regra não satisfeita. Pulando.")
                                    driver.close()
                                    driver.switch_to.window(escaninho_handle)
                            else:
                                logger.info(f"[MANDADOS_UI] #{numero_processo}: Não é certidão ou não carregou timeline. Pulando.")
                                driver.close()
                                driver.switch_to.window(escaninho_handle)

                        except Exception as e:
                            logger.error(f"[MANDADOS_UI] Erro ao processar detalhes de #{numero_processo}: {e}")
                            try:
                                if getattr(driver, 'current_window_handle', None) != escaninho_handle:
                                    driver.close()
                                    driver.switch_to.window(escaninho_handle)
                            except Exception:
                                pass

                except Exception as e:
                    logger.warning("[MANDADOS_UI] Erro ao acessar linha. Reiniciando iteração: %s", e)
                    processou_algum = True
                    break

            if not processou_algum:
                logger.info("[MANDADOS_UI] Fim da lista de Certidão de Oficial. Parando iteração para o primeiro passo.")
                break

        except Exception as e:
            logger.error(f"[MANDADOS_UI] Erro geral no loop: {e}")
            break

    logger.info('[MANDADOS_UI] Fluxo de Mandados UI concluído.')
    return True
