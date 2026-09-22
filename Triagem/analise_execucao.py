"""Triagem/analise_execucao.py
Consolidado dos módulos de análise e execução da Triagem Inicial.

Originado da fusão de: service.py, acoes.py, preprocess.py, citacao.py, utils.py
"""

# ── Imports consolidados ──
import re
import time
import traceback
from Fix.utils import normalizar_texto
from typing import Any, Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.core import esperar_elemento, safe_click, preencher_campo
from Fix.headless_helpers import limpar_overlays_headless
from Fix.extracao import criar_gigs
from Fix.abas import trocar_para_nova_aba
from Fix.log import logger

from api.variaveis import PjeApiClient, session_from_driver
from Fix.variaveis import url_processo_detalhe

# NOTA: imports de .coleta e .regras sao feitos dentro de triagem_peticao()
# para evitar ciclo: __init__ → acoes (shim) → analise_execucao → coleta/regras
#                 → preprocess/utils (shim) → analise_execucao (ainda carregando)

# ── Dependencias opcionais ──
try:
    import pytesseract  # noqa: F401
    _pytesseract_ok = True
except ImportError:
    _pytesseract_ok = False

try:
    import pdf2image  # noqa: F401
    _pdf2image_ok = True
except ImportError:
    _pdf2image_ok = False

__all__ = [
    'triagem_peticao',
    'acao_bucket_a', 'acao_bucket_b', 'acao_bucket_c', 'acao_bucket_d',
    'def_citacao', '_FALHA_CITACAO',
    '_RE_ARTEFATOS_PJE', '_RE_INICIO_JURIDICO',
    '_remover_artefatos_pje', '_aprender_cabecalho', '_remover_cabecalho_por_pagina',
    '_strip_cabecalho_rodape',
    '_formatar_endereco_parte',
]


## ── utils ──


def _formatar_endereco_parte(endereco: dict) -> str:
    if not endereco or not isinstance(endereco, dict):
        return ''
    partes = []
    for chave in ('logradouro', 'numero', 'bairro', 'municipio', 'uf', 'complemento'):
        valor = endereco.get(chave)
        if valor:
            valor = str(valor).strip()
            if valor:
                partes.append(valor)
    return ', '.join(partes)[:120]


## ── preprocess ──


_RE_ARTEFATOS_PJE = re.compile(
    r'(?:^Documento assinado eletronicamente por[^\n]*\n?)'
    r'|(?:^https?://pje\.[^\n]+\n?)'
    r'|(?:^N[uú]mero do documento\s+\d+[^\n]*\n?)'
    r'|(?:^(?:Start|End) of OCR for page \d+[^\n]*\n?)'
    r'|(?:^\s*PJe\s*\n?)'
    r'|(?:^\s*LOGO\s+IMAGE[^\n]*\n?)',
    re.IGNORECASE | re.MULTILINE,
)

_RE_INICIO_JURIDICO = re.compile(
    r'\b(EXCELENT[ÍI]SSIM[OA]|RECLAMAÇÃO\s+TRABALHISTA|'
    r'RECLAMAÇÃO\s+TRABALHISTA|AO\s+EXCELENT|'
    r'INSTRUMENTO\s+PARTICULAR|AÇ[ÃA]O\s+DE\s+CONSIGNAÇ)',
    re.IGNORECASE,
)


def _remover_artefatos_pje(texto: str) -> str:
    """Nivel 1: remove marcadores PJe/OCR deterministicos (risco zero)."""
    return _RE_ARTEFATOS_PJE.sub('', texto)


