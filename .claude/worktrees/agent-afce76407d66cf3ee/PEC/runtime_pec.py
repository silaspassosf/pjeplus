"""PEC - Runtime Consolidado

Consolidado de: api_client, helpers, core_progresso, carta_utils,
                carta_formatacao, orquestrador.
"""

import json
import logging
import re
from datetime import date, datetime, timedelta

from Fix.utils import remover_acentos, normalizar_texto
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from api import PjeApiClient, buscar_todas_paginas, session_from_driver
from Fix.extracao import extrair_dados_processo
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    processo_ja_executado_unificado,
    marcar_processo_executado_unificado,
    extrair_numero_processo_unificado,
    verificar_acesso_negado_unificado,
)
from utilitarios_processamento import run_batch, resultado_ok, resultado_falha
from .regras_execucao import BUCKET_ORDEM, determinar_regra

logger = logging.getLogger(__name__)

from Fix.variaveis import url_processo_detalhe


# ═══════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════

class AtividadePEC:
    def __init__(self, numero_processo, observacao, status, data_prazo, tipo_gigs, id_processo=None):
        self.numero_processo = numero_processo
        self.id_processo = id_processo
        self.observacao = observacao
        self.status = status
        self.data_prazo = data_prazo
        self.tipo_gigs = tipo_gigs


class PECAPIClient:
    def fetch_atividades_vencidas(self, driver: WebDriver, tamanho_pagina: int = 100) -> List[AtividadePEC]:
        logger.info("[PECAPIClient] Iniciando fetch_atividades_vencidas (API Gateway)...")
        try:
            sess, trt_host = session_from_driver(driver)
            client = PjeApiClient(sess, trt_host)
        except Exception as exc:
            logger.error(f"[PECAPIClient] Erro ao preparar sessao autenticada: {exc}")
            return []

        resultado = buscar_todas_paginas(
            client,
            "/pje-gigs-api/api/relatorioatividades/",
            params_base={
                'filtrarVencidas': 'true',
                'ordenacaoCrescente': 'true',
                'filtrarPorDestinatario': 'false',
                'filtrarPorLocalizacao': 'false',
            },
            page_param='pagina',
            size_param='tamanhoPagina',
            pagina_inicial=1,
            tamanho_pagina=tamanho_pagina,
            limite_paginas=500,
            timeout=60,
        )

        if not resultado.get('ok'):
            erro = resultado.get('error') or {}
            logger.error(f"[PECAPIClient] Erro ao buscar atividades: {erro.get('type', 'sem_resposta')}")
            logger.error(f"[PECAPIClient] HTTP erro: status={resultado.get('status', '?')} detalhe={erro.get('message', '?')}")
            return []

        dados = resultado.get('data') or []
        total = len(dados)
        logger.info(f"[PECAPIClient] OK {len(dados)}/{total} atividades carregadas")

        atividades = [
            AtividadePEC(
                numero_processo=(item.get("processo") or {}).get("numero") or (item.get("processo") or {}).get("numeroProcesso") or "",
                observacao=(item.get("observacao") or "").strip(),
                status=(item.get("statusAtividade") or "").upper(),
                data_prazo=(item.get("dataPrazo") or "")[:10],
                tipo_gigs=(item.get("tipoAtividade") or {}).get("descricao") or (item.get("tipoAtividade") or {}).get("nome") or "",
                id_processo=(item.get("processo") or {}).get("id") or item.get("idProcesso")
            )
            for item in dados
        ]
        logger.info(f"[PECAPIClient] Total de atividades parseadas: {len(atividades)}")
        if atividades:
            logger.debug(f"[PECAPIClient] Exemplo: {vars(atividades[0])}")
        return atividades


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════



def gerar_regex_geral(termo: str) -> re.Pattern:
    """Gera regex flexivel para um termo, permitindo pontuacao entre palavras."""
    termo_norm: str = normalizar_texto(termo)
    palavras: List[str] = termo_norm.split()
    partes: List[str] = [re.escape(p) for p in palavras]
    regex: str = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)


