"""Fix.exceptions - Exceções customizadas"""
class PJePlusError(Exception): pass
class ElementoNaoEncontradoError(PJePlusError): pass
class NavegacaoError(PJePlusError): pass
__all__ = ['PJePlusError', 'ElementoNaoEncontradoError', 'NavegacaoError']
