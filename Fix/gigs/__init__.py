import logging
from selenium.webdriver.common.by import By
import time

logger = logging.getLogger(__name__)

"""
@module: Fix.gigs
@responsibility: Sistema GIGS - Criação e gestão de atividades PJe
@depends_on: Fix.selenium_base
@used_by: Prazo, Mandado
@entry_points: criar_gigs, criar_comentario, criar_lembrete_posit, gigs_minuta
@tags: #gigs #atividades #pje #minuta
"""

import time
from typing import Optional, Dict, Any, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from Fix.log import logger
from Fix.selenium_base.wait_operations import aguardar_e_clicar
from Fix.selenium_base.element_interaction import preencher_campo

__all__ = [
	'criar_gigs',
	'criar_comentario',
	'criar_lembrete_posit',
]


def _gigs_responsavel_valido(responsavel: Optional[str]) -> bool:
	"""
	Verifica se responsável é válido (não vazio, não '-').
	"""
	return responsavel is not None and responsavel.strip() and responsavel.strip() != '-'


def _parse_gigs_string(string: str) -> Dict[str, Optional[Union[int, str]]]:
	"""
	Parseia string de teste GIGS automaticamente.
	"""
	if '/' not in string:
		return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}

	if '//' in string:
		partes = string.split('//', 1)
		if len(partes) == 2:
			prazo_str, obs = partes
			try:
				dias_uteis = int(prazo_str.strip())
			except ValueError:
				dias_uteis = None
			return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}

	partes = string.split('/')
	if len(partes) == 2:
		prazo_str, obs = partes
		try:
			dias_uteis = int(prazo_str.strip())
		except ValueError:
			dias_uteis = None
		return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
	elif len(partes) == 3:
		prazo_str, resp, obs = partes
		try:
			dias_uteis = int(prazo_str.strip())
		except ValueError:
			dias_uteis = None
		return {'dias_uteis': dias_uteis, 'responsavel': resp.strip(), 'observacao': obs.strip()}

	return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}


def _preencher_texto_colado(driver: WebDriver, seletor: str, texto: str, timeout: int) -> None:
	campo = WebDriverWait(driver, timeout).until(
		EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
	)
	driver.execute_script(
		"arguments[0].value = arguments[1];"
		"arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
		"arguments[0].dispatchEvent(new Event('change', {bubbles: true}));"
		"arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));",
		campo,
		texto,
	)


def escolher_lembrete_restrito(driver: WebDriver, debug: bool = False) -> bool:
	"""
	Abre o seletor de destinatário para lembretes privados.
	Similar à função escolherLembreteRestrito() do JavaScript em a.py
	"""
	try:
		# Abrir seletor de destinatário (igual ao JavaScript)
		ancora = aguardar_e_clicar(driver, 'pje-dialogo-post-it mat-select[id="destinatarioPostit"]', timeout=5, log=debug)
		if not ancora:
			if debug:
				logger.warning('[LEMBRETE][RESTRITO] Seletor de destinatário não encontrado')
			return False

		# Aguardar transição (igual ao JavaScript)
		time.sleep(1)

		if debug:
			logger.info('[LEMBRETE][RESTRITO] Seletor aberto - aguardando seleção manual')
		return True

	except Exception as e:
		if debug:
			logger.error(f'[LEMBRETE][RESTRITO][ERRO] {e}')
		return False


def escolher_opcao_teste(driver: WebDriver, seletor: str, valor: str, debug: bool = False) -> bool:
	"""
	Implementa escolherOpcaoTeste do JavaScript a.py
	Clica no seletor para abrir dropdown e seleciona a opção por texto
	Sempre faz a seleção como no JavaScript (não verifica se já está selecionado)
	"""
	try:
		if debug:
			logger.info(f'[OPCAO][TESTE] Selecionando "{valor}" em "{seletor}"')

		# Verificar se o valor já está selecionado
		try:
			mat_select = WebDriverWait(driver, 2).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
			)
			current_value = mat_select.get_attribute('aria-label') or mat_select.text.strip()
			if current_value and valor.upper() in current_value.upper():
				if debug:
					logger.info(f'[OPCAO][TESTE] "{valor}" já está selecionado')
				return True
		except:
			pass  # Se não conseguir verificar, continua normalmente

		# Sempre clicar no seletor para abrir dropdown (como no JavaScript)
		elem = driver.find_element(By.CSS_SELECTOR, seletor)
		if elem:
			# Clicar diretamente no elemento (igual ao JavaScript: clicarBotao(el))
			elem.click()
		else:
			if debug:
				logger.warning(f'[OPCAO][TESTE] Seletor "{seletor}" não encontrado')
			return False

		time.sleep(0.5)  # Pequena pausa para dropdown abrir

		# Clicar na opção (igual ao JavaScript: mat-option[role="option"] ou option)
		# Procurar por mat-option que contenha o texto (considerando span.mat-option-text)
		try:
			opcao_elem = WebDriverWait(driver, 3).until(
				EC.element_to_be_clickable((By.XPATH, f"//mat-option[@role='option']//span[@class='mat-option-text' and normalize-space(text())='{valor}']"))
			)
			opcao_elem.click()
			opcao_clicked = True
		except:
			opcao_clicked = False

		if not opcao_clicked:
			# Tentar com mat-option direto (fallback)
			try:
				opcao_elem = WebDriverWait(driver, 2).until(
					EC.element_to_be_clickable((By.XPATH, f"//mat-option[@role='option' and contains(normalize-space(.), '{valor}')]"))
				)
				opcao_elem.click()
				opcao_clicked = True
			except:
				opcao_clicked = False

		if not opcao_clicked:
			if debug:
				logger.warning(f'[OPCAO][TESTE] Opção "{valor}" não encontrada')
			return False

		if debug:
			logger.info(f'[OPCAO][TESTE] Selecionado "{valor}" com sucesso')
		return True

	except Exception as e:
		if debug:
			logger.error(f'[OPCAO][TESTE][ERRO] {e}')
		return False


