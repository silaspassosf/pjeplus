"""
tr.py - Triagem de petiÃ§Ã£o inicial trabalhista.

Uso: triagem_peticao(driver) -> str (max 8000 chars)
Driver deve estar autenticado na pÃ¡gina do processo (detalhe) no PJe.
ExtraÃ§Ã£o via API autenticada (session_from_driver + PjeApiClient).
Sem dependÃªncia de interface visual ou DOM.
"""

import re
import io
import logging
import unicodedata
import threading
from typing import List, Dict, Any

from api.variaveis import PjeApiClient, session_from_driver

# Suprime warnings de metadados de fonte do pdfminer (ex: "Could not get FontBBox...")
logging.getLogger('pdfminer').setLevel(logging.ERROR)

# ===== CONSTANTES =====
SALARIO_MINIMO = 1622.00                          # 2026
ALCADA = SALARIO_MINIMO * 2                        # R$ 3.244,00
RITO_SUMARISSIMO_MAX = SALARIO_MINIMO * 40         # R$ 64.880,00

INTERVALOS_CEP_ZONA_SUL = [
    (4307000, 4314999), (4316000, 4477999), (4603000, 4620999),
    (4624000, 4703999), (4708000, 4967999), (5640000, 5642999),
    (5657000, 5665999), (5692000, 5692999), (5703000, 5743999),
    (5745000, 5750999), (5752000, 5895999),
]


def _norm(t: str) -> str:
    return unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode().lower()


# ===== PRÃ‰-PROCESSAMENTO â€” RemoÃ§Ã£o de cabeÃ§alho/rodapÃ© =====

# NÃ­vel 1: artefatos PJe determinÃ­sticos (risco zero)
_RE_ARTEFATOS_PJE = re.compile(
    r'(?:^Documento assinado eletronicamente por[^\n]*\n?)'
    r'|(?:^https?://pje\.[^\n]+\n?)'
    r'|(?:^N[uÃº]mero do documento\s+\d+[^\n]*\n?)'
    r'|(?:^(?:Start|End) of OCR for page \d+[^\n]*\n?)'
    r'|(?:^\s*PJe\s*\n?)'
    r'|(?:^\s*LOGO\s+IMAGE[^\n]*\n?)',
    re.IGNORECASE | re.MULTILINE,
)

# NÃ­vel 2: inÃ­cio do conteÃºdo jurÃ­dico â€” ancora o fingerprint do cabeÃ§alho
_RE_INICIO_JURIDICO = re.compile(
    r'\b(EXCELENT[ÃI]SSIM[OA]|RECLAMAÃ‡ÃƒO\s+TRABALHISTA|'
    r'RECLAMAÃ‡ÃƒO\s+TRABALHISTA|AO\s+EXCELENT|'
    r'INSTRUMENTO\s+PARTICULAR|AÃ‡[ÃƒA]O\s+DE\s+CONSIGNAÃ‡)',
    re.IGNORECASE,
)


def _remover_artefatos_pje(texto: str) -> str:
    """NÃ­vel 1: remove marcadores PJe/OCR determinÃ­sticos (risco zero)."""
    return _RE_ARTEFATOS_PJE.sub('', texto)


def _aprender_cabecalho(texto_sem_artefatos: str) -> list:
    """
    Extrai as linhas de cabeÃ§alho do escritÃ³rio a partir da 1Âª pÃ¡gina.
    Retorna lista de strings normalizadas que representam o fingerprint.
    """
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
        # Aceitar apenas linhas curtas (< 90 chars) que pareÃ§am cabeÃ§alho:
        # nome do escritÃ³rio, telefone, email, URL, endereÃ§o
        if len(ln) >= 90:
            continue
        ln_norm = _norm(ln)
        tem_contato = bool(re.search(
            r'\d{2}[\s\-]?\d{4}[\s\-]?\d{4}'   # telefone
            r'|@\w|www\.'                         # email/url
            r'|\.com\.br|\.adv\.br',
            ln_norm,
        ))
        eh_nome_escritorio = bool(re.match(
            r'^[A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘\s\-\.]{4,}$', ln
        ))
        tem_endereco_escritorio = bool(
            re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cÃ§]a|sala)\b', ln_norm)
            and re.search(r'\d', ln)
            and (
                'cep' in ln_norm
                or re.search(r'\d{5}\s*[-]?\s*\d{3}', ln_norm)
                or re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cÃ§]a)\b.*\d', ln_norm)
                and any(k in ln_norm for k in ('adv', 'escrit', 'oab', 'advogado', 'advogada'))
            )
        )

        if tem_contato or eh_nome_escritorio or tem_endereco_escritorio:
            fingerprint.append(ln)

    return fingerprint


def _remover_cabecalho_por_pagina(texto: str, fingerprint: list) -> str:
    """
    NÃ­vel 2: remove as linhas do fingerprint onde quer que apareÃ§am no texto.
    Usa correspondÃªncia exata (apÃ³s strip) para seguranÃ§a mÃ¡xima.
    """
    if not fingerprint:
        return texto
    fp_set = {l.strip() for l in fingerprint if l.strip()}
    linhas_out = []
    for linha in texto.splitlines():
        if linha.strip() in fp_set:
            continue
        linhas_out.append(linha)
    return '\n'.join(linhas_out)


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


def _strip_cabecalho_rodape(texto: str) -> str:
    """
    Ponto de entrada Ãºnico: aplica nÃ­vel 1 (artefatos PJe) e nÃ­vel 2
    (cabeÃ§alho do escritÃ³rio) ao texto extraÃ­do da petiÃ§Ã£o inicial.
    Seguro: nunca remove conteÃºdo do corpo jurÃ­dico.
    """
    if not texto:
        return texto
    texto = _remover_artefatos_pje(texto)
    fingerprint = _aprender_cabecalho(texto)
    if fingerprint:
        print(f'[TRIAGEM] cabecalho_fingerprint: {len(fingerprint)} linha(s) identificadas: '
              f'{fingerprint[:3]}')
        texto = _remover_cabecalho_por_pagina(texto, fingerprint)
    else:
        print('[TRIAGEM] cabecalho_fingerprint: nao identificado (texto inicia direto no conteudo juridico)')
    # Compactar linhas em branco excessivas geradas pela remoÃ§Ã£o
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


# ===== API â€” ExtraÃ§Ã£o sem DOM =====

def _extrair_id_processo_da_url(url: str):
    if not url:
        return None
    match = re.search(r'/processo/(\d+)(?:/|$)', url)
    return match.group(1) if match else None


def _eh_peticao_inicial(documento: dict) -> bool:
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    return 'peticao inicial' in tipo or 'peticao inicial' in titulo


def _eh_certidao_distribuicao(documento: dict) -> bool:
    """Aceita SOMENTE 'CertidÃ£o de DistribuiÃ§Ã£o' â€” exclui redistribuiÃ§Ã£o."""
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'certidao' in txt and 'distribuicao' in txt and 'redistribuicao' not in txt:
            return True
    return False


def _eh_procuracao(documento: dict) -> bool:
    """Verifica se documento Ã© ProcuraÃ§Ã£o."""
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'procuracao' in txt or 'procuraÃ§Ã£o' in txt:
            return True
    return False


def _eh_documento_identidade(documento: dict) -> bool:
    """Verifica se documento Ã© de Identidade (RG, CNH, Passport, etc).

    Verifica APENAS pelo tÃ­tulo â€” o campo 'tipo' Ã© genÃ©rico ('Documento')
    para todos os anexos na API do PJe e nÃ£o serve como discriminador.
    """
    titulo = _norm(documento.get('titulo') or '')
    # Palavras especÃ­ficas de documento de identidade pessoal
    # ExcluÃ­dos: 'documento' (genÃ©rico â€” tipo API), 'carteira' (Carteira de Trabalho/CTPS)
    palavras_chave = ['rg', 'cnh', 'identidade', 'cpf', 'passport', 'passaporte']
    return any(p in titulo for p in palavras_chave)


