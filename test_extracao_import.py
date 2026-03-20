import sys
import os
import importlib.util
from types import ModuleType


def load_module_from_path(path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location('extracao_documento', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    try:
        path = os.path.join(os.getcwd(), 'Fix', 'extracao_documento.py')
        m = load_module_from_path(path)
        ok = (
            hasattr(m, 'extrair_direto'),
            hasattr(m, 'extrair_documento'),
            hasattr(m, 'extrair_pdf'),
            hasattr(m, '_extrair_formatar_texto'),
        )
        print('IMPORT_OK', ok)
        return 0
    except Exception:
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