def criar_lembrete_posit(driver: WebDriver, titulo: str, conteudo: str, prazo: str = 'LOCAL', salvar: bool = True, debug: bool = False) -> bool:
	"""
	Cria lembrete/post-it genérico com título, conteúdo e visibilidade customizáveis.
	Similar à função lancarLembrete() do JavaScript em a.py
	"""
	try:
		if debug:
			logger.info(f'[LEMBRETE][POSIT] Criando: "{titulo}" / "{conteudo}" / prazo: {prazo}')

		# 1. ABRIR MENU (igual ao JavaScript: button[id="botao-menu"])
		if debug:
			logger.info('[LEMBRETE][POSIT] Clicando no menu...')
		menu_clicked = aguardar_e_clicar(driver, 'button[id="botao-menu"]', timeout=3, log=debug)
		if not menu_clicked:
			if debug:
				logger.warning('[LEMBRETE][POSIT] Menu não encontrado')
			return False
		time.sleep(0.5)

		# 2. CLICAR NO ÍCONE DE LEMBRETE (igual ao JavaScript: pje-icone-post-it button)
		if debug:
			logger.info('[LEMBRETE][POSIT] Clicando no ícone do lembrete...')
		lembrete_clicked = aguardar_e_clicar(driver, 'pje-icone-post-it button', timeout=3, log=debug)
		if not lembrete_clicked:
			if debug:
				logger.warning('[LEMBRETE][POSIT] Ícone de lembrete não encontrado')
			return False
		time.sleep(0.5)

		# 3. PREENCHER TÍTULO
		if debug:
			logger.info(f'[LEMBRETE][POSIT] Preenchendo título: {titulo}')
		preencher_campo(driver, 'input[id="tituloPostit"]', titulo)

		# 4. ESCOLHER VISIBILIDADE (igual ao JavaScript: mat-select[id="visibilidadePostit"])
		if debug:
			logger.info(f'[LEMBRETE][POSIT] Selecionando visibilidade: {prazo}')
		escolher_opcao_teste(driver, 'mat-select[id="visibilidadePostit"]', prazo, debug=debug)

		# 5. SE PRIVADO, escolher destinatário restrito (igual ao JavaScript)
		if prazo == 'PRIVADO':
			if debug:
				logger.info('[LEMBRETE][POSIT] Configurando lembrete privado...')
			time.sleep(1)  # esperarTransicao
			escolher_lembrete_restrito(driver, debug=debug)

		# 6. PREENCHER CONTEÚDO
		if debug:
			logger.info(f'[LEMBRETE][POSIT] Preenchendo conteúdo: {conteudo}')
		preencher_campo(driver, 'textarea[id="conteudoPostit"]', conteudo)

		# 7. SALVAR (condicional como no JavaScript)
		if salvar:
			if debug:
				logger.info('[LEMBRETE][POSIT] Salvando lembrete...')
			# Usar XPath mais específico para o botão salvar do lembrete
			from selenium.webdriver.common.by import By
			try:
				# Tentar primeiro com aria-label específico
				salvar_elem = WebDriverWait(driver, 3).until(
					EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar']"))
				)
				salvar_elem.click()
				salvar_clicked = True
			except:
				try:
					# Fallback para texto "Salvar"
					salvar_elem = WebDriverWait(driver, 2).until(
						EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Salvar')]"))
					)
					salvar_elem.click()
					salvar_clicked = True
				except:
					salvar_clicked = False

			if salvar_clicked:
				time.sleep(0.5)  # esperarSalvamento
			else:
				if debug:
					logger.warning('[LEMBRETE][POSIT] Botão salvar não encontrado')

		if debug:
			logger.info(f'[LEMBRETE][POSIT] Criado com sucesso: "{titulo}"')
		return True

	except Exception as e:
		if debug:
			logger.error(f'[LEMBRETE][POSIT][ERRO] {e}')
		return False


