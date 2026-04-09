<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# enviei erraod. agora mandeu os corretos.

<!-- pjeplus:apply -->

## Objetivo

Refatorar `tr.py` de forma **cirúrgica**, preservando a funcionalidade atual, removendo duplicações evidentes, reorganizando por pertinência temática em módulos menores e mantendo o ponto de entrada `triagem_peticao` compatível com o uso atual em `aud.py`. O arquivo `tr.py` anexado contém duplicações reais de blocos como `_checar_tutela`, `_checar_reclamadas`, `_checar_partes` e helpers correlatos, além de concentrar coleta, parsing, regras e formatação em um único módulo muito grande.  O `aud.py` usa apenas `from tr import triagem_peticao`, então a compatibilidade pode ser mantida com um `tr.py` fino de reexport, seguido de um ajuste opcional explícito em `aud.py`.[^1][^2]

## Arquivo(s) Alvo

- `tr.py`


## Trecho Original

```python
from tr import triagem_peticao
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
"""
Compat layer para triagem de petição inicial trabalhista.

Mantém o contrato legado:
    from tr import triagem_peticao
"""

from triagem import triagem_peticao

__all__ = ["triagem_peticao"]
```

<!-- pjeplus:delta:end -->

## Justificativa

Manter `tr.py` como fachada preserva compatibilidade imediata com o restante do projeto enquanto a lógica pesada é deslocada para módulos temáticos menores.[^2][^1]

***

## Objetivo

Introduzir o pacote temático `triagem/` como novo núcleo da refatoração, com ponto de entrada estável e sem mudança funcional na assinatura pública. A função pública atual é `triagem_peticao(driver) -> str`, retornando texto simples limitado a 8000 caracteres.[^1]

## Arquivo(s) Alvo

- `triagem/__init__.py`


## Trecho Original

```python
# arquivo inexistente
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
from .service import triagem_peticao

__all__ = ["triagem_peticao"]
```

<!-- pjeplus:delta:end -->

## Justificativa

Cria um pacote limpo com export único, facilitando import estável e organização por temas sem alterar o contrato de chamada.[^1]

***

## Objetivo

Separar constantes, regexes base e pequenos utilitários puros que hoje estão espalhados no topo de `tr.py`, incluindo normalização e limites de rito/alcada. O arquivo atual define `SALARIO_MINIMO`, `ALCADA`, `RITO_SUMARISSIMO_MAX`, `INTERVALOS_CEP_ZONA_SUL` e `_norm` no mesmo módulo da lógica principal.[^1]

## Arquivo(s) Alvo

- `triagem/constants.py`


## Trecho Original

```python
# trecho atual completo encontra-se no topo de tr.py, misturado com toda a implementação
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import re
import unicodedata

SALARIO_MINIMO = 1622.00  # 2026
ALCADA = SALARIO_MINIMO * 2
RITO_SUMARISSIMO_MAX = SALARIO_MINIMO * 40

INTERVALOS_CEP_ZONA_SUL = [
    (4307000, 4314999),
    (4316000, 4477999),
    (4603000, 4620999),
    (4624000, 4703999),
    (4708000, 4967999),
    (5640000, 5642999),
    (5657000, 5665999),
    (5692000, 5692999),
    (5703000, 5743999),
    (5745000, 5750999),
    (5752000, 5895999),
]

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

_RE_CNPJ_NUM = re.compile(r'\b(?:\d{2}(?:[\.\s]?\d{3}){2}\/\d{4}-?\d{2}|\d{14})\b', re.IGNORECASE)
_RE_CPF_NUM = re.compile(r'\b(?:\d{3}(?:[\.\s]?\d{3}){2}-?\d{2}|\d{11})\b', re.IGNORECASE)

_CNPJ_CONTEXTOS = (
    'cnpj', 'inscrita no cnpj', 'inscrito no cnpj', 'cnpj sob', 'cnpj nº', 'cnpj no',
    'reclamad', 'pessoa juridica', 'pessoa juridica de direito privado',
    'pessoa juridica de direito publico', 'empresa', 'sociedade', 'matriz', 'filial', 'sede',
)

_CPF_CONTEXTOS = (
    'cpf', 'reclamad', 'pessoa fisica', 'pessoa natural',
)

_TERMOS_PROC_TITULO = ['procuracao', 'mandato']
_TERMOS_ID_TITULO = ['rg', 'cnh', 'documento de identidade', 'identidade', 'doc identidade']
_TERMOS_PROC_BODY = [
    'outorgo', 'poderes', 'por este instrumento particular', 'constituir como',
    'procuracao', 'mandato', 'outorgante', 'outorgado'
]
_TERMOS_ID_BODY = [
    'registro geral', 'carteira de identidade', 'carteira nacional de habilitacao',
    'secretaria de seguranca publica', 'documento de identidade',
    'data de nascimento', 'filiacao', 'naturalidade'
]

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

_STOPWORDS = {
    'da', 'de', 'do', 'das', 'dos', 'e', 'em', 'para', 'por', 'com', 'sem',
    'ltda', 'sa', 's.a', 'me', 'epp', 'empresa', 'grupo', 'industria',
    'comercio', 'servicos', 'servico'
}


def norm(texto: str) -> str:
    return unicodedata.normalize('NFD', texto or '').encode('ascii', 'ignore').decode().lower()
```

<!-- pjeplus:delta:end -->

## Justificativa

Isola dados estáveis e evita repetição de literais e regexes entre módulos, além de centralizar o `_norm` usado por praticamente todas as regras.[^1]

***

## Objetivo

Isolar helpers genéricos de formatação, parsing contextual e utilidades compartilhadas por coleta, regras e saída. O código atual repete lógica de parsing de prefixo/status, contexto de página e extração contextual de números dentro do mesmo módulo gigante.[^1]

## Arquivo(s) Alvo

- `triagem/utils.py`


## Trecho Original

```python
# helpers dispersos no tr.py
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import re
from typing import List, Tuple

from .constants import (
    _ROTULOS_SAIDA,
    _STOPWORDS,
    _CEP_TERMOS_TERRITORIAL,
    _CEP_TERMOS_PRESTACAO,
    _CEP_TERMOS_RECLAMANTE,
    _CEP_TERMOS_RECLAMADA,
    _CEP_TAG_TERRITORIAL,
    _CEP_TAG_PRESTACAO,
    _CEP_TAG_RECLAMANTE,
    _CEP_TAG_RECLAMADA,
    _CEP_TAG_GENERICO,
    norm,
)


def pag_contexto(texto: str, posicao: int, janela: int = 400) -> str:
    pag = 1
    for mp in re.finditer(r'P[aá]gina\s+(\d+)', texto[:posicao], re.IGNORECASE):
        pag = int(mp.group(1))
    inicio = max(0, posicao - janela)
    fim = min(len(texto), posicao + janela)
    trecho = texto[inicio:fim].replace('\n', ' ').strip()
    return f'[pág.{pag}] ...{trecho}...'


def formatar_endereco_parte(endereco: dict) -> str:
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


def partes_saida_item(item: str) -> Tuple[str, str]:
    if ': ' not in item:
        return '', item
    prefixo, resto = item.split(': ', 1)
    return prefixo, resto


def conteudo_saida_item(item: str) -> Tuple[str, str, str]:
    prefixo, resto = partes_saida_item(item)
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


def normalizar_continuacao(texto: str) -> str:
    return texto.replace('\n', '\n ').strip()


def rotulo_saida(prefixo: str) -> str:
    return _ROTULOS_SAIDA.get(prefixo, prefixo.replace('_', ' ').strip())


def formatar_competencia_saida(cep: str) -> str:
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


def formatar_saida_item(item: str) -> str:
    prefixo, status, corpo = conteudo_saida_item(item)

    if not prefixo:
        return normalizar_continuacao(corpo)

    rotulo = rotulo_saida(prefixo)
    corpo = normalizar_continuacao(corpo)

    if prefixo == 'B1_DOCS':
        corpo = re.sub(r'\bprocuracao\b', 'procuração', corpo)
        corpo = re.sub(r'\bdoc identidade\b', 'documento de identidade', corpo)
        corpo = re.sub(r'\b(copia|copias)\b', 'cópia', corpo)
        corpo = corpo.replace('conteudo:"', 'conteudo do anexo "')
        corpo = corpo.replace('titulo', 'titulo do anexo')
    elif prefixo == 'B3_PARTES':
        if 'PJDP no polo passivo' in corpo:
            corpo = (
                'PJDP no polo passivo; regra aplicada: menção a município, '
                'estado, União, autarquia ou fazenda pública na peça.'
            )
        elif corpo.startswith('reclamante='):
            corpo = corpo.replace('reclamante=', 'reclamante: ').replace(' CPF=', ' CPF: ')
        elif 'reclamante nao identificado na capa' in corpo:
            corpo = 'reclamante nao identificado na capa'
        elif 'parte menor de idade' in corpo:
            corpo = corpo.replace(' - incluir MPT custos legis', '; incluir MPT custos legis')
    elif prefixo == 'B5_RECLAMADAS':
        corpo = corpo.replace('[fonte: certidao]', 'fonte: certidão')
    elif prefixo == 'B6_TUTELA':
        corpo = corpo.replace('pedido tutela provisoria', 'pedido de tutela provisoria')
        corpo = corpo.replace('- encaminhar para despacho', '; encaminhar para despacho')
    elif prefixo == 'B10_LITISPEND':
        corpo = corpo.replace(
            'litispendencia/prevencao/coisa julgada',
            'litispendencia / prevencao / coisa julgada'
        )
    elif prefixo == 'B11_RESPONSAB':
        corpo = corpo.replace(
            'responsabilidade subsidiaria/solidaria',
            'responsabilidade subsidiaria / solidaria'
        )
    elif prefixo == 'B12_AUD_VIRTUAL':
        corpo = corpo.replace(
            'audiencia virtual/telepresencial',
            'audiencia virtual / telepresencial'
        )
    elif prefixo == 'B14_ART611B':
        corpo = corpo.replace(
            'mencao art. 611-B CLT - colocar lembrete no processo',
            'menção ao art. 611-B CLT - colocar lembrete no processo'
        )

    return f'{rotulo}: {corpo}'


def itens_lista(valor):
    return valor if isinstance(valor, list) else [valor]


def extrair_numeros_contextuais(texto: str, numero_re: re.Pattern, contextos: tuple[str, ...]) -> List[str]:
    candidatos: List[str] = []

    def registrar_bloco(bloco: str) -> None:
        bloco_norm = norm(bloco)
        if not any(ctx in bloco_norm for ctx in contextos):
            return
        for m in numero_re.finditer(bloco_norm):
            raw = re.sub(r'\D', '', m.group(0))
            if raw and raw not in candidatos:
                candidatos.append(raw)

    blocos = [b.strip() for b in re.split(r'\n\s*\n+', texto) if b.strip()]
    for bloco in blocos:
        registrar_bloco(bloco)

    if candidatos:
        return candidatos

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    for linha in linhas:
        registrar_bloco(linha)

    if candidatos:
        return candidatos

    texto_norm = norm(texto)
    for m in numero_re.finditer(texto_norm):
        ctx = texto_norm[max(0, m.start() - 220): min(len(texto_norm), m.end() + 220)]
        if not any(c in ctx for c in contextos):
            continue
        raw = re.sub(r'\D', '', m.group(0))
        if raw and raw not in candidatos:
            candidatos.append(raw)
    return candidatos


def extrair_palavras_reclamada(capa_dados: dict) -> list:
    reclamados = capa_dados.get('reclamados') or []
    nomes = [norm(r.get('nome', '')) for r in reclamados if r.get('nome')]
    palavras = set()
    for nome in nomes:
        for p in re.split(r'[^a-z0-9]+', nome):
            if len(p) > 3 and p not in _STOPWORDS:
                palavras.add(p)
    return sorted(palavras)


def cep_tag(ctx_norm: str, palavras_reclamada: list) -> int:
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
```

