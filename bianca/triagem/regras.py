# -*- coding: utf-8 -*-
"""
bianca/triagem/regras.py -- Regras de negocio B1 a B14 (apenas regras puras).

Contem as funcoes de checagem de negocio:
  B1  - Procuracao e identidade
  B2  - CEP / Competencia territorial
  B3  - Partes / PJDP
  B4  - Segredo de justica
  B5  - Reclamadas
  B6  - Tutela provisoria
  B7  - Juizo 100% digital
  B8  - Pedidos liquidados
  B9  - Pessoa fisica no polo passivo
  B10 - Litispendencia / prevencao
  B11 - Responsabilidade subsidiaria / solidaria
  B12 - Endereco do reclamante / Audiencia virtual
  B13 - Rito processual
  B14 - Art. 611-B CLT

Os helpers de formatacao e a funcao ``triagem_peticao`` foram movidos
para ``service.py``.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from selenium.webdriver.remote.webdriver import WebDriver

from bianca.triagem.constants import (
    ZONA_SUL_CEPS,
    ZONA_LESTE_CEPS,
    RUI_BARBOSA_CEPS,
    ALCADA,
    RITO_SUMARISSIMO_MAX,
)
from bianca.triagem.utils import _norm

logger = logging.getLogger("bianca.triagem.regras")


# =============================================================================
# Business rules -- checagens de triagem
# =============================================================================

_UF_BRASIL = {
    'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms',
    'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc',
    'sp', 'se', 'to'
}


# ---------------------------------------------------------------------------
# B1 - Procuracao e identidade
# ---------------------------------------------------------------------------


def _checar_procuracao_e_identidade(anexos: List[Dict[str, Any]], nome_reclamante: str = '') -> str:
    proc_via = None
    id_via = None
    termos_proc_tit = ['procuracao', 'mandato']
    termos_id_tit = ['rg', 'cnh', 'documento de identidade', 'identidade',
                     'doc identidade', 'documento pessoal',
                     'documento de identificacao', 'identificacao']
    termos_proc_body = [
        'outorgo', 'poderes', 'por este instrumento particular', 'constituir como',
        'procuracao', 'mandato', 'outorgante', 'outorgado']
    termos_id_body = [
        'registro geral', 'carteira de identidade', 'carteira nacional de habilitacao',
        'secretaria de seguranca publica', 'documento de identidade',
        'data de nascimento', 'filiacao', 'naturalidade']

    for anx in anexos:
        tref = _norm('%s %s' % (anx.get('titulo', ''), anx.get('tipo', '')))
        tbody = _norm(anx.get('texto') or '')
        tnome = (anx.get('titulo') or anx.get('tipo') or '').strip()

        if proc_via is None:
            if any(t in tref for t in termos_proc_tit):
                proc_via = 'titulo'
            elif tbody and any(t in tbody for t in termos_proc_body):
                proc_via = 'conteudo:"%s"' % (tnome or '(sem titulo)')

        if id_via is None:
            if any(t in tref for t in termos_id_tit):
                id_via = 'titulo'
            elif tbody and any(t in tbody for t in termos_id_body):
                id_via = 'conteudo:"%s"' % (tnome or '(sem titulo)')

    extra_proc = ''
    if proc_via and nome_reclamante:
        nome_norm = _norm(nome_reclamante)
        for anx in anexos:
            tref = _norm('%s %s' % (anx.get('titulo', ''), anx.get('tipo', '')))
            tbody = _norm(anx.get('texto') or '')
            if (any(t in tref for t in termos_proc_tit)
                    or (tbody and any(t in tbody for t in termos_proc_body))):
                # Verificar se o texto foi extraido (OCR falho = texto vazio)
                if not tbody or len(tbody) < 100:
                    extra_proc = ' [ATENCAO: texto procuracao nao extraido ou OCR vazio]'
                else:
                    # Tentar buscar nome completo ou partes dele
                    partes_nome = nome_norm.split()
                    nomes_busca = [
                        ' '.join(partes_nome),           # nome completo
                        partes_nome[0] if partes_nome else '',  # primeiro nome
                        partes_nome[-1] if partes_nome else '',  # sobrenome
                    ]
                    
                    # Helper: substitui I<->Y para variacoes ortograficas
                    def _expandir_variacao_i_y(nome: str) -> list:
                        """Retorna nome + variacao com I/Y trocados."""
                        if not nome or len(nome) <= 1:
                            return [nome]
                        variacoes = [nome]
                        if 'i' in nome:
                            variacoes.append(nome.replace('i', 'y'))
                        if 'y' in nome:
                            variacoes.append(nome.replace('y', 'i'))
                        return variacoes
                    
                    # Expandir cada parte com variacoes I/Y
                    nomes_expandidos = []
                    for nome in nomes_busca:
                        if nome:
                            nomes_expandidos.extend(_expandir_variacao_i_y(nome))
                    
                    nome_encontrado = any(
                        nome and len(nome) > 3 and (' ' + nome + ' ' in ' ' + tbody + ' ' or nome in tbody)
                        for nome in nomes_expandidos if nome
                    )
                    if nome_encontrado:
                        extra_proc = ' [nome reclamante localizado na procuracao]'
                    else:
                        extra_proc = ' [ATENCAO: nome reclamante nao localizado na procuracao]'
                break

    tem_proc = proc_via is not None
    tem_id = id_via is not None

    if tem_proc and tem_id:
        return ('B1_DOCS: OK - procuracao (%s)%s '
                'e doc identidade (%s) presentes') % (proc_via, extra_proc, id_via)
    if not tem_proc and not tem_id:
        return 'B1_DOCS: ALERTA - faltam procuracao e copia de documento de identidade em anexos separados'
    if not tem_proc:
        return 'B1_DOCS: ALERTA - falta procuracao em anexo (doc identidade: %s)' % id_via
    return 'B1_DOCS: ALERTA - falta copia de documento de identidade em anexo (procuracao: %s%s)' % (
        proc_via, extra_proc)


# ---------------------------------------------------------------------------
# Helper de contexto (pagina)
# ---------------------------------------------------------------------------


def _pag_contexto(texto: str, posicao: int, janela: int = 400) -> str:
    pag = 1
    for mp in re.finditer(r'Pagina\s+(\d+)', texto[:posicao], re.IGNORECASE):
        pag = int(mp.group(1))
    inicio = max(0, posicao - janela)
    fim = min(len(texto), posicao + janela)
    trecho = texto[inicio:fim].replace('\n', ' ').strip()
    return '[pag.%d] ...%s...' % (pag, trecho)


# ---------------------------------------------------------------------------
# B2 - CEP / Competencia territorial
# ---------------------------------------------------------------------------

_CEP_TERMOS_TERRITORIAL = [
    'competencia territorial', 'competencia funcional', 'foro competente',
    'art. 651', 'art 651', 'artigo 651', 'art.651', 'art651']
_CEP_TERMOS_PRESTACAO = [
    'ultimo local', 'prestacao de servico', 'local de trabalho', 'local de prestacao',
    'prestou servicos', 'prestava servicos', 'laborou', 'trabalhou',
    'desempenhou suas atividades', 'desempenhou suas funcoes', 'exerceu suas funcoes',
    'endereco da prestacao', 'prestacao de servicos', 'local de servicos']
_CEP_TERMOS_RECLAMANTE = ['residente', 'domiciliad', 'endereco do reclamante', 'residencia do reclamante']
_CEP_TERMOS_RECLAMADA = [
    'cnpj', 'com sede', 'filial', 'estabelecimento', 'sede social',
    'endereco da reclamada', 'sede da empresa',
    'reclamad', 'em face', 'contra o reclamado', 'contra a reclamada',
    'cpf', 'pessoa fisica', 'com endereco', 'endereco a']

_CEP_TAG_TERRITORIAL = 1
_CEP_TAG_PRESTACAO = 2
_CEP_TAG_RECLAMADA = 3
_CEP_TAG_GENERICO = 4
_CEP_TAG_RECLAMANTE = 5


def _foro_competente(cep_num: int) -> str:
    for lo, hi in ZONA_LESTE_CEPS:
        if lo <= cep_num <= hi:
            return 'ZONA LESTE'
    for lo, hi in RUI_BARBOSA_CEPS:
        if lo <= cep_num <= hi:
            return 'RUI BARBOSA'
    return 'RUI BARBOSA'


def _cep_tag(ctx_norm: str, palavras_reclamada: List[str]) -> int:
    if any(t in ctx_norm for t in _CEP_TERMOS_TERRITORIAL):
        return _CEP_TAG_TERRITORIAL
    if any(t in ctx_norm for t in _CEP_TERMOS_PRESTACAO):
        return _CEP_TAG_PRESTACAO
    if any(t in ctx_norm for t in _CEP_TERMOS_RECLAMANTE):
        return _CEP_TAG_RECLAMANTE
    if any(t in ctx_norm for t in _CEP_TERMOS_RECLAMADA):
        return _CEP_TAG_RECLAMADA
    if palavras_reclamada and any(p in ctx_norm for p in palavras_reclamada):
        return _CEP_TAG_RECLAMADA
    return _CEP_TAG_GENERICO


def _checar_cep(texto: str, capa_dados: Dict[str, Any]) -> str:
    matches = list(re.finditer(
        r'(?<!\d)(?:CEP[:\s]*)?(\d{2})\.?\s*(\d{3})\s*[-]?\s*(\d{3})(?!\d)',
        texto, re.IGNORECASE))
    if not matches:
        return "B2_CEP: ALERTA - nenhum CEP identificado no documento"

    reclamados_api = capa_dados.get('reclamados') or []
    ceps_api = [r.get('cep') for r in reclamados_api if r.get('cep')]

    if reclamados_api:
        todos_nomes = ' '.join(r.get('nome', '') for r in reclamados_api)
        reclamado_norm = _norm(todos_nomes)
    else:
        reclamado_norm = _norm(capa_dados.get('reclamado_nome') or '')
    stopwords = {'ltda', 'eireli', 'sa', 'me', 'epp', 'do', 'da', 'de', 'e'}
    palavras_reclamada = [p for p in reclamado_norm.split() if len(p) > 3 and p not in stopwords]

    cep_fone = re.compile(r'\b(?:telefone|fone|tel|fax|whats|whatsapp)\b', re.IGNORECASE)
    candidatos = []
    for ordem, m in enumerate(matches):
        num = int(m.group(1) + m.group(2) + m.group(3))
        fmt = "%s.%s-%s" % (m.group(1), m.group(2), m.group(3))
        inicio = max(0, m.start() - 240)
        fim = min(len(texto), m.end() + 240)
        ctx = texto[inicio:fim]
        ctx_norm = _norm(ctx)
        tag = _cep_tag(ctx_norm, palavras_reclamada)
        explicit = (bool(re.search(r'\bCEP\s*[:\-.]?\s*$', texto[max(0, m.start() - 12):m.start()], re.IGNORECASE))
                   or m.group(0)[:3].upper() == 'CEP')
        endereco_context = bool(re.search(
            r'\bendereco\b|\blogradouro\b|\bbairro\b|\bmunicipio\b|\buf\b|\bnumero\b|\bcomplemento\b',
            ctx_norm)) or any(t in ctx_norm for t in _CEP_TERMOS_PRESTACAO + _CEP_TERMOS_RECLAMADA)
        telefone_proximo = bool(cep_fone.search(ctx_norm))
        candidatos.append((
            tag, 0 if explicit else 1, 0 if endereco_context else 1,
            2 if telefone_proximo else 0, ordem, num, fmt))

    # Preserve TERRITORIAL/PRESTACAO tags regardless of telefone_proximo
    # (footer phone lines must not disqualify high-priority contextual CEPs)
    candidatos = [c for c in candidatos if c[3] == 0 or c[1] == 0 or c[0] <= _CEP_TAG_PRESTACAO]
    if not candidatos:
        if ceps_api:
            for cep_raw in ceps_api:
                if not (len(cep_raw) == 8 and cep_raw.isdigit()):
                    continue
                cn = int(cep_raw)
                cf = "%s.%s-%s" % (cep_raw[:2], cep_raw[2:5], cep_raw[5:])
                for lo, hi in ZONA_SUL_CEPS:
                    if lo <= cn <= hi:
                        return ("B2_CEP: OK - %s (%s) Zona Sul "
                                "[sede da reclamada - referencia subsidiaria]") % (cf, cn)
                for lo, hi in ZONA_LESTE_CEPS:
                    if lo <= cn <= hi:
                        return ("B2_CEP: ALERTA - Incompetencia Territorial - "
                                "CEP %s (%s) | foro competente: ZONA LESTE") % (cf, cn)
                for lo, hi in RUI_BARBOSA_CEPS:
                    if lo <= cn <= hi:
                        return ("B2_CEP: ALERTA - Incompetencia Territorial - "
                                "CEP %s (%s) | foro competente: RUI BARBOSA") % (cf, cn)
            return ("B2_CEP: ALERTA - CEPs das reclamadas testados "
                    "mas nenhum pertence a faixa SP - verificar manualmente")
        norm_texto = _norm(texto)
        termos_estritos = _CEP_TERMOS_TERRITORIAL + _CEP_TERMOS_PRESTACAO
        if any(t in norm_texto for t in termos_estritos):
            return ("B2_CEP: ALERTA - nenhum CEP de prestacao de servicos "
                    "identificado no contexto relevante")
        return ("B2_CEP: ALERTA - nenhum CEP de prestacao de servicos "
                "ou reclamada identificado")

    candidatos.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
    tag_label = {
        _CEP_TAG_TERRITORIAL: 'competencia territorial (art.651 CLT)',
        _CEP_TAG_PRESTACAO: 'ultimo local de prestacao de servicos (art.651 CLT)',
        _CEP_TAG_RECLAMADA: ('sede da reclamada - referencia subsidiaria '
                              '(art.651 CLT, ultimo local nao indicado)'),
        _CEP_TAG_RECLAMANTE: 'endereco do reclamante (referencia subsidiaria)',
        _CEP_TAG_GENERICO: 'generico',
    }

    cands_reclamante = [(cep_num, cep_fmt)
                        for tag, _, _, _, _, cep_num, cep_fmt in candidatos
                        if tag == _CEP_TAG_RECLAMANTE]
    cands_ctx_fora_zona_sul = []

    for cand in candidatos:
        best_tag, _, _, _, _, cep_num, cep_fmt = cand
        if best_tag == _CEP_TAG_RECLAMANTE:
            continue
        label = tag_label[best_tag]
        matched = next(((lo, hi) for lo, hi in ZONA_SUL_CEPS if lo <= cep_num <= hi), None)
        if matched:
            lo_match, hi_match = matched
            return ("B2_CEP: OK - %s (%s) no intervalo %s-%s Zona Sul [%s]") % (
                cep_fmt, cep_num, lo_match, hi_match, label)
        _foro = _foro_competente(cep_num)
        cands_ctx_fora_zona_sul.append('%s (%s)' % (cep_fmt, _foro))

    if ceps_api:
        _label_sub = 'sede da reclamada'
        api_fora_zona_sul = []
        for cep_raw in ceps_api:
            if not (len(cep_raw) == 8 and cep_raw.isdigit()):
                continue
            cn = int(cep_raw)
            cf = "%s.%s-%s" % (cep_raw[:2], cep_raw[2:5], cep_raw[5:])
            em_zona_sul = any(lo <= cn <= hi for lo, hi in ZONA_SUL_CEPS)
            if em_zona_sul:
                ctx_suf = ' (apos nao localizar CEP de prestacao)' if cands_ctx_fora_zona_sul else ''
                return ("B2_CEP: OK - %s (%s) Zona Sul [%s%s]") % (cf, cn, _label_sub, ctx_suf)
            _foro = _foro_competente(cn)
            api_fora_zona_sul.append("CEP %s (%s) [%s] | foro: %s" % (cf, cn, _label_sub, _foro))
        if api_fora_zona_sul:
            ctx_str = ', '.join(cands_ctx_fora_zona_sul) if cands_ctx_fora_zona_sul else ''
            prefixo = ("B2_CEP: ALERTA - Incompetencia Territorial - CEPs fora da Zona Sul (%s) + reclamadas: " % ctx_str
                       ) if ctx_str else "B2_CEP: ALERTA - Incompetencia Territorial - reclamadas: "
            return prefixo + '; '.join(api_fora_zona_sul)

    termos_dom_autor = [
        'domicilio do reclamante', 'domicilio do autor', 'foro do domicilio',
        'competencia pelo domicilio', 'empregado viajante', 'trabalhador externo',
        'sem local fixo de trabalho', 'art. 651, § 3', 'art 651, § 3',
        'art.651, § 3', 'art 651 paragrafo 3', 'art. 651 paragrafo terceiro',
    ]
    norm_texto = _norm(texto)
    if cands_reclamante and any(t in norm_texto for t in termos_dom_autor):
        cep_num_r, cep_fmt_r = cands_reclamante[0]
        for lo, hi in ZONA_SUL_CEPS:
            if lo <= cep_num_r <= hi:
                return ("B2_CEP: OK - %s (%s) no intervalo %s-%s Zona Sul "
                        "[endereco do reclamante | DOMICILIO_AUTOR]") % (
                    cep_fmt_r, cep_num_r, lo, hi)
    return "B2_CEP: ALERTA - nenhum CEP de SP (Zona Sul/Leste/Rui Barbosa) identificado no processo"


# ---------------------------------------------------------------------------
# B3 - Partes / PJDP
# ---------------------------------------------------------------------------

_PJDP_NOME_KEYWORDS = [
    'municipio', 'prefeitura', 'estado de', 'estado do', 'governo do estado',
    'governo do municipio', 'uniao federal', 'ministerio', 'autarquia',
    'fazenda publica', 'inss', 'tribunal',
]


def _detectar_pjdp_api(capa_dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Detecta PJDP no polo passivo via dados da API."""
    reclamados = capa_dados.get('reclamados') or []
    for r in reclamados:
        nome_norm = _norm(r.get('nome', ''))
        for kw in _PJDP_NOME_KEYWORDS:
            if kw in nome_norm:
                return True, r.get('nome', nome_norm)
    return False, ''


