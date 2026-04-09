import re
from typing import Any, Dict, List

from .coleta import _coletar_textos_processo
from .regras import (
    _checar_art611b,
    _checar_cep,
    _checar_digital,
    _checar_endereco_reclamante,
    _checar_litispendencia,
    _checar_pedidos_liquidados,
    _checar_pessoa_fisica,
    _checar_procuracao_e_identidade,
    _checar_reclamadas,
    _checar_responsabilidade,
    _checar_rito,
    _checar_segredo,
    _checar_tutela,
    _checar_partes,
)

__all__ = ['triagem_peticao']


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
        corpo = re.sub(r'\bprocuracao\b', 'procura\u00e7\u00e3o', corpo)
        corpo = re.sub(r'\bdoc identidade\b', 'documento de identidade', corpo)
        corpo = re.sub(r'\b(copia|copias)\b', 'c\u00f3pia', corpo)
        corpo = corpo.replace('conteudo:"', 'conteudo do anexo "')
        corpo = corpo.replace('titulo', 'titulo do anexo')

    elif prefixo == 'B3_PARTES':
        if 'PJDP no polo passivo' in corpo:
            corpo = ('PJDP no polo passivo; regra aplicada: mencao a municipio, '
                     'estado, Uniao, autarquia ou fazenda publica na peca.')
        elif corpo.startswith('reclamante='):
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
    _pytesseract_ok = True
    _pdf2image_ok = True
    try:
        import pytesseract
    except ImportError:
        _pytesseract_ok = False
        print('[TRIAGEM] ⚠ pytesseract nao instalado — OCR indisponivel (documentos de identidade podem retornar vazio)')

    try:
        import pdf2image
    except ImportError:
        _pdf2image_ok = False
        print('[TRIAGEM] ⚠ pdf2image nao instalado — OCR indisponivel')

    if not (_pytesseract_ok and _pdf2image_ok):
        print('[TRIAGEM] ℹ️ Para extrair texto de documentos digitalizados (RG, CNH), instale: pip install pytesseract pdf2image')

    print('[TRIAGEM] ▶ Iniciando _coletar_textos_processo...')
    coleta = _coletar_textos_processo(driver)
    print(f'[TRIAGEM] _coletar_textos_processo retornou: erro={coleta.get("erro")}')
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
    ped = _checar_pedidos_liquidados(texto)
    pf = _checar_pessoa_fisica(texto, capa_dados)
    lit = _checar_litispendencia(texto, coleta.get('associados_sistema'))
    resp = _checar_responsabilidade(texto, capa_dados)
    end = _checar_endereco_reclamante(texto)
    rito = _checar_rito(texto, capa_dados)
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