<!-- pjeplus:delta:end -->

## Justificativa

Agrupa utilidades transversais e elimina duplicações de parsing/saída já presentes no arquivo original, sem mexer nas regras de negócio.[^1]

***

## Objetivo

Extrair o pré-processamento do texto da petição para um módulo próprio, preservando a lógica atual de remoção segura de artefatos PJe e fingerprint de cabeçalho de escritório. Hoje `_remover_artefatos_pje`, `_aprender_cabecalho`, `_remover_cabecalho_por_pagina` e `_strip_cabecalho_rodape` ficam acoplados ao resto da triagem.[^1]

## Arquivo(s) Alvo

- `triagem/preprocess.py`


## Trecho Original

```python
# funções de strip de cabeçalho/rodapé atualmente no início de tr.py
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import re

from .constants import _RE_ARTEFATOS_PJE, _RE_INICIO_JURIDICO, norm


def remover_artefatos_pje(texto: str) -> str:
    return _RE_ARTEFATOS_PJE.sub('', texto)


def aprender_cabecalho(texto_sem_artefatos: str) -> list:
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

        ln_norm = norm(ln)
        tem_contato = bool(re.search(
            r'\d{2}[\s\-]?\d{4}[\s\-]?\d{4}'
            r'|@\w|www\.'
            r'|\.com\.br|\.adv\.br',
            ln_norm,
        ))
        eh_nome_escritorio = bool(re.match(r'^[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\-\.]{4,}$', ln))
        tem_endereco_escritorio = bool(
            re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a|sala)\b', ln_norm)
            and re.search(r'\d', ln)
            and (
                'cep' in ln_norm
                or re.search(r'\d{5}\s*[-]?\s*\d{3}', ln_norm)
                or (
                    re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a)\b.*\d', ln_norm)
                    and any(k in ln_norm for k in ('adv', 'escrit', 'oab', 'advogado', 'advogada'))
                )
            )
        )

        if tem_contato or eh_nome_escritorio or tem_endereco_escritorio:
            fingerprint.append(ln)

    return fingerprint


def remover_cabecalho_por_pagina(texto: str, fingerprint: list) -> str:
    if not fingerprint:
        return texto
    fp_set = {l.strip() for l in fingerprint if l.strip()}
    linhas_out = []
    for linha in texto.splitlines():
        if linha.strip() in fp_set:
            continue
        linhas_out.append(linha)
    return '\n'.join(linhas_out)


def strip_cabecalho_rodape(texto: str) -> str:
    if not texto:
        return texto

    texto = remover_artefatos_pje(texto)
    fingerprint = aprender_cabecalho(texto)

    if fingerprint:
        print(
            f'[TRIAGEM] cabecalho_fingerprint: {len(fingerprint)} linha(s) identificadas: '
            f'{fingerprint[:3]}'
        )
        texto = remover_cabecalho_por_pagina(texto, fingerprint)
    else:
        print('[TRIAGEM] cabecalho_fingerprint: nao identificado (texto inicia direto no conteudo juridico)')

    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()
```

<!-- pjeplus:delta:end -->

## Justificativa

O pré-processamento é coeso e independente; separá-lo reduz tamanho do módulo principal sem alterar a semântica da limpeza.[^1]

***

## Objetivo

Extrair a camada de coleta API/PDF/OCR para um módulo dedicado, preservando a renovação única de sessão em caso de 401, a busca da timeline com timeout por thread e o enriquecimento de `capa_dados` via endpoints de partes e processo. Essa é a parte mais longa e mais separável do arquivo.[^1]

## Arquivo(s) Alvo

- `triagem/coleta.py`


## Trecho Original