def _aprender_cabecalho(texto_sem_artefatos: str) -> List[str]:
    m = _RE_INICIO_JURIDICO.search(texto_sem_artefatos)
    if not m:
        return []

    bloco_pre = texto_sem_artefatos[:m.start()]
    linhas = [l.strip() for l in bloco_pre.splitlines() if l.strip()]
    if not linhas:
        return []

    fingerprint = []
    for linha in linhas:
        ln = linha.strip()
        if not ln:
            continue
        if len(ln) >= 90:
            continue
        ln_norm = normalizar_texto(ln or '')
        tem_contato = bool(re.search(
            r'\d{2}[\s\-]?\d{4}[\s\-]?\d{4}'
            r'|@\w|www\.'
            r'|\.com\.br|\.adv\.br',
            ln_norm,
        ))
        eh_nome_escritorio = bool(re.match(
            r'^[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\-\.]{4,}$', ln
        ))
        tem_endereco_escritorio = bool(
            re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a|sala)\b', ln_norm)
            and re.search(r'\d', ln)
            and (
                'cep' in ln_norm
                or re.search(r'\d{5}\s*[-]?\s*\d{3}', ln_norm)
                or re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a)\b.*\d', ln_norm)
                and any(k in ln_norm for k in ('adv', 'escrit', 'oab', 'advogado', 'advogada'))
            )
        )

        if tem_contato or eh_nome_escritorio or tem_endereco_escritorio:
            fingerprint.append(ln)

    return fingerprint


def _remover_cabecalho_por_pagina(texto: str, fingerprint: List[str]) -> str:
    if not fingerprint:
        return texto
    fp_set = {l.strip() for l in fingerprint if l.strip()}
    linhas_out = []
    for linha in texto.splitlines():
        if linha.strip() in fp_set:
            continue
        linhas_out.append(linha)
    return '\n'.join(linhas_out)


def _strip_cabecalho_rodape(texto: str) -> str:
    """
    Ponto de entrada unico: aplica nivel 1 (artefatos PJe) e nivel 2
    (cabecalho do escritorio) ao texto extraido da peticao inicial.
    Seguro: nunca remove conteudo do corpo juridico.
    """
    if not texto:
        return texto
    texto = _remover_artefatos_pje(texto)
    fingerprint = _aprender_cabecalho(texto)
    if fingerprint:
        logger.info(f'[TRIAGEM] cabecalho_fingerprint: {len(fingerprint)} linha(s) identificadas: '
                     f'{fingerprint[:3]}')
        texto = _remover_cabecalho_por_pagina(texto, fingerprint)
    else:
        logger.info('[TRIAGEM] cabecalho_fingerprint: nao identificado (texto inicia direto no conteudo juridico)')
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


## ── citacao ──


_FALHA_CITACAO = {
    'gigs_obs': [],
    'pec_wrappers': [],
    'com_domicilio': 0,
    'sem_domicilio': 0,
    'total': 0,
    'sucesso': False,
}


def def_citacao(driver: WebDriver, processo_info: Dict) -> Dict:
    tipo = (processo_info.get('tipo') or '').upper().strip()
    base = 'sum' if tipo == 'ATSUM' else 'ord'

    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
    except Exception as e:
        logger.error(f"[TRIAGEM/CITACAO] ERRO cliente API: {e}")
        return _FALHA_CITACAO

    m = re.search(r'/processo/(\d+)(?:/|$)', driver.current_url)
    if not m:
        logger.error("[TRIAGEM/CITACAO] ERRO: ID nao encontrado na URL")
        return _FALHA_CITACAO
    id_processo = m.group(1)

    try:
        partes_raw = client.partes(id_processo) or {}
    except Exception as e:
        logger.error(f"[TRIAGEM/CITACAO] ERRO partes: {e}")
        return _FALHA_CITACAO

    passivos = partes_raw.get('PASSIVO') or []
    total = len(passivos)
    if total == 0:
        logger.warning("[TRIAGEM/CITACAO] POLO PASSIVO VAZIO — abortando.")
        return _FALHA_CITACAO

    com_dom = 0
    sem_dom = 0

    for parte in passivos:
        id_parte = str(
            parte.get('idPessoa') or parte.get('id') or
            parte.get('idParticipante') or parte.get('idParte') or ''
        )
        dom_flag = None
        if id_parte:
            dom_flag = client.domicilio_eletronico(id_parte)
        if dom_flag is True:
            com_dom += 1
        else:
            sem_dom += 1

    # Regra unica: se ao menos um passivo tem domicilio eletronico → ord/sum
    # Se nenhum tem → ordc/sumc
    # Atualizado: criar GIGS com IDs do fluxo 1/Bianca e observacoes c.* conforme mapeamento
    if com_dom >= 1:
        if base == 'ord':
            gigs_obs = ['1/Bianca/c.Ord']
        else:
            gigs_obs = ['1/Bianca/c.Sum']
        pec_list = [f'pec_{base}']
    else:
        if base == 'ord':
            gigs_obs = ['1/Bianca/c.Ord.AR']
        else:
            gigs_obs = ['1/Bianca/c.Sum.AR']
        pec_list = [f'pec_{base}c']

    return {
        'gigs_obs': gigs_obs,
        'pec_wrappers': pec_list,
        'com_domicilio': com_dom,
        'sem_domicilio': sem_dom,
        'total': total,
        'sucesso': True,
    }


