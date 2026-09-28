"""Shim de compatibilidade — reexporta de Fix.browser_suporte."""
from Fix.browser_suporte import (  # noqa: F401
    limpar_overlays_headless,
    scroll_to_element_safe,
    click_headless_safe,
    is_headless_mode,
)