def _detectar_menor_idade(contexto_partes: str, capa_dados: Dict[str, Any]) -> str:
    """Detecta reclamante menor de 18 anos.

    Fonte primaria: campo reclamante_data_nascimento da API.
    Sem API: busca contextual na secao de qualificacao da peticao.
    Retorna string de alerta B3_PARTES ou '' se nao detectado.
    """

    def _parse_data(s):
        # DD/MM/AAAA ou DD-MM-AAAA ou DD.MM.AAAA
        m = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', s)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
        # ISO: AAAA-MM-DD
        m = re.search(r'(\d{4})[/\-](\d{2})[/\-](\d{2})', s)
        if m:
            return int(m.group(3)), int(m.group(2)), int(m.group(1))
        return None

    def _calcular_idade(dia_n, mes_n, ano_n, data_dist_str):
        ref = _parse_data(data_dist_str)
        if ref:
            ref_dia, ref_mes, ref_ano = ref
        else:
            m_ano = re.search(r'(\d{4})', data_dist_str)
            ref_ano = int(m_ano.group(1)) if m_ano else 2026
            ref_mes, ref_dia = 12, 31
        idade = ref_ano - ano_n
        if (ref_mes, ref_dia) < (mes_n, dia_n):
            idade -= 1
        return idade

    data_dist = capa_dados.get('distribuido_em') or ''

    # 1. Fonte primaria: campo da API (sem fallback para texto se disponivel)
    dn_api = capa_dados.get('reclamante_data_nascimento') or ''
    if dn_api:
        parsed = _parse_data(dn_api)
        if parsed:
            dia, mes, ano = parsed
            if _calcular_idade(dia, mes, ano, data_dist) < 18:
                return (
                    'B3_PARTES: ALERTA - reclamante menor de idade '
                    '(nasc %02d/%02d/%d) - intimar MPT custos legis' % (dia, mes, ano)
                )
        return ''

    # 2. Busca contextual: primeiros ~1500 chars da qualificacao
    area = contexto_partes[:1500]

    # 2a. Mencao literal na secao do reclamante
    if re.search(r'\bmenor\s+de\s+idade\b', area):
        return (
            'B3_PARTES: ALERTA - reclamante menor de idade '
            '(mencao no texto) - intimar MPT custos legis'
        )

    # 2b. Data em contexto de nascimento
    _re_nasc = re.compile(
        r'(?:nascid[ao]|data\s+de\s+nascimento|nascimento|dt\.?\s*nasc\.?)'
        r'[:\s,]+(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
        re.IGNORECASE,
    )
    for m in _re_nasc.finditer(area):
        try:
            dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if _calcular_idade(dia, mes, ano, data_dist) < 18:
                return (
                    'B3_PARTES: ALERTA - reclamante menor de idade '
                    '(nasc %02d/%02d/%d) - intimar MPT custos legis' % (dia, mes, ano)
                )
        except Exception:
            continue

    return ''