def criar_gigs(driver: WebDriver, dias_uteis: Optional[Union[int, str]] = None, responsavel: Optional[str] = None, observacao: Optional[str] = None, timeout: int = 10, log: bool = True) -> bool:
	"""
	Cria atividade GIGS na aba /detalhe.
	"""
	if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
		parsed = _parse_gigs_string(dias_uteis)
		dias_uteis = parsed['dias_uteis']
		responsavel = parsed['responsavel']
		observacao = parsed['observacao']

	if observacao is None and responsavel is not None:
		observacao = responsavel
		responsavel = None

	try:
		if log:
			info = f"{dias_uteis or '-'}" + f"/{responsavel or '-'}" + f"/{observacao or '-'}"

		nova_atividade_xpath = (
			"//button[.//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')] "
			"or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')]"
		)
		if not aguardar_e_clicar(driver, nova_atividade_xpath, timeout=timeout, by=By.XPATH, log=log):
			raise RuntimeError('Botão Nova atividade não foi encontrado ou clicável')

		WebDriverWait(driver, timeout).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
		)
		if dias_uteis:
			if not preencher_campo(driver, 'input[formcontrolname="dias"]', str(dias_uteis), log=log):
				if log:
					logger.warning('[GIGS][AVISO] Falha ao preencher prazo de GIGS')
		if responsavel and _gigs_responsavel_valido(responsavel):
			campo_resp = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
			if not preencher_campo(driver, 'input[formcontrolname="responsavel"]', responsavel, log=log):
				if log:
					logger.warning('[GIGS][AVISO] Falha ao preencher responsável do GIGS')
			campo_resp.send_keys(Keys.ARROW_DOWN)
			campo_resp.send_keys(Keys.ENTER)
		if observacao:
			preencher_campo(driver, 'textarea[formcontrolname="observacao"]', observacao, log=log)
		if not aguardar_e_clicar(driver, "//button[contains(., 'Salvar')]", timeout=timeout, by=By.XPATH, log=log):
			raise RuntimeError('Botão Salvar não foi encontrado ou clicável no GIGS')

		try:
			WebDriverWait(driver, timeout).until(
				EC.presence_of_element_located((By.XPATH, "//snack-bar-container//span[contains(normalize-space(.), 'Atividade salva com sucesso')]"))
			)
		except TimeoutException:
			pass

		try:
			WebDriverWait(driver, timeout).until(
				EC.invisibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"], textarea[name="observacao"]'))
			)
		except TimeoutException:
			if log:
				logger.warning('[GIGS][AVISO] Modal de GIGS não fechou após salvar')

		return True

	except Exception as e:
		if log:
			logger.error(f'[GIGS][ERRO] {e}')
		return False


def criar_comentario(driver: WebDriver, observacao: str, visibilidade: str = 'LOCAL', timeout: int = 10, log: bool = True) -> bool:
	"""
	Cria comentário GIGS na aba /detalhe.
	"""
	try:
		if not aguardar_e_clicar(driver, "//button[contains(., 'Novo Comentário') or contains(., 'Novo comentário')]", timeout=timeout, by=By.XPATH, log=log):
			raise RuntimeError('Botão Novo Comentário não foi encontrado ou clicável')

		WebDriverWait(driver, timeout).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]'))
		)
		preencher_campo(
			driver,
			'textarea[formcontrolname="descricao"], textarea[name="descricao"]',
			observacao,
			log=log,
		)
		visibilidade_upper = visibilidade.upper()
		try:
			radio_buttons = driver.find_elements(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-radio-button, mat-radio-button')
			if len(radio_buttons) >= 3:
				index_map = {'LOCAL': 0, 'RESTRITA': 1, 'GLOBAL': 2}
				idx = index_map.get(visibilidade_upper, 0)
				radio_input = radio_buttons[idx].find_element(By.CSS_SELECTOR, 'input')
				aguardar_e_clicar(driver, radio_input, timeout=timeout, log=log)
		except Exception:
			pass
		if not aguardar_e_clicar(driver, "//button[contains(., 'Salvar')]", timeout=timeout, by=By.XPATH, log=log):
			raise RuntimeError('Botão Salvar não foi encontrado ou clicável no comentário')

		# Aguardar snackbar "Comentário salvo com sucesso!" — sinal imediato de conclusão
		try:
			WebDriverWait(driver, timeout).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, 'simple-snack-bar, snack-bar-container'))
			)
		except Exception:
			pass

		try:
			WebDriverWait(driver, timeout).until(
				EC.invisibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]'))
			)
		except Exception:
			if log:
				logger.warning('[COMENTARIO][AVISO] Modal de comentário não fechou após salvar')
			return False

		return True

	except Exception as e:
		if log:
			logger.error(f'[COMENTARIO][ERRO] {e}')
		return False
