import logging
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ..utils import safe_click

logger = logging.getLogger(__name__)

"""
SISBAJUD Ordens - Selecionar acao por fluxo

Estrutura real do HTML /desdobrar (confirmada em doc.txt):
  Cada instituicao tem painel expansion com div:
    class="com-acoes"              -> banco COM saldo -> recebe acao do fluxo
    class="com-acoes-nao-resposta" -> sem resposta (98) -> Cancelar/Reiterar/blank
  Paineis sem resposta de saldo (codigo 02) ficam COLLAPSED (visibility:hidden).
"""


def _fechar_dropdown(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.3)
    except Exception:
        pass


def _aguardar_opcoes(driver, timeout=4):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
        )
    except Exception:
        return []


def _abrir_select(driver, select_el):
    try:
        parent = driver.execute_script(
            "return arguments[0].parentElement.parentElement;", select_el
        )
        safe_click(driver, parent or select_el, 'click')
    except Exception:
        safe_click(driver, select_el, 'click')
    time.sleep(0.8)


def _classificar_selects(driver):
    """
    JS classifica cada mat-select[name='assessor'] por tipo de pai:
      'com-saldo'    -> pai tem classe 'com-acoes' (nao nao-resposta)
      'nao-resposta' -> pai tem classe 'com-acoes-nao-resposta'
      None           -> painel fechado (ignorado)
    Retorna lista de (elemento_selenium, tipo_str).
    """
    tipos = driver.execute_script("""
        var sels = Array.from(document.querySelectorAll('mat-select[name="assessor"]'));
        return sels.map(function(s) {
            // Verificar se o painel de conteudo esta fechado
            var panel = s.closest('.mat-expansion-panel-content');
            if (panel) {
                var st = window.getComputedStyle(panel);
                if (st.visibility === 'hidden' || panel.style.height === '0px') return null;
            }
            // .com-acoes/.com-acoes-nao-resposta sao IRMAOS de div-row-acao-valor,
            // nao ancestrais — subir ate mat-expansion-panel-body e checar filhos
            var body = s.closest('.mat-expansion-panel-body');
            if (!body) return 'unknown';
            if (body.querySelector('.com-acoes-nao-resposta')) return 'nao-resposta';
            if (body.querySelector('.com-acoes')) return 'com-saldo';
            return 'unknown';
        });
    """)
    all_sels = driver.find_elements(By.CSS_SELECTOR, "mat-select[name='assessor']")
    if not tipos or len(tipos) != len(all_sels):
        # Fallback: todos visíveis como com-saldo
        return [(s, 'com-saldo') for s in all_sels if s.is_displayed()]

    return [(el, t) for el, t in zip(all_sels, tipos) if t is not None]


def _acao_com_saldo(driver, select_el, tipo_fluxo, valor_parcial, log):
    """Seleciona Transferir/Desbloquear em banco com saldo."""
    _abrir_select(driver, select_el)
    opcoes = _aguardar_opcoes(driver)

    if not opcoes:
        if log:
            logger.warning("[_acao] com-saldo: nenhuma opção apareceu")
        _fechar_dropdown(driver)
        return False

    if log:
        logger.info(f"[_acao] com-saldo: {len(opcoes)} opções: {[o.text.strip() for o in opcoes]}")

    desbloquear_el = None
    for op in opcoes:
        t = op.text.strip()
        if 'Desbloquear valor' in t:
            desbloquear_el = op

    # Preferência: exato 'Transferir valor' > contém 'Transferir valor' > 'Desbloquear valor'
    alvo = None
    for op in opcoes:
        t = op.text.strip()
        if tipo_fluxo == 'POSITIVO':
            if t == 'Transferir valor':
                alvo = op
                break
        elif tipo_fluxo == 'DESBLOQUEIO':
            if 'Desbloquear valor' in t:
                alvo = op
                break

    # Fallback: contém o texto sem ser exato
    if not alvo:
        for op in opcoes:
            t = op.text.strip()
            if tipo_fluxo == 'POSITIVO' and 'Transferir valor' in t:
                alvo = op
                break
            elif tipo_fluxo == 'DESBLOQUEIO' and 'Desbloquear' in t:
                alvo = op
                break

    if alvo:
        safe_click(driver, alvo, 'click')
        time.sleep(0.5)
        if log:
            logger.info(f"[_acao] ✅ '{alvo.text.strip()}' selecionado")
        return True

    if log:
        logger.error(f"[_acao] com-saldo: opção para '{tipo_fluxo}' não encontrada")
    _fechar_dropdown(driver)
    return False


