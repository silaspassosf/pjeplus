from typing import Optional, Any, Dict, List

import re

from api.variaveis_client import PjeApiClient


def obter_codigo_validacao_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Replica a construção de 'chave' feita na extensão."""
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
    """Resolve o equivalente a obterPecaProcessualDaTimeline do JS."""
    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

    pesquisar_anexos = modo == 'anexos'

    flat = []
    for d in dados:
        flat.append(d)
        if d.get('anexos'):
            for a in d.get('anexos'):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get('tipo') or '').strip()
        titulo = (docto.get('titulo') or '').strip()
        is_chave_acesso = (tipo_label.lower() == 'chave de acesso' and (tipo.lower() == 'chave de acesso' or (tipo.lower() == 'certidão' and 'chave de acesso' in titulo.lower())))
        is_planilha = (tipo_label.lower() == 'planilha de cálculos' and tipo in ['Planilha de Cálculos', 'Planilha de Atualização de Cálculos'])
        if is_chave_acesso or is_planilha or tipo == tipo_label:
            if modo == 'chave':
                doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idDocumentoPai')
                if not doc_id:
                    doc_id = docto.get('idUnicoDocumento')
                if not doc_id:
                    return None
                return obter_codigo_validacao_documento(client, id_processo, doc_id)
            elif modo == 'id':
                return docto.get('idUnicoDocumento') or docto.get('id')
            elif modo == 'anexos':
                id_pai = docto.get('id')
                anexos = [a for a in flat if a.get('idDocumentoPai') == id_pai]
                lista = ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
                return lista
            else:
                return docto

    return None


def resolver_variavel(client: PjeApiClient, id_processo: str, variavel: str) -> Optional[str]:
    """Recebe nomes como '[maisPje:últimaSentença:chave]' ou 'últimaSentença:chave' e retorna valor."""
    v = variavel
    if v.startswith('[') and v.endswith(']'):
        v = v[1:-1]
    parts = v.split(':')
    if parts[0] == 'maisPje':
        parts = parts[1:]
    tipo_token = parts[0]
    modo = 'chave' if (len(parts) > 1 and parts[1] == 'chave') else ('id' if (len(parts) > 1 and parts[1] == 'id') else ('anexos' if (len(parts) > 1 and parts[1] == 'anexos') else 'chave'))

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
        tipo_label = tipo_token

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
            anexos = primeiro.get('anexos') or []
            return ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
        else:
            return primeiro

    return obter_peca_processual_da_timeline(client, id_processo, tipo_label, modo)


def get_all_variables(client: PjeApiClient, id_processo: str) -> Dict[str, Optional[str]]:
    """Resolve the common set of variables exposed by the extension and"""
    result: Dict[str, Optional[str]] = {}

    proc = client.processo_por_id(id_processo)
    partes = client.partes(id_processo) or []

    exequente = None
    executado = None
    if partes:
        for p in partes:
            polo = (p.get('tipoPolo') or '').lower()
            nome = p.get('nome') or p.get('parte') or p.get('nomeParte')
            if not nome:
                continue
            if 'autor' in polo or 'exequente' in polo or ('polo' in polo and 'autor' in polo):
                exequente = exequente or nome
            if 'reu' in polo or 'executado' in polo or 'demandado' in polo:
                executado = executado or nome

    if not exequente:
        exequente = (proc.get('partes') and proc.get('partes')[0].get('nome')) if proc and proc.get('partes') else None
    if not executado:
        if proc and proc.get('partes') and len(proc.get('partes')) > 1:
            executado = proc.get('partes')[1].get('nome')

    result['exequente'] = exequente
    result['executado'] = executado

    calculos = client.calculos(id_processo)
    valor_divida = None
    if calculos:
        if isinstance(calculos, dict):
            if 'valor' in calculos:
                valor_divida = calculos.get('valor')
            elif calculos.get('totalElements') and calculos.get('content'):
                content = calculos.get('content')
                if content:
                    item = content[0]
                    valor_divida = item.get('valor') or item.get('valorExecucao')

    result['valorDivida'] = valor_divida

    result['justicaGratuita'] = proc.get('justicaGratuita') if proc else None
    result['justicaGratuitaData'] = None

    result['transitoJulgado'] = proc.get('dataTransito') or proc.get('transito') or proc.get('transitoEm') if proc else None

    result['custasArbitradas'] = None

    pericias = client.pericias(id_processo)
    audiencia_data = None
    audiencia_hora = None
    if pericias and isinstance(pericias, dict):
        if pericias.get('content'):
            p = pericias.get('content')[0]
            audiencia_data = p.get('dataPrazo') or p.get('data')
    if not audiencia_data and proc:
        audiencia_data = proc.get('audiencia') or proc.get('dataAudiencia')

    result['audiencia:data'] = audiencia_data
    result['audiencia:hora'] = audiencia_hora

    timeline_tokens = [
        'petiçãoInicial', 'últimaContestação', 'últimaManifestação', 'últimaSentença',
        'últimoAcórdão', 'últimoDespacho', 'últimaDecisão', 'últimaAta', 'últimaCertidão', 'últimoCálculo', 'último'
    ]
    for tok in timeline_tokens:
        key_id = f"{tok}:id"
        key_ch = f"{tok}:chave"
        key_an = f"{tok}:anexos"
        result[key_id] = resolver_variavel(client, id_processo, tok + ':id')
        result[key_ch] = resolver_variavel(client, id_processo, tok + ':chave')
        result[key_an] = resolver_variavel(client, id_processo, tok + ':anexos')

    result['chaveDeAcesso:id'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:id')
    result['chaveDeAcesso:chave'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:chave')

    perito = None
    if pericias and isinstance(pericias, dict) and pericias.get('content'):
        p0 = pericias.get('content')[0]
        perito = p0.get('perito') or p0.get('peritoNome') or p0.get('responsavel')
    result['perito'] = perito

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
    if tipos is None:
        tipos = ['Sentença', 'Decisão', 'Despacho']

    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

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
            doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idUnicoDocumento')
            if not doc_id:
                continue
            try:
                chave = obter_codigo_validacao_documento(client, id_processo, doc_id)
                if not chave:
                    continue
                base = client.trt_host
                if not base.startswith('http'):
                    base = 'https://' + base
                instancia = getattr(client, 'grau', 1)
                link = f"{base}/pjekz/validacao/{chave}?instancia={instancia}"
                return link
            except Exception:
                continue

    return None