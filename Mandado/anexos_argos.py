"""Mandado - Processamento de Anexos Argos"""

import re
import time
from typing import Optional, Dict, List, Any

from core.resultado_execucao import ResultadoExecucao

from Fix.log import logger
from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.core import safe_click_no_scroll
from Fix import espera


_SIGILO_TYPES = [
    "infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "ir2025", "ir2026",
    "ir 2023", "ir 2024", "ir 2025", "ir 2026", "ir23", "ir24", "ir25", "ir26",
    "ir_2022", "ir_2023", "ir_2024", "ir_2025", "ir_2026",
    "ir_22", "ir_23", "ir_24", "ir_25", "ir_26",
    "dimob", "ecac", "efinanceira", "e-financeira", "decred", "DEC9"
]

_SELETORES_ANEXOS = {
    'btn_anexos': 'button.botao-anexos, pje-timeline-anexos > div > div',
    'anexos': '.tl-item-anexo',
    'btn_sigilo': 'i.fa-wpexplorer',
    'icone_plus': 'i.fas.fa-plus.tl-sigiloso',
    'modal_container': '.cdk-overlay-container .mat-dialog-container',
    'checkbox': 'mat-checkbox',
    'btn_salvar': ".//div[@mat-dialog-actions]//button[contains(., 'Salvar')]",
    'selecionar_todos': 'i.fa.fa-check.botao-icone-titulo-coluna'
}


def _identificar_tipo_anexo(texto: str) -> Optional[str]:
    """Identifica tipo de anexo especial."""
    texto_lower = texto.strip().lower()
    for tipo in _SIGILO_TYPES:
        if tipo == "DEC9":
            if re.search(r"dec\d{9}", texto_lower):
                return tipo
        elif tipo in texto_lower:
            return tipo

    ir_match = re.search(r"\bir[_\s-]*\d+", texto_lower)
    if ir_match:
        return ir_match.group(0)

    return None


def _extrair_executados_pdf(texto_documento: str) -> List[Dict[str, str]]:
    """Extrai lista de executados do texto do documento."""
    if not texto_documento:
        return []

    lines = texto_documento.splitlines()
    executados = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r'^[0-9]+\.', line):
            nome = line.split('.', 1)[1].strip()
            documento = ''
            j = i + 1
            while j < len(lines):
                doc_line = lines[j].strip()
                if doc_line.startswith('CPF') or doc_line.startswith('CNPJ'):
                    documento = doc_line.split(':', 1)[-1].strip()
                    break
                if re.match(r'^[0-9]+\.', doc_line):
                    break
                j += 1
            executados.append({'nome': nome, 'documento': documento})
        i += 1
    return executados