## ── service ──


def _rotulo_saida(prefixo: str) -> str:
    return {
        'B1_DOCS': 'Documentos essenciais',
        'B3_PARTES': 'Partes',
        'B4_SEGREDO': 'Segredo de justica',
        'B5_RECLAMADAS': 'Reclamadas',
        'B6_TUTELA': 'Tutela provisoria',
        'B7_DIGITAL': 'Juizo 100% digital',
        'B8_PEDIDOS': 'Pedidos liquidados',
        'B9_PESSOA_FIS': 'Pessoa fisica no polo passivo',
        'B10_LITISPEND': 'Litispendencia / prevencao',
        'B11_RESPONSAB': 'Responsabilidade subsidiaria / solidaria',
        'B12_ENDERECO': 'Endereco do reclamante',
        'B12_AUD_VIRTUAL': 'Audiencia virtual / telepresencial',
        'B13_RITO': 'Rito processual',
        'B14_ART611B': 'Art. 611-B CLT',
    }.get(prefixo, prefixo.replace('_', ' ').strip())


def _partes_saida_item(item: str) -> tuple[str, str]:
    if ': ' not in item:
        return '', item
    prefixo, resto = item.split(': ', 1)
    return prefixo, resto


def _conteudo_saida_item(item: str) -> tuple[str, str, str]:
    prefixo, resto = _partes_saida_item(item)
    status = ''
    if resto.startswith('ALERTA - '):
        status = 'ALERTA'
        resto = resto[9:]
    elif resto.startswith('OK - '):
        status = 'OK'
        resto = resto[5:]
    elif resto.startswith('INFO - '):
        status = 'INFO'
        resto = resto[7:]
    return prefixo, status, resto.strip()


def _normalizar_continuacao(texto: str) -> str:
    return texto.replace('\n', '\n  ').strip()


