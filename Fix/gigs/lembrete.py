"""
lembrete.py - Funções para criação e gestão de lembretes/post-its no PJe
"""
import logging
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def criar_lembrete_posit(driver: WebDriver, titulo: str, conteudo: str, debug: bool = False) -> bool:
	"""
	Cria lembrete/post-it genérico com título e conteúdo customizáveis.
	Baseado na implementação otimizada do a.py
	"""
	try:
		# Clicar no botão do menu (fa-bars)
		if not aguardar_e_clicar(driver, '.fa-bars', timeout=5, log=debug):
			return False

		# Clicar diretamente no botão de post-it
		if not aguardar_e_clicar(driver, 'pje-icone-post-it button', timeout=5, log=debug):
			return False

		# Aguardar modal abrir (não clicar nele)
		try:
			WebDriverWait(driver, 5).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, '.mat-dialog-content'))
			)
		except Exception:
			return False

		# Pequena pausa para estabilizar
		time.sleep(0.5)

		# Preencher título
		try:
			titulo_elem = WebDriverWait(driver, 5).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, '#tituloPostit'))
			)
			titulo_elem.clear()
			titulo_elem.send_keys(titulo)
			if debug:
				logger.info(f'[LEMBRETE] Título preenchido: {titulo}')
		except Exception as e:
			if debug:
				logger.error(f'[LEMBRETE] Erro ao preencher título: {e}')
			return False

		# Preencher conteúdo
		try:
			conteudo_elem = WebDriverWait(driver, 5).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, '#conteudoPostit'))
			)
			conteudo_elem.clear()
			conteudo_elem.send_keys(conteudo)
			if debug:
				logger.info(f'[LEMBRETE] Conteúdo preenchido: {conteudo[:50]}...')
		except Exception as e:
			if debug:
				logger.error(f'[LEMBRETE] Erro ao preencher conteúdo: {e}')
			return False

		# Aguardar um pouco antes de salvar
		time.sleep(0.3)

		# Salvar - seletor específico baseado no HTML real do modal
		salvo = False

		# Primeiro: tentar botão com color="primary" E aria-label="Salvar" (mais específico)
		try:
			botao_salvar = WebDriverWait(driver, 3).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[color="primary"][aria-label="Salvar"]'))
			)
			botao_salvar.click()
			salvo = True
			if debug:
				logger.info('[LEMBRETE] Lembrete salvo com button[color="primary"][aria-label="Salvar"]')
		except Exception:
			# Segundo: tentar botão com color="primary" que contenha texto "Salvar"
			try:
				botoes_primary = driver.find_elements(By.CSS_SELECTOR, 'button[color="primary"]')
				for botao in botoes_primary:
					if 'salvar' in botao.text.lower().strip():
						botao.click()
						salvo = True
						if debug:
							logger.info(f'[LEMBRETE] Lembrete salvo com button[color="primary"] texto: "{botao.text.strip()}"')
						break
			except Exception as e:
				if debug:
					logger.error(f'[LEMBRETE] Erro ao buscar botão primary: {e}')

		# Terceiro: fallback geral - procurar qualquer botão com texto "Salvar"
		if not salvo:
			try:
				botoes = driver.find_elements(By.CSS_SELECTOR, 'button')
				for botao in botoes:
					texto = botao.text.strip()
					if texto.lower() == 'salvar':
						botao.click()
						salvo = True
						if debug:
							logger.info(f'[LEMBRETE] Lembrete salvo com fallback texto exato: "{texto}"')
						break
			except Exception as e:
				if debug:
					logger.error(f'[LEMBRETE] Erro no fallback geral: {e}')

		if salvo:
			# Aguardar um pouco para o salvamento ser processado
			time.sleep(0.5)
			return True

		if debug:
			logger.error('[LEMBRETE] Falha ao salvar lembrete - nenhum botão de salvar encontrado')
		return False

	except Exception as e:
		if debug:
			logger.error(f'[LEMBRETE][ERRO] {e}')
		return False


# Import necessário para aguardar_e_clicar
try:
	from Fix.core import aguardar_e_clicar
except ImportError:
	# Fallback se não conseguir importar
	def aguardar_e_clicar(*args, **kwargs):
		return False