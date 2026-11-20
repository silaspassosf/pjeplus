"""Fix/calendario.py — Calendário unificado de dias úteis (TRT2) usado por PEC, SISB e x.py."""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Set, Tuple

CALENDARIO_DIAS_UTEIS_PATH = Path("dias-uteis-trt2-2026.json")
_CACHE_DIAS: Optional[Set[date]] = None
_CACHE_INTERVALO: Optional[Tuple[date, date]] = None


def _arquivos_calendario():
    achados = sorted(Path(".").glob("dias-uteis-trt2-*.json"))
    if achados:
        return achados
    return [CALENDARIO_DIAS_UTEIS_PATH] if CALENDARIO_DIAS_UTEIS_PATH.exists() else []


def carregar_calendario_dias_uteis() -> Tuple[Set[date], Optional[Tuple[date, date]]]:
    """Carrega e cacheia os conjuntos de dias úteis de `dias-uteis-trt2-*.json`."""
    global _CACHE_DIAS, _CACHE_INTERVALO
    if _CACHE_DIAS is not None:
        return _CACHE_DIAS, _CACHE_INTERVALO

    dias: Set[date] = set()
    anos: Set[int] = set()
    for arq in _arquivos_calendario():
        m = re.search(r"(\d{4})", arq.name)
        if m:
            anos.add(int(m.group(1)))
        try:
            conteudo = json.loads(arq.read_text(encoding="utf-8"))
            for entrada in conteudo.get("dias_uteis", []):
                try:
                    dias.add(datetime.fromisoformat(entrada).date())
                except ValueError:
                    continue
        except Exception:
            continue

    _CACHE_DIAS = dias
    _CACHE_INTERVALO = (date(min(anos), 1, 1), date(max(anos), 12, 31)) if anos else None
    return _CACHE_DIAS, _CACHE_INTERVALO


def eh_dia_util(alvo: date) -> bool:
    dias, intervalo = carregar_calendario_dias_uteis()
    if dias and intervalo and intervalo[0] <= alvo <= intervalo[1]:
        return alvo in dias
    return alvo.weekday() < 5


def proximo_dia_util(data_base: date, inclusive: bool = True) -> date:
    """Primeiro dia útil a partir de `data_base` (inclusive=True) ou estritamente após (inclusive=False)."""
    alvo = data_base if inclusive else (data_base + timedelta(days=1))
    for _ in range(60):
        if eh_dia_util(alvo):
            return alvo
        alvo += timedelta(days=1)
    return alvo


def somar_dias_uteis(data_base: Optional[date], quantidade: int) -> Optional[date]:
    if not data_base or quantidade <= 0:
        return data_base
    atual = data_base
    acumulado = 0
    for _ in range(1000):
        atual += timedelta(days=1)
        if eh_dia_util(atual):
            acumulado += 1
            if acumulado >= quantidade:
                return atual
    return None


def dia_util_anterior(data_ref: date) -> date:
    """Retorna o dia útil imediatamente anterior a `data_ref`."""
    alvo = data_ref - timedelta(days=1)
    for _ in range(30):
        if eh_dia_util(alvo):
            return alvo
        alvo -= timedelta(days=1)
    return data_ref - timedelta(days=1)