def _formatar_competencia_saida(cep: str) -> str:
    if not cep:
        return 'CEP nao analisado'

    texto = cep.strip().replace('B2_CEP: ', '')

    # OK — CEP dentro da Zona Sul
    m_ok = re.search(
        r'OK - (?P<cep>\d{2}\.\d{3}-\d{3}) \((?P<num>\d+)\) '
        r'no intervalo (?P<lo>\d+)-(?P<hi>\d+) Zona Sul \[(?P<label>.+?)\]',
        texto
    )
    if m_ok:
        return (
            f'CEP: {m_ok.group("cep")} ({m_ok.group("num")}) - '
            f'intervalo {m_ok.group("lo")}-{m_ok.group("hi")} Zona Sul '
            f'[{m_ok.group("label")}]'
        )

    # ALERTA — incompetencia com foro identificado
    m_alerta = re.search(
        r'ALERTA - Incompetencia Territorial - CEP (?P<cep>\d{2}\.\d{3}-\d{3}) '
        r'\((?P<num>\d+)\).*\| foro competente: (?P<foro>.+?)$',
        texto
    )
    if m_alerta:
        return (
            f'CEP: ALERTA - Zona Sul nao detectado - '
            f'CEP {m_alerta.group("cep")} ({m_alerta.group("num")}) '
            f'detectado ({m_alerta.group("foro").strip()})'
        )

    # ALERTA — incompetencia sem foro (legado sem | foro competente:)
    m_alerta_sem_foro = re.search(
        r'ALERTA - Incompetencia Territorial - CEP (?P<cep>\d{2}\.\d{3}-\d{3}) '
        r'\((?P<num>\d+)\)',
        texto
    )
    if m_alerta_sem_foro:
        return (
            f'CEP: ALERTA - Zona Sul nao detectado - '
            f'CEP {m_alerta_sem_foro.group("cep")} ({m_alerta_sem_foro.group("num")}) detectado'
        )

    # Nenhum CEP identificado
    if 'nenhum cep' in texto.lower() or 'nao identificado' in texto.lower():
        return 'CEP: ALERTA - Zona Sul nao detectado - nao detectado CEP dos foruns competentes'

    return f'CEP: {texto}'


def _formatar_saida_item(item: str) -> str:
    prefixo, status, corpo = _conteudo_saida_item(item)

    if not prefixo:
        return _normalizar_continuacao(corpo)

    rotulo = _rotulo_saida(prefixo)
    corpo = _normalizar_continuacao(corpo)

    if prefixo == 'B1_DOCS':
        corpo = re.sub(r'\bprocuracao\b', 'procuração', corpo)
        corpo = re.sub(r'\bdoc identidade\b', 'documento de identidade', corpo)
        corpo = re.sub(r'\b(copia|copias)\b', 'cópia', corpo)
        corpo = corpo.replace('conteudo:"', 'conteudo do anexo "')
        corpo = corpo.replace('titulo', 'titulo do anexo')

    elif prefixo == 'B3_PARTES':
        if corpo.startswith('reclamante='):
            corpo = corpo.replace('reclamante=', 'reclamante: ').replace(' CPF=', ' CPF: ')
        elif 'reclamante nao identificado na capa' in corpo:
            corpo = 'reclamante nao identificado na capa'
        elif 'parte menor de idade' in corpo:
            corpo = corpo.replace(' - incluir MPT custos legis', '; incluir MPT custos legis')

    elif prefixo == 'B5_RECLAMADAS':
        corpo = corpo.replace('[fonte: certidao]', 'fonte: certidao')

    elif prefixo == 'B6_TUTELA':
        corpo = corpo.replace('pedido tutela provisoria', 'pedido de tutela provisoria')
        corpo = corpo.replace('- encaminhar para despacho', '; encaminhar para despacho')

    elif prefixo == 'B7_DIGITAL':
        corpo = corpo.replace('sem pedido expresso de Juizo 100% Digital na peticao',
                              'sem pedido expresso de Juizo 100% Digital na peticao')

    elif prefixo == 'B10_LITISPEND':
        corpo = corpo.replace('litispendencia/prevenção/coisa julgada',
                              'litispendencia / prevencao / coisa julgada')

    elif prefixo == 'B11_RESPONSAB':
        corpo = corpo.replace('responsabilidade subsidiaria/solidaria',
                              'responsabilidade subsidiaria / solidaria')

    elif prefixo == 'B12_AUD_VIRTUAL':
        corpo = corpo.replace('audiencia virtual/telepresencial',
                              'audiencia virtual / telepresencial')

    elif prefixo == 'B14_ART611B':
        corpo = corpo.replace('mencao art. 611-B CLT - colocar lembrete no processo',
                              'mencao ao art. 611-B CLT - colocar lembrete no processo')

    return f'{rotulo}: {corpo}'


