"""Shim mínimo de compatibilidade para o pacote legado Fix.drivers."""

from .lifecycle import (
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
)

__all__ = [
    "criar_driver_PC",
    "criar_driver_VT",
    "criar_driver_notebook",
    "criar_driver_sisb_pc",
    "criar_driver_sisb_notebook",
    "finalizar_driver",
]