def _parsear_capa(texto: str) -> dict:
    dados = {
        'numero_processo': None, 'segredo_justica': None, 'medida_urgencia': None,
        'rito_declarado': None, 'valor_causa': None, 'classe_judicial': None,
        'reclamante_nome': None, 'reclamante_cpf': None,
        'reclamado_nome': None, 'reclamado_cnpj': None,
        'distribuido_em': None,
    }
    n = _norm(texto)

    m = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
    if m:
        dados['numero_processo'] = m.group(1)

    m = re.search(r'segredo de justic[aÃ§][:\s]+(sim|n[aÃ£]o)', n)
    if m:
        dados['segredo_justica'] = m.group(1).startswith('s')

    m = re.search(r'medida de urgencia[:\s]+(sim|n[aÃ£]o)', n)
    if m:
        dados['medida_urgencia'] = m.group(1).startswith('s')

    m = re.search(r'classe judicial[:\s]+(.+?)(?:\n|\(|\r)', texto, re.IGNORECASE)
    if m:
        dados['classe_judicial'] = m.group(1).strip()
        cl = _norm(dados['classe_judicial'])
        if 'sumarissimo' in cl:
            dados['rito_declarado'] = 'SUMARISSIMO'
        elif 'ordinario' in cl:
            dados['rito_declarado'] = 'ORDINARIO'

    # Tentativa 1: "Valor da Causa: R$ XX" na mesma linha
    m = re.search(r'valor da causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
    if m:
        try:
            dados['valor_causa'] = float(m.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            pass
    else:
        # Tentativa 2: tabela multi-coluna do PDF da certidÃ£o
        m2 = re.search(r'valor da causa', texto, re.IGNORECASE)
        if m2:
            trecho = texto[m2.end(): m2.end() + 400]
            mv = re.search(r'R\$\s*([\d\.,]+)', trecho)
            if mv:
                try:
                    dados['valor_causa'] = float(mv.group(1).replace('.', '').replace(',', '.'))
                except ValueError:
                    pass

    m = re.search(r'Partes[:\s]+(.+?)\s+-\s+([\d\.\-]+)\s+[Xx]\s+(.+?)\s+-\s+([\d\.\/\-]+)', texto)
    if m:
        dados['reclamante_nome'] = m.group(1).strip()
        dados['reclamante_cpf'] = re.sub(r'\D', '', m.group(2))
        dados['reclamado_nome'] = m.group(3).strip()
        dados['reclamado_cnpj'] = re.sub(r'\D', '', m.group(4))
    else:
        mr = re.search(r'RECLAMANTE\s*[\n\r]+\s*([A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘][^\n\r]+)', texto)
        if mr:
            dados['reclamante_nome'] = mr.group(1).strip()
        md = re.search(r'RECLAMAD[AO]\s*[\n\r]+\s*([A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘][^\n\r]+)', texto)
        if md:
            dados['reclamado_nome'] = md.group(1).strip()

    m = re.search(r'distribui[Ã­i]d[oa]\s+em\s+(\d{1,2}/\d{2}/\d{4})', texto, re.IGNORECASE)
    if m:
        dados['distribuido_em'] = m.group(1)

    return dados


def _pag_contexto(texto: str, posicao: int, janela: int = 400) -> str:
    pag = 1
    for mp in re.finditer(r'P[aÃ¡]gina\s+(\d+)', texto[:posicao], re.IGNORECASE):
        pag = int(mp.group(1))
    inicio = max(0, posicao - janela)
    fim = min(len(texto), posicao + janela)
    trecho = texto[inicio:fim].replace('\n', ' ').strip()
    return f'[pÃ¡g.{pag}] ...{trecho}...'


class _ErroAutenticacao401(Exception):
    """401 Unauthorized na API PJe â€” sessÃ£o expirada, necessÃ¡rio re-auth."""


def _extrair_texto_pdf_api(client: 'PjeApiClient', id_processo: str, id_doc: str) -> str:
    """Extrai texto de PDF via API PJe. 
    
    Faz: HTTP GET â†’ pdfplumber (nativo) â†’ OCR se necessÃ¡rio.
    OCR Ã© MUITO lento (pode levar segundos por pÃ¡gina).
    """
    import time as _t
    LIMIAR = 30
    tempo_inicio = _t.time()
    
    try:
        import pdfplumber
    except ImportError:
        return ''
    
    url = client._url(
        f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
    )
    try:
        resp = client.sess.get(url, timeout=60)
        if resp.status_code == 401:
            raise _ErroAutenticacao401(f'401 Unauthorized â€” doc {id_doc}')
        resp.raise_for_status()
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            return ''

        pdf_bytes = resp.content
        textos = []
        total = 0
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total = len(pdf.pages)
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)

        texto_nativo = '\n'.join(textos).strip()
        media = len(texto_nativo) / total if total else 0
        if media >= LIMIAR:
            return texto_nativo

        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            import shutil, pathlib
            _poppler_path = None
            if shutil.which('pdftoppm'):
                _poppler_path = str(pathlib.Path(shutil.which('pdftoppm')).parent)
            else:
                for _c in [r'D:\poppler\bin', r'C:\poppler\bin',
                           r'C:\Program Files\poppler\bin', r'C:\tools\poppler\bin']:
                    if pathlib.Path(_c).exists():
                        _poppler_path = _c
                        break
            imagens = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=_poppler_path)
            textos_ocr = [pytesseract.image_to_string(img, lang='por') for img in imagens]
            return '\n'.join(t for t in textos_ocr if t.strip())
        except ImportError:
            return texto_nativo
        except Exception as e:
            print(f'[TRIAGEM] OCR falhou ({id_doc}): {e}')
            return texto_nativo
    except _ErroAutenticacao401:
        raise
    except Exception as e:
        print(f'[TRIAGEM] ERRO PDF {id_doc}: {e}')
        return ''


def _listar_documentos_timeline(timeline: list) -> list:
    documentos = []
    for item in timeline or []:
        if not isinstance(item, dict):
            continue
        documentos.append(item)
        for anexo in item.get('anexos') or []:
            if isinstance(anexo, dict):
                documentos.append(anexo)
    return documentos

    # ===== B3 â€” AnÃ¡lise das Partes =====

    def _checar_partes(texto: str, capa_dados: dict) -> List[str]:
        linhas = []
        norm = _norm(texto)

        nome_rec = capa_dados.get('reclamante_nome') or ''
        cpf_rec = capa_dados.get('reclamante_cpf') or ''
        if nome_rec:
            sufixo = f' CPF={cpf_rec}' if cpf_rec else ''
            linhas.append(f"B3_PARTES: reclamante={nome_rec[:60]}{sufixo}")
        else:
            m = re.search(
                r'RECLAMANTE[:\s]+([A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘][A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘a-z\s\.]+?)'
                r'(?:\s*[-â€“]\s*|\s*CPF|\n)',
                texto[:3000])
            if m:
                linhas.append(f"B3_PARTES: reclamante={m.group(1).strip()[:60]}")
            else:
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
                        f"(nasc {m_nasc.group(3)}) - incluir MPT custos legis")
            except Exception:
                pass

        if re.search(r'\b(municipio|estado\s+de|uniao\s+federal|autarquia|fazenda\s+p[ue]blica)\b', norm):
            linhas.append(
                "B3_PARTES: ALERTA - PJDP no polo passivo (rito ordinario obrigatorio)")

        if not any('ALERTA' in l for l in linhas):
            linhas.append("B3_PARTES: OK")
        return linhas


if True:
    pass

    # ===== B4 â€” Segredo de JustiÃ§a =====

    def _checar_segredo(texto: str, capa_dados: dict) -> str:
        norm = _norm(texto)
        tem_pedido_no_texto = bool(re.search(r'segredo\s+de\s+justi[cÃ§]a|tramita[cÃ§][aÃ£]o\s+sigilosa', norm))
        segredo_na_capa = capa_dados.get('segredo_justica')
        if segredo_na_capa is True and not tem_pedido_no_texto:
            return "B4_SEGREDO: ALERTA - certidao indica segredo mas nao ha requerimento fundamentado na peticao"
        if tem_pedido_no_texto:
            fund = bool(re.search(r'art\.?\s*189', norm))
            suf = 'com art. 189 CPC' if fund else 'sem fundamentacao (art. 189 CPC ausente)'
            return f"B4_SEGREDO: ALERTA - pedido de segredo de justica {suf}"
        return "B4_SEGREDO: OK"


    # ===== B5 â€” Reclamadas / CNPJ =====

    def _checar_reclamadas(texto: str, capa_dados: dict) -> List[str]:
        linhas = []

        cnpj_capa = capa_dados.get('reclamado_cnpj') or ''
        if cnpj_capa and len(cnpj_capa) == 14:
            sufixo = cnpj_capa[8:12]
            tipo_cnpj = 'matriz' if sufixo == '0001' else f'filial/{sufixo}'
            fmt = f"{cnpj_capa[:2]}.{cnpj_capa[2:5]}.{cnpj_capa[5:8]}/{cnpj_capa[8:12]}-{cnpj_capa[12:]}"
            linhas.append(f"B5_RECLAMADAS: OK - CNPJ {fmt} ({tipo_cnpj}) [fonte: certidao]")
            return linhas

        cnpj_raws = []
        for m in re.finditer(
            r'CNPJ[\s]*(?:n[oÂºÂ°]\.?[\s]*)?([\d]{2}\.?[\d]{3}\.?[\d]{3}[\/\\][\d]{4}-?[\d]{2})',
            texto, re.IGNORECASE
        ):
            raw = re.sub(r'\D', '', m.group(1))
            cnpj_raws.append(raw)

        if not cnpj_raws:
            cpf_reclamante_raw = re.sub(r'\D', '', capa_dados.get('reclamante_cpf') or '')
            m_cpf = re.search(r'RECLAMAD[AO][^C\n]{0,200}CPF[:\s]*([\d\.\-]+)', texto, re.IGNORECASE | re.DOTALL)
            if m_cpf:
                cpf_found = re.sub(r'\D', '', m_cpf.group(1))[:11]
                if cpf_found and cpf_found == cpf_reclamante_raw:
                    linhas.append("B5_RECLAMADAS: ALERTA - nenhum CNPJ/CPF encontrado na peticao")
                else:
                    linhas.append(f"B5_RECLAMADAS: OK - reclamada pessoa fisica CPF={m_cpf.group(1)[:20]}")
            else:
                linhas.append("B5_RECLAMADAS: ALERTA - nenhum CNPJ/CPF encontrado na peticao")
            return linhas

        for cnpj in cnpj_raws:
            if len(cnpj) != 14:
                linhas.append(f"B5_RECLAMADAS: ALERTA - CNPJ {cnpj} invalido ({len(cnpj)} digitos)")
                continue
            sufixo = cnpj[8:12]
            tipo = 'matriz' if sufixo == '0001' else f'filial/{sufixo}'
            fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            linhas.append(f"B5_RECLAMADAS: OK - CNPJ {fmt} ({tipo})")

        filiais = [c for c in cnpj_raws if len(c) == 14 and c[8:12] != '0001']
        matrizes = {c[:8] for c in cnpj_raws if len(c) == 14 and c[8:12] == '0001'}
        for f in filiais:
            if f[:8] not in matrizes:
                linhas.append(f"B5_RECLAMADAS: ALERTA - filial {f[:8]}/... sem referencia a matriz")
                break
        return linhas