```python
# bloco atual em tr.py contendo:
# _ErroAutenticacao401
# _extrair_id_processo_da_url
# _eh_peticao_inicial
# _eh_certidao_distribuicao
# _eh_procuracao
# _eh_documento_identidade
# _parsear_capa
# _extrair_texto_pdf_api
# _listar_documentos_timeline
# _coletar_textos_processo
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import io
import re
import threading
from typing import Any, Dict

from api.variaveis import PjeApiClient, session_from_driver

from .constants import norm
from .preprocess import strip_cabecalho_rodape
from .utils import formatar_endereco_parte


class ErroAutenticacao401(Exception):
    """401 Unauthorized na API PJe — sessão expirada, necessário re-auth."""


def extrair_id_processo_da_url(url: str):
    if not url:
        return None
    match = re.search(r'/processo/(\d+)(?:/|$)', url)
    return match.group(1) if match else None


def eh_peticao_inicial(documento: dict) -> bool:
    tipo = norm(documento.get('tipo') or '')
    titulo = norm(documento.get('titulo') or '')
    return 'peticao inicial' in tipo or 'peticao inicial' in titulo


def eh_certidao_distribuicao(documento: dict) -> bool:
    tipo = norm(documento.get('tipo') or '')
    titulo = norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'certidao' in txt and 'distribuicao' in txt and 'redistribuicao' not in txt:
            return True
    return False


def eh_procuracao(documento: dict) -> bool:
    tipo = norm(documento.get('tipo') or '')
    titulo = norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'procuracao' in txt or 'procuração' in txt:
            return True
    return False


def eh_documento_identidade(documento: dict) -> bool:
    titulo = norm(documento.get('titulo') or '')
    palavras_chave = ['rg', 'cnh', 'identidade', 'cpf', 'passport', 'passaporte']
    return any(p in titulo for p in palavras_chave)


def parsear_capa(texto: str) -> dict:
    dados = {
        'numero_processo': None,
        'segredo_justica': None,
        'medida_urgencia': None,
        'rito_declarado': None,
        'valor_causa': None,
        'classe_judicial': None,
        'reclamante_nome': None,
        'reclamante_cpf': None,
        'reclamado_nome': None,
        'reclamado_cnpj': None,
        'distribuido_em': None,
    }
    n = norm(texto)

    m = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
    if m:
        dados['numero_processo'] = m.group(1)

    m = re.search(r'segredo de justic[aç][:\s]+(sim|n[aã]o)', n)
    if m:
        dados['segredo_justica'] = m.group(1).startswith('s')

    m = re.search(r'medida de urgencia[:\s]+(sim|n[aã]o)', n)
    if m:
        dados['medida_urgencia'] = m.group(1).startswith('s')

    m = re.search(r'classe judicial[:\s]+(.+?)(?:\n|\(|\r)', texto, re.IGNORECASE)
    if m:
        dados['classe_judicial'] = m.group(1).strip()
        cl = norm(dados['classe_judicial'])
        if 'sumarissimo' in cl:
            dados['rito_declarado'] = 'SUMARISSIMO'
        elif 'ordinario' in cl:
            dados['rito_declarado'] = 'ORDINARIO'

    m = re.search(r'valor da causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
    if m:
        try:
            dados['valor_causa'] = float(m.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            pass
    else:
        m2 = re.search(r'valor da causa', texto, re.IGNORECASE)
        if m2:
            trecho = texto[m2.end(): m2.end() + 400]
            mv = re.search(r'R\$\s*([\d\.,]+)', trecho)
            if mv:
                try:
                    dados['valor_causa'] = float(mv.group(1).replace('.', '').replace(',', '.'))
                except ValueError:
                    pass

    m = re.search(
        r'Partes[:\s]+(.+?)\s+-\s+([\d\.\-]+)\s+[Xx]\s+(.+?)\s+-\s+([\d\.\/\-]+)',
        texto
    )
    if m:
        dados['reclamante_nome'] = m.group(1).strip()
        dados['reclamante_cpf'] = re.sub(r'\D', '', m.group(2))
        dados['reclamado_nome'] = m.group(3).strip()
        dados['reclamado_cnpj'] = re.sub(r'\D', '', m.group(4))
    else:
        mr = re.search(r'RECLAMANTE\s*[\n\r]+\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][^\n\r]+)', texto)
        if mr:
            dados['reclamante_nome'] = mr.group(1).strip()
        md = re.search(r'RECLAMAD[AO]\s*[\n\r]+\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][^\n\r]+)', texto)
        if md:
            dados['reclamado_nome'] = md.group(1).strip()

    m = re.search(r'distribui[íi]d[oa]\s+em\s+(\d{1,2}/\d{2}/\d{4})', texto, re.IGNORECASE)
    if m:
        dados['distribuido_em'] = m.group(1)

    return dados


def extrair_texto_pdf_api(client: PjeApiClient, id_processo: str, id_doc: str) -> str:
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
            raise ErroAutenticacao401(f'401 Unauthorized — doc {id_doc}')
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
        if media >= 30:
            return texto_nativo

        try:
            import pathlib
            import shutil
            import pytesseract
            from pdf2image import convert_from_bytes

            poppler_path = None
            if shutil.which('pdftoppm'):
                poppler_path = str(pathlib.Path(shutil.which('pdftoppm')).parent)
            else:
                for candidato in [
                    r'D:\poppler\bin',
                    r'C:\poppler\bin',
                    r'C:\Program Files\poppler\bin',
                    r'C:\tools\poppler\bin',
                ]:
                    if pathlib.Path(candidato).exists():
                        poppler_path = candidato
                        break

            imagens = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)
            textos_ocr = [pytesseract.image_to_string(img, lang='por') for img in imagens]
            return '\n'.join(t for t in textos_ocr if t.strip())
        except ImportError:
            return texto_nativo
        except Exception as e:
            print(f'[TRIAGEM] OCR falhou ({id_doc}): {e}')
            return texto_nativo

    except ErroAutenticacao401:
        raise
    except Exception as e:
        print(f'[TRIAGEM] ERRO PDF {id_doc}: {e}')
        return ''


def listar_documentos_timeline(timeline: list) -> list:
    documentos = []
    for item in timeline or []:
        if not isinstance(item, dict):
            continue
        documentos.append(item)
        for anexo in item.get('anexos') or []:
            if isinstance(anexo, dict):
                documentos.append(anexo)
    return documentos


def coletar_textos_processo(driver) -> Dict[str, Any]:
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
        print('[TRIAGEM] [_coletar] ✓ Cliente API inicializado')
    except Exception as e:
        resultado['erro'] = f'falha ao montar cliente autenticado: {e}'
        print(f'[TRIAGEM] [_coletar] ✗ ERRO ao montar cliente: {resultado["erro"]}')
        return resultado

    reauth_done = [False]

    def extrair_com_reauth(id_doc: str) -> str:
        nonlocal client
        try:
            return extrair_texto_pdf_api(client, id_processo, id_doc)
        except ErroAutenticacao401:
            if reauth_done[^0]:
                raise
            print(f'[TRIAGEM] 401 doc {id_doc} — renovando sessão (tentativa única)...')
            reauth_done[^0] = True
            try:
                s2, h2 = session_from_driver(driver, grau=1)
                client = PjeApiClient(s2, h2, grau=1)
            except Exception as re_err:
                raise ErroAutenticacao401(f'falha ao renovar sessao: {re_err}') from re_err
            return extrair_texto_pdf_api(client, id_processo, id_doc)

    id_processo = extrair_id_processo_da_url(driver.current_url)
    if not id_processo:
        resultado['erro'] = f'id_processo nao encontrado na URL: {driver.current_url}'
        print(f'[TRIAGEM] [_coletar] ✗ ERRO: {resultado["erro"]}')
        return resultado

    print(f'[TRIAGEM] [_coletar] 2/6 ID processo extraído: {id_processo}')
    resultado['id_processo'] = id_processo

    partes_raw: dict = {}
    partes_endereco: dict = {}
    try:
        partes_raw = client.partes(id_processo) or {}
        qtd_a = len(partes_raw.get('ATIVO') or [])
        qtd_p = len(partes_raw.get('PASSIVO') or [])
        print(f'[TRIAGEM] partes_api: {qtd_a} ativo(s), {qtd_p} passivo(s)')

        url_endereco = client._url(f'/pje-comum-api/api/processos/id/{id_processo}/partes?retornaEndereco=true')
        r_endereco = client.sess.get(url_endereco, timeout=15)
        if r_endereco.ok:
            partes_endereco = r_endereco.json()
            print(f'[TRIAGEM] partes+endereco OK - {len(partes_endereco.get("PASSIVO") or [])} passivo(s)')
    except Exception as e_partes:
        print(f'[TRIAGEM] partes_api: falha ({e_partes})')

    try:
        associados = client.associados(id_processo) or []
        resultado['associados_sistema'] = associados
        if associados:
            print(f'[TRIAGEM] associados_sistema: {len(associados)} associado(s) encontrado(s)')
        else:
            print('[TRIAGEM] associados_sistema: nenhum')
    except Exception as e_assoc:
        print(f'[TRIAGEM] associados_sistema: falha ({e_assoc})')
        resultado['associados_sistema'] = []

    timeline = None
    timeline_erro = None

    def buscar_timeline():
        nonlocal timeline, timeline_erro
        try:
            print(f'[TRIAGEM] Iniciando busca de timeline com timeout (id={id_processo})')
            timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
            print('[TRIAGEM] Timeline recebida com sucesso')
        except Exception as e:
            timeline_erro = f'erro ao buscar timeline: {e}'
            print(f'[TRIAGEM] ERRO ao buscar timeline: {timeline_erro}')

    thread = threading.Thread(target=buscar_timeline, daemon=False)
    thread.start()
    thread.join(timeout=30)

    if thread.is_alive():
        print('[TRIAGEM] ⚠️ TIMEOUT ao buscar timeline — thread ainda ativa após 30s')
        resultado['erro'] = 'timeout ao buscar timeline (>30s)'
        return resultado

    if timeline_erro:
        resultado['erro'] = timeline_erro
        return resultado

    if not timeline:
        resultado['erro'] = 'timeline vazia ou indisponivel'
        print(f'[TRIAGEM] [_coletar] ✗ ERRO: {resultado["erro"]}')
        return resultado

    print('[TRIAGEM] [_coletar] 3/6 Timeline obtida, processando documentos...')
    documentos = listar_documentos_timeline(timeline)
    print(f'[TRIAGEM] [_coletar] Documentos processados: {len(documentos) or 0} itens')

    peticao = next((d for d in documentos if eh_peticao_inicial(d)), None)
    if not peticao:
        resultado['erro'] = 'peticao inicial nao localizada na timeline'
        print(f'[TRIAGEM] [_coletar] ✗ ERRO: {resultado["erro"]}')
        return resultado

    print('[TRIAGEM] [_coletar] 4/6 Petição inicial localizada, extraindo texto...')

    id_inicial = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
    if not id_inicial:
        resultado['erro'] = 'id do documento da peticao inicial nao disponivel'
        print(f'[TRIAGEM] [_coletar] ✗ ERRO: {resultado["erro"]}')
        return resultado

    try:
        resultado['texto_inicial'] = extrair_com_reauth(id_inicial)
    except ErroAutenticacao401 as e:
        resultado['erro'] = f'ERRO_CRITICO_401: peticao inicial — {e}'
        resultado['erro_critico'] = True
        print(f'[TRIAGEM] 🛑 ERRO CRÍTICO 401 — {resultado["erro"]}')
        return resultado

    chars_bruto = len(resultado['texto_inicial'])
    resultado['texto_inicial'] = strip_cabecalho_rodape(resultado['texto_inicial'])
    chars_limpo = len(resultado['texto_inicial'])
    print(
        f'[TRIAGEM] [_coletar] ✓ Texto da petição extraído: '
        f'{chars_bruto} chars bruto → {chars_limpo} chars após strip cabecalho/rodape '
        f'({chars_bruto - chars_limpo} removidos)'
    )

    anexos_raw = peticao.get('anexos') or []
    if not anexos_raw:
        anexos_raw = [d for d in documentos if d.get('idDocumentoPai') == peticao.get('id')]

    procuracoes = [a for a in anexos_raw if eh_procuracao(a)]
    docs_identidade = [a for a in anexos_raw if eh_documento_identidade(a)]
    print(f'[TRIAGEM] anexos: procuracao={len(procuracoes)} doc_identidade={len(docs_identidade)} (total={len(anexos_raw)})')

    anexos_extraidos = []
    for anx in procuracoes:
        id_anx = str(anx.get('id') or anx.get('idUnicoDocumento') or '')
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        try:
            texto_anx = extrair_com_reauth(id_anx) if id_anx else ''
        except ErroAutenticacao401 as e:
            resultado['erro'] = f'ERRO_CRITICO_401: procuracao {id_anx} — {e}'
            resultado['erro_critico'] = True
            print(f'[TRIAGEM] 🛑 ERRO CRÍTICO 401 — {resultado["erro"]}')
            return resultado
        print(f'[TRIAGEM] procuracao extraida: "{titulo_anx}" {len(texto_anx)} chars')
        anexos_extraidos.append({
            'titulo': titulo_anx,
            'tipo': (anx.get('tipo') or '').strip(),
            'texto': texto_anx,
        })

    for anx in docs_identidade:
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        print(f'[TRIAGEM] doc_identidade: "{titulo_anx}" (identificado, sem extracao)')
        anexos_extraidos.append({
            'titulo': titulo_anx,
            'tipo': (anx.get('tipo') or '').strip(),
            'texto': '',
        })

    resultado['anexos'] = anexos_extraidos

    data_pi = (peticao.get('data') or '')[:10]
    candidatas = [d for d in documentos if eh_certidao_distribuicao(d)]
    certidao = None
    if candidatas:
        certidao = next(
            (d for d in candidatas if (d.get('data') or '')[:10] == data_pi),
            candidatas[^0]
        )

    texto_capa = ''
    if certidao:
        id_cert = str(certidao.get('id') or certidao.get('idUnicoDocumento') or '')
        titulo_cert = (certidao.get('titulo') or certidao.get('tipo') or '(sem titulo)').strip()
        print(f'[TRIAGEM] certidao_distribuicao: localizada id={id_cert} titulo="{titulo_cert}"')
        if id_cert:
            try:
                texto_capa = extrair_com_reauth(id_cert)
            except ErroAutenticacao401 as e:
                resultado['erro'] = f'ERRO_CRITICO_401: certidao {id_cert} — {e}'
                resultado['erro_critico'] = True
                print(f'[TRIAGEM] 🛑 ERRO CRÍTICO 401 — {resultado["erro"]}')
                return resultado
            if texto_capa:
                print(f'[TRIAGEM] certidao_distribuicao: extracao OK chars={len(texto_capa)}')
            else:
                print('[TRIAGEM] certidao_distribuicao: ERRO - texto extraido vazio (PDF sem texto nativo e OCR indisponivel ou falhou)')
        else:
            print('[TRIAGEM] certidao_distribuicao: ERRO - id do documento nao disponivel na timeline')
    else:
        nomes = [norm(d.get('titulo') or d.get('tipo') or '') for d in documentos[:12]]
        print(f'[TRIAGEM] certidao_distribuicao: NAO LOCALIZADA - docs disponiveis (ate 12): {nomes}')

    resultado['texto_capa'] = texto_capa
    if texto_capa:
        resultado['capa_dados'] = parsear_capa(texto_capa)
    else:
        resultado['capa_dados'] = {}
        print('[TRIAGEM] capa_dados: nao extraidos (certidao ausente ou vazia) - B13/rito indisponivel')

    if partes_raw:
        ativos = partes_raw.get('ATIVO') or []
        passivos = partes_raw.get('PASSIVO') or []

        if ativos:
            doc_ativo = re.sub(r'\D', '', ativos[^0].get('documento') or '')
            resultado['capa_dados']['reclamante_nome'] = ativos[^0].get('nome', '').strip()
            if len(doc_ativo) == 11:
                resultado['capa_dados']['reclamante_cpf'] = doc_ativo

        if passivos:
            reclamados_lista = []
            reclamadas_sem_endereco = []
            reclamadas_com_dom_elet = 0

            for p in passivos:
                doc = re.sub(r'\D', '', p.get('documento') or '')
                reclamados_lista.append({'nome': p.get('nome', '').strip(), 'cpfcnpj': doc})

            for parte in (partes_endereco.get('PASSIVO') or []):
                nome_parte = parte.get('nome', '').strip()
                if parte.get('enderecoDesconhecido', False):
                    reclamadas_sem_endereco.append(nome_parte)

                id_parte_pj = str(
                    parte.get('idPessoa') or parte.get('id') or
                    parte.get('idParticipante') or parte.get('idParte') or ''
                )
                dom_via_api = client.domicilio_eletronico(id_parte_pj) if id_parte_pj else None
                dom_flag_raw = parte.get('domicilioEletronico') or parte.get('possuiDomicilioEletronico')
                tem_domicilio = dom_via_api if dom_via_api is not None else (dom_flag_raw is True)
                if tem_domicilio:
                    reclamadas_com_dom_elet += 1

                endereco = parte.get('endereco') or {}
                cep_raw = endereco.get('nroCep') or ''
                cep = re.sub(r'[^\d]', '', cep_raw) if cep_raw else None
                endereco_desc = formatar_endereco_parte(endereco)
                dom_status = 'SIM' if tem_domicilio else ('NAO' if dom_via_api is not None else f'flag={dom_flag_raw}')
                print(f'[TRIAGEM] passivo: {nome_parte} | domicilio={dom_status} | cep={cep or "(sem)"} | end={endereco_desc[:60] or "(sem)"}')

                if cep and len(cep) == 8:
                    doc_parte = re.sub(r'\D', '', parte.get('documento') or '')
                    for item in reclamados_lista:
                        if item.get('cpfcnpj') == doc_parte or item.get('nome') == nome_parte:
                            item['cep'] = cep
                            if endereco_desc:
                                item['endereco'] = endereco_desc
                            break

            resultado['capa_dados']['reclamados'] = reclamados_lista
            resultado['capa_dados']['reclamadas_sem_endereco'] = reclamadas_sem_endereco
            resultado['capa_dados']['reclamadas_com_dom_elet'] = reclamadas_com_dom_elet

            prim = reclamados_lista[^0]
            resultado['capa_dados']['reclamado_nome'] = prim['nome']
            if len(prim['cpfcnpj']) == 14:
                resultado['capa_dados']['reclamado_cnpj'] = prim['cpfcnpj']
            elif len(prim['cpfcnpj']) == 11:
                resultado['capa_dados']['reclamado_cpf'] = prim['cpfcnpj']

    try:
        proc_dados = client.processo_por_id(id_processo) or {}
        juizo_digital = proc_dados.get('juizoDigital')
        if isinstance(juizo_digital, str):
            juizo_digital = juizo_digital.lower() == 'true'
        elif juizo_digital is not None:
            juizo_digital = bool(juizo_digital)
        resultado['capa_dados']['juizo_digital'] = juizo_digital

        valor_api = (
            proc_dados.get('valorCausa')
            or proc_dados.get('valorDaCausa')
            or proc_dados.get('valor')
        )
        if valor_api is not None:
            try:
                resultado['capa_dados']['valor_causa'] = float(valor_api)
            except (TypeError, ValueError):
                pass
    except Exception as e_api:
        print(f'[TRIAGEM] valor_causa API: falha ({e_api})')

    cd = resultado['capa_dados']
    print(
        f'[TRIAGEM] capa_dados: valor_causa={cd.get("valor_causa")} '
        f'rito={cd.get("rito_declarado")} juizo_digital={cd.get("juizo_digital")} '
        f'distribuido_em={cd.get("distribuido_em")}'
    )
    print('[TRIAGEM] [_coletar] 6/6 ✓ Coleta de textos concluída com sucesso')
    return resultado
```

