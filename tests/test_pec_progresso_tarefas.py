# -*- coding: utf-8 -*-
"""Testes unitários para o controle de progresso por tarefa no fluxo PEC."""

import unittest
from unittest.mock import patch, MagicMock

from PEC.runtime_pec import (
    AtividadePEC,
    obter_chave_tarefa_pec,
    tarefa_ja_executada_pec,
    marcar_tarefa_executada_pec,
    processo_ja_executado_pec,
)


class TestPECProgressoTarefas(unittest.TestCase):

    def setUp(self):
        self.atv_sob = AtividadePEC(
            numero_processo="1000886-64.2019.5.02.0703",
            observacao="xs sob 24",
            status="PENDENTE",
            data_prazo="2026-10-15",
            tipo_gigs="Sobrestamento",
            id_processo=2716938,
        )
        self.atv_exeq = AtividadePEC(
            numero_processo="1000886-64.2019.5.02.0703",
            observacao="xs pec exequente pessoal",
            status="PENDENTE",
            data_prazo="2026-10-15",
            tipo_gigs="Intimação",
            id_processo=2716938,
        )

    def test_obter_chave_tarefa_pec_formatacao(self):
        """Chave de tarefa deve combinar número CNJ formatado e observação normalizada."""
        chave_sob = obter_chave_tarefa_pec(self.atv_sob)
        self.assertEqual(chave_sob, "1000886-64.2019.5.02.0703::xs sob 24")

        chave_exeq = obter_chave_tarefa_pec(self.atv_exeq)
        self.assertEqual(chave_exeq, "1000886-64.2019.5.02.0703::xs pec exequente pessoal")

    def test_obter_chave_tarefa_com_id_atividade(self):
        """Quando id_atividade estiver presente, deve ser incluído na chave."""
        atv_com_id = AtividadePEC(
            numero_processo="10008866420195020703",
            observacao="xs pec exequente pessoal",
            status="PENDENTE",
            data_prazo="2026-10-15",
            tipo_gigs="Intimação",
            id_processo=2716938,
            id_atividade=998877,
        )
        chave = obter_chave_tarefa_pec(atv_com_id)
        self.assertEqual(chave, "1000886-64.2019.5.02.0703::id:998877::xs pec exequente pessoal")

    def test_multiplas_tarefas_mesmo_processo_nao_pulam(self):
        """Executar uma tarefa (ex: xs sob 24) NÃO deve fazer o PEC pular outra tarefa (ex: xs pec exequente pessoal)."""
        progresso = {
            "processos_executados": [],
            "processos_com_erro": [],
            "tarefas_executadas": [],
            "tarefas_com_erro": [],
            "datas_execucao": {},
        }

        # Inicialmente nenhuma tarefa foi executada
        self.assertFalse(tarefa_ja_executada_pec(self.atv_sob, progresso))
        self.assertFalse(tarefa_ja_executada_pec(self.atv_exeq, progresso))

        # Executa e marca a primeira tarefa (xs sob 24)
        with patch('PEC.runtime_pec.salvar_progresso_pec'):
            marcar_tarefa_executada_pec(self.atv_sob, progresso, status="SUCESSO")

        # Agora xs sob 24 está executada, mas xs pec exequente pessoal NÃO!
        self.assertTrue(tarefa_ja_executada_pec(self.atv_sob, progresso))
        self.assertFalse(tarefa_ja_executada_pec(self.atv_exeq, progresso))

        # Executa e marca a segunda tarefa (xs pec exequente pessoal)
        with patch('PEC.runtime_pec.salvar_progresso_pec'):
            marcar_tarefa_executada_pec(self.atv_exeq, progresso, status="SUCESSO")

        # Agora ambas constam como executadas
        self.assertTrue(tarefa_ja_executada_pec(self.atv_sob, progresso))
        self.assertTrue(tarefa_ja_executada_pec(self.atv_exeq, progresso))

    def test_marcar_tarefa_com_erro(self):
        """Tarefa com erro deve ser registrada em tarefas_com_erro e não bloquear execução futura."""
        progresso = {
            "processos_executados": [],
            "processos_com_erro": [],
            "tarefas_executadas": [],
            "tarefas_com_erro": [],
            "datas_execucao": {},
        }

        with patch('PEC.runtime_pec.salvar_progresso_pec'):
            marcar_tarefa_executada_pec(self.atv_exeq, progresso, status="ERRO", detalhes="Timeout de rede")

        self.assertIn("1000886-64.2019.5.02.0703::xs pec exequente pessoal", progresso["tarefas_com_erro"])
        self.assertNotIn("1000886-64.2019.5.02.0703::xs pec exequente pessoal", progresso["tarefas_executadas"])
        # Como não teve sucesso, tarefa_ja_executada_pec retorna False permitindo retry
        self.assertFalse(tarefa_ja_executada_pec(self.atv_exeq, progresso))


if __name__ == '__main__':
    unittest.main()
