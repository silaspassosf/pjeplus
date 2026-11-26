"""Prazo.argos_poupa — Camada Python do Argos Poupa Convênios (Art. 131 CNC).

Consulta via API REST do Argos todas as pesquisas reaproveitáveis das executadas,
aplica as regras do Ofício Circular CR nº 124/2026 (Provimento GP/CR nº 4/2026):
  - ARISP: 12 meses
  - RENAJUD: 6 meses
  - INFOJUD: a qualquer tempo, limitado aos 3 anos disponíveis mais recentes por tipo
  - Demais consultas: 12 meses
  - Atos de constrição (SISBAJUD/CNIB/SERASAJUD): excluídos (§ 4º)

Baixa a certidão de reaproveitamento e os anexos PDF/imagem e mescla em PDFs por
empresa no formato `Empresa (DOI OK, Renajud NEG).pdf` (separados Positivas/Negativas
ou unificado Positivas -> Negativas).
"""
from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from Fix.log import logger
from Fix.variaveis import cliente_para

DEFAULT_PAGE_SIZE = 500
DEFAULT_TIMEOUT_S = 60
MAX_ANOS_INFOJUD_POR_TIPO = 3
PASTA_SAIDA_PADRAO = Path.home() / "Downloads" / "ArgosPoupa"

TIPOS_CONSTRICAO = frozenset({
    "SISBAJUD_BLOQUEIO",
    "CNIB_INDISPONIBILIDADE",
    "SERASAJUD_INCLUSAO",
})

MAPA_SIGLA_PESQUISA: Dict[str, str] = {
    "ARISP_CONSULTA": "ARISP",
    "RENAJUD_CONSULTA": "Renajud",
    "INFOJUD_CONSULTA_DOI": "DOI",
    "INFOJUD_CONSULTA_DIMOB": "DIMOB",
    "INFOJUD_CONSULTA_ECF": "ECF",
    "INFOJUD_CONSULTA_E_FINANCEIRA": "e-Financeira",
    "INFOJUD_CONSULTA_DECRED": "DECRED",
    "INFOJUD_CONSULTA_DIRPF": "DIRPF",
    "INFOJUD_CONSULTA_DIRPJ": "DIRPJ",
    "INFOJUD_CONSULTA_DITR": "DITR",
    "SISBAJUD_BLOQUEIO": "Sisbajud",
    "CNIB_INDISPONIBILIDADE": "CNIB",
    "SERASAJUD_INCLUSAO": "Serasajud",
}

MAPA_TIPO_PARA_CHECKBOX: Dict[str, str] = {
    "RENAJUD_CONSULTA": "RENAJUD",
    "ARISP_CONSULTA": "ARISP",
    "INFOJUD_CONSULTA_DIRPF": "DIRPF",
    "INFOJUD_CONSULTA_DECRED": "DECRED",
    "INFOJUD_CONSULTA_DOI": "DOI",
    "INFOJUD_CONSULTA_DIMOB": "DIMOB",
}


