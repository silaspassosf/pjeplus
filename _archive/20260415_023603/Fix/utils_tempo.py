import time
import logging
logger = logging.getLogger(__name__)

TIME_ENABLED = True

def medir_tempo(label: str = None):
    """Decorator simples para medir tempo de funções de alto nível.

    Usage:
        @medir_tempo('nome')
        def func(...):
            ...
    """
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            if not TIME_ENABLED:
                return func(*args, **kwargs)
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                logger.info('[TEMPO] %s.%s: %.3fs', func.__name__, label or func.__name__, elapsed)
        try:
            _wrapper.__name__ = func.__name__
            _wrapper.__doc__ = func.__doc__
        except Exception:
            pass
        return _wrapper
    return _decorator
