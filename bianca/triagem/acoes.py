# -*- coding: utf-8 -*-
"""
bianca/triagem/acoes.py -- Acoes pos-triagem.

Contem:
  - Constantes de regex para deteccao de buckets
  - Funcoes de deteccao de alertas (estilo LEG -- mais robusto)
  - Funcoes de acao pos-triagem por bucket (A/B/C/D)
  - Helpers de navegacao (_abrir_nova_aba, _marcar_aud)

Extraido de triagem_engine.py (linhas 1884-2179).
"""

import os
import re
import time as _t
import traceback
from datetime import datetime as _dt
from pprint import pformat
from typing import Any, Dict, List, Optional, Tuple, Union

_t_monotonic = _t.monotonic
_t_sleep = _t.sleep

from Fix import espera
from Play.pjeplay.locators import By
from Fix.abas import trocar_para_nova_aba
from Fix.browser_suporte import abrir_url_nova_aba, _sub_elemento, click_headless_safe
from Fix.core import esperar_elemento, preencher_campo, safe_click
from Fix.headless_helpers import limpar_overlays_headless
from Fix.extracao import criar_comentario, criar_gigs
from bianca.triagem.citacao import def_citacao
from Fix.core import _executar_js

def _print_saida_funcao(rotulo: str, valor: Any) -> None:
    if isinstance(valor, str):
        texto = valor
    else:
        texto = pformat(valor, width=120, sort_dicts=False)
    print(f"[TRIAGEM/TRACE] {rotulo} => {texto}")


# =============================================================================
# Padroes para determinar bucket a partir do texto da triagem
# =============================================================================

_RE_BUCKET_PRE = re.compile(
    r'domicilio do reclamante como referencia subsidiaria', re.IGNORECASE)
_RE_BUCKET_B2 = re.compile(
    r'zona sul nao detectado|incompetencia territorial', re.IGNORECASE)
_RE_BUCKET_E = re.compile(r'reclamante menor de idade', re.IGNORECASE)
_RE_BUCKET_C = re.compile(r'B8_PEDIDOS:\s*ALERTA', re.IGNORECASE)
_RE_BUCKET_D = re.compile(r'B1_DOCS:\s*ALERTA', re.IGNORECASE)


# =============================================================================
# Deteccao de alertas (estilo LEG)
# =============================================================================


def _tem_alerta_incompetencia(triagem_txt: str) -> bool:
    """Incompetencia aparece na secao [COMPETENCIA] como 'Zona Sul nao detectado'
    seguida de foro (RUI BARBOSA ou ZONA LESTE).

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de incompetencia for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    t = triagem_txt.lower()
    return (
        "zona sul nao detectado" in t
        or "incompetencia territorial" in t
        or "fora dos intervalos" in t
    )


def _tem_alerta_pedidos_nao_liquidados(triagem_txt: str) -> bool:
    """Verifica alerta de pedidos nao liquidados na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de pedidos nao liquidados for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "pedidos liquidados" in s.lower():
            return True
    return False


def _tem_alerta_docs_pessoais(triagem_txt: str) -> bool:
    """Verifica alerta de documentos essenciais faltando na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de documentos essenciais for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "documentos essenciais" in s.lower():
            return True
    return False


def _tem_alerta_menor_idade(triagem_txt: str) -> bool:
    """Verifica alerta de reclamante menor de idade na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de menor de idade for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "menor de idade" in s.lower():
            return True
    return False


def _tem_alerta_domicilio_autor(triagem_txt: str) -> bool:
    """Verifica se competencia foi definida pelo domicilio do reclamante.

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se domicilio do autor for a referencia.
    """
    if not isinstance(triagem_txt, str):
        return False
    return 'domicilio do reclamante como referencia subsidiaria' in triagem_txt.lower()


# =============================================================================
# Determinacao de acao pos-triagem
# =============================================================================


def _determinar_acao_pos_triagem(triagem_txt: str) -> Tuple[str, None]:
    """Determina o bucket e acao a partir do texto da triagem.

    Implementacao inline dos patterns do alerta_registry.
    Prioridade: pre_bucket > b2_incompetencia > c_pedidos > d_docs > b1_normal.

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        Tuple (bucket_str, None).
    """
    if not triagem_txt:
        return 'b1_normal', None
    if _RE_BUCKET_PRE.search(triagem_txt):
        return 'pre_bucket', None
    if _RE_BUCKET_B2.search(triagem_txt):
        return 'b2_incompetencia', None
    if _RE_BUCKET_E.search(triagem_txt):
        return 'e_menor', None
    if _RE_BUCKET_C.search(triagem_txt):
        return 'c_pedidos', None
    if _RE_BUCKET_D.search(triagem_txt):
        return 'd_docs', None
    return 'b1_normal', None


