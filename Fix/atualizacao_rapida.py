# -*- coding: utf-8 -*-
"""Atualização Rápida do PJe-Calc — réplica autônoma do botão +PJe."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from Fix.log import logger
from Fix.scripts import carregar_js

__all__ = ["executar_atualizacao_rapida", "executar_atualizacao_rapida_detalhada",
           "ResultadoAtualizacao", "AtualizacaoRapidaErro"]

_CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
_JS_NOME = "atualizacao_rapida.js"
_PASTA_JS = Path(__file__).resolve().parent
_TETO_EVAL_MS = 240_000


class AtualizacaoRapidaErro(RuntimeError):
    """Falha da atualização rápida. ``pos_envio=True`` => não reenviar."""

    def __init__(self, mensagem: str, *, fase: str = "", pos_envio: bool = False):
        super().__init__(mensagem)
        self.fase = fase
        self.pos_envio = pos_envio


@dataclass
class ResultadoAtualizacao:
    sucesso: bool
    numero_processo: str = ""
    numero_calculo: str = ""
    data: str = ""
    fase: str = ""
    erro: str = ""
    pos_envio: bool = False


def _data_atual() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _validar_data(valor: str) -> str:
    try:
        datetime.strptime(valor, "%d/%m/%Y")
    except (ValueError, TypeError):
        raise AtualizacaoRapidaErro(f"Data de liquidação inválida: {valor!r} (use dd/mm/aaaa)")
    return valor


def _ler_cnj_da_pagina(page) -> Optional[str]:
    """Lê o CNJ do cabeçalho/título do processo aberto (como o +PJe)."""
    try:
        texto = page.evaluate(
            "() => (document.querySelector('pje-cabecalho-processo')?.innerText || '')"
            " + ' ' + (document.title || '')"
        )
    except Exception:
        return None
    achado = _CNJ_RE.search(texto or "")
    return achado.group(0) if achado else None


def _origem_pje(driver) -> str:
    url = getattr(driver, "current_url", "") or ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc and "pje." in parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "https://pje.trt2.jus.br"


def executar_atualizacao_rapida(
    driver,
    numero_processo: Optional[str] = None,
    *,
    data: Optional[str] = None,
    id_calculo: Optional[str] = None,
    selecionar_mais_recente: bool = False,
    somente_busca: bool = False,
) -> bool:
    """Executa a atualização rápida e retorna ``True`` somente após "Sucesso!"."""
    resultado = _executar(driver, numero_processo, data=data, id_calculo=id_calculo,
                          selecionar_mais_recente=selecionar_mais_recente,
                          somente_busca=somente_busca)
    return resultado.sucesso


def executar_atualizacao_rapida_detalhada(
    driver,
    numero_processo: Optional[str] = None,
    *,
    data: Optional[str] = None,
    id_calculo: Optional[str] = None,
    selecionar_mais_recente: bool = False,
    somente_busca: bool = False,
) -> ResultadoAtualizacao:
    """Igual a :func:`executar_atualizacao_rapida`, mas devolve o dataclass
    completo (número do cálculo atualizado, data, fase) para o chamador."""
    return _executar(driver, numero_processo, data=data, id_calculo=id_calculo,
                     selecionar_mais_recente=selecionar_mais_recente,
                     somente_busca=somente_busca)


_FASES_PRE_EFEITO = ("", "inicio", "limpar-memoria", "busca-processo", "lista-calculos",
                     "selecao-calculo", "abrir-calculo", "menu-liquidar", "enviar-tela")
_MAX_RETOMADAS_JSF = 10

_PROBE_PRONTO = """() => (document.readyState === 'complete') && !!(
    document.querySelector('div[id="barraTitulo"]') ||
    document.querySelector('[title="Buscar Cálculo"]') ||
    document.querySelector('input[id*="formulario"]') ||
    document.querySelector('form'))"""


def _assentar_aba(aba) -> bool:
    """Espera o PJe-Calc assentar antes de injetar o motor."""
    try:
        aba.wait_for_load_state("load", timeout=15_000)
    except Exception:
        pass
    try:
        aba.wait_for_function(_PROBE_PRONTO, timeout=20_000)
    except Exception:
        pass
    try:
        url_1 = aba.url
        aba.wait_for_timeout(1200)
        return aba.url == url_1
    except Exception:
        return False


def _espelho_fase(aba) -> str:
    """Lê a última fase registrada pelo motor no sessionStorage da aba."""
    try:
        return (aba.evaluate(
            "() => { try { return sessionStorage.getItem('__pjeplusAR') || ''; }"
            " catch (e) { return ''; } }") or "")
    except Exception:
        return ""


def _confirmar_sucesso_pos_navegacao(aba) -> tuple[bool, str]:
    """Após navegação JSF em 'enviar'/'sucesso', apenas lê a página de confirmação (sem reenviar)."""
    _assentar_aba(aba)
    try:
        aba.wait_for_function(
            "() => Array.from(document.querySelectorAll('h2'))"
            ".some(h => (h.textContent || '').includes('Sucesso!'))",
            timeout=20_000,
        )
    except Exception:
        return False, ""
    calc_mem = ""
    try:
        calc_mem = str(aba.evaluate(
            "() => { try { return sessionStorage.getItem('__pjeplusAR_calc') || ''; } catch (e) { return ''; } }"
        ) or "")
    except Exception:
        pass
    try:
        aba.evaluate("() => { document.querySelector('li#li_operacoes_fechar a, a.menuImageClose, .menuImageClose')?.click(); }")
    except Exception:
        pass
    return True, calc_mem


def _executar(driver, numero_processo, *, data, id_calculo,
              selecionar_mais_recente=False, somente_busca=False) -> ResultadoAtualizacao:
    page = getattr(driver, "page", None)
    context = getattr(driver, "context", None)
    if page is None or context is None:
        raise AtualizacaoRapidaErro(
            "Driver sem superfície Playwright (page/context); rode via pw.py.")

    numero = (numero_processo or "").strip()
    if not numero:
        numero = _ler_cnj_da_pagina(page) or ""
    if not _CNJ_RE.fullmatch(numero):
        raise AtualizacaoRapidaErro(
            f" Número CNJ inválido ou não identificado: {numero!r}. "
            "Informe numero_processo ou abra a aba de detalhe do processo.")

    data_liq = _validar_data(data) if data else _data_atual()
    id_calc = str(id_calculo).strip() if id_calculo is not None else None

    js = carregar_js(_JS_NOME, pasta=_PASTA_JS)
    if not js.strip():
        raise AtualizacaoRapidaErro(f"JS {_JS_NOME} não carregado de {_PASTA_JS}.")

    origem = _origem_pje(driver)
    url_calc = f"{origem}/pjecalc/pages/principal.jsf"
    cfg = {"numeroProcesso": numero, "data": data_liq, "idCalculo": id_calc,
           "selecionarMaisRecente": bool(selecionar_mais_recente),
           "somenteBusca": bool(somente_busca)}

    logger.info("[ATUALIZACAO_RAPIDA] processo=%s data=%s id_calculo=%s%s%s",
                numero, data_liq, id_calc or "(único/auto)",
                " mais_recente=True" if selecionar_mais_recente else "",
                " somente_busca=True" if somente_busca else "")

    aba = context.new_page()
    bruto = None
    try:
        try:
            aba.set_default_timeout(_TETO_EVAL_MS)
            aba.goto(url_calc, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            raise AtualizacaoRapidaErro(
                f"PJeCalc não abriu: {type(e).__name__}: {e}",
                fase="abrir-pjecalc", pos_envio=False) from e
        _assentar_aba(aba)
        for tentativa in range(1, _MAX_RETOMADAS_JSF + 1):
            try:
                bruto = aba.evaluate(js, cfg)
                break
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                destruido = ("context was destroyed" in msg
                             or "navigation" in msg.lower())
                fase_espelho = _espelho_fase(aba)
                if destruido and fase_espelho in ("enviar", "sucesso"):
                    ok_pos, calc_pos = _confirmar_sucesso_pos_navegacao(aba)
                    if ok_pos:
                        bruto = {
                            "ok": True,
                            "numeroProcesso": numero,
                            "numeroCalculo": calc_pos or (id_calc or ""),
                            "data": data_liq,
                        }
                        break
                    raise AtualizacaoRapidaErro(
                        f"Envio interrompido por navegação sem confirmação 'Sucesso!' (não reenviar): {msg}",
                        fase="sucesso", pos_envio=True) from e
                pre_efeito = fase_espelho in _FASES_PRE_EFEITO
                if not (destruido and pre_efeito and tentativa < _MAX_RETOMADAS_JSF):
                    raise AtualizacaoRapidaErro(
                        f"Execução no PJeCalc interrompida: {msg}",
                        fase="transporte", pos_envio=True) from e
                logger.warning("[ATUALIZACAO_RAPIDA] navegação JSF na fase '%s' "
                               "— assentando e retomando (etapa %d/%d)",
                               fase_espelho or "(sem marca)",
                               tentativa + 1, _MAX_RETOMADAS_JSF)
                _assentar_aba(aba)
        if bruto is None:
            raise AtualizacaoRapidaErro(
                "Execução no PJeCalc não retornou resultado.",
                fase="transporte", pos_envio=True)
    finally:
        try:
            if not aba.is_closed():
                aba.close()
        except Exception:
            pass

    if not isinstance(bruto, dict):
        raise AtualizacaoRapidaErro(f"Retorno inesperado do PJeCalc: {bruto!r}", pos_envio=True)

    if bruto.get("ok"):
        if bruto.get("somenteBusca"):
            logger.info("[ATUALIZACAO_RAPIDA] SOMENTE BUSCA OK processo=%s calculo=%s "
                        "(nada foi liquidado nem enviado)",
                        bruto.get("numeroProcesso"), bruto.get("numeroCalculo"))
            return ResultadoAtualizacao(
                sucesso=True,
                numero_processo=bruto.get("numeroProcesso", numero),
                numero_calculo=str(bruto.get("numeroCalculo", "")),
                fase="somente-busca",
            )
        logger.info("[ATUALIZACAO_RAPIDA] SUCESSO processo=%s calculo=%s data=%s",
                    bruto.get("numeroProcesso"), bruto.get("numeroCalculo"), bruto.get("data"))
        return ResultadoAtualizacao(
            sucesso=True,
            numero_processo=bruto.get("numeroProcesso", numero),
            numero_calculo=str(bruto.get("numeroCalculo", "")),
            data=bruto.get("data", data_liq),
            fase="sucesso",
        )

    erro = str(bruto.get("erro") or "falha desconhecida")
    fase = str(bruto.get("fase") or "")
    pos_envio = bool(bruto.get("posEnvio"))
    logger.error("[ATUALIZACAO_RAPIDA] FALHA fase=%s pos_envio=%s: %s", fase, pos_envio, erro)
    raise AtualizacaoRapidaErro(erro, fase=fase, pos_envio=pos_envio)


_GAP_DIAS_CALCULO = 45


def calculo_antigo(data_divida: str, *, dias: int = _GAP_DIAS_CALCULO) -> bool:
    """True se a data de liquidação (dd/mm/aaaa) tem mais de `dias` dias."""
    try:
        dt = datetime.strptime((data_divida or "").strip(), "%d/%m/%Y")
    except (ValueError, TypeError):
        return False
    return (datetime.now() - dt).days > dias


def _divida_mais_recente_api(driver, id_processo) -> Optional[dict]:
    """Repuxa a dívida corrente via API — mesma consulta/ordenação de"""
    import requests
    from Fix.utils import formatar_data_brasileira, formatar_moeda_brasileira
    from Fix.variaveis import session_from_driver

    sess, trt_host = session_from_driver(driver)
    url = (f"https://{trt_host}/pje-comum-api/api/calculos/processo"
           f"?pagina=1&tamanhoPagina=10&ordenacaoCrescente=false&idProcesso={id_processo}")
    resp = sess.get(url, timeout=(5, 15))
    if not resp.ok:
        return None
    j = resp.json()
    resultado = (j or {}).get("resultado") or []
    if not resultado:
        return None
    mais_recente = resultado[0]
    return {
        "valor": formatar_moeda_brasileira(mais_recente.get("total", 0)),
        "data": formatar_data_brasileira(mais_recente.get("dataLiquidacao", "")),
    }


def atualizar_calculo_se_antigo(driver_pje, dados_processo, *, log: bool = True) -> Optional[str]:
    """Se o cálculo da dívida tem >45 dias, atualiza e repuxa o valor via API."""
    divida = dados_processo.get("divida") if isinstance(dados_processo, dict) else None
    data_divida = (divida or {}).get("data", "") if isinstance(divida, dict) else ""
    if not calculo_antigo(data_divida):
        return None

    numero_lista = (dados_processo or {}).get("numero") or []
    numero = str(numero_lista[0]).strip() if numero_lista else ""
    id_processo = (dados_processo or {}).get("id") or (dados_processo or {}).get("id_processo")

    if log:
        logger.info("[SISBAJUD][CALC] cálculo de %s (>%d dias) — executando atualização rápida",
                    data_divida, _GAP_DIAS_CALCULO)

    res = executar_atualizacao_rapida_detalhada(
        driver_pje, numero or None, selecionar_mais_recente=True)

    # A propagação PJeCalc→PJe pode demorar alguns segundos; espera observável
    from Fix import espera

    def _divida_fresca(_d):
        if not id_processo:
            return None
        try:
            cand = _divida_mais_recente_api(driver_pje, id_processo)
        except Exception:
            return None
        if cand and cand.get("valor") and not calculo_antigo(cand.get("data", "")):
            return cand
        return None

    nova = espera.ate(driver_pje, _divida_fresca, teto=30, intervalo=5) or None
    if nova:
        dados_processo["divida"] = nova
        if log:
            logger.info("[SISBAJUD][CALC] dívida atualizada via API: %s (liquidada em %s, cálculo %s)",
                        nova["valor"], nova["data"], res.numero_calculo)
    else:
        if log:
            logger.warning("[SISBAJUD][CALC] API ainda não reflete a atualização — "
                           "mantendo dívida anterior; minuta seguirá com GIGS CALC")
    return "calculo_antigo"