# ── Placeholder de seleção de executadas (a ser refinado em seguida) ─────────
def definir_executadas_poupa(
    partes_passivo: List[Dict[str, Any]],
    partes_ativo: Optional[List[Dict[str, Any]]] = None,
    *,
    id_processo: Optional[str] = None,
    numero_processo: Optional[str] = None,
    texto_normalizado: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Placeholder para definição das executadas alvo do Argos Poupa.

    Comportamento temporário: retorna TODAS as reclamadas (polo PASSIVO) que
    possuam CPF/CNPJ válido. Será substituído pela regra definitiva de seleção.
    """
    _ = (partes_ativo, id_processo, numero_processo, texto_normalizado)
    selecionadas: List[Dict[str, Any]] = []
    vistos: set[str] = set()
    for p in partes_passivo or []:
        doc = _so_digitos(p.get("documento"))
        if not doc or doc in vistos:
            continue
        vistos.add(doc)
        selecionadas.append({
            "nome": str(p.get("nome") or "").strip(),
            "documento": doc,
            "polo": "PASSIVO",
        })
    return selecionadas


# ── Helpers gerais ───────────────────────────────────────────────────────────
def _so_digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _norm_cmp(texto: Any) -> str:
    s = unicodedata.normalize("NFD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.upper().strip()


def _subtrair_meses(dt: datetime, meses: int) -> datetime:
    ano = dt.year
    mes = dt.month - meses
    while mes <= 0:
        mes += 12
        ano -= 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(dt.day, ultimo_dia)
    return dt.replace(year=ano, month=mes, day=dia)


def _parse_iso_dt(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    s = str(valor).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _sigla_pesquisa(t: Dict[str, Any], incluir_ano: bool = False) -> str:
    tipo = str(t.get("tipoTarefa") or "").upper()
    base = MAPA_SIGLA_PESQUISA.get(tipo)
    if not base:
        base = str(t.get("nomeTarefa") or t.get("rotuloTarefa") or tipo)
        base = re.sub(r"^Consulta\s+", "", base, flags=re.IGNORECASE)
        base = re.sub(r"\s+(?:no|na)\s+(?:INFOJUD|ARISP|RENAJUD|SISBAJUD)$", "", base, flags=re.IGNORECASE)
        base = re.sub(r"\s*\(Consulta\)$", "", base, flags=re.IGNORECASE).strip()
    ano = t.get("anoDocumentoInfojud")
    if incluir_ano and ano:
        return f"{base} {ano}"
    return base


def _sanitizar_nome_arquivo(nome: str) -> str:
    limpo = re.sub(r'[\\/:*?"<>|]+', " ", str(nome or "documento"))
    limpo = re.sub(r"\s+", " ", limpo).strip().rstrip(".")
    if len(limpo) > 180:
        limpo = limpo[:177].strip() + "..."
    return limpo


def _ordenar_positivas_depois_negativas(tarefas: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        tarefas,
        key=lambda t: (
            0 if t.get("resultadoPositivo") else 1,
            _sigla_pesquisa(t, incluir_ano=True).lower(),
        ),
    )


def _abreviar_nomes_empresas(grupos: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    entries = []
    for g in grupos:
        bruto = str(g.get("nomeEmpresa") or g.get("documento") or "Executado")
        tokens = [tok for tok in re.sub(r"[,.;:]+", " ", bruto).split() if tok]
        entries.append({"doc": g["documento"], "tokens": tokens or [g["documento"]], "len": 1})

    houve_colisao = True
    while houve_colisao:
        houve_colisao = False
        contagem: Dict[str, int] = {}
        for e in entries:
            chave = _norm_cmp(" ".join(e["tokens"][: e["len"]]))
            contagem[chave] = contagem.get(chave, 0) + 1
        for e in entries:
            chave = _norm_cmp(" ".join(e["tokens"][: e["len"]]))
            if contagem[chave] > 1 and e["len"] < len(e["tokens"]):
                e["len"] += 1
                houve_colisao = True

    mapa: Dict[str, str] = {}
    usados: Dict[str, int] = {}
    for e in entries:
        curto = " ".join(e["tokens"][: e["len"]]) or e["doc"]
        chave = _norm_cmp(curto)
        usados[chave] = usados.get(chave, 0) + 1
        mapa[e["doc"]] = curto

    for e in entries:
        curto = mapa[e["doc"]]
        if usados.get(_norm_cmp(curto), 0) > 1 and e["doc"] and e["doc"] != "SEM_DOC":
            mapa[e["doc"]] = f"{curto} {e['doc'][-4:]}"
    return mapa


def _montar_nome_arquivo_empresa(nome_empresa: str, tarefas_ordenadas: Sequence[Dict[str, Any]]) -> str:
    contagem_tipo: Dict[str, int] = {}
    for t in tarefas_ordenadas:
        k = str(t.get("tipoTarefa") or t.get("nomeTarefa") or "")
        contagem_tipo[k] = contagem_tipo.get(k, 0) + 1

    tags: List[str] = []
    vistos: set[str] = set()
    for t in tarefas_ordenadas:
        k = str(t.get("tipoTarefa") or t.get("nomeTarefa") or "")
        sigla = _sigla_pesquisa(t, incluir_ano=contagem_tipo[k] > 1)
        tag = f"{sigla} {'OK' if t.get('resultadoPositivo') else 'NEG'}"
        if tag not in vistos:
            vistos.add(tag)
            tags.append(tag)

    empresa_limpa = re.sub(r"\s+", " ", str(nome_empresa or "Executado")).strip()
    return _sanitizar_nome_arquivo(f"{empresa_limpa} ({', '.join(tags)})") + ".pdf"


# ── Camada HTTP / API do Argos via PjeApiClient ──────────────────────────────
def _obter_partes_e_numero(client: Any, id_processo: str) -> Tuple[Optional[str], Dict[str, List[Dict[str, Any]]]]:
    numero: Optional[str] = None
    try:
        proc = client.processo_por_id(id_processo)
        if isinstance(proc, dict):
            numero = proc.get("numero") or proc.get("numeroProcesso")
    except Exception as e:
        logger.warning("[ARGOS_POUPA] falha ao obter processo_por_id(%s): %s", id_processo, e)

    partes = {"ativo": [], "passivo": []}
    try:
        r = client.sess.get(
            client._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes"),
            timeout=15,
        )
        if r.ok:
            raw = r.json() or {}
            for chave_api, chave_out, polo in (("ATIVO", "ativo", "ATIVO"), ("PASSIVO", "passivo", "PASSIVO")):
                partes[chave_out] = [
                    {
                        "nome": str(p.get("nome") or "").strip(),
                        "documento": _so_digitos(p.get("documento")),
                        "polo": polo,
                    }
                    for p in (raw.get(chave_api) or [])
                ]
    except Exception as e:
        logger.warning("[ARGOS_POUPA] falha ao obter partes(%s): %s", id_processo, e)

    return numero, partes


def normalizar_tarefa(it: Dict[str, Any]) -> Dict[str, Any]:
    ano = it.get("anoDocumentoInfojud") or it.get("anodocumentoinfojud")
    oculta_ano = bool(
        it.get("ocultaAnoNaExibicao")
        if it.get("ocultaAnoNaExibicao") is not None
        else it.get("ocultaanonaexibicao")
    )
    nome_base = str(
        it.get("nomeTarefa") or it.get("nometarefa") or it.get("tipoTarefa") or it.get("tipotarefa") or ""
    )
    rotulo = f"{nome_base} ({ano})" if (ano and not oculta_ano) else nome_base
    return {
        "idTarefa": it.get("idTarefa") if it.get("idTarefa") is not None else it.get("idtarefa"),
        "idResultado": it.get("idResultado") if it.get("idResultado") is not None else it.get("idresultado"),
        "idConvenio": it.get("idconvenio") if it.get("idconvenio") is not None else it.get("idConvenio"),
        "documentoExecutado": _so_digitos(it.get("documentoExecutado") or it.get("documentoexecutado")),
        "nomeExecutado": str(it.get("nomeExecutado") or it.get("nomeexecutado") or "").strip(),
        "executadoPessoaFisica": bool(
            it.get("executadoPessoaFisica")
            if it.get("executadoPessoaFisica") is not None
            else it.get("executadopessoafisica")
        ),
        "numeroProcessoOrigem": str(it.get("numeroProcesso") or it.get("numeroprocesso") or ""),
        "nomeOrgaoJulgador": str(it.get("nomeOrgaoJulgador") or it.get("nomeorgaojulgador") or ""),
        "tipoTarefa": str(it.get("tipoTarefa") or it.get("tipotarefa") or ""),
        "nomeTarefa": nome_base,
        "rotuloTarefa": rotulo,
        "anoDocumentoInfojud": str(ano) if ano is not None else None,
        "ocultaAnoNaExibicao": oculta_ano,
        "dataFinalizacao": str(it.get("dataFinalizacao") or it.get("datafinalizacao") or ""),
        "resultadoPositivo": bool(
            it.get("resultadoPositivo")
            if it.get("resultadoPositivo") is not None
            else it.get("resultadopositivo")
        ),
        "possuiAnexo": bool(
            it.get("possuiAnexo") if it.get("possuiAnexo") is not None else it.get("possuianexo")
        ),
        "reaproveitamento": bool(it.get("reaproveitamento")),
        "sempreReaproveitavel": bool(
            it.get("semprereaproveitavel")
            if it.get("semprereaproveitavel") is not None
            else it.get("sempreReaproveitavel")
        ),
        "diasReaproveitamento": it.get("quantidadediasreaproveitamentotarefa"),
        "statusTarefa": str(it.get("statustarefa") or it.get("statusTarefa") or ""),
    }


def buscar_todas_reaproveitaveis(
    client: Any,
    docs: Sequence[str],
    *,
    tamanho_pagina: int = DEFAULT_PAGE_SIZE,
    apenas_localizacao_usuario: bool = False,
) -> Dict[str, Any]:
    docs_limpos = list(dict.fromkeys(_so_digitos(d) for d in docs if _so_digitos(d)))
    if not docs_limpos:
        return {"totalRegistros": 0, "qtdPaginas": 0, "paginasLidas": 0, "resultado": []}

    url = client._url("/pje-argos-api/api/consulta-tarefas-reaproveitaveis")
    todos: List[Dict[str, Any]] = []
    pagina = 1
    qtd_paginas = 1
    total_registros = 0

    while pagina <= qtd_paginas:
        params: List[Tuple[str, str]] = [
            ("pesquisarProcessos", "true"),
            ("pesquisasRealizadasNaLocalizacaoUsuarioLogado", "true" if apenas_localizacao_usuario else "false"),
        ]
        for d in docs_limpos:
            params.append(("pesquisaRapidaMultiplaTarefas", d))
        params.append(("pagina", str(pagina)))
        params.append(("tamanhoPagina", str(tamanho_pagina)))

        r = client.sess.get(url, params=params, timeout=(10, DEFAULT_TIMEOUT_S))
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code} em consulta-tarefas-reaproveitaveis (pág {pagina})")
        data = r.json() or {}
        total_registros = int(data.get("totalRegistros") or total_registros)
        qtd_paginas = int(data.get("qtdPaginas") or 1)
        lote = data.get("resultado") or []
        for item in lote:
            todos.append(normalizar_tarefa(item))
        if not lote:
            break
        pagina += 1

    return {
        "totalRegistros": total_registros,
        "qtdPaginas": qtd_paginas,
        "paginasLidas": pagina - 1,
        "resultado": todos,
    }


# ── Regras Art. 131 CNC (Ofício Circular CR nº 124/2026) ─────────────────────
def avaliar_elegibilidade_art131(
    tarefa: Dict[str, Any],
    data_ref: Optional[datetime] = None,
) -> Dict[str, Any]:
    agora = data_ref or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)

    tipo = str(tarefa.get("tipoTarefa") or "").upper()
    if tipo in TIPOS_CONSTRICAO:
        return {"elegivel": False, "regra": "Constrição (§ 4º)", "motivo": "Ato de constrição não reaproveitável", "prazoMeses": 0}

    dt_fin = _parse_iso_dt(tarefa.get("dataFinalizacao"))
    dias_decorridos = int((agora - dt_fin).total_seconds() // 86400) if dt_fin else None

    if tipo.startswith("INFOJUD_") or tarefa.get("idConvenio") == 3 or tarefa.get("sempreReaproveitavel"):
        return {
            "elegivel": True,
            "regra": "INFOJUD (3 anos)",
            "motivo": "Válida a qualquer tempo (art. 131, c)",
            "prazoMeses": None,
            "diasDecorridos": dias_decorridos,
        }

    prazo_meses = 12
    rotulo = "Demais (12 meses)"
    if tipo.startswith("ARISP_") or tarefa.get("idConvenio") == 4:
        prazo_meses = 12
        rotulo = "ARISP (12 meses)"
    elif tipo.startswith("RENAJUD_") or tarefa.get("idConvenio") == 2:
        prazo_meses = 6
        rotulo = "RENAJUD (6 meses)"

    if not dt_fin:
        return {"elegivel": False, "regra": rotulo, "motivo": "Sem data de finalização", "prazoMeses": prazo_meses, "diasDecorridos": None}

    limite = _subtrair_meses(agora, prazo_meses)
    dentro = dt_fin >= limite
    return {
        "elegivel": dentro,
        "regra": rotulo,
        "motivo": f"Válida — há {dias_decorridos}d" if dentro else f"Expirada — há {dias_decorridos}d (limite {prazo_meses}m)",
        "prazoMeses": prazo_meses,
        "diasDecorridos": dias_decorridos,
    }


def selecionar_elegiveis_art131(
    itens: Sequence[Dict[str, Any]],
    *,
    data_ref: Optional[datetime] = None,
    max_anos_infojud: int = MAX_ANOS_INFOJUD_POR_TIPO,
) -> Dict[str, Any]:
    agora = data_ref or datetime.now(timezone.utc)
    avaliadas = [dict(it, art131=avaliar_elegibilidade_art131(it, agora)) for it in itens]
    validas = [it for it in avaliadas if it["art131"]["elegivel"]]

    # Deduplica por (documentoExecutado, tipoTarefa, ano visível), mantendo mais recente
    dedup_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for it in validas:
        ano_chave = str(it["anoDocumentoInfojud"]) if (it.get("anoDocumentoInfojud") and not it.get("ocultaAnoNaExibicao")) else ""
        chave = (str(it.get("documentoExecutado") or ""), str(it.get("tipoTarefa") or ""), ano_chave)
        atual = dedup_map.get(chave)
        if not atual or str(it.get("dataFinalizacao") or "") > str(atual.get("dataFinalizacao") or ""):
            dedup_map[chave] = it

    # Regra estrita: nunca pegar mais de uma data de pesquisa para o mesmo (documentoExecutado, tipoTarefa)
    data_mais_recente: Dict[Tuple[str, str], str] = {}
    for it in dedup_map.values():
        k = (str(it.get("documentoExecutado") or ""), str(it.get("tipoTarefa") or ""))
        dia = str(it.get("dataFinalizacao") or "")[:10]
        if dia > data_mais_recente.get(k, ""):
            data_mais_recente[k] = dia

    descartadas_anos: List[Dict[str, Any]] = []
    grupos_infojud: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    nao_infojud_por_tipo: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for it in dedup_map.values():
        k = (str(it.get("documentoExecutado") or ""), str(it.get("tipoTarefa") or ""))
        dia = str(it.get("dataFinalizacao") or "")[:10]
        max_dia = data_mais_recente.get(k, "")
        if max_dia and dia != max_dia:
            descartadas_anos.append(it)
            continue
        is_infojud_anual = (
            (str(it.get("tipoTarefa") or "").upper().startswith("INFOJUD_") or it.get("idConvenio") == 3)
            and bool(it.get("anoDocumentoInfojud"))
            and not bool(it.get("ocultaAnoNaExibicao"))
        )
        if not is_infojud_anual:
            prev = nao_infojud_por_tipo.get(k)
            if not prev or str(it.get("dataFinalizacao") or "") > str(prev.get("dataFinalizacao") or ""):
                nao_infojud_por_tipo[k] = it
            continue
        grupos_infojud.setdefault(k, []).append(it)

    infojud_mantidas: List[Dict[str, Any]] = []
    for lista in grupos_infojud.values():
        lista.sort(
            key=lambda x: (
                int(re.sub(r"\D", "", str(x.get("anoDocumentoInfojud") or "0")) or 0),
                str(x.get("dataFinalizacao") or ""),
            ),
            reverse=True,
        )
        for idx, it in enumerate(lista):
            if idx < max_anos_infojud:
                infojud_mantidas.append(it)
            else:
                descartadas_anos.append(it)

    elegiveis = sorted(
        list(nao_infojud_por_tipo.values()) + infojud_mantidas,
        key=lambda x: (
            str(x.get("documentoExecutado") or ""),
            0 if x.get("resultadoPositivo") else 1,
            str(x.get("rotuloTarefa") or ""),
        ),
    )

    return {
        "todasAvaliadas": avaliadas,
        "elegiveis": elegiveis,
        "expiradasOuExcluidas": [it for it in avaliadas if not it["art131"]["elegivel"]] + descartadas_anos,
    }


def calcular_convenios_excluidos(
    docs_alvo: Sequence[str],
    elegiveis_art131: Sequence[Dict[str, Any]],
    tem_cpf: bool = False,
) -> List[str]:
    docs = list(dict.fromkeys(_so_digitos(d) for d in docs_alvo if _so_digitos(d)))
    if not docs or not elegiveis_art131:
        return []
    cobertos: Dict[str, set[str]] = {d: set() for d in docs}
    for t in elegiveis_art131:
        doc = _so_digitos(t.get("documentoExecutado"))
        if doc not in cobertos:
            continue
        cb = MAPA_TIPO_PARA_CHECKBOX.get(str(t.get("tipoTarefa") or "").upper())
        if cb:
            cobertos[doc].add(cb)

    candidatos = ("RENAJUD", "ARISP", "DIRPF", "DECRED", "DOI", "DIMOB")
    excluidos = [cb for cb in candidatos if all(cb in cobertos[d] for d in docs)]
    sub_infojud = ("DIRPF", "DECRED", "DOI", "DIMOB") if tem_cpf else ("DECRED", "DOI", "DIMOB")
    if all(sub in excluidos for sub in sub_infojud):
        excluidos.append("INFOJUD")
    return excluidos


# ── Download e Merge de PDFs (PyMuPDF / fitz) ────────────────────────────────
def _baixar_certidao_reaproveitamento(client: Any, numero_processo: str, ids_tarefas: Sequence[int]) -> bytes:
    url = client._url(f"/pje-argos-api/api/processos/{numero_processo}/tarefas-processo/certidao-avulsa-reaproveitamento")
    r = client.sess.post(
        url,
        json={"numeroProcesso": numero_processo, "idsTarefasReaproveitadas": list(ids_tarefas)},
        timeout=(10, 30),
    )
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} ao gerar certidão de reaproveitamento")
    return r.content


def _listar_arquivos_tarefa(client: Any, id_tarefa: Any, id_resultado: Any) -> List[Dict[str, Any]]:
    url = client._url(f"/pje-argos-api/api/tarefas/{id_tarefa}/resultados/{id_resultado}/arquivos")
    r = client.sess.get(url, timeout=20)
    if not r.ok:
        return []
    data = r.json()
    return data if isinstance(data, list) else []


def _baixar_arquivo_anexo(client: Any, id_tarefa: Any, id_resultado: Any, id_arquivo: Any) -> Tuple[bytes, str]:
    url = client._url(
        f"/pje-argos-api/api/tarefas/{id_tarefa}/resultados/{id_resultado}/arquivos/{id_arquivo}/conteudo/download"
    )
    r = client.sess.get(url, timeout=(10, 60))
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} ao baixar anexo {id_arquivo}")
    return r.content, (r.headers.get("content-type") or "").lower()


MAX_PDF_BYTES = int(9.5 * 1024 * 1024)  # margem segura abaixo de 10 MB
# Sem deflate_images=True para não descomprimir/desfazer streams JPEG/1-bit otimizados
_FITZ_SAVE_KW = dict(garbage=4, deflate=True, deflate_fonts=True)
_IMG_MIN_BYTES_OTIMIZAR = 18 * 1024
_IMG_MAX_LADO_PX = 1350  # ~160 DPI em A4 (1100 quando lote >= 80 págs)
_IMG_JPEG_QUALIDADE = 50


def _otimizar_imagem_grayscale_bytes(
    raw: bytes,
    *,
    max_lado: int = _IMG_MAX_LADO_PX,
    qualidade: int = _IMG_JPEG_QUALIDADE,
) -> Optional[bytes]:
    """Converte imagem grande para grayscale + DPI comprimido (JPEG) se reduzir tamanho."""
    if not raw or len(raw) < _IMG_MIN_BYTES_OTIMIZAR:
        return None
    try:
        import io
        from PIL import Image

        im = Image.open(io.BytesIO(raw)).convert("L")
        im.thumbnail((max_lado, int(max_lado * 1.45)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=qualidade, optimize=True)
        novo = out.getvalue()
        return novo if len(novo) < len(raw) else None
    except Exception:
        return None


def _otimizar_imagens_pdf_rapido(doc: Any) -> int:
    """Converte páginas escaneadas para 1-bit P&B (/FlateDecode) e reduz tarjas /SMask sem rasterizar texto."""
    import io
    import zlib
    from PIL import Image

    otimizadas = 0
    vistos: set = set()
    max_lado_pag = 1100 if doc.page_count >= 80 else _IMG_MAX_LADO_PX

    for pg in doc:
        try:
            imgs = pg.get_images(full=True)
        except Exception:
            continue
        for info in imgs:
            xref = info[0]
            if xref in vistos:
                continue
            vistos.add(xref)
            try:
                st_orig = doc.xref_stream_raw(xref)
                if not st_orig or len(st_orig) < _IMG_MIN_BYTES_OTIMIZAR:
                    continue
                obj_str = doc.xref_object(xref)
                base = doc.extract_image(xref)
                raw = base.get("image") if base else None
                if not raw:
                    continue
                im = Image.open(io.BytesIO(raw)).convert("L")

                if "/SMask" in obj_str:
                    # Tarja lateral repetida (~36KB/pág): reduz JPEG mantendo SMask
                    im.thumbnail((450, 1200), Image.Resampling.LANCZOS)
                    out = io.BytesIO()
                    im.save(out, format="JPEG", quality=35, optimize=True)
                    nv = out.getvalue()
                    if len(nv) < len(st_orig):
                        doc.xref_set_key(xref, "Width", str(im.width))
                        doc.xref_set_key(xref, "Height", str(im.height))
                        doc.xref_set_key(xref, "ColorSpace", "/DeviceGray")
                        doc.xref_set_key(xref, "BitsPerComponent", "8")
                        doc.xref_set_key(xref, "Filter", "/DCTDecode")
                        doc.xref_set_key(xref, "DecodeParms", "null")
                        doc.update_stream(xref, nv, compress=False)
                        otimizadas += 1
                else:
                    if max(im.size) > max_lado_pag:
                        im.thumbnail((max_lado_pag, int(max_lado_pag * 1.45)), Image.Resampling.LANCZOS)
                    im1 = im.point(lambda p: 255 if p > 185 else 0, mode="1")
                    comp = zlib.compress(im1.tobytes(), level=6)
                    if len(comp) < len(st_orig):
                        doc.xref_set_key(xref, "Width", str(im1.width))
                        doc.xref_set_key(xref, "Height", str(im1.height))
                        doc.xref_set_key(xref, "ColorSpace", "/DeviceGray")
                        doc.xref_set_key(xref, "BitsPerComponent", "1")
                        doc.xref_set_key(xref, "Filter", "/FlateDecode")
                        doc.xref_set_key(xref, "DecodeParms", "null")
                        doc.update_stream(xref, comp, compress=False)
                        otimizadas += 1
            except Exception:
                continue
    return otimizadas


def _caminho_parte_pdf(caminho_base: Path, parte: int, total_partes: int) -> Path:
    if total_partes <= 1:
        return caminho_base
    return caminho_base.with_name(f"{caminho_base.stem} - Parte {parte} de {total_partes}.pdf")


def _fatia_pdf_bytes(doc_origem: Any, inicio: int, fim: int) -> bytes:
    import fitz

    sub = fitz.open()
    try:
        sub.insert_pdf(doc_origem, from_page=inicio, to_page=fim - 1)
        return sub.tobytes(**_FITZ_SAVE_KW)
    finally:
        sub.close()


def _dividir_e_salvar_pdf(
    pdf_final: Any,
    caminho_saida: Path,
    *,
    max_bytes: int = MAX_PDF_BYTES,
) -> List[Dict[str, Any]]:
    """Comprime (deflate/garbage=4) e divide em partes <= max_bytes (<10 MB)."""
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    total_pgs = pdf_final.page_count
    raw_unico = pdf_final.tobytes(**_FITZ_SAVE_KW)

    if len(raw_unico) <= max_bytes or total_pgs <= 1:
        caminho_saida.write_bytes(raw_unico)
        return [{
            "caminho": str(caminho_saida),
            "nomeArquivo": caminho_saida.name,
            "totalPaginas": total_pgs,
            "bytesFinal": len(raw_unico),
            "parte": 1,
            "totalPartes": 1,
        }]

    partes_raw: List[Tuple[bytes, int]] = []
    media_pag = max(1.0, len(raw_unico) / total_pgs)
    cursor = 0
    while cursor < total_pgs:
        restantes = total_pgs - cursor
        qtd = max(1, min(restantes, int((max_bytes * 0.92) / media_pag)))
        blob = _fatia_pdf_bytes(pdf_final, cursor, cursor + qtd)

        if len(blob) > max_bytes and qtd > 1:
            lo, hi = 1, qtd - 1
            melhor_qtd, melhor_blob = 1, None
            while lo <= hi:
                mid = (lo + hi) // 2
                cand = _fatia_pdf_bytes(pdf_final, cursor, cursor + mid)
                if len(cand) <= max_bytes:
                    melhor_qtd, melhor_blob = mid, cand
                    lo = mid + 1
                else:
                    hi = mid - 1
            qtd = melhor_qtd
            blob = melhor_blob if melhor_blob is not None else _fatia_pdf_bytes(pdf_final, cursor, cursor + 1)
        elif len(blob) < max_bytes * 0.72 and cursor + qtd < total_pgs:
            for _ in range(2):
                if cursor + qtd >= total_pgs:
                    break
                fator = min(1.6, (max_bytes * 0.92) / max(1, len(blob)))
                nova_qtd = min(total_pgs - cursor, max(qtd + 1, int(qtd * fator)))
                if nova_qtd <= qtd:
                    break
                cand = _fatia_pdf_bytes(pdf_final, cursor, cursor + nova_qtd)
                if len(cand) <= max_bytes:
                    qtd, blob = nova_qtd, cand
                else:
                    break

        partes_raw.append((blob, qtd))
        cursor += qtd

    total_partes = len(partes_raw)
    saida: List[Dict[str, Any]] = []
    for idx, (blob, pags) in enumerate(partes_raw, start=1):
        destino = _caminho_parte_pdf(caminho_saida, idx, total_partes)
        destino.write_bytes(blob)
        saida.append({
            "caminho": str(destino),
            "nomeArquivo": destino.name,
            "totalPaginas": pags,
            "bytesFinal": len(blob),
            "parte": idx,
            "totalPartes": total_partes,
        })
    return saida


def _extrair_matricula_e_cartorio_texto(texto: str) -> Tuple[List[str], str]:
    s = re.sub(r"\.pdf$", "", str(texto or ""), flags=re.I)
    s = re.sub(r"[_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return [], ""

    matriculas: List[str] = []
    for m_mat in re.finditer(r"(?:matr[ií]cula|matr\.?|mat\.?)\s*(?:n[º°o\.]*)?\s*[:\-]?\s*(\d{1,3}(?:\.\s*\d{3})+|\d{2,10})", s, re.I):
        limpa = re.sub(r"[\.\s]+", "", m_mat.group(1))
        if 2 <= len(limpa) <= 10 and limpa not in matriculas:
            matriculas.append(limpa)

    cartorio = ""
    m_cri = re.search(
        r"(\d+\s*[º°oª]?\s*(?:oficial\s+de\s+)?(?:registro\s+de\s+im[oó]veis|c\.?\s*r\.?\s*i\.?|r\.?\s*i\.?)"
        r"(?:\s+(?:de|da|do)\s+[A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})?)",
        s,
        re.I,
    )
    if m_cri:
        c = m_cri.group(1)
        c = re.sub(r"oficial\s+de\s+registro\s+de\s+im[oó]veis", "CRI", c, flags=re.I)
        c = re.sub(r"registro\s+de\s+im[oó]veis", "CRI", c, flags=re.I)
        c = re.sub(r"c\.?\s*r\.?\s*i\.?", "CRI", c, flags=re.I)
        cartorio = re.sub(r"\s+", " ", c).strip()
    else:
        m_cart = re.search(r"((?:\d+\s*[º°oª]?\s*)?cart[oó]rio\s+[A-Za-zÀ-ÿ0-9º°ª]+(?:\s+[A-Za-zÀ-ÿ0-9º°ª]+){0,3})", s, re.I)
        if m_cart:
            cartorio = re.sub(r"\s+", " ", m_cart.group(1)).strip()
        else:
            m_seg = re.search(
                r"(?:matr[ií]cula|matr\.?|mat\.?)\s*[\d\.\s]+\s*[-–]\s*([A-Za-zÀ-ÿ0-9º°ª\s]{2,24}?)(?:\s*[-–]\s*(?:proc|peeq|otim|$)|$)",
                s,
                re.I,
            )
            if m_seg:
                cartorio = re.sub(r"\s+", " ", m_seg.group(1)).strip()

    return matriculas, cartorio


def _extrair_info_arisp_de_fontes(fontes: Sequence[str]) -> str:
    mats: List[str] = []
    cartorio = ""
    for f in fontes:
        ms, c = _extrair_matricula_e_cartorio_texto(f)
        for m in ms:
            if m not in mats:
                mats.append(m)
        if not cartorio and c:
            cartorio = c
    # Se o mesmo arquivo contém múltiplas matrículas agrupadas, não nomear com a primeira
    if len(mats) > 1:
        return ""
    partes = []
    if len(mats) == 1:
        partes.append(f"Mat {mats[0]}")
    if cartorio:
        partes.append(cartorio)
    return " - ".join(partes)


def _mesclar_lote_em_pdf(
    client: Any,
    numero_processo: str,
    tarefas_lote: Sequence[Dict[str, Any]],
    caminho_saida: Path,
    *,
    max_bytes: int = MAX_PDF_BYTES,
    enriquecer_nome_arisp: bool = False,
    nome_curto_empresa: str = "",
    arquivos_pre_filtrados: Optional[Sequence[Tuple[Dict[str, Any], Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    import fitz  # PyMuPDF

    tarefas_ord = _ordenar_positivas_depois_negativas(tarefas_lote)
    ids = list(dict.fromkeys(int(t["idTarefa"]) for t in tarefas_ord if t.get("idTarefa") is not None))
    avisos: List[str] = []
    anexos_mesclados = 0
    fontes_arisp: List[str] = []
    if enriquecer_nome_arisp:
        for t in tarefas_ord:
            for campo in ("rotuloTarefa", "nomeTarefa", "descricaoResultado", "observacao"):
                val = t.get(campo)
                if val:
                    fontes_arisp.append(str(val))

    pdf_final = fitz.open()
    try:
        # 1. Certidão / Sumário consolidado do Argos
        cert_bytes = _baixar_certidao_reaproveitamento(client, numero_processo, ids)
        with fitz.open(stream=cert_bytes, filetype="pdf") as doc_cert:
            if enriquecer_nome_arisp:
                for pi in range(min(2, doc_cert.page_count)):
                    fontes_arisp.append(doc_cert[pi].get_text("text") or "")
            pdf_final.insert_pdf(doc_cert)

        # 2. Anexos de cada tarefa (ou lista pré-filtrada para ARISP 1 arquivo por PDF)
        fila_anexos: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        if arquivos_pre_filtrados is not None:
            fila_anexos = list(arquivos_pre_filtrados)
        else:
            for t in tarefas_ord:
                if not (t.get("possuiAnexo") and t.get("idTarefa") and t.get("idResultado")):
                    continue
                for arq in _listar_arquivos_tarefa(client, t["idTarefa"], t["idResultado"]):
                    fila_anexos.append((t, arq))

        hashes_inseridos: set = set()
        for t, arq in fila_anexos:
            id_arq = arq.get("id")
            nome_arq = str(arq.get("nomeArquivo") or f"anexo_{id_arq}.pdf")
            if enriquecer_nome_arisp and nome_arq:
                fontes_arisp.append(nome_arq)
            if not id_arq:
                continue
            try:
                import hashlib
                raw, ctype = _baixar_arquivo_anexo(client, t["idTarefa"], t["idResultado"], id_arq)
                sig_md5 = hashlib.md5(raw).hexdigest()
                if sig_md5 in hashes_inseridos:
                    avisos.append(f"Anexo duplicado ignorado: {nome_arq}")
                    continue
                hashes_inseridos.add(sig_md5)
                if raw[:5] == b"%PDF-" or "pdf" in ctype:
                    with fitz.open(stream=raw, filetype="pdf") as doc_anx:
                        if enriquecer_nome_arisp:
                            for pi in range(min(2, doc_anx.page_count)):
                                fontes_arisp.append(doc_anx[pi].get_text("text") or "")
                        pdf_final.insert_pdf(doc_anx)
                    anexos_mesclados += 1
                elif any(ext in ctype or nome_arq.lower().endswith(ext) for ext in ("png", "jpg", "jpeg")):
                    ot_img = _otimizar_imagem_grayscale_bytes(raw)
                    if ot_img:
                        raw, ext = ot_img, "jpeg"
                    else:
                        ext = "png" if ("png" in ctype or nome_arq.lower().endswith(".png")) else "jpeg"
                    with fitz.open(stream=raw, filetype=ext) as img_doc:
                        pdf_bytes = img_doc.convert_to_pdf()
                    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc_img_pdf:
                        pdf_final.insert_pdf(doc_img_pdf)
                    anexos_mesclados += 1
                else:
                    avisos.append(f"Ignorado não-PDF: {nome_arq} ({ctype})")
            except Exception as e:
                avisos.append(f"Falha ao mesclar {nome_arq}: {e}")

        if enriquecer_nome_arisp:
            detalhe_arisp = _extrair_info_arisp_de_fontes(fontes_arisp)
            if detalhe_arisp:
                base_emp = nome_curto_empresa or "Executado"
                novo_nome = _sanitizar_nome_arquivo(f"{base_emp} (ARISP OK - {detalhe_arisp})") + ".pdf"
                caminho_saida = caminho_saida.with_name(novo_nome)

        _otimizar_imagens_pdf_rapido(pdf_final)
        partes = _dividir_e_salvar_pdf(pdf_final, caminho_saida, max_bytes=max_bytes)
    finally:
        pdf_final.close()

    for p in partes:
        p["anexosMesclados"] = anexos_mesclados
        p["avisos"] = avisos
    return partes


def gerar_pdfs_por_empresa(
    client: Any,
    numero_processo: str,
    tarefas_selecionadas: Sequence[Dict[str, Any]],
    *,
    separar_positivas_negativas: bool = True,
    pasta_saida: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    if not tarefas_selecionadas:
        return []

    base_dir = (Path(pasta_saida) if pasta_saida else PASTA_SAIDA_PADRAO) / _sanitizar_nome_arquivo(numero_processo)

    grupos_map: Dict[str, Dict[str, Any]] = {}
    for t in tarefas_selecionadas:
        doc = str(t.get("documentoExecutado") or "SEM_DOC")
        if doc not in grupos_map:
            grupos_map[doc] = {"documento": doc, "nomeEmpresa": t.get("nomeExecutado") or doc, "tarefas": []}
        grupos_map[doc]["tarefas"].append(t)

    grupos = list(grupos_map.values())
    nomes_curtos = _abreviar_nomes_empresas(grupos)

    def _eh_arisp(t: Dict[str, Any]) -> bool:
        return "ARISP" in str(t.get("tipoTarefa") or t.get("nomeTarefa") or "").upper()

    def _eh_renajud(t: Dict[str, Any]) -> bool:
        return "RENAJUD" in str(t.get("tipoTarefa") or t.get("nomeTarefa") or "").upper()

    def _extrair_indice_parte_arisp(nome_arq: str) -> int:
        s = re.sub(r"\.pdf$", "", str(nome_arq or ""), flags=re.I).strip()
        m = re.search(r"(?:[-_\s](?:otimizado|parte|pt|pag)[-_.\s]*|_)(\d{1,3})$", s, re.I)
        return int(m.group(1)) if m else 0

    def _chave_imovel_canonica(matricula: str, cartorio: str) -> str:
        if not matricula:
            return ""
        c_norm = _norm_cmp(cartorio or "")
        m_of = re.search(r"\b(\d{1,2})\s*(?:O|º|°)?\s*(?:CRI|CARTORIO|SP|OFICIO|RI)\b", c_norm) or re.match(r"^(\d{1,2})SP$", c_norm)
        sufixo = f"CRI{m_of.group(1)}" if m_of else re.sub(r"[^A-Z0-9]", "", c_norm)[:12]
        return f"{matricula}|{sufixo}"

    lotes: List[Dict[str, Any]] = []
    matriculas_emitidas_global: set = set()
    # Regra por parte executada (Art. 131 CNC):
    # Positivas: (a) ARISP 1 PDF por matrícula (reunindo partes _1.._N na ordem e sem repetir matrícula já gerada),
    # (b) Renajud agrupado, (c) Demais agrupado.
    # Negativas: 1 PDF agrupado por parte executada.
    _ = separar_positivas_negativas
    for g in grupos:
        nome_curto = nomes_curtos.get(g["documento"], g["nomeEmpresa"])
        ordenadas = _ordenar_positivas_depois_negativas(g["tarefas"])
        pos = [t for t in ordenadas if t.get("resultadoPositivo")]
        neg = [t for t in ordenadas if not t.get("resultadoPositivo")]

        pos_arisp = [t for t in pos if _eh_arisp(t)]
        pos_renajud = [t for t in pos if not _eh_arisp(t) and _eh_renajud(t)]
        pos_demais = [t for t in pos if not _eh_arisp(t) and not _eh_renajud(t)]

        for idx, t_arisp in enumerate(pos_arisp, start=1):
            arqs_arisp = (
                _listar_arquivos_tarefa(client, t_arisp["idTarefa"], t_arisp["idResultado"])
                if (t_arisp.get("possuiAnexo") and t_arisp.get("idTarefa") and t_arisp.get("idResultado"))
                else []
            )
            if not arqs_arisp:
                sufixo = f" {idx}" if len(pos_arisp) > 1 else ""
                lotes.append({
                    "doc": g["documento"],
                    "tipo": "ARISP_OK",
                    "nome": _sanitizar_nome_arquivo(f"{nome_curto} (ARISP OK{sufixo})") + ".pdf",
                    "tarefas": [t_arisp],
                    "arquivos_pre": [],
                    "enriquecer": True,
                })
            else:
                nomes_vistos_tarefa: set = set()
                grupos_mat: Dict[str, Dict[str, Any]] = {}
                avulsos: List[Tuple[Dict[str, Any], str]] = []

                for arq in arqs_arisp:
                    nome_raw = str(arq.get("nomeArquivo") or "")
                    chave_nome = _norm_cmp(nome_raw)
                    if chave_nome and chave_nome in nomes_vistos_tarefa:
                        continue
                    if chave_nome:
                        nomes_vistos_tarefa.add(chave_nome)

                    mats, cart = _extrair_matricula_e_cartorio_texto(nome_raw)
                    detalhe = _extrair_info_arisp_de_fontes([nome_raw])
                    parte_num = _extrair_indice_parte_arisp(nome_raw)

                    if len(mats) == 1:
                        mat = mats[0]
                        k_imovel = _chave_imovel_canonica(mat, cart)
                        if k_imovel not in grupos_mat:
                            grupos_mat[k_imovel] = {
                                "k_imovel": k_imovel,
                                "detalhe": detalhe or f"Mat {mat}",
                                "itens": [],
                            }
                        grupos_mat[k_imovel]["itens"].append((parte_num, arq))
                    else:
                        avulsos.append((arq, detalhe))

                for grp in grupos_mat.values():
                    k_im = grp["k_imovel"]
                    if k_im and k_im in matriculas_emitidas_global:
                        continue
                    if k_im:
                        matriculas_emitidas_global.add(k_im)
                    grp["itens"].sort(key=lambda x: x[0])
                    base_nome = f"{nome_curto} (ARISP OK - {grp['detalhe']})"
                    lotes.append({
                        "doc": g["documento"],
                        "tipo": "ARISP_OK",
                        "nome": _sanitizar_nome_arquivo(base_nome) + ".pdf",
                        "tarefas": [t_arisp],
                        "arquivos_pre": [(t_arisp, a) for _, a in grp["itens"]],
                        "enriquecer": False,
                    })

                for ai, (arq, detalhe) in enumerate(avulsos, start=1):
                    base_nome = (
                        f"{nome_curto} (ARISP OK - {detalhe})"
                        if detalhe
                        else f"{nome_curto} (ARISP OK {ai})"
                    )
                    lotes.append({
                        "doc": g["documento"],
                        "tipo": "ARISP_OK",
                        "nome": _sanitizar_nome_arquivo(base_nome) + ".pdf",
                        "tarefas": [t_arisp],
                        "arquivos_pre": [(t_arisp, arq)],
                        "enriquecer": not bool(detalhe),
                    })
        if pos_renajud:
            lotes.append({"doc": g["documento"], "tipo": "RENAJUD_OK", "nome": _montar_nome_arquivo_empresa(nome_curto, pos_renajud), "tarefas": pos_renajud, "arquivos_pre": None, "enriquecer": False})
        if pos_demais:
            lotes.append({"doc": g["documento"], "tipo": "DEMAIS_OK", "nome": _montar_nome_arquivo_empresa(nome_curto, pos_demais), "tarefas": pos_demais, "arquivos_pre": None, "enriquecer": False})
        if neg:
            lotes.append({"doc": g["documento"], "tipo": "NEGATIVAS", "nome": _montar_nome_arquivo_empresa(nome_curto, neg), "tarefas": neg, "arquivos_pre": None, "enriquecer": False})

    gerados: List[Dict[str, Any]] = []
    for lote in lotes:
        partes = _mesclar_lote_em_pdf(
            client,
            numero_processo,
            lote["tarefas"],
            base_dir / lote["nome"],
            enriquecer_nome_arisp=lote["enriquecer"],
            nome_curto_empresa=nomes_curtos.get(lote["doc"], ""),
            arquivos_pre_filtrados=lote["arquivos_pre"],
        )
        for res in partes:
            res["documento"] = lote["doc"]
            res["tipoLote"] = lote["tipo"]
            gerados.append(res)
    return gerados


# ── Entrypoint para P2B (inicar_exec) ────────────────────────────────────────
def executar_argos_poupa_p2b(
    driver: Any,
    *,
    client: Any = None,
    id_processo: Optional[str] = None,
    numero_processo: Optional[str] = None,
    texto_normalizado: Optional[str] = None,
    separar_positivas_negativas: bool = True,
    pasta_saida: Optional[Path] = None,
    gerar_pdfs: bool = True,
) -> Dict[str, Any]:
    """Executa o Argos Poupa Convênios via API no fluxo P2B `inicar_exec`.

    Chamado após a criação dos GIGS (Argos / xs sigilo) e antes do `ato_*`.
    Usa `definir_executadas_poupa(...)` (placeholder) para selecionar as executadas.
    """
    resultado: Dict[str, Any] = {
        "ok": False,
        "numero_processo": numero_processo,
        "executadas_alvo": [],
        "total_api": 0,
        "elegiveis": [],
        "convenios_excluidos": [],
        "arquivos_gerados": [],
        "erro": None,
    }
    try:
        if client is None:
            client = cliente_para(driver)
        if not id_processo:
            from Fix.core import extrair_id_processo
            id_processo = extrair_id_processo(driver)
        if not id_processo:
            resultado["erro"] = "id_processo_indisponivel"
            return resultado

        num_api, partes = _obter_partes_e_numero(client, str(id_processo))
        num = numero_processo or num_api
        resultado["numero_processo"] = num
        if not num:
            resultado["erro"] = "numero_processo_indisponivel"
            return resultado

        executadas = definir_executadas_poupa(
            partes.get("passivo") or [],
            partes.get("ativo") or [],
            id_processo=str(id_processo),
            numero_processo=num,
            texto_normalizado=texto_normalizado,
        )
        resultado["executadas_alvo"] = executadas
        docs = [e["documento"] for e in executadas if e.get("documento")]
        if not docs:
            logger.info("[ARGOS_POUPA] %s: nenhuma executada com CPF/CNPJ selecionada", num)
            resultado["ok"] = True
            return resultado

        logger.info("[ARGOS_POUPA] %s: consultando API para %d executada(s)", num, len(docs))
        reap = buscar_todas_reaproveitaveis(client, docs)
        resultado["total_api"] = len(reap.get("resultado") or [])

        analise = selecionar_elegiveis_art131(reap.get("resultado") or [])
        elegiveis = analise["elegiveis"]
        resultado["elegiveis"] = elegiveis

        tem_cpf = any(len(d) == 11 for d in docs)
        excluidos = calcular_convenios_excluidos(docs, elegiveis, tem_cpf=tem_cpf)
        resultado["convenios_excluidos"] = excluidos

        if gerar_pdfs and elegiveis:
            arquivos = gerar_pdfs_por_empresa(
                client,
                num,
                elegiveis,
                separar_positivas_negativas=separar_positivas_negativas,
                pasta_saida=pasta_saida,
            )
            resultado["arquivos_gerados"] = arquivos
            logger.info(
                "[ARGOS_POUPA] %s: %d elegível(is) Art.131 | %d PDF(s) gerado(s) | convênios cobertos=%s",
                num,
                len(elegiveis),
                len(arquivos),
                ", ".join(excluidos) or "nenhum",
            )
        else:
            logger.info(
                "[ARGOS_POUPA] %s: total_api=%d | elegiveis=%d (sem PDFs a gerar)",
                num,
                resultado["total_api"],
                len(elegiveis),
            )

        resultado["ok"] = True
        return resultado
    except Exception as e:
        logger.error("[ARGOS_POUPA] erro no processo %s: %s", numero_processo or id_processo, e)
        resultado["erro"] = str(e)
        return resultado
