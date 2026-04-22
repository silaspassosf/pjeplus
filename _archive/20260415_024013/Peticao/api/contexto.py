"""
Peticao/api/contexto.py

Análise de contexto para decisão sobre petições:
  - Identifica o último despacho/decisão/sentença anterior na timeline
  - Mapeia quais partes já agiram após aquele despacho
  - Determina se ainda é necessário aguardar ou já se pode agir

Chamadas de API:
  1. timeline (sempre — traz tudo em uma única requisição GET)
  2. partes (opcional — só se necessário para enriquecer polo via nome)
  + 1 por documento se extrair_conteudo_despacho ou extrair_conteudo_peticoes

Integração com pet.py:
  - Tarefa "aguardando prazo": chamar com prazo_vencido=False
    → deve_aguardar=True enquanto partes pendentes; pode_agir=True quando todas agiram
  - Tarefa "prazo vencido": chamar com prazo_vencido=True
    → pode_agir=True sempre, independente do estado das partes
"""

import html as _html
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.log import get_module_logger
from .client import PjeApiClient

logger = get_module_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes — tipos de documentos
# ---------------------------------------------------------------------------

TIPOS_DESPACHO_PADRAO: frozenset = frozenset([
    'Despacho',
    'Decisão',
    'Sentença',
    'Acórdão',
    'Decisão Monocrática',
    'Despacho de Mero Expediente',
    'Decisão Interlocutória',
])

# Tipos que NÃO são petições (excluídos da contagem de "petições extras")
TIPOS_NAO_PETICAO: frozenset = frozenset([
    'Certidão',
    'Ata da Audiência',
    'Chave de Acesso',
    'Planilha de Cálculos',
    'Planilha de Atualização de Cálculos',
    'Carta Precatória',
    'Carta Rogatória',
    'Ofício',
    'Edital',
    # tipos de decisão também excluídos (já capturados por TIPOS_DESPACHO_PADRAO)
    'Despacho',
    'Decisão',
    'Sentença',
    'Acórdão',
    'Decisão Monocrática',
    'Despacho de Mero Expediente',
    'Decisão Interlocutória',
])


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ItemTimeline:
    """Representação simplificada de um documento da timeline relevante."""
    id_interno: Optional[str]
    id_unico: Optional[str]
    tipo: str
    titulo: str
    data: str
    polo: Optional[str]           # 'ativo' | 'passivo' | 'terceiro' | None
    nome_peticionante: Optional[str]
    texto: Optional[str] = None   # preenchido só se extrair_conteudo=True


@dataclass
class ContextoPeticao:
    """
    Resultado da análise contextual de uma petição na timeline processual.

    Campos de decisão rápida:
      deve_aguardar: True se partes esperadas ainda não agiram e prazo não venceu.
      pode_agir:     True se todas as partes esperadas agiram OU prazo_vencido=True.
    """
    id_processo: str
    id_peticao_atual: Optional[str]

    despacho_anterior: Optional[ItemTimeline]
    peticao_atual: Optional[ItemTimeline]
    polo_peticionante_atual: Optional[str]

    peticoes_extras: List[ItemTimeline] = field(default_factory=list)
    partes_que_agiram: List[str] = field(default_factory=list)
    partes_pendentes: List[str] = field(default_factory=list)
    todas_partes_esperadas_agiram: bool = False

    deve_aguardar: bool = True
    pode_agir: bool = False

    @property
    def total_extra(self) -> int:
        return len(self.peticoes_extras)

    @property
    def resumo(self) -> str:
        partes_str = ', '.join(self.partes_que_agiram) or 'nenhuma'
        pendentes_str = ', '.join(self.partes_pendentes) or 'nenhuma'
        desp = self.despacho_anterior
        desp_info = f"{desp.tipo} ({desp.data[:10]})" if desp else "nao encontrado"
        return (
            f"Despacho anterior: {desp_info} | "
            f"Peticoes extras apos despacho: {self.total_extra} | "
            f"Partes que agiram: {partes_str} | "
            f"Pendentes: {pendentes_str} | "
            f"Pode agir: {self.pode_agir}"
        )


# ---------------------------------------------------------------------------
# Auxiliares privados
# ---------------------------------------------------------------------------

def _normalizar_polo(polo_raw: str) -> Optional[str]:
    p = polo_raw.upper().strip()
    if 'ATIVO' in p:
        return 'ativo'
    if 'PASSIVO' in p:
        return 'passivo'
    if 'TERCEIRO' in p or 'INTERVENIENTE' in p or 'PERITO' in p:
        return 'terceiro'
    return None