def processar_sisbajud(texto_pdf: str, log: bool = True) -> tuple[str, str, list]:
    """ANÁLISE SISBAJUD: Sempre processa usando o texto extraído (texto_pdf)."""
    import unicodedata

    texto_normalizado = unicodedata.normalize('NFD', texto_pdf)
    texto_normalizado = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')
    texto_normalizado = texto_normalizado.lower()
    texto_colapsado = ' '.join(texto_normalizado.split())

    if 'determinacoes normativas e legais' not in texto_colapsado:
        if log:
            from Fix.log import logger as _logger
            amostra = texto_colapsado[:500] if len(texto_colapsado) > 500 else texto_colapsado
            _logger.info('[SISBAJUD][DEBUG] Marcador nao encontrado. Texto normalizado (primeiros 500 chars):\n%s', amostra)
        raise ValueError('[SISBAJUD][ERRO] Marcador "determinações normativas e legais" não encontrado no texto')

    lines = texto_pdf.splitlines()
    det_idx = -1
    for idx, line in enumerate(lines):
        nl = unicodedata.normalize('NFD', line)
        nl = ''.join(c for c in nl if unicodedata.category(c) != 'Mn').lower()
        if 'determinacoes' in nl or 'normativas e legais' in nl:
            det_idx = idx
            break
    if det_idx == -1:
        for idx in range(len(lines) - 1):
            nl1 = unicodedata.normalize('NFD', lines[idx])
            nl1 = ''.join(c for c in nl1 if unicodedata.category(c) != 'Mn').lower()
            nl2 = unicodedata.normalize('NFD', lines[idx+1])
            nl2 = ''.join(c for c in nl2 if unicodedata.category(c) != 'Mn').lower()
            combinado = (nl1.rstrip() + ' ' + nl2.lstrip())
            if 'determinacoes normativas e legais' in combinado:
                det_idx = idx
                break

    executados = _extrair_executados_pdf(texto_pdf)
    bloqueio_idx = -1
    for offset in range(1, 21):
        if det_idx + offset >= len(lines):
            break
        result_line = lines[det_idx + offset].strip().lower()
        if not result_line:
            continue
        if 'bloqueio de valores' in result_line:
            bloqueio_idx = det_idx + offset
            break
    if bloqueio_idx == -1:
        return 'negativo', 'Bloqueio de valores não encontrado, sem SISBAJUD', executados

    max_linhas = min(len(lines), bloqueio_idx + 25)
    secao_linhas = []
    for idx_l in range(bloqueio_idx, max_linhas):
        l_txt = lines[idx_l].strip().lower()
        if not l_txt:
            continue
        l_norm = ''.join(
            c for c in unicodedata.normalize('NFD', l_txt)
            if unicodedata.category(c) != 'Mn'
        )
        # para não contaminar o veredito do SISBAJUD com "positivo.pdf" de outros convênios.
        if idx_l > bloqueio_idx and any(sec in l_norm for sec in [
            'pesquisa de bens', 'pesquisa patrimonial', 'restricao e indisponibilidade',
            'renajud', 'infojud', 'cnib', 'serasajud', 'arisp', 'sniper',
            'anexos', 'observacoes', 'documento assinado',
            'certifico finalmente', 'conclusao', 'registro de veiculos',
        ]):
            break
        secao_linhas.append(l_txt)

    texto_secao = ' '.join(secao_linhas)
    logger.info('[SISBAJUD][SECAO] det_idx=%s bloqueio_idx=%s linhas=%d texto=%r',
                det_idx, bloqueio_idx, len(secao_linhas), texto_secao[:500])

    valores_encontrados = []
    for match in re.finditer(r'r\$\s*([\d.,]+)', texto_secao):
        valor_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            val_f = float(valor_str)
            valores_encontrados.append(val_f)
        except ValueError:
            pass

    maior_valor = max(valores_encontrados) if valores_encontrados else 0.0
    if maior_valor > 0:
        return 'positivo', f'SISBAJUD com valor positivo: R$ {maior_valor:.2f}', executados

    # 2. Veredito declarado pelo próprio SISBAJUD na seção (ex.: "sisbajud negativo")
    compacto_secao = re.sub(r'\s+', '', texto_secao)
    if 'sisbajudnegativo' in compacto_secao:
        return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores', executados
    if 'sisbajudpositivo' in compacto_secao:
        return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores', executados

    tem_negativo = any('negativo' in l for l in secao_linhas)
    tem_positivo = any('positivo' in l for l in secao_linhas)

    if tem_negativo:
        return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores', executados

    if tem_positivo:
        return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores', executados

    return 'negativo', 'SISBAJUD não encontrado na seção Bloqueio de valores', executados