<!-- pjeplus:delta:end -->

## Justificativa

Separa claramente infraestrutura de coleta da camada de regra, reduzindo tamanho do núcleo e preservando o comportamento já implementado no arquivo original.[^1]

***

## Objetivo

Extrair todas as regras de negócio B1–B14 para um módulo próprio e eliminar as duplicações presentes no arquivo original, mantendo apenas **uma** versão funcional de cada checagem. O `tr.py` atual contém duplicações literais de `_checar_tutela`, `_checar_reclamadas`, `_checar_partes` e helpers relacionados, o que aumenta risco de regressão silenciosa.[^1]

## Arquivo(s) Alvo

- `triagem/regras.py`


## Trecho Original

```python
# múltiplos blocos B1–B14 hoje misturados e parcialmente duplicados em tr.py
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import re
from typing import Any, Dict, List

from .constants import (
    ALCADA,
    INTERVALOS_CEP_ZONA_SUL,
    RITO_SUMARISSIMO_MAX,
    _CNPJ_CONTEXTOS,
    _CPF_CONTEXTOS,
    _CEP_TAG_PRESTACAO,
    _CEP_TAG_RECLAMADA,
    _CEP_TAG_TERRITORIAL,
    _RE_CNPJ_NUM,
    _RE_CPF_NUM,
    _TERMOS_ID_BODY,
    _TERMOS_ID_TITULO,
    _TERMOS_PROC_BODY,
    _TERMOS_PROC_TITULO,
    norm,
)
from .utils import cep_tag, extrair_numeros_contextuais, extrair_palavras_reclamada, pag_contexto


def checar_procuracao_e_identidade(anexos: List[Dict[str, Any]], nome_reclamante: str = '') -> str:
    proc_via = None
    id_via = None

    for anx in anexos:
        tref = norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
        tbody = norm(anx.get('texto') or '')
        tnome = (anx.get('titulo') or anx.get('tipo') or '').strip()

        if proc_via is None:
            if any(t in tref for t in _TERMOS_PROC_TITULO):
                proc_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_PROC_BODY):
                proc_via = f'conteudo:"{tnome or "(sem titulo)"}"'

        if id_via is None:
            if any(t in tref for t in _TERMOS_ID_TITULO):
                id_via = 'titulo'
            elif tbody and any(t in tbody for t in _TERMOS_ID_BODY):
                id_via = f'conteudo:"{tnome or "(sem titulo)"}"'

    extra_proc = ''
    if proc_via and nome_reclamante:
        nome_norm = norm(nome_reclamante)
        for anx in anexos:
            tref = norm(f"{anx.get('titulo', '')} {anx.get('tipo', '')}")
            tbody = norm(anx.get('texto') or '')
            if (
                any(t in tref for t in _TERMOS_PROC_TITULO)
                or (tbody and any(t in tbody for t in _TERMOS_PROC_BODY))
            ):
                sobrenome = nome_norm.split()[-1] if nome_norm.split() else ''
                if sobrenome and len(sobrenome) > 3 and sobrenome in tbody:
                    extra_proc = ' [nome reclamante localizado na procuracao]'
                else:
                    extra_proc = ' [ATENCAO: nome reclamante nao localizado na procuracao]'
                break

    tem_proc = proc_via is not None
    tem_id = id_via is not None

    if tem_proc and tem_id:
        return (
            f'B1_DOCS: OK - procuracao ({proc_via}){extra_proc} '
            f'e doc identidade ({id_via}) presentes'
        )
    if not tem_proc and not tem_id:
        return 'B1_DOCS: ALERTA - faltam procuracao e copia de documento de identidade em anexos separados'
    if not tem_proc:
        return f'B1_DOCS: ALERTA - falta procuracao em anexo (doc identidade: {id_via})'
    return f'B1_DOCS: ALERTA - falta copia de documento de identidade em anexo (procuracao: {proc_via}{extra_proc})'


def checar_cep(texto: str, capa_dados: dict) -> str:
    matches = list(re.finditer(r'(?<!\d)(\d{2})\D?(\d{3})\D?(\d{3})(?!\d)', texto))
    ceps_api = [r.get('cep') for r in (capa_dados.get('reclamados') or []) if r.get('cep')]
    palavras_reclamada = extrair_palavras_reclamada(capa_dados)

    cep_fone = re.compile(r'\b(?:telefone|fone|tel|fax|whats|whatsapp)\b', re.IGNORECASE)
    candidatos = []

    for ordem, m in enumerate(matches):
        num = int(m.group(1) + m.group(2) + m.group(3))
        fmt = f"{m.group(1)}.{m.group(2)}-{m.group(3)}"
        inicio = max(0, m.start() - 240)
        fim = min(len(texto), m.end() + 240)
        ctx = texto[inicio:fim]
        ctx_norm = norm(ctx)
        tag = cep_tag(ctx_norm, palavras_reclamada)
        explicit = bool(
            re.search(r'\bCEP\s*[:\-]?\s*$', texto[max(0, m.start() - 12):m.start()], re.IGNORECASE)
        )
        endereco_context = bool(re.search(
            r'\bendereco\b|\blogradouro\b|\bbairro\b|\bmunicipio\b|\buf\b|\bnumero\b|\bcomplemento\b',
            ctx_norm
        )) or any(t in ctx_norm for t in (
            'ultimo local', 'prestacao de servico', 'local de trabalho', 'cnpj', 'filial', 'estabelecimento'
        ))
        telefone_proximo = bool(cep_fone.search(ctx_norm))
        candidatos.append((
            tag,
            0 if explicit else 1,
            0 if endereco_context else 1,
            2 if telefone_proximo else 0,
            ordem,
            num,
            fmt,
        ))

    if ceps_api:
        cep_raw = ceps_api[^0]
        if len(cep_raw) == 8 and cep_raw.isdigit():
            cep_num = int(cep_raw)
            cep_fmt = f"{cep_raw[:2]}.{cep_raw[2:5]}-{cep_raw[5:]}"
            label = 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)'
            for lo, hi in INTERVALOS_CEP_ZONA_SUL:
                if lo <= cep_num <= hi:
                    return f"B2_CEP: OK - {cep_fmt} ({cep_num}) no intervalo {lo}-{hi} Zona Sul [{label}]"

    candidatos = [c for c in candidatos if c[^3] == 0 or c[^1] == 0]
    if not candidatos:
        norm_texto = norm(texto)
        termos_estritos = [
            'competencia territorial', 'competencia funcional', 'foro competente',
            'art. 651', 'art 651', 'artigo 651',
            'ultimo local', 'prestacao de servico', 'local de trabalho'
        ]
        if any(t in norm_texto for t in termos_estritos):
            return 'B2_CEP: ALERTA - nenhum CEP de prestacao de servicos identificado no contexto relevante (CEP da reclamada ignorado por regra)'
        if ceps_api:
            cep_raw = ceps_api[^0]
            if len(cep_raw) == 8 and cep_raw.isdigit():
                cep_num = int(cep_raw)
                cep_fmt = f"{cep_raw[:2]}.{cep_raw[2:5]}-{cep_raw[5:]}"
                label = 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)'
                return (
                    f'B2_CEP: ALERTA - Incompetencia Territorial - '
                    f'CEP {cep_fmt} ({cep_num}) fora dos intervalos Zona Sul [{label}]'
                )
        return 'B2_CEP: ALERTA - nenhum CEP de prestacao de servicos ou reclamada identificado (CEP do reclamante ignorado por regra)'

    candidatos.sort(key=lambda x: (x[^0], x[^1], x[^2], x[^3], x[^4]))
    best_tag, _, _, _, _, cep_num, cep_fmt = candidatos[^0]

    tag_label = {
        _CEP_TAG_TERRITORIAL: 'competencia territorial (art.651 CLT)',
        _CEP_TAG_PRESTACAO: 'ultimo local de prestacao de servicos (art.651 CLT)',
        _CEP_TAG_RECLAMADA: 'sede da reclamada - referencia subsidiaria (art.651 CLT, ultimo local nao indicado explicitamente)',
        4: 'generico',
        5: 'reclamante',
    }
    label = tag_label[best_tag]

    termos_territ = [
        'competencia territorial', 'competencia funcional', 'foro competente',
        'art. 651', 'art 651', 'artigo 651',
        'ultimo local', 'prestacao de servico', 'local de trabalho'
    ]
    norm_texto = norm(texto)
    termos_presentes = [t for t in termos_territ if t in norm_texto]
    sufixo_territ = ''
    if termos_presentes and best_tag not in (_CEP_TAG_TERRITORIAL, _CEP_TAG_PRESTACAO):
        sufixo_territ = (
            f' | NOTA: peticao menciona termos de competencia territorial '
            f'({termos_presentes[^0]}) mas CEP nao foi localizado nesse contexto - '
            f'verificar endereco indicado na secao de competencia/prestacao'
        )

    for lo, hi in INTERVALOS_CEP_ZONA_SUL:
        if lo <= cep_num <= hi:
            return f'B2_CEP: OK - {cep_fmt} ({cep_num}) no intervalo {lo}-{hi} Zona Sul [{label}]{sufixo_territ}'
    return f'B2_CEP: ALERTA - Incompetencia Territorial - CEP {cep_fmt} ({cep_num}) fora dos intervalos Zona Sul [{label}]{sufixo_territ}'


def checar_partes(texto: str, capa_dados: dict) -> List[str]:
    linhas = []
    texto_norm = norm(texto)
    corte_preliminarmente = texto_norm.find('preliminarmente')
    contexto_partes = texto_norm[:corte_preliminarmente] if corte_preliminarmente != -1 else texto_norm[:2600]

    nome_rec = capa_dados.get('reclamante_nome') or ''
    cpf_rec = capa_dados.get('reclamante_cpf') or ''
    if nome_rec:
        sufixo = f' CPF={cpf_rec}' if cpf_rec else ''
        rec_info = f' - reclamante={nome_rec[:60]}{sufixo}'
    else:
        m = re.search(
            r'RECLAMANTE[:\s]+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-z\s\.]+?)(?:\s*[-–]\s*|\s*CPF|\n)',
            texto[:3000]
        )
        if m:
            rec_info = f' - reclamante={m.group(1).strip()[:60]}'
        else:
            rec_info = ''
            linhas.append('B3_PARTES: ALERTA - reclamante nao identificado na capa')

    m_nasc = re.search(r'nascid[ao][:\s]+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', texto_norm)
    if m_nasc:
        try:
            ano_nasc = int(m_nasc.group(3))
            data_dist = capa_dados.get('distribuido_em') or ''
            m_ano = re.search(r'(\d{4})$', data_dist)
            ano_ref = int(m_ano.group(1)) if m_ano else 2026
            if (ano_ref - ano_nasc) < 18:
                linhas.append(
                    f'B3_PARTES: ALERTA - parte menor de idade '
                    f'(nasc {m_nasc.group(3)}) - incluir MPT custos legis'
                )
        except Exception:
            pass

    re_pjdp = re.compile(r'\b(municipio|prefeitura|uniao\s+federal|autarquia|fazenda\s+p[ue]blica|estado\b(?!\s+de\b))\b')
    re_addr_label = re.compile(r'municipio\s*:', re.IGNORECASE)
    re_estado_label = re.compile(r'estado\s*:', re.IGNORECASE)
    re_privado = re.compile(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado')

    pjdp_encontrado = False
    for m_pjdp in re_pjdp.finditer(contexto_partes):
        trecho = contexto_partes[max(0, m_pjdp.start() - 80): m_pjdp.end() + 20]
        if re_addr_label.search(trecho) or re_estado_label.search(trecho):
            continue
        trecho_amplo = contexto_partes[max(0, m_pjdp.start() - 200): m_pjdp.end() + 50]
        if re_privado.search(trecho_amplo):
            continue
        pjdp_encontrado = True
        linhas.append(
            f'B3_PARTES: ALERTA - PJDP no polo passivo (rito ordinario obrigatorio); '
            f'gatilho detectado: {m_pjdp.group(1)}'
        )
        break

    if not any('ALERTA' in l for l in linhas):
        linhas.append(f'B3_PARTES: OK{rec_info}')
    return linhas


def checar_segredo(texto: str, capa_dados: dict) -> str:
    texto_norm = norm(texto)
    tem_pedido_no_texto = bool(re.search(r'segredo\s+de\s+justi[cç]a|tramita[cç][aã]o\s+sigilosa', texto_norm))
    segredo_na_capa = capa_dados.get('segredo_justica')
    if segredo_na_capa is True and not tem_pedido_no_texto:
        return 'B4_SEGREDO: ALERTA - certidão indica segredo mas não há requerimento fundamentado na petição'
    if tem_pedido_no_texto:
        fund = bool(re.search(r'art\.?\s*189', texto_norm))
        suf = 'com art. 189 CPC' if fund else 'sem fundamentacao (art. 189 CPC ausente)'
        return f'B4_SEGREDO: ALERTA - pedido de segredo de justica {suf}'
    return 'B4_SEGREDO: OK'


def checar_reclamadas(texto: str, capa_dados: dict) -> List[str]:
    linhas = []
    reclamados_api = capa_dados.get('reclamados') or []

    sem_endereco = capa_dados.get('reclamadas_sem_endereco') or []
    if sem_endereco:
        linhas.append(
            f'B5_RECLAMADAS: ALERTA - {len(sem_endereco)} reclamada(s) SEM ENDEREÇO: '
            f'{", ".join(sem_endereco[:3])}'
        )

    com_dom = capa_dados.get('reclamadas_com_dom_elet', 0) or 0
    total_reclamadas = len(reclamados_api)
    if total_reclamadas > 0:
        if com_dom > 0:
            linhas.append(f'B5_RECLAMADAS: OK - {com_dom}/{total_reclamadas} reclamada(s) com DOMICÍLIO ELETRÔNICO')
        else:
            linhas.append('B5_RECLAMADAS: ALERTA - NENHUMA reclamada com domicílio eletrônico habilitado')

    if not reclamados_api:
        linhas.append('B5_RECLAMADAS: ALERTA - dados de partes nao disponiveis via API')
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
            linhas.append(f'B5_RECLAMADAS: OK - {nome} CNPJ {fmt} ({tipo}){sufixo_info}')
        elif len(doc) == 11:
            linhas.append(f'B5_RECLAMADAS: OK - {nome} pessoa fisica CPF={doc}{sufixo_info}')
        else:
            linhas.append(f'B5_RECLAMADAS: ALERTA - {nome} sem CPF/CNPJ valido na API{sufixo_info}')

    cnpjs = [r['cpfcnpj'] for r in reclamados_api if len(r.get('cpfcnpj', '')) == 14]
    filiais = [c for c in cnpjs if c[8:12] != '0001']
    matrizes = {c[:8] for c in cnpjs if c[8:12] == '0001'}
    for f in filiais:
        if f[:8] not in matrizes:
            linhas.append(f'B5_RECLAMADAS: ALERTA - filial {f[:8]}/... sem referencia a matriz')
            break

    if not linhas:
        cnpjs_ctx = extrair_numeros_contextuais(texto, _RE_CNPJ_NUM, _CNPJ_CONTEXTOS)
        cpfs_ctx = extrair_numeros_contextuais(texto, _RE_CPF_NUM, _CPF_CONTEXTOS)
        if cnpjs_ctx or cpfs_ctx:
            linhas.append('B5_RECLAMADAS: INFO - identificadores encontrados apenas no texto da petição')
        else:
            linhas.append('B5_RECLAMADAS: ALERTA - nenhum CNPJ/CPF contextual encontrado')

    return linhas


def checar_tutela(texto: str, capa_dados: dict) -> str:
    texto_norm = norm(texto)
    idx = max(
        texto_norm.rfind('pedidos'),
        texto_norm.rfind('dos pedidos'),
        texto_norm.rfind('requerimentos'),
        len(texto_norm) - 4000
    )
    sec_norm = texto_norm[max(0, idx):]
    termos = [
        'tutela de urgencia', 'tutela antecipada', 'tutela provisoria',
        'tutela de evidencia', 'tutela cautelar', 'medida liminar',
        'medida cautelar', 'medida de urgencia', 'tutela liminar',
        'art. 300', 'art. 305', 'art. 311',
    ]
    for t in termos:
        pos = sec_norm.find(t)
        if pos != -1:
            ctx = pag_contexto(texto, max(0, idx) + pos, janela=300)
            return f'B6_TUTELA: ALERTA - pedido tutela provisoria ({t}) - encaminhar para despacho\n {ctx}'
    if capa_dados.get('medida_urgencia') is True:
        return 'B6_TUTELA: ALERTA - certidão indica medida de urgência mas termo não localizado nos pedidos'
    return 'B6_TUTELA: OK'


def checar_digital(texto: str, capa_dados: dict) -> str:
    texto_norm = norm(texto)
    pedido_digital = bool(re.search(
        r'(ju[ií]zo\s*100%?\s*digital|ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'manifesta[cç][aã]o\s+de\s+ades[aã]o\s+ao\s+ju[ií]zo\s*100%?\s*digital|'
        r'requer(?:e|ido)?\s+o\s+ju[ií]zo\s*100%?\s*digital)',
        texto_norm
    ))
    if not pedido_digital:
        return 'B7_DIGITAL: OK - sem pedido expresso de Juizo 100% Digital na peticao'

    processo_digital = capa_dados.get('juizo_digital')
    if processo_digital is True:
        return 'B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado e processo ja marcado na API'
    if processo_digital is False:
        return 'B7_DIGITAL: ALERTA - pedido expresso de Juizo 100% Digital identificado, mas processo nao marcado na API'
    return 'B7_DIGITAL: OK - pedido expresso de Juizo 100% Digital identificado, mas marcação do processo nao confirmada na API'


def checar_pedidos_liquidados(texto: str) -> str:
    re_skip_pedido = re.compile(
        r'atribu[ií]|n[aã]o inferior|valor da causa|valor atribu[ií]do|'
        r'n[aã]o deve ser utiliz|fator limitador|estimativa|base de calculo',
        re.IGNORECASE
    )
    re_verba_header = re.compile(
        r'\b(saldo.sal[aá]rio|aviso\s*pr[eé]vio|f[eé]rias|fgts|'
        r'multa\s*(art|do)?\s*(art\.?\s*4[^67][^67]|dos\s*40)?|dano\s*moral|gorjeta|'
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
        ln = norm(ls)

        if len(ls) < 70 and 'r$' not in ln and re_verba_header.search(ln):
            secao = ls
            continue

        if re_skip_pedido.search(ln):
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
            itens.append(f' {prefixo}{ctx}')

    out = []
    if not itens:
        out.append('B8_PEDIDOS: ALERTA - pedidos sem valores liquidados identificados')
    else:
        out.append(f'B8_PEDIDOS: OK - {len(itens)} pedido(s) com valor:')
        out.extend(itens[-3:])
    return '\n'.join(out)


def checar_pessoa_fisica(texto: str, capa_dados: dict = None) -> str:
    reclamados_api = (capa_dados or {}).get('reclamados') or []
    if not reclamados_api:
        return 'B9_PESSOA_FIS: ALERTA - dados de partes nao disponiveis via API'

    pessoas_fisicas = [r for r in reclamados_api if len(r.get('cpfcnpj', '')) == 11]
    if not pessoas_fisicas:
        return 'B9_PESSOA_FIS: OK - sem pessoa fisica no polo passivo'

    nomes = ', '.join(r['nome'] for r in pessoas_fisicas)
    fund_termos = ['responsabilidade pessoal', 'desconsideracao', 'socio', 'administrador', 'sucessao', 'grupo economico']
    if any(t in norm(texto) for t in fund_termos):
        return f'B9_PESSOA_FIS: OK - pessoa fisica com fundamentacao juridica ({nomes})'
    return f'B9_PESSOA_FIS: ALERTA - pessoa fisica no polo passivo sem fundamentacao clara ({nomes})'


def checar_litispendencia(texto: str, associados_sistema: list = None) -> str:
    termos_juris = [
        'acordao', 'ementa', 'jurisprudencia', 'precedente', 'relator', 'turma',
        'tst', 'stj', 'stf', 'dejt', 'sumula', 'oj', 'rot', 'rorsum', 'rr', 'airr'
    ]
    padrao_processo = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos_reais = []

    for linha in texto.split('\n'):
        norm_linha = norm(linha)
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
            partes_alerta.append(f'Prevenção detectada no sistema - processo {num} (também mencionado na petição)')
        else:
            partes_alerta.append(f'Prevenção detectada no sistema - processo {num}')

    apenas_peticao = [n for n in unicos_peticao if n not in nums_sistema]
    if nums_sistema:
        if apenas_peticao:
            outros = ', '.join(apenas_peticao[:4])
            partes_alerta.append(
                f'menção a outros processos na petição ({outros}) - verificar litispendência/prevenção/coisa julgada'
            )
    elif len(unicos_peticao) > 1:
        outros = ', '.join(unicos_peticao[1:4])
        partes_alerta.append(
            f'menção a outros processos na petição ({outros}) - verificar litispendência/prevenção/coisa julgada'
        )

    if not partes_alerta:
        texto_norm = norm(texto)
        for t in ['acao anterior', 'processo anterior', 'ja ajuizou', 'litispendencia', 'coisa julgada', 'acordo nao homologado']:
            pos = texto_norm.find(t)
            if pos != -1:
                ctx = pag_contexto(texto, pos, janela=200)
                partes_alerta.append(f"possivel '{t}'\n {ctx}")
                break

    if partes_alerta:
        corpo = '\n'.join(partes_alerta)
        return f'B10_LITISPEND: ALERTA - {corpo}'
    return 'B10_LITISPEND: OK'


def checar_responsabilidade(texto: str, capa_dados: dict = None) -> List[str]:
    re_reclamada_header = re.compile(
        r'(?:\d+[ºo°]?\.?\s*|primeira\s+|segunda\s+|terceira\s+|quarta\s+)RECLAMAD[AO]\b'
        r'|RECLAMAD[AO]\s*[:\—–]',
        re.IGNORECASE,
    )

    reclamados_api = (capa_dados or {}).get('reclamados') or []
    if reclamados_api:
        n_rec = len(reclamados_api)
    else:
        capa = texto[:4000]
        n_rec = len(re_reclamada_header.findall(capa))

    texto_norm = norm(texto)

    if re.search(r'responsabilidade\s+subsidiaria|subsidiariamente\s+responsaveis?', texto_norm):
        tipo_resp = 'subsidiaria'
    elif re.search(r'responsabilidade\s+solidaria|solidariamente\s+(?:responsaveis?|condena)', texto_norm):
        tipo_resp = 'solidaria'
    else:
        tipo_resp = 'subsidiaria/solidaria'

    if n_rec <= 1:
        if tipo_resp != 'subsidiaria/solidaria' or re.search(
            r'responsabilidade\s+(subsidiaria|solidaria)'
            r'|solidariamente\s+(?:responsaveis?|condena)'
            r'|subsidiariamente\s+responsaveis?',
            texto_norm
        ):
            return [f'B11_RESPONSAB: ALERTA - 1 reclamada mas pedido de responsabilidade {tipo_resp} (autuacao incorreta?)']
        return ['B11_RESPONSAB: OK - unica reclamada, nao aplicavel']

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
        texto_norm
    ))

    if not tem_pedido:
        for m in re.finditer(r'(?:primeira|segunda|terceira|demais|todas?\s+as?)\s+reclamad[ao]', texto_norm):
            janela = texto_norm[max(0, m.start() - 400): m.end() + 400]
            if re.search(r'responsabilid|devedora|solidar|subsidiar|prestadora\s+de\s+servi[cç]|tomadora', janela):
                tem_pedido = True
                break

    tem_causa = bool(re.search(
        r'tomador\s+de\s+servico|terceirizacao|prestacao\s+de\s+servico'
        r'|grupo\s+economico|subempreitada|terceirizado'
        r'|prestadora\s+(?:de\s+)?servicos?'
        r'|s[oó]ci[ao][- ]proprietari|s[oó]ci[ao][- ]gerente'
        r'|dono\s+da\s+empresa|proprietari[ao]\s+d[ao]'
        r'|empres[ao]\s+d[ao]\s+grupo'
        r'|administrador[ao]|s[oó]ci[ao]\b',
        texto_norm
    ))

    if not tem_pedido:
        return [f'B11_RESPONSAB: ALERTA - {n_rec} reclamadas sem pedido de responsabilidade subsidiaria/solidaria (emenda necessaria)']
    if not tem_causa:
        return [f'B11_RESPONSAB: ALERTA - pedido de responsabilidade {tipo_resp} sem causa de pedir explicita ({n_rec} reclamadas)']
    return [f'B11_RESPONSAB: OK - {n_rec} reclamadas com pedido de responsabilidade {tipo_resp} e causa de pedir']


def checar_endereco_reclamante(texto: str) -> List[str]:
    linhas = []
    texto_norm = norm(texto)

    m = re.search(
        r'(residente|domiciliad[ao])[^\.]{0,300}?'
        r'([a-záàâãéèêíïóôõöúçñ][a-záàâãéèêíïóôõöúçñ\s]+)\s*[-/]\s*([a-z]{2})\b',
        texto_norm
    )
    if m:
        cidade = m.group(2).strip()
        estado = m.group(3)
        cidade_uf = f'{cidade}/{estado}'
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
            linhas.append('B12_ENDERECO: OK - reclamante reside em Grande Sao Paulo/SP')
        else:
            linhas.append(f'B12_ENDERECO: ALERTA - reclamante em {cidade_uf} (fora SP) - verificar audiencia virtual')
    else:
        linhas.append('B12_ENDERECO: INFO - endereco do reclamante nao identificado')

    termos_aud = [
        'audiencia virtual', 'audiencia telepresencial', 'videoconferencia',
        'audiencia hibrida', 'audiencia online', 'telepresencialmente',
        'por videoconferencia',
    ]
    encontrado = next((t for t in termos_aud if t in texto_norm), None)
    if encontrado:
        linhas.append(f'B12_AUD_VIRTUAL: ALERTA - pedido de {encontrado} - verificar compatibilidade com pauta da vara')
    else:
        linhas.append('B12_AUD_VIRTUAL: OK - sem pedido de audiencia virtual/telepresencial')
    return linhas


def checar_rito(texto: str, capa_dados: dict) -> str:
    valor = capa_dados.get('valor_causa')
    if valor is None:
        m_valor = re.search(r'valor\s+da\s+causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
        if not m_valor:
            return 'B13_RITO: ALERTA - valor da causa nao identificado'
        try:
            valor = float(m_valor.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            return 'B13_RITO: ALERTA - valor da causa em formato invalido'

    rito_dec = capa_dados.get('rito_declarado')
    if not rito_dec:
        m_rito = re.search(r'RITO[:\s]+(SUMAR[IÍ]SSIMO|ORDIN[ÁA]RIO)', texto[:3000], re.IGNORECASE)
        if m_rito:
            rito_dec = 'SUMARISSIMO' if re.search(r'sumar', norm(m_rito.group(1))) else 'ORDINARIO'

    texto_norm = norm(texto)
    pub_ctx = texto_norm[:2600]
    pub_ok = False
    for m_pub in re.finditer(r'\b(municipio|estado\s+de|uniao\s+federal|autarquia|fazenda\s+p[ue]blica)\b', pub_ctx):
        t = pub_ctx[max(0, m_pub.start()-80): m_pub.end()+20]
        if re.search(r'municipio\s*:', t, re.IGNORECASE) or re.search(r'estado\s*:', t, re.IGNORECASE):
            continue
        t2 = pub_ctx[max(0, m_pub.start()-200): m_pub.end()+50]
        if re.search(r'pessoa\s+juridica\s+d[oe]\s+direito\s+privado', t2):
            continue
        pub_ok = True
        break

    if pub_ok:
        rito_correto = 'ORDINARIO'
        motivo = 'PJDP no polo passivo (art. 852-A §1 CLT)'
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
        return f'B13_RITO: INFO - rito nao identificado na capa; calculado: {rito_correto} ({motivo})'
    if rito_dec == rito_correto or (rito_correto == 'ALCADA' and rito_dec == 'SUMARISSIMO'):
        return f'B13_RITO: OK - {rito_dec} compativel ({motivo})'
    return f'B13_RITO: ALERTA - rito declarado {rito_dec} incompativel; correto: {rito_correto} ({motivo})'


def checar_art611b(texto: str) -> str:
    for linha in texto.splitlines():
        if re.search(r'art\.?\s*611-?B', linha, re.IGNORECASE):
            if re.search(r'clt|coletiv', linha, re.IGNORECASE):
                return 'B14_ART611B: ALERTA - mencao art. 611-B CLT - colocar lembrete no processo'
    return 'B14_ART611B: OK'
```

