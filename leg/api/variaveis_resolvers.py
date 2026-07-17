from typing import Optional, Any, Dict, List

import re

from Fix.variaveis_client import PjeApiClient


def obter_codigo_validacao_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Replica a construção de 'chave' feita na extensão.

    Chave := parte numérica de dataInclusaoBin (posições 2..16) + idBin (pad 14)
    """
    dados = client.documento_por_id(id_processo, id_documento, incluirAssinatura=False, incluirAnexos=False)
    if not dados:
        return None
    data = dados.get('dataInclusaoBin', '')
    idBin = dados.get('idBin')
    if not data or idBin is None:
        return None
    nums = re.sub(r'\D', '', data)
    part = nums[2:17] if len(nums) >= 17 else nums
    chave = part + str(idBin).zfill(14)
    return chave


def obter_peca_processual_da_timeline(client: PjeApiClient, id_processo: str, tipo_label: str, modo: str = 'chave', itens_timeline: Optional[List[Dict]] = None) -> Optional[str]:
    """Resolve o equivalente a obterPecaProcessualDaTimeline do JS.

    modo: 'chave'|'id'|'anexos'|'raw' ('raw' retorna id interno)
    """
    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

    pesquisar_anexos = modo == 'anexos'

    # flatten documentos + anexos (anexos mantêm idDocumentoPai)
    flat = []
    for d in dados:
        flat.append(d)
        if d.get('anexos'):
            for a in d.get('anexos'):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get('tipo') or '').strip()
        titulo = (docto.get('titulo') or '').strip()
        # special cases similar ao JS
        is_chave_acesso = (tipo_label.lower() == 'chave de acesso' and (tipo.lower() == 'chave de acesso' or (tipo.lower() == 'certidão' and 'chave de acesso' in titulo.lower())))
        is_planilha = (tipo_label.lower() == 'planilha de cálculos' and tipo in ['Planilha de Cálculos', 'Planilha de Atualização de Cálculos'])
        if is_chave_acesso or is_planilha or tipo == tipo_label:
            # encontrado
            if modo == 'chave':
                # precisa do id do documento real
                doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idDocumentoPai')
                if not doc_id:
                    # tentar idUnicoDocumento como fallback
                    doc_id = docto.get('idUnicoDocumento')
                if not doc_id:
                    return None
                return obter_codigo_validacao_documento(client, id_processo, doc_id)
            elif modo == 'id':
                return docto.get('idUnicoDocumento') or docto.get('id')
            elif modo == 'anexos':
                # compõe lista de anexos pertencentes ao documento pai
                id_pai = docto.get('id')
                anexos = [a for a in flat if a.get('idDocumentoPai') == id_pai]
                lista = ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
                return lista
            else:
                return docto

    return None


def resolver_variavel(client: PjeApiClient, id_processo: str, variavel: str) -> Optional[str]:
    """Recebe nomes como '[maisPje:últimaSentença:chave]' ou 'últimaSentença:chave' e retorna valor.

    Implementa as variáveis de timeline mais comuns (sentença, despacho, decisão, etc.).
    """
    # normalizar
    v = variavel
    if v.startswith('[') and v.endswith(']'):
        v = v[1:-1]
    # formatos: maisPje:últimaSentença:chave or últimaSentença:chave
    parts = v.split(':')
    # se começar com 'maisPje' descarta
    if parts[0] == 'maisPje':
        parts = parts[1:]
    # agora parts ex: ['últimaSentença', 'chave'] or ['último','chave']
    tipo_token = parts[0]
    modo = 'chave' if (len(parts) > 1 and parts[1] == 'chave') else ('id' if (len(parts) > 1 and parts[1] == 'id') else ('anexos' if (len(parts) > 1 and parts[1] == 'anexos') else 'chave'))

    # mapear token para label do tipo do documento usado pela timeline
    mapa = {
        'últimaSentença': 'Sentença',
        'últimoDespacho': 'Despacho',
        'últimaDecisão': 'Decisão',
        'últimoAcórdão': 'Acórdão',
        'últimaAta': 'Ata da Audiência',
        'últimaCertidão': 'Certidão',
        'últimaContestação': 'Contestação',
        'últimaManifestação': 'Manifestação',
        'petiçãoInicial': 'Petição Inicial',
        'chaveDeAcesso': 'Chave de Acesso',
        'últimoCálculo': 'Planilha de Cálculos',
        'último': '*'
    }

    tipo_label = mapa.get(tipo_token, None)
    if tipo_label is None:
        # se não mapeado, tenta usar o token como label direta
        tipo_label = tipo_token

    # modo '*' significa primeiro documento no timeline
    if tipo_label == '*':
        itens = client.timeline(id_processo)
        if not itens:
            return None
        primeiro = itens[0]
        if modo == 'chave':
            return obter_codigo_validacao_documento(client, id_processo, primeiro.get('id'))
        elif modo == 'id':
            return primeiro.get('idUnicoDocumento') or primeiro.get('id')
        elif modo == 'anexos':
            # montar lista de anexos do primeiro
            anexos = primeiro.get('anexos') or []
            return ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
        else:
            return primeiro

    return obter_peca_processual_da_timeline(client, id_processo, tipo_label, modo)


def get_all_variables(client: PjeApiClient, id_processo: str) -> Dict[str, Optional[str]]:
    """Resolve the common set of variables exposed by the extension and
    returns a dict mapping tokens (without bracket) to values.

    Example keys: 'últimaSentença:chave', 'exequente', 'valorDivida', 'audiencia:data'
    """
    result: Dict[str, Optional[str]] = {}

    # Basic process info
    proc = client.processo_por_id(id_processo)
    partes = client.partes(id_processo) or []

    # partes: try to find autor/exequente and respondente/executado
    exequente = None
    executado = None
    if partes:
        # extension picks primary polo; try buscar por tipoPolo
        for p in partes:
            polo = (p.get('tipoPolo') or '').lower()
            nome = p.get('nome') or p.get('parte') or p.get('nomeParte')
            if not nome:
                continue
            if 'autor' in polo or 'exequente' in polo or ('polo' in polo and 'autor' in polo):
                exequente = exequente or nome
            if 'reu' in polo or 'executado' in polo or 'demandado' in polo:
                executado = executado or nome

    # fallback to process main fields
    if not exequente:
        exequente = (proc.get('partes') and proc.get('partes')[0].get('nome')) if proc and proc.get('partes') else None
    if not executado:
        # try second
        if proc and proc.get('partes') and len(proc.get('partes')) > 1:
            executado = proc.get('partes')[1].get('nome')

    result['exequente'] = exequente
    result['executado'] = executado

    # dívida / cálculos
    calculos = client.calculos(id_processo)
    valor_divida = None
    if calculos:
        # look for a 'valor' field or take first
        if isinstance(calculos, dict):
            # diversos formatos possíveis
            if 'valor' in calculos:
                valor_divida = calculos.get('valor')
            elif calculos.get('totalElements') and calculos.get('content'):
                # try last content
                content = calculos.get('content')
                if content:
                    item = content[0]
                    valor_divida = item.get('valor') or item.get('valorExecucao')

    result['valorDivida'] = valor_divida

    # justiça gratuita and date - try to obtain from processo data
    result['justicaGratuita'] = proc.get('justicaGratuita') if proc else None
    result['justicaGratuitaData'] = None

    # trânsito em julgado - heurística: procurar campo dataTransito or dtTransito
    result['transitoJulgado'] = proc.get('dataTransito') or proc.get('transito') or proc.get('transitoEm') if proc else None

    # custas arbitradas - try to infer from calculos/process data
    result['custasArbitradas'] = None

    # audiência - try pericias or processo info
    pericias = client.pericias(id_processo)
    audiencia_data = None
    audiencia_hora = None
    if pericias and isinstance(pericias, dict):
        # take first pericia with prazoEntrega or data
        if pericias.get('content'):
            p = pericias.get('content')[0]
            audiencia_data = p.get('dataPrazo') or p.get('data')
    # fallback: look into proc
    if not audiencia_data and proc:
        audiencia_data = proc.get('audiencia') or proc.get('dataAudiencia')

    result['audiencia:data'] = audiencia_data
    result['audiencia:hora'] = audiencia_hora

    # timeline-based tokens - use resolver_variavel
    timeline_tokens = [
        'petiçãoInicial', 'últimaContestação', 'últimaManifestação', 'últimaSentença',
        'últimoAcórdão', 'últimoDespacho', 'últimaDecisão', 'últimaAta', 'últimaCertidão', 'últimoCálculo', 'último'
    ]
    for tok in timeline_tokens:
        # id
        key_id = f"{tok}:id"
        key_ch = f"{tok}:chave"
        key_an = f"{tok}:anexos"
        result[key_id] = resolver_variavel(client, id_processo, tok + ':id')
        result[key_ch] = resolver_variavel(client, id_processo, tok + ':chave')
        result[key_an] = resolver_variavel(client, id_processo, tok + ':anexos')

    # chave de acesso
    result['chaveDeAcesso:id'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:id')
    result['chaveDeAcesso:chave'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:chave')

    # perito (first pericia)
    perito = None
    if pericias and isinstance(pericias, dict) and pericias.get('content'):
        p0 = pericias.get('content')[0]
        perito = p0.get('perito') or p0.get('peritoNome') or p0.get('responsavel')
    result['perito'] = perito

    # exequente telefone - try partes
    tel = None
    if partes:
        for p in partes:
            nome = p.get('nome')
            if nome and exequente and nome == exequente:
                tel = p.get('telefone') or p.get('telefoneContato') or p.get('contatos')
                break
    result['exequente:telefone'] = tel

    return result


def obter_chave_ultimo_despacho_decisao_sentenca(client: PjeApiClient, id_processo: str, tipos: Optional[List[str]] = None, itens_timeline: Optional[List[Dict]] = None) -> Optional[str]:
    """Retorna a chave de validação do documento mais recente entre
    Despacho, Decisão ou Sentença.

    - Busca a timeline (ou usa `itens_timeline` se fornecido).
    - Itera os elementos (documentos + anexos) na ordem retornada pela
      API (a extensão assume que o primeiro item é o mais recente).
    - Ao encontrar o primeiro documento cujo `tipo` esteja na lista de
      `tipos` (padrão: ['Sentença','Decisão','Despacho']), retorna a chave
      construída via `obter_codigo_validacao_documento`.

    Retorna `None` se não houver documento correspondente ou em caso de erro.
    """
    if tipos is None:
        tipos = ['Sentença', 'Decisão', 'Despacho']

    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

    # flatten similar to obter_peca_processual_da_timeline
    flat = []
    for d in dados:
        flat.append(d)
        if d.get('anexos'):
            for a in d.get('anexos'):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get('tipo') or '').strip()
        if not tipo:
            continue
        if tipo in tipos:
            # obter id do documento na forma esperada pela API documento_por_id
            doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idUnicoDocumento')
            if not doc_id:
                continue
            try:
                chave = obter_codigo_validacao_documento(client, id_processo, doc_id)
                if not chave:
                    continue
                # build validation URL using the client's host and grau (instance)
                base = client.trt_host
                if not base.startswith('http'):
                    base = 'https://' + base
                instancia = getattr(client, 'grau', 1)
                link = f"{base}/pjekz/validacao/{chave}?instancia={instancia}"
                return link
            except Exception:
                # falha ao obter, tentar próximo
                continue

    return None