def _checar_partes(texto: str, capa_dados: Dict[str, Any]) -> List[str]:
    linhas = []
    norm = _norm(texto)
    corte = norm.find('preliminarmente')
    contexto_partes = norm[:corte] if corte != -1 else norm[:2600]

    nome_rec = capa_dados.get('reclamante_nome') or ''
    cpf_rec = capa_dados.get('reclamante_cpf') or ''
    if nome_rec:
        sufixo = ' CPF=%s' % cpf_rec if cpf_rec else ''
        rec_info = ' - reclamante=%s%s' % (nome_rec[:60], sufixo)
    else:
        m = re.search(
            r'RECLAMANTE[:\s]+([A-ZA-AE-EI-IO-O-U-UC-N][A-ZA-AE-EI-IO-O-U-UC-Na-z\s\.]+?)'
            r'(?:\s*[-]\s*|\s*CPF|\n)', texto[:3000])
        if m:
            rec_info = ' - reclamante=%s' % m.group(1).strip()[:60]
        else:
            rec_info = ''
            linhas.append("B3_PARTES: ALERTA - reclamante nao identificado na capa")

    alerta_menor = _detectar_menor_idade(contexto_partes, capa_dados)
    if alerta_menor:
        linhas.append(alerta_menor)

    pjdp_detectado, pjdp_nome = _detectar_pjdp_api(capa_dados)
    if not pjdp_detectado and not capa_dados.get('reclamados'):
        re_pjdp = re.compile(
            r'\b(municipio|prefeitura|uniao\s+federal|autarquia|fazenda\s+p[ue]blica|estado\b(?!\s+de\b))\b')
        re_addr = re.compile(r'municipio\s*:', re.IGNORECASE)
        re_privado = re.compile(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado')
        for m_pjdp in re_pjdp.finditer(contexto_partes):
            trecho = contexto_partes[max(0, m_pjdp.start() - 80): m_pjdp.end() + 20]
            if re_addr.search(trecho):
                continue
            trecho_amplo = contexto_partes[max(0, m_pjdp.start() - 200): m_pjdp.end() + 50]
            if re_privado.search(trecho_amplo):
                continue
            pjdp_detectado = True
            pjdp_nome = m_pjdp.group(1)
            break

    if pjdp_detectado:
        rito_dec = capa_dados.get('rito_declarado')
        if not rito_dec:
            m_rito = re.search(r'RITO[:\s]+(SUMAR[IÍ]SSIMO|ORDIN[ÁA]RIO)', texto[:3000], re.IGNORECASE)
            if m_rito:
                rito_dec = 'SUMARISSIMO' if re.search(r'sumar', _norm(m_rito.group(1))) else 'ORDINARIO'
        if rito_dec != 'ORDINARIO':
            linhas.append(
                "B3_PARTES: ALERTA - PJDP no polo passivo (rito ordinario obrigatorio); "
                "detectado via nome: %s; rito atual: %s" % (pjdp_nome, rito_dec or 'nao identificado'))
        else:
            linhas.append(
                "B3_PARTES: INFO - PJDP no polo passivo - rito ORDINARIO compativel; "
                "detectado via nome: %s" % pjdp_nome)

    if not any('ALERTA' in l for l in linhas):
        linhas.append("B3_PARTES: OK%s" % rec_info)
    return linhas


# ---------------------------------------------------------------------------
# B4 - Segredo de justica
# ---------------------------------------------------------------------------


def _checar_segredo(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)
    tem_pedido = bool(re.search(r'segredo\s+de\s+justi[cç]a|tramita[cç][aã]o\s+sigilosa', norm))
    segredo_na_capa = capa_dados.get('segredo_justica')
    if segredo_na_capa is True and not tem_pedido:
        return ("B4_SEGREDO: ALERTA - certidao indica segredo "
                "mas nao ha requerimento fundamentado na peticao")
    if tem_pedido:
        fund = bool(re.search(r'art\.?\s*189', norm))
        suf = 'com art. 189 CPC' if fund else 'sem fundamentacao (art. 189 CPC ausente)'
        return "B4_SEGREDO: ALERTA - pedido de segredo de justica %s" % suf
    return "B4_SEGREDO: OK"


# ---------------------------------------------------------------------------
# B5 - Reclamadas
# ---------------------------------------------------------------------------


def _checar_reclamadas(texto: str, capa_dados: Dict[str, Any]) -> List[str]:
    linhas = []
    reclamados_api = capa_dados.get('reclamados') or []

    sem_endereco = capa_dados.get('reclamadas_sem_endereco') or []
    if sem_endereco:
        linhas.append('B5_RECLAMADAS: ALERTA - %s reclamada(s) SEM ENDERECO CADASTRADO' % len(sem_endereco))

    com_dom = capa_dados.get('reclamadas_com_dom_elet', 0) or 0
    total_reclamadas = len(reclamados_api)
    if total_reclamadas > 0:
        if com_dom > 0:
            linhas.append('B5_RECLAMADAS OK - %s/%s reclamada(s) com DOMICILIO ELETRONICO' % (
                com_dom, total_reclamadas))
        else:
            linhas.append('B5_RECLAMADAS ALERTA - NENHUMA reclamada com domicilio eletronico habilitado')

    if not reclamados_api:
        linhas.append("B5_RECLAMADAS: ALERTA - dados de partes nao disponiveis via API")
        return linhas

    n_com_end = sum(1 for r in reclamados_api if r.get('cep') or r.get('endereco'))
    ceps_rec = [r['cep'] for r in reclamados_api if r.get('cep')]
    ceps_str = ', '.join(ceps_rec) if ceps_rec else 'nenhum'
    sem_doc = [r for r in reclamados_api if len(r.get('cpfcnpj', '')) not in (11, 14)]
    if sem_doc:
        linhas.append("B5_RECLAMADAS: ALERTA - %s reclamada(s) sem CPF/CNPJ valido na API" % len(sem_doc))
    linhas.append("B5_RECLAMADAS: OK - %s reclamada(s); %s com endereco detectado; CEPs analisados: %s" % (
        len(reclamados_api), n_com_end, ceps_str))
    return linhas


# ---------------------------------------------------------------------------
# B6 - Tutela provisoria
# ---------------------------------------------------------------------------


def _checar_tutela(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)
    idx = max(norm.rfind('pedidos'), norm.rfind('dos pedidos'),
              norm.rfind('requerimentos'), len(norm) - 4000)
    sec_norm = norm[max(0, idx):]
    termos = [
        'tutela de urgencia', 'tutela urgencia', 'tutela antecipada',
        'tutela provisoria', 'tutela de evidencia', 'tutela cautelar',
        'medida liminar', 'pedido liminar', 'medida cautelar',
        'medida de urgencia', 'tutela liminar',
        'art. 300', 'art. 305', 'art. 311',
    ]
    for t in termos:
        pos = sec_norm.find(t)
        if pos != -1:
            ctx = _pag_contexto(texto, max(0, idx) + pos, janela=300)
            return ("B6_TUTELA: ALERTA - pedido tutela provisoria (%s) "
                    "- encaminhar para despacho\n  %s") % (t, ctx)
    # Busca adicional no cabecalho/titulo (primeiros 3000 chars):
    # titulos como "PEDIDO LIMINAR TUTELA URGENCIA" indicam pedido mesmo sem
    # os termos aparecerem na secao de pedidos.
    cabecalho = norm[:3000]
    for t in termos:
        pos = cabecalho.find(t)
        if pos != -1:
            ctx = _pag_contexto(texto, pos, janela=300)
            return ("B6_TUTELA: ALERTA - pedido tutela provisoria identificado "
                    "no cabecalho/titulo (%s) - encaminhar para despacho\n  %s") % (t, ctx)
    if capa_dados.get('medida_urgencia') is True:
        return "B6_TUTELA: ALERTA - certidao indica medida de urgencia mas termo nao localizado nos pedidos"
    return "B6_TUTELA: OK"


# ---------------------------------------------------------------------------
# B7 - Juizo 100% digital
# ---------------------------------------------------------------------------


def _checar_digital(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)

    # Detecta discordância/rejeição expressa ao Juízo 100% Digital.
    # Nesse caso a parte NÃO quer o juízo digital → nenhum alerta necessário.
    discordancia_digital = bool(re.search(
        r'(discordan[cç][ai]|discorda|n[aã]o\s+concorda|n[aã]o\s+adere|'
        r'se\s+op[oõ]e|oposi[cç][aã]o|manifest[ao]\s+.*discordan[cç][ai]|'
        r'discordan[cç][ai]\s+.*ju[ií]zo|n[aã]o\s+.*ju[ií]zo\s*100%?\s*digital)'
        r'.*ju[ií]zo\s*100%?\s*digital|'
        r'ju[ií]zo\s*100%?\s*digital.*'
        r'(discordan[cç][ai]|discorda|n[aã]o\s+concorda|n[aã]o\s+adere|se\s+op[oõ]e)',
        norm))
    if discordancia_digital:
        return "B7_DIGITAL: OK - parte manifesta discordancia com Juizo 100% Digital (nao quer)"

    pedido_digital = bool(re.search(
        r'(ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'manifesta[cç][aã]o\s+de\s+ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'requer(?:e|ido)?\s+o\s+ju[ií]zo\s*100%?\s*digital|'
        r'opta\s+pelo\s+ju[ií]zo\s*100%?\s*digital|'
        r'adere\s+ao\s+ju[ií]zo\s*100%?\s*digital)', norm))
    if not pedido_digital:
        return "B7_DIGITAL: OK - sem pedido expresso de Juizo 100% Digital na peticao"

    processo_digital = capa_dados.get('juizo_digital')
    if processo_digital is True:
        return "B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado e processo ja marcado na API"
    if processo_digital is False:
        return ("B7_DIGITAL: ALERTA - pedido expresso de Juizo 100% Digital "
                "identificado, mas processo nao marcado na API")
    return ("B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital "
            "identificado, mas marcacao nao confirmada na API")


# ---------------------------------------------------------------------------
# B8 - Pedidos liquidados
# ---------------------------------------------------------------------------


def _checar_pedidos_liquidados(texto: str) -> str:
    re_skip = re.compile(
        r'atribu[ií]|n[aã]o inferior|valor da causa|valor atribu[ií]do|'
        r'n[aã]o deve ser utiliz|fator limitador|estimativa|base de calculo', re.IGNORECASE)
    re_verba = re.compile(
        r'\b(saldo.sal[aá]rio|aviso\s*pr[eé]vio|f[eé]rias|fgts|'
        r'multa\s*(art|do)?\s*(art\.?\s*4[67][67]|dos\s*40)?|dano\s*moral|gorjeta|'
        r'adicional|13[°o]\s*sal[aá]rio|d[eé]cimo|hora\s*extra|'
        r'indeniza[cç][aã]o|seguro[- ]desemprego|libera[cç][aã]o)\b', re.IGNORECASE)

    secao = ''
    itens = []
    seen = set()

    for linha in texto.split('\n'):
        ls = linha.strip()
        if not ls:
            continue
        ln = _norm(ls)
        if len(ls) < 70 and 'r$' not in ln and re_verba.search(ln):
            secao = ls
            continue
        if re_skip.search(ln):
            continue
        for mv in re.finditer(r'R\$\s*([\d\.]+,\d{2})', ls):
            try:
                num = float(mv.group(1).replace('.', '').replace(',', '.'))
            except ValueError:
                continue
            if num <= 50:
                continue
            chave = (secao, mv.group(1))
            if chave in seen:
                continue
            seen.add(chave)
            secao_label = secao if secao else 'pedido'
            itens.append("  [%s - R$ %s]" % (secao_label, mv.group(1)))

    if not itens:
        amostra = []
        for linha in texto.split('\n'):
            if re.search(r'R\$\s*[\d\.\,]+', linha):
                amostra.append(linha.strip())
                if len(amostra) == 3:
                    break
        if amostra:
            out = ["B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados"]
            out.append("B8_PEDIDOS: amostra de linhas com valores encontrados:")
            out.extend("  %s" % linha for linha in amostra)
            return '\n'.join(out)
        return "B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados"
    out = ["B8_PEDIDOS: OK - %s pedido(s) com valor:" % len(itens)]
    out.extend(itens[:2])
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# B9 - Pessoa fisica no polo passivo
# ---------------------------------------------------------------------------


def _checar_pessoa_fisica(texto: str, capa_dados: Dict[str, Any] = None) -> str:
    reclamados_api = (capa_dados or {}).get('reclamados') or []
    if not reclamados_api:
        return "B9_PESSOA_FIS: ALERTA - dados de partes nao disponiveis via API"

    pessoas_fisicas = [r for r in reclamados_api if len(r.get('cpfcnpj', '')) == 11]
    if not pessoas_fisicas:
        return "B9_PESSOA_FIS: OK - sem pessoa fisica no polo passivo"

    nomes = ', '.join(r['nome'] for r in pessoas_fisicas)
    fund_termos = ['responsabilidade pessoal', 'desconsideracao', 'socio',
                   'administrador', 'sucessao', 'grupo economico']
    if any(t in _norm(texto) for t in fund_termos):
        return "B9_PESSOA_FIS: OK - pessoa fisica com fundamentacao juridica (%s)" % nomes
    return "B9_PESSOA_FIS: ALERTA - pessoa fisica no polo passivo sem fundamentacao clara (%s)" % nomes


# ---------------------------------------------------------------------------
# B10 - Litispendencia
# ---------------------------------------------------------------------------


def _checar_litispendencia(texto: str, associados_sistema: List[Dict[str, Any]] = None) -> str:
    termos_juris = [
        "acordao", "ementa", "jurisprudencia", "precedente", "relator", "turma",
        "tst", "stj", "stf", "dejt", "sumula", "oj", "rot", "rorsum", "rr", "airr"]
    padrao_processo = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos_reais = []
    for linha in texto.split('\n'):
        if any(t in _norm(linha) for t in termos_juris):
            continue
        matches = padrao_processo.findall(linha)
        if matches:
            processos_reais.extend(matches)
    unicos_peticao = list(dict.fromkeys(processos_reais))

    nums_sistema: List[str] = []
    for assoc in (associados_sistema or []):
        if not isinstance(assoc, dict):
            continue
        num = str(assoc.get('numero') or assoc.get('numeroCnj')
                  or assoc.get('numeroProcesso') or assoc.get('num') or '').strip()
        if re.match(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', num):
            nums_sistema.append(num)

    partes_alerta: List[str] = []
    for num in nums_sistema:
        if num in unicos_peticao:
            partes_alerta.append("Prevencao detectada no sistema - processo %s (tambem mencionado na peticao)" % num)
        else:
            partes_alerta.append("Prevencao detectada no sistema - processo %s" % num)

    apenas_peticao = [n for n in unicos_peticao if n not in nums_sistema]
    if nums_sistema:
        if apenas_peticao:
            outros = ', '.join(apenas_peticao[:4])
            partes_alerta.append(
                "mencao a outros processos na peticao (%s) - verificar litispendencia" % outros)
    elif len(unicos_peticao) > 1:
        outros = ', '.join(unicos_peticao[1:4])
        partes_alerta.append(
            "mencao a outros processos na peticao (%s) - verificar litispendencia" % outros)

    if not partes_alerta:
        norm = _norm(texto)
        for t in ['acao anterior', 'processo anterior', 'ja ajuizou', 'litispendencia',
                  'coisa julgada', 'acordo nao homologado']:
            pos = norm.find(t)
            if pos != -1:
                ctx = _pag_contexto(texto, pos, janela=200)
                partes_alerta.append("possivel '%s'\n  %s" % (t, ctx))
                break

    if partes_alerta:
        return "B10_LITISPEND: ALERTA - %s" % '\n'.join(partes_alerta)
    return "B10_LITISPEND: OK"


# ---------------------------------------------------------------------------
# B11 - Responsabilidade subsidiaria / solidaria
# ---------------------------------------------------------------------------

_RE_RECLAMADA_HEADER = re.compile(
    r'(?:\d+[o]\.?\s*|primeira\s+|segunda\s+|terceira\s+|quarta\s+)RECLAMAD[AO]\b'
    r'|RECLAMAD[AO]\s*[:\-]',
    re.IGNORECASE
)


def _checar_responsabilidade(texto: str, capa_dados: Dict[str, Any] = None) -> List[str]:
    reclamados_api = (capa_dados or {}).get('reclamados') or []
    if reclamados_api:
        n_rec = len(reclamados_api)
    else:
        capa = texto[:4000]
        n_rec = len(_RE_RECLAMADA_HEADER.findall(capa))

    norm = _norm(texto)
    if re.search(r'responsabilidade\s+subsidiaria|subsidiariamente\s+responsaveis?', norm):
        tipo_resp = 'subsidiaria'
    elif re.search(r'responsabilidade\s+solidaria|solidariamente\s+(?:responsaveis?|condena)', norm):
        tipo_resp = 'solidaria'
    else:
        tipo_resp = 'subsidiaria/solidaria'

    if n_rec <= 1:
        if tipo_resp != 'subsidiaria/solidaria' or re.search(
            r'responsabilidade\s+(subsidiaria|solidaria)'
            r'|solidariamente\s+(?:responsaveis?|condena)'
            r'|subsidiariamente\s+responsaveis?', norm
        ):
            return ["B11_RESPONSAB: ALERTA - 1 reclamada mas pedido de responsabilidade %s" % tipo_resp]
        return ["B11_RESPONSAB: OK - unica reclamada, nao aplicavel"]

    tem_pedido = bool(re.search(
        r'responsabilidade\s+(subsidiaria|solidaria)'
        r'|responsabilizacao\s+subsidiaria'
        r'|solidariamente\s+(?:responsaveis?|condena)'
        r'|subsidiariamente\s+responsaveis?'
        r'|condena[cç][aã]o\s+solidar'
        r'|devedoras?\s+solidar'
        r'|devedoras?\s+subsidiar'
        r'|respondam?\s+solidariamente'
        r'|respondam?\s+subsidiariamente', norm
    ))

    if not tem_pedido:
        for _m in re.finditer(
            r'(?:primeira|segunda|terceira|demais|todas?\s+as?)\s+reclamad[ao]', norm
        ):
            janela = norm[max(0, _m.start() - 400): _m.end() + 400]
            if re.search(
                r'responsabilid|devedora|solidar|subsidiar'
                r'|prestadora\s+de\s+servico|tomadora', janela
            ):
                tem_pedido = True
                break

    tem_causa = bool(re.search(
        r'tomador\s+de\s+servico|terceirizacao|prestacao\s+de\s+servico'
        r'|grupo\s+economico|subempreitada|terceirizad[ao]|terceirizado'
        r'|prestadora\s+(?:de\s+)?servicos?'
        r'|s[o]ci[ao][- ]proprietari|s[o]ci[ao][- ]gerente'
        r'|dono\s+da\s+empresa|proprietari[ao]\s+d[ao]'
        r'|empres[ao]\s+d[ao]\s+grupo'
        r'|administrador[ao]|s[o]ci[ao]\b'
        r'|culpa\s+in\s+eligendo|culpa\s+in\s+vigilando', norm
    ))

    if not tem_pedido:
        return ["B11_RESPONSAB: ALERTA - %s reclamadas sem pedido de responsabilidade subsidiaria/solidaria" % n_rec]
    if not tem_causa:
        return ["B11_RESPONSAB: ALERTA - pedido de responsabilidade %s sem causa de pedir explicita (%s reclamadas)" % (
            tipo_resp, n_rec)]
    return ["B11_RESPONSAB: OK - %s reclamadas com pedido de responsabilidade %s e causa de pedir" % (
        n_rec, tipo_resp)]


# ---------------------------------------------------------------------------
# B12 - Endereco do reclamante / Audiencia virtual
# ---------------------------------------------------------------------------


def _checar_endereco_reclamante(texto: str, capa_dados: Dict[str, Any] = None) -> List[str]:
    linhas = []
    norm = _norm(texto)
    cd = capa_dados or {}

    mun_api = cd.get('reclamante_municipio') or ''
    uf_api = cd.get('reclamante_uf') or ''
    fonte = cd.get('reclamante_end_fonte') or ('api' if mun_api else 'texto')

    ctx_texto = None
    if mun_api:
        cidade = mun_api
        estado = uf_api
        fonte_label = 'api'
    else:
        nome_rec = cd.get('reclamante_nome') or ''
        if nome_rec:
            nome_norm = _norm(nome_rec)[:20]
            idx_nome = norm.find(nome_norm)
            busca_ini = max(0, idx_nome) if idx_nome >= 0 else 0
        else:
            busca_ini = 0
        trecho = norm[busca_ini: busca_ini + 1200]
        m = re.search(
            r'(?:residente|domiciliad[ao])[\s\S]{0,200}?'
            r'([a-z][a-z ]{2,35}?)[ /\-]+([a-z]{2})\b', trecho)
        cidade = None
        estado = None
        if m:
            c = m.group(1).strip()
            e = m.group(2)
            if e in _UF_BRASIL:
                cidade = c
                estado = e
                inicio = max(0, m.start() - 60)
                fim = min(len(trecho), m.end() + 60)
                ctx_texto = trecho[inicio:fim].replace('\n', ' ').strip()
        fonte_label = 'texto (%s)' % fonte if fonte != 'texto' else 'texto'

    if cidade:
        grande_sp = {
            'sao paulo', 'aruja', 'barueri', 'biritiba-mirim', 'caieiras',
            'cajamar', 'carapicuiba', 'cotia', 'diadema', 'embu das artes',
            'embu-guacu', 'ferraz de vasconcelos', 'francisco morato',
            'franco da rocha', 'guararema', 'guarulhos', 'itapevi',
            'itaquaquecetuba', 'itapecerica da serra', 'jandira', 'juquitiba',
            'mairipora', 'maua', 'mogi das cruzes', 'osasco',
            'pirapora do bom jesus', 'poa', 'ribeirao pires',
            'rio grande da serra', 'salesopolis', 'santa isabel',
            'santana de parnaiba', 'santo andre', 'sao bernardo do campo',
            'sao caetano do sul', 'sao lourenco da serra', 'suzano',
            'taboao da serra', 'vargem grande paulista',
        }
        sufixo_fonte = ' [fonte: %s' % fonte_label
        if ctx_texto:
            sufixo_fonte += ' | contexto: "%s"' % ctx_texto[:120]
        sufixo_fonte += ']'
        if fonte_label != 'api':
            sufixo_fonte += ' [ATENCAO: API sem endereco - dado por extracao de texto, verificar]'
        cidade_norm = _norm(cidade)
        grande_sp_norm = {_norm(g) for g in grande_sp}
        if not estado:
            if cidade_norm in grande_sp_norm or cidade_norm == _norm('sao paulo'):
                linhas.append("B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP (UF nao informada)%s" % sufixo_fonte)
            else:
                linhas.append("B12_ENDERECO: ALERTA - reclamante em %s (UF nao informada)%s" % (cidade.upper(), sufixo_fonte))
        elif estado == 'sp' and (cidade_norm in grande_sp_norm or cidade_norm == _norm('sao paulo')):
            linhas.append("B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP%s" % sufixo_fonte)
        else:
            cidade_uf = "%s/%s" % (cidade, estado.upper())
            linhas.append("B12_ENDERECO: ALERTA - reclamante em %s (fora SP)%s" % (cidade_uf, sufixo_fonte))
    else:
        fonte_info = ' [fonte tentada: %s]' % fonte if fonte else ''
        linhas.append("B12_ENDERECO: INFO - endereco do reclamante nao identificado%s" % fonte_info)

    termos_aud = [
        'audiencia virtual', 'audiencia telepresencial', 'videoconferencia',
        'audiencia hibrida', 'audiencia online', 'telepresencialmente',
        'por videoconferencia',
    ]
    encontrado = next((t for t in termos_aud if t in norm), None)
    if encontrado:
        if cd.get('juizo_digital') is True:
            linhas.append("B12_AUD_VIRTUAL: OK - pedido de %s em processo 100%% digital" % encontrado)
        else:
            linhas.append("B12_AUD_VIRTUAL: ALERTA - pedido de %s - verificar compatibilidade" % encontrado)
    else:
        linhas.append("B12_AUD_VIRTUAL: OK - sem pedido de audiencia virtual/telepresencial")
    return linhas


# ---------------------------------------------------------------------------
# B13 - Rito processual
# ---------------------------------------------------------------------------


def _checar_rito(texto: str, capa_dados: Dict[str, Any], pjdp_detectado: bool = False) -> str:
    rito_dec = capa_dados.get('rito_declarado')
    if not rito_dec:
        m_rito = re.search(r'RITO[:\s]+(SUMAR[IÍ]SSIMO|ORDIN[ÁA]RIO)', texto[:3000], re.IGNORECASE)
        if m_rito:
            rito_dec = 'SUMARISSIMO' if re.search(r'sumar', _norm(m_rito.group(1))) else 'ORDINARIO'

    if pjdp_detectado:
        if not rito_dec:
            return "B13_RITO: ALERTA - Detectada PJDP - rito nao identificado (obrigatorio ORDINARIO)"
        if rito_dec == 'ORDINARIO':
            return "B13_RITO: OK - Detectada PJDP - Rito Ordinario"
        return "B13_RITO: ALERTA - Detectada PJDP - Rito %s incorreto (obrigatorio ORDINARIO)" % rito_dec

    valor = capa_dados.get('valor_causa')
    if valor is None:
        m_valor = re.search(r'valor\s+da\s+causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
        if not m_valor:
            return "B13_RITO: ALERTA - valor da causa nao identificado"
        try:
            valor = float(m_valor.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            return "B13_RITO: ALERTA - valor da causa em formato invalido"

    if valor <= ALCADA:
        rito_correto = 'ALCADA'
        motivo = 'R$ %.2f <= alcada R$ %.2f' % (valor, ALCADA)
    elif valor <= RITO_SUMARISSIMO_MAX:
        rito_correto = 'SUMARISSIMO'
        motivo = 'R$ %.2f entre alcada e 40 SM' % valor
    else:
        rito_correto = 'ORDINARIO'
        motivo = 'R$ %.2f > R$ %.2f' % (valor, RITO_SUMARISSIMO_MAX)

    if not rito_dec:
        return "B13_RITO: INFO - rito nao identificado na capa; calculado: %s (%s)" % (rito_correto, motivo)
    if rito_dec == rito_correto or (rito_correto == 'ALCADA' and rito_dec == 'SUMARISSIMO'):
        return "B13_RITO: OK - %s compativel (%s)" % (rito_dec, motivo)
    return "B13_RITO: ALERTA - rito declarado %s incompativel; correto: %s (%s)" % (
        rito_dec, rito_correto, motivo)


# ---------------------------------------------------------------------------
# B14 - Art. 611-B CLT
# ---------------------------------------------------------------------------


def _checar_art611b(texto: str) -> str:
    for linha in texto.splitlines():
        if re.search(r'art\.?\s*611-?B', linha, re.IGNORECASE):
            if re.search(r'clt|coletiv', linha, re.IGNORECASE):
                return "B14_ART611B: ALERTA - mencao art. 611-B CLT - colocar lembrete no processo"
    return "B14_ART611B: OK"
