"""
Gerenciador unificado de estado para o sistema P2B
Substitui todas as funções duplicadas de progresso (carregar/salvar_progresso)
"""

import os
import json
from datetime import datetime


class StateManager:
    """
    Gerenciador unificado de estado para controle de progresso
    Centraliza todas as operações de carregamento e salvamento de estado
    """

    def __init__(self, state_file="progresso_p2b.json"):
        """
        Inicializa o gerenciador de estado

        Args:
            state_file (str): Caminho do arquivo de estado
        """
        self.state_file = state_file
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self):
        """Garante que o arquivo de estado existe"""
        if not os.path.exists(self.state_file):
            self._create_default_state()

    def _create_default_state(self):
        """Cria arquivo de estado com valores padrão"""
        default_state = {
            "processos_executados": [],
            "session_active": True,
            "last_update": None,
            "statistics": {
                "total_processos": 0,
                "sucessos": 0,
                "falhas": 0,
                "ultima_execucao": None
            }
        }
        self._save_state(default_state)

    def load_state(self):
        """
        Carrega o estado do arquivo

        Returns:
            dict: Estado atual
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[STATE_MANAGER][AVISO] Erro ao carregar estado: {e}")

        # Fallback para estado padrão
        return self._get_default_state()

    def _get_default_state(self):
        """Retorna estado padrão"""
        return {
            "processos_executados": [],
            "session_active": True,
            "last_update": None
        }

    def save_state(self, state):
        """
        Salva o estado no arquivo

        Args:
            state (dict): Estado a ser salvo
        """
        try:
            state["last_update"] = datetime.now().isoformat()
            self._save_state(state)
        except Exception as e:
            print(f"[STATE_MANAGER][ERRO] Falha ao salvar estado: {e}")

    def _save_state(self, state):
        """Salva estado no arquivo (método interno)"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def is_process_executed(self, process_id):
        """
        Verifica se um processo já foi executado

        Args:
            process_id (str): ID do processo

        Returns:
            bool: True se já foi executado
        """
        if not process_id:
            return False

        state = self.load_state()
        return process_id in state.get("processos_executados", [])

    def mark_process_executed(self, process_id, mark_as_executed=True):
        """
        Marca ou desmarca um processo como executado

        Args:
            process_id (str): ID do processo
            mark_as_executed (bool): True para marcar como executado, False para remover
        """
        if not process_id:
            return

        state = self.load_state()
        executed_list = state.setdefault("processos_executados", [])

        if mark_as_executed:
            if process_id not in executed_list:
                executed_list.append(process_id)
                print(f"[STATE_MANAGER] Processo {process_id} marcado como executado")
        else:
            if process_id in executed_list:
                executed_list.remove(process_id)
                print(f"[STATE_MANAGER] Processo {process_id} removido da lista de executados")

        self.save_state(state)

    def reset_state(self):
        """
        Reseta o estado completamente

        Returns:
            bool: True se resetado com sucesso
        """
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                print("[STATE_MANAGER][RESET] ✅ Estado resetado com sucesso")
            else:
                print("[STATE_MANAGER][RESET] Arquivo de estado não existe")

            self._ensure_state_file_exists()
            return True

        except Exception as e:
            print(f"[STATE_MANAGER][RESET][ERRO] Falha ao resetar: {e}")
            return False

    def list_executed_processes(self):
        """
        Lista todos os processos executados

        Returns:
            list: Lista de processos executados
        """
        state = self.load_state()
        executed = state.get("processos_executados", [])

        if executed:
            print(f"[STATE_MANAGER][LIST] {len(executed)} processos executados:")
            for i, proc in enumerate(executed, 1):
                print(f"  {i:3d}. {proc}")
        else:
            print("[STATE_MANAGER][LIST] Nenhum processo executado ainda")

        return executed

    def get_statistics(self):
        """
        Retorna estatísticas do estado

        Returns:
            dict: Estatísticas
        """
        state = self.load_state()
        executed = state.get("processos_executados", [])

        return {
            "total_executados": len(executed),
            "session_active": state.get("session_active", True),
            "last_update": state.get("last_update"),
            "processos": executed
        }

    def update_statistics(self, success=True):
        """
        Atualiza estatísticas de execução

        Args:
            success (bool): True se foi sucesso, False se foi falha
        """
        state = self.load_state()
        stats = state.setdefault("statistics", {
            "total_processos": 0,
            "sucessos": 0,
            "falhas": 0,
            "ultima_execucao": None
        })

        stats["total_processos"] += 1
        if success:
            stats["sucessos"] += 1
        else:
            stats["falhas"] += 1

        stats["ultima_execucao"] = datetime.now().isoformat()
        self.save_state(state)