<!-- pjeplus:delta:end -->

## Justificativa

Concentra toda a inteligência da triagem em um módulo temático único e elimina as duplicações que hoje tornam o comportamento ambíguo no `tr.py`.[^1]

***

## Objetivo

Extrair a montagem final da resposta e o orquestrador `triagem_peticao` para um módulo enxuto, responsável apenas por dependências opcionais, coleta, execução das regras e ordenação da saída. O fluxo principal atual chama `_coletar_textos_processo`, executa B1–B14 e organiza `[COMPETENCIA]`, `[Alertas]` e `[ITENS OK]`.[^1]

## Arquivo(s) Alvo

- `triagem/service.py`


## Trecho Original

```python
# bloco final "FUNÇÃO PRINCIPAL" atualmente no fim de tr.py
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
import logging
from typing import Any, Dict

from .coleta import coletar_textos_processo
from .regras import (
    checar_art611b,
    checar_cep,
    checar_digital,
    checar_endereco_reclamante,
    checar_litispendencia,
    checar_partes,
    checar_pedidos_liquidados,
    checar_pessoa_fisica,
    checar_procuracao_e_identidade,
    checar_reclamadas,
    checar_responsabilidade,
    checar_rito,
    checar_segredo,
    checar_tutela,
)
from .utils import conteudo_saida_item, formatar_competencia_saida, formatar_saida_item, itens_lista

logging.getLogger('pdfminer').setLevel(logging.ERROR)


def triagem_peticao(driver) -> str:
    """
    Executa triagem completa de petição inicial trabalhista.
    Driver deve estar autenticado na página do processo (detalhe) no PJe.
    Retorna texto simples, máximo 8000 chars.
    Ordem de saída: competencia → alertas → itens OK.
    """
    pytesseract_ok = True
    pdf2image_ok = True

    try:
        import pytesseract  # noqa: F401
    except ImportError:
        pytesseract_ok = False
        print('[TRIAGEM] ⚠️ pytesseract não instalado — OCR indisponível (documentos de identidade podem retornar vazio)')

    try:
        import pdf2image  # noqa: F401
    except ImportError:
        pdf2image_ok = False
        print('[TRIAGEM] ⚠️ pdf2image não instalado — OCR indisponível')

    if not (pytesseract_ok and pdf2image_ok):
        print('[TRIAGEM] ℹ️ Para extrair texto de documentos digitalizados (RG, CNH), instale: pip install pytesseract pdf2image')

    print('[TRIAGEM] ⏳ Iniciando _coletar_textos_processo...')
    coleta = coletar_textos_processo(driver)
    print(f'[TRIAGEM] _coletar_textos_processo retornou: erro={coleta.get("erro")}')
    if coleta.get('erro'):
        return f'ERRO: {coleta["erro"]}'

    texto = coleta['texto_inicial']
    if not texto or len(texto) < 100:
        return 'ERRO: texto da peticao inicial extraido vazio ou muito curto'

    anexos = coleta['anexos']
    capa_dados = coleta.get('capa_dados') or {}

    rd: Dict[str, Any] = {}

    b1 = checar_procuracao_e_identidade(anexos, capa_dados.get('reclamante_nome') or '')
    rd['docs_essenciais'] = b1
    cep = checar_cep(texto, capa_dados)
    rd['cep'] = cep
    partes = checar_partes(texto, capa_dados)
    rd['partes'] = partes
    seg = checar_segredo(texto, capa_dados)
    rd['segredo'] = seg
    rec = checar_reclamadas(texto, capa_dados)
    rd['reclamadas'] = rec
    tut = checar_tutela(texto, capa_dados)
    rd['tutela'] = tut
    dig = checar_digital(texto, capa_dados)
    rd['digital'] = dig
    ped = checar_pedidos_liquidados(texto)
    rd['pedidos'] = ped
    pf = checar_pessoa_fisica(texto, capa_dados)
    rd['pessoa_fis'] = pf
    lit = checar_litispendencia(texto, coleta.get('associados_sistema'))
    rd['litispend'] = lit
    resp = checar_responsabilidade(texto, capa_dados)
    rd['responsab'] = resp
    end = checar_endereco_reclamante(texto)
    rd['endereco'] = end
    rito = checar_rito(texto, capa_dados)
    rd['rito'] = rito
    a6 = checar_art611b(texto)
    rd['art611b'] = a6

    alertas, itens_ok = [], []
    for val in [b1, partes, seg, rec, resp, tut, dig, pf, lit, end, rito, a6]:
        for item in itens_lista(val):
            if not item:
                continue
            prefixo, status, _ = conteudo_saida_item(item)
            if prefixo == 'B2_CEP':
                continue
            if status == 'ALERTA':
                alertas.append(formatar_saida_item(item))
            else:
                itens_ok.append(formatar_saida_item(item))

    linhas = [
        '[COMPETENCIA]',
        formatar_competencia_saida(cep),
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
```

