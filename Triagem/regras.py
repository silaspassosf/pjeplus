import re
from typing import Any, Dict, List, Tuple

from .constants import ALCADA, INTERVALOS_CEP_ZONA_SUL, INTERVALOS_CEP_ZONA_LESTE, INTERVALOS_CEP_RUI_BARBOSA, RITO_SUMARISSIMO_MAX
from .utils import _norm


# UFs válidas para validar resultado do fallback de texto
_UF_BRASIL = {
    'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms',
    'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc',
    'sp', 'se', 'to'
}

_TERMOS_PROC_TITULO = ['procuracao', 'mandato']
_TERMOS_ID_TITULO = [
    'rg', 'cnh', 'documento de identidade', 'identidade', 'doc identidade',
    'documento pessoal', 'documento de identificacao', 'identificacao',
]
_TERMOS_PROC_BODY = [
    'outorgo', 'poderes', 'por este instrumento particular', 'constituir como',
    'procuracao', 'mandato', 'outorgante', 'outorgado'
]
_TERMOS_ID_BODY = [
    'registro geral', 'carteira de identidade', 'carteira nacional de habilitacao',
    'secretaria de seguranca publica', 'documento de identidade',
    'data de nascimento', 'filiacao', 'naturalidade'
]


def _checar_procuracao_e_identidade(
    anexos: List[Dict[str, Any]], nome_reclamante: str = ''
) -> str:
    proc_via = None
    id_via = None

    for anx in anexos:
        tref = _norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
        tbody = _norm(anx.get('texto') or '')
        tnome = (anx.get('titulo') or anx.get('tipo') or '').strip()

        if proc_via is None:
            if any(t in tref for t in _TERMOS_PROC_TITULO):
                proc_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_PROC_BODY):
                proc_via = f'conteudo:"{tnome or "(sem titulo)"}'

        if id_via is None:
            if any(t in tref for t in _TERMOS_ID_TITULO):
                id_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_ID_BODY):
                id_via = f'conteudo:"{tnome or "(sem titulo)"}'

    extra_proc = ''
    if proc_via and nome_reclamante:
        nome_norm = _norm(nome_reclamante)
        for anx in anexos:
            tref = _norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
            tbody = _norm(anx.get('texto') or '')
            if (any(t in tref for t in _TERMOS_PROC_TITULO)
                    or (tbody and any(t in tbody for t in _TERMOS_PROC_BODY))):
                sobrenome = nome_norm.split()[-1] if nome_norm.split() else ''
                if sobrenome and len(sobrenome) > 3 and sobrenome in tbody:
                    extra_proc = ' [nome reclamante localizado na procuracao]'
                else:
                    extra_proc = ' [ATENCAO: nome reclamante nao localizado na procuracao]'
                break

    tem_proc = proc_via is not None
    tem_id = id_via is not None

    if tem_proc and tem_id:
        return (f'B1_DOCS: OK - procuracao ({proc_via}){extra_proc} '
                f'e doc identidade ({id_via}) presentes')
    if not tem_proc and not tem_id:
        return 'B1_DOCS: ALERTA - faltam procuracao e copia de documento de identidade em anexos separados'
    if not tem_proc:
        return f'B1_DOCS: ALERTA - falta procuracao em anexo (doc identidade: {id_via})'
    return f'B1_DOCS: ALERTA - falta copia de documento de identidade em anexo (procuracao: {proc_via}{extra_proc})'


_CEP_TAG_TERRITORIAL = 1
_CEP_TAG_PRESTACAO = 2
_CEP_TAG_RECLAMADA = 3
_CEP_TAG_GENERICO = 4
_CEP_TAG_RECLAMANTE = 5

_CEP_TERMOS_TERRITORIAL = [
    'competencia territorial', 'competencia funcional', 'foro competente',
    'art. 651', 'art 651', 'artigo 651', 'art.651', 'art651'
]
_CEP_TERMOS_PRESTACAO = [
    'ultimo local', 'prestacao de servico', 'local de trabalho', 'local de prestacao',
    'prestou servicos', 'prestava servicos', 'laborou', 'trabalhou',
    'desempenhou suas atividades', 'desempenhou suas funcoes', 'exerceu suas funcoes',
    'endereco da prestacao', 'prestacao de servicos', 'local de servicos'
]
_CEP_TERMOS_RECLAMANTE = ['residente', 'domiciliad', 'endereco do reclamante', 'residencia do reclamante']
_CEP_TERMOS_RECLAMADA = [
    'cnpj', 'com sede', 'filial', 'estabelecimento', 'sede social',
    'endereco da reclamada', 'sede da empresa',
    'reclamad', 'em face', 'contra o reclamado', 'contra a reclamada',
    'cpf', 'pessoa fisica', 'com endereco', 'endereco a'
]