def _extrair_polo_item(raw: Dict[str, Any]) -> tuple:
    """Retorna (polo_key, nome_peticionante) a partir de um item raw da timeline."""
    polo_raw = (
        raw.get('poloPeticionante') or
        raw.get('polo') or
        raw.get('parte') or
        raw.get('peticionante') or
        ''
    )
    nome = ''
    if isinstance(polo_raw, dict):
        nome = polo_raw.get('nome') or polo_raw.get('descricao') or ''
        polo_raw = polo_raw.get('polo') or polo_raw.get('tipoPolo') or ''

    polo_key = _normalizar_polo(str(polo_raw)) if polo_raw else None

    if not nome:
        titulo = raw.get('titulo') or ''
        if ' - ' in titulo:
            candidato = titulo.split(' - ', 1)[-1].strip()
            # Descartar "ID. abc123" que é apenas referência de documento
            if candidato and not candidato.startswith('ID.'):
                nome = candidato

    return polo_key, nome or None


def _e_peticao(raw: Dict[str, Any], tipos_despacho: frozenset, tipos_excluir: frozenset) -> bool:
    tipo = (raw.get('tipo') or '').strip()
    if not tipo or tipo == 'Movimento':
        return False
    if tipo in tipos_despacho or tipo in tipos_excluir:
        return False
    return True


def _id_interno(raw: Dict[str, Any]) -> Optional[str]:
    v = raw.get('id') or raw.get('idDocumento')
    return str(v) if v else None


def _id_unico(raw: Dict[str, Any]) -> Optional[str]:
    v = raw.get('idUnicoDocumento')
    return str(v) if v else None


def _fazer_item(raw: Dict[str, Any], texto: Optional[str] = None) -> ItemTimeline:
    polo, nome = _extrair_polo_item(raw)
    return ItemTimeline(
        id_interno=_id_interno(raw),
        id_unico=_id_unico(raw),
        tipo=(raw.get('tipo') or '').strip(),
        titulo=(raw.get('titulo') or '').strip(),
        data=(raw.get('data') or raw.get('dataInclusao') or ''),
        polo=polo,
        nome_peticionante=nome,
        texto=texto,
    )


def _obter_texto_documento(client: PjeApiClient, id_processo: str, id_doc: str) -> Optional[str]:
    """
    Extrai conteúdo textual de um documento via API.
    Ordem: campo JSON do documento_por_id → endpoint /conteudo → None.
    """
    try:
        dados = client.documento_por_id(id_processo, id_doc)
        if dados:
            for k in ('conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento'):
                v = dados.get(k)
                if isinstance(v, str) and v.strip():
                    return _limpar_html(v)
    except Exception:
        pass

    for path in (
        f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo",
        f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudoHtml",
    ):
        try:
            r = client.sess.get(client._url(path), timeout=15)
            if not r.ok:
                continue
            ctype = (r.headers.get('Content-Type') or '').lower()
            if 'pdf' in ctype or 'octet' in ctype:
                continue
            if 'json' in ctype:
                j = r.json()
                for k in ('conteudo', 'conteudoHtml', 'texto', 'previewModeloDocumento'):
                    v = j.get(k)
                    if isinstance(v, str) and v.strip():
                        return _limpar_html(v)
            elif r.text:
                return _limpar_html(r.text)
        except Exception:
            continue

    return None


def _limpar_html(texto: str) -> str:
    sem_tags = re.sub(r'<[^>]+>', '', texto)
    sem_tags = _html.unescape(sem_tags)
    return re.sub(r'\s{2,}', ' ', sem_tags).strip()


def _buscar_texto_item(
    client: PjeApiClient,
    id_processo: str,
    raw: Dict[str, Any],
) -> Optional[str]:
    doc_id = _id_interno(raw)
    if not doc_id:
        return None
    try:
        return _obter_texto_documento(client, id_processo, doc_id)
    except Exception as e:
        logger.warning(f"[CONTEXTO] Falha ao extrair texto do documento {doc_id}: {e}")
        return None


