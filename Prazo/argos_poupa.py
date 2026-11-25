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

    # Limita INFOJUD anual aos N anos disponíveis mais recentes por (empresa, tipoTarefa)
    grupos_infojud: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    nao_infojud_anual: List[Dict[str, Any]] = []
    for it in dedup_map.values():
        is_infojud_anual = (
            (str(it.get("tipoTarefa") or "").upper().startswith("INFOJUD_") or it.get("idConvenio") == 3)
            and bool(it.get("anoDocumentoInfojud"))
            and not bool(it.get("ocultaAnoNaExibicao"))
        )
        if not is_infojud_anual:
            nao_infojud_anual.append(it)
            continue
        k = (str(it.get("documentoExecutado") or ""), str(it.get("tipoTarefa") or ""))
        grupos_infojud.setdefault(k, []).append(it)

    descartadas_anos: List[Dict[str, Any]] = []
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
        nao_infojud_anual + infojud_mantidas,
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
_FITZ_SAVE_KW = dict(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)
_IMG_MIN_BYTES_OTIMIZAR = 50 * 1024
_IMG_MAX_LADO_PX = 1240  # ~120-150 DPI em A4
_IMG_JPEG_QUALIDADE = 58


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
        im.thumbnail((max_lado, int(max_lado * 1.42)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=qualidade, optimize=True)
        novo = out.getvalue()
        return novo if len(novo) < len(raw) else None
    except Exception:
        return None


def _otimizar_imagens_pdf_rapido(doc: Any) -> int:
    """Re-comprime in-place imagens grandes (>=50KB) do PDF para grayscale + DPI comprimido sem rasterizar texto."""
    otimizadas = 0
    vistos: set = set()
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
                base = doc.extract_image(xref)
                raw = base.get("image") if base else None
                if not raw or len(raw) < _IMG_MIN_BYTES_OTIMIZAR:
                    continue
                novo = _otimizar_imagem_grayscale_bytes(raw)
                if novo:
                    pg.replace_image(xref, stream=novo)
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


def _mesclar_lote_em_pdf(
    client: Any,
    numero_processo: str,
    tarefas_lote: Sequence[Dict[str, Any]],
    caminho_saida: Path,
    *,
    max_bytes: int = MAX_PDF_BYTES,
) -> List[Dict[str, Any]]:
    import fitz  # PyMuPDF

    tarefas_ord = _ordenar_positivas_depois_negativas(tarefas_lote)
    ids = list(dict.fromkeys(int(t["idTarefa"]) for t in tarefas_ord if t.get("idTarefa") is not None))
    avisos: List[str] = []
    anexos_mesclados = 0

    pdf_final = fitz.open()
    try:
        # 1. Certidão / Sumário consolidado do Argos
        cert_bytes = _baixar_certidao_reaproveitamento(client, numero_processo, ids)
        with fitz.open(stream=cert_bytes, filetype="pdf") as doc_cert:
            pdf_final.insert_pdf(doc_cert)

        # 2. Anexos de cada tarefa com possuiAnexo
        for t in tarefas_ord:
            if not (t.get("possuiAnexo") and t.get("idTarefa") and t.get("idResultado")):
                continue
            arqs = _listar_arquivos_tarefa(client, t["idTarefa"], t["idResultado"])
            for arq in arqs:
                id_arq = arq.get("id")
                nome_arq = str(arq.get("nomeArquivo") or f"anexo_{id_arq}.pdf")
                if not id_arq:
                    continue
                try:
                    raw, ctype = _baixar_arquivo_anexo(client, t["idTarefa"], t["idResultado"], id_arq)
                    if raw[:5] == b"%PDF-" or "pdf" in ctype:
                        with fitz.open(stream=raw, filetype="pdf") as doc_anx:
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

    lotes: List[Tuple[str, str, str, List[Dict[str, Any]]]] = []
    # Regra por parte executada (Art. 131 CNC):
    # Positivas: (a) ARISP 1 por 1, (b) Renajud agrupado, (c) Demais agrupado.
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
            sufixo = f" {idx}" if len(pos_arisp) > 1 else ""
            nome_arisp = _sanitizar_nome_arquivo(f"{nome_curto} (ARISP OK{sufixo})") + ".pdf"
            lotes.append((g["documento"], "ARISP_OK", nome_arisp, [t_arisp]))
        if pos_renajud:
            lotes.append((g["documento"], "RENAJUD_OK", _montar_nome_arquivo_empresa(nome_curto, pos_renajud), pos_renajud))
        if pos_demais:
            lotes.append((g["documento"], "DEMAIS_OK", _montar_nome_arquivo_empresa(nome_curto, pos_demais), pos_demais))
        if neg:
            lotes.append((g["documento"], "NEGATIVAS", _montar_nome_arquivo_empresa(nome_curto, neg), neg))

    gerados: List[Dict[str, Any]] = []
    for doc, tipo_lote, nome_arq, tarefas_lote in lotes:
        partes = _mesclar_lote_em_pdf(client, numero_processo, tarefas_lote, base_dir / nome_arq)
        for res in partes:
            res["documento"] = doc
            res["tipoLote"] = tipo_lote
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
