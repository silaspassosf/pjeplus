"""
SISB.processamento_relatorios - Módulo de relatórios e finalização SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
Contém funções de salvar minuta, gerar relatórios e finalizar.
"""

import time
from datetime import datetime

def _salvar_minuta(driver):
    """Salva a minuta com múltiplas estratégias."""
    try:
        log_sisbajud("Salvando minuta...")

        # Estratégia 1: Botão principal
        script_salvar = """
        var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
        if (btnSalvar) {
            btnSalvar.closest('button').click();
            return true;
        }

        // Estratégia 2: Fallback
        var btnFallback = document.querySelector('button mat-icon.fa-save');
        if (btnFallback) {
            btnFallback.closest('button').click();
            return true;
        }

        return false;
        """

        if driver.execute_script(script_salvar):
            log_sisbajud("Botão salvar clicado")
            time.sleep(3)

            # Verificar se salvou
            status = driver.execute_script("""
            var btnAlterar = document.querySelector('button mat-icon.fa-edit');
            if (btnAlterar) {
                var btnTexto = btnAlterar.closest('button');
                if (btnTexto && btnTexto.textContent.includes('Alterar')) {
                    return 'SALVO';
                }
            }
            return 'NAO_SALVOU';
            """)

            if status == 'SALVO':
                log_sisbajud("Minuta salva com sucesso")
                return True
            else:
                log_sisbajud("Status de salvamento incerto")
                return False
        else:
            log_sisbajud("Falha ao clicar no botão salvar")
            return False

    except Exception as e:
        log_sisbajud(f"Erro ao salvar minuta: {e}", "ERROR")
        return False

def _gerar_relatorio_minuta(driver, numero_processo):
    """Gera relatório da minuta criada coletando dados reais da página SISBAJUD.
    
    Args:
        driver: WebDriver SISBAJUD
        numero_processo: String com número CNJ do processo (ex: "1000235-44.2015.5.02.0712")
    """
    try:
        log_sisbajud("Gerando relatório da minuta...")

        # Validar numero_processo
        if not numero_processo or not isinstance(numero_processo, str):
            log_sisbajud(f"⚠️ numero_processo inválido: {numero_processo}")
            numero_processo = "SISBAJUD"  # Fallback apenas em erro crítico

        # Importar função de coleta de dados completa
        try:
            from .core import coletar_dados_minuta_sisbajud
        except ImportError:
            log_sisbajud(f"Não foi possível importar coletar_dados_minuta_sisbajud do core")
            # Fallback para relatório simples
            dados_relatorio = f"""
            <h3>Minuta de Bloqueio SISBAJUD</h3>
            <p>Processo: {numero_processo or 'N/A'}</p>
            <p>Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            """
            return _salvar_relatorios(dados_relatorio, numero_processo)

        # Coletar dados reais da página SISBAJUD
        dados_relatorio = coletar_dados_minuta_sisbajud(driver)

        if not dados_relatorio:
            log_sisbajud("Não foi possível coletar dados da minuta, usando relatório básico")
            dados_relatorio = f"""
            <h3>Minuta de Bloqueio SISBAJUD</h3>
            <p>Processo: {numero_processo or 'N/A'}</p>
            <p>Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            """

        return _salvar_relatorios(dados_relatorio, numero_processo)

    except Exception as e:
        log_sisbajud(f"Erro ao gerar relatório: {e}")
        # Em caso de erro, gerar relatório básico (preservar numero_processo)
        dados_relatorio = f"""
        <h3>Minuta de Bloqueio SISBAJUD</h3>
        <p>Processo: {numero_processo or 'N/A'}</p>
        <p>Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        """
        return _salvar_relatorios(dados_relatorio, numero_processo)

def _salvar_relatorios(dados_relatorio, numero_processo=None):
    """Salva os relatórios no clipboard.txt centralizado.
    
    Args:
        dados_relatorio: Conteúdo HTML do relatório
        numero_processo: Número do processo (nunca None - garantido pelo chamador)
    """
    try:
        # Garantir que numero_processo seja sempre válido para busca posterior
        if not numero_processo or not isinstance(numero_processo, str):
            log_sisbajud(f"⚠️ numero_processo inválido em _salvar_relatorios: {numero_processo}")
            # Nunca salvar com fallback "SISBAJUD" - se chegou aqui é erro
            return None
        
        # Usar clipboard centralizado do PEC/anexos.py
        try:
            from PEC.anexos import salvar_conteudo_clipboard

            sucesso = salvar_conteudo_clipboard(
                conteudo=dados_relatorio,
                numero_processo=numero_processo,  # Sempre passar o número real
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
        # Fechar driver se foi criado aqui
        if driver_created and driver_sisbajud:
            driver_sisbajud.quit()
            log_sisbajud("Driver SISBAJUD fechado")

        # Retornar foco para PJE
        if driver_pje:
            try:
                driver_pje.switch_to.window(driver_pje.window_handles[-1])
                log_sisbajud("Foco retornado para PJE")
            except Exception as e:
                log_sisbajud(f"Erro ao retornar foco para PJE: {e}")

    except Exception as e:
        log_sisbajud(f"Erro na finalização: {e}")