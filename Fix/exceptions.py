# Hierarquia de exceções tipadas para o PJePlus

class PJePlusError(Exception):
    """Exceção base para erros do PJePlus."""
    pass

class DriverFatalError(PJePlusError):
    """Driver inutilizável."""
    pass

class ElementoNaoEncontradoError(PJePlusError):
    """Elemento não localizado."""
    def __init__(self, seletor: str, contexto: str = ""):
        super().__init__(f"Elemento não encontrado: {seletor} (contexto: {contexto})")
        self.seletor = seletor
        self.contexto = contexto

class TimeoutFluxoError(PJePlusError):
    """Timeout de operação."""
    def __init__(self, operacao: str, timeout: int):
        super().__init__(f"Timeout na operação: {operacao} (timeout: {timeout}s)")
        self.operacao = operacao
        self.timeout = timeout

class NavegacaoError(PJePlusError):
    """Falha ao trocar aba ou navegar."""
    pass

class LoginError(PJePlusError):
    """Falha de login."""
    pass
