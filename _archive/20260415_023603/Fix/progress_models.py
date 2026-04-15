"""Fix.progress_models — stub de compatibilidade.

O conteúdo deste módulo foi consolidado em Fix.progress.models.
Imports daqui continuam funcionando mas emitem DeprecationWarning.
"""
import warnings
warnings.warn(
    "Fix.progress_models está obsoleto; importe de Fix.progress",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.progress.models import (  # noqa: F401,E402
    StatusModulo,
    NivelLog,
    Checkpoint,
    StatusModuloData,
    RegistroLog,
)

__all__ = ["StatusModulo", "NivelLog", "Checkpoint", "StatusModuloData", "RegistroLog"]