def _encontrar_peticao_atual(
    itens: List[Dict[str, Any]],
    id_peticao_atual: Optional[str],
    tipos_despacho: frozenset,
    tipos_excluir: frozenset,
) -> Optional[int]:
    """
    Localiza índice da petição atual na timeline (reverse-chronological).
    Se id_peticao_atual for None, usa a primeira petição (mais recente).
    """
    if id_peticao_atual:
        id_str = str(id_peticao_atual)
        for i, it in enumerate(itens):
            if str(it.get('id') or '') == id_str or str(it.get('idUnicoDocumento') or '') == id_str:
                return i
        logger.warning(f"[CONTEXTO] Peticao {id_peticao_atual} nao localizada na timeline - usando a mais recente")

    for i, it in enumerate(itens):
        if _e_peticao(it, tipos_despacho, tipos_excluir):
            return i
    return None


def _encontrar_despacho_anterior(
    itens: List[Dict[str, Any]],
    idx_atual: Optional[int],
    tipos_despacho: frozenset,
) -> Optional[int]:
    """
    Localiza o despacho/decisão/sentença imediatamente ANTERIOR à petição atual.
    Na timeline reverse-chronological, "anterior cronologicamente" = índice maior.
    Busca a partir de idx_atual+1 em direção à origem do processo.
    """
    inicio = (idx_atual + 1) if idx_atual is not None else 0
    for i in range(inicio, len(itens)):
        tipo = (itens[i].get('tipo') or '').strip()
        if tipo in tipos_despacho:
            return i
    return None