def _coletar_textos_processo(driver) -> Dict[str, Any]:
    print('[TRIAGEM] [_coletar] 1/6 Inicializando cliente API...')
    resultado: Dict[str, Any] = {
        'texto_inicial': '',
        'texto_capa': '',
        'capa_dados': {},
        'anexos': [],
        'id_processo': None,
        'associados_sistema': [],
        'erro': None,
    }
    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
        print('[TRIAGEM] [_coletar] âœ“ Cliente API inicializado')
    except Exception as e:
        resultado['erro'] = f'falha ao montar cliente autenticado: {e}'
        print(f'[TRIAGEM] [_coletar] âœ— ERRO ao montar cliente: {resultado["erro"]}')
        return resultado

    # Helper: tenta extrair PDF; em caso de 401 renova sessÃ£o UMA vez e retenta
    _reauth_done = [False]

    def _extrair_com_reauth(id_doc: str) -> str:
        nonlocal client
        try:
            return _extrair_texto_pdf_api(client, id_processo, id_doc)
        except _ErroAutenticacao401:
            if _reauth_done[0]:
                raise  # re-auth jÃ¡ tentado â€” propaga como erro crÃ­tico
            print(f'[TRIAGEM] 401 doc {id_doc} â€” renovando sessÃ£o (tentativa Ãºnica)...')
            _reauth_done[0] = True
            try:
                s2, h2 = session_from_driver(driver, grau=1)
                client = PjeApiClient(s2, h2, grau=1)
            except Exception as re_err:
                raise _ErroAutenticacao401(f'falha ao renovar sessao: {re_err}') from re_err
            return _extrair_texto_pdf_api(client, id_processo, id_doc)

    id_processo = _extrair_id_processo_da_url(driver.current_url)
    if not id_processo:
        resultado['erro'] = f'id_processo nao encontrado na URL: {driver.current_url}'
        print(f'[TRIAGEM] [_coletar] âœ— ERRO: {resultado["erro"]}')
        return resultado
    
    print(f'[TRIAGEM] [_coletar] 2/6 ID processo extraÃ­do: {id_processo}')
    resultado['id_processo'] = id_processo

    # Buscar partes ANTES de ler qualquer PDF â€” dados do endpoint sÃ£o definitivos
    _partes_raw: dict = {}
    _partes_endereco: dict = {}
    try:
        _partes_raw = client.partes(id_processo) or {}
        _qtd_a = len(_partes_raw.get('ATIVO') or [])
        _qtd_p = len(_partes_raw.get('PASSIVO') or [])
        print(f'[TRIAGEM] partes_api: {_qtd_a} ativo(s), {_qtd_p} passivo(s)')

        url_endereco = client._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes?retornaEndereco=true")
        r_endereco = client.sess.get(url_endereco, timeout=15)
        if r_endereco.ok:
            _partes_endereco = r_endereco.json()
            print(f'[TRIAGEM] partes+endereco OK - {len(_partes_endereco.get("PASSIVO") or [])} passivo(s)')
    except Exception as _e_partes:
        print(f'[TRIAGEM] partes_api: falha ({_e_partes})')

    # Buscar processos associados (prevenÃ§Ã£o detectada pelo sistema)
    try:
        _associados = client.associados(id_processo) or []
        resultado['associados_sistema'] = _associados
        if _associados:
            print(f'[TRIAGEM] associados_sistema: {len(_associados)} associado(s) encontrado(s)')
        else:
            print('[TRIAGEM] associados_sistema: nenhum')
    except Exception as _e_assoc:
        print(f'[TRIAGEM] associados_sistema: falha ({_e_assoc})')
        resultado['associados_sistema'] = []

    # Buscar timeline com timeout para evitar travamentos
    timeline = None
    timeline_erro = None
    
    def _buscar_timeline():
        nonlocal timeline, timeline_erro
        try:
            print(f'[TRIAGEM] Iniciando busca de timeline com timeout (id={id_processo})')
            timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
            print(f'[TRIAGEM] Timeline recebida com sucesso')
        except Exception as e:
            timeline_erro = f'erro ao buscar timeline: {e}'
            print(f'[TRIAGEM] ERRO ao buscar timeline: {timeline_erro}')
    
    thread = threading.Thread(target=_buscar_timeline, daemon=False)
    thread.start()
    thread.join(timeout=30)  # Timeout de 30 segundos
    
    if thread.is_alive():
        # Thread ainda rodando apÃ³s timeout
        print('[TRIAGEM] âš ï¸ TIMEOUT ao buscar timeline â€” thread ainda ativa apÃ³s 30s')
        resultado['erro'] = 'timeout ao buscar timeline (>30s)'
        return resultado
    
    if timeline_erro:
        resultado['erro'] = timeline_erro
        return resultado

    if not timeline:
        resultado['erro'] = 'timeline vazia ou indisponivel'
        print(f'[TRIAGEM] [_coletar] âœ— ERRO: {resultado["erro"]}')
        return resultado

    print('[TRIAGEM] [_coletar] 3/6 Timeline obtida, processando documentos...')
    documentos = _listar_documentos_timeline(timeline)
    print(f'[TRIAGEM] [_coletar] Documentos processados: {len(documentos) or 0} itens')
    
    peticao = next((d for d in documentos if _eh_peticao_inicial(d)), None)
    if not peticao:
        resultado['erro'] = 'peticao inicial nao localizada na timeline'
        print(f'[TRIAGEM] [_coletar] âœ— ERRO: {resultado["erro"]}')
        return resultado
    
    print('[TRIAGEM] [_coletar] 4/6 PetiÃ§Ã£o inicial localizada, extraindo texto...')

    id_inicial = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
    if not id_inicial:
        resultado['erro'] = 'id do documento da peticao inicial nao disponivel'
        print(f'[TRIAGEM] [_coletar] âœ— ERRO: {resultado["erro"]}')
        return resultado

    try:
        resultado['texto_inicial'] = _extrair_com_reauth(id_inicial)
    except _ErroAutenticacao401 as e:
        resultado['erro'] = f'ERRO_CRITICO_401: peticao inicial â€” {e}'
        resultado['erro_critico'] = True
        print(f'[TRIAGEM] ðŸ›‘ ERRO CRÃTICO 401 â€” {resultado["erro"]}')
        return resultado
    chars_bruto = len(resultado['texto_inicial'])
    resultado['texto_inicial'] = _strip_cabecalho_rodape(resultado['texto_inicial'])
    chars_limpo = len(resultado['texto_inicial'])
    print(f'[TRIAGEM] [_coletar] âœ“ Texto da petiÃ§Ã£o extraÃ­do: '
          f'{chars_bruto} chars bruto â†’ {chars_limpo} chars apÃ³s strip cabecalho/rodape '
          f'({chars_bruto - chars_limpo} removidos)')

    anexos_raw = peticao.get('anexos') or []
    if not anexos_raw:
        anexos_raw = [d for d in documentos if d.get('idDocumentoPai') == peticao.get('id')]

    # Filtrar apenas anexos essenciais: ProcuraÃ§Ã£o + Documento de Identidade
    procuracoes = [a for a in anexos_raw if _eh_procuracao(a)]
    docs_identidade = [a for a in anexos_raw if _eh_documento_identidade(a)]
    print(f'[TRIAGEM] anexos: procuracao={len(procuracoes)} doc_identidade={len(docs_identidade)} (total={len(anexos_raw)})')

    anexos_extraidos = []
    for anx in procuracoes:
        id_anx = str(anx.get('id') or anx.get('idUnicoDocumento') or '')
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        try:
            texto_anx = _extrair_com_reauth(id_anx) if id_anx else ''
        except _ErroAutenticacao401 as e:
            resultado['erro'] = f'ERRO_CRITICO_401: procuracao {id_anx} â€” {e}'
            resultado['erro_critico'] = True
            print(f'[TRIAGEM] ðŸ›‘ ERRO CRÃTICO 401 â€” {resultado["erro"]}')
            return resultado
        print(f'[TRIAGEM] procuracao extraida: "{titulo_anx}" {len(texto_anx)} chars')
        anexos_extraidos.append({'titulo': titulo_anx, 'tipo': (anx.get('tipo') or '').strip(), 'texto': texto_anx})
    for anx in docs_identidade:
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        print(f'[TRIAGEM] doc_identidade: "{titulo_anx}" (identificado, sem extracao)')
        anexos_extraidos.append({'titulo': titulo_anx, 'tipo': (anx.get('tipo') or '').strip(), 'texto': ''})
    resultado['anexos'] = anexos_extraidos

    # CertidÃ£o de distribuiÃ§Ã£o: mesma data da petiÃ§Ã£o inicial (campo 'data' da timeline)
    _data_pi = (peticao.get('data') or '')[:10]  # 'YYYY-MM-DD'
    candidatas = [d for d in documentos if _eh_certidao_distribuicao(d)]
    certidao = None
    if candidatas:
        # Preferir a que tem mesma data da PI; fallback: primeira candidata
        certidao = next(
            (d for d in candidatas if (d.get('data') or '')[:10] == _data_pi),
            candidatas[0]
        )
    texto_capa = ''
    if certidao:
        id_cert = str(certidao.get('id') or certidao.get('idUnicoDocumento') or '')
        titulo_cert = (certidao.get('titulo') or certidao.get('tipo') or '(sem titulo)').strip()
        print(f'[TRIAGEM] certidao_distribuicao: localizada id={id_cert} titulo="{titulo_cert}"')
        if id_cert:
            try:
                texto_capa = _extrair_com_reauth(id_cert)
            except _ErroAutenticacao401 as e:
                resultado['erro'] = f'ERRO_CRITICO_401: certidao {id_cert} â€” {e}'
                resultado['erro_critico'] = True
                print(f'[TRIAGEM] ðŸ›‘ ERRO CRÃTICO 401 â€” {resultado["erro"]}')
                return resultado
            if texto_capa:
                print(f'[TRIAGEM] certidao_distribuicao: extracao OK chars={len(texto_capa)}')
            else:
                print('[TRIAGEM] certidao_distribuicao: ERRO - texto extraido vazio '
                      '(PDF sem texto nativo e OCR indisponivel ou falhou)')
        else:
            print('[TRIAGEM] certidao_distribuicao: ERRO - id do documento nao disponivel na timeline')
    else:
        nomes = [(_norm(d.get('titulo') or d.get('tipo') or '')) for d in documentos[:12]]
        print(f'[TRIAGEM] certidao_distribuicao: NAO LOCALIZADA - '
              f'docs disponiveis (ate 12): {nomes}')

    resultado['texto_capa'] = texto_capa
    if texto_capa:
        resultado['capa_dados'] = _parsear_capa(texto_capa)
    else:
        resultado['capa_dados'] = {}
        print('[TRIAGEM] capa_dados: nao extraidos (certidao ausente ou vazia) - '
              'B13/rito indisponivel')

    # Enriquecer capa_dados com partes definitivas da API (sobrescreve certidÃ£o quando disponÃ­vel)
    if _partes_raw:
        ativos = _partes_raw.get('ATIVO') or []
        passivos = _partes_raw.get('PASSIVO') or []
        if ativos:
            doc_ativo = re.sub(r'\D', '', ativos[0].get('documento') or '')
            resultado['capa_dados']['reclamante_nome'] = ativos[0].get('nome', '').strip()
            if len(doc_ativo) == 11:
                resultado['capa_dados']['reclamante_cpf'] = doc_ativo
        if passivos:
            reclamados_lista = []
            reclamadas_sem_endereco = []
            reclamadas_com_dom_elet = 0
            for _p in passivos:
                _doc = re.sub(r'\D', '', _p.get('documento') or '')
                reclamados_lista.append({'nome': _p.get('nome', '').strip(), 'cpfcnpj': _doc})

            for _parte in (_partes_endereco.get('PASSIVO') or []):
                nome_parte = _parte.get('nome', '').strip()
                if _parte.get('enderecoDesconhecido', False):
                    reclamadas_sem_endereco.append(nome_parte)

                # IdÃªntico a def_citacao em aud.py: tenta endpoint dedicado primeiro
                id_parte_pj = str(
                    _parte.get('idPessoa') or _parte.get('id') or
                    _parte.get('idParticipante') or _parte.get('idParte') or '')
                dom_via_api = client.domicilio_eletronico(id_parte_pj) if id_parte_pj else None
                dom_flag_raw = _parte.get('domicilioEletronico') or _parte.get('possuiDomicilioEletronico')
                tem_domicilio = dom_via_api if dom_via_api is not None else (dom_flag_raw is True)
                if tem_domicilio:
                    reclamadas_com_dom_elet += 1

                endereco = _parte.get('endereco') or {}
                cep_raw = endereco.get('nroCep') or ''
                cep = re.sub(r'[^\d]', '', cep_raw) if cep_raw else None
                endereco_desc = _formatar_endereco_parte(endereco)
                _dom_status = 'SIM' if tem_domicilio else ('NAO' if dom_via_api is not None else f'flag={dom_flag_raw}')
                print(f'[TRIAGEM] passivo: {nome_parte} | domicilio={_dom_status} | cep={cep or "(sem)"} | end={endereco_desc[:60] or "(sem)"}')
                if cep and len(cep) == 8:
                    _doc_parte = re.sub(r'\D', '', _parte.get('documento') or '')
                    for item in reclamados_lista:
                        if item.get('cpfcnpj') == _doc_parte or item.get('nome') == nome_parte:
                            item['cep'] = cep
                            if endereco_desc:
                                item['endereco'] = endereco_desc
                            break

            resultado['capa_dados']['reclamados'] = reclamados_lista
            resultado['capa_dados']['reclamadas_sem_endereco'] = reclamadas_sem_endereco
            resultado['capa_dados']['reclamadas_com_dom_elet'] = reclamadas_com_dom_elet
            # Compat legacy: primeiro rÃ©u
            _prim = reclamados_lista[0]
            resultado['capa_dados']['reclamado_nome'] = _prim['nome']
            if len(_prim['cpfcnpj']) == 14:
                resultado['capa_dados']['reclamado_cnpj'] = _prim['cpfcnpj']
            elif len(_prim['cpfcnpj']) == 11:
                resultado['capa_dados']['reclamado_cpf'] = _prim['cpfcnpj']

    # Valor da causa via API (mais confiÃ¡vel que parsear PDF)
    try:
        proc_dados = client.processo_por_id(id_processo) or {}
        juizo_digital = proc_dados.get('juizoDigital')
        if isinstance(juizo_digital, str):
            juizo_digital = juizo_digital.lower() == 'true'
        elif juizo_digital is not None:
            juizo_digital = bool(juizo_digital)
        resultado['capa_dados']['juizo_digital'] = juizo_digital
        valor_api = (proc_dados.get('valorCausa')
                     or proc_dados.get('valorDaCausa')
                     or proc_dados.get('valor'))
        if valor_api is not None:
            try:
                resultado['capa_dados']['valor_causa'] = float(valor_api)
            except (TypeError, ValueError):
                pass
    except Exception as e_api:
        print(f'[TRIAGEM] valor_causa API: falha ({e_api})')

    cd = resultado['capa_dados']
    print(f'[TRIAGEM] capa_dados: valor_causa={cd.get("valor_causa")} '
            f'rito={cd.get("rito_declarado")} juizo_digital={cd.get("juizo_digital")} '
            f'distribuido_em={cd.get("distribuido_em")}')
    print('[TRIAGEM] [_coletar] 6/6 âœ“ Coleta de textos concluÃ­da com sucesso')
    return resultado


