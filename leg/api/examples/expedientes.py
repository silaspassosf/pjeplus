"""Exemplo: api/examples/expedientes.py
Uso:
  from requests import Session
  s = Session()
  # carregar cookies/autenticação em s
  expedientes = get_expedientes(s, 'https://seu-pje', 6108528)
"""
from datetime import datetime, timedelta
from typing import List, Optional

def _fmt_ddmmyy(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    except Exception:
        return None
    return dt.strftime('%d/%m/%y')

def _compute_fim_prazo(item):
    if item.get('fimDoPrazoLegal'):
        return item['fimDoPrazoLegal']
    prazo = item.get('prazoLegal')
    base_iso = item.get('dataCiencia') or item.get('dataCriacao')
    try:
        prazo_days = int(prazo) if prazo is not None else None
    except Exception:
        prazo_days = None
    if prazo_days is None or not base_iso:
        return None
    try:
        base = datetime.fromisoformat(base_iso.replace('Z', '+00:00'))
    except Exception:
        return None
    return (base + timedelta(days=prazo_days)).isoformat()

def get_expedientes(session, base_url: str, processo_id: int, tamanho_pagina: int = 50) -> List[dict]:
    """Retorna lista normalizada de expedientes para uso programático.

    session: requests.Session autenticada com cookies/headers.
    base_url: url base do PJe (ex: 'https://pje.trt2.jus.br') sem barra final.
    processo_id: id numérico do processo.
    """
    pagina = 1
    resultados = []
    while True:
        url = f"{base_url}/pje-comum-api/api/processos/id/{processo_id}/expedientes"
        params = {'pagina': pagina, 'tamanhoPagina': tamanho_pagina, 'instancia': 1}
        r = session.get(url, params=params)
        r.raise_for_status()
        body = r.json()
        items = body.get('resultado') or []
        for it in items:
            fim_iso = _compute_fim_prazo(it)
            resultados.append({
                'destinatario': it.get('nomePessoaParte'),
                'tipo': it.get('tipoExpediente'),
                'meio': it.get('meioExpediente'),
                'dataCriacao': _fmt_ddmmyy(it.get('dataCriacao')),
                'dataCiencia': _fmt_ddmmyy(it.get('dataCiencia')),
                'prazo': it.get('prazoLegal'),
                'fimPrazo': _fmt_ddmmyy(fim_iso),
                'fechado': bool(it.get('fechado'))
            })
        if not isinstance(items, list) or len(items) < tamanho_pagina:
            break
        pagina += 1
    return resultados