def _resultado_vazio(
    id_processo: str,
    id_peticao_atual: Optional[str],
    polo_atual: Optional[str],
    prazo_vencido: bool,
) -> ContextoPeticao:
    return ContextoPeticao(
        id_processo=id_processo,
        id_peticao_atual=id_peticao_atual,
        despacho_anterior=None,
        peticao_atual=None,
        polo_peticionante_atual=polo_atual,
        deve_aguardar=not prazo_vencido,
        pode_agir=prazo_vencido,
    )


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def analisar_contexto_peticao(
    client: PjeApiClient,
    id_processo: str,
    *,
    id_peticao_atual: Optional[str] = None,
    polo_peticao_atual: Optional[str] = None,
    tipos_despacho: Optional[List[str]] = None,
    tipos_excluir_peticao: Optional[List[str]] = None,
    partes_esperadas: Optional[List[str]] = None,
    prazo_vencido: bool = False,
    extrair_conteudo_despacho: bool = False,
    extrair_conteudo_peticoes: bool = False,
    timeline_raw: Optional[List[Dict]] = None,
) -> ContextoPeticao:
    """
    Analisa o contexto de uma petição dentro da timeline de um processo.

    Identifica:
      - O despacho/decisão/sentença anterior que gerou os prazos
      - Quem apresentou a petição atual (polo)
      - Quantas e quais outras petições foram juntadas após esse despacho
      - Quais partes já agiram e quais estão pendentes

    Chamadas de API (mínimo):
      1 chamada → timeline (GET — sem XSRF)
      + 0 ou 1  → partes (GET — apenas se necessário inferir polo via nome)
      + N       → conteúdo de documentos (opcional, se extrair_conteudo_* ativo)

    Args:
        client:
            PjeApiClient com sessão ativa.
        id_processo:
            ID interno do processo (número inteiro como string).
        id_peticao_atual:
            ID do documento da petição sendo analisada.
            Se None, usa a petição mais recente encontrada na timeline.
        polo_peticao_atual:
            Polo da petição atual ('ativo' | 'passivo' | 'terceiro').
            Fornecido diretamente quando disponível via PeticaoItem.polo,
            evitando inferência e chamada adicional.
        tipos_despacho:
            Tipos de documento que servem como "ponto de corte" na timeline.
            Padrão: ['Despacho', 'Decisão', 'Sentença', 'Acórdão', ...].
        tipos_excluir_peticao:
            Tipos a ignorar na contagem de petições extras (certidões, atas, etc.).
            Padrão: lista TIPOS_NAO_PETICAO.
        partes_esperadas:
            Polos esperados para agir, ex: ['ativo', 'passivo'].
            Determina partes_pendentes e todas_partes_esperadas_agiram.
            Se None, apenas registra quem agiu sem calcular pendentes.
        prazo_vencido:
            Se True, pode_agir=True independentemente das partes pendentes.
            Use quando a tarefa já está em "prazo vencido" — sempre agir.
        extrair_conteudo_despacho:
            Se True, busca o texto completo do despacho anterior (1 req. extra).
            Útil para entender o que foi determinado.
        extrair_conteudo_peticoes:
            Se True, busca o texto de cada petição extra (1 req. por petição).
            Útil para análise de conteúdo das manifestações.
        timeline_raw:
            Dados de timeline já obtidos externamente.
            Passar quando a timeline já foi buscada, evitando chamada duplicada.

    Returns:
        ContextoPeticao com todos os campos preenchidos.
        Consultar .pode_agir e .deve_aguardar para decisão de fluxo.
    """
    _tipos_despacho = frozenset(tipos_despacho) if tipos_despacho else TIPOS_DESPACHO_PADRAO
    _tipos_excluir = frozenset(tipos_excluir_peticao) if tipos_excluir_peticao else TIPOS_NAO_PETICAO

    # 1. Obter timeline — 1 única chamada GET -----------------------------------
    dados_timeline = timeline_raw or client.timeline(
        id_processo, buscarDocumentos=True, buscarMovimentos=False
    )
    if not dados_timeline:
        logger.warning(f"[CONTEXTO] Timeline vazia para processo {id_processo}")
        return _resultado_vazio(id_processo, id_peticao_atual, polo_peticao_atual, prazo_vencido)

    # Timeline é reverse-chronological (índice 0 = mais recente).
    # Filtramos movimentos; documentos e anexos raiz permanecem.
    itens_doc = [it for it in dados_timeline if (it.get('tipo') or '') != 'Movimento']

    # 2. Localizar a petição atual na timeline ----------------------------------
    idx_atual = _encontrar_peticao_atual(itens_doc, id_peticao_atual, _tipos_despacho, _tipos_excluir)

    # 3. Localizar o despacho anterior -----------------------------------------
    # Na timeline reversa, "antes cronologicamente" = índice maior.
    idx_despacho = _encontrar_despacho_anterior(itens_doc, idx_atual, _tipos_despacho)

    # 4. Coletar petições extras entre o despacho e o presente -----------------
    # Janela: itens de índice 0 até idx_despacho-1 (exclusive),
    # excluindo a petição atual (idx_atual).
    limite = idx_despacho if idx_despacho is not None else len(itens_doc)
    peticoes_extras_raw = [
        it for i, it in enumerate(itens_doc[:limite])
        if i != idx_atual and _e_peticao(it, _tipos_despacho, _tipos_excluir)
    ]

    # 5. Extrair conteúdo opcional (N chamadas extras) -------------------------
    despacho_raw = itens_doc[idx_despacho] if idx_despacho is not None else None
    txt_despacho = (
        _buscar_texto_item(client, id_processo, despacho_raw)
        if (extrair_conteudo_despacho and despacho_raw)
        else None
    )

    extras: List[ItemTimeline] = []
    for raw_pet in peticoes_extras_raw:
        txt = _buscar_texto_item(client, id_processo, raw_pet) if extrair_conteudo_peticoes else None
        extras.append(_fazer_item(raw_pet, txt))

    # 6. Montar item da petição atual ------------------------------------------
    peticao_atual_raw = itens_doc[idx_atual] if idx_atual is not None else None
    peticao_atual_item = _fazer_item(peticao_atual_raw) if peticao_atual_raw else None

    # Polo atual: preferência ao fornecido pelo chamador (já resolvido via PeticaoItem)
    polo_atual = polo_peticao_atual or (peticao_atual_item.polo if peticao_atual_item else None)
    if peticao_atual_item and not peticao_atual_item.polo and polo_atual:
        peticao_atual_item.polo = polo_atual

    # 7. Calcular partes que agiram / pendentes --------------------------------
    partes_agiram: List[str] = []
    if polo_atual and polo_atual not in partes_agiram:
        partes_agiram.append(polo_atual)
    for extra in extras:
        if extra.polo and extra.polo not in partes_agiram:
            partes_agiram.append(extra.polo)

    esperadas = list(partes_esperadas) if partes_esperadas else []
    partes_pendentes = [p for p in esperadas if p not in partes_agiram]
    todas_agiram = bool(esperadas) and not partes_pendentes

    deve_aguardar = not todas_agiram and not prazo_vencido
    pode_agir = todas_agiram or prazo_vencido

    return ContextoPeticao(
        id_processo=id_processo,
        id_peticao_atual=id_peticao_atual,
        despacho_anterior=_fazer_item(despacho_raw, txt_despacho) if despacho_raw else None,
        peticao_atual=peticao_atual_item,
        polo_peticionante_atual=polo_atual,
        peticoes_extras=extras,
        partes_que_agiram=partes_agiram,
        partes_pendentes=partes_pendentes,
        todas_partes_esperadas_agiram=todas_agiram,
        deve_aguardar=deve_aguardar,
        pode_agir=pode_agir,
    )