# ===== B1 â€” ProcuraÃ§Ã£o e Documento de Identidade =====

_TERMOS_PROC_TITULO  = ['procuracao', 'mandato']
_TERMOS_ID_TITULO    = ['rg', 'cnh', 'documento de identidade', 'identidade', 'doc identidade']
_TERMOS_PROC_BODY    = ['outorgo', 'poderes', 'por este instrumento particular', 'constituir como',
                        'procuracao', 'mandato', 'outorgante', 'outorgado']
_TERMOS_ID_BODY      = ['registro geral', 'carteira de identidade', 'carteira nacional de habilitacao',
                        'secretaria de seguranca publica', 'documento de identidade',
                        'data de nascimento', 'filiacao', 'naturalidade']

def _checar_procuracao_e_identidade(
    anexos: List[Dict[str, Any]], nome_reclamante: str = ''
) -> str:
    proc_via = None   # 'titulo' | 'conteudo:<titulo_anexo>'
    id_via   = None

    for anx in anexos:
        tref  = _norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
        tbody = _norm(anx.get('texto') or '')
        tnome = (anx.get('titulo') or anx.get('tipo') or '').strip()

        # ProcuraÃ§Ã£o
        if proc_via is None:
            if any(t in tref for t in _TERMOS_PROC_TITULO):
                proc_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_PROC_BODY):
                proc_via = f'conteudo:"{tnome or "(sem titulo)"}"'

        # Documento de identidade
        if id_via is None:
            if any(t in tref for t in _TERMOS_ID_TITULO):
                id_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_ID_BODY):
                id_via = f'conteudo:"{tnome or "(sem titulo)"}"'

    # Cross-check: nome do reclamante presente na procuraÃ§Ã£o
    extra_proc = ''
    if proc_via and nome_reclamante:
        nome_norm = _norm(nome_reclamante)
        for anx in anexos:
            tref  = _norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
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
    tem_id   = id_via   is not None

    if tem_proc and tem_id:
        return (f'B1_DOCS: OK - procuracao ({proc_via}){extra_proc} '
                f'e doc identidade ({id_via}) presentes')
    if not tem_proc and not tem_id:
        return 'B1_DOCS: ALERTA - faltam procuracao e copia de documento de identidade em anexos separados'
    if not tem_proc:
        return f'B1_DOCS: ALERTA - falta procuracao em anexo (doc identidade: {id_via})'
    return f'B1_DOCS: ALERTA - falta copia de documento de identidade em anexo (procuracao: {proc_via}{extra_proc})'