def triagem_peticao(driver) -> str:
    from .coleta import _coletar_textos_processo  # lazy import p/ evitar ciclo
    from .regras import (  # lazy import p/ evitar ciclo
        _checar_art611b, _checar_cep, _checar_digital, _checar_endereco_reclamante,
        _checar_litispendencia, _checar_pedidos_liquidados, _checar_pessoa_fisica,
        _checar_procuracao_e_identidade, _checar_reclamadas, _checar_responsabilidade,
        _checar_rito, _checar_segredo, _checar_tutela, _checar_partes,
    )

    if not _pytesseract_ok:
        logger.warning('[TRIAGEM] AVISO: pytesseract nao instalado — OCR indisponivel (documentos de identidade podem retornar vazio)')

    if not _pdf2image_ok:
        logger.warning('[TRIAGEM] AVISO: pdf2image nao instalado — OCR indisponivel')

    if not (_pytesseract_ok and _pdf2image_ok):
        logger.warning('[TRIAGEM] Para extrair texto de documentos digitalizados (RG, CNH), instale: pip install pytesseract pdf2image')

    logger.info('[TRIAGEM] Iniciando _coletar_textos_processo...')
    coleta = _coletar_textos_processo(driver)
    logger.info(f'[TRIAGEM] _coletar_textos_processo retornou: erro={coleta.get("erro")}')
    if coleta.get('erro'):
        return f"ERRO: {coleta['erro']}"

    texto = coleta['texto_inicial']
    if not texto or len(texto) < 100:
        return 'ERRO: texto da peticao inicial extraido vazio ou muito curto'

    anexos = coleta['anexos']
    capa_dados = coleta.get('capa_dados') or {}

    b1 = _checar_procuracao_e_identidade(anexos, capa_dados.get('reclamante_nome') or '')
    cep = _checar_cep(texto, capa_dados)
    partes = _checar_partes(texto, capa_dados)
    seg = _checar_segredo(texto, capa_dados)
    rec = _checar_reclamadas(texto, capa_dados)
    tut = _checar_tutela(texto, capa_dados)
    dig = _checar_digital(texto, capa_dados)
    _ped_full = _checar_pedidos_liquidados(texto)
    ped = _ped_full
    pf = _checar_pessoa_fisica(texto, capa_dados)
    lit = _checar_litispendencia(texto, coleta.get('associados_sistema'))
    resp = _checar_responsabilidade(texto, capa_dados)
    end = _checar_endereco_reclamante(texto, capa_dados)
    pjdp_detectado = any('PJDP no polo passivo' in l for l in (partes if isinstance(partes, list) else [partes]))
    rito = _checar_rito(texto, capa_dados, pjdp_detectado=pjdp_detectado)
    a6 = _checar_art611b(texto)

    def _itens(v):
        return v if isinstance(v, list) else [v]

    alertas, itens_ok = [], []
    for val in [b1, partes, seg, rec, resp, tut, dig, ped, pf, lit, end, rito, a6]:
        for item in _itens(val):
            if not item:
                continue
            prefixo, status, _ = _conteudo_saida_item(item)
            if prefixo == 'B2_CEP':
                continue
            if status == 'ALERTA':
                alertas.append(_formatar_saida_item(item))
            else:
                itens_ok.append(_formatar_saida_item(item))

    if isinstance(cep, str) and 'DOMICILIO_AUTOR' in cep:
        alertas.insert(0, 'Competencia territorial: competencia definida pelo domicilio do reclamante como referencia subsidiaria (art. 651 §3º CLT) - aguardar excecao de incompetencia')

    linhas = [
        '[COMPETENCIA]',
        _formatar_competencia_saida(cep),
        '',
        '[Alertas]',
    ]
    if alertas:
        linhas.extend(f'- {item}' for item in alertas)
    else:
        linhas.append('- nenhum alerta identificado')

    linhas.extend(['', '[ITENS OK]'])
    if itens_ok:
        linhas.extend(f'- {item}' for item in itens_ok)
    else:
        linhas.append('- nenhum item concluido com OK/INFO')

    return '\n'.join(linhas)[:8000]


