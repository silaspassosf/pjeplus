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

from Fix import espera

from api import PjeApiClient, buscar_todas_paginas, session_from_driver
from Fix.extracao import extrair_dados_processo, criar_gigs
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    processo_ja_executado_unificado,
    marcar_processo_executado_unificado,
    extrair_numero_processo_unificado,
    verificar_acesso_negado_unificado,
    formatar_numero_cnj,
)
from utilitarios_processamento import run_batch, resultado_ok, resultado_falha
from .regras_execucao import BUCKET_ORDEM, determinar_regra

logger = logging.getLogger(__name__)

from Fix.variaveis import url_processo_detalhe
from Fix.abas import fechar_abas_extras as _fechar_abas_extras
from Fix.browser_suporte import is_browsing_context_discarded_error


# ═══════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════

class AtividadePEC:
    def __init__(self, numero_processo, observacao, status, data_prazo, tipo_gigs, id_processo=None, id_atividade=None):
        self.numero_processo = numero_processo
        self.id_processo = id_processo
        self.observacao = observacao
        self.status = status
        self.data_prazo = data_prazo
        self.tipo_gigs = tipo_gigs
        self.id_atividade = id_atividade


class PECAPIClient:
    def fetch_atividades_vencidas(self, driver: Any, tamanho_pagina: int = 100) -> Optional[List[AtividadePEC]]:
        """Retorna a lista de atividades; None quando a API falha (403/401/
        sessao morta) — para que o orquestrador reporte FALHA e o main()
        acione o retry com novo login (mesmo contrato de mandado/p2b)."""
        logger.info("[PECAPIClient] Iniciando fetch_atividades_vencidas (API Gateway)...")
        try:
            sess, trt_host = session_from_driver(driver)
            client = PjeApiClient(sess, trt_host)
        except Exception as exc:
            logger.error(f"[PECAPIClient] Erro ao preparar sessao autenticada: {exc}")
            return None

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
            return None

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
                id_processo=(item.get("processo") or {}).get("id") or item.get("idProcesso"),
                id_atividade=item.get("id") or item.get("idAtividade"),
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