# ===== B2 â€” CEP / CompetÃªncia Territorial =====

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
    # reclamado pessoa fÃ­sica tambÃ©m pode indicar o endereÃ§o relevante
    'reclamad', 'em face', 'contra o reclamado', 'contra a reclamada',
    'cpf', 'pessoa fisica', 'com endereco', 'endereco a'
]


def _cep_tag(ctx_norm: str, palavras_reclamada: list) -> int:
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


def _checar_cep(texto: str, capa_dados: dict) -> str:
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

    # NOVA LÃ“GICA: Se o CEP da reclamada (API) jÃ¡ for da competÃªncia, retorna imediatamente
    if ceps_api:
        cep_raw = ceps_api[0]
        if len(cep_raw) == 8 and cep_raw.isdigit():
            cep_num = int(cep_raw)
            cep_fmt = f"{cep_raw[:2]}.{cep_raw[2:5]}-{cep_raw[5:]}"
            label = 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)'
            for lo, hi in INTERVALOS_CEP_ZONA_SUL:
                if lo <= cep_num <= hi:
                    return (f"B2_CEP: OK - {cep_fmt} ({cep_num}) "
                            f"no intervalo {lo}-{hi} Zona Sul [{label}]")
    # SÃ³ aceita fallback para CEP da reclamada se NÃƒO houver nenhum CEP contextual de prestaÃ§Ã£o de serviÃ§os ou competÃªncia territorial
    candidatos = [c for c in candidatos if c[3] == 0 or c[1] == 0]
    if not candidatos:
        norm_texto = _norm(texto)
        termos_estritos = _CEP_TERMOS_TERRITORIAL + _CEP_TERMOS_PRESTACAO
        if any(t in norm_texto for t in termos_estritos):
            return "B2_CEP: ALERTA - nenhum CEP de prestacao de servicos identificado no contexto relevante (CEP da reclamada ignorado por regra)"
        # SÃ³ aqui faz fallback para CEP da reclamada (fora da faixa)
        if ceps_api:
            cep_raw = ceps_api[0]
            if len(cep_raw) == 8 and cep_raw.isdigit():
                cep_num = int(cep_raw)
                cep_fmt = f"{cep_raw[:2]}.{cep_raw[2:5]}-{cep_raw[5:]}"
                label = 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)'
                return (f"B2_CEP: ALERTA - Incompetencia Territorial - "
                        f"CEP {cep_fmt} ({cep_num}) fora dos intervalos Zona Sul [{label}]")
        return "B2_CEP: ALERTA - nenhum CEP de prestacao de servicos ou reclamada identificado (CEP do reclamante ignorado por regra)"

    candidatos.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
    best_tag, _, _, _, _, cep_num, cep_fmt = candidatos[0]

    _TAG_LABEL = {
        _CEP_TAG_TERRITORIAL: 'competencia territorial (art.651 CLT)',
        _CEP_TAG_PRESTACAO: 'ultimo local de prestacao de servicos (art.651 CLT)',
        _CEP_TAG_RECLAMADA: 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)',
        _CEP_TAG_GENERICO: 'generico',
    }
    label = _TAG_LABEL[best_tag]

    # Detectar se petiÃ§Ã£o menciona competÃªncia territorial / local de prestaÃ§Ã£o
    # mesmo que o CEP nÃ£o esteja nesse trecho
    _TERMOS_TERRIT = _CEP_TERMOS_TERRITORIAL + _CEP_TERMOS_PRESTACAO
    norm_texto = _norm(texto)
    termos_presentes = [t for t in _TERMOS_TERRIT if t in norm_texto]
    sufixo_territ = ''
    if termos_presentes and best_tag not in (_CEP_TAG_TERRITORIAL, _CEP_TAG_PRESTACAO):
        sufixo_territ = (f' | NOTA: peticao menciona termos de competencia territorial '
                         f'({termos_presentes[0]}) mas CEP nao foi localizado nesse contexto - '
                         f'verificar endereco indicado na secao de competencia/prestacao')

    for lo, hi in INTERVALOS_CEP_ZONA_SUL:
        if lo <= cep_num <= hi:
            return (f"B2_CEP: OK - {cep_fmt} ({cep_num}) "
                    f"no intervalo {lo}-{hi} Zona Sul [{label}]{sufixo_territ}")
    return (f"B2_CEP: ALERTA - Incompetencia Territorial - "
            f"CEP {cep_fmt} ({cep_num}) fora dos intervalos Zona Sul [{label}]{sufixo_territ}")


# ===== B3 â€” AnÃ¡lise das Partes =====