## ── acoes ──


def _abrir_nova_aba(driver: WebDriver, url: str, aba_origem: str, url_fragmento: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                abas = driver.window_handles
                for h in abas:
                    if h == aba_origem:
                        continue
                    driver.switch_to.window(h)
                    if not url_fragmento:
                        return h
                    try:
                        if url_fragmento in (driver.current_url or ""):
                            return h
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        logger.error("ERRO em _abrir_nova_aba: %s: %s", type(e).__name__, e)
        return None


def desmarcar_100(driver: WebDriver, id_processo: str) -> Optional[str]:
    aba_detalhe = driver.current_window_handle
    url_retificar = url_processo_detalhe(id_processo, "retificar")

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            by=By.CSS_SELECTOR,
            timeout=15
        )
        if not step_carac:
            raise Exception("Step 'Caracteristicas' nao encontrado")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        time.sleep(1)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juizo 100% digital nao encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juizo 100% digital" in (modal.text or ""):
                # Clique no botão "Sim" para confirmar
                btn_sim = modal.find_element(By.XPATH, ".//button[contains(normalize-space(.), 'Sim')]")
                safe_click(driver, btn_sim)
                time.sleep(0.5)
                
                # Clique no botão "Não" para completar
                try:
                    btn_nao = modal.find_element(By.XPATH, ".//button[contains(normalize-space(.), 'Não')]")
                    safe_click(driver, btn_nao)
                except Exception:
                    pass  # Se não houver botão "Não", continua
            
            # Validar que modal foi fechado
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "pje-modal-juizo-digital"))
                )
            except Exception as e:
                raise Exception(f"Modal nao fechou apos confirmar: {e}")
            
            time.sleep(0.5)
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital']:not(.mat-checked)",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
        return nova_aba
    except Exception as e:
        logger.error("ERRO em desmarcar_100: %s: %s", type(e).__name__, e)
        return nova_aba


def remarcar_100_pos_aud(driver: WebDriver):
    try:
        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juizo 100% digital nao encontrado")

        if "mat-checked" not in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juizo 100% digital" in (modal.text or ""):
                # Clique no botão "Sim" para confirmar
                btn_sim = modal.find_element(By.XPATH, ".//button[contains(normalize-space(.), 'Sim')]")
                safe_click(driver, btn_sim)
                time.sleep(0.5)
                
                # Clique no botão "Não" para completar
                try:
                    btn_nao = modal.find_element(By.XPATH, ".//button[contains(normalize-space(.), 'Não')]")
                    safe_click(driver, btn_nao)
                except Exception:
                    pass  # Se não houver botão "Não", continua
            
            # Validar que modal foi fechado após confirmar
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "pje-modal-juizo-digital"))
                )
            except Exception as e:
                raise Exception(f"Modal nao fechou apos confirmar remarcar: {e}")
            
            time.sleep(0.5)
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital'].mat-checked",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
    except Exception as e:
        logger.error("ERRO em remarcar_100_pos_aud: %s: %s", type(e).__name__, e)


