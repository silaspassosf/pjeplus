import logging
from typing import List, Dict, Any
from .api_client import AtividadePEC
from PEC.executor import executar_acao_pec

logger = logging.getLogger(__name__)

def processo_ja_executado_pec(numero: str, progresso: Dict) -> bool:
    return progresso.get(numero) is True

def marcar_processo_executado_pec(numero: str, progresso: Dict):
    progresso[numero] = True

def get_or_create_driver_sisbajud(driver):
    # Stub para integração real
    return driver

def fechar_driver_sisbajud_global():
    pass

class PECExecutorIndividual:
    def __init__(self, driver, progresso: Dict):
        self.driver = driver
        self.progresso = progresso
        self.driver_sisb = None

    def processar_atividade(self, atv: AtividadePEC) -> bool:
        numero = atv.numero_processo
        if processo_ja_executado_pec(numero, self.progresso):
            logger.info(f"[SKIP] {numero} já executado")
            return True
        try:
            id_processo = getattr(atv, 'id_processo', None)
            target = id_processo or numero
            if not self._abrir_processo(target):
                return False
            acoes = atv.acoes
            if not acoes:
                logger.warning(f"[WARN] {numero}: nenhuma ação mapeada para '{atv.observacao}'")
                return False
            driver_exec = self.driver
            dados_processo = {
                'numero_processo': atv.numero_processo,
                'id_processo': getattr(atv, 'id_processo', None),
                'observacao': atv.observacao,
                'status': atv.status,
                'data_prazo': atv.data_prazo,
                'tipo_gigs': atv.tipo_gigs,
            }
            if self._is_sisbajud(acoes):
                if not self.driver_sisb:
                    self.driver_sisb = get_or_create_driver_sisbajud(self.driver)
                driver_exec = self.driver_sisb or self.driver
            sucesso = True
            for acao in acoes:
                if not executar_acao_pec(driver_exec, acao, numero, atv.observacao, debug=True, dados_processo=dados_processo):
                    sucesso = False
                    break
            if sucesso:
                marcar_processo_executado_pec(numero, self.progresso)
                logger.info(f"[OK] {numero} processado com sucesso")
            else:
                logger.error(f"[FAIL] {numero} falhou na execução")
            return sucesso
        except Exception as e:
            if 'RESTART_PEC' in str(e) or 'acesso negado' in str(e).lower():
                raise
            logger.error(f"[ERRO] {numero}: {e}")
            return False
        finally:
            self._fechar_abas_extras()

    def _abrir_processo(self, numero) -> bool:
        try:
            numero_texto = str(numero or '')
            numero_limpo = ''.join(filter(str.isdigit, numero_texto))
            if len(numero_limpo) == 20:
                url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_limpo}/detalhe"
            else:
                url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_texto}/detalhe"
            self.driver.get(url)
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            if 'acesso-negado' in self.driver.current_url.lower():
                raise Exception(f"RESTART_PEC: Acesso negado ao abrir {numero}")
            return True
        except Exception as e:
            logger.error(f"[ABRIR] Falha ao abrir {numero}: {e}")
            return False

    def _is_sisbajud(self, acoes: List[Any]) -> bool:
        for acao in acoes:
            nome = getattr(acao, '__name__', str(acao)).lower()
            if 'sisb' in nome or 'bloqueio' in nome:
                return True
        return False

    def _fechar_abas_extras(self):
        try:
            abas = self.driver.window_handles
            if len(abas) <= 1:
                return
            aba_principal = abas[0]
            for aba in abas[1:]:
                try:
                    self.driver.switch_to.window(aba)
                    self.driver.close()
                except Exception:
                    pass
            self.driver.switch_to.window(aba_principal)
        except Exception:
            pass

    def cleanup(self):
        # Não fechar driver_sisbajud aqui para manter sessão persistente
        self._fechar_abas_extras()

    def finalizar(self):
        # Encerrar driver SISBAJUD explicitamente ao final do fluxo
        if self.driver_sisb:
            fechar_driver_sisbajud_global()
            self.driver_sisb = None