def extrair_numero_processo_pec(driver: Any) -> Optional[str]:
    """Extrai o numero do processo da URL ou elemento da pagina (adaptado para PEC)."""
    try:
        url = getattr(driver, 'current_url', '') or ''
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
            candidatos = espera.elementos(driver, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho, .numero-processo', teto=2)
            for elemento in candidatos:
                texto = getattr(elemento, 'text', '').strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_limpo = re.sub(r'[^\d]', '', match.group(1))
                    logger.info(f"[PROGRESSO_PEC]  Numero extraido do elemento: {numero_limpo}")
                    return numero_limpo
        except Exception as inner_e:
            logger.info(f"[PROGRESSO_PEC]  Erro ao buscar por seletores: {inner_e}")

        try:
            script = """
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
            """
            fn = getattr(driver, 'execute_script', None)
            numero_js = fn(script) if fn else None
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


def obter_chave_tarefa_pec(atv: Any, observacao: Optional[str] = None) -> str:
    """Gera chave identificadora única para a tarefa no fluxo PEC.

    Combina o número do processo (formatado CNJ) e a observação da atividade no GIGS.
    Exemplo: '1000886-64.2019.5.02.0703::xs pec exequente pessoal'
    """
    if hasattr(atv, 'numero_processo'):
        numero = atv.numero_processo or ""
        obs = normalizar_texto(getattr(atv, 'observacao', '') or '')
        id_atv = getattr(atv, 'id_atividade', None)
    elif isinstance(atv, dict):
        numero = atv.get('numero_processo') or atv.get('numero') or ""
        obs = normalizar_texto(atv.get('observacao') or '')
        id_atv = atv.get('id_atividade') or atv.get('id')
    else:
        numero = str(atv or "")
        obs = normalizar_texto(observacao or "")
        id_atv = None

    num_norm = formatar_numero_cnj(numero) or numero.strip()
    partes = [num_norm]
    if id_atv:
        partes.append(f"id:{id_atv}")
    if obs:
        partes.append(obs)
    return "::".join(partes)


def tarefa_ja_executada_pec(atv: Any, progresso: Optional[Dict[str, Any]] = None) -> bool:
    """Verifica se uma tarefa específica do PEC já foi executada.
    
    A checagem é por tarefa (processo + observação/atividade), permitindo que um
    mesmo processo execute múltiplas tarefas distintas no GIGS sem pular.
    """
    if not atv:
        return False
    if progresso is None:
        progresso = carregar_progresso_pec()

    chave = obter_chave_tarefa_pec(atv)
    tarefas_executadas = progresso.get("tarefas_executadas", [])
    if chave in tarefas_executadas:
        return True

    # Fallback caso a chave tenha sido gravada sem id_atividade (ou com variação de id)
    if hasattr(atv, 'numero_processo') and getattr(atv, 'observacao', None):
        num_norm = formatar_numero_cnj(atv.numero_processo) or atv.numero_processo.strip()
        chave_simples = f"{num_norm}::{normalizar_texto(atv.observacao)}"
        if chave_simples in tarefas_executadas:
            return True

    return False


def marcar_tarefa_executada_pec(
    atv: Any,
    progresso: Optional[Dict[str, Any]] = None,
    status: str = "SUCESSO",
    detalhes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Marca tarefa como executada (ou com erro) no fluxo PEC usando sistema unificado."""
    if not atv:
        return progresso
    if progresso is None:
        progresso = carregar_progresso_pec()

    chave = obter_chave_tarefa_pec(atv)
    sucesso = True if (status or "").upper() == "SUCESSO" else False
    hoje = datetime.now().strftime("%Y-%m-%d")

    tarefas_exec = progresso.setdefault("tarefas_executadas", [])
    tarefas_err = progresso.setdefault("tarefas_com_erro", [])
    datas = progresso.setdefault("datas_execucao", {})

    if sucesso:
        if chave not in tarefas_exec:
            tarefas_exec.append(chave)
        if chave in tarefas_err:
            tarefas_err.remove(chave)
        datas[chave] = hoje
        logger.info(f"[PROGRESSO_PEC] ✅ Tarefa marcada como executada: {chave}")
    else:
        if chave not in tarefas_err and chave not in tarefas_exec:
            tarefas_err.append(chave)
        datas[chave] = hoje
        logger.info(f"[PROGRESSO_PEC] ❌ Tarefa marcada com erro: {chave}")

    # Para rastreabilidade global, também marca processo em processos_executados
    num = getattr(atv, 'numero_processo', str(atv) if not isinstance(atv, dict) else atv.get('numero_processo', ''))
    if num:
        marcar_processo_executado_unificado('pec', num, progresso, sucesso=sucesso, motivo=detalhes)

    salvar_progresso_pec(progresso)
    return progresso


def processo_ja_executado_pec(numero_processo: str, progresso: Optional[Dict[str, Any]] = None) -> bool:
    """Verifica se o processo ja foi executado no fluxo PEC usando sistema unificado."""
    if not numero_processo:
        return False
    if progresso is None:
        progresso = carregar_progresso_pec()
    return processo_ja_executado_unificado(numero_processo, progresso)


def marcar_processo_executado_pec(
    numero_processo: Any,
    progresso: Optional[Dict[str, Any]] = None,
    status: str = "SUCESSO",
    detalhes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Marca processo como executado no fluxo PEC usando sistema unificado."""
    if hasattr(numero_processo, 'numero_processo') or (isinstance(numero_processo, dict) and ('observacao' in numero_processo or 'id_atividade' in numero_processo)):
        return marcar_tarefa_executada_pec(numero_processo, progresso, status=status, detalhes=detalhes)
    if not numero_processo:
        return progresso
    if progresso is None:
        progresso = carregar_progresso_pec()
    sucesso = True if (status or "").upper() == "SUCESSO" else False
    # Sucesso vence erro: processo já executado com sucesso nunca é re-marcado
    # como erro — evita duplicação de estado (processo em executados E em erros)
    # que causava re-execução indevida. O skip se apoia só em processos_executados.
    if not sucesso and processo_ja_executado_pec(str(numero_processo), progresso):
        logger.info(f'[PROGRESSO_PEC] Já executado com sucesso — ignorando erro: {numero_processo}')
        return progresso
    marcar_processo_executado_unificado('pec', str(numero_processo), progresso, sucesso=sucesso, motivo=detalhes)
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
        id_pje_link = item.get('ID_PJE_LINK', '')
        if id_pje:
            if id_pje_link:
                html_bloco += f'ID: <a href="{id_pje_link}" target="_blank">{id_pje}</a><br>'
            else:
                html_bloco += f'ID: {id_pje}<br>'

        destinatario = item.get('DESTINATARIO', '')
        if destinatario:
            html_bloco += f'DESTINATÁRIO: {destinatario}<br>'

        data_envio = item.get('DATA_ENVIO', '')
        if data_envio:
            html_bloco += f'DATA DO ENVIO: {data_envio}<br>'

        status = item.get('STATUS', '')
        falso_positivo = bool(item.get('FALSO_POSITIVO'))
        is_devolvido = bool(re.search(r'devolvid[oa]', status, re.IGNORECASE) or falso_positivo)

        data_entrega = item.get('DATA_ENTREGA', '')
        if not is_devolvido and data_entrega:
            html_bloco += f'DATA DE ENTREGA: {data_entrega}<br>'

        if status:
            html_bloco += f'RESULTADO: {status}'
            if falso_positivo:
                html_bloco += ' ⚠️ FALSO POSITIVO CORRIGIDO (era "Entregue", mas houve devolução)'
            html_bloco += '<br>'

        evidencia = item.get('EVIDENCIA', '')
        if evidencia:
            html_bloco += f'└ Evidência: {evidencia}<br>'

        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                rastreamento_limpo = rastreamento.strip()
                codigo_match = re.search(r'codigo=([A-Z0-9]+)', rastreamento_limpo)
                codigo_display = codigo_match.group(1) if codigo_match else rastreamento_limpo
                html_bloco += f'OBJETO: <a target="_blank" rel="noopener noreferrer" href="{rastreamento_limpo}">{codigo_display}</a><br>'
            else:
                html_bloco += f'OBJETO: {rastreamento}<br>'

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
        tem_devolvido = any(
            re.search(r'devolvid[oa]', item.get('STATUS', ''), re.IGNORECASE) or item.get('FALSO_POSITIVO')
            for item in dados_mais_recentes
        )
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

        status = item.get('STATUS', '')
        falso_positivo = bool(item.get('FALSO_POSITIVO'))
        is_devolvido = bool(re.search(r'devolvid[oa]', status, re.IGNORECASE) or falso_positivo)

        if not is_devolvido and item.get('DATA_ENTREGA'):
            bloco.append(f"    Data da entrega: {item.get('DATA_ENTREGA')}")

        status_mostrar = status
        if falso_positivo:
            status_mostrar += " ⚠️ FALSO POSITIVO CORRIGIDO"
        bloco.append(f"    Status: {status_mostrar}")
        if item.get('EVIDENCIA'):
            bloco.append(f"    └ Evidência: {item.get('EVIDENCIA')}")
        
        # Calcular prazos individuais para entregas confirmadas
        if not is_devolvido:
            data_entrega = _parse_data_ecarta(item.get('DATA_ENTREGA', ''))
            if data_entrega:
                prazo_8 = _somar_dias_uteis(data_entrega, 8)
                prazo_15 = _somar_dias_uteis(data_entrega, 15)
                if prazo_8 and prazo_15:
                    bloco.append(f"    Prazo: 08 dias={prazo_8.strftime('%d/%m/%Y')} / 15 dias={prazo_15.strftime('%d/%m/%Y')}")
        bloco_texto = '\n'.join(bloco)
        if i < len(dados_mais_recentes):
            bloco_texto += '\n' + '-' * 50
        blocos_formatados.append(bloco_texto)

    conteudo_final = '\n\n'.join(blocos_formatados)
    if prazo_texto:
        conteudo_final = (conteudo_final + '\n\n' if conteudo_final else '') + prazo_texto
    return conteudo_final, html_para_juntada, prazo_texto


# ═══════════════════════════════════════════════════
# GIGS DE PRAZO A PARTIR DA CERTIDAO (complemento do fluxo carta)
# ═══════════════════════════════════════════════════

_RE_PRAZO_15 = re.compile(r'15\s*(?:dias?\s*)?\((\d{2}/\d{2}/\d{4})\)', re.IGNORECASE)
_RE_PRAZO_8 = re.compile(r'0?8\s*(?:dias?\s*)?\((\d{2}/\d{2}/\d{4})\)', re.IGNORECASE)


def _contar_dias_uteis_ate(data_base, data_alvo):
    """Dias uteis (mesmo calendario de _somar_dias_uteis) de data_base ate data_alvo.

    Garante a propriedade _somar_dias_uteis(data_base, retorno) == data_alvo.
    Retorna None se data_alvo <= data_base ou se o alvo nao e alcancavel.
    """
    if not data_base or not data_alvo or data_alvo <= data_base:
        return None
    dias_calendario, intervalo = _carregar_calendario_dias_uteis()
    data_atual = data_base
    acumulado = 0
    seguranca = 0
    while data_atual < data_alvo and seguranca < 1000:
        data_atual += timedelta(days=1)
        seguranca += 1
        dentro_intervalo = intervalo and intervalo[0] <= data_atual <= intervalo[1]
        if dias_calendario and dentro_intervalo:
            if data_atual in dias_calendario:
                acumulado += 1
        else:
            if data_atual.weekday() < 5:
                acumulado += 1
    if data_atual != data_alvo:
        return None
    return acumulado


def criar_gigs_prazo_certidao(driver, prazo_texto, obs_15='xs pzi', obs_8=None, log=True):
    """Complemento do fluxo carta: cria GIGS de prazo alinhado a data certificada.

    A certidao juntada pelo fluxo carta traz o prazo contado (15 ou 8 dias uteis
    a partir da entrega da carta) com a data exata, ex.:
      - "Prazo: 15 dias (13/11/2026)"   (caso desconsideracao)
      - "Prazo: 8 dias (05/11/2026)"
      - "Prazos: 15 (13/11/2026) - 08 (05/11/2026)"

    O GIGS do PJe vence em HOJE + N dias uteis. Esta funcao recalcula N com o
    mesmo calendario do projeto ate que hoje + N dias uteis == a data certificada,
    e chama criar_gigs com esse N e a observacao correspondente:
      - prazo de 15 dias -> obs_15 (padrao 'xs pzi')
      - prazo de 8 dias  -> obs_8 (padrao None: nao cria)

    Nao levanta excecao; falhas sao logadas. Retorna True se criou ao menos um GIGS.
    """
    if not prazo_texto:
        if log:
            logger.info('[CARTA][GIGS] Sem prazo na certidao — nenhum GIGS de prazo.')
        return False

    m15 = _RE_PRAZO_15.search(prazo_texto)
    m8 = _RE_PRAZO_8.search(prazo_texto)
    if not m15 and not m8:
        if log:
            logger.info('[CARTA][GIGS] prazo_texto sem data reconhecivel: %r', prazo_texto[:80])
        return False

    hoje = datetime.now().date()
    alvos = []
    if m15 and obs_15:
        alvos.append((15, obs_15, _parse_data_ecarta(m15.group(1))))
    if m8 and obs_8:
        alvos.append((8, obs_8, _parse_data_ecarta(m8.group(1))))

    criados = 0
    for dias_certidao, observacao, data_certificada in alvos:
        if not data_certificada:
            if log:
                logger.warning('[CARTA][GIGS] Data do prazo de %s dias invalida.', dias_certidao)
            continue
        if data_certificada <= hoje:
            if log:
                logger.info(
                    '[CARTA][GIGS] Prazo de %s dias (%s) vencido ou hoje — GIGS nao criado.',
                    dias_certidao, data_certificada.strftime('%d/%m/%Y'),
                )
            continue
        dias = _contar_dias_uteis_ate(hoje, data_certificada)
        if dias is None:
            if log:
                logger.warning(
                    '[CARTA][GIGS] Nao consegui contar dias uteis ate %s — GIGS nao criado.',
                    data_certificada.strftime('%d/%m/%Y'),
                )
            continue
        try:
            if criar_gigs(driver, dias, '', observacao, log=log):
                criados += 1
                if log:
                    logger.info(
                        '[CARTA][GIGS] GIGS criado: %r com %s dias uteis — hoje + %s DU == %s '
                        '(data certificada).',
                        observacao, dias, dias, data_certificada.strftime('%d/%m/%Y'),
                    )
            elif log:
                logger.error('[CARTA][GIGS] criar_gigs falhou para %r.', observacao)
        except Exception as e:
            if log:
                logger.error('[CARTA][GIGS] Erro ao criar GIGS: %s', e)

    return criados > 0


# ═══════════════════════════════════════════════════
# EDITAL IDPJ POR RESULTADO NEGATIVO (complemento do fluxo carta)
# ═══════════════════════════════════════════════════


def _tem_resultado_negativo_por_destinatario(dados_mais_recentes):
    """True se pelo menos um destinatario tem APENAS resultados devolvidos.

    Agrupamento por DESTINATARIO: se o mesmo destinatario tem 2 cartas e uma
    delas foi entregue (positiva), ele NAO conta como negativo. So vale o
    destinatario cujo conjunto inteiro de resultados e de devolucoes
    (status devolvido ou falso positivo corrigido).
    """
    if not dados_mais_recentes:
        return False
    grupos = {}
    for item in dados_mais_recentes:
        destinatario = (item.get('DESTINATARIO') or '').strip().upper()
        if not destinatario:
            continue
        status = item.get('STATUS', '') or ''
        devolvido = bool(
            re.search(r'devolvid[oa]', status, re.IGNORECASE) or item.get('FALSO_POSITIVO')
        )
        grupos.setdefault(destinatario, []).append(devolvido)
    return any(todos and all(todos) for todos in grupos.values())


def executar_edital_idpj_negativo(driver, dados_mais_recentes, intimacoes_info, log=True):
    """Complemento do fluxo carta: intimação de desconsideração (IDPJ, prazo de
    15 dias) com resultado NEGATIVO dos Correios -> intimação por edital.

    Detecção (mesma lógica do prazo de 15 dias):
      - intimacoes_info com tem_desconsideracao (texto da intimação menciona
        "desconsideração" — carta_execucao._ler_intimacao_correio);
      - resultado negativo: existe pelo menos um destinatario cujas cartas no
        lote foram TODAS devolvidas (status 'devolvido' ou falso positivo).
        Destinatario com entrega positiva entre as cartas nao conta.

    Ação: criar_gigs(driver, 1, '', 'xs pec idpj') e depois o ato de edital
    do IDPJ (atos.ato_edidpj — Despacho, modelo 'xseditid', prazo 1).

    Nao levanta excecao; falhas sao logadas. Retorna True se o edital executou.
    """
    tem_desconsideracao = any(
        info.get('tem_desconsideracao') for info in (intimacoes_info or [])
    )
    if not tem_desconsideracao:
        if log:
            logger.info(
                '[CARTA][EDITAL] Sem intimacao de desconsideracao (IDPJ/15 dias) '
                '— fluxo edital nao se aplica.'
            )
        return False

    if not _tem_resultado_negativo_por_destinatario(dados_mais_recentes):
        if log:
            logger.info(
                '[CARTA][EDITAL] Nenhum destinatario com resultado apenas devolvido '
                '— fluxo edital nao se aplica.'
            )
        return False

    if log:
        logger.info('[CARTA][EDITAL] IDPJ + resultado negativo — criando GIGS "xs pec idpj"...')

    try:
        ok_gigs = criar_gigs(driver, 1, '', 'xs pec idpj', log=log)
        if log:
            if ok_gigs:
                logger.info('[CARTA][EDITAL] GIGS "xs pec idpj" criado (1 dia).')
            else:
                logger.error('[CARTA][EDITAL] criar_gigs "xs pec idpj" falhou.')
    except Exception as e:
        ok_gigs = False
        if log:
            logger.error('[CARTA][EDITAL] Erro ao criar GIGS "xs pec idpj": %s', e)

    try:
        from atos import ato_edidpj
        ok_edital = bool(ato_edidpj(driver, debug=log))
        if log:
            if ok_edital:
                logger.info('[CARTA][EDITAL] ato_edidpj (edital IDPJ) executado com sucesso.')
            else:
                logger.error('[CARTA][EDITAL] ato_edidpj retornou falha.')
        return ok_edital
    except Exception as e:
        if log:
            logger.error('[CARTA][EDITAL] Erro ao executar ato_edidpj: %s', e)
        return False


# ═══════════════════════════════════════════════════
# ORQUESTRADOR
# ═══════════════════════════════════════════════════

def _aguardar_carregamento(driver) -> None:
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, timeout=10)
    except Exception:
        espera.ate_js(driver, "document.readyState === 'complete'", teto=10)


class PECOrquestrador:
    def __init__(self, driver):
        self.driver = driver
        self.api = PECAPIClient()

    def executar(self, dry_run: bool = False, filtro_d1: bool = True,
                 data_minima: Optional[str] = None) -> Dict[str, int]:
        atividades = self.api.fetch_atividades_vencidas(self.driver)
        if atividades is None:
            # API falhou (ex: 403 ARQ-516, sessao morta). Nao e "zero
            # atividades" — sinaliza falha para o retry com novo login.
            logger.error('[PEC] Falha ao buscar atividades (API) — reportando falha para retry.')
            return {'total': 0, 'sucesso': 0, 'erro': 1}

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

        if dry_run:
            self._log_dry_run(buckets)
            return {'total': len(atividades), 'sucesso': 0, 'erro': 0}

        items = []
        for bucket in BUCKET_ORDEM:
            for atv, acao in buckets[bucket]:
                items.append((atv, acao))

        progresso = carregar_progresso_pec()
        _critical_exc = None

        _DRIVER_DEAD_MSGS = (
            'browsing context',
            'no longer exist',
            'failed to decode response from marionette',
            'tried to run command without establishing a connection',
            'no such window',
            'unable to connect to marionette',
            'session deleted',
        )

        def _is_critical(exc: Exception) -> bool:
            msg = str(exc).lower()
            return (
                'RESTART_PEC' in str(exc)
                or 'acesso negado' in msg
                or is_browsing_context_discarded_error(msg)
                or any(k in msg for k in _DRIVER_DEAD_MSGS)
            )

        def should_skip(item):
            atv, _ = item
            # Controle por tarefa: um mesmo processo com múltiplas tarefas executa todas
            ja_executado = tarefa_ja_executada_pec(atv, progresso)
            if ja_executado:
                logger.info(f'[PEC] Skip já executado: {atv.numero_processo} ({atv.observacao})')
            return ja_executado

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
                ultimo_retorno = True
                if isinstance(acao, tuple):
                    for f in acao:
                        retorno = f(self.driver, atv)
                        if retorno is None or retorno is False or (isinstance(retorno, tuple) and not all(retorno)):
                            nome_acao = getattr(f, '__name__', repr(f))
                            return resultado_falha(
                                f"Acao {nome_acao} retornou {retorno!r}",
                                observacao=atv.observacao,
                            )
                        if retorno is not True:
                            ultimo_retorno = retorno
                else:
                    retorno = acao(self.driver, atv)
                    if retorno is None or retorno is False or (isinstance(retorno, tuple) and not all(retorno)):
                        nome_acao = getattr(acao, '__name__', repr(acao))
                        return resultado_falha(
                            f"Acao {nome_acao} retornou {retorno!r}",
                            observacao=atv.observacao,
                        )
                    if retorno is not True:
                        ultimo_retorno = retorno
                return resultado_ok(retorno=ultimo_retorno)
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
                causa = dados.get('_exception') or RuntimeError(result.get('erro', ''))
                # 'RESTART_PEC' é o contrato de reinício do launcher: sem ele a
                # exceção é engolida em executar_fluxo_novo_simplificado.
                _critical_exc = RuntimeError(f'RESTART_PEC: {causa}')
            status = 'SUCESSO' if result.get('ok') else 'ERRO'
            marcar_tarefa_executada_pec(atv, progresso, status=status, detalhes=result.get('erro'))

        batch_result = run_batch(
            items=items,
            should_skip=should_skip,
            open_item=open_item,
            execute_item=execute_item,
            persist_result=persist_result,
            stop_on_critical=True,
        )

        # try:
        #     from .regras_execucao import fechar_driver_sisbajud_compartilhado
        #     fechar_driver_sisbajud_compartilhado()
        # except Exception as e:
        #     logger.error(f"[PEC] Erro ao fechar driver SISBAJUD compartilhado: {e}")

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


def executar_fluxo_novo_simplificado(driver, filtro_d1: bool = False,
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