def tratar_anexos_argos(driver: Any, documentos_sequenciais: List[Any], log: bool = True, escopo_doc: bool = False) -> Optional[Dict]:
    """ETAPA 2 DO FLUXO ARGOS - Processar anexos sigilosos e extrair SISBAJUD"""
    if not documentos_sequenciais:
        if log:
            logger.info('[ARGOS][ANEXOS][ERRO] Nenhum documento sequencial fornecido')
        return None

    from atos.anexos_sigilo import aguardar_visibilidade_concluida
    if not aguardar_visibilidade_concluida(driver, timeout=25.0, estabilidade=0.4, log=log):
        if log:
            logger.warning('[ARGOS][ANEXOS] Dialog/overlay de visibilidade anterior ainda aberto na entrada — prosseguindo com cautela')

    doc = documentos_sequenciais[0]

    seletores_teste = [
        'button.botao-anexos'
    ]

    btn_anexos_encontrado = None
    for sel in seletores_teste:
        try:
            # A ETAPA 1.5 (sigilo) pode deixar a timeline re-renderizando; com
            elementos = espera.elementos(doc, sel, teto=3)
            if elementos:
                btn_anexos_encontrado = elementos[0]
                if log:
                    logger.info(f'[ARGOS][ANEXOS][SELETOR_BOTAO] [OK] Funcionou com: "{sel}"')
                break
        except Exception:
            continue

    anexos_ja_abertos = espera.elementos(doc, _SELETORES_ANEXOS['anexos'], teto=0.2) if escopo_doc else []
    if anexos_ja_abertos:
        anexos = anexos_ja_abertos
        if log:
            logger.info('[ARGOS][ANEXOS] Anexos já expandidos no documento (%d)', len(anexos))
    elif btn_anexos_encontrado:
        try:
            # JavaScript direto conforme legado (evita abertura de aba e ignora overlays)
            safe_click_no_scroll(driver, btn_anexos_encontrado)
            if log:
                logger.info('[ARGOS][ANEXOS]  Anexos abertos (via clique no botão de anexos)')
            if escopo_doc:
                # Aguarda os anexos renderizarem dentro do próprio documento, pois documentos
                # anteriores podem já estar com `.tl-item-anexo` expandido no DOM global.
                anexos = espera.elementos(doc, _SELETORES_ANEXOS['anexos'], teto=5)
            else:
                aguardar_renderizacao_nativa(driver, _SELETORES_ANEXOS['anexos'], modo='aparecer', timeout=5)
                anexos = espera.elementos(driver, _SELETORES_ANEXOS['anexos'], teto=2)
        except Exception as e:
            if log:
                logger.info(f'[ARGOS][ANEXOS][ERRO] Falha ao abrir anexos: {e}')
            return None
    else:
        if log:
            logger.info('[ARGOS][ANEXOS]  Botão de anexos não encontrado com nenhum seletor testado')
        return None

    tem_anexos = len(anexos) > 0

    if not anexos:
        if log:
            logger.info('[ARGOS][ANEXOS]  Nenhum anexo encontrado')
    else:
        if log:
            logger.info(f'[ARGOS][ANEXOS]  {len(anexos)} anexos encontrados')
    found_sigilo = {k: False for k in _SIGILO_TYPES}
    sigilo_anexos = {k: "nao" for k in _SIGILO_TYPES}
    any_sigilo = False
    executados = []
    resultado_sisbajud = None

    # Identifica previamente se há algum anexo especial neste documento — evita ativar
    # e desativar múltipla seleção à toa em certidões sem anexos INFOJUD/IRPF/etc.
    anexos_especiais = []
    for anexo in anexos:
        try:
            texto_anexo = anexo.text.strip()
        except Exception:
            texto_anexo = ''
        tipo = _identificar_tipo_anexo(texto_anexo)
        if tipo:
            anexos_especiais.append((anexo, tipo))

    if not anexos_especiais:
        if log:
            logger.info('[ARGOS][ANEXOS] Nenhum anexo especial encontrado.')
        return ResultadoExecucao(
            sucesso=True,
            status='OK',
            detalhes={
                'found_sigilo': found_sigilo,
                'sigilo_anexos': sigilo_anexos,
                'sigiloso': False,
                'tem_anexos': tem_anexos
            }
        )

    if log:
        logger.info('[ARGOS][ANEXOS] Ativando múltipla seleção...')
    try:
        sel_ocultar = 'button[aria-label="Ocultar múltipla seleção."]'
        seletor_multi = 'button[aria-label="Exibir múltipla seleção."]'
        if espera.elemento(driver, sel_ocultar, teto=0.3):
            if log:
                logger.info('[ARGOS][ANEXOS]  [OK] Múltipla seleção já ativa')
        elif espera.ate_habilitar(driver, seletor_multi, teto=10):
            btn_multi = espera.elemento(driver, seletor_multi, teto=1)
            if btn_multi:
                safe_click_no_scroll(driver, btn_multi)
                espera.elemento(anexos_especiais[0][0], 'mat-checkbox', teto=2)
                if log:
                    logger.info('[ARGOS][ANEXOS]  [OK] Múltipla seleção ativada')
        elif log:
            logger.warning('[ARGOS][ANEXOS]  ⚠️ Falha ao ativar múltipla seleção (não crítico)')
    except Exception:
        if log:
            logger.warning('[ARGOS][ANEXOS]  ⚠️ Falha ao ativar múltipla seleção (não crítico)')

    # === FASE 1: INSERIR SIGILO INDIVIDUALMENTE ===
    if log:
        logger.info('[ARGOS][ANEXOS] === FASE 1: INSERIR SIGILO INDIVIDUALMENTE ===')

    from atos.anexos_sigilo import inserir_sigilo_individual

    anexos_com_sigilo = []

    # Desativa implicit_wait durante o loop para evitar latência em find_element se suportado
    _implicit_saved = None
    try:
        if hasattr(driver, 'timeouts') and hasattr(driver.timeouts, 'implicit_wait'):
            _implicit_saved = driver.timeouts.implicit_wait
            driver.implicitly_wait(0)
    except Exception:
        pass

    # 1. Inserir sigilo individualmente em cada anexo especial
    try:
        for anexo, tipo in anexos_especiais:
            if tipo not in found_sigilo:
                found_sigilo[tipo] = False
            if tipo not in sigilo_anexos:
                sigilo_anexos[tipo] = "nao"

            found_sigilo[tipo] = True

            # Tentar inserir sigilo
            sig_ok = inserir_sigilo_individual(anexo, driver, debug=False)
            if sig_ok:
                anexos_com_sigilo.append((anexo, tipo))
                sigilo_anexos[tipo] = "sim"
                if log:
                    logger.info(f'[ARGOS][ANEXOS]  [OK] Sigilo inserido: {tipo.upper()}')
            else:
                anexos_com_sigilo.append((anexo, tipo))
                sigilo_anexos[tipo] = "sim"
                if log:
                    logger.info(f'[ARGOS][ANEXOS]  [OK] Sigilo mantido/detectado: {tipo.upper()}')

            try:
                inp_cb = espera.elemento(anexo, 'mat-checkbox input[type="checkbox"]', teto=0.4)
                ja_marcado = False
                if inp_cb:
                    ja_marcado = getattr(inp_cb, 'is_selected', lambda: False)() or getattr(inp_cb, 'is_checked', lambda: False)()
                if not ja_marcado:
                    chk = (
                        espera.elemento(anexo, 'span.mat-checkbox-inner-container', teto=0.4)
                        or espera.elemento(anexo, 'mat-checkbox', teto=0.4)
                    )
                    if chk:
                        safe_click_no_scroll(driver, chk)
                        espera.assentar(driver, 0.1)
            except Exception as e:
                if log:
                    logger.warning(f'[ARGOS][ANEXOS] Falha ao marcar checkbox de {tipo.upper()}: {e}')
    finally:
        if _implicit_saved is not None:
            try:
                driver.implicitly_wait(_implicit_saved)
            except Exception:
                pass

    # Falha pode indicar que sigilo já estava presente mas não foi detectado
    tem_especiais = any(found_sigilo.values())
    if anexos_com_sigilo or tem_especiais:
        any_sigilo = True
        if log:
            if anexos_com_sigilo:
                logger.info(f'[ARGOS][ANEXOS] {len(anexos_com_sigilo)} anexo(s) receberam sigilo')
            else:
                logger.info('[ARGOS][ANEXOS] Anexos especiais encontrados (sigilo já presente) — aplicando visibilidade')

        if log:
            logger.info('[ARGOS][ANEXOS] === FASE 2: APLICAR VISIBILIDADE EM LOTE ===')

        try:
            from atos.anexos_sigilo import visibilidade_sigilosos_lote_apenas

            vis_ok = visibilidade_sigilosos_lote_apenas(driver, polo='ativo', log=True)

            if vis_ok:
                if log:
                    logger.info('[ARGOS][ANEXOS]  [OK] Visibilidade em lote aplicada com sucesso')
            else:
                if log:
                    logger.warning('[ARGOS][ANEXOS] [ERRO] Falha ao aplicar visibilidade em lote (não é crítico, continuando)')

        except Exception as e:
            if log:
                logger.error(f'[ARGOS][ANEXOS] Erro ao aplicar visibilidade em lote: {e}')
            try:
                if hasattr(driver, 'page'):
                    driver.page.keyboard.press('Escape')
                elif hasattr(driver, '_page'):
                    driver._page.keyboard.press('Escape')
                elif hasattr(driver, 'keyboard'):
                    driver.keyboard.press('Escape')
            except Exception:
                pass
    else:
        if log:
            logger.info('[ARGOS][ANEXOS] Nenhum anexo especial encontrado.')
        try:
            sel_ocultar = 'button[aria-label="Ocultar múltipla seleção."]'
            btn_ocultar = espera.elemento(driver, sel_ocultar, teto=1.0)
            if btn_ocultar:
                safe_click_no_scroll(driver, btn_ocultar)
                espera.ate_sumir(driver, sel_ocultar, teto=5)
        except Exception:
            pass

    aguardar_visibilidade_concluida(driver, timeout=25.0, estabilidade=0.4, log=log)

    return ResultadoExecucao(
        sucesso=True,
        status='OK',
        detalhes={
            'found_sigilo': found_sigilo,
            'sigilo_anexos': sigilo_anexos,
            'sigiloso': any_sigilo,
            'tem_anexos': tem_anexos
        }
    )