def _foro_competente(cep_num: int) -> str:
    """Retorna o foro competente para um CEP SP fora da Zona Sul."""
    for lo, hi in INTERVALOS_CEP_ZONA_LESTE:
        if lo <= cep_num <= hi:
            return 'ZONA LESTE'
    for lo, hi in INTERVALOS_CEP_RUI_BARBOSA:
        if lo <= cep_num <= hi:
            return 'RUI BARBOSA'
    return 'RUI BARBOSA'  # default SP (faixas nao mapeadas)


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
        texto,
        re.IGNORECASE
    ))
    if not matches:
        return "B2_CEP: ALERTA - nenhum CEP identificado no documento"

    _reclamados_api = capa_dados.get('reclamados') or []
    ceps_api = [r.get('cep') for r in _reclamados_api if r.get('cep')]
    if ceps_api:
        print(f'[TRIAGEM] ceps_api encontrados: {ceps_api}')

    if _reclamados_api:
        _todos_nomes = ' '.join(r.get('nome', '') for r in _reclamados_api)
        reclamado_norm = _norm(_todos_nomes)
    else:
        reclamado_norm = _norm(capa_dados.get('reclamado_nome') or '')
    _STOPWORDS = {'ltda', 'eireli', 'sa', 'me', 'epp', 'do', 'da', 'de', 'e'}
    palavras_reclamada = [p for p in reclamado_norm.split() if len(p) > 3 and p not in _STOPWORDS]

    _CEP_FONE = re.compile(r'\b(?:telefone|fone|tel|fax|whats|whatsapp)\b', re.IGNORECASE)
    candidatos = []
    for ordem, m in enumerate(matches):
        num = int(m.group(1) + m.group(2) + m.group(3))
        fmt = f"{m.group(1)}.{m.group(2)}-{m.group(3)}"
        inicio = max(0, m.start() - 240)
        fim = min(len(texto), m.end() + 240)
        ctx = texto[inicio:fim]
        ctx_norm = _norm(ctx)
        tag = _cep_tag(ctx_norm, palavras_reclamada)
        explicit = bool(re.search(r'\bCEP\s*[:\-]?\s*$', texto[max(0, m.start() - 12):m.start()], re.IGNORECASE))
        endereco_context = bool(re.search(
            r'\bendereco\b|\blogradouro\b|\bbairro\b|\bmunicipio\b|\buf\b|\bnumero\b|\bcomplemento\b',
            ctx_norm
        )) or any(t in ctx_norm for t in _CEP_TERMOS_PRESTACAO + _CEP_TERMOS_RECLAMADA)
        telefone_proximo = bool(_CEP_FONE.search(ctx_norm))
        candidatos.append((
            tag,
            0 if explicit else 1,
            0 if endereco_context else 1,
            2 if telefone_proximo else 0,
            ordem,
            num,
            fmt,
        ))

    candidatos = [c for c in candidatos if c[3] == 0 or c[1] == 0]
    if not candidatos:
        norm_texto = _norm(texto)
        termos_estritos = _CEP_TERMOS_TERRITORIAL + _CEP_TERMOS_PRESTACAO
        if any(t in norm_texto for t in termos_estritos):
            return "B2_CEP: ALERTA - nenhum CEP de prestacao de servicos identificado no contexto relevante (CEP da reclamada ignorado por regra)"
        if ceps_api:
            _label_sub = 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)'
            _cep_resultado = None
            for _cep_raw in ceps_api:
                if not (len(_cep_raw) == 8 and _cep_raw.isdigit()):
                    continue
                _cn = int(_cep_raw)
                _cf = f"{_cep_raw[:2]}.{_cep_raw[2:5]}-{_cep_raw[5:]}"
                print(f'[TRIAGEM] cep_api testado: {_cf} ({_cn})')
                if any(lo <= _cn <= hi for lo, hi in INTERVALOS_CEP_ZONA_SUL):
                    _cep_resultado = (_cn, _cf, 'ZONA_SUL')
                    break
                if any(lo <= _cn <= hi for lo, hi in INTERVALOS_CEP_ZONA_LESTE):
                    _cep_resultado = (_cn, _cf, 'ZONA LESTE')
                    break
                if any(lo <= _cn <= hi for lo, hi in INTERVALOS_CEP_RUI_BARBOSA):
                    _cep_resultado = (_cn, _cf, 'RUI BARBOSA')
                    break
                print(f'[TRIAGEM] cep_api {_cf} nao pertence a nenhuma faixa SP conhecida — ignorado')
            if _cep_resultado:
                _cn, _cf, _zona = _cep_resultado
                if _zona == 'ZONA_SUL':
                    return (f"B2_CEP: OK - {_cf} ({_cn}) "
                            f"Zona Sul [{_label_sub}]")
                return (f"B2_CEP: ALERTA - Incompetencia Territorial - "
                        f"CEP {_cf} ({_cn}) [{_label_sub}] | foro competente: {_zona}")
            return "B2_CEP: ALERTA - CEPs das reclamadas testados mas nenhum pertence a faixa SP - verificar competencia manualmente"
        return "B2_CEP: ALERTA - nenhum CEP de prestacao de servicos ou reclamada identificado (CEP do reclamante ignorado por regra)"

    candidatos.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))

    _TAG_LABEL = {
        _CEP_TAG_TERRITORIAL: 'competencia territorial (art.651 CLT)',
        _CEP_TAG_PRESTACAO: 'ultimo local de prestacao de servicos (art.651 CLT)',
        _CEP_TAG_RECLAMADA: 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)',
        _CEP_TAG_RECLAMANTE: 'endereco do reclamante (referencia subsidiaria)',
        _CEP_TAG_GENERICO: 'generico',
    }
    _TERMOS_TERRIT = _CEP_TERMOS_TERRITORIAL + _CEP_TERMOS_PRESTACAO
    norm_texto = _norm(texto)
    termos_presentes = [t for t in _TERMOS_TERRIT if t in norm_texto]

    def _sufixo_territ(tag):
        if termos_presentes and tag not in (_CEP_TAG_TERRITORIAL, _CEP_TAG_PRESTACAO):
            return (f' | NOTA: peticao menciona termos de competencia territorial '
                    f'({termos_presentes[0]}) mas CEP nao foi localizado nesse contexto - '
                    f'verificar endereco indicado na secao de competencia/prestacao')
        return ''

    # Separar candidatos do reclamante — tratados exclusivamente na Fase 3
    cands_reclamante = [(cep_num, cep_fmt)
                        for tag, _, _, _, _, cep_num, cep_fmt in candidatos
                        if tag == _CEP_TAG_RECLAMANTE]

    # ── Fase 1: CEPs contextuais (territorial, prestação, reclamada, genérico)
    #    Retorna OK se Zona Sul. Coleta os que caem fora para compor evidência no Fase 2.
    _cands_ctx_fora_zona_sul: List[str] = []  # cep_fmt dos candidatos fora da Zona Sul
    for cand in candidatos:
        best_tag, _, _, _, _, cep_num, cep_fmt = cand
        if best_tag == _CEP_TAG_RECLAMANTE:
            continue  # reservado para Fase 3
        label = _TAG_LABEL[best_tag]
        matched = next(((lo, hi) for lo, hi in INTERVALOS_CEP_ZONA_SUL if lo <= cep_num <= hi), None)
        if matched:
            lo_match, hi_match = matched
            print(f'[TRIAGEM] cep_detectado: {cep_fmt} ({cep_num}) → Zona Sul')
            return (f"B2_CEP: OK - {cep_fmt} ({cep_num}) "
                f"no intervalo {lo_match}-{hi_match} Zona Sul [{label}]{_sufixo_territ(best_tag)}")
        # Fora da Zona Sul: registrar como evidência para Fase 2
        _foro_ctx = None
        for lo, hi in INTERVALOS_CEP_ZONA_LESTE:
            if lo <= cep_num <= hi:
                _foro_ctx = 'ZONA LESTE'
                break
        if not _foro_ctx:
            for lo, hi in INTERVALOS_CEP_RUI_BARBOSA:
                if lo <= cep_num <= hi:
                    _foro_ctx = 'RUI BARBOSA'
                    break
        if _foro_ctx:
            _cands_ctx_fora_zona_sul.append(f'{cep_fmt} ({_foro_ctx})')
            print(f'[TRIAGEM] cep_ctx_fora_zona_sul: {cep_fmt} ({cep_num}) → {_foro_ctx}')

    def _prefixo_alerta() -> str:
        """Monta prefixo descritivo para ALERTA de Fase 2 incluindo evidência de Fase 1."""
        if _cands_ctx_fora_zona_sul:
            ctx_str = ', '.join(_cands_ctx_fora_zona_sul)
            return (f"B2_CEP: ALERTA - Incompetencia Territorial - "
                    f"CEPs de contexto fora da Zona Sul ({ctx_str}) + reclamada: ")
        return "B2_CEP: ALERTA - Incompetencia Territorial - "

    # ── Fase 2: CEPs das reclamadas via API → pode gerar OK ou ALERTA
    if ceps_api:
        _label_sub = 'sede da reclamada'
        for _cep_raw in ceps_api:
            if not (len(_cep_raw) == 8 and _cep_raw.isdigit()):
                continue
            _cn = int(_cep_raw)
            _cf = f"{_cep_raw[:2]}.{_cep_raw[2:5]}-{_cep_raw[5:]}"
            if any(lo <= _cn <= hi for lo, hi in INTERVALOS_CEP_ZONA_SUL):
                print(f'[TRIAGEM] cep_api_detectado: {_cf} ({_cn}) → Zona Sul')
                _ok_sfx = ' (apos nao localizar CEP de prestacao de servicos)' if _cands_ctx_fora_zona_sul else ''
                return (f"B2_CEP: OK - {_cf} ({_cn}) Zona Sul [{_label_sub}{_ok_sfx}]")
            for lo, hi in INTERVALOS_CEP_ZONA_LESTE:
                if lo <= _cn <= hi:
                    print(f'[TRIAGEM] cep_api_detectado: {_cf} ({_cn}) → ZONA LESTE')
                    return (_prefixo_alerta() +
                            f"CEP {_cf} ({_cn}) [{_label_sub}] | foro competente: ZONA LESTE")
            for lo, hi in INTERVALOS_CEP_RUI_BARBOSA:
                if lo <= _cn <= hi:
                    print(f'[TRIAGEM] cep_api_detectado: {_cf} ({_cn}) → RUI BARBOSA')
                    return (_prefixo_alerta() +
                            f"CEP {_cf} ({_cn}) [{_label_sub}] | foro competente: RUI BARBOSA")

    # ── Fase 3: CEP do reclamante — SOMENTE se há pedido expresso de competência
    #    pelo domicílio do autor na petição E o CEP está na Zona Sul
    _TERMOS_DOM_AUTOR = [
        'domicilio do reclamante', 'domicilio do autor', 'foro do domicilio',
        'competencia pelo domicilio', 'empregado viajante', 'trabalhador externo',
        'sem local fixo de trabalho', 'art. 651, § 3', 'art 651, § 3',
        'art.651, § 3', 'art 651 paragrafo 3', 'art. 651 paragrafo terceiro',
    ]
    if cands_reclamante and any(t in norm_texto for t in _TERMOS_DOM_AUTOR):
        cep_num_r, cep_fmt_r = cands_reclamante[0]
        label_r = _TAG_LABEL[_CEP_TAG_RECLAMANTE]
        for lo, hi in INTERVALOS_CEP_ZONA_SUL:
            if lo <= cep_num_r <= hi:
                print(f'[TRIAGEM] cep_reclamante_dom: {cep_fmt_r} ({cep_num_r}) → Zona Sul (pedido domicilio)')
                return (f"B2_CEP: OK - {cep_fmt_r} ({cep_num_r}) "
                        f"no intervalo {lo}-{hi} Zona Sul [{label_r}] | DOMICILIO_AUTOR")
        print(f'[TRIAGEM] cep_reclamante_dom: {cep_fmt_r} ({cep_num_r}) pedido domicilio mas fora da Zona Sul — ignorado')

    return "B2_CEP: ALERTA - nenhum CEP de SP (Zona Sul/Leste/Rui Barbosa) identificado no processo"


