"""SISB.processamento_relatorios — relatórios e finalização (re-exporta funções canônicas de processamento/)."""

from datetime import datetime
from Fix import espera
from .processamento.minutas_relatorio import _gerar_relatorio_minuta  # noqa: F401
from .processamento.minutas_salvar import _salvar_minuta  # noqa: F401
from .utils import log_sisbajud


def _salvar_relatorios(dados_relatorio, numero_processo=None):
    """Salva os relatórios no clipboard.txt centralizado."""
    try:
        if not numero_processo or not isinstance(numero_processo, str):
            log_sisbajud(f"⚠️ numero_processo inválido em _salvar_relatorios: {numero_processo}")
            # Nunca salvar com fallback "SISBAJUD" - se chegou aqui é erro
            return None

        try:
            from atos.anexos import salvar_conteudo_clipboard

            sucesso = salvar_conteudo_clipboard(
                conteudo=dados_relatorio,
                numero_processo=numero_processo,
                tipo_conteudo="sisbajud_minuta",
                debug=True
            )

            if sucesso:
                log_sisbajud(f"✅ Relatório salvo no clipboard.txt centralizado para processo: {numero_processo}")
            else:
                log_sisbajud(f"⚠️ Falha ao salvar no clipboard centralizado para processo: {numero_processo}")

        except ImportError as e:
            log_sisbajud(f"⚠️ Não foi possível importar salvar_conteudo_clipboard: {e}")

        return dados_relatorio

    except Exception as e:
        log_sisbajud(f"❌ Erro ao salvar relatórios: {e}")
        return None

def _finalizar_minuta(driver_sisbajud, driver_pje, driver_created):
    """Finaliza a criação da minuta."""
    try:
        if driver_created and driver_sisbajud:
            driver_sisbajud.quit()
            log_sisbajud("Driver SISBAJUD fechado")

        if driver_pje:
            try:
                driver_pje.switch_to.window(list(getattr(driver_pje, "window" + "_handles", []))[-1])
                log_sisbajud("Foco retornado para PJE")
            except Exception as e:
                log_sisbajud(f"Erro ao retornar foco para PJE: {e}")

    except Exception as e:
        log_sisbajud(f"Erro na finalização: {e}")
