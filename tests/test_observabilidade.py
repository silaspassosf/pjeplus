"""
tests/test_observabilidade.py - Validação da observabilidade e log estruturado do PJePlus.
"""

import unittest
from Fix.diagnostico_runtime import sanitizar_dados_sensiveis, log_erro_estruturado


class TestObservabilidade(unittest.TestCase):

    def test_sanitizacao_cpf_cnpj_tokens(self):
        texto = "Processo do autor CPF 123.456.789-10 e reclamada CNPJ 12.345.678/0001-90 com token=secret_xyz"
        sanitizado = sanitizar_dados_sensiveis(texto)
        self.assertNotIn("123.456.789-10", sanitizado)
        self.assertNotIn("12.345.678/0001-90", sanitizado)
        self.assertNotIn("secret_xyz", sanitizado)
        self.assertIn("[CPF_OCULTADO]", sanitizado)
        self.assertIn("[CNPJ_OCULTADO]", sanitizado)
        self.assertIn("token=[OCULTADO]", sanitizado)

    def test_log_erro_estruturado_formato_canonico(self):
        msg = log_erro_estruturado(
            codigo="PEC-ELEMENTO-NAO-ENCONTRADO",
            fluxo="PEC",
            modulo="atos.comunicacao_preenchimento",
            funcao="executar_preenchimento_minuta",
            processo="1000123-45.2023.5.02.0001",
            etapa="selecionar_tipo_expediente",
            acao="tipo_expediente",
            seletor="mat-select#tipoExpediente",
            excecao="TimeoutError",
            causa="Elemento não apareceu após 5s para o CPF 111.222.333-44",
            retry=False,
            consequencia="Minuta não criada",
        )

        linhas = msg.strip().split("\n")
        self.assertEqual(linhas[0], "ERRO [PEC-ELEMENTO-NAO-ENCONTRADO]")
        self.assertIn("fluxo=PEC", linhas)
        self.assertIn("modulo=atos.comunicacao_preenchimento", linhas)
        self.assertIn("funcao=executar_preenchimento_minuta", linhas)
        self.assertIn("processo=1000123-45.2023.5.02.0001", linhas)
        self.assertIn("etapa=selecionar_tipo_expediente", linhas)
        self.assertIn("acao=tipo_expediente", linhas)
        self.assertIn("seletor=mat-select#tipoExpediente", linhas)
        self.assertIn("excecao=TimeoutError", linhas)
        self.assertIn("retry=false", linhas)
        self.assertIn("consequencia=Minuta não criada", linhas)
        # Verifica se o CPF na causa foi sanitizado
        self.assertNotIn("111.222.333-44", msg)
        self.assertIn("[CPF_OCULTADO]", msg)


if __name__ == '__main__':
    unittest.main()