_PJDP_NOME_KEYWORDS = [
    'municipio', 'prefeitura', 'estado de', 'estado do', 'governo do estado',
    'governo do municipio', 'uniao federal', 'ministerio', 'autarquia',
    'fazenda publica', 'inss', 'tribunal',
]


def _detectar_pjdp_api(capa_dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Detecta PJDP verificando nomes das reclamadas extraidas via API.
    Retorna (detectado, nome_da_reclamada_gatilho).
    """
    reclamados = capa_dados.get('reclamados') or []
    for r in reclamados:
        nome_norm = _norm(r.get('nome', ''))
        for kw in _PJDP_NOME_KEYWORDS:
            if kw in nome_norm:
                return True, r.get('nome', nome_norm)
    return False, ''


def _checar_partes(texto: str, capa_dados: Dict[str, Any]) -> List[str]:
    linhas = []
    norm = _norm(texto)
    corte_preliminarmente = norm.find('preliminarmente')
    contexto_partes = norm[:corte_preliminarmente] if corte_preliminarmente != -1 else norm[:2600]

    nome_rec = capa_dados.get('reclamante_nome') or ''
    cpf_rec = capa_dados.get('reclamante_cpf') or ''
    if nome_rec:
        sufixo = f' CPF={cpf_rec}' if cpf_rec else ''
        rec_info = f' - reclamante={nome_rec[:60]}{sufixo}'
    else:
        m = re.search(
            r'RECLAMANTE[:\s]+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-z\s\.]+?)'
            r'(?:\s*[-–]\s*|\s*CPF|\n)',
            texto[:3000])
        if m:
            rec_info = f' - reclamante={m.group(1).strip()[:60]}'
        else:
            rec_info = ''
            linhas.append("B3_PARTES: ALERTA - reclamante nao identificado na capa")

    m_nasc = re.search(r'nascid[ao][:\s]+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', norm)
    if m_nasc:
        try:
            ano_nasc = int(m_nasc.group(3))
            data_dist = capa_dados.get('distribuido_em') or ''
            m_ano = re.search(r'(\d{4})$', data_dist)
            ano_ref = int(m_ano.group(1)) if m_ano else 2026
            if (ano_ref - ano_nasc) < 18:
                linhas.append(
                    f"B3_PARTES: ALERTA - parte menor de idade "
                    f"(nasc {m_nasc.group(3)}) - incluir MPT custos legis"
                )
        except Exception:
            pass

    pjdp_detectado, pjdp_nome = _detectar_pjdp_api(capa_dados)
    if not pjdp_detectado and not capa_dados.get('reclamados'):
        # Fallback: analise de texto quando nao ha dados de reclamadas via API
        _RE_PJDP = re.compile(
            r'\b(municipio|prefeitura|uniao\s+federal|autarquia|fazenda\s+p[ue]blica|estado\b(?!\s+de\b))\b')
        _RE_ADDR_LABEL = re.compile(r'municipio\s*:', re.IGNORECASE)
        _RE_ESTADO_LABEL = re.compile(r'estado\s*:', re.IGNORECASE)
        _RE_PRIVADO = re.compile(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado')
        for m_pjdp in _RE_PJDP.finditer(contexto_partes):
            trecho = contexto_partes[max(0, m_pjdp.start() - 80): m_pjdp.end() + 20]
            if _RE_ADDR_LABEL.search(trecho) or _RE_ESTADO_LABEL.search(trecho):
                continue
            trecho_amplo = contexto_partes[max(0, m_pjdp.start() - 200): m_pjdp.end() + 50]
            if _RE_PRIVADO.search(trecho_amplo):
                continue
            pjdp_detectado = True
            pjdp_nome = m_pjdp.group(1)
            break

    if pjdp_detectado:
        linhas.append(
            f"B3_PARTES: ALERTA - PJDP no polo passivo (rito ordinario obrigatorio); "
            f"detectado via nome: {pjdp_nome}"
        )

    if not any('ALERTA' in l for l in linhas):
        linhas.append(f"B3_PARTES: OK{rec_info}")
    return linhas


def _checar_segredo(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)
    tem_pedido_no_texto = bool(re.search(r'segredo\s+de\s+justi[cç]a|tramita[cç][aã]o\s+sigilosa', norm))
    segredo_na_capa = capa_dados.get('segredo_justica')
    if segredo_na_capa is True and not tem_pedido_no_texto:
        return "B4_SEGREDO: ALERTA - certidao indica segredo mas nao ha requerimento fundamentado na peticao"
    if tem_pedido_no_texto:
        fund = bool(re.search(r'art\.?\s*189', norm))
        suf = 'com art. 189 CPC' if fund else 'sem fundamentacao (art. 189 CPC ausente)'
        return f"B4_SEGREDO: ALERTA - pedido de segredo de justica {suf}"
    return "B4_SEGREDO: OK"


_RE_CNPJ_NUM = re.compile(r'\b(?:\d{2}(?:[\.\s]?\d{3}){2}/\d{4}-?\d{2}|\d{14})\b', re.IGNORECASE)
_RE_CPF_NUM = re.compile(r'\b(?:\d{3}(?:[\.\s]?\d{3}){2}-?\d{2}|\d{11})\b', re.IGNORECASE)

_CNPJ_CONTEXTOS = (
    'cnpj', 'inscrita no cnpj', 'inscrito no cnpj', 'cnpj sob', 'cnpj nº', 'cnpj no',
    'reclamad', 'pessoa juridica', 'pessoa juridica de direito privado',
    'pessoa juridica de direito publico', 'empresa', 'sociedade', 'matriz', 'filial', 'sede',
)

_CPF_CONTEXTOS = (
    'cpf', 'reclamad', 'pessoa fisica', 'pessoa natural',
)


def _extrair_numeros_contextuais(texto: str, numero_re: re.Pattern, contextos: Tuple[str, ...]) -> List[str]:
    candidatos: List[str] = []

    def _registrar_bloco(bloco: str) -> None:
        bloco_norm = _norm(bloco)
        if not any(ctx in bloco_norm for ctx in contextos):
            return
        for m in numero_re.finditer(bloco_norm):
            raw = re.sub(r'\D', '', m.group(0))
            if raw and raw not in candidatos:
                candidatos.append(raw)

    blocos = [b.strip() for b in re.split(r'\n\s*\n+', texto) if b.strip()]
    for bloco in blocos:
        _registrar_bloco(bloco)

    if candidatos:
        return candidatos

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    for linha in linhas:
        _registrar_bloco(linha)

    if candidatos:
        return candidatos

    texto_norm = _norm(texto)
    for m in numero_re.finditer(texto_norm):
        ctx = texto_norm[max(0, m.start() - 220): min(len(texto_norm), m.end() + 220)]
        if not any(c in ctx for c in contextos):
            continue
        raw = re.sub(r'\D', '', m.group(0))
        if raw and raw not in candidatos:
            candidatos.append(raw)
    return candidatos


def _checar_reclamadas(texto: str, capa_dados: Dict[str, Any]) -> List[str]:
    linhas = []
    reclamados_api = capa_dados.get('reclamados') or []

    sem_endereco = capa_dados.get('reclamadas_sem_endereco') or []
    if sem_endereco:
        linhas.append(
            f'B5_RECLAMADAS: ALERTA - {len(sem_endereco)} reclamada(s) SEM ENDERECO CADASTRADO'
        )

    com_dom = capa_dados.get('reclamadas_com_dom_elet', 0) or 0
    total_reclamadas = len(reclamados_api)
    if total_reclamadas > 0:
        if com_dom > 0:
            linhas.append(f'B5_RECLAMADAS OK - {com_dom}/{total_reclamadas} reclamada(s) com DOMICILIO ELETRONICO')
        else:
            linhas.append('B5_RECLAMADAS ALERTA - NENHUMA reclamada com domicilio eletronico habilitado')

    if not reclamados_api:
        linhas.append("B5_RECLAMADAS: ALERTA - dados de partes nao disponiveis via API")
        return linhas

    n_total = len(reclamados_api)
    n_com_end = sum(1 for r in reclamados_api if r.get('cep') or r.get('endereco'))
    ceps_rec = [r['cep'] for r in reclamados_api if r.get('cep')]
    ceps_str = ', '.join(ceps_rec) if ceps_rec else 'nenhum'
    sem_doc = [r for r in reclamados_api if len(r.get('cpfcnpj', '')) not in (11, 14)]
    if sem_doc:
        linhas.append(f"B5_RECLAMADAS: ALERTA - {len(sem_doc)} reclamada(s) sem CPF/CNPJ valido na API")
    linhas.append(
        f"B5_RECLAMADAS: OK - {n_total} reclamada(s); "
        f"{n_com_end} com endereco detectado; "
        f"CEPs analisados: {ceps_str}"
    )

    cnpjs = [r['cpfcnpj'] for r in reclamados_api if len(r.get('cpfcnpj', '')) == 14]
    filiais = [c for c in cnpjs if c[8:12] != '0001']
    matrizes = {c[:8] for c in cnpjs if c[8:12] == '0001'}
    for f in filiais:
        if f[:8] not in matrizes:
            linhas.append(f"B5_RECLAMADAS: ALERTA - filial {f[:8]}/... sem referencia a matriz")
            break
    return linhas


def _checar_tutela(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)
    idx = max(norm.rfind('pedidos'), norm.rfind('dos pedidos'),
              norm.rfind('requerimentos'), len(norm) - 4000)
    sec_norm = norm[max(0, idx):]
    termos = [
        'tutela de urgencia', 'tutela antecipada', 'tutela provisoria',
        'tutela de evidencia', 'tutela cautelar', 'medida liminar',
        'medida cautelar', 'medida de urgencia', 'tutela liminar',
        'art. 300', 'art. 305', 'art. 311',
    ]
    for t in termos:
        pos = sec_norm.find(t)
        if pos != -1:
            ctx = _pag_contexto(texto, max(0, idx) + pos, janela=300)
            return (f"B6_TUTELA: ALERTA - pedido tutela provisoria ({t}) "
                    f"- encaminhar para despacho\n  {ctx}")
    if capa_dados.get('medida_urgencia') is True:
        return "B6_TUTELA: ALERTA - certidao indica medida de urgencia mas termo nao localizado nos pedidos"
    return "B6_TUTELA: OK"


def _checar_digital(texto: str, capa_dados: Dict[str, Any]) -> str:
    norm = _norm(texto)
    pedido_digital = bool(re.search(
        r'(ju[ií]zo\s*100%?\s*digital|ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'manifesta[cç][aã]o\s+de\s+ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'requer(?:e|ido)?\s+o\s+ju[ií]zo\s*100%?\s*digital)', norm))
    if not pedido_digital:
        return "B7_DIGITAL: OK - sem pedido expresso de Juizo 100% Digital na peticao"

    processo_digital = capa_dados.get('juizo_digital')
    if processo_digital is True:
        return "B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado e processo ja marcado na API"
    if processo_digital is False:
        return "B7_DIGITAL: ALERTA - pedido expresso de Juizo 100% Digital identificado, mas processo nao marcado na API"
    return "B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado, mas marcacao do processo nao confirmada na API"


def _checar_pedidos_liquidados(texto: str) -> str:
    _RE_SKIP_PEDIDO = re.compile(
        r'atribu[ií]|n[aã]o inferior|valor da causa|valor atribu[ií]do|'
        r'n[aã]o deve ser utiliz|fator limitador|estimativa|base de calculo',
        re.IGNORECASE
    )

    _RE_VERBA_HEADER = re.compile(
        r'\b(saldo.sal[aá]rio|aviso\s*pr[eé]vio|f[eé]rias|fgts|'
        r'multa\s*(art|do)?\s*(art\.?\s*4[67][67]|dos\s*40)?|dano\s*moral|gorjeta|'
        r'adicional|13[°oº]?\s*sal[aá]rio|d[eé]cimo|hora\s*extra|'
        r'indeniza[cç][aã]o|seguro[- ]desemprego|libera[cç][aã]o)\b',
        re.IGNORECASE
    )

    secao = ''
    itens = []
    seen = set()

    for linha in texto.split('\n'):
        ls = linha.strip()
        if not ls:
            continue
        ln = _norm(ls)

        if len(ls) < 70 and 'r$' not in ln and _RE_VERBA_HEADER.search(ln):
            secao = ls
            continue

        if _RE_SKIP_PEDIDO.search(ln):
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
            itens.append(f"  [{secao_label} - R$ {mv.group(1)}]")

    out = []
    if not itens:
        amostra = []
        for linha in texto.split('\n'):
            if re.search(r'R\$\s*[\d\.\,]+', linha):
                amostra.append(linha.strip())
                if len(amostra) == 3:
                    break
        if amostra:
            out.append("B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados")
            out.append("B8_PEDIDOS: amostra de linhas com valores encontrados:")
            out.extend(f"  {linha}" for linha in amostra)
        else:
            out.append("B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados")
    else:
        out.append(f"B8_PEDIDOS: OK - {len(itens)} pedido(s) com valor:")
        out.extend(itens[:2])
    return '\n'.join(out)


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
        return f"B9_PESSOA_FIS: OK - pessoa fisica com fundamentacao juridica ({nomes})"
    return f"B9_PESSOA_FIS: ALERTA - pessoa fisica no polo passivo sem fundamentacao clara ({nomes})"


def _checar_litispendencia(texto: str, associados_sistema: List[Dict[str, Any]] = None) -> str:
    termos_juris = [
        "acordao", "ementa", "jurisprudencia", "precedente", "relator", "turma",
        "tst", "stj", "stf", "dejt", "sumula", "oj", "rot", "rorsum", "rr", "airr"
    ]
    padrao_processo = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos_reais = []
    for linha in texto.split('\n'):
        norm_linha = _norm(linha)
        if any(t in norm_linha for t in termos_juris):
            continue
        matches = padrao_processo.findall(linha)
        if matches:
            processos_reais.extend(matches)
    unicos_peticao = list(dict.fromkeys(processos_reais))

    nums_sistema: List[str] = []
    for assoc in (associados_sistema or []):
        if not isinstance(assoc, dict):
            continue
        num = str(
            assoc.get('numero') or assoc.get('numeroCnj')
            or assoc.get('numeroProcesso') or assoc.get('num') or ''
        ).strip()
        if re.match(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', num):
            nums_sistema.append(num)

    partes_alerta: List[str] = []
    for num in nums_sistema:
        if num in unicos_peticao:
            partes_alerta.append(
                f"Prevencao detectada no sistema - processo {num} (tambem mencionado na peticao)"
            )
        else:
            partes_alerta.append(f"Prevencao detectada no sistema - processo {num}")

    apenas_peticao = [n for n in unicos_peticao if n not in nums_sistema]
    if nums_sistema:
        if apenas_peticao:
            outros = ', '.join(apenas_peticao[:4])
            partes_alerta.append(
                f"mencao a outros processos na peticao ({outros}) "
                f"- verificar litispendencia/prevenção/coisa julgada"
            )
    elif len(unicos_peticao) > 1:
        outros = ', '.join(unicos_peticao[1:4])
        partes_alerta.append(
            f"mencao a outros processos na peticao ({outros}) "
            f"- verificar litispendencia/prevenção/coisa julgada"
        )

    if not partes_alerta:
        norm = _norm(texto)
        for t in ['acao anterior', 'processo anterior', 'ja ajuizou', 'litispendencia',
                  'coisa julgada', 'acordo nao homologado']:
            pos = norm.find(t)
            if pos != -1:
                ctx = _pag_contexto(texto, pos, janela=200)
                partes_alerta.append(f"possivel '{t}'\n  {ctx}")
                break

    if partes_alerta:
        corpo = '\n'.join(partes_alerta)
        return f"B10_LITISPEND: ALERTA - {corpo}"
    return "B10_LITISPEND: OK"


_RE_RECLAMADA_HEADER = re.compile(
    r'(?:\d+[ºo°]?\.?\s*|primeira\s+|segunda\s+|terceira\s+|quarta\s+)RECLAMAD[AO]\b'
    r'|RECLAMAD[AO]\s*[:\-—–]',
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
            r'|subsidiariamente\s+responsaveis?',
            norm
        ):
            return [f"B11_RESPONSAB: ALERTA - 1 reclamada mas pedido de responsabilidade {tipo_resp} (autuacao incorreta?)"]
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
        r'|respondam?\s+subsidiariamente',
        norm
    ))

    if not tem_pedido:
        for m in re.finditer(
            r'(?:primeira|segunda|terceira|demais|todas?\s+as?)\s+reclamad[ao]',
            norm
        ):
            janela = norm[max(0, m.start() - 400): m.end() + 400]
            if re.search(
                r'responsabilid|devedora|solidar|subsidiar'
                r'|prestadora\s+de\s+servico|tomadora',
                janela
            ):
                tem_pedido = True
                break

    tem_causa = bool(re.search(
        r'tomador\s+de\s+servico|terceirizacao|prestacao\s+de\s+servico'
        r'|grupo\s+economico|subempreitada|terceirizad[ao]|terceirizado'
        r'|prestadora\s+(?:de\s+)?servicos?'
        r'|s[oó]ci[ao][- ]proprietari|s[oó]ci[ao][- ]gerente'
        r'|dono\s+da\s+empresa|proprietari[ao]\s+d[ao]'
        r'|empres[ao]\s+d[ao]\s+grupo'
        r'|administrador[ao]|s[oó]ci[ao]\b'
        r'|culpa\s+in\s+eligendo|culpa\s+in\s+vigilando',
        norm
    ))

    if not tem_pedido:
        return [f"B11_RESPONSAB: ALERTA - {n_rec} reclamadas sem pedido de responsabilidade subsidiaria/solidaria (emenda necessaria)"]
    if not tem_causa:
        return [f"B11_RESPONSAB: ALERTA - pedido de responsabilidade {tipo_resp} sem causa de pedir explicita ({n_rec} reclamadas)"]
    return [f"B11_RESPONSAB: OK - {n_rec} reclamadas com pedido de responsabilidade {tipo_resp} e causa de pedir"]


def _checar_endereco_reclamante(texto: str, capa_dados: Dict[str, Any] = None) -> List[str]:
    linhas = []
    norm = _norm(texto)
    cd = capa_dados or {}

    _mun_api = cd.get('reclamante_municipio') or ''
    _uf_api = cd.get('reclamante_uf') or ''
    _fonte = cd.get('reclamante_end_fonte') or ('api' if _mun_api else 'texto')

    ctx_texto = None
    if _mun_api:
        # API retornou ao menos o município — usar mesmo sem UF
        cidade = _mun_api
        estado = _uf_api  # pode estar vazio se a API não preencheu
        fonte_label = 'api'
    else:
        # Endereço do reclamante fica no 1º parágrafo, perto do nome já detectado pela API
        nome_rec = cd.get('reclamante_nome') or ''
        if nome_rec:
            _nome_norm = _norm(nome_rec)[:20]
            _idx_nome = norm.find(_nome_norm)
            _busca_ini = max(0, _idx_nome) if _idx_nome >= 0 else 0
        else:
            _busca_ini = 0
        _trecho = norm[_busca_ini: _busca_ini + 1200]
        # residente/domiciliado (reclamante é sempre pessoa física)
        # [\s\S]{0,200}? cobre período no meio do endereço (ex: "n. 5")
        # separador [ /\-]+ cobre em-dash que virou espaço após _norm
        # UF validada contra _UF_BRASIL
        _m = re.search(
            r'(?:residente|domiciliad[ao])[\s\S]{0,200}?'
            r'([a-z][a-z ]{2,35}?)[ /\-]+([a-z]{2})\b',
            _trecho)
        cidade = None
        estado = None
        if _m:
            _c = _m.group(1).strip()
            _e = _m.group(2)
            if _e in _UF_BRASIL:
                cidade = _c
                estado = _e
                inicio = max(0, _m.start() - 60)
                fim = min(len(_trecho), _m.end() + 60)
                ctx_texto = _trecho[inicio:fim].replace('\n', ' ').strip()
        fonte_label = f'texto ({_fonte})' if _fonte != 'texto' else 'texto'

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
            'taboao da serra', 'vargem grande paulista'
        }
        sufixo_fonte = f' [fonte: {fonte_label}'
        if ctx_texto:
            sufixo_fonte += f' | contexto: \"{ctx_texto[:120]}\"'
        sufixo_fonte += ']'
        if fonte_label != 'api':
            sufixo_fonte += ' [ATENCAO: API sem endereco - dado por extracao de texto, verificar]'
        if not estado:
            # API retornou município mas sem UF — checar se está na Grande SP
            _cidade_norm_cmp = _norm(cidade)
            if _cidade_norm_cmp == 'sao paulo' or _cidade_norm_cmp in grande_sp:
                linhas.append(f"B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP (UF nao informada pela API){sufixo_fonte}")
            else:
                linhas.append(f"B12_ENDERECO: ALERTA - reclamante em {cidade.upper()} (UF nao informada pela API) - verificar se fora de SP{sufixo_fonte}")
        elif estado == 'sp' and (_norm(cidade) in grande_sp or _norm(cidade) == 'sao paulo'):
            linhas.append(f"B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP{sufixo_fonte}")
        else:
            cidade_uf = f"{cidade}/{estado.upper()}"
            linhas.append(f"B12_ENDERECO: ALERTA - reclamante em {cidade_uf} (fora SP) - verificar audiencia virtual{sufixo_fonte}")
    else:
        _fonte_info = f' [fonte tentada: {_fonte}]' if _fonte else ''
        linhas.append(f"B12_ENDERECO: INFO - endereco do reclamante nao identificado{_fonte_info}")

    termos_aud = [
        'audiencia virtual', 'audiencia telepresencial', 'videoconferencia',
        'audiencia hibrida', 'audiencia online', 'telepresencialmente',
        'por videoconferencia',
    ]
    encontrado = next((t for t in termos_aud if t in norm), None)
    if encontrado:
        processo_digital = cd.get('juizo_digital')
        if processo_digital is True:
            linhas.append(f"B12_AUD_VIRTUAL: OK - pedido de {encontrado} em processo 100% digital")
        else:
            linhas.append(f"B12_AUD_VIRTUAL: ALERTA - pedido de {encontrado} - verificar compatibilidade com pauta da vara")
    else:
        linhas.append("B12_AUD_VIRTUAL: OK - sem pedido de audiencia virtual/telepresencial")
    return linhas


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
        return f"B13_RITO: ALERTA - Detectada PJDP - Rito {rito_dec} incorreto (obrigatorio ORDINARIO)"

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
        motivo = f'R$ {valor:_.2f} <= alcada R$ {ALCADA:_.2f}'.replace('_', '.')
    elif valor <= RITO_SUMARISSIMO_MAX:
        rito_correto = 'SUMARISSIMO'
        motivo = f'R$ {valor:_.2f} entre alcada e 40 SM'.replace('_', '.')
    else:
        rito_correto = 'ORDINARIO'
        motivo = f'R$ {valor:_.2f} > R$ {RITO_SUMARISSIMO_MAX:_.2f}'.replace('_', '.')

    if not rito_dec:
        return (f"B13_RITO: INFO - rito nao identificado na capa; "
                f"calculado: {rito_correto} ({motivo})")
    if rito_dec == rito_correto or (rito_correto == 'ALCADA' and rito_dec == 'SUMARISSIMO'):
        return f"B13_RITO: OK - {rito_dec} compativel ({motivo})"
    return (f"B13_RITO: ALERTA - rito declarado {rito_dec} incompativel; "
            f"correto: {rito_correto} ({motivo})")


def _checar_art611b(texto: str) -> str:
    for linha in texto.splitlines():
        if re.search(r'art\.?\s*611-?B', linha, re.IGNORECASE):
            if re.search(r'clt|coletiv', linha, re.IGNORECASE):
                return "B14_ART611B: ALERTA - mencao art. 611-B CLT - colocar lembrete no processo"
    return "B14_ART611B: OK"


__all__ = [
    '_detectar_pjdp_api',
    '_checar_procuracao_e_identidade',
    '_checar_cep',
    '_checar_partes',
    '_checar_segredo',
    '_checar_reclamadas',
    '_checar_tutela',
    '_checar_digital',
    '_checar_pedidos_liquidados',
    '_checar_pessoa_fisica',
    '_checar_litispendencia',
    '_checar_responsabilidade',
    '_checar_endereco_reclamante',
    '_checar_rito',
    '_checar_art611b',
]
