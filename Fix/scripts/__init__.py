from pathlib import Path
_cache: dict[str, str] = {}

def carregar_js(nome_arquivo: str, pasta: str | None = None) -> str:
    if pasta is None:
        pasta = Path(__file__).parent
    chave = str(Path(pasta) / nome_arquivo)
    if chave not in _cache:
        _cache[chave] = Path(pasta / nome_arquivo).read_text(encoding="utf-8")
    return _cache[chave]

def limpar_cache_js() -> None:
    _cache.clear()
