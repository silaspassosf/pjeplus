# P2B Refatorado - Módulo Principal
# Arquitetura modular para processamento BNDT, PEC e pagamentos

__version__ = "2.0.0"
__author__ = "Sistema PJE Plus"

# Compatibilidade: exportar função de nível superior usada por scripts legados
try:
	from .core.p2b_engine import P2BEngine
	from .core.config import DEBUG_MODE

	def processar_p2(driver_existente=None, process_id=None, debug=None):
		"""Compatibilidade com interface antiga:
		processar_p2(driver_existente=driver)

		Retorna True se o processamento foi bem-sucedido, False caso contrário.
		Internamente usa P2BEngine.process_prescription para realizar o trabalho.
		"""
		try:
			engine = P2BEngine(debug=(DEBUG_MODE if debug is None else bool(debug)))
			resultado = engine.process_prescription(driver_existente, process_id)
			if isinstance(resultado, dict):
				return bool(resultado.get('success', False))
			# Caso inesperado, considera sucesso quando truthy
			return bool(resultado)
		except Exception as e:
			print(f"[p2b.__init__][ERRO] Falha ao executar processar_p2: {e}")
			return False
except Exception:
	# Se import falhar, não bloquear a importação do pacote; apenas declare nome vazio
	processar_p2 = None

__all__ = ["P2BEngine", "processar_p2"]