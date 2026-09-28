"""Thin shim — reexporta de runtime_pec."""
from Fix.utils import remover_acentos, normalizar_texto  # noqa: F401 — canonical
from Fix.abas import fechar_abas_extras as _fechar_abas_extras  # noqa: F401
from .runtime_pec import gerar_regex_geral, _montar_url_processo  # noqa: F401