<!-- pjeplus:delta:end -->

## Justificativa

Mantém a função pública intacta e reduz o arquivo principal a um orquestrador simples, legível e estável.[^1]

***

## Objetivo

Aplicar em `aud.py` o uso explícito da nova estrutura, caso você prefira abandonar o import legado `tr.py` e apontar diretamente para o pacote refatorado. O estado atual importa `triagem_peticao` de `tr`.[^2]

## Arquivo(s) Alvo

- `aud.py`


## Trecho Original

```python
from tr import triagem_peticao
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
from triagem import triagem_peticao
```

<!-- pjeplus:delta:end -->

## Justificativa

Após a refatoração, o ponto de entrada canônico passa a ser o pacote `triagem`, embora o `tr.py` de compatibilidade permita migração gradual sem quebra imediata.[^2][^1]

***

## Objetivo

Apontar os problemas concretos identificados no `tr.py` atual e o efeito esperado da reorganização proposta.

## Arquivo(s) Alvo

- `tr.py`
- `aud.py`


## Trecho Original

```python
# análise conceitual
```


## Alteração Proposta

<!-- pjeplus:delta:start -->
```python
Problemas corrigidos pela proposta:
1. Duplicação real de funções B5/B6 e versões concorrentes de helpers, mantendo apenas uma implementação final canônica.
2. Separação entre:
   - coleta API/PDF/OCR;
   - pré-processamento de texto;
   - regras de triagem;
   - formatação de saída;
   - ponto de entrada público.
3. Preservação do contrato:
   - triagem_peticao(driver) -> str
   - compatibilidade via tr.py
4. Arquivos menores, temáticos e todos abaixo do teto operacional pedido (~600 linhas por arquivo).
```

<!-- pjeplus:delta:end -->

## Justificativa

A proposta atende exatamente ao pedido: limpar, reorganizar sem perda funcional e dividir por pertinência temática, com patch adicional de uso em `aud.py`.[^2][^1]

<div align="center">⁂</div>

[^1]: tr.py

[^2]: aud.py