def _acao_nao_resposta(driver, select_el, idx, log):
    """
    Para com-acoes-nao-resposta: tenta Cancelar > Reiterar > 1ª opção (blank).
    Igual ao fallback do a.py: document.querySelector('mat-option').click()
    """
    try:
        _abrir_select(driver, select_el)
        opcoes = _aguardar_opcoes(driver)

        if not opcoes:
            if log:
                logger.warning(f"[_acao] nao-resposta #{idx}: sem opções")
            return

        if log:
            logger.info(f"[_acao] nao-resposta #{idx}: {[o.text.strip() for o in opcoes]}")

        for op in opcoes:
            if op.text.strip().lower().startswith('cancelar'):
                safe_click(driver, op, 'click')
                time.sleep(0.4)
                return

        for op in opcoes:
            if op.text.strip().lower().startswith('reiterar'):
                safe_click(driver, op, 'click')
                time.sleep(0.4)
                return

        # Blank (primeira opção — como a.py)
        safe_click(driver, opcoes[0], 'click')
        time.sleep(0.4)
        if log:
            logger.info(f"[_acao] nao-resposta #{idx}: selecionado 1ª opção (blank)")

    except Exception as e:
        if log:
            logger.error(f"[_acao] nao-resposta #{idx}: erro: {e}")
        _fechar_dropdown(driver)


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """
    Seleciona a ação em todos os dropdowns com-saldo via JS puro.
    Não usa referências Python (evita StaleElementReferenceException).
    Cada interação faz query fresh no DOM — idêntico ao que funciona no console.
    """
    time.sleep(0.5)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[name='assessor']"))
        )
    except Exception:
        if log:
            logger.error("[_acao] Nenhum mat-select[name='assessor'] encontrado")
        return False

    # JS: conta selects visíveis em painéis com-saldo (sem nao-resposta)
    JS_SELS = """
        return Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
            var panel = s.closest('.mat-expansion-panel-content');
            if (panel) {
                var st = window.getComputedStyle(panel);
                if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
            }
            var body = s.closest('.mat-expansion-panel-body');
            if (!body) return false;
            return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
        }).length;
    """
    count = driver.execute_script(JS_SELS)

    if not count:
        if log:
            logger.error("[_acao] Nenhum select com-saldo encontrado via JS")
        return False

    if log:
        logger.info(f"[_acao] {count} select(s) com-saldo (JS)")

    texto_alvo = 'Transferir valor' if tipo_fluxo == 'POSITIVO' else 'Desbloquear valor'
    processados = 0

    # JS: clica o i-ésimo select com-saldo (query fresh)
    JS_CLICK_SEL = """
        var sels = Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
            var panel = s.closest('.mat-expansion-panel-content');
            if (panel) {
                var st = window.getComputedStyle(panel);
                if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
            }
            var body = s.closest('.mat-expansion-panel-body');
            if (!body) return false;
            return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
        });
        if (sels[arguments[0]]) { sels[arguments[0]].click(); return true; }
        return false;
    """

    # JS: clica a opção correta no overlay (query fresh)
    JS_CLICK_OPT = """
        var alvo = arguments[0];
        var opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
        var el = opcoes.find(function(o) { return o.textContent.trim() === alvo; });
        if (!el) el = opcoes.find(function(o) { return o.textContent.trim().indexOf(alvo) >= 0; });
        if (el) { el.click(); return el.textContent.trim(); }
        return null;
    """

    for i in range(count):
        clicou = driver.execute_script(JS_CLICK_SEL, i)
        if not clicou:
            if log:
                logger.warning(f"[_acao] Select com-saldo #{i} não encontrado via JS")
            continue

        time.sleep(0.8)  # aguarda overlay do Angular Material abrir

        resultado = driver.execute_script(JS_CLICK_OPT, texto_alvo)

        if resultado:
            processados += 1
            if log:
                logger.info(f"[_acao] ✅ com-saldo #{i}: '{resultado}' selecionado ({processados}/{count})")
        else:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            if log:
                logger.warning(f"[_acao] com-saldo #{i}: opção '{texto_alvo}' não encontrada no overlay")

        time.sleep(0.3)

    return processados > 0