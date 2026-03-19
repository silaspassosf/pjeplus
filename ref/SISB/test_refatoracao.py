"""
Testes da Refatoração SISB/s.py

Valida a funcionalidade dos módulos refatorados:
- standards.py: Padrões e tipos
- utils.py: Utilitários
- processamento_refatorado.py: Lógica de processamento
- performance.py: Otimizações
- s_orquestrador.py: Orquestrador principal
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

# Adicionar caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports dos módulos refatorados
from SISB.standards import (
    SISBConstants,
    StatusProcessamento,
    TipoFluxo,
    DadosProcesso,
    ResultadoProcessamento,
    SISBLogger,
    sisb_logger
)

from SISB.utils import (
    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    validar_numero_processo,
    formatar_valor_monetario,
    log_sisbajud
)

from SISB.performance import (
    PerformanceOptimizer,
    PollingReducer,
    CacheManager,
    ParallelProcessor
)

from SISB.s_orquestrador import executar_sisbajud_completo

class TestStandards(unittest.TestCase):
    """Testes dos padrões implementados"""

    def test_constants(self):
        """Testa constantes do SISB"""
        self.assertEqual(SISBConstants.TIMEOUT_PADRAO, 30)
        self.assertEqual(SISBConstants.MAX_TENTATIVAS, 3)
        self.assertEqual(SISBConstants.URL_SISBAJUD, "https://sisbajud.bacen.gov.br")

    def test_status_processamento(self):
        """Testa enum de status"""
        self.assertEqual(StatusProcessamento.SUCESSO.value, "sucesso")
        self.assertEqual(StatusProcessamento.ERRO.value, "erro")
        self.assertEqual(StatusProcessamento.PENDENTE.value, "pendente")

    def test_tipo_fluxo(self):
        """Testa enum de tipo de fluxo"""
        self.assertEqual(TipoFluxo.POSITIVO.value, "positivo")
        self.assertEqual(TipoFluxo.NEGATIVO.value, "negativo")

    def test_dados_processo(self):
        """Testa dataclass DadosProcesso"""
        dados = DadosProcesso(
            numero="1234567-89.2024.8.26.0100",
            valor=1000.50,
            tipo="bloqueio"
        )
        self.assertEqual(dados.numero, "1234567-89.2024.8.26.0100")
        self.assertEqual(dados.valor, 1000.50)
        self.assertEqual(dados.tipo, "bloqueio")

    def test_resultado_processamento(self):
        """Testa dataclass ResultadoProcessamento"""
        resultado = ResultadoProcessamento(
            status=StatusProcessamento.SUCESSO,
            tipo_fluxo=TipoFluxo.POSITIVO,
            series_processadas=5,
            ordens_processadas=10
        )
        self.assertEqual(resultado.status, StatusProcessamento.SUCESSO)
        self.assertEqual(resultado.tipo_fluxo, TipoFluxo.POSITIVO)
        self.assertEqual(resultado.series_processadas, 5)
        self.assertEqual(resultado.ordens_processadas, 10)

    def test_logger(self):
        """Testa logger SISB"""
        logger = SISBLogger()
        # Testa que não lança erro
        logger.log("Teste", "INFO", "teste")
        logger.log("Erro teste", "ERROR", "teste")

class TestUtils(unittest.TestCase):
    """Testes dos utilitários refatorados"""

    def test_validar_numero_processo(self):
        """Testa validação de número de processo"""
        # Válidos
        self.assertTrue(validar_numero_processo("1234567-89.2024.8.26.0100"))
        self.assertTrue(validar_numero_processo("0001234-56.2023.8.26.0001"))

        # Inválidos
        self.assertFalse(validar_numero_processo(""))
        self.assertFalse(validar_numero_processo("123"))
        self.assertFalse(validar_numero_processo("abc-def.ghi.jkl.mno"))

    def test_formatar_valor_monetario(self):
        """Testa formatação de valores monetários"""
        self.assertEqual(formatar_valor_monetario(1000.50), "R$ 1.000,50")
        self.assertEqual(formatar_valor_monetario(500), "R$ 500,00")
        self.assertEqual(formatar_valor_monetario(0), "R$ 0,00")

    def test_criar_js_otimizado(self):
        """Testa criação do framework JavaScript otimizado"""
        js_code = criar_js_otimizado()
        self.assertIsInstance(js_code, str)
        self.assertIn("MutationObserver", js_code)
        self.assertIn("safeClick", js_code)
        self.assertIn("waitForElement", js_code)

    @patch('SISB.utils.webdriver')
    def test_safe_click(self, mock_webdriver):
        """Testa função safe_click"""
        mock_element = Mock()
        mock_element.click = Mock()

        # Testa clique bem-sucedido
        result = safe_click(mock_element)
        self.assertTrue(result)
        mock_element.click.assert_called_once()

    @patch('SISB.utils.webdriver')
    def test_aguardar_elemento(self, mock_webdriver):
        """Testa função aguardar_elemento"""
        mock_driver = Mock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element

        # Testa busca bem-sucedida
        result = aguardar_elemento(mock_driver, "id", "teste", timeout=1)
        self.assertEqual(result, mock_element)

class TestPerformance(unittest.TestCase):
    """Testes das otimizações de performance"""

    def test_performance_optimizer(self):
        """Testa otimizador de performance"""
        optimizer = PerformanceOptimizer()

        # Testa cache
        @optimizer.cached(ttl=60)
        def test_func(x):
            return x * 2

        result1 = test_func(5)
        result2 = test_func(5)  # Deve vir do cache
        self.assertEqual(result1, result2)
        self.assertEqual(result1, 10)

    def test_cache_manager(self):
        """Testa gerenciador de cache"""
        cache = CacheManager()

        # Testa set/get
        cache.set("teste", "valor", ttl=60)
        result = cache.get("teste")
        self.assertEqual(result, "valor")

        # Testa expiração
        cache.set("expira", "valor", ttl=0)
        result = cache.get("expira")
        self.assertIsNone(result)

    def test_polling_reducer(self):
        """Testa redutor de polling"""
        reducer = PollingReducer()

        # Testa redução de polling
        intervals = [1, 2, 3, 4, 5]
        optimized = reducer.optimize_intervals(intervals)
        self.assertIsInstance(optimized, list)
        self.assertGreaterEqual(len(optimized), len(intervals))

class TestOrquestrador(unittest.TestCase):
    """Testes do orquestrador principal"""

    @patch('SISB.s_orquestrador.iniciar_sisbajud')
    @patch('SISB.s_orquestrador.minuta_bloqueio')
    def test_executar_sisbajud_completo_sucesso(self, mock_minuta, mock_iniciar):
        """Testa execução completa bem-sucedida"""
        # Mocks
        mock_driver = Mock()
        mock_iniciar.return_value = mock_driver

        mock_minuta.return_value = {
            'status': 'sucesso',
            'tipo_fluxo': 'positivo',
            'series_processadas': 3,
            'ordens_processadas': 6
        }

        # Dados de teste
        dados_processo = {
            'numero': '1234567-89.2024.8.26.0100',
            'sisbajud': {'tipo': 'bloqueio'}
        }

        # Executa
        resultado = executar_sisbajud_completo(dados_processo)

        # Verificações
        self.assertEqual(resultado.status, StatusProcessamento.SUCESSO)
        self.assertEqual(resultado.tipo_fluxo, TipoFluxo.POSITIVO)
        self.assertEqual(resultado.series_processadas, 3)
        self.assertEqual(resultado.ordens_processadas, 6)

    @patch('SISB.s_orquestrador.iniciar_sisbajud')
    def test_executar_sisbajud_completo_erro_inicializacao(self, mock_iniciar):
        """Testa execução com erro na inicialização"""
        mock_iniciar.return_value = None

        dados_processo = {'numero': '1234567-89.2024.8.26.0100'}

        resultado = executar_sisbajud_completo(dados_processo)

        self.assertEqual(resultado.status, StatusProcessamento.ERRO)
        self.assertIn("Falha na inicialização", str(resultado.erros[0]))

    def test_executar_sisbajud_completo_dados_invalidos(self):
        """Testa execução com dados inválidos"""
        resultado = executar_sisbajud_completo(None)

        self.assertEqual(resultado.status, StatusProcessamento.ERRO)
        self.assertIn("Dados do processo não fornecidos", str(resultado.erros[0]))

class TestIntegracao(unittest.TestCase):
    """Testes de integração entre módulos"""

    def test_imports_modulares(self):
        """Testa que todos os módulos podem ser importados"""
        try:
            from SISB.core import (
                SISBConstants, StatusProcessamento, TipoFluxo,
                criar_js_otimizado, safe_click,
                performance_optimizer, executar_sisbajud_completo
            )
            # Se chegou aqui, imports funcionaram
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Falha no import: {e}")

    def test_compatibilidade_legacy(self):
        """Testa compatibilidade com código legacy"""
        # Verifica que funções antigas ainda existem
        from SISB.s_orquestrador import (
            minuta_bloqueio_legacy,
            criar_js_otimizado_legacy
        )
        self.assertTrue(callable(minuta_bloqueio_legacy))
        self.assertTrue(callable(criar_js_otimizado_legacy))

def run_tests():
    """Executa todos os testes"""
    print("=== EXECUTANDO TESTES DA REFATORAÇÃO SISB ===")

    # Criar suite de testes
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Adicionar classes de teste
    suite.addTests(loader.loadTestsFromTestCase(TestStandards))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestOrquestrador))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegracao))

    # Executar testes
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Resultado
    print(f"\n=== RESULTADO DOS TESTES ===")
    print(f"Executados: {result.testsRun}")
    print(f"Sucessos: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Falhas: {len(result.failures)}")
    print(f"Erros: {len(result.errors)}")

    if result.failures:
        print("\nFALHAS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERROS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    return result.wasSuccessful()

if __name__ == "__main__":
    sucesso = run_tests()
    sys.exit(0 if sucesso else 1)