def marcar_aud(driver: WebDriver, numero_processo: str, rito: str, aba_retorno: str):
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        return

    sucesso = False
    try:
        esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15)

        if rito.upper() == 'ATSUM':
            linha = esperar_elemento(
                driver,
                "//tr[.//span[contains(normalize-space(.), 'Una (rito sumarissimo)')]]",
                by=By.XPATH,
                timeout=10
            )
        else:
            linha = esperar_elemento(
                driver,
                "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.), 'sumar')]) ]",
                by=By.XPATH,
                timeout=10
            )

        if not linha:
            raise Exception("Linha de pauta nao encontrada")

        btn_plus = linha.find_element(By.XPATH, ".//button[@aria-label='Designar Audiencia'] | .//i[contains(@class,'fa-plus-circle')]/ancestor::button")
        safe_click(driver, btn_plus)

        modal = esperar_elemento(driver, "mat-dialog-container", by=By.CSS_SELECTOR, timeout=10)
        if not modal:
            raise Exception("Modal de audiencia nao encontrado")

        input_num = modal.find_element(By.CSS_SELECTOR, "input#inputNumeroProcesso")
        valor_atual = (input_num.get_attribute('value') or '').strip()
        if not valor_atual:
            try:
                safe_click(driver, input_num)
                input_num.clear()
                input_num.send_keys(numero_processo)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    input_num
                )
            except Exception:
                preencher_campo(driver, "#inputNumeroProcesso", numero_processo)
        time.sleep(0.8)
        btn_confirmar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]",
            by=By.XPATH,
            timeout=10
        )
        if not btn_confirmar:
            raise Exception("Botao Confirmar nao encontrado")
        safe_click(driver, btn_confirmar)
        time.sleep(1)
        modal_confirmado = esperar_elemento(
            driver,
            "//mat-dialog-container//*[self::h4 or self::h3][contains(normalize-space(.), 'Designacao Confirmada')]",
            by=By.XPATH,
            timeout=10
        )
        if not modal_confirmado:
            raise Exception("Confirmacao de designacao de audiencia nao encontrada no dialogo")
        
        btn_fechar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]",
            by=By.XPATH,
            timeout=10
        )
        if not btn_fechar:
            raise Exception("Botao Fechar nao encontrado na confirmacao")
        safe_click(driver, btn_fechar)
        time.sleep(0.5)
        sucesso = True
    except Exception as e:
        logger.error("ERRO em marcar_aud: %s: %s", type(e).__name__, e)
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in driver.window_handles:
                    driver.switch_to.window(aba_retorno)
            except Exception:
                pass


def acao_bucket_a(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('digital', processo_info.get('tem_100', False)))

        numero_formatado = processo_info.get('numero')
        id_processo = str(processo_info.get('id_processo') or '')
        if not numero_formatado or not id_processo:
            logger.error("ERRO em acao_bucket_a: Falha ao extrair numero/ID do processo %s", numero_processo)
            return False

        rito = 'ATSum' if tipo == 'ATSUM' else 'ATOrd'

        if not tem_100:
            logger.debug("[TRIAGEM/A] Processo %s sem 100%% digital. Marcando audiencia.", numero_processo)

            limpar_overlays_headless(driver)

            citacao_a = def_citacao(driver, processo_info)
            if not citacao_a.get('sucesso', True):
                logger.warning("[TRIAGEM/A] Polo passivo vazio — abortando execucao de GIGS para %s", numero_processo)
                return False
            for obs in citacao_a['gigs_obs']:
                try:
                    criar_gigs(driver, "1", "", obs)
                except Exception as e:
                    logger.error("ERRO em acao_bucket_a: Erro ao criar GIGS (%s): %s", obs, e)

            marcar_aud(driver, numero_formatado, rito, driver.current_window_handle)
            limpar_overlays_headless(driver)

            try:
                from atos import ato_unap
                return bool(ato_unap(driver, debug=True))
            except Exception as e:
                logger.error("ERRO em acao_bucket_a: Erro ao executar ato_unap: %s", e)
                return False

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            logger.debug("[TRIAGEM/A] Processo %s nao atende criterios de rito. Pulando.", numero_processo)
            return True

        aba_retificar = desmarcar_100(driver, id_processo)
        if not aba_retificar:
            logger.error("ERRO em acao_bucket_a: Nao foi possivel abrir/usar aba retificar")
            return False

        marcar_aud(driver, numero_formatado, rito, aba_retificar)

        try:
            if aba_retificar in driver.window_handles:
                driver.switch_to.window(aba_retificar)
                remarcar_100_pos_aud(driver)
                driver.close()
        except Exception as e:
            logger.error("ERRO em acao_bucket_a: Erro ao finalizar retificar: %s", e)

        try:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if '/detalhe' in driver.current_url:
                    break
        except Exception:
            pass

        limpar_overlays_headless(driver)
        # 'xs triagem' GIGS removido per request

        citacao_a2 = def_citacao(driver, processo_info)
        if not citacao_a2.get('sucesso', True):
            logger.warning("[TRIAGEM/A] Polo passivo vazio apos triagem — abortando GIGS para %s", numero_processo)
            return False
        for obs in citacao_a2['gigs_obs']:
            try:
                criar_gigs(driver, "1", "", obs)
            except Exception as e:
                logger.error("ERRO em acao_bucket_a: Erro ao criar GIGS (%s): %s", obs, e)

        try:
            from atos import ato_100
            ato_100(driver, debug=True)
        except Exception as e:
            logger.error("ERRO em acao_bucket_a: Erro ao executar ato_100: %s", e)

        return True
    except Exception as e:
        logger.error("ERRO em acao_bucket_a: Erro ao executar acoes: %s", e)
        traceback.print_exc()
        return False


def acao_bucket_b(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        # 'xs triagem' GIGS removido per request

        limpar_overlays_headless(driver)

        citacao_b = def_citacao(driver, processo_info)
        if not citacao_b.get('sucesso', True):
            logger.warning("[TRIAGEM/B] Polo passivo vazio — abortando GIGS para %s", numero_processo)
            return False

        for obs in citacao_b['gigs_obs']:
            logger.debug("[TRIAGEM/B] Criando GIGS para %s (prazo: 1, observacao: %s)", numero_processo, obs)
            criar_gigs(driver, "1", "", obs)

        try:
            from atos import ato_100
            ato_100(driver, debug=True)
        except Exception as e:
            logger.error("ERRO em acao_bucket_b: Erro ao executar ato_100: %s", e)

        return True
    except Exception as e:
        logger.error("ERRO em acao_bucket_b: Erro ao criar GIGS: %s", e)
        traceback.print_exc()
        return False


def acao_bucket_c(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        from atos import mov_aud
        from atos.wrappers_pec import pec_ord, pec_sum, pec_ordc, pec_sumc
        _PEC_MAP = {'pec_ord': pec_ord, 'pec_sum': pec_sum,
                    'pec_ordc': pec_ordc, 'pec_sumc': pec_sumc}

        citacao_c = def_citacao(driver, processo_info)
        if not citacao_c.get('sucesso', True):
            logger.warning("[TRIAGEM/C] Polo passivo vazio — abortando PEC para %s", numero_processo)
            return False

        ok = False
        for pec_nome in citacao_c['pec_wrappers']:
            pec_fn = _PEC_MAP.get(pec_nome)
            if pec_fn:
                logger.debug("[TRIAGEM/C] Executando %s para %s", pec_nome, numero_processo)
                try:
                    ok = bool(pec_fn(driver, debug=True)) or ok
                except Exception as e:
                    logger.error("ERRO em acao_bucket_c: Erro em %s: %s", pec_nome, e)

        if ok:
            logger.debug("[TRIAGEM/C] Executando mov_aud para %s", numero_processo)
            return bool(mov_aud(driver, debug=True))
        return ok
    except Exception as e:
        logger.error("ERRO em acao_bucket_c: Erro na acao: %s", e)
        traceback.print_exc()
        return False


def acao_bucket_d(driver: WebDriver, numero_processo: str, processo_info: Dict) -> bool:
    try:
        # 'xs triagem' GIGS removido per request

        try:
            from atos import ato_ratif
        except ImportError:
            logger.error("ERRO em acao_bucket_d: ato_ratif nao disponivel")
            return False

        try:
            logger.debug("[TRIAGEM/D] Executando ato_ratif para %s", numero_processo)
            return bool(ato_ratif(driver, debug=True))
        except Exception as e:
            logger.error("ERRO em acao_bucket_d: Erro ao executar ato_ratif: %s", e)
            return False
    except Exception as e:
        logger.error("ERRO em acao_bucket_d: Erro geral na acao: %s", e)
        traceback.print_exc()
        return False
