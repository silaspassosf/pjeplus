"""Shim para compatibilidade entre a pasta 'Triagem' (existente)
e o pacote lowercase `triagem`.

Esse arquivo permite `import triagem` e ainda preserva compatibilidade
com a implementação legada quando a pasta `triagem/` ainda não estiver
acessível como package.
"""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_DIR = HERE / 'triagem'
LEGACY_PACKAGE = 'Triagem'

if PACKAGE_DIR.is_dir():
    __path__ = [str(PACKAGE_DIR)]

__all__ = ['triagem_peticao']

try:
    if PACKAGE_DIR.is_dir():
        from .service import triagem_peticao
    else:
        raise ImportError('package folder not found')
except Exception:
    try:
        pkg = importlib.import_module(LEGACY_PACKAGE)
        triagem_peticao = getattr(pkg, 'triagem_peticao', None)
        if triagem_peticao is None:
            raise ImportError
    except Exception:
        try:
            from tr import triagem_peticao
        except Exception:
            def triagem_peticao(*args, **kwargs):
                raise ImportError('triagem.triagem_peticao: dependencia legada `tr.triagem_peticao` nao importavel no momento')