def _montar_url_processo(numero_cnj: str, base_url: str = "https://pje.trt2.jus.br") -> str:
    """Monta URL de detalhe do processo para navegacao direta no PJe."""
    numero_texto = str(numero_cnj or "")
    numero_limpo = ''.join(filter(str.isdigit, numero_texto))
    identificador = numero_limpo if len(numero_limpo) == 20 else numero_texto
    return f"{base_url}/pjekz/processo/{identificador}/detalhe"


def _fechar_abas_extras(driver) -> None:
    """Mantem apenas a aba principal aberta, fechando as demais."""
    try:
        abas = driver.window_handles
        if len(abas) <= 1:
            return
        aba_principal = abas[0]
        for aba in abas[1:]:
            try:
                driver.switch_to.window(aba)
                driver.close()
            except Exception:
                pass
        driver.switch_to.window(aba_principal)
    except Exception:
        pass


# ═══════════════════════════════════════════════════
# PROGRESSO
# ═══════════════════════════════════════════════════

def carregar_progresso_pec() -> Dict[str, Any]:
    """Carrega o estado de progresso usando sistema unificado."""
    return carregar_progresso_unificado('pec')


def salvar_progresso_pec(progresso: Dict[str, Any]) -> bool:
    """Salva o estado de progresso usando sistema unificado."""
    salvar_progresso_unificado('pec', progresso)
    return True


def extrair_numero_processo_pec(driver: WebDriver) -> Optional[str]:
    """Extrai o numero do processo da URL ou elemento da pagina (adaptado para PEC)."""
    try:
        url = driver.current_url
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                numero_limpo = match.group(1)
                if len(numero_limpo) == 20:
                    n = numero_limpo
                    numero_formatado = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"
                    logger.info(f"[PROGRESSO_PEC]  Numero extraido da URL e formatado: {numero_formatado}")
                    return numero_formatado
                logger.info(f"[PROGRESSO_PEC]  Numero extraido da URL: {numero_limpo}")
                return numero_limpo

        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho, .numero-processo')
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_limpo = re.sub(r'[^\d]', '', match.group(1))
                    logger.info(f"[PROGRESSO_PEC]  Numero extraido do elemento: {numero_limpo}")
                    return numero_limpo
        except Exception as inner_e:
            logger.info(f"[PROGRESSO_PEC]  Erro ao buscar por seletores: {inner_e}")

        try:
            numero_js = driver.execute_script("""
                var textoCompleto = document.body.innerText || document.body.textContent || '';
                var matches = textoCompleto.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/g);
                if (matches && matches.length > 0) {
                    return matches[0].replace(/[^\\d]/g, '');
                }
                var titulo = document.title;
                var matchTitulo = titulo.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/);
                if (matchTitulo) {
                    return matchTitulo[0].replace(/[^\\d]/g, '');
                }
                return null;
            """)
            if numero_js:
                logger.info(f"[PROGRESSO_PEC]  Numero extraido via JavaScript: {numero_js}")
                return numero_js
        except Exception as js_e:
            logger.info(f"[PROGRESSO_PEC]  Erro no JavaScript de extracao: {js_e}")

        logger.info("[PROGRESSO_PEC]  Nenhum numero de processo encontrado")
        return None
    except Exception as e:
        logger.info(f"[PROGRESSO_PEC][ERRO] Falha ao extrair numero do processo: {e}")
        return None


def verificar_acesso_negado_pec(driver: Any) -> bool:
    """Verifica se estamos na pagina de acesso negado no sistema PEC."""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
    except Exception as e:
        msg = str(e)
        logger.error(f"[PROGRESSO_PEC][ERRO] Falha ao verificar acesso negado: {msg}")
        if "browsing context has been discarded" in msg.lower() or "session deleted because of page crash" in msg.lower():
            return True
        return False


