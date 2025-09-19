"""
Motor Principal do Sistema P2B
Coordena todos os componentes: Timeline, Estado, Prescrição, etc.
"""

from ..processors.timeline_processor import TimelineProcessor
from ..processors.prescription_handler import PrescriptionHandler
from ..core.state_manager import StateManager


class P2BEngine:
    """
    Motor principal do sistema P2B
    Coordena todas as operações e componentes
    """

    def __init__(self, debug=False, state_file="progresso_p2b.json"):
        """
        Inicializa o motor P2B

        Args:
            debug (bool): Habilita modo debug
            state_file (str): Arquivo de estado
        """
        self.debug = debug
        self.state_manager = StateManager(state_file)

        # Componentes principais
        self.timeline_processor = TimelineProcessor(debug=debug)
        self.prescription_handler = PrescriptionHandler(debug=debug)

        print("[P2B_ENGINE] ✅ Motor P2B inicializado")

    def analyze_timeline(self, driver):
        """
        Analisa a timeline do processo atual

        Args:
            driver: Instância do WebDriver

        Returns:
            list: Documentos encontrados
        """
        return self.timeline_processor.analyze_timeline(driver)

    def process_prescription(self, driver, process_id=None):
        """
        Processa prescrição completa

        Args:
            driver: Instância do WebDriver
            process_id (str): ID do processo

        Returns:
            dict: Resultado do processamento
        """
        return self.prescription_handler.handle_prescription(driver, process_id)

    def is_process_already_executed(self, process_id):
        """
        Verifica se processo já foi executado

        Args:
            process_id (str): ID do processo

        Returns:
            bool: True se já executado
        """
        return self.state_manager.is_process_executed(process_id)

    def mark_process_executed(self, process_id):
        """
        Marca processo como executado

        Args:
            process_id (str): ID do processo
        """
        self.state_manager.mark_process_executed(process_id)

    def get_execution_statistics(self):
        """
        Retorna estatísticas de execução

        Returns:
            dict: Estatísticas
        """
        return self.state_manager.get_statistics()

    def reset_execution_state(self):
        """
        Reseta o estado de execução

        Returns:
            bool: True se resetado com sucesso
        """
        return self.state_manager.reset_state()

    def list_executed_processes(self):
        """
        Lista processos já executados

        Returns:
            list: Lista de processos executados
        """
        return self.state_manager.list_executed_processes()

    # Métodos de compatibilidade com código legado
    def carregar_progresso_p2b(self):
        """Compatibilidade: carrega progresso (deprecated)"""
        print("[P2B_ENGINE][WARN] carregar_progresso_p2b() é deprecated. Use get_execution_statistics()")
        return self.state_manager.load_state()

    def salvar_progresso_p2b(self, state):
        """Compatibilidade: salva progresso (deprecated)"""
        print("[P2B_ENGINE][WARN] salvar_progresso_p2b() é deprecated. Use state_manager.save_state()")
        self.state_manager.save_state(state)

    def processo_ja_executado_p2b(self, process_id):
        """Compatibilidade: verifica se executado (deprecated)"""
        print("[P2B_ENGINE][WARN] processo_ja_executado_p2b() é deprecated. Use is_process_already_executed()")
        return self.is_process_already_executed(process_id)

    def marcar_processo_executado_p2b(self, process_id):
        """Compatibilidade: marca como executado (deprecated)"""
        print("[P2B_ENGINE][WARN] marcar_processo_executado_p2b() é deprecated. Use mark_process_executed()")
        self.mark_process_executed(process_id)