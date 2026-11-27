# -*- coding: utf-8 -*-
"""api.filtro_analise — Filtro via API REST do PJe para processos livres em Análise.

Critérios implementados (validados ao vivo no TRT2):
  0. Fase Liquidação ou Execução, tarefa Análise (`idTarefa=500`)
     → `PATCH /pje-comum-api/api/agrupamentotarefas/processos/todos`
  1. Sem GIGS (sem atividades abertas)
     → `GET /pje-gigs-api/api/tiposatividades/poridsprocessos` (lote) + `dataPrazoFinal`
       + confirmação opcional via `GET /pje-gigs-api/api/atividade/processo/{id}`
  2. Sem comentário
     → `temComentario`, `temComentarioSecretaria`, `ultimoComentario`, `numComentariosNaoLidos`
       + confirmação opcional via `GET /pje-gigs-api/api/comentario/processo/{id}`
  3. Sem responsável
     → `idUsuarioResponsavel` e `nomeUsuarioResponsavel` vazios
  4. Sem documento não apreciado
     → `isPeticaoNaoApreciada` / `peticaoNaoApreciada` falsos
       + cruzamento opcional com `GET /pje-comum-api/api/escaninhos/peticoesjuntadas?naoApreciados=true`
  5. Estado da transição "Aguardando prazo" — disponível ou não
     → `GET /pje-comum-api/api/processos/id/{id}/tarefas/{idTarefa}/transicoes`
       (`nomeTransicaoDestino == "Aguardando prazo"` → `transicaoDisponivel`)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
import unicodedata
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple, Union

if TYPE_CHECKING:
    from Fix.variaveis import PjeApiClient

logger = logging.getLogger(__name__)

FASES_LIQUIDACAO_EXECUCAO: Tuple[str, ...] = ("Liquidação", "Execução")
ID_TAREFA_ANALISE: int = 500
ID_TAREFA_CUMPRIMENTO: int = 491
ID_AGRUPAMENTO_PRAZOS_VENCIDOS: int = 14
ID_AGRUPAMENTO_ANALISE: int = 8
ID_AGRUPAMENTO_CUMPRIMENTO: int = 6
NOME_TAREFA_ANALISE: str = "Análise"
NOME_TRANSICAO_ANALISE: str = "Análise"
NOME_TRANSICAO_CUMPRIMENTO: str = "Cumprimento de providências"
NOME_TRANSICAO_AGUARDANDO_PRAZO: str = "Aguardando prazo"


@dataclass
class ProcessoAnaliseFiltrado:
    """Processo em Análise (Liquidação/Execução) que passou pelos critérios 0–5."""

    id_processo: int
    numero_processo: str
    fase_processual: str
    id_tarefa: int
    tarefa: str
    data_entrada_tarefa: Optional[str] = None
    aguardando_prazo_disponivel: Optional[bool] = None
    estado_aguardando_prazo: str = "desconhecido"
    id_orgao_julgador: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id_processo,
            "numeroProcesso": self.numero_processo,
            "faseProcessual": self.fase_processual,
            "idTarefa": self.id_tarefa,
            "tarefa": self.tarefa,
            "dataEntradaTarefa": self.data_entrada_tarefa,
            "aguardandoPrazoDisponivel": self.aguardando_prazo_disponivel,
            "estadoAguardandoPrazo": self.estado_aguardando_prazo,
        }


def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def _resolver_cliente(client_ou_driver: Any, grau: int = 1) -> "PjeApiClient":
    from Fix.variaveis import PjeApiClient, cliente_para

    if isinstance(client_ou_driver, PjeApiClient):
        return client_ou_driver
    return cliente_para(client_ou_driver, grau=grau)


def _tem_comentario(item: Dict[str, Any]) -> bool:
    ultimo = item.get("ultimoComentario")
    return bool(
        item.get("temComentario")
        or item.get("temComentarioSecretaria")
        or (isinstance(ultimo, str) and ultimo.strip())
        or int(item.get("numComentariosNaoLidos") or 0) > 0
    )


def _tem_responsavel(item: Dict[str, Any]) -> bool:
    nome = item.get("nomeUsuarioResponsavel")
    return bool(
        item.get("idUsuarioResponsavel")
        or (isinstance(nome, str) and nome.strip())
    )


def _tem_doc_nao_apreciado_campo(item: Dict[str, Any]) -> bool:
    return bool(item.get("isPeticaoNaoApreciada") or item.get("peticaoNaoApreciada"))


def _buscar_base_analise(
    client: PjeApiClient,
    *,
    fases: Sequence[str],
    id_tarefa: int,
    nome_tarefa: str,
    tamanho_pagina: int,
    max_paginas: int,
    timeout: int,
) -> List[Dict[str, Any]]:
    fases_lista = list(fases)
    fases_norm = {_norm(f) for f in fases_lista}
    tarefa_norm = _norm(nome_tarefa)

    todos: List[Dict[str, Any]] = []
    for pagina in range(1, max_paginas + 1):
        body = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
            "subCaixa": None,
            "tipoAtividade": None,
            "processos": None,
            "nomeConclusoMagistrado": None,
            "usuarioResponsavel": None,
            "faseProcessualString": fases_lista,
            "idTarefa": [int(id_tarefa)],
            "numeroProcesso": None,
            "juizoDigital": None,
        }
        res = client.gateway_patch(
            "/pje-comum-api/api/agrupamentotarefas/processos/todos",
            json_data=body,
            timeout=timeout,
        )
        if not res.get("ok"):
            if res.get("status") == 401:
                raise PermissionError("sessao_expirada_401")
            raise RuntimeError(
                f"Falha em agrupamentotarefas/processos/todos p{pagina}: {res.get('error')}"
            )

        data = res.get("data") or {}
        if isinstance(data, dict):
            lista = data.get("resultado") or data.get("content") or []
            qtd_paginas = data.get("qtdPaginas") or data.get("totalPaginas")
        elif isinstance(data, list):
            lista = data
            qtd_paginas = None
        else:
            lista = []
            qtd_paginas = None

        todos.extend(p for p in lista if isinstance(p, dict))
        if not lista:
            break
        if isinstance(qtd_paginas, int) and pagina >= qtd_paginas:
            break
        if len(lista) < tamanho_pagina:
            break

    filtrados: List[Dict[str, Any]] = []
    for p in todos:
        fase_p = _norm(p.get("faseProcessual") or p.get("labelFaseProcessual"))
        tarefa_p = _norm(p.get("tarefa") or p.get("nomeTarefa"))
        id_t = p.get("idTarefa")
        fase_ok = not fases_norm or fase_p in fases_norm
        tarefa_ok = (id_t == id_tarefa) or (bool(tarefa_norm) and tarefa_p == tarefa_norm)
        if fase_ok and tarefa_ok:
            filtrados.append(p)
    return filtrados


def _buscar_ids_escaninho_nao_apreciados(
    client: PjeApiClient,
    *,
    tamanho_pagina: int = 100,
    max_paginas: int = 50,
    timeout: int = 20,
) -> Set[int]:
    ids: Set[int] = set()
    for pagina in range(1, max_paginas + 1):
        res = client.gateway_get(
            "/pje-comum-api/api/escaninhos/peticoesjuntadas",
            params={
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
                "naoApreciados": "true",
            },
            timeout=timeout,
        )
        if not res.get("ok"):
            if res.get("status") == 401:
                raise PermissionError("sessao_expirada_401")
            logger.warning(
                "[FILTRO_ANALISE] Escaninho p%d indisponível (%s) — usando apenas campo do painel",
                pagina, res.get("error"),
            )
            break
        data = res.get("data") or {}
        if isinstance(data, dict):
            lista = data.get("resultado") or data.get("content") or []
            qtd_paginas = data.get("qtdPaginas") or data.get("totalPaginas")
        elif isinstance(data, list):
            lista = data
            qtd_paginas = None
        else:
            lista = []
            qtd_paginas = None

        for item in lista:
            if not isinstance(item, dict):
                continue
            pid = item.get("idProcesso")
            if pid is not None:
                try:
                    ids.add(int(pid))
                except (TypeError, ValueError):
                    pass

        if not lista:
            break
        if isinstance(qtd_paginas, int) and pagina >= qtd_paginas:
            break
        if len(lista) < tamanho_pagina:
            break
    return ids


def _estado_transicao_aguardando_prazo(
    client: PjeApiClient,
    id_processo: int,
    id_tarefa: int,
    *,
    timeout: int = 15,
) -> Optional[bool]:
    transicoes = client.transicoes_tarefa(id_processo, id_tarefa, timeout=timeout)
    if transicoes is None:
        return None
    alvo_norm = _norm(NOME_TRANSICAO_AGUARDANDO_PRAZO)
    for t in transicoes:
        if not isinstance(t, dict):
            continue
        if _norm(t.get("nomeTransicaoDestino")) == alvo_norm:
            return bool(t.get("transicaoDisponivel"))
    return False


def filtrar_processos_analise_livres(
    client_ou_driver: Union[PjeApiClient, Any],
    *,
    fases: Sequence[str] = FASES_LIQUIDACAO_EXECUCAO,
    id_tarefa: int = ID_TAREFA_ANALISE,
    nome_tarefa: str = NOME_TAREFA_ANALISE,
    confirmar_gigs_individual: bool = True,
    confirmar_comentarios_individual: bool = False,
    consultar_escaninho: bool = True,
    aguardando_prazo_disponivel: Optional[bool] = None,
    tamanho_pagina: int = 100,
    max_paginas: int = 50,
    timeout: int = 25,
    grau: int = 1,
    retornar_diagnostico: bool = False,
) -> Union[List[ProcessoAnaliseFiltrado], Tuple[List[ProcessoAnaliseFiltrado], Dict[str, Any]]]:
    """Filtra processos via API PJe segundo os critérios 0–5.

    Args:
        client_ou_driver: `PjeApiClient` ou driver autenticado (Playwright / compatível).
        fases: Fases processuais aceitas (padrão: `("Liquidação", "Execução")`).
        id_tarefa: ID da tarefa alvo (padrão: `500` = Análise).
        nome_tarefa: Nome da tarefa alvo para conferência defensiva.
        confirmar_gigs_individual: Confirma `GET /pje-gigs-api/api/atividade/processo/{id}`
            nos pré-filtrados (barato e garante zero falsos positivos).
        confirmar_comentarios_individual: Confirma `GET /pje-gigs-api/api/comentario/processo/{id}`
            nos pré-filtrados.
        consultar_escaninho: Cruza também com `/escaninhos/peticoesjuntadas?naoApreciados=true`
            além dos campos `isPeticaoNaoApreciada`/`peticaoNaoApreciada`.
        aguardando_prazo_disponivel:
            - `None` (padrão): retorna ambos, anotando `aguardando_prazo_disponivel` (`True`/`False`);
            - `True`: retorna somente onde a transição "Aguardando prazo" está disponível;
            - `False`: retorna somente onde a transição "Aguardando prazo" NÃO está disponível.
        retornar_diagnostico: Se `True`, retorna `(processos, diagnostico)`.
    """
    t0 = time.monotonic()
    client = _resolver_cliente(client_ou_driver, grau=grau)

    base = _buscar_base_analise(
        client,
        fases=fases,
        id_tarefa=id_tarefa,
        nome_tarefa=nome_tarefa,
        tamanho_pagina=tamanho_pagina,
        max_paginas=max_paginas,
        timeout=timeout,
    )

    ids_base = [int(p["id"]) for p in base if p.get("id") is not None]
    mapa_gigs_lote = client.tipos_atividades_gigs_lote(ids_base, timeout=timeout)
    if mapa_gigs_lote is None:
        logger.warning(
            "[FILTRO_ANALISE] tiposatividades/poridsprocessos falhou — forçando confirmação individual de GIGS"
        )
        mapa_gigs_lote = {}
        confirmar_gigs_individual = True

    ids_escaninho: Set[int] = (
        _buscar_ids_escaninho_nao_apreciados(client, tamanho_pagina=tamanho_pagina, timeout=timeout)
        if consultar_escaninho
        else set()
    )

    descartados = {
        "com_gigs_lote": 0,
        "com_gigs_individual": 0,
        "com_comentario": 0,
        "com_comentario_individual": 0,
        "com_responsavel": 0,
        "com_doc_nao_apreciado": 0,
        "filtro_aguardando_prazo": 0,
    }

    pre_filtrados: List[Dict[str, Any]] = []
    for p in base:
        pid = p.get("id")
        if pid is None:
            continue
        pid_int = int(pid)

        if pid_int in mapa_gigs_lote or bool(p.get("dataPrazoFinal")):
            descartados["com_gigs_lote"] += 1
            continue
        if _tem_comentario(p):
            descartados["com_comentario"] += 1
            continue
        if _tem_responsavel(p):
            descartados["com_responsavel"] += 1
            continue
        if _tem_doc_nao_apreciado_campo(p) or pid_int in ids_escaninho:
            descartados["com_doc_nao_apreciado"] += 1
            continue
        pre_filtrados.append(p)

    resultado: List[ProcessoAnaliseFiltrado] = []
    for p in pre_filtrados:
        pid_int = int(p["id"])
        tid = int(p.get("idTarefa") or id_tarefa)

        if confirmar_gigs_individual:
            ativs = client.atividades_gigs(str(pid_int))
            if isinstance(ativs, list) and len(ativs) > 0:
                descartados["com_gigs_individual"] += 1
                continue

        if confirmar_comentarios_individual:
            coms = client.comentarios_gigs(str(pid_int))
            if isinstance(coms, list) and len(coms) > 0:
                descartados["com_comentario_individual"] += 1
                continue

        ag_disp = _estado_transicao_aguardando_prazo(client, pid_int, tid, timeout=timeout)
        if aguardando_prazo_disponivel is not None and ag_disp is not aguardando_prazo_disponivel:
            descartados["filtro_aguardando_prazo"] += 1
            continue

        estado_str = (
            "disponivel" if ag_disp is True
            else ("indisponivel" if ag_disp is False else "erro")
        )
        resultado.append(
            ProcessoAnaliseFiltrado(
                id_processo=pid_int,
                numero_processo=str(p.get("numeroProcesso") or ""),
                fase_processual=str(p.get("faseProcessual") or p.get("labelFaseProcessual") or ""),
                id_tarefa=tid,
                tarefa=str(p.get("tarefa") or p.get("nomeTarefa") or nome_tarefa),
                data_entrada_tarefa=p.get("dataEntradaTarefa"),
                aguardando_prazo_disponivel=ag_disp,
                estado_aguardando_prazo=estado_str,
                raw=p,
            )
        )

    diagnostico = {
        "ok": True,
        "ms": round((time.monotonic() - t0) * 1000),
        "total_analise_liq_exec": len(base),
        "pre_filtrados": len(pre_filtrados),
        "total_filtrados": len(resultado),
        "aguardando_prazo_disponivel": sum(1 for x in resultado if x.aguardando_prazo_disponivel is True),
        "aguardando_prazo_indisponivel": sum(1 for x in resultado if x.aguardando_prazo_disponivel is False),
        "escaninho_ids_nao_apreciados": len(ids_escaninho),
        "descartados": descartados,
    }
    logger.info(
        "[FILTRO_ANALISE] %d/%d processos livres em Análise (%dms) | ag_prazo disp=%d indisp=%d | descartados=%s",
        diagnostico["total_filtrados"],
        diagnostico["total_analise_liq_exec"],
        diagnostico["ms"],
        diagnostico["aguardando_prazo_disponivel"],
        diagnostico["aguardando_prazo_indisponivel"],
        descartados,
    )

    if retornar_diagnostico:
        return resultado, diagnostico
    return resultado


def _instanciar_processo_filtrado(
    p: Dict[str, Any],
    *,
    id_tarefa_padrao: int = 0,
    nome_tarefa_padrao: str = "",
    ag_disp: Optional[bool] = None,
) -> ProcessoAnaliseFiltrado:
    estado_str = (
        "disponivel" if ag_disp is True
        else ("indisponivel" if ag_disp is False else "desconhecido")
    )
    oj_raw = p.get("idOrgaoJulgador")
    if oj_raw is None and isinstance(p.get("orgaoJulgador"), dict):
        oj_raw = p["orgaoJulgador"].get("id")
    return ProcessoAnaliseFiltrado(
        id_processo=int(p["id"]),
        numero_processo=str(p.get("numeroProcesso") or ""),
        fase_processual=str(p.get("faseProcessual") or p.get("labelFaseProcessual") or ""),
        id_tarefa=int(p.get("idTarefa") or id_tarefa_padrao or 0),
        tarefa=str(p.get("tarefa") or p.get("nomeTarefa") or nome_tarefa_padrao),
        data_entrada_tarefa=p.get("dataEntradaTarefa"),
        aguardando_prazo_disponivel=ag_disp,
        estado_aguardando_prazo=estado_str,
        id_orgao_julgador=int(oj_raw) if oj_raw is not None else None,
        raw=p,
    )


def _eh_apenas_gigs_xs1(atividades: Any) -> bool:
    """True se o processo possui atividade(s) GIGS mas TODAS são exatamente 'xs1'."""
    if not isinstance(atividades, list) or not atividades:
        return False
    obs_list = [str(a.get("observacao") or "").strip().lower() for a in atividades if isinstance(a, dict)]
    return bool(obs_list) and all(o == "xs1" for o in obs_list)


def classificar_processos_agrupamento(
    client_ou_driver: Union[PjeApiClient, Any],
    id_agrupamento: Union[int, str],
    *,
    fases: Optional[Sequence[str]] = None,
    id_tarefa: Optional[int] = None,
    nome_tarefa: Optional[str] = None,
    confirmar_gigs_individual: bool = True,
    consultar_escaninho: bool = True,
    ids_escaninho_cache: Optional[Set[int]] = None,
    verificar_aguardando_prazo_nos_livres: bool = False,
    excetuar_apenas_xs1: bool = False,
    tamanho_pagina: int = 100,
    max_paginas: int = 50,
    timeout: int = 25,
    grau: int = 1,
) -> Dict[str, Any]:
    """Classifica processos de um agrupamento (14/8/6) em livres, nao_livres, apenas_xs1 e com_doc_nao_apreciado.

    Regras (equivalentes ao DOM do PJe):
      - `nao_livres`: possui GIGS (lote ou individual), comentário ou responsável
        (exceto quando `excetuar_apenas_xs1=True` e o único motivo for GIGS `xs1`, sem comentário/responsável).
      - `apenas_xs1`: sem comentário/responsável e todas as atividades GIGS abertas são `xs1`.
      - `com_doc_nao_apreciado`: sem GIGS/comentário/responsável, mas com petição/documento não apreciado.
      - `livres`: sem GIGS, sem comentário, sem responsável e sem doc não apreciado.
    """
    t0 = time.monotonic()
    client = _resolver_cliente(client_ou_driver, grau=grau)

    fases_lista = list(fases) if fases else None
    fases_norm = {_norm(f) for f in fases_lista} if fases_lista else set()
    tarefa_norm = _norm(nome_tarefa) if nome_tarefa else ""

    brutos = client.listar_agrupamento_processos(
        id_agrupamento,
        fases=fases_lista,
        id_tarefa=id_tarefa,
        tamanho_pagina=tamanho_pagina,
        max_paginas=max_paginas,
        timeout=timeout,
    )

    base: List[Dict[str, Any]] = []
    for p in brutos:
        if p.get("id") is None:
            continue
        fase_p = _norm(p.get("faseProcessual") or p.get("labelFaseProcessual"))
        tarefa_p = _norm(p.get("tarefa") or p.get("nomeTarefa"))
        id_t = p.get("idTarefa")
        fase_ok = not fases_norm or fase_p in fases_norm
        tarefa_ok = (
            (id_tarefa is None and not tarefa_norm)
            or (id_tarefa is not None and id_t == id_tarefa)
            or (bool(tarefa_norm) and tarefa_p == tarefa_norm)
        )
        if fase_ok and tarefa_ok:
            base.append(p)

    ids_base = [int(p["id"]) for p in base]
    mapa_gigs_lote = client.tipos_atividades_gigs_lote(ids_base, timeout=timeout) if ids_base else {}
    if mapa_gigs_lote is None:
        logger.warning(
            "[FILTRO_AGRUPAMENTO] tiposatividades/poridsprocessos falhou (agrup=%s) — forçando confirmação individual",
            id_agrupamento,
        )
        mapa_gigs_lote = {}
        confirmar_gigs_individual = True

    if ids_escaninho_cache is not None:
        ids_escaninho = ids_escaninho_cache
    elif consultar_escaninho and ids_base:
        ids_escaninho = _buscar_ids_escaninho_nao_apreciados(
            client, tamanho_pagina=tamanho_pagina, timeout=timeout,
        )
    else:
        ids_escaninho = set()

    livres: List[ProcessoAnaliseFiltrado] = []
    nao_livres: List[ProcessoAnaliseFiltrado] = []
    apenas_xs1: List[ProcessoAnaliseFiltrado] = []
    com_doc_nao_apreciado: List[ProcessoAnaliseFiltrado] = []
    candidatos_livres: List[Dict[str, Any]] = []

    for p in base:
        pid_int = int(p["id"])
        tem_gigs = pid_int in mapa_gigs_lote or bool(p.get("dataPrazoFinal"))
        tem_com = _tem_comentario(p)
        tem_resp = _tem_responsavel(p)
        if tem_gigs or tem_com or tem_resp:
            if excetuar_apenas_xs1 and tem_gigs and not tem_com and not tem_resp:
                ativs_nl = client.atividades_gigs(str(pid_int))
                if _eh_apenas_gigs_xs1(ativs_nl):
                    apenas_xs1.append(
                        _instanciar_processo_filtrado(
                            p, id_tarefa_padrao=id_tarefa or 0, nome_tarefa_padrao=nome_tarefa or "",
                        )
                    )
                    continue
            nao_livres.append(
                _instanciar_processo_filtrado(
                    p, id_tarefa_padrao=id_tarefa or 0, nome_tarefa_padrao=nome_tarefa or "",
                )
            )
            continue
        if _tem_doc_nao_apreciado_campo(p) or pid_int in ids_escaninho:
            com_doc_nao_apreciado.append(
                _instanciar_processo_filtrado(
                    p, id_tarefa_padrao=id_tarefa or 0, nome_tarefa_padrao=nome_tarefa or "",
                )
            )
            continue
        candidatos_livres.append(p)

    for p in candidatos_livres:
        pid_int = int(p["id"])
        tid = int(p.get("idTarefa") or id_tarefa or 0)

        if confirmar_gigs_individual:
            ativs = client.atividades_gigs(str(pid_int))
            if isinstance(ativs, list) and len(ativs) > 0:
                if excetuar_apenas_xs1 and _eh_apenas_gigs_xs1(ativs):
                    apenas_xs1.append(
                        _instanciar_processo_filtrado(
                            p, id_tarefa_padrao=tid, nome_tarefa_padrao=nome_tarefa or "",
                        )
                    )
                else:
                    nao_livres.append(
                        _instanciar_processo_filtrado(
                            p, id_tarefa_padrao=tid, nome_tarefa_padrao=nome_tarefa or "",
                        )
                    )
                continue

        ag_disp: Optional[bool] = None
        if verificar_aguardando_prazo_nos_livres and tid:
            ag_disp = _estado_transicao_aguardando_prazo(client, pid_int, tid, timeout=timeout)

        livres.append(
            _instanciar_processo_filtrado(
                p, id_tarefa_padrao=tid, nome_tarefa_padrao=nome_tarefa or "", ag_disp=ag_disp,
            )
        )

    diag = {
        "ok": True,
        "agrupamento": id_agrupamento,
        "ms": round((time.monotonic() - t0) * 1000),
        "total": len(base),
        "livres": len(livres),
        "nao_livres": len(nao_livres),
        "apenas_xs1": len(apenas_xs1),
        "com_doc_nao_apreciado": len(com_doc_nao_apreciado),
        "escaninho_ids_nao_apreciados": len(ids_escaninho),
    }
    logger.info(
        "[FILTRO_AGRUPAMENTO] agrup=%s total=%d | livres=%d nao_livres=%d apenas_xs1=%d doc_nao_apreciado=%d (%dms)",
        id_agrupamento,
        diag["total"],
        diag["livres"],
        diag["nao_livres"],
        diag["apenas_xs1"],
        diag["com_doc_nao_apreciado"],
        diag["ms"],
    )
    return {
        "ok": True,
        "livres": livres,
        "nao_livres": nao_livres,
        "apenas_xs1": apenas_xs1,
        "com_doc_nao_apreciado": com_doc_nao_apreciado,
        "ids_escaninho": ids_escaninho,
        "diagnostico": diag,
    }


__all__ = [
    "FASES_LIQUIDACAO_EXECUCAO",
    "ID_AGRUPAMENTO_ANALISE",
    "ID_AGRUPAMENTO_CUMPRIMENTO",
    "ID_AGRUPAMENTO_PRAZOS_VENCIDOS",
    "ID_TAREFA_ANALISE",
    "ID_TAREFA_CUMPRIMENTO",
    "NOME_TAREFA_ANALISE",
    "NOME_TRANSICAO_AGUARDANDO_PRAZO",
    "NOME_TRANSICAO_ANALISE",
    "NOME_TRANSICAO_CUMPRIMENTO",
    "ProcessoAnaliseFiltrado",
    "classificar_processos_agrupamento",
    "filtrar_processos_analise_livres",
]