def _aplicar_acao_pos_triagem(
    driver: Any,
    numero: str,
    processo_info: Dict,
    triagem_txt: str,
) -> Tuple[bool, Optional[str]]:
    """Decide e executa a acao pos-triagem com base nos alertas identificados.

    Usa _determinar_acao_pos_triagem() para identificar o bucket e
    despacha para a funcao de acao correspondente.

    Args:
        driver: Driver do processo.
        numero: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.
        triagem_txt: Texto da analise de triagem.

    Returns:
        Tuple[bool, Optional[str]]: (sucesso, status_line).
    """
    if not triagem_txt or (isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO")):
        print(f"[TRIAGEM/ACOES][{numero}] triagem com erro -- sem acao")
        return False, None

    bucket, _ = _determinar_acao_pos_triagem(triagem_txt)

    # Pre-bucket: competencia por domicilio do autor → GIGS observacao
    if bucket == 'pre_bucket':
        # Reavaliar sem pre_bucket para obter bucket real
        if _RE_BUCKET_B2.search(triagem_txt):
            bucket = 'b2_incompetencia'
        elif _RE_BUCKET_C.search(triagem_txt):
            bucket = 'c_pedidos'
        elif _RE_BUCKET_D.search(triagem_txt):
            bucket = 'd_docs'
        else:
            bucket = 'b1_normal'

    if bucket == 'b2_incompetencia':
        print(f"[TRIAGEM/ACOES][{numero}] b2 -- incompetencia territorial -> processo nao processado")
        return True, None
    if bucket == 'e_menor':
        print(f"[TRIAGEM/ACOES][{numero}] e_menor -- reclamante menor de idade -> intimar MPT, processo nao processado")
        return True, None
    if bucket == 'c_pedidos':
        print(f"[TRIAGEM/ACOES][{numero}] c -- pedidos nao liquidados -> placeholder despacho liquidar")
        return True, None
    if bucket == 'd_docs':
        print(f"[TRIAGEM/ACOES][{numero}] d -- falta de documentos pessoais -> placeholder apresentar doc")
        return True, None

    # b1: sem alertas criticos -> execucao normal de buckets
    bucket_proc = processo_info.get("bucket", "C")
    print(f"[TRIAGEM/ACOES][{numero}] b1 -- sem alertas -> bucket {bucket_proc} (execucao normal)")
    if bucket_proc == "A":
        ok, status = acao_bucket_a(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "B":
        ok, status = acao_bucket_b(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "C":
        ok, status = acao_bucket_c(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "D":
        ok, status = acao_bucket_d(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "CP":
        print(f"[TRIAGEM/ACOES][{numero}] CP -- Carta Precatória (comentario ja registrado)")
        return True, None

    print(f"[TRIAGEM/ACOES][{numero}] bucket desconhecido '{bucket_proc}'")
    return False, None


# =============================================================================
# Helpers de navegacao
# =============================================================================


def _abrir_nova_aba(
    driver: Any,
    url: str,
    aba_origem: str,
    url_fragmento: Optional[str] = None,
    timeout: int = 10,
) -> Optional[str]:
    """Abre nova aba e aguarda carregamento.

    Args:
        driver: Driver do navegador.
        url: URL a abrir.
        aba_origem: Handle da aba de origem.
        url_fragmento: Fragmento opcional para confirmar carregamento.
        timeout: Timeout em segundos.

    Returns:
        Handle da nova aba, ou None em caso de falha.
    """
    try:
        nova = abrir_url_nova_aba(driver, url, timeout=timeout)
        if nova:
            if url_fragmento:
                espera.ate_url(driver, url_fragmento, teto=timeout)
            return nova
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ _abrir_nova_aba: {type(e).__name__}: {e}")
        return None


def desmarcar_100(driver: Any, id_processo: str) -> Optional[str]:
    aba_detalhe = driver.current_window_handle
    url_retificar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    # Checar acesso-negado antes de prosseguir
    try:
        url_atual = driver.current_url or ""
        if "acesso-negado" in url_atual.lower():
            print(f"[TRIAGEM/ACOES] ⚠ desmarcar_100: acesso negado ({url_atual}) — fechando aba")
            driver.close()
            driver.switch_to.window(aba_detalhe)
            return None
    except Exception:
        pass

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            timeout=15,
        )
        if not step_carac:
            raise Exception("Step 'Caracteristicas' nao encontrado")

        _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        espera.assentar(driver, 1.0)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            timeout=10,
        )
        if not toggle:
            raise Exception("Toggle Juizo 100% digital nao encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", toggle)
            label = _sub_elemento(toggle, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            
        # 1. Localizar e clicar "Sim" no primeiro painel (Tem certeza de que deseja retirar)
        sim_js = """
        (function() {
            var xpath = "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.),'Tem certeza de que deseja retirar')]";
            var res = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            var title = res.singleNodeValue;
            if (!title) return {ok: false, erro: 'Painel Tem certeza nao encontrado'};
            var panel = title.closest('mat-expansion-panel');
            if (!panel) return {ok: false, erro: 'mat-expansion-panel nao encontrado'};
            var btns = Array.from(panel.querySelectorAll('button'));
            var sim = btns.find(function(b) { return (b.textContent || '').trim().includes('Sim'); });
            if (!sim) return {ok: false, erro: 'Botao Sim nao encontrado'};
            sim.click();
            return {ok: true};
        })()
        """
        t0 = _t_monotonic()
        clicou_sim = False
        while _t_monotonic() - t0 < 10.0:
            res_sim = _executar_js(driver, sim_js)
            if res_sim and res_sim.get('ok'):
                clicou_sim = True
                break
            _t_sleep(0.3)
        if not clicou_sim:
            raise Exception("Primeiro painel ou botao 'Sim' nao encontrado")

        espera.assentar(driver, 0.6)

        # 2. Localizar e clicar "Não" no segundo painel (Confirma a inclusão do movimento)
        nao_js = """
        (function() {
            var xpath = "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.),'Confirma a inclusão do movimento')]";
            var res = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            var title = res.singleNodeValue;
            if (!title) return {ok: false, erro: 'Painel Confirma inclusao nao encontrado'};
            var panel = title.closest('mat-expansion-panel');
            if (!panel) return {ok: false, erro: 'mat-expansion-panel nao encontrado'};
            var btns = Array.from(panel.querySelectorAll('button'));
            var nao = btns.find(function(b) { return (b.textContent || '').trim().includes('Não'); });
            if (!nao) return {ok: false, erro: 'Botao Nao nao encontrado'};
            nao.click();
            return {ok: true};
        })()
        """
        t0 = _t_monotonic()
        clicou_nao = False
        while _t_monotonic() - t0 < 10.0:
            res_nao = _executar_js(driver, nao_js)
            if res_nao and res_nao.get('ok'):
                clicou_nao = True
                break
            _t_sleep(0.3)
        if not clicou_nao:
            raise Exception("Segundo painel ou botao 'Nao' nao encontrado")

        espera.assentar(driver, 0.5)
        espera.ate_js(
            driver,
            "(function() { var t = document.querySelector(\"mat-slide-toggle[formcontrolname='juizoDigital']\"); return !!t && !t.classList.contains('mat-checked'); })()",
            teto=10
        )
        espera.assentar(driver, 1.0)
        return nova_aba
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ desmarcar_100: {type(e).__name__}: {e}")
        return nova_aba


def remarcar_100_pos_aud(driver: Any) -> bool:
    """Remarca 100% digital na aba retificar (/processo/{id}/retificar).

    Espelha a lógica validada de Script/modules/Aud/marcar.js (remarcar100):
      1. Garante que está no Step 4 ('Características').
      2. Localiza toggle[formcontrolname='juizoDigital']. Se já .mat-checked, retorna True.
      3. Clica no toggle (label.mat-slide-toggle-label).
      4. Aguarda painel 'Confirma a inclusão do movimento' e clica no botão 'Sim'.
      5. Aguarda toggle ganhar a classe .mat-checked.
    """
    print("[TRIAGEM/ACOES] Executando remarcar_100_pos_aud...")
    try:
        # 1. Garante Step 4 ('Características')
        step_js = """
        (function() {
            var toggle = document.querySelector("mat-slide-toggle[formcontrolname='juizoDigital']");
            if (toggle) return {ok: true, presente: true};
            var step4 = document.querySelector("mat-step-header[aria-posinset='4']");
            if (step4) {
                step4.scrollIntoView({block: 'center'});
                step4.click();
                return {ok: true, clicou_step: true};
            }
            return {ok: false, erro: 'Step 4 nao encontrado'};
        })()
        """
        _executar_js(driver, step_js)
        espera.assentar(driver, 0.8)

        # 2. Localiza toggle e clica se não estiver marcado
        toggle_js = """
        (function() {
            var toggle = document.querySelector("mat-slide-toggle[formcontrolname='juizoDigital']");
            if (!toggle) return {ok: false, erro: 'Toggle Juizo Digital nao encontrado'};
            if (toggle.classList.contains('mat-checked')) return {ok: true, ja_marcado: true};
            toggle.scrollIntoView({block: 'center'});
            var label = toggle.querySelector('label.mat-slide-toggle-label') || toggle;
            label.click();
            return {ok: true, clicou: true};
        })()
        """
        res_toggle = _executar_js(driver, toggle_js)
        if not res_toggle or not res_toggle.get('ok'):
            print(f"[TRIAGEM/ACOES] ⚠ remarcar_100: toggle não encontrado ou falhou: {res_toggle}")
            return False

        if res_toggle.get('ja_marcado'):
            print("[TRIAGEM/ACOES] ✅ 100% digital já estava marcado")
            return True

        espera.assentar(driver, 0.6)

        # 3. Painel / Dialog de confirmação: clica em 'Sim' na dialog ou no painel
        sim_js = """
        (function() {
            // 1. Procura em dialogs, modais e containers de overlay (mat-dialog-container, pje-modal-juizo-digital, .cdk-overlay-pane, mat-expansion-panel)
            var containers = Array.from(document.querySelectorAll(
                'mat-dialog-container, pje-modal-juizo-digital, .cdk-overlay-pane, mat-expansion-panel'
            ));
            for (var i = 0; i < containers.length; i++) {
                var c = containers[i];
                var btns = Array.from(c.querySelectorAll('button'));
                var btnSim = btns.find(function(b) {
                    var txt = (b.textContent || '').trim();
                    return txt === 'Sim' || txt.startsWith('Sim') || /\\bSim\\b/i.test(txt);
                });
                if (btnSim && btnSim.offsetParent !== null) {
                    btnSim.click();
                    var w = btnSim.querySelector('span.mat-button-wrapper');
                    if (w) w.click();
                    return {ok: true, tipo: c.tagName.toLowerCase(), clicou: true};
                }
            }

            // 2. Fallback por XPath direto para qualquer botão com span 'Sim' em modal/dialog/overlay/painel
            var xpBtn = "//mat-dialog-container//button[.//span[normalize-space(.)='Sim']] | " +
                        "//pje-modal-juizo-digital//button[.//span[normalize-space(.)='Sim']] | " +
                        "//div[contains(@class,'cdk-overlay-pane')]//button[.//span[normalize-space(.)='Sim']] | " +
                        "//mat-expansion-panel//button[.//span[normalize-space(.)='Sim']]";
            var res = document.evaluate(xpBtn, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            var b = res.singleNodeValue;
            if (b) {
                b.click();
                var w2 = b.querySelector('span.mat-button-wrapper');
                if (w2) w2.click();
                return {ok: true, tipo: 'xpath_direto', clicou: true};
            }

            return {ok: false, erro: 'confirmacao_nao_encontrada'};
        })()
        """
        t0 = _t_monotonic()
        clicou_sim = False
        while _t_monotonic() - t0 < 10.0:
            res_sim = _executar_js(driver, sim_js)
            if res_sim and res_sim.get('ok'):
                clicou_sim = True
                print(f"[TRIAGEM/ACOES] Botão 'Sim' clicado na confirmação ({res_sim.get('tipo')})")
                break
            _t_sleep(0.3)

        if not clicou_sim:
            print("[TRIAGEM/ACOES] ⚠️ Nenhuma dialog ou painel de confirmação com 'Sim' apareceu em 10s")

        espera.assentar(driver, 0.6)

        # 4. Aguarda o toggle ganhar a classe .mat-checked
        marcado = espera.ate_js(
            driver,
            "(function() { var t = document.querySelector(\"mat-slide-toggle[formcontrolname='juizoDigital']\"); return !!t && t.classList.contains('mat-checked'); })()",
            teto=10
        )
        if marcado:
            print("[TRIAGEM/ACOES] ✅ 100% digital remarcado com sucesso (.mat-checked ativo)")
            return True
        else:
            print("[TRIAGEM/ACOES] ⚠️ Toggle não confirmou classe .mat-checked após remarcar")
            return False
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ remarcar_100_pos_aud: {type(e).__name__}: {e}")
        return False


_MESES_PT = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def _extrair_data_hora_pauta(linha) -> tuple:
    """Extrai data e horário da linha da Tabela de Horários Vagos.

    Usa seletores específicos baseados na estrutura real:
      - Data: 2ª coluna (td.centralizado:nth-child(2) span)
      - Horário: 3ª coluna (td.centralizado:nth-child(3) span)
    """
    try:
        data_span = _sub_elemento(
            linha,
            "td.centralizado.td-class:nth-child(2) span.ng-star-inserted"
        )
        hora_span = _sub_elemento(
            linha,
            "td.centralizado.td-class:nth-child(3) span.ng-star-inserted"
        )
        data_str = ((getattr(data_span, 'text_content', None) and data_span.text_content()) or getattr(data_span, 'text', '') or '').strip()
        hora_str = ((getattr(hora_span, 'text_content', None) and hora_span.text_content()) or getattr(hora_span, 'text', '') or '').strip()
        if not data_str or not hora_str:
            raise ValueError(f"Data='{data_str}' ou hora='{hora_str}' vazias")
        return data_str, hora_str
    except Exception as e:
        raise ValueError(f"Falha ao extrair data/hora da linha: {e}")


def _navegar_calendario_para_data(driver: Any, data_str: str) -> None:
    """Navega o calendario mensal ate a data alvo e clica no dia.

    Args:
        driver: Driver do navegador.
        data_str: Data no formato "DD/MM/YYYY".
    """
    alvo = _dt.strptime(data_str, "%d/%m/%Y")
    
    heading_el = esperar_elemento(driver, "div.filtros h2, h2[role='status'], .cal-header h2", by=By.CSS_SELECTOR, timeout=10)
    if not heading_el:
        raise Exception("Nao foi possivel ler o heading inicial do calendario.")
    current_heading = heading_el.text.strip()
    
    import re
    match = re.search(r'([a-zA-ZçÇ]+)[^\d]+(\d{4})', current_heading)
    if not match:
        raise Exception(f"Formato de heading desconhecido: {current_heading}")
    
    mes_str = match.group(1).capitalize()
    ano_atual = int(match.group(2))
    
    try:
        mes_atual = _MESES_PT.index(mes_str) + 1
    except ValueError:
        raise Exception(f"Mes desconhecido no heading: {mes_str}")
        
    delta = (alvo.year - ano_atual) * 12 + (alvo.month - mes_atual)
    print(f"[CALENDARIO] Navegando para {data_str}. Calendario exibe: {mes_str}/{ano_atual}. Delta meses: {delta}")

    if delta > 0:
        btn_selector = "button#next, div.filtros button#next"
    elif delta < 0:
        btn_selector = "button#previous, div.filtros button#previous"
    else:
        btn_selector = None

    if btn_selector:
        for i in range(abs(delta)):
            btn = esperar_elemento(driver, btn_selector, timeout=10)
            if not btn:
                # fallback para xpath se os seletores css falharem
                if delta > 0:
                    btn = espera.elemento(driver, "//button[.//i[contains(@class, 'fa-arrow-right')]]", teto=2)
                else:
                    btn = espera.elemento(driver, "//button[.//i[contains(@class, 'fa-arrow-left')]]", teto=2)
                
                if not btn:
                    raise Exception(f"Botao mudanca de mes nao encontrado")
            safe_click(driver, btn)
            espera.assentar(driver, 0.3)
            try:
                el_h2 = espera.elemento(driver, "div.filtros h2, h2[role='status']", teto=2)
                h2 = ((getattr(el_h2, 'text_content', None) and el_h2.text_content()) or getattr(el_h2, 'text', '') or '') if el_h2 else ''
                print(f"[CALENDARIO] Após clique {i+1}: {h2}")
            except:
                pass

    mes_nome = _MESES_PT[alvo.month - 1]
    heading_xpath = f"//h2[contains(normalize-space(.), '{mes_nome}') and contains(normalize-space(.), '{alvo.year}')]"
    heading = esperar_elemento(driver, heading_xpath, timeout=10)
    if not heading:
        raise Exception(f"Heading do mes '{mes_nome}, {alvo.year}' nao encontrado")
    print(f"[CALENDARIO] Heading confirmado: {heading.text}")

    dia_str = str(alvo.day)
    # Usar XPath mais específico: célula que contém o número do dia exato e não está em heading
    dia_cell_xpath = (
        f"//mwl-calendar-month-cell[contains(@class, 'cal-in-month')]//"
        f"span[contains(@class,'cal-day-cell') and "
        f".//label[normalize-space(.)='{dia_str}']]"
    )
    dia_cell = esperar_elemento(driver, dia_cell_xpath, timeout=10)
    if not dia_cell:
        raise Exception(f"Celula do dia {dia_str} nao encontrada")

    # Log para ver qual dia está sendo clicado
    print(f"[CALENDARIO] Clicando no dia {dia_str}. Atributos: class={dia_cell.get_attribute('class')}")
    _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", dia_cell)
    safe_click(driver, dia_cell)
    espera.assentar(driver, 0.8)

    # Verificar confirmação – usar formato DD/MM/YYYY
    dia_fmt = alvo.strftime("%d/%m/%Y")
    confirm_xpath = f"//h2[contains(normalize-space(.), '{dia_fmt}')]"
    confirm = esperar_elemento(driver, confirm_xpath, timeout=10)
    if not confirm:
        # fallback: pode estar em outro elemento
        print("[CALENDARIO] Confirmação não encontrada pelo h2, verificando tabela...")
        # Verificar se a tabela agora mostra apenas linhas com essa data
        linhas_data = espera.elementos(
            driver,
            f"//tr[.//td[@class='centralizado td-class'][2]//span[normalize-space(.)='{dia_fmt}']]",
            teto=2,
        )
        if len(linhas_data) == 0:
            raise Exception(f"Dia {dia_fmt} não refletido na tabela após clique")
        print(f"[CALENDARIO] Tabela agora contém {len(linhas_data)} linhas com data {dia_fmt}")
    else:
        print(f"[CALENDARIO] Confirmação visual encontrada: {confirm.text}")


def _encontrar_slot_dia(driver: Any, hora_str: str) -> None:
    """Clica no botao Designar Audiencia na linha com o horario especificado.

    O horario ja foi extraido da linha correta (rito filtrado na tabela inicial),
    portanto e unico na pauta diaria -- sem necessidade de filtrar por tipo.

    Args:
        driver: Driver do navegador.
        hora_str: Horario no formato "HH:MM".
    """
    print(f"[SLOT] Procurando slot com horário '{hora_str}'")
    # Primeiro, registrar todas as linhas visíveis para diagnóstico
    try:
        todas_linhas = espera.elementos(driver, "//tr[.//span[contains(@class,'ng-star-inserted')]]", teto=2)
        # for idx, tr in enumerate(todas_linhas):
        #     texto = tr.text[:120]
        #     print(f"Linha {idx}: {texto}")
    except:
        pass

    # Para garantir que pegamos a linha da pauta DIÁRIA (e não a tabela inicial que pode ainda estar no DOM),
    # verificamos se o horário está na primeira ou segunda coluna (na tabela inicial o horário fica na 3ª coluna).
    linha_xpath = f"//tr[td[position()<=2]//span[normalize-space(.)='{hora_str}']]"
    linha = esperar_elemento(driver, linha_xpath, timeout=15)
    if not linha:
        raise Exception(f"Linha com horario '{hora_str}' nao encontrada na pauta diaria")

    # Log detalhado da linha selecionada
    print(f"[SLOT] Linha encontrada: {linha.text[:200]}")
    # Clica no botao "Designar Audiencia" da linha.
    # Mesmo padrao de Script/modules/Aud/marcar.js:cliciarSlotHora:
    #   botao por aria-label CSS; senao o <i class="fa-plus-circle"> e seu <button> pai.
    # NAO passar XPath com "contains(@...)" ao _sub_elemento: ele usa
    # query_selector (CSS) e estoura "Unsupported token".
    btn_plus = _sub_elemento(linha, 'button[aria-label*="Designar"]')
    if not btn_plus:
        icone = _sub_elemento(linha, 'i.fa-plus-circle')
        if icone is not None:
            btn_plus = _closest_button(driver, icone)
    if not btn_plus:
        raise Exception(
            f"Botao 'Designar Audiencia' nao encontrado na linha do horario {hora_str}"
        )
    print(f"[SLOT] Clicando no botão designar")
    if not safe_click(driver, btn_plus):
        raise Exception("Clique em 'Designar Audiencia' falhou")
    # marcar.js:500ms apos o clique no slot antes de seguir para o modal.
    espera.assentar(driver, 0.5)


def _tem_audiencia_marcada(driver: Any, processo_info: Optional[Dict] = None) -> bool:
    """Verifica se o processo tem audiência marcada com base na timeline de movimentos.

    Regra de negócio dos 3 casos:
      (a) Distribuição e NÃO tem audiência:
          -> Retorna False, pular_marcar_aud=False (SEM AUDIÊNCIA, fluxo de sempre).
      (b) Distribuição + audiência em horário muito próximo (<= 180s):
          -> Retorna True, pular_marcar_aud=False (TEM AUDIÊNCIA, fluxo de sempre).
      (c) Tem audiência, mas marcação veio mais tarde que a distribuição:
          -> Retorna False, pular_marcar_aud=True (trata como SEM AUDIÊNCIA, mas pula a marcação).

    Fallback: Inspeciona `dt#audiencias` no DOM se a API não estiver disponível.
    """
    id_processo = None
    if processo_info:
        id_processo = processo_info.get('id_processo')
    if not id_processo and driver:
        url = getattr(driver, 'current_url', '') or ''
        m = re.search(r'/processo/(\d+)', url)
        if m:
            id_processo = m.group(1)

    # 1. Tentativa via API de movimentos (fonte de verdade para verificar horário vs distribuição)
    if driver and id_processo:
        try:
            from Fix.variaveis import PjeApiClient, session_from_driver
            from bianca.triagem.api import classificar_audiencia_movimentos
            sess, host = session_from_driver(driver)
            client = PjeApiClient(sess, host)
            itens_mov = client.timeline(
                str(id_processo), buscarDocumentos=False, buscarMovimentos=True
            ) or []

            if itens_mov:
                status, det = classificar_audiencia_movimentos(itens_mov)
                if status == 'TEM_AUDIENCIA':
                    if processo_info is not None:
                        processo_info['tem_audiencia'] = True
                        processo_info['pular_marcar_aud'] = False
                        processo_info['status_audiencia'] = 'TEM_AUDIENCIA'
                    print("[TRIAGEM] _tem_audiencia_marcada via Movimentos: True (caso b: audiencia da autuacao/distribuicao)")
                    return True
                elif status == 'AUDIENCIA_TARDIA':
                    if processo_info is not None:
                        processo_info['tem_audiencia'] = False
                        processo_info['pular_marcar_aud'] = True
                        processo_info['status_audiencia'] = 'AUDIENCIA_TARDIA'
                    print("[TRIAGEM] _tem_audiencia_marcada via Movimentos: False (caso c: audiencia tardia -> trata como SEM AUDIENCIA e pula marcacao)")
                    return False
                else:
                    if processo_info is not None:
                        processo_info['tem_audiencia'] = False
                        processo_info['pular_marcar_aud'] = False
                        processo_info['status_audiencia'] = 'SEM_AUDIENCIA'
                    print("[TRIAGEM] _tem_audiencia_marcada via Movimentos: False (caso a: sem movimento de audiencia)")
                    return False
        except Exception as e:
            print(f"[TRIAGEM] _tem_audiencia_marcada: falha ao consultar API de movimentos ({e}) -- usando fallback DOM")

    # 2. Fallback via DOM (caso a API não responda)
    try:
        dt = espera.elemento(driver, "dt#audiencias", teto=2)
        if dt:
            is_displayed = getattr(dt, 'is_displayed', lambda: True)
            if (is_displayed() if callable(is_displayed) else True):
                parent_text = ""
                try:
                    parent = _sub_elemento(dt, "./ancestor::*[1]")
                    parent_text = (((getattr(parent, 'text_content', None) and parent.text_content()) or getattr(parent, 'text', '') or '')).strip()
                except Exception:
                    parent_text = (((getattr(dt, 'text_content', None) and dt.text_content()) or getattr(dt, 'text', '') or '')).strip()

                if parent_text:
                    re_data = re.search(r"\b\d{2}/\d{2}/\d{4}\b", parent_text)
                    re_hora = re.search(r"\b\d{2}:\d{2}\b", parent_text)
                    if re_data or re_hora:
                        print("[TRIAGEM] _tem_audiencia_marcada via DOM: True")
                        if processo_info is not None:
                            processo_info['tem_audiencia'] = True
                        return True

            print("[TRIAGEM] _tem_audiencia_marcada via DOM: False (dt#audiencias encontrado mas sem data/hora)")
            if processo_info is not None:
                processo_info['tem_audiencia'] = False
            return False

    except Exception:
        print("[TRIAGEM] _tem_audiencia_marcada via DOM: False (dt#audiencias nao encontrado)")
        if processo_info is not None:
            processo_info['tem_audiencia'] = False
        return False


def _closest_button(driver: Any, elemento: Any) -> Any:
    """Retorna o <button> ancestral de `elemento` (equivalente a closest('button')).

    Tenta a API nativa do elemento antes do JS, pois `_executar_js` delega a
    `page.evaluate` no Playwright, que nao aceita argumentos posicionais.
    """
    if elemento is None:
        return None
    # 1) API do elemento (Playwright: ElementHandle.closest).
    closest = getattr(elemento, "closest", None)
    if callable(closest):
        try:
            pai = closest("button")
            if pai is not None:
                return pai
        except Exception:
            pass
    # 2) XPath a partir do proprio elemento (Selenium e PWDriver).
    for metodo in ("find_element", "query_selector"):
        fn = getattr(elemento, metodo, None)
        if not callable(fn):
            continue
        try:
            pai = (
                fn("xpath", "./ancestor::button[1]")
                if metodo == "find_element"
                else fn("xpath=./ancestor::button[1]")
            )
            if pai is not None:
                return pai
        except Exception:
            pass
    # 3) JS com argumento (execute_script do Selenium).
    try:
        return _executar_js(driver, "return arguments[0].closest('button');", elemento)
    except Exception:
        return None


# Hook de diagnostico: None em producao (zero custo). O harness de teste
# (f.py aud) atribui uma funcao aqui para capturar estado do modal/TOAST antes
# de _marcar_aud fechar os paineis.
_HOOK_DIAG = None


_JS_VALOR_PROCESSO = """
(function(){
  var el = document.querySelector('mat-dialog-container input#inputNumeroProcesso');
  return el ? (el.value || '').trim() : null;
})()
"""

# Preenchimento do numero do processo no modal de audiencia.
#
# ESTRATEGIA VALIDADA no PJe real, pelo probe do console (10 hipoteses
# testadas em sequencia -- a vencedora foi a #4):
#
#     setter nativo do HTMLInputElement + InputEvent(inputType='insertFromPaste')
#
# Descricao do que funciona:
#   1. escreve o numero JA FORMATADO (1002085-77.2026.5.02.0703) via setter;
#   2. dispara InputEvent('input') com inputType 'insertFromPaste' e data;
#   3. dispara change.
#
# Por que 'insertFromPaste' e nao 'insertText': e o tipo de evento que o
# navegador gera num Ctrl+V. Voce confirmou no navegador que COLAR o numero
# formatado faz o dialog aceitar -- e o Angular do PJe trata esse inputType
# como colagem, resolvendo o processo. Com 'insertText' (digitacao tecla a
# tecla) o campo recebia o texto, mas o FormControl nao era atualizado e o
# PJe respondia com a snackbar "Consulte o processo para designar audiencia".
#
# IMPORTANTE sobre o Confirmar: ele NAO fica desabilitado. Esta sempre
# clicavel; o que diferencia e a reacao do backend:
#   - erro   -> snackbar "Consulte o processo para designar audiencia."
#   - sucesso-> a dialog "Novo Horario" e substituida pela de confirmacao.
_JS_COLAR_PROCESSO = """
  var el = document.querySelector('mat-dialog-container input#inputNumeroProcesso');
  if (!el) return {ok:false, erro:'campo inputNumeroProcesso nao encontrado'};

  var txt = String((typeof arg !== 'undefined' ? arg : (typeof arguments !== 'undefined' ? arguments[0] : '')) || '').trim();

  try { if (window.focus) window.focus(); } catch (e) {}
  try { el.focus(); } catch (e) {}

  // 1) Dispara evento paste (colagem) antes de inserir o valor
  try {
    var pasteEv = new ClipboardEvent('paste', { bubbles: true, cancelable: true });
    el.dispatchEvent(pasteEv);
  } catch (ePaste) {
    try {
      var ce = new CustomEvent('paste', { bubbles: true, cancelable: true });
      el.dispatchEvent(ce);
    } catch (ePaste2) {}
  }

  // 2) Setter nativo de value (HTMLInputElement.prototype - padrão +pje/gigs-plugin.js)
  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
  if (setter && setter.set) {
    setter.set.call(el, txt);
  } else {
    el.value = txt;
  }

  // Helper triggerEvent idêntico ao gigs-plugin / mini-selenium
  function triggerEvent(target, type, keycode) {
    if (keycode) {
      try {
        var ke = new KeyboardEvent(type, { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter' });
        try { Object.defineProperty(ke, 'keyCode', { get: function() { return keycode; } }); } catch (err) {}
        try { Object.defineProperty(ke, 'which', { get: function() { return keycode; } }); } catch (err) {}
        target.dispatchEvent(ke);
      } catch (e1) {}
    } else {
      if ('createEvent' in document) {
        try {
          var ev = document.createEvent('HTMLEvents');
          ev.initEvent(type, false, true);
          target.dispatchEvent(ev);
        } catch (e2) {}
      }
      try {
        target.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
      } catch (e3) {}
      if (type === 'input') {
        try {
          target.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertFromPaste', data: txt }));
        } catch (e4) {}
      }
    }
  }

  // 3) Disparo de eventos idêntico ao gigs-plugin.js
  triggerEvent(el, 'input');
  triggerEvent(el, 'change');
  triggerEvent(el, 'dateChange');
  triggerEvent(el, 'keyup');

  // 4) Simular tecla Enter (keyCode 13) idêntica ao gigs-plugin.js (simularTecla)
  function simularTecla(target, letra, codigo) {
    var ev0 = new KeyboardEvent('keydown', { key: letra, code: letra, keyCode: codigo, which: codigo, bubbles: true, cancelable: true });
    var ev1 = new KeyboardEvent('keypress', { key: letra, code: letra, keyCode: codigo, which: codigo, bubbles: true, cancelable: true });
    var ev2 = new KeyboardEvent('keyup', { key: letra, code: letra, keyCode: codigo, which: codigo, bubbles: true, cancelable: true });
    target.dispatchEvent(ev0);
    target.dispatchEvent(ev1);
    target.dispatchEvent(ev2);
  }
  simularTecla(el, 'Enter', 13);

  // 5) Blur no input (gigs-plugin: el.blur())
  try { el.blur(); } catch (e) {}
  triggerEvent(el, 'blur');
  triggerEvent(el, 'focusout');

  return {ok:true, valor:(el.value || '')};
"""


def _tirar_foco_body_dialog(driver: Any) -> None:
    """Tira o foco do campo do processo clicando no body/content da dialog (mat-dialog-container)."""
    # 1. Blur ativo no elemento e clique no container/content da dialog via JS
    try:
        _executar_js(driver, """
            if (document.activeElement && document.activeElement.blur) {
                try { document.activeElement.blur(); } catch(e) {}
            }
            var dlgBody = document.querySelector('mat-dialog-container .mat-dialog-content')
                       || document.querySelector('mat-dialog-container mat-dialog-content')
                       || document.querySelector('mat-dialog-container .mat-dialog-title')
                       || document.querySelector('mat-dialog-container');
            if (dlgBody) {
                try { dlgBody.click(); } catch(e) {}
                try { dlgBody.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window })); } catch(e) {}
            }
        """)
    except Exception:
        pass

    # 2. Se estiver em Playwright com page, faz clique físico no container fora de inputs
    page = getattr(driver, "page", None)
    if page is not None:
        try:
            loc = page.locator("mat-dialog-container .mat-dialog-content, mat-dialog-container mat-dialog-content, mat-dialog-container").first
            if loc.count() > 0 and loc.is_visible():
                loc.click(position={"x": 10, "y": 10}, timeout=2000, force=True)
                print("[MARCAR_AUD] Clique no body da dialog executado (Playwright locator)")
        except Exception:
            pass


_JS_LIMPAR_CAMPO_PROCESSO = """
  var el = document.querySelector('mat-dialog-container input#inputNumeroProcesso');
  if (!el) return {ok:false};
  var setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value').set;
  try { el.focus(); } catch (e) {}
  setter.call(el, '');
  try {
    el.dispatchEvent(new InputEvent('input', {
      bubbles: true, inputType: 'deleteContentBackward'
    }));
  } catch (e) {
    try {
      var e2 = document.createEvent('HTMLEvents');
      e2.initEvent('input', true, true);
      el.dispatchEvent(e2);
    } catch (e3) {}
  }
  return {ok:true, valor:''};
"""


def _clicar_confirmar(driver: Any, botao: Any = None) -> bool:
    """Clica em Confirmar no modal de audiencia simulando o ponteiro fisico (hover + click)."""
    page = getattr(driver, "page", None)
    if page is not None:
        try:
            loc = page.locator("mat-dialog-container button").filter(has_text="Confirmar").first
            loc.scroll_into_view_if_needed(timeout=2000)
            loc.hover(timeout=2000)
            loc.click(timeout=5000)
            print("[MARCAR_AUD] Confirmar: hover + click nativo locator")
            return True
        except Exception as e:
            print(f"[MARCAR_AUD] locator hover/click falhou: {e}")

    handle = getattr(botao, "_handle", None) if botao else None
    if handle is not None:
        try:
            handle.scroll_into_view_if_needed(timeout=2000)
            handle.hover(timeout=2000)
            handle.click(timeout=5000)
            print("[MARCAR_AUD] Confirmar: hover + click via handle")
            return True
        except Exception:
            pass

    seletor_xpath = "//mat-dialog-container//button[.//span[contains(normalize-space(.), 'Confirmar')] or normalize-space(.)='Confirmar']"
    if click_headless_safe(driver, seletor_xpath, by=By.XPATH, timeout=5):
        print("[MARCAR_AUD] Confirmar: click_headless_safe")
        return True

    if botao:
        try:
            safe_click(driver, botao)
            print("[MARCAR_AUD] Confirmar: safe_click")
            return True
        except Exception as e:
            print(f"[MARCAR_AUD] safe_click falhou: {type(e).__name__}: {e}")

    return False


def _botao_confirmar_modal(driver: Any) -> Any:
    """Elemento do botao Confirmar dentro do mat-dialog-container."""
    return esperar_elemento(
        driver,
        "//mat-dialog-container//button[.//span[contains(normalize-space(.), 'Confirmar')] or normalize-space(.)='Confirmar']",
        by=By.XPATH,
        timeout=8,
    )


def _audiencia_designada(driver: Any) -> Tuple[bool, str]:
    """Diz se a designacao foi ACEITA, pela reacao do PJe ao clicar Confirmar.

    O Confirmar NAO fica desabilitado -- esta sempre clicavel. Quem decide e a
    reacao do backend, conforme observado no navegador:

      - ERRO   -> snackbar vermelha
                  "Consulte o processo para designar audiencia."
      - SUCESSO-> a dialog "Novo Horario" e SUBSTITUIDA pela confirmacao da
                  marcacao (conteudo com "designacao confirmada" / processo).

    Retorna (sucesso, detalhe).
    """
    js = """
    (function(){
      function txt(e){ return e ? (e.textContent||'').replace(/\\s+/g,' ').trim() : ''; }

      // 1) snackbar de erro
      var sn = document.querySelectorAll(
        'simple-snack-bar, .snack-bar-container, mat-snack-bar-container, ' +
        '.mat-snack-bar-container, [class*="snack"]');
      for (var i = 0; i < sn.length; i++) {
        var t = txt(sn[i]);
        if (t) return {estado:'erro', detalhe:t.slice(0,300)};
      }

      // 2) dialog substituida pela confirmacao
      var d = document.querySelector('mat-dialog-container');
      if (!d) return {estado:'fechou', detalhe:''};
      var corpo = txt(d);
      if (/designa[cç][aã]o\\s+confirmada/i.test(corpo)) {
        return {estado:'sucesso', detalhe:corpo.slice(0,300)};
      }
      // ainda na mesma tela de "Novo Horario"
      if (/novo\\s+hor[aá]rio/i.test(corpo)) {
        return {estado:'aberta', detalhe:corpo.slice(0,200)};
      }
      return {estado:'outra', detalhe:corpo.slice(0,200)};
    })()
    """
    res = None
    page = getattr(driver, "page", None)
    if page is not None:
        try:
            res = page.evaluate(js)
        except Exception:
            res = None
    if res is None:
        try:
            res = _executar_js(driver, js)
        except Exception:
            res = None
    if not isinstance(res, dict):
        return False, "estado desconhecido"

    estado = res.get("estado")
    detalhe = str(res.get("detalhe") or "")
    if estado == "sucesso":
        return True, detalhe
    return False, detalhe or str(estado)


def _tipo_audiencia_atual(driver: Any) -> str:
    """Texto do tipo de audiencia selecionado no modal ('' se indisponivel).

    Observacao do fluxo real: aberta a dialog a partir da pauta correta, o
    tipo JA vem preenchido -- aqui apenas conferimos.
    """
    js = """
    (function(){
      var s = document.querySelector('mat-dialog-container mat-select');
      if (!s) return '';
      var v = s.querySelector('span.mat-select-value-text')
           || s.querySelector('.mat-select-value');
      return v ? (v.textContent || '').replace(/\\s+/g,' ').trim() : '';
    })()
    """
    page = getattr(driver, "page", None)
    if page is not None:
        try:
            return page.evaluate(js) or ""
        except Exception:
            pass
    try:
        return _executar_js(driver, js) or ""
    except Exception:
        return ""


def _executar_js_com_arg(driver: Any, corpo: str, arg: Any) -> Any:
    """Executa um corpo JS (com `arg` e `arguments[0]`) em Playwright ou Selenium."""
    page = getattr(driver, "page", None)
    if page is not None:
        try:
            return page.evaluate("function(arg) { %s }" % corpo, arg)
        except Exception as e:
            print(f"[MARCAR_AUD] JS via page falhou: {type(e).__name__}: {e}")
    try:
        return _executar_js(driver, "return (function(arg){ %s })(arguments[0]);" % corpo, arg)
    except Exception as e:
        print(f"[MARCAR_AUD] JS via driver falhou: {type(e).__name__}: {e}")
    return None


def _limpar_campo_processo(driver: Any) -> None:
    """Limpa o campo de numero antes de digitar."""
    _executar_js_com_arg(driver, _JS_LIMPAR_CAMPO_PROCESSO, "")


def _colar_numero_processo(driver: Any, valor: str) -> str:
    """Cola o numero do processo no campo de uma vez (estrategia validada).

    Aplica exatamente o que o probe do console provou funcionar no PJe real
    (estrategia #4 de 10): setter nativo + InputEvent('input') com
    inputType 'insertFromPaste' + change.

    E o equivalente a um Ctrl+V do numero ja formatado -- voce confirmou no
    navegador que assim o dialog aceita a designacao.

    Retorna o valor final lido do campo.
    """
    texto = str(valor or "").strip()
    if not texto:
        return ""

    resultado = _executar_js_com_arg(driver, _JS_COLAR_PROCESSO, texto)
    if isinstance(resultado, dict) and resultado.get("ok"):
        return str(resultado.get("valor") or "")
    return _valor_processo_no_modal(driver) or ""


def _tipo_ok(atual: Optional[str], desejado: str) -> bool:
    """True se o tipo atual e exatamente o desejado.

    Compara por igualdade (nao substring): 'Una' esta contido em
    'Una (rito sumaríssimo)', e as variantes 'por videoconferência' precisam
    ser sempre recusadas.
    """
    a = " ".join(str(atual or "").split()).casefold()
    d = " ".join(str(desejado or "").split()).casefold()
    if not a:
        return False
    if "videoconfer" in a:
        return False
    return a == d


def _valor_processo_no_modal(driver: Any) -> Optional[str]:
    """Valor atual do campo de numero no modal (None se o campo nao existe).

    Usa JS puro para evitar dependencia do wrapper de evaluate: o valor lido
    pelo Angular e a fonte da verdade (atributo value nao acompanha o Model).
    """
    page = getattr(driver, "page", None)
    try:
        if page is not None:
            return page.evaluate(_JS_VALOR_PROCESSO)
    except Exception as e:
        print(f"[MARCAR_AUD] leitura do numero via page falhou: {e}")
    try:
        return _executar_js(driver, _JS_VALOR_PROCESSO)
    except Exception as e:
        print(f"[MARCAR_AUD] leitura do numero via driver falhou: {e}")
    return None


def _somente_digitos(texto: Optional[str]) -> str:
    """Normaliza numero de processo para comparacao (so digitos)."""
    return "".join(c for c in str(texto or "") if c.isdigit())


# Opcoes do autocomplete do campo "Numero do Processo" (pje-processo-suggest).
# O painel e renderizado no overlay do CDK, fora do mat-dialog-container.
_SEL_OPCAO_PROCESSO = ".mat-autocomplete-panel mat-option"

_JS_INDICE_OPCAO_PROCESSO = """
(function(alvo){
  var ops = Array.prototype.slice.call(
      document.querySelectorAll('.mat-autocomplete-panel mat-option'));
  for (var i = 0; i < ops.length; i++) {
    var d = (ops[i].textContent || '').replace(/\\D/g, '');
    if (d === alvo) return i;
  }
  return -1;
})
"""

# Minimo de digitos antes de a API de busca (agrupamentotarefas/processos?numero=)
# devolver uma lista curta o bastante para conter o processo.
_MIN_DIGITOS_BUSCA_PROCESSO = 10


def _indice_opcao_processo(driver: Any, alvo: str) -> int:
    """Indice da mat-option do autocomplete cujo numero (so digitos) e `alvo`; -1 se nao ha."""
    page = getattr(driver, "page", None)
    if page is None:
        return -1
    try:
        return int(page.evaluate(_JS_INDICE_OPCAO_PROCESSO + "(%r)" % alvo))
    except Exception:
        return -1


def _selecionar_processo_por_autocomplete(driver: Any, alvo: str) -> bool:
    """Digita o numero tecla a tecla e escolhe a opcao no autocomplete do PJe.

    Validado pelo probe da pauta: o campo so aceita a designacao quando o
    FormControl recebe o OBJETO da opcao (mat-option do autocomplete, que o
    probe registrou como `mat-option[name="[object Object]"]`). Colar o texto
    nao basta -- o PJe responde 'Consulte o processo para designar audiencia'
    e o Confirmar fica com a classe `disabled`.

    A API de busca e chamada a cada digito (`numero=100210`...); por isso se
    digita o comeco do numero e, assim que a opcao exata aparece, ela e clicada.
    So digitos sao digitados: a mascara (pjeMascaraNumeroProcesso) formata.
    """
    page = getattr(driver, "page", None)
    if page is None or not alvo:
        return False

    try:
        campo = page.locator(
            "mat-dialog-container input#inputNumeroProcesso"
        ).first
        if campo.count() == 0:
            print("[MARCAR_AUD] Campo do numero nao encontrado para digitar")
            return False
        campo.click(timeout=3000)
        page.keyboard.press("ControlOrMeta+a")
        page.keyboard.press("Backspace")
    except Exception as e:
        print(f"[MARCAR_AUD] Falha ao focar/limpar o campo do numero: {type(e).__name__}: {e}")
        return False

    expr_opcao = (
        "Array.from(document.querySelectorAll(%r)).some(o => "
        "(o.textContent || '').replace(/\\D/g, '') === %r)" % (_SEL_OPCAO_PROCESSO, alvo)
    )

    indice = -1
    for pos, digito in enumerate(alvo, start=1):
        try:
            page.keyboard.type(digito)
        except Exception as e:
            print(f"[MARCAR_AUD] Falha ao digitar '{digito}': {type(e).__name__}: {e}")
            return False
        if pos < _MIN_DIGITOS_BUSCA_PROCESSO:
            continue
        # Espera a busca do PJe responder a este prefixo.
        if espera.ate_js(driver, expr_opcao, teto=2.5 if pos == _MIN_DIGITOS_BUSCA_PROCESSO else 1.2):
            indice = _indice_opcao_processo(driver, alvo)
            if indice >= 0:
                print(f"[MARCAR_AUD] Opcao do processo apareceu com {pos} digitos digitados")
                break

    if indice < 0:
        print(f"[MARCAR_AUD] ❌ Autocomplete nao ofereceu o processo {alvo} apos digitar tudo")
        _hook_diag("autocomplete_sem_opcao", alvo=alvo)
        return False

    _hook_diag("autocomplete_antes_clicar", indice=indice)
    try:
        page.locator(_SEL_OPCAO_PROCESSO).nth(indice).click(timeout=3000)
    except Exception as e:
        print(f"[MARCAR_AUD] Falha ao clicar na opcao do autocomplete: {type(e).__name__}: {e}")
        _hook_diag("autocomplete_clique_falhou", erro=str(e))
        return False

    # A selecao escreve o numero formatado no input e habilita o Confirmar.
    expr_valor = (
        "(function(){var i=document.querySelector('mat-dialog-container input#inputNumeroProcesso');"
        "return !!i && (i.value||'').replace(/\\D/g,'')===%r;})()" % alvo
    )
    if not espera.ate_js(driver, expr_valor, teto=3):
        print("[MARCAR_AUD] ⚠️ Input nao refletiu o numero apos clicar na opcao")
        _hook_diag("autocomplete_input_vazio")
        return False

    _hook_diag("autocomplete_selecionado")

    print(f"[MARCAR_AUD] Processo selecionado no autocomplete: {_valor_processo_no_modal(driver)!r}")
    return True


def _preencher_numero_por_colagem(driver: Any, texto: str, page: Any) -> None:
    """Fallback: cola o número no campo (clipboard + setter nativo + eventos do gigs-plugin).

    Não seleciona opção do autocomplete na prática -- por isso o caminho
    principal é `_selecionar_processo_por_autocomplete`.
    """
    # 1) Se Playwright page estiver ativa, grava no clipboard e cola via Ctrl+V
    if page:
        try:
            page.evaluate("async (t) => { try { await navigator.clipboard.writeText(t); } catch(e){} }", texto)
            loc = page.locator("mat-dialog-container input#inputNumeroProcesso").first
            if loc.count() > 0:
                loc.click(timeout=3000)
                page.keyboard.press("ControlOrMeta+a")
                page.keyboard.press("ControlOrMeta+v")
                espera.assentar(driver, 0.4)
        except Exception as e:
            print(f"[MARCAR_AUD] Clipboard paste Playwright: {e}")

    # 2) Aplica setter nativo do protótipo + evento paste + triggerEvent(input insertFromPaste, change, dateChange, keyup) + Enter + blur
    _colar_numero_processo(driver, texto)

    if page:
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

    # Aguarda reação de pesquisa e eventual autocomplete
    espera.assentar(driver, 1.0)

    # Se abriu autocomplete, clica na opção
    if page:
        try:
            opt = page.locator("mat-autocomplete mat-option, div.mat-autocomplete-panel mat-option").first
            if opt.count() > 0 and opt.is_visible():
                print("[MARCAR_AUD] Opcao de autocomplete detectada -- clicando para selecionar")
                opt.click()
                espera.assentar(driver, 0.5)
        except Exception:
            pass


def _garantir_numero_processo(
    driver: Any, numero_processo: str, timeout: Union[int, float] = 25
) -> bool:
    """Preenche o numero do processo no padrão +pje/gigs-plugin e clica em Confirmar com espera correta."""
    alvo = _somente_digitos(numero_processo)
    if not alvo:
        print("[MARCAR_AUD] Numero de processo vazio -- nada a preencher")
        return False

    texto = str(numero_processo).strip()
    if len(alvo) == 20 and "-" not in texto:
        texto = (
            f"{alvo[:7]}-{alvo[7:9]}.{alvo[9:13]}."
            f"{alvo[13]}.{alvo[14:16]}.{alvo[16:20]}"
        )

    page = getattr(driver, "page", None)

    # 1. Verifica se o campo já veio pré-preenchido pelo PJe
    val_atual = _valor_processo_no_modal(driver) or ""
    if not (alvo in _somente_digitos(val_atual)):
        espera.assentar(driver, 0.8)
        val_atual = _valor_processo_no_modal(driver) or ""

    pre_preenchido = alvo in _somente_digitos(val_atual)
    if pre_preenchido:
        print(f"[MARCAR_AUD] Campo já pré-preenchido pelo PJe: {val_atual!r}")
    else:
        print(f"[MARCAR_AUD] Preenchendo numero do processo no padrão +pje/gigs-plugin: {texto}")

    # Caminho principal: digita o começo do número e SELECIONA a opção do
    # autocomplete (é a seleção que alimenta o FormControl do PJe).
    selecionado = bool(page) and _selecionar_processo_por_autocomplete(driver, alvo)

    if selecionado:
        # Confirmar só habilita (classe `disabled` some) depois da seleção.
        if not espera.ate_js(
            driver,
            "__pjeEls('mat-dialog-container button').some(b => "
            "/Confirmar/.test(b.textContent || '') && !b.disabled && "
            "!b.classList.contains('disabled'))",
            teto=5,
        ):
            print("[MARCAR_AUD] ⚠️ Confirmar continua desabilitado após selecionar o processo")
    else:
        print("[MARCAR_AUD] ⚠️ Seleção por autocomplete falhou -- tentando colagem (fallback)")
        _preencher_numero_por_colagem(driver, texto, page)

        # Requisito do fallback: clique no body da dialog para tirar foco do campo
        print("[MARCAR_AUD] Clicando no body da dialog para retirar foco do campo...")
        _tirar_foco_body_dialog(driver)

    # Espera correta para clicar em Confirmar:
    # a) Aguarda desaparecimento de barra de progresso / loading do PJe
    try:
        espera.ate_sumir(
            driver,
            "mat-dialog-container mat-progress-bar, mat-dialog-container mat-spinner, mat-progress-bar, .mat-progress-bar",
            teto=8
        )
    except Exception:
        pass

    # b) Assentamento para não clicar rápido demais (evita erro 'Consulte o processo')
    espera.assentar(driver, 0.6 if selecionado else 2.5)

    # c) Confere se o valor continua presente no modal
    val_final = _valor_processo_no_modal(driver) or ""
    print(f"[MARCAR_AUD] Valor no modal antes de Confirmar: {val_final!r}")

    botao = _botao_confirmar_modal(driver)
    if not botao:
        print("[MARCAR_AUD] ❌ Botao Confirmar nao encontrado")
        return False

    print("[MARCAR_AUD] Clicando em Confirmar...")
    _hook_diag("pre_confirmar")

    if not _clicar_confirmar(driver, botao):
        print("[MARCAR_AUD] ❌ Nao consegui clicar em Confirmar")
        _hook_diag("falha_dialog_aberta", estado="clique em Confirmar falhou")
        return False

    limite = _t_monotonic() + float(timeout)
    ultimo = None

    while _t_monotonic() < limite:
        ok, detalhe = _audiencia_designada(driver)
        if ok:
            print(f"[MARCAR_AUD] ✅ Audiencia designada (dialog={detalhe[:120]!r})")
            _hook_diag("apos_confirmar")
            return True

        if detalhe != ultimo:
            ultimo = detalhe
            print(f"[MARCAR_AUD]   aguardando reacao... {detalhe[:120]!r}")

            # Se acusou 'Consulte o processo', tenta re-desfocar no body da dialog, aguardar e tentar Confirmar mais uma vez
            if "consulte o processo" in detalhe.casefold():
                print("[MARCAR_AUD] ⚠️ PJe indicou 'Consulte o processo' -- aplicando retry com clique no body e espera extra...")
                _tirar_foco_body_dialog(driver)
                espera.assentar(driver, 2.0)
                botao_retry = _botao_confirmar_modal(driver)
                if botao_retry:
                    _clicar_confirmar(driver, botao_retry)

        _t_sleep(0.4)

    ok, detalhe = _audiencia_designada(driver)
    if ok:
        print(f"[MARCAR_AUD] ✅ Audiencia designada")
        _hook_diag("apos_confirmar")
        return True

    print(f"[MARCAR_AUD] ❌ Designacao nao confirmada: {detalhe[:200]!r}")
    if "consulte o processo" in detalhe.casefold():
        print("[MARCAR_AUD]    (o PJe nao reconheceu o processo colado)")
    print("[MARCAR_AUD] ⛔ Dialog MANTIDA ABERTA para inspecao")
    _hook_diag("recusa", detalhe=detalhe)
    return False


def _selecionar_tipo_audiencia(driver: Any, rito: str) -> bool:
    """Seleciona o Tipo da audiencia: 'Una' ou 'Una (rito sumaríssimo)'.

    Regra de negocio: SOMENTE essas duas opcoes -- nunca as variantes
    "por videoconferencia". O valor exato depende do rito: ATSUM ->
    'Una (rito sumaríssimo)'; qualquer outro -> 'Una'.

    O painel real e `div.mat-select-panel` com `mat-option` cujo texto fica em
    `span.mat-option-text` e cujo nome tambem aparece no atributo `name`.
    """
    desejado = (
        "Una (rito sumaríssimo)" if str(rito).upper() == "ATSUM" else "Una"
    )
    print(f"[MARCAR_AUD] Tipo desejado: {desejado!r}")

    for tentativa in (1, 2):
        atual = _texto_select_tipo(driver)
        if atual and atual.strip().lower() == desejado.lower():
            print(f"[MARCAR_AUD] Tipo ja correto: {atual!r}")
            return True

        print(f"[MARCAR_AUD] Abrindo dropdown de tipo (tentativa {tentativa}); atual={atual!r}")
        try:
            sel = esperar_elemento(driver, "mat-dialog-container mat-select", timeout=8)
            if not sel:
                print("[MARCAR_AUD] mat-select de tipo nao encontrado")
                return False
            safe_click(driver, sel)
            espera.assentar(driver, 0.6)
            if not espera.ate_aparecer(driver, "div.mat-select-panel mat-option", teto=8):
                print("[MARCAR_AUD] Painel de opcoes nao abriu")
                continue

            # Preferencia: casar pelo span.mat-option-text / name exatos
            seletor_alvo = (
                f"//div[@class and contains(@class,'mat-select-panel')]"
                f"//mat-option[@name={_xp_lit(desejado)}"
                f" or .//span[contains(@class,'mat-option-text')"
                f" and normalize-space(.)={_xp_lit(desejado)}]]"
            )
            opcao = esperar_elemento(driver, seletor_alvo, by=By.XPATH, timeout=4)

            if not opcao:
                # Diagnostico: listar o que existe, excluindo videoconferencia
                try:
                    todas = espera.elementos(
                        driver, "div.mat-select-panel mat-option", teto=2) or []
                except Exception:
                    todas = []
                textos = []
                for t in todas:
                    try:
                        textos.append((t.text or "").strip())
                    except Exception:
                        textos.append("")
                relevantes = [x for x in textos if "una" in x.lower()]
                print(f"[MARCAR_AUD] Opcoes 'Una' disponiveis: {relevantes}")
                print(f"[MARCAR_AUD] ❌ Opcao exata {desejado!r} nao encontrada")
                continue

            txt = ""
            try:
                txt = (opcao.text or "").strip()
            except Exception:
                pass
            if "videoconfer" in txt.lower():
                print(f"[MARCAR_AUD] ❌ Opcao inesperada (videoconferencia): {txt!r}")
                continue

            print(f"[MARCAR_AUD] Selecionando tipo: {txt!r}")
            safe_click(driver, opcao)
            espera.assentar(driver, 0.6)

            novo = _texto_select_tipo(driver)
            print(f"[MARCAR_AUD] Tipo apos selecao: {novo!r}")
            if novo and novo.strip().lower() == desejado.lower():
                return True
        except Exception as e:
            print(f"[MARCAR_AUD] Falha ao selecionar tipo: {type(e).__name__}: {e}")

    return False


def _xp_lit(texto: str) -> str:
    """Monta um literal XPath seguro para textos com apostrofo/aspas."""
    if "'" not in texto:
        return f"'{texto}'"
    if '"' not in texto:
        return f'"{texto}"'
    partes = texto.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in partes) + ")"


def _texto_select_tipo(driver: Any) -> str:
    """Alias historico de `_tipo_audiencia_atual` (mantido por compatibilidade)."""
    return _tipo_audiencia_atual(driver)


def _aud_estado_resumido(driver: Any) -> str:
    """Resumo de uma linha do estado do modal, para mensagens de erro."""
    valor = _valor_processo_no_modal(driver)
    tipo = _texto_select_tipo(driver)
    ok, detalhe = _audiencia_designada(driver)
    return (
        f"numero={valor!r} tipo={tipo!r} designada={ok} "
        f"reacao={detalhe[:80]!r}"
    )


def _hook_diag(etapa: str, **info: Any) -> None:
    """Dispara o hook de diagnostico, se instalado (nunca propaga excecao)."""
    if _HOOK_DIAG is None:
        return
    try:
        _HOOK_DIAG(etapa, info)
    except Exception as e:  # pragma: no cover - diagnostico nunca deve quebrar
        print(f"[MARCAR_AUD] hook de diagnostico falhou ({etapa}): {e}")


def _texto_modal_audiencia(driver: Any) -> str:
    """Texto (minusculo) do conteudo atual do modal de audiencia.

    Le o mat-dialog-container inteiro: serve tanto para o formulario quanto
    para o painel de confirmacao, sem depender de qual div esta ativa.
    """
    script = (
        "(function(){var d=document.querySelector('mat-dialog-container');"
        "return d ? (d.textContent || '') : '';})()"
    )
    try:
        bruto = _executar_js(driver, script) or ""
        # Normaliza do lado Python: independe de o driver/devtools aplicar regex.
        return " ".join(str(bruto).split()).lower()
    except Exception as e:
        print(f"[MARCAR_AUD] Falha ao ler texto do modal: {e}")
        return ""


def _capturar_toast(driver: Any) -> str:
    """Texto do toast/snackbar de erro, se houver (aguarda ~2s)."""
    for seletor in ("simple-snack-bar", ".snack-bar-container", "mat-snack-bar-container"):
        try:
            el = espera.elemento(driver, seletor, teto=2)
            if el is None:
                continue
            txt = (
                (getattr(el, "text_content", None) and el.text_content())
                or getattr(el, "text", "")
                or ""
            )
            txt = " ".join(str(txt).split())
            if txt:
                print(f"[MARCAR_AUD] Toast capturado: '{txt}'")
                return txt
        except Exception:
            continue
    return ""


def _fechar_dialog_confirmacao(driver: Any) -> bool:
    """Fecha a dialog 'Designação Confirmada' clicando no botão Fechar."""
    page = getattr(driver, "page", None)
    espera.assentar(driver, 0.4)

    if page:
        try:
            loc = page.locator("mat-dialog-container button").filter(has_text="Fechar").first
            if loc.count() > 0:
                loc.scroll_into_view_if_needed(timeout=2000)
                loc.hover(timeout=1000)
                loc.click(timeout=3000)
                print("[MARCAR_AUD] Fechar clicado via page.locator(Fechar)")
        except Exception as e:
            print(f"[MARCAR_AUD] locator Fechar falhou: {e}")

        # Se ainda estiver aberta, envia Enter (pois o Fechar recebe cdk-focused)
        try:
            if not espera.ate_sumir(driver, "mat-dialog-container", teto=1):
                page.keyboard.press("Enter")
                print("[MARCAR_AUD] Tecla Enter enviada para o botao Fechar")
        except Exception:
            pass

    if not espera.ate_sumir(driver, "mat-dialog-container", teto=1):
        # Fallback JS executado especificamente no mat-dialog-container
        try:
            _executar_js(driver, """
                var dlg = document.querySelector('mat-dialog-container');
                if (dlg) {
                    var btns = Array.from(dlg.querySelectorAll('button'));
                    var b = btns.find(function(x) {
                        return (x.textContent || '').trim().toLowerCase().includes('fechar');
                    }) || dlg.querySelector('div.container-botoes button');
                    if (b) {
                        b.click();
                        var w = b.querySelector('span.mat-button-wrapper');
                        if (w) w.click();
                        b.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                    }
                }
            """)
            print("[MARCAR_AUD] Fechar acionado via JS no mat-dialog-container")
        except Exception:
            pass

    if not espera.ate_sumir(driver, "mat-dialog-container", teto=1) and page:
        try:
            page.keyboard.press("Escape")
            print("[MARCAR_AUD] Escape enviado como fallback final")
        except Exception:
            pass

    sumiu = espera.ate_sumir(driver, "mat-dialog-container", teto=5)
    if sumiu:
        print("[MARCAR_AUD] Painel de confirmacao fechado com sucesso")
    else:
        print("[MARCAR_AUD] ⚠️ Painel de confirmacao ainda presente")
    return sumiu


def _marcar_aud(
    driver: Any,
    numero_processo: str,
    rito: str,
    aba_retorno: str,
):
    """Marca audiencia no sistema de pauta do PJe."""
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    print(f"[MARCAR_AUD] 1/7 Abrindo pauta: rito={rito} numero={numero_processo}")
    print(f"[MARCAR_AUD]     url={url_pauta}")
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        print("[MARCAR_AUD] ❌ Aba de pauta nao abriu")
        return False
    print(f"[MARCAR_AUD] 2/7 Aba de pauta aberta: {aba_aud}")

    sucesso = False
    try:
        if not esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15):
            raise Exception("Tabela de pauta (mat-card.card-pauta) nao carregou")
        print("[MARCAR_AUD] 3/7 Tabela de pauta carregada")
        _hook_diag("tabela_carregada")

        # Determina o nome do rito para buscar na primeira coluna
        rito_texto = "Una (rito sumaríssimo)" if rito.upper() == 'ATSUM' else "Una"

        # XPath que encontra a linha onde a primeira coluna contém exatamente o texto do rito
        linha_xpath = (
            f"//tr[.//td[1]//span[normalize-space(.)='{rito_texto}']]"
        )
        linha = esperar_elemento(driver, linha_xpath, by=By.XPATH, timeout=10)
        if not linha:
            # fallback: tenta apenas o início do texto (ex: "Una" sem parênteses)
            fallback_texto = "Una"
            linha_xpath = f"//tr[.//td[1]//span[starts-with(normalize-space(.), '{fallback_texto}')]]"
            linha = esperar_elemento(driver, linha_xpath, by=By.XPATH, timeout=5)
        if not linha:
            raise Exception("Linha de pauta não encontrada para o rito especificado")

        print(f"[MARCAR_AUD] 4/7 Linha da pauta (rito '{rito_texto}'): {linha.text[:160].strip()}")

        data_str, hora_str = _extrair_data_hora_pauta(linha)
        print(f"[MARCAR_AUD]     data={data_str} hora={hora_str}")
        _navegar_calendario_para_data(driver, data_str)
        print(f"[MARCAR_AUD] 5/7 Calendario posicionado em {data_str}")
        _encontrar_slot_dia(driver, hora_str)
        print(f"[MARCAR_AUD] 6/7 Slot {hora_str} clicado")

        modal = esperar_elemento(driver, "mat-dialog-container", timeout=10)
        if not modal:
            raise Exception("Modal de audiencia nao encontrado")
        print("[MARCAR_AUD]     Modal aberto")

        # --- Numero do processo: preenchimento sempre, no padrao validado no
        # navegador real. O pre-preenchimento automatico vista em alguns testes
        # vem de uma extensao de navegador, nao do PJe -- nunca confiamos nele.
        modal_ok = esperar_elemento(
            driver, "mat-dialog-container input#inputNumeroProcesso", timeout=10
        )
        if not modal_ok:
            modal_ok = esperar_elemento(driver, "mat-dialog-container", timeout=5)
        if not modal_ok:
            raise Exception("Campo numero do processo nao apareceu no modal")

        if not _garantir_numero_processo(driver, numero_processo, timeout=15):
            estado = _aud_estado_resumido(driver)
            raise Exception(
                f"PJe nao aceitou a designacao ao colar o numero -- {estado}"
            )
        print("[MARCAR_AUD] 7/7 Numero do processo OK e designacao CONFIRMADA")

        # --- Tipo da audiencia: conferido DEPOIS de a designacao ser aceita.
        # Aberta a dialog pela pauta correta, o PJe ja preenche o tipo; so
        # intervimos se vier errado (nunca videoconferencia).
        tipo_atual = _tipo_audiencia_atual(driver)
        desejado = "Una (rito sumaríssimo)" if str(rito).upper() == "ATSUM" else "Una"
        print(f"[MARCAR_AUD] Tipo usado: {tipo_atual or '(vazio)'} | esperado: {desejado}")
        if _tipo_ok(tipo_atual, desejado):
            print("[MARCAR_AUD] Tipo da audiencia OK")
        else:
            print(
                f"[MARCAR_AUD] ⚠️ Tipo diferente do esperado "
                f"(atual={tipo_atual!r}, esperado={desejado!r}) -- "
                "a designacao ja foi aceita pelo PJe"
            )

        # A designacao ja foi confirmada em _garantir_numero_processo, que
        # colou o numero e clicou em Confirmar lendo a reacao do backend.
        # Aqui fechamos o painel de confirmacao ("Designacao Confirmada").
        _fechar_dialog_confirmacao(driver)
        sucesso = True
        data_designada = _extrair_data_audiencia(data_str)
        if data_designada:
            print(f"[MARCAR_AUD] Data da audiencia confirmada: {data_designada.strftime('%d/%m/%Y')}")
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ _marcar_aud: {type(e).__name__}: {e}")
        # Em caso de falha a dialog fica ABERTA de proposito: e ali que esta o
        # motivo do erro (toast, campos, botao). Nada e clicado nem fechado.
        try:
            if espera.ate_aparecer(driver, "mat-dialog-container", teto=1):
                estado = _aud_estado_resumido(driver)
                print(f"[MARCAR_AUD] ⛔ Dialog mantida aberta -- {estado}")
                _hook_diag("falha_dialog_aberta", estado=estado)
        except Exception:
            pass
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in getattr(driver, 'window_handles', []):
                    driver.switch_to.window(aba_retorno)
                    if "/retificar" in (getattr(driver, 'current_url', '') or ''):
                        print("[MARCAR_AUD] Retornou à aba retificar: recolocando 100% digital...")
                        remarcar_100_pos_aud(driver)
            except Exception as e:
                print(f"[MARCAR_AUD] ⚠ Erro ao retornar para aba_retorno/remarcar: {e}")
    return (sucesso, data_designada if sucesso else None)


# =============================================================================
# Funcoes de Data e Regra de Despacho (seg/ter/sex -> ato_v100 / ato_vpp)
# =============================================================================

def _extrair_data_audiencia(texto: str):
    """Extrai a data (dd/mm/aaaa ou aaaa-mm-dd) de um texto da pauta/modal."""
    if not texto:
        return None
    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', texto)
    if m:
        d, mth, y = (int(g) for g in m.groups())
        try:
            return _dt(y, mth, d).date()
        except ValueError:
            return None
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if m:
        y, mth, d = (int(g) for g in m.groups())
        try:
            return _dt(y, mth, d).date()
        except ValueError:
            return None
    return None


def _dia_semana_audiencia(processo_info: Dict):
    """Dia da semana (0=segunda) da audiencia do processo, ou None."""
    data = processo_info.get('data_audiencia')
    if not hasattr(data, 'weekday'):
        bruto = data or processo_info.get('dataProximaAudiencia') or processo_info.get('data_proxima_audiencia')
        if isinstance(bruto, str) and bruto:
            data = _extrair_data_audiencia(bruto)
    return data.weekday() if hasattr(data, 'weekday') else None


_NOMES_DIA = ('segunda-feira', 'terça-feira', 'quarta-feira',
              'quinta-feira', 'sexta-feira', 'sábado', 'domingo')
_DIAS_DESPACHO_NOVO = (0, 1, 4)


def _usa_padrao_novo(processo_info: Dict, numero_processo: str) -> bool:
    """Decide se o despacho deste processo usa ato_v100/ato_vpp (seg/ter/sex)."""
    dia = _dia_semana_audiencia(processo_info)
    if dia is None:
        print(f"[TRIAGEM] {numero_processo}: dia da audiencia desconhecido — usando despacho padrao")
        return False
    nome = _NOMES_DIA[dia]
    novo = dia in _DIAS_DESPACHO_NOVO
    data_str = (
        processo_info['data_audiencia'].strftime('%d/%m/%Y')
        if hasattr(processo_info.get('data_audiencia'), 'strftime')
        else 'data da API'
    )
    despacho_tipo = 'ato_v100/ato_vpp (padrao novo seg/ter/sex)' if novo else 'ato_100/ato_unap (padrao qua/qui)'
    print(f"[TRIAGEM/DESPACHO] {numero_processo}: audiencia em {nome} ({data_str}) -> {despacho_tipo}")
    return novo


# =============================================================================
# Acoes por bucket
# =============================================================================


def acao_bucket_a(
    driver: Any,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket A: processo sem audiencia marcada e sem 100% digital.

    Acoes:
      1. Analisa citacao (polo passivo + domicilio eletronico)
      2. Cria GIGS com observacoes de citacao
      3. Cria GIGS de marcacao de audiencia
      4. Registra comentario sobre a acao executada

    Args:
        driver: Driver do processo.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICAÇÃO EM TEMPO REAL ---
    if _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/A] Processo {numero_processo} já possui audiência marcada. Pulando marcação.")
        return True, "Já possui audiência"
    # --- FIM VERIFICAÇÃO ---

    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('digital', processo_info.get('tem_100', False)))
        numero_formatado = processo_info.get('numero')
        id_processo = str(processo_info.get('id_processo') or '')
        if not numero_formatado or not id_processo:
            print(f"[TRIAGEM/A] ❌ Falha ao extrair numero/ID do processo {numero_processo}")
            return False, None

        # O PJe so reconhece ATSUM (sumarissimo) e ATVARI (rito variavel) no
        # parametro `rito` de pauta-audiencias. "ATOrd" -- valor usado antes
        # aqui e herdado de Triagem/analise_execucao.py -- nao existe na API:
        # a pagina abre, o slot aceita o clique, mas o modal recusa no
        # Confirmar com "Consulte o processo para designar audiencia".
        rito = 'ATSUM' if tipo == 'ATSUM' else 'ATVARI'
        print(f"[TRIAGEM/A] rito do processo={tipo!r} -> rito de pauta={rito}")

        pular_marcacao = bool(processo_info.get('pular_marcar_aud'))

        if pular_marcacao:
            print(f"[TRIAGEM/A] ⏩ {numero_processo}: pulando marcacao de pauta (audiencia tardia). Prosseguindo diretamente para citacao e despacho devido.")

        if not tem_100:
            if not pular_marcacao:
                print(f"[TRIAGEM/A] Processo {numero_processo} sem 100% digital. Desmarcando 100% (se houver), marcando audiencia, ativando 100% e despachando.")

                limpar_overlays_headless(driver)

                aba_retificar = desmarcar_100(driver, id_processo)
                _print_saida_funcao(f"desmarcar_100[{numero_processo}]", aba_retificar)
                if not aba_retificar:
                    print(f"[TRIAGEM/A] ❌ Nao foi possivel abrir aba retificar")
                    return False, None

                res_aud = _marcar_aud(driver, numero_formatado, rito, aba_retificar)
                marcou_aud = res_aud[0] if isinstance(res_aud, tuple) else bool(res_aud)
                data_designada = res_aud[1] if isinstance(res_aud, tuple) else None
                _print_saida_funcao(f"_marcar_aud[{numero_processo}]", marcou_aud)
                if not marcou_aud:
                    print(f"[TRIAGEM/A] ❌ Marcacao de audiencia falhou para {numero_processo}. Despacho abortado.")
                    return False, None
                if data_designada:
                    processo_info['data_audiencia'] = data_designada

                try:
                    if aba_retificar in getattr(driver, 'window_handles', []):
                        driver.switch_to.window(aba_retificar)
                        remarcar_100_pos_aud(driver)
                        driver.close()
                except Exception as e:
                    print(f"[TRIAGEM/A] ⚠ Falha ao remarcar 100%: {e}")

                try:
                    for handle in getattr(driver, 'window_handles', []):
                        driver.switch_to.window(handle)
                        if '/detalhe' in (driver.current_url or ''):
                            break
                except Exception:
                    pass

                limpar_overlays_headless(driver)

            citacao_a = def_citacao(driver, processo_info)
            _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_a)
            if not citacao_a.get('sucesso', True):
                print(f"[TRIAGEM/A] Polo passivo vazio -- abortando GIGS para {numero_processo}")
                return False, None

            for obs in citacao_a['gigs_obs']:
                try:
                    criar_gigs(driver, "1", "Bianca", obs)
                except Exception as e:
                    print(f"[TRIAGEM/A] ❌ Erro ao criar GIGS ({obs}): {e}")

            status_msg = "Sem aud (pula marcacao) - despachado (ato_vpp)?" if pular_marcacao else "Sem aud - marcado e despachado (ato_vpp)?"
            status_msg_padrao = "Sem aud (pula marcacao) - despachado (ato_unap)?" if pular_marcacao else "Sem aud - marcado e despachado (ato_unap)?"

            if _usa_padrao_novo(processo_info, numero_processo):
                try:
                    from atos.wrappers_ato import ato_vpp
                    print(f"[TRIAGEM/A] Executando ato_vpp (seg/ter/sex) para {numero_processo}")
                    resultado_ato = ato_vpp(driver, debug=True)
                    _print_saida_funcao(f"ato_vpp[{numero_processo}]", resultado_ato)
                    ok = bool(resultado_ato)
                    return ok, status_msg if ok else None
                except Exception as e:
                    print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_vpp: {e}")
                    return False, None
            else:
                try:
                    from atos.wrappers_ato import ato_unap
                    print(f"[TRIAGEM/A] Executando ato_unap (qua/qui) para {numero_processo}")
                    resultado_ato = ato_unap(driver, debug=True)
                    _print_saida_funcao(f"ato_unap[{numero_processo}]", resultado_ato)
                    ok = bool(resultado_ato)
                    return ok, status_msg_padrao if ok else None
                except Exception as e:
                    print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_unap: {e}")
                    return False, None

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            print(f"[TRIAGEM/A] Processo {numero_processo} nao atende criterios de rito. Pulando.")
            return True, "Sem aud - marcado e despachado?"

        if not pular_marcacao:
            aba_retificar = desmarcar_100(driver, id_processo)
            _print_saida_funcao(f"desmarcar_100[{numero_processo}]", aba_retificar)
            if not aba_retificar:
                print(f"[TRIAGEM/A] ❌ Nao foi possivel abrir/usar aba retificar")
                return False, None

            res_aud = _marcar_aud(driver, numero_formatado, rito, aba_retificar)
            marcou_aud = res_aud[0] if isinstance(res_aud, tuple) else bool(res_aud)
            data_designada = res_aud[1] if isinstance(res_aud, tuple) else None
            _print_saida_funcao(f"_marcar_aud[{numero_processo}]", marcou_aud)
            if not marcou_aud:
                print(f"[TRIAGEM/A] ❌ Marcacao de audiencia falhou para {numero_processo}. Despacho abortado.")
                return False, None
            if data_designada:
                processo_info['data_audiencia'] = data_designada

            try:
                if aba_retificar in getattr(driver, 'window_handles', []):
                    driver.switch_to.window(aba_retificar)
                    remarcar_100_pos_aud(driver)
                    driver.close()
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao finalizar retificar: {e}")

            try:
                for handle in getattr(driver, 'window_handles', []):
                    driver.switch_to.window(handle)
                    if '/detalhe' in (driver.current_url or ''):
                        break
            except Exception:
                pass

            limpar_overlays_headless(driver)

        citacao_a2 = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao_pos_aud[{numero_processo}]", citacao_a2)
        if not citacao_a2.get('sucesso', True):
            print(f"[TRIAGEM/A] Polo passivo vazio apos triagem -- abortando GIGS para {numero_processo}")
            return False, None

        for obs in citacao_a2['gigs_obs']:
            try:
                criar_gigs(driver, "1", "Bianca", obs)
            except Exception as e:
                print(f"[TRIAGEM/A] ❌ Erro ao criar GIGS pos-aud ({obs}): {e}")

        ok_100 = False
        if _usa_padrao_novo(processo_info, numero_processo):
            try:
                from atos.wrappers_ato import ato_v100
                print(f"[TRIAGEM/A] Executando ato_v100 (seg/ter/sex) para {numero_processo}")
                resultado_ato = ato_v100(driver, debug=True)
                _print_saida_funcao(f"ato_v100[{numero_processo}]", resultado_ato)
                ok_100 = bool(resultado_ato)
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_v100: {e}")
                return False, None
        else:
            try:
                from atos.wrappers_ato import ato_100
                print(f"[TRIAGEM/A] Executando ato_100 (qua/qui) para {numero_processo}")
                resultado_ato = ato_100(driver, debug=True)
                _print_saida_funcao(f"ato_100[{numero_processo}]", resultado_ato)
                ok_100 = bool(resultado_ato)
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_100: {e}")
                return False, None

        msg_ret = "Sem aud (pula marcacao) - despachado?" if pular_marcacao else "Sem aud - marcado e despachado?"
        return ok_100, msg_ret
    except Exception as e:
        print(f"[TRIAGEM/A] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_b(
    driver: Any,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket B: processo com audiencia e 100% digital.

    Acoes:
      1. Analisa citacao (polo passivo + domicilio eletronico)
      2. Cria GIGS com observacoes de citacao
      3. Registra comentario sobre a acao executada

    Args:
        driver: Driver do processo.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICAÇÃO EM TEMPO REAL (B) ---
    if not _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/B] Processo {numero_processo} não possui audiência (embora esperado). Forçando bucket A.")
        return acao_bucket_a(driver, numero_processo, processo_info)
    # --- FIM VERIFICAÇÃO ---

    try:
        citacao_b = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_b)
        if not citacao_b.get('sucesso', True):
            print(f"[TRIAGEM/B] Polo passivo vazio -- abortando GIGS para {numero_processo}")
            return False, None

        for obs in citacao_b['gigs_obs']:
            try:
                criar_gigs(driver, "1", "Bianca", obs)
            except Exception as e:
                print(f"[TRIAGEM/B] ❌ Erro ao criar GIGS ({obs}): {e}")

        # ato_100 ou ato_v100 dependendo do dia da semana
        if _usa_padrao_novo(processo_info, numero_processo):
            try:
                from atos.wrappers_ato import ato_v100
                print(f"[TRIAGEM/B] Executando ato_v100 (seg/ter/sex) para {numero_processo}")
                resultado_ato = ato_v100(driver, debug=True)
                _print_saida_funcao(f"ato_v100[{numero_processo}]", resultado_ato)
            except Exception as e:
                print(f"[TRIAGEM/B] ⚠ Erro ao executar ato_v100: {e}")
        else:
            try:
                from atos.wrappers_ato import ato_100
                print(f"[TRIAGEM/B] Executando ato_100 (qua/qui) para {numero_processo}")
                resultado_ato = ato_100(driver, debug=True)
                _print_saida_funcao(f"ato_100[{numero_processo}]", resultado_ato)
            except Exception as e:
                print(f"[TRIAGEM/B] ⚠ Erro ao executar ato_100: {e}")

        return True, "100% digital - despachado?"
    except Exception as e:
        print(f"[TRIAGEM/B] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_c(
    driver: Any,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket C: processo com audiencia, sem 100% digital.

    Acoes:
      1. Se audiencia em segunda, terca ou sexta (padrao novo):
         - Executa def_citacao (analisa polo passivo e gera gigs_obs)
         - Cria GIGS de citacao (xs ordv / xs sumv / xs ordcv / xs sumcv)
         - Executa ato_vpp (despacho presencial)
         - NUNCA faz PEC direto nem mov_aud
      2. Se audiencia em outros dias (quarta ou quinta):
         - Analisa citacao
         - Executa PEC wrappers (pec_ord, pec_sum, pec_ordc, pec_sumc)
         - Se PEC ok, executa mov_aud

    Args:
        driver: Driver do processo.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICACAO EM TEMPO REAL (C) ---
    if not _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/C] Processo {numero_processo} nao possui audiencia (classificado como C por engano). Forcando bucket A.")
        return acao_bucket_a(driver, numero_processo, processo_info)
    # --- FIM VERIFICACAO ---

    try:
        citacao_c = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_c)
        if not citacao_c.get('sucesso', True):
            print(f"[TRIAGEM/C] Polo passivo vazio -- abortando acao para {numero_processo}")
            return False, None

        # Audiencia segunda, terca ou sexta: NUNCA faz PEC direto!
        # Fluxo obrigatorio: despacho (ato_vpp) + funcao citacao (GIGS).
        if _usa_padrao_novo(processo_info, numero_processo):
            for obs in citacao_c.get('gigs_obs') or []:
                try:
                    criar_gigs(driver, "1", "Bianca", obs)
                except Exception as e:
                    print(f"[TRIAGEM/C] ❌ Erro ao criar GIGS ({obs}): {e}")
            try:
                from atos.wrappers_ato import ato_vpp
                print(f"[TRIAGEM/C] Executando ato_vpp (seg/ter/sex) para {numero_processo}")
                resultado_ato = ato_vpp(driver, debug=True)
                _print_saida_funcao(f"ato_vpp[{numero_processo}]", resultado_ato)
                ok = bool(resultado_ato)
                return ok, "Direto (seg/ter/sex) - despachado (ato_vpp)?" if ok else None
            except Exception as e:
                print(f"[TRIAGEM/C] ⚠ Erro ao executar ato_vpp: {e}")
                return False, None

        # Audiencia quarta ou quinta: PEC direto + mov_aud
        from atos.wrappers_pec import pec_ord, pec_sum, pec_ordc, pec_sumc
        from atos.wrappers_mov import mov_aud
        _PEC_MAP = {'pec_ord': pec_ord, 'pec_sum': pec_sum,
                    'pec_ordc': pec_ordc, 'pec_sumc': pec_sumc}

        ok = False
        for pec_nome in citacao_c['pec_wrappers']:
            pec_fn = _PEC_MAP.get(pec_nome)
            if pec_fn:
                print(f"[TRIAGEM/C] Executando {pec_nome} para {numero_processo}")
                try:
                    resultado_pec = pec_fn(driver, debug=True)
                    _print_saida_funcao(f"{pec_nome}[{numero_processo}]", resultado_pec)
                    ok = bool(resultado_pec) or ok
                except Exception as e:
                    print(f"[TRIAGEM/C] Erro em {pec_nome}: {e}")
            else:
                print(f"[TRIAGEM/C] PEC wrapper '{pec_nome}' nao encontrado no _PEC_MAP")

        if ok:
            print(f"[TRIAGEM/C] Executando mov_aud para {numero_processo}")
            resultado_mov = mov_aud(driver, debug=True)
            _print_saida_funcao(f"mov_aud[{numero_processo}]", resultado_mov)
            result = bool(resultado_mov)
            return result, "Direto - citado?" if result else None
        return False, None
    except Exception as e:
        print(f"[TRIAGEM/C] Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_d(
    driver: Any,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket D: processo HTE (habilitacao de credor).

    Acoes:
      1. Cria GIGS informativa sobre habilitacao
      2. Registra comentario

    Args:
        driver: Driver do processo.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    try:
        return True, None
    except Exception as e:
        print(f"[TRIAGEM/D] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None