def _checar_partes(texto: str, capa_dados: dict) -> List[str]:
    linhas = []
    norm = _norm(texto)
    corte_preliminarmente = norm.find('preliminarmente')
    contexto_partes = norm[:corte_preliminarmente] if corte_preliminarmente != -1 else norm[:2600]

    nome_rec = capa_dados.get('reclamante_nome') or ''
    cpf_rec = capa_dados.get('reclamante_cpf') or ''
    # rec_info Ã© embutido na linha OK ao final â€” nÃ£o gera item separado
    if nome_rec:
        sufixo = f' CPF={cpf_rec}' if cpf_rec else ''
        rec_info = f' - reclamante={nome_rec[:60]}{sufixo}'
    else:
        m = re.search(
            r'RECLAMANTE[:\s]+([A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘][A-ZÃÃ€Ã‚ÃƒÃ‰ÃˆÃŠÃÃÃ“Ã”Ã•Ã–ÃšÃ‡Ã‘a-z\s\.]+?)'
            r'(?:\s*[-â€“]\s*|\s*CPF|\n)',
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
                    f"(nasc {m_nasc.group(3)}) - incluir MPT custos legis")
        except Exception:
            pass

    # PJDP: excluir falsos positivos de campos de endereÃ§o ("MunicÃ­pio:", "Estado:") e
    # contexto "pessoa jurÃ­dica de/do direito privado"
    _RE_PJDP = re.compile(
        r'\b(municipio|prefeitura|uniao\s+federal|autarquia|fazenda\s+p[ue]blica|estado\b(?!\s+de\b))\b')
    _RE_ADDR_LABEL = re.compile(r'municipio\s*:', re.IGNORECASE)
    _RE_ESTADO_LABEL = re.compile(r'estado\s*:', re.IGNORECASE)
    _RE_PRIVADO = re.compile(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado')

    pjdp_encontrado = False
    for m_pjdp in _RE_PJDP.finditer(contexto_partes):
        trecho = contexto_partes[max(0, m_pjdp.start() - 80): m_pjdp.end() + 20]
        # Descartar se Ã© label de endereÃ§o ("MunicÃ­pio: SÃ£o Paulo", "Estado: SP")
        if _RE_ADDR_LABEL.search(trecho) or _RE_ESTADO_LABEL.search(trecho):
            continue
        # Descartar se contexto prÃ³ximo diz "pessoa jurÃ­dica de direito privado"
        trecho_amplo = contexto_partes[max(0, m_pjdp.start() - 200): m_pjdp.end() + 50]
        if _RE_PRIVADO.search(trecho_amplo):
            continue
        pjdp_encontrado = True
        linhas.append(
            f"B3_PARTES: ALERTA - PJDP no polo passivo (rito ordinario obrigatorio); "
            f"gatilho detectado: {m_pjdp.group(1)}")
        break

    if not pjdp_encontrado:
        pass  # sem alerta PJDP

    if not any('ALERTA' in l for l in linhas):
        linhas.append(f"B3_PARTES: OK{rec_info}")
    return linhas


# ===== B4 â€” Segredo de JustiÃ§a =====

def _checar_segredo(texto: str, capa_dados: dict) -> str:
    norm = _norm(texto)
    tem_pedido_no_texto = bool(re.search(r'segredo\s+de\s+justi[cÃ§]a|tramita[cÃ§][aÃ£]o\s+sigilosa', norm))
    segredo_na_capa = capa_dados.get('segredo_justica')
    if segredo_na_capa is True and not tem_pedido_no_texto:
        return "B4_SEGREDO: ALERTA - certidÃ£o indica segredo mas nÃ£o hÃ¡ requerimento fundamentado na petiÃ§Ã£o"
    if tem_pedido_no_texto:
        fund = bool(re.search(r'art\.?\s*189', norm))
        suf = 'com art. 189 CPC' if fund else 'sem fundamentacao (art. 189 CPC ausente)'
        return f"B4_SEGREDO: ALERTA - pedido de segredo de justica {suf}"
    return "B4_SEGREDO: OK"


# ===== B5 â€” Reclamadas / CNPJ =====

_RE_CNPJ_NUM = re.compile(r'\b(?:\d{2}(?:[\.\s]?\d{3}){2}\/\d{4}-?\d{2}|\d{14})\b', re.IGNORECASE)
_RE_CPF_NUM = re.compile(r'\b(?:\d{3}(?:[\.\s]?\d{3}){2}-?\d{2}|\d{11})\b', re.IGNORECASE)

_CNPJ_CONTEXTOS = (
    'cnpj', 'inscrita no cnpj', 'inscrito no cnpj', 'cnpj sob', 'cnpj nÂº', 'cnpj no',
    'reclamad', 'pessoa juridica', 'pessoa juridica de direito privado',
    'pessoa juridica de direito publico', 'empresa', 'sociedade', 'matriz', 'filial', 'sede',
)

_CPF_CONTEXTOS = (
    'cpf', 'reclamad', 'pessoa fisica', 'pessoa natural',
    # 'reclamante' removido â€” evita capturar CPF do prÃ³prio reclamante
)


def _extrair_numeros_contextuais(texto: str, numero_re: re.Pattern, contextos: tuple[str, ...]) -> List[str]:
    """Extrai nÃºmeros apenas quando aparecem em blocos com contexto compatÃ­vel."""
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


def _checar_reclamadas(texto: str, capa_dados: dict) -> List[str]:
    linhas = []
    reclamados_api = capa_dados.get('reclamados') or []

    sem_endereco = capa_dados.get('reclamadas_sem_endereco') or []
    if sem_endereco:
        linhas.append(
            f'B5_RECLAMADAS ALERTA - {len(sem_endereco)} reclamada(s) SEM ENDEREÃ‡O: '
            f'{", ".join(sem_endereco[:3])}'
        )

    com_dom = capa_dados.get('reclamadas_com_dom_elet', 0) or 0
    total_reclamadas = len(reclamados_api)
    if total_reclamadas > 0:
        if com_dom > 0:
            linhas.append(f'B5_RECLAMADAS OK - {com_dom}/{total_reclamadas} reclamada(s) com DOMICÃLIO ELETRÃ”NICO')
        else:
            linhas.append('B5_RECLAMADAS ALERTA - NENHUMA reclamada com domicÃ­lio eletrÃ´nico habilitado')

    if not reclamados_api:
        linhas.append("B5_RECLAMADAS: ALERTA - dados de partes nao disponiveis via API")
        return linhas

    for r in reclamados_api:
        nome = r.get('nome', '')
        doc = r.get('cpfcnpj', '')
        cep = r.get('cep')
        endereco = r.get('endereco', '')
        info = []
        if cep:
            info.append(f'CEP={cep}')
        if endereco:
            info.append(f'end={endereco}')
        sufixo_info = f' ({"; ".join(info)})' if info else ''

        if len(doc) == 14:
            sufixo = doc[8:12]
            tipo = 'matriz' if sufixo == '0001' else f'filial/{sufixo}'
            fmt = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
            linhas.append(f"B5_RECLAMADAS: OK - {nome} CNPJ {fmt} ({tipo}){sufixo_info}")
        elif len(doc) == 11:
            linhas.append(f"B5_RECLAMADAS: OK - {nome} pessoa fisica CPF={doc}{sufixo_info}")
        else:
            linhas.append(f"B5_RECLAMADAS: ALERTA - {nome} sem CPF/CNPJ valido na API{sufixo_info}")

    cnpjs = [r['cpfcnpj'] for r in reclamados_api if len(r.get('cpfcnpj', '')) == 14]
    filiais = [c for c in cnpjs if c[8:12] != '0001']
    matrizes = {c[:8] for c in cnpjs if c[8:12] == '0001'}
    for f in filiais:
        if f[:8] not in matrizes:
            linhas.append(f"B5_RECLAMADAS: ALERTA - filial {f[:8]}/... sem referencia a matriz")
            break
    return linhas


# ===== B6 â€” Tutelas ProvisÃ³rias =====

def _checar_tutela(texto: str, capa_dados: dict) -> str:
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


# ===== B6 â€” Tutelas ProvisÃ³rias =====

def _checar_tutela(texto: str, capa_dados: dict) -> str:
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
        return "B6_TUTELA: ALERTA - certidÃ£o indica medida de urgÃªncia mas termo nÃ£o localizado nos pedidos"
    return "B6_TUTELA: OK"


# ===== B7 â€” JuÃ­zo 100% Digital =====

def _checar_digital(texto: str, capa_dados: dict) -> str:
    norm = _norm(texto)
    pedido_digital = bool(re.search(
        r'(ju[iÃ­]zo\s*100%?\s*digital|ades[aÃ£]o\s+ao\s+ju[iÃ­]zo\s*100%?\s*digital|'
        r'manifesta[cÃ§][aÃ£]o\s+de\s+ades[aÃ£]o\s+ao\s+ju[iÃ­]zo\s*100%?\s*digital|'
        r'requer(?:e|ido)?\s+o\s+ju[iÃ­]zo\s*100%?\s*digital)', norm))
    if not pedido_digital:
        return "B7_DIGITAL: OK - sem pedido expresso de Juizo 100% Digital na peticao"

    processo_digital = capa_dados.get('juizo_digital')
    if processo_digital is True:
        return "B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado e processo ja marcado na API"
    if processo_digital is False:
        return "B7_DIGITAL: ALERTA - pedido expresso de Juizo 100% Digital identificado, mas processo nao marcado na API"
    return "B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado, mas marcaÃ§Ã£o do processo nao confirmada na API"


# ===== B8 â€” Pedidos Liquidados =====

def _checar_pedidos_liquidados(texto: str) -> str:
    # Linhas que indicam "valor da causa" â€” nÃ£o sÃ£o pedidos liquidados
    _RE_SKIP_PEDIDO = re.compile(
        r'atribu[iÃ­]|n[aÃ£]o inferior|valor da causa|valor atribu[iÃ­]do|'
        r'n[aÃ£]o deve ser utiliz|fator limitador|estimativa|base de calculo',
        re.IGNORECASE
    )

    # CabeÃ§alhos de verbas rescisÃ³rias (linhas curtas sem R$, com nome de verba)
    _RE_VERBA_HEADER = re.compile(
        r'\b(saldo.sal[aÃ¡]rio|aviso\s*pr[eÃ©]vio|f[eÃ©]rias|fgts|'
        r'multa\s*(art|do)?\s*(art\.?\s*4[67][67]|dos\s*40)?|dano\s*moral|gorjeta|'
        r'adicional|13[Â°oÂº]?\s*sal[aÃ¡]rio|d[eÃ©]cimo|hora\s*extra|'
        r'indeniza[cÃ§][aÃ£]o|seguro[- ]desemprego|libera[cÃ§][aÃ£]o)\b',
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
            ctx = ls[-80:] if len(ls) > 80 else ls
            prefixo = f'[{secao}] ' if secao else ''
            itens.append(f"  {prefixo}{ctx}")

    out = []
    if not itens:
        out.append("B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados")
    else:
        out.append(f"B8_PEDIDOS: OK - {len(itens)} pedido(s) com valor:")
        out.extend(itens[-3:])
    return '\n'.join(out)


# ===== B9 â€” Pessoas FÃ­sicas no Polo Passivo =====

def _checar_pessoa_fisica(texto: str, capa_dados: dict = None) -> str:
    """B9: verifica pessoa fÃ­sica no polo passivo via dados da API."""
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


# ===== B10 â€” LitispendÃªncia / Coisa Julgada / PrevenÃ§Ã£o =====

def _checar_litispendencia(texto: str, associados_sistema: list = None) -> str:
    # Termos tÃ­picos de contexto jurisprudencial/ementa/acÃ³rdÃ£o
    termos_juris = [
        "acordao", "ementa", "jurisprudencia", "precedente", "relator", "turma",
        "tst", "stj", "stf", "dejt", "sumula", "oj", "rot", "rorsum", "rr", "airr"
    ]
    padrao_processo = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos_reais = []
    for linha in texto.split('\n'):
        norm_linha = _norm(linha)
        # Ignora linhas com termos tÃ­picos de citaÃ§Ã£o jurisprudencial
        if any(t in norm_linha for t in termos_juris):
            continue
        matches = padrao_processo.findall(linha)
        if matches:
            processos_reais.extend(matches)
    unicos_peticao = list(dict.fromkeys(processos_reais))

    # Processos associados detectados pelo sistema via API
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

    # 1) Processos detectados pelo sistema â€” sempre ALERTA
    for num in nums_sistema:
        if num in unicos_peticao:
            partes_alerta.append(
                f"PrevenÃ§Ã£o detectada no sistema - processo {num} (tambÃ©m mencionado na petiÃ§Ã£o)"
            )
        else:
            partes_alerta.append(f"PrevenÃ§Ã£o detectada no sistema - processo {num}")

    # 2) Processos mencionados na petiÃ§Ã£o
    apenas_peticao = [n for n in unicos_peticao if n not in nums_sistema]
    if nums_sistema:
        # Com dados do sistema, relatar qualquer nÃºmero extra na petiÃ§Ã£o nÃ£o coberto pelo sistema
        if apenas_peticao:
            outros = ', '.join(apenas_peticao[:4])
            partes_alerta.append(
                f"menÃ§Ã£o a outros processos na petiÃ§Ã£o ({outros}) "
                f"- verificar litispendÃªncia/prevenÃ§Ã£o/coisa julgada"
            )
    elif len(unicos_peticao) > 1:
        # LÃ³gica original: >1 nÃºmero na petiÃ§Ã£o (primeiro pode ser o prÃ³prio nÃºmero do processo)
        outros = ', '.join(unicos_peticao[1:4])
        partes_alerta.append(
            f"menÃ§Ã£o a outros processos na petiÃ§Ã£o ({outros}) "
            f"- verificar litispendÃªncia/prevenÃ§Ã£o/coisa julgada"
        )

    # 3) Palavras-chave quando nÃ£o hÃ¡ nenhum nÃºmero identificado
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


# ===== B11 â€” Responsabilidade SubsidiÃ¡ria/SolidÃ¡ria =====

# PadrÃ£o amplo: "1Âª RECLAMADA â€”", "1Âº RECLAMADA â€”", "RECLAMADA:", "PRIMEIRA RECLAMADA"
_RE_RECLAMADA_HEADER = re.compile(
    r'(?:\d+[ÂºoÂ°]?\.?\s*|primeira\s+|segunda\s+|terceira\s+|quarta\s+)RECLAMAD[AO]\b'
    r'|RECLAMAD[AO]\s*[:\â€”â€“]',
    re.IGNORECASE
)

def _checar_responsabilidade(texto: str, capa_dados: dict = None) -> List[str]:
    # Usa contagem da API se disponÃ­vel; fallback para regex no texto
    reclamados_api = (capa_dados or {}).get('reclamados') or []
    if reclamados_api:
        n_rec = len(reclamados_api)
    else:
        capa = texto[:4000]
        n_rec = len(_RE_RECLAMADA_HEADER.findall(capa))

    norm = _norm(texto)

    # Detecta o tipo especÃ­fico: subsidiÃ¡ria ou solidÃ¡ria
    if re.search(r'responsabilidade\s+subsidiaria|subsidiariamente\s+responsaveis?', norm):
        tipo_resp = 'subsidiaria'
    elif re.search(r'responsabilidade\s+solidaria|solidariamente\s+(?:responsaveis?|condena)', norm):
        tipo_resp = 'solidaria'
    else:
        tipo_resp = 'subsidiaria/solidaria'

    if n_rec <= 1:
        # Com 1 (ou 0 detectada), verificar se hÃ¡ pedido de subsidiÃ¡ria (autuaÃ§Ã£o errada)
        if tipo_resp != 'subsidiaria/solidaria' or re.search(
            r'responsabilidade\s+(subsidiaria|solidaria)'
            r'|solidariamente\s+(?:responsaveis?|condena)'
            r'|subsidiariamente\s+responsaveis?',
            norm
        ):
            return [f"B11_RESPONSAB: ALERTA - 1 reclamada mas pedido de "
                    f"responsabilidade {tipo_resp} (autuacao incorreta?)"]
        return ["B11_RESPONSAB: OK - unica reclamada, nao aplicavel"]

    # ---- Duas ou mais reclamadas ----

    # 1) Pedido explÃ­cito ou implÃ­cito por palavras-chave
    tem_pedido = bool(re.search(
        r'responsabilidade\s+(subsidiaria|solidaria)'
        r'|responsabilizacao\s+subsidiaria'
        r'|solidariamente\s+(?:responsaveis?|condena)'
        r'|subsidiariamente\s+responsaveis?'
        r'|condena[cÃ§][aÃ£]o\s+solidar'
        r'|devedoras?\s+solidar'
        r'|devedoras?\s+subsidiar'
        r'|respondam?\s+solidariamente'
        r'|respondam?\s+subsidiariamente',
        norm
    ))

    # 2) PadrÃ£o contextual: menÃ§Ã£o Ã  primeira/segunda/demais reclamada em janela com
    #    "responsabilidade", "devedora", "solidar", "subsidiar" ou "prestadora de serviÃ§o"
    if not tem_pedido:
        for m in re.finditer(
            r'(?:primeira|segunda|terceira|demais|todas?\s+as?)\s+reclamad[ao]',
            norm
        ):
            janela = norm[max(0, m.start() - 400): m.end() + 400]
            if re.search(
                r'responsabilid|devedora|solidar|subsidiar'
                r'|prestadora\s+de\s+servi[cÃ§]|tomadora',
                janela
            ):
                tem_pedido = True
                break

    # 3) Causa de pedir (terceirizaÃ§Ã£o, grupo econÃ´mico, sÃ³cio, etc.)
    tem_causa = bool(re.search(
        r'tomador\s+de\s+servico|terceirizacao|prestacao\s+de\s+servico'
        r'|grupo\s+economico|subempreitada|terceirizado'
        r'|prestadora\s+(?:de\s+)?servicos?'
        r'|s[oÃ³]ci[ao][- ]proprietari|s[oÃ³]ci[ao][- ]gerente'
        r'|dono\s+da\s+empresa|proprietari[ao]\s+d[ao]'
        r'|empres[ao]\s+d[ao]\s+grupo'
        r'|administrador[ao]|s[oÃ³]ci[ao]\b',
        norm
    ))

    if not tem_pedido:
        return [f"B11_RESPONSAB: ALERTA - {n_rec} reclamadas sem pedido de "
                f"responsabilidade subsidiaria/solidaria (emenda necessaria)"]
    if not tem_causa:
        return [f"B11_RESPONSAB: ALERTA - pedido de responsabilidade {tipo_resp} sem "
                f"causa de pedir explicita ({n_rec} reclamadas)"]
    return [f"B11_RESPONSAB: OK - {n_rec} reclamadas com pedido de responsabilidade {tipo_resp} e causa de pedir"]


# ===== B12 â€” EndereÃ§o Reclamante + AudiÃªncia Virtual =====

def _checar_endereco_reclamante(texto: str) -> List[str]:
    linhas = []
    norm = _norm(texto)

    # EndereÃ§o do reclamante
    m = re.search(
        r'(residente|domiciliad[ao])[^\.]{0,300}?'
        r'([a-zÃ¡Ã Ã¢Ã£Ã©Ã¨ÃªÃ­Ã¯Ã³Ã´ÃµÃ¶ÃºÃ§Ã±][a-zÃ¡Ã Ã¢Ã£Ã©Ã¨ÃªÃ­Ã¯Ã³Ã´ÃµÃ¶ÃºÃ§Ã±\s]+)\s*[-/]\s*([a-z]{2})\b',
        norm)
    if m:
        cidade = m.group(2).strip()
        estado = m.group(3)
        cidade_uf = f"{cidade}/{estado}"
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
        if estado == 'sp' and (cidade in grande_sp or cidade == 'sao paulo'):
            linhas.append("B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP")
        else:
            linhas.append(f"B12_ENDERECO: ALERTA - reclamante em {cidade_uf} "
                          f"(fora SP) - verificar audiencia virtual")
    else:
        linhas.append("B12_ENDERECO: INFO - endereco do reclamante nao identificado")

    # AudiÃªncia virtual / telepresencial (separado do Bloco 7)
    termos_aud = [
        'audiencia virtual', 'audiencia telepresencial', 'videoconferencia',
        'audiencia hibrida', 'audiencia online', 'telepresencialmente',
        'por videoconferencia',
    ]
    encontrado = next((t for t in termos_aud if t in norm), None)
    if encontrado:
        linhas.append(f"B12_AUD_VIRTUAL: ALERTA - pedido de {encontrado} "
                      f"- verificar compatibilidade com pauta da vara")
    else:
        linhas.append("B12_AUD_VIRTUAL: OK - sem pedido de audiencia virtual/telepresencial")
    return linhas


# ===== B13 â€” Rito Processual =====

def _checar_rito(texto: str, capa_dados: dict) -> str:
    norm = _norm(texto)
    valor = capa_dados.get('valor_causa')
    if valor is None:
        m_valor = re.search(r'valor\s+da\s+causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
        if not m_valor:
            return "B13_RITO: ALERTA - valor da causa nao identificado"
        try:
            valor = float(m_valor.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            return "B13_RITO: ALERTA - valor da causa em formato invalido"

    rito_dec = capa_dados.get('rito_declarado')
    if not rito_dec:
        m_rito = re.search(r'RITO[:\s]+(SUMAR[IÃ]SSIMO|ORDIN[ÃA]RIO)', texto[:3000], re.IGNORECASE)
        if m_rito:
            rito_dec = 'SUMARISSIMO' if re.search(r'sumar', _norm(m_rito.group(1))) else 'ORDINARIO'

    # Mesma lÃ³gica anti-falso-positivo do B3: ignorar labels de endereÃ§o e "direito privado"
    _pub_ctx = norm[:2600]
    _pub_ok = False
    for _m_pub in re.finditer(r'\b(municipio|estado\s+de|uniao\s+federal|autarquia|fazenda\s+p[ue]blica)\b', _pub_ctx):
        _t = _pub_ctx[max(0, _m_pub.start()-80): _m_pub.end()+20]
        if re.search(r'municipio\s*:', _t, re.IGNORECASE) or re.search(r'estado\s*:', _t, re.IGNORECASE):
            continue
        _t2 = _pub_ctx[max(0, _m_pub.start()-200): _m_pub.end()+50]
        if re.search(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado', _t2):
            continue
        _pub_ok = True
        break
    tem_pub = _pub_ok

    if tem_pub:
        rito_correto = 'ORDINARIO'
        motivo = 'PJDP no polo passivo (art. 852-A Â§1 CLT)'
    elif valor <= ALCADA:
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


# ===== B14 â€” Art. 611-B CLT =====

def _checar_art611b(texto: str) -> str:
    # SÃ³ alerta se "art. 611-B" aparecer junto de "CLT" ou "coletiva" na mesma linha
    for linha in texto.splitlines():
        if re.search(r'art\.?\s*611-?B', linha, re.IGNORECASE):
            if re.search(r'clt|coletiv', linha, re.IGNORECASE):
                return "B14_ART611B: ALERTA - mencao art. 611-B CLT - colocar lembrete no processo"
    return "B14_ART611B: OK"


_ROTULOS_SAIDA = {
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
}


def _rotulo_saida(prefixo: str) -> str:
    return _ROTULOS_SAIDA.get(prefixo, prefixo.replace('_', ' ').strip())


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

    m_ok = re.search(
        r'OK - (?P<cep>\d{2}\.\d{3}-\d{3}) \((?P<num>\d+)\) '
        r'no intervalo (?P<lo>\d+)-(?P<hi>\d+) Zona Sul \[(?P<label>.+)\]$',
        texto
    )
    if m_ok:
        return (
            f'CEP: {m_ok.group("cep")} ({m_ok.group("num")}) - '
            f'intervalo {m_ok.group("lo")}-{m_ok.group("hi")} Zona Sul '
            f'[{m_ok.group("label")}]'
        )

    m_alerta = re.search(
        r'ALERTA - Incompetencia Territorial - CEP (?P<cep>\d{2}\.\d{3}-\d{3}) '
        r'\((?P<num>\d+)\) fora dos intervalos Zona Sul \[(?P<label>.+)\]$',
        texto
    )
    if m_alerta:
        return (
            f'CEP: {m_alerta.group("cep")} ({m_alerta.group("num")}) - '
            f'fora dos intervalos Zona Sul [{m_alerta.group("label")}]'
        )

    return f'CEP: {texto}'


def _formatar_saida_item(item: str) -> str:
    prefixo, status, corpo = _conteudo_saida_item(item)

    if not prefixo:
        return _normalizar_continuacao(corpo)

    rotulo = _rotulo_saida(prefixo)
    corpo = _normalizar_continuacao(corpo)

    if prefixo == 'B1_DOCS':
        corpo = re.sub(r'\bprocuracao\b', 'procuraÃ§Ã£o', corpo)
        corpo = re.sub(r'\bdoc identidade\b', 'documento de identidade', corpo)
        corpo = re.sub(r'\b(copia|copias)\b', 'cÃ³pia', corpo)
        corpo = corpo.replace('conteudo:"', 'conteudo do anexo "')
        corpo = corpo.replace('titulo', 'titulo do anexo')

    elif prefixo == 'B3_PARTES':
        if 'PJDP no polo passivo' in corpo:
            corpo = ('PJDP no polo passivo; regra aplicada: menÃ§Ã£o a municÃ­pio, '
                     'estado, UniÃ£o, autarquia ou fazenda pÃºblica na peÃ§a.')
        elif corpo.startswith('reclamante='):
            corpo = corpo.replace('reclamante=', 'reclamante: ').replace(' CPF=', ' CPF: ')
        elif 'reclamante nao identificado na capa' in corpo:
            corpo = 'reclamante nao identificado na capa'
        elif 'parte menor de idade' in corpo:
            corpo = corpo.replace(' - incluir MPT custos legis', '; incluir MPT custos legis')

    elif prefixo == 'B5_RECLAMADAS':
        corpo = corpo.replace('[fonte: certidao]', 'fonte: certidÃ£o')

    elif prefixo == 'B6_TUTELA':
        corpo = corpo.replace('pedido tutela provisoria', 'pedido de tutela provisoria')
        corpo = corpo.replace('- encaminhar para despacho', '; encaminhar para despacho')

    elif prefixo == 'B8_PEDIDOS':
        if status == 'OK':
            corpo = corpo.replace('pedido(s) com valor:', 'pedido(s) com valor:')

    elif prefixo == 'B7_DIGITAL':
        if status == 'ALERTA':
            corpo = corpo.replace('pedido expresso de Juizo 100% Digital identificado, mas processo nao marcado na API',
                                  'pedido expresso de Juizo 100% Digital identificado, mas processo nao marcado na API')
        else:
            corpo = corpo.replace('sem pedido expresso de Juizo 100% Digital na peticao',
                                  'sem pedido expresso de Juizo 100% Digital na peticao')

    elif prefixo == 'B10_LITISPEND':
        corpo = corpo.replace('litispendencia/prevencao/coisa julgada',
                              'litispendencia / prevencao / coisa julgada')

    elif prefixo == 'B11_RESPONSAB':
        corpo = corpo.replace('responsabilidade subsidiaria/solidaria',
                              'responsabilidade subsidiaria / solidaria')

    elif prefixo == 'B12_AUD_VIRTUAL':
        corpo = corpo.replace('audiencia virtual/telepresencial',
                              'audiencia virtual / telepresencial')

    elif prefixo == 'B14_ART611B':
        corpo = corpo.replace('mencao art. 611-B CLT - colocar lembrete no processo',
                              'menÃ§Ã£o ao art. 611-B CLT - colocar lembrete no processo')

    return f'{rotulo}: {corpo}'


# ===== FUNÃ‡ÃƒO PRINCIPAL =====

def triagem_peticao(driver) -> str:
    """
    Executa triagem completa de petiÃ§Ã£o inicial trabalhista.
    Driver deve estar autenticado na pÃ¡gina do processo (detalhe) no PJe.
    Retorna texto simples, mÃ¡ximo 8000 chars.
    Ordem de saÃ­da: competencia â†’ alertas â†’ itens OK.
    """
    # Checagem de dependÃªncias para OCR
    _pytesseract_ok = True
    _pdf2image_ok = True
    try:
        import pytesseract
    except ImportError:
        _pytesseract_ok = False
        print('[TRIAGEM] âš ï¸ pytesseract nÃ£o instalado â€” OCR indisponÃ­vel (documentos de identidade podem retornar vazio)')
    
    try:
        import pdf2image
    except ImportError:
        _pdf2image_ok = False
        print('[TRIAGEM] âš ï¸ pdf2image nÃ£o instalado â€” OCR indisponÃ­vel')
    
    if not (_pytesseract_ok and _pdf2image_ok):
        print('[TRIAGEM] â„¹ï¸ Para extrair texto de documentos digitalizados (RG, CNH), instale: pip install pytesseract pdf2image')
    
    print('[TRIAGEM] â³ Iniciando _coletar_textos_processo...')
    coleta = _coletar_textos_processo(driver)
    print(f'[TRIAGEM] _coletar_textos_processo retornou: erro={coleta.get("erro")}')
    if coleta.get('erro'):
        return f"ERRO: {coleta['erro']}"

    texto = coleta['texto_inicial']
    if not texto or len(texto) < 100:
        return "ERRO: texto da peticao inicial extraido vazio ou muito curto"

    anexos = coleta['anexos']
    capa_dados = coleta.get('capa_dados') or {}

    rd: Dict[str, Any] = {}

    b1 = _checar_procuracao_e_identidade(anexos, capa_dados.get('reclamante_nome') or ''); rd['docs_essenciais'] = b1
    cep = _checar_cep(texto, capa_dados); rd['cep'] = cep
    partes = _checar_partes(texto, capa_dados); rd['partes'] = partes
    seg = _checar_segredo(texto, capa_dados); rd['segredo'] = seg
    rec = _checar_reclamadas(texto, capa_dados); rd['reclamadas'] = rec
    tut = _checar_tutela(texto, capa_dados); rd['tutela'] = tut
    dig = _checar_digital(texto, capa_dados); rd['digital'] = dig
    ped = _checar_pedidos_liquidados(texto); rd['pedidos'] = ped
    pf = _checar_pessoa_fisica(texto, capa_dados); rd['pessoa_fis'] = pf
    lit = _checar_litispendencia(texto, coleta.get('associados_sistema')); rd['litispend'] = lit
    resp = _checar_responsabilidade(texto, capa_dados); rd['responsab'] = resp
    end = _checar_endereco_reclamante(texto); rd['endereco'] = end
    rito = _checar_rito(texto, capa_dados); rd['rito'] = rito
    a6 = _checar_art611b(texto); rd['art611b'] = a6

    def _itens(v):
        return v if isinstance(v, list) else [v]

    alertas, itens_ok = [], []
    for val in [b1, partes, seg, rec, resp, tut, dig, pf, lit, end, rito, a6]:
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