def processo_ja_executado_pec(numero_processo: str, progresso: Optional[Dict[str, Any]] = None) -> bool:
    """Verifica se o processo ja foi executado no fluxo PEC usando sistema unificado."""
    if not numero_processo:
        return False
    if progresso is None:
        progresso = carregar_progresso_pec()
    return processo_ja_executado_unificado(numero_processo, progresso)


def marcar_processo_executado_pec(
    numero_processo: str,
    progresso: Optional[Dict[str, Any]] = None,
    status: str = "SUCESSO",
    detalhes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Marca processo como executado no fluxo PEC usando sistema unificado."""
    if not numero_processo:
        return progresso
    if progresso is None:
        progresso = carregar_progresso_pec()
    sucesso = True if (status or "").upper() == "SUCESSO" else False
    marcar_processo_executado_unificado('pec', numero_processo, progresso, sucesso=sucesso)
    return progresso


# ═══════════════════════════════════════════════════
# CARTA UTILS
# ═══════════════════════════════════════════════════

CALENDARIO_DIAS_UTEIS_PATH = Path('dias-uteis-trt2-2025.json')
_CALENDARIO_DIAS_UTEIS = None
_CALENDARIO_INTERVALO = None


def _carregar_calendario_dias_uteis():
    global _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO
    if _CALENDARIO_DIAS_UTEIS is not None:
        return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO
    dias_calendario = set()
    intervalo = None
    if CALENDARIO_DIAS_UTEIS_PATH.exists():
        try:
            with open(CALENDARIO_DIAS_UTEIS_PATH, 'r', encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
            for entrada in conteudo.get('dias_uteis', []):
                try:
                    data_convertida = datetime.fromisoformat(entrada).date()
                    dias_calendario.add(data_convertida)
                except ValueError:
                    continue
            if dias_calendario:
                intervalo = (min(dias_calendario), max(dias_calendario))
        except Exception:
            dias_calendario = set()
            intervalo = None
    _CALENDARIO_DIAS_UTEIS = dias_calendario
    _CALENDARIO_INTERVALO = intervalo
    return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO


def _somar_dias_uteis(data_base, quantidade):
    if not data_base or quantidade <= 0:
        return data_base
    dias_calendario, intervalo = _carregar_calendario_dias_uteis()
    data_atual = data_base
    acumulado = 0
    seguranca = 0
    while acumulado < quantidade and seguranca < 1000:
        data_atual += timedelta(days=1)
        seguranca += 1
        dentro_intervalo = intervalo and intervalo[0] <= data_atual <= intervalo[1]
        if dias_calendario and dentro_intervalo:
            if data_atual in dias_calendario:
                acumulado += 1
        else:
            if data_atual.weekday() < 5:
                acumulado += 1
    if acumulado < quantidade:
        return None
    return data_atual


def _dia_util_anterior(data_ref):
    """Retorna o dia util imediatamente anterior a data_ref, considerando o calendario."""
    dias_calendario, intervalo = _carregar_calendario_dias_uteis()
    data = data_ref - timedelta(days=1)
    for _ in range(30):
        dentro_intervalo = intervalo and intervalo[0] <= data <= intervalo[1]
        if dias_calendario and dentro_intervalo:
            if data in dias_calendario:
                return data
        else:
            if data.weekday() < 5:  # seg=0 ... sex=4
                return data
        data -= timedelta(days=1)
    return data_ref - timedelta(days=1)  # fallback seguro


def _parse_data_ecarta(valor):
    if not valor:
        return None
    valor_limpo = valor.strip()
    if not valor_limpo:
        return None
    parte_data = re.split(r'[\sT]', valor_limpo)[0]
    formatos = ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d')
    for fmt in formatos:
        try:
            return datetime.strptime(parte_data, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(parte_data).date()
    except ValueError:
        return None


def _obter_numero_processo(driver, log):
    process_number = None
    try:
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception:
        pass
    try:
        p = Path('dadosatuais.json')
        if p.exists():
            j = json.loads(p.read_text(encoding='utf-8'))
            maybe = j.get('numero') if isinstance(j, dict) else None
            if isinstance(maybe, (list, tuple)) and len(maybe) > 0:
                process_number = maybe[0]
            elif isinstance(maybe, str):
                process_number = maybe
    except Exception as e:
        if log:
            logger.error(f"[CARTA][DADOSATUAIS] Erro ao ler dadosatuais.json: {e}")
    return process_number


# ═══════════════════════════════════════════════════
# CARTA FORMATACAO
# ═══════════════════════════════════════════════════

def gerar_html_carta_para_juntada(dados):
    blocos_html = []
    for _, item in enumerate(dados, 1):
        html_bloco = (
            '<p class="corpo" style="font-size: 12pt; line-height: normal; '
            'margin-left: 0px !important; text-align: justify !important; '
            'text-indent: 4.5cm;">'
        )
        html_bloco += '&nbsp; &nbsp; '
        id_pje = item.get('ID_PJE', '')
        if id_pje:
            html_bloco += f'IID: {id_pje}<br>'
        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                rastreamento_limpo = rastreamento.strip()
                codigo_match = re.search(r'codigo=([A-Z0-9]+)', rastreamento_limpo)
                codigo_display = codigo_match.group(1) if codigo_match else rastreamento_limpo
                html_bloco += f'OBJETO: <a target="_blank" rel="noopener noreferrer" href="{rastreamento_limpo}">{codigo_display}</a><br>'
            else:
                html_bloco += f'OBJETO: {rastreamento}<br>'
        destinatario = item.get('DESTINATARIO', '')
        if destinatario:
            html_bloco += f'DESTINATARIO: {destinatario}<br>'
        data_envio = item.get('DATA_ENVIO', '')
        if data_envio:
            html_bloco += f'DATA DO ENVIO: {data_envio}<br>'
        data_entrega = item.get('DATA_ENTREGA', '')
        if data_entrega:
            html_bloco += f'DATA DE ENTREGA: {data_entrega}<br>'
        status = item.get('STATUS', '')
        if status:
            html_bloco += f'RESULTADO: {status}<br>'
        if 'entregue' in status.lower():
            html_bloco += 'DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.'
        html_bloco += '</p>'
        blocos_html.append(html_bloco)
    return '\n'.join(blocos_html)


def formatar_dados_ecarta(dados_mais_recentes, intimacoes_info, log=True):
    if not dados_mais_recentes:
        return "", "", ""
    prazo_texto = ""
    data_base_prazo = None
    datas_entrega_validas = []
    for item in dados_mais_recentes:
        data_entrega = _parse_data_ecarta(item.get('DATA_ENTREGA', ''))
        if data_entrega:
            datas_entrega_validas.append(data_entrega)
    if datas_entrega_validas:
        data_base_prazo = max(datas_entrega_validas)
    else:
        for item in dados_mais_recentes:
            data_base_prazo = _parse_data_ecarta(item.get('DATA_ENVIO', ''))
            if data_base_prazo:
                break
    if data_base_prazo:
        tem_devolvido = any(re.search(r'devolvid[oa]', item.get('STATUS', ''), re.IGNORECASE) for item in dados_mais_recentes)
        if tem_devolvido:
            prazo_texto = ""
        else:
            tem_alguma_desconsideracao = any(info.get('tem_desconsideracao') for info in intimacoes_info)
            if tem_alguma_desconsideracao:
                prazo_principal = _somar_dias_uteis(data_base_prazo, 15)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 8)
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 15 dias ({prazo_principal.strftime('%d/%m/%Y')})"
            else:
                prazo_principal = _somar_dias_uteis(data_base_prazo, 8)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 15)
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 8 dias ({prazo_principal.strftime('%d/%m/%Y')})"
            if not prazo_texto:
                prazo_8 = _somar_dias_uteis(data_base_prazo, 8)
                prazo_15 = _somar_dias_uteis(data_base_prazo, 15)
                if prazo_8 and prazo_15:
                    prazo_texto = f"Prazos: 15 ({prazo_15.strftime('%d/%m/%Y')}) - 08 ({prazo_8.strftime('%d/%m/%Y')})"

    html_para_juntada = gerar_html_carta_para_juntada(dados_mais_recentes)
    if prazo_texto:
        html_prazo = (
            '<p class="corpo" style="font-size: 12pt; line-height: normal; '
            'margin-left: 0px !important; text-align: justify !important; '
            'text-indent: 4.5cm;">&nbsp; &nbsp; '
            f'{prazo_texto}</p>'
        )
        html_para_juntada = f"{html_para_juntada}\n{html_prazo}" if html_para_juntada else html_prazo

    blocos_formatados = []
    for i, item in enumerate(dados_mais_recentes, 1):
        bloco = []
        bloco.append(f"    Id Pje: {item.get('ID_PJE', '')}")
        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                rastreamento_limpo = rastreamento.strip()
                bloco.append(f'    Rastreamento: {rastreamento_limpo}')
            else:
                bloco.append(f"    Rastreamento: {rastreamento}")
        else:
            bloco.append("    Rastreamento: Indisponivel")
        bloco.append(f"    Destinatario: {item.get('DESTINATARIO', '')}")
        bloco.append(f"    Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponivel'}")
        bloco.append(f"    Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponivel'}")
        bloco.append(f"    Status: {item.get('STATUS', '')}")
        bloco_texto = '\n'.join(bloco)
        if i < len(dados_mais_recentes):
            bloco_texto += '\n' + '-' * 50
        blocos_formatados.append(bloco_texto)

    conteudo_final = '\n\n'.join(blocos_formatados)
    if prazo_texto:
        conteudo_final = (conteudo_final + '\n\n' if conteudo_final else '') + prazo_texto
    return conteudo_final, html_para_juntada, prazo_texto


# ═══════════════════════════════════════════════════
# ORQUESTRADOR
# ═══════════════════════════════════════════════════

def _aguardar_carregamento(driver) -> None:
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, timeout=10)
    except Exception:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )


class PECOrquestrador:
    def __init__(self, driver):
        self.driver = driver
        self.api = PECAPIClient()

    def executar(self, dry_run: bool = False, filtro_d1: bool = False,
                 data_minima: Optional[str] = None) -> Dict[str, int]:
        atividades = self.api.fetch_atividades_vencidas(self.driver)

        if data_minima:
            antes = len(atividades)
            atividades = [a for a in atividades if (a.data_prazo or '')[:10] >= data_minima]
            logger.info(f'[PEC] data_minima ({data_minima}): {antes} -> {len(atividades)}')
        elif filtro_d1:
            data_d1 = _dia_util_anterior(date.today()).isoformat()
            antes = len(atividades)
            atividades = [a for a in atividades if (a.data_prazo or '')[:10] >= data_d1]
            logger.info(f'[PEC] D-1 ({data_d1}): {antes} -> {len(atividades)} (filtrado por data, dia util anterior)')
        else:
            logger.info(f'[PEC] Filtro D-1 OFF — processando todas: {len(atividades)}')

        if not atividades:
            return {'total': 0, 'sucesso': 0, 'erro': 0}

        buckets: Dict[str, list] = {b: [] for b in BUCKET_ORDEM}
        for atv in atividades:
            match = determinar_regra(atv.observacao or '')
            if match:
                _, bucket, acao = match
                buckets[bucket].append((atv, acao))
            else:
                logger.warning(f'[PEC] Sem regra: {atv.observacao!r} — {atv.numero_processo}')

        if buckets.get('comunicacoes'):
            buckets['comunicacoes'].sort(
                key=lambda item: 0 if 'xs sigilo' in (getattr(item[0], 'observacao', '') or '').lower() else 1
            )

        if dry_run:
            self._log_dry_run(buckets)
            return {'total': len(atividades), 'sucesso': 0, 'erro': 0}

        items = []
        for bucket in BUCKET_ORDEM:
            for atv, acao in buckets[bucket]:
                items.append((atv, acao))

        progresso = carregar_progresso_pec()
        _critical_exc = None

        def _is_critical(exc: Exception) -> bool:
            msg = str(exc)
            return 'RESTART_PEC' in msg or 'acesso negado' in msg.lower()

        def should_skip(item):
            atv, _ = item
            return processo_ja_executado_pec(atv.numero_processo, progresso)

        def open_item(item):
            atv, _ = item
            try:
                if atv.id_processo:
                    url = url_processo_detalhe(atv.id_processo)
                else:
                    url = _montar_url_processo(atv.numero_processo or '')
                self.driver.get(url)
                _aguardar_carregamento(self.driver)
                return resultado_ok()
            except Exception as e:
                if _is_critical(e):
                    return resultado_falha(str(e), critical=True, _exception=e)
                return resultado_falha(str(e))
            finally:
                _fechar_abas_extras(self.driver)

        def execute_item(item):
            atv, acao = item
            if acao is None:
                return resultado_falha("Acao None", observacao=atv.observacao)
            try:
                if isinstance(acao, tuple):
                    for f in acao:
                        f(self.driver, atv)
                else:
                    acao(self.driver, atv)
                return resultado_ok()
            except Exception as e:
                if _is_critical(e):
                    return resultado_falha(str(e), critical=True, _exception=e)
                return resultado_falha(str(e))
            finally:
                _fechar_abas_extras(self.driver)

        def persist_result(item, result):
            nonlocal _critical_exc
            atv, _ = item
            dados = result.get('dados') or {}
            if dados.get('critical') and _critical_exc is None:
                _critical_exc = dados.get('_exception') or RuntimeError(result.get('erro', ''))
            status = 'SUCESSO' if result.get('ok') else 'ERRO'
            marcar_processo_executado_pec(atv.numero_processo, progresso, status=status)

        batch_result = run_batch(
            items=items,
            should_skip=should_skip,
            open_item=open_item,
            execute_item=execute_item,
            persist_result=persist_result,
        )

        if _critical_exc:
            raise _critical_exc

        stats = {
            'total': len(atividades),
            'sucesso': batch_result['sucesso'],
            'erro': batch_result['falha'],
        }
        logger.info(f'[RESUMO] Total: {stats["total"]} | Sucesso: {stats["sucesso"]} | Erro: {stats["erro"]}')
        return stats

    def _log_dry_run(self, buckets: Dict[str, list]):
        logger.info("[DRY RUN] Distribuicao prevista:")
        for nome, items in buckets.items():
            if items:
                logger.info(f"  {nome}: {len(items)}")
                for atv, acao in items[:3]:
                    acao_nome = getattr(acao, '__name__', repr(acao))
                    logger.info(f"    - {atv.numero_processo}: {atv.observacao[:50]} -> {acao_nome}")


def executar_fluxo_novo_simplificado(driver, filtro_d1: bool = True,
                                     data_minima: Optional[str] = None) -> dict:
    try:
        orq = PECOrquestrador(driver)
        stats = orq.executar(dry_run=False, filtro_d1=filtro_d1, data_minima=data_minima)
        stats['sucesso'] = stats['erro'] == 0
        return stats
    except Exception as e:
        if 'RESTART_PEC' in str(e):
            raise
        logger.error(f'[FLUXO] Erro fatal: {e}')
        return {'total': 0, 'sucesso': False, 'erro': 1}
