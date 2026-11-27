import importlib

_EXPORTS = {
	'PjeApiClient': ('.variaveis_client', 'PjeApiClient'),
	'session_from_driver': ('.variaveis_client', 'session_from_driver'),
	'buscar_todas_paginas': ('.variaveis_helpers', 'buscar_todas_paginas'),
	'ProcessoAnaliseFiltrado': ('.filtro_analise', 'ProcessoAnaliseFiltrado'),
	'filtrar_processos_analise_livres': ('.filtro_analise', 'filtrar_processos_analise_livres'),
}


def __getattr__(name: str):
	if name in _EXPORTS:
		import Fix.variaveis  # noqa: F401
		mod_name, attr = _EXPORTS[name]
		mod = importlib.import_module(mod_name, __name__)
		val = getattr(mod, attr)
		globals()[name] = val
		return val
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
	'PjeApiClient',
	'session_from_driver',
	'buscar_todas_paginas',
	'ProcessoAnaliseFiltrado',
	'filtrar_processos_analise_livres',
]
