"""Prazo P2B - Regras de Execucao (Core + Criteria Matcher)"""

import datetime
import json
import logging
import os
import re
import sys
import time
import traceback
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Callable, Optional, Tuple

from Fix import espera

from Fix.utils import remover_acentos, normalizar_texto

logger = logging.getLogger(__name__)


class CriteriaMatcher:
    """Matcher de critérios com early termination para buscas em loop."""

    def __init__(self, driver, config, wait_pool):
        """Inicializa matcher."""
        self.driver = driver
        self.config = config
        self.wait_pool = wait_pool

    def buscar_com_criterio(self, criterio_fn: Callable[[Dict], bool],
                           max_paginas: int = 50) -> Tuple[bool, Optional[Dict]]:
        """Busca com early termination quando critério atende."""
        pagina_atual = 1

        while pagina_atual <= max_paginas:
            try:
                logger.debug(f"Verificando critério na página {pagina_atual}")

                dados_pagina = self._extrair_dados_pagina()

                if criterio_fn(dados_pagina):
                    logger.info(f"Criterio encontrado na pagina {pagina_atual}")
                    return True, dados_pagina

                if not self._ir_proxima_pagina():
                    logger.info("Última página atingida, critério não encontrado")
                    return False, None

                pagina_atual += 1

            except Exception as e:
                logger.error(f"Erro na página {pagina_atual}: {e}")
                return False, None

        logger.warning(f"Max páginas ({max_paginas}) atingido, critério não encontrado")
        return False, None

    def buscar_prazo_ativo(self, max_paginas: int = 20) -> Tuple[bool, Optional[Dict]]:
        """Busca específica por prazo ativo (não vencido)."""
        def criterio_prazo_ativo(dados: Dict) -> bool:
            """Critério: prazo não vencido e ativo."""
            prazos = dados.get('prazos', [])

            for prazo in prazos:
                status = prazo.get('status', '').lower()
                if 'ativo' in status or 'vigente' in status:
                    data_fim = prazo.get('data_fim')
                    if data_fim and not self._prazo_vencido(data_fim):
                        return True
            return False

        return self.buscar_com_criterio(criterio_prazo_ativo, max_paginas)

    def _extrair_dados_pagina(self) -> Dict:
        """Extrai dados da página atual."""
        try:
            self.wait_pool.esperar_elemento("tabela_dados", timeout=5)

            prazos = self._extrair_prazos_tabela()

            metadados = {
                'pagina_atual': self._obter_numero_pagina(),
                'total_paginas': self._obter_total_paginas(),
                'timestamp_extracao': self._timestamp_atual()
            }

            from core.resultado_execucao import ResultadoExecucao
            return ResultadoExecucao(
                sucesso=True,
                status='OK',
                detalhes={
                    'prazos': prazos,
                    'metadados': metadados
                }
            )

        except Exception as e:
            logger.warning(f"Erro ao extrair dados da página: {e}")
            return ResultadoExecucao(
                sucesso=False,
                status='FALHA',
                erro=str(e),
                detalhes={'prazos': [], 'metadados': {}}
            )

    def _extrair_prazos_tabela(self) -> list:
        """Extrai lista de prazos da tabela atual."""
        prazos = []

        try:
            tabela = espera.elemento(self.driver, "#data-table", teto=2)
            if not tabela:
                return prazos

            linhas = espera.elementos(tabela, "tr", teto=1)[1:]

            for linha in linhas:
                try:
                    colunas = espera.elementos(linha, "td", teto=0.5)

                    if len(colunas) >= 4:
                        prazo = {
                            'tipo': colunas[0].text.strip(),
                            'data_inicio': colunas[1].text.strip(),
                            'data_fim': colunas[2].text.strip(),
                            'status': colunas[3].text.strip(),
                            'linha_html': linha.get_attribute('outerHTML')
                        }
                        prazos.append(prazo)

                except Exception as e:
                    logger.debug(f"Erro ao extrair linha de prazo: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Erro ao extrair prazos da tabela: {e}")

        return prazos

    def _ir_proxima_pagina(self) -> bool:
        """Navega para a próxima página."""
        try:
            botao_proximo = self.wait_pool.esperar_clicavel("botao_proximo", timeout=3)

            if botao_proximo.is_enabled():
                botao_proximo.click()
                logger.debug("Navegou para próxima página")

                self.wait_pool.esperar_invisibilidade("spinner", timeout=5)
                return True
            else:
                logger.debug("Botão próximo desabilitado - última página")
                return False

        except Exception as e:
            logger.debug(f"Não foi possível navegar para próxima página: {e}")
            return False

    def _obter_numero_pagina(self) -> int:
        """Obtém número da página atual."""
        try:
            elementos_pagina = espera.elementos(self.driver, "//*[contains(text(), 'Página')]", teto=1)
            for elem in elementos_pagina:
                texto = elem.text
                if 'Página' in texto:
                    match = re.search(r'Página\s+(\d+)', texto)
                    if match:
                        return int(match.group(1))
            return 1
        except Exception:
            return 1

    def _obter_total_paginas(self) -> int:
        """Obtém total de páginas."""
        try:
            elementos_pagina = espera.elementos(self.driver, "//*[contains(text(), 'Página')]", teto=1)
            for elem in elementos_pagina:
                texto = elem.text
                if 'de' in texto:
                    match = re.search(r'de\s+(\d+)', texto)
                    if match:
                        return int(match.group(1))
            return 1
        except Exception:
            return 1

    def _prazo_vencido(self, data_fim: str) -> bool:
        """Verifica se prazo está vencido."""
        try:
            from datetime import datetime
            data_fim_dt = datetime.strptime(data_fim, '%d/%m/%Y')
            return data_fim_dt < datetime.now()
        except Exception:
            return False

    def _timestamp_atual(self) -> str:
        """Retorna timestamp atual formatado."""
        from datetime import datetime
        return datetime.now().isoformat()


try:
    with open("p2b_log.txt", "w", encoding="utf-8") as f:
        f.write(f"# Ultima execucao P2B: {datetime.datetime.now()}\n")
        f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
        f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")
except Exception:
    pass

# Evitar modificações em arquivos não explicitamente mencionados.
# nao é neceasário varrer o codigo todo para cada edição pedida


SCRIPT_ANALISE_TIMELINE = """
function analisarTimeline() {
    const itens = document.querySelectorAll('li.tl-item-container');
    const resultados = [];

    for (let item of itens) {
        try {
            const link = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!link) continue;

            const texto = link.textContent.toLowerCase();
            const dataElement = item.querySelector('.tl-data');
            const data = dataElement ? dataElement.textContent.trim() : '';

            // Verificar se é documento relevante
            const relevante = /despacho|decisão|sentença|conclusão/i.test(texto);

            if (relevante) {
                resultados.push({
                    texto: texto,
                    data: data,
                    elemento: item
                });
            }
        } catch (e) {
            continue;
        }
    }

    return resultados;
}

return analisarTimeline();
"""

REGEX_PATTERNS = {
    'prescricao': re.compile(r'A pronúncia da', re.IGNORECASE),
    'bloqueio': re.compile(r'sob pena de bloqueio', re.IGNORECASE),
    'sobrestamento': re.compile(r'05 dias para a apresentação|suspensão da execução, com fluência|05 dias para oferta|concede-se 05 dias para oferta|cinco dias para apresentação|cinco dias para oferta|cinco dias para apresentacao|concedo o prazo de oito dias|oito dias para apresentacao|visibilidade aos advogados|início da fluência|oito dias para apresentação|oito dias para apresentacao|Reitere-se a intimação para que o\(a\) reclamante apresente cálculos|remessa ao sobrestamento, com fluência|sob pena de sobrestamento e fluência do prazo prescricional', re.IGNORECASE),
    'homologacao': re.compile(r'é revel, não|concorda com homologação|concorda com homologacao|tomarem ciência dos esclarecimentos apresentados|no prazo de oito dias, impugnar|concordância quanto à imediata homologação da conta|conclusos para homologação de cálculos|ciência do laudo técnico apresentado|homologação imediata|aceita a imediata homologação|aceita a imediata homologacao|informar se aceita a imediata homologação|apresentar impugnação, querendo', re.IGNORECASE),
    'embargos': re.compile(r'exequente, ora embargado', re.IGNORECASE),
    'pec': re.compile(r'hasta|saldo devedor|admito o parcelamento', re.IGNORECASE),
    'descumprimento': re.compile(r'Ante a notícia de descumprimento', re.IGNORECASE),
    'impugnacao': re.compile(r'impugnações apresentadas|impugnacoes apresentadas|homologo estes|fixando o crédito do autor em|referente ao principal|sob pena de sequestro|comprovar a quitação|comprovar o pagamento|a reclamada para pagamento da parcela pendente|intime-se a reclamada para pagamento das|líquida a sentença, intime-se', re.IGNORECASE),
    'arquivamento': re.compile(r'arquivem-se os autos|remetam-se os autos ao aquivo|A pronúncia da prescrição intercorrente se trata|Se revê o novo sobrestamento|cumprido o acordo homologado|julgo extinta a presente execução, nos termos do art. 924', re.IGNORECASE),
    'bloqueio_convertido': re.compile(r'bloqueio realizado, ora convertido', re.IGNORECASE),
    'parcelamento': re.compile(r'sobre o preenchimento dos pressupostos legais para concessão do parcelamento', re.IGNORECASE),
    'recolhimento': re.compile(r'comprovar recolhimento|comprovar recolhimentos', re.IGNORECASE),
    'baixa': re.compile(r'determinar cancelamento/baixa|deixo\s+de\s+receber\s+o\s+Agravo|quanto à petição|art. 112 do CPC|comunique-se por Edital|Aguarde-se o cumprimento do mandado expedido', re.IGNORECASE),
    'penhora': re.compile(r'Defiro a penhora no rosto dos autos', re.IGNORECASE),
    'calculos': re.compile(r'RECLAMANTE para apresentar cálculos de liquidação', re.IGNORECASE),
    'tentativas': re.compile(r'deverá realizar tentativas', re.IGNORECASE),
    'instauracao': re.compile(r'defiro a instauração', re.IGNORECASE),
    'iniciar_exec_outros': re.compile(r'pagamento da parcela pendente|sob pena de sequestro', re.IGNORECASE),
    'nao_amparada': re.compile(r'não está amparada', re.IGNORECASE),
    'instaurado_face': re.compile(r'instaurado em face', re.IGNORECASE)
}


def gerar_regex_geral(termo: str) -> re.Pattern:
    """Gera regex tolerante para busca de termos em texto."""
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()

    partes = [re.escape(p) for p in palavras]
    regex = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\.,;:!\-–—()$]*'

    return re.compile(rf"{regex}", re.IGNORECASE)


def parse_gigs_param(parametro: str) -> tuple:
    """Parse parâmetro GIGS no formato 'dias/responsavel/observacao'."""
    partes = parametro.split('/')
    if len(partes) == 3:
        return partes[0], partes[1], partes[2]
    else:
        return "1", parametro, parametro


def carregar_progresso_p2b() -> dict:
    """Carrega progresso salvo do P2B."""
    try:
        from Fix.monitoramento_progresso_unificado import carregar_progresso_p2b as _carregar
        progresso = _carregar()

        if 'p2b' in progresso and isinstance(progresso['p2b'], dict):
            old_p2b = progresso.pop('p2b')
            processos_executados = progresso.get('processos_executados', [])
            for proc_id, details in old_p2b.items():
                if details.get('executado') and proc_id not in processos_executados:
                    processos_executados.append(proc_id)
            progresso['processos_executados'] = processos_executados
            salvar_progresso_p2b(progresso)

        return progresso
    except Exception:
        return {}


def salvar_progresso_p2b(progresso: dict) -> None:
    """Salva progresso do P2B."""
    try:
        from Fix.monitoramento_progresso_unificado import salvar_progresso_p2b as _salvar
        _salvar(progresso)
    except Exception as e:
        logger.error('Erro ao salvar progresso P2B (delegate): %s: %s', type(e).__name__, e)


def marcar_processo_executado_p2b(processo_id: str, progresso: dict) -> None:
    """Marca processo como executado no progresso P2B."""
    from Fix.monitoramento_progresso_unificado import marcar_processo_executado_unificado
    marcar_processo_executado_unificado('p2b', processo_id, progresso, sucesso=True)


def processo_ja_executado_p2b(processo_id: str, progresso: dict) -> bool:
    """Verifica se processo já foi executado no P2B."""
    return processo_id in progresso.get('processos_executados', [])


def calc1(driver: Any) -> Optional[Any]:
    """Extrai dados do processo e escolhe o ato correto para réu."""
    try:
        from Fix.extracao import extrair_dados_processo
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception:
        pass

    caminho = os.path.join(os.getcwd(), 'dadosatuais.json')
    if not os.path.exists(caminho):
        return None

    try:
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
    except Exception:
        return None

    reus = dados.get('reu', []) or []
    if not reus:
        return None

    try:
        from atos import ato_crda, ato_revel
    except Exception:
        return None

    for reu in reus:
        advogado = reu.get('advogado')
        if isinstance(advogado, dict) and any(str(valor).strip() for valor in advogado.values()):
            try:
                return ato_crda(driver)
            except Exception:
                return None

    try:
        return ato_revel(driver)
    except Exception:
        return None


def checar_prox(driver: Any, itens: List[Any], doc_idx: int, regras: List[Any], texto_normalizado: str) -> Tuple[Optional[Any], Optional[Any], Optional[int]]:
    """Verifica se há próximo documento relevante na timeline."""
    if not driver or not itens or doc_idx < 0 or doc_idx >= len(itens):
        return None, None, None

    next_idx = doc_idx + 1
    if next_idx >= len(itens):
        return None, None, None

    for idx in range(next_idx, len(itens)):
        try:
            item = itens[idx]

            # Buscar link do documento (seletor específico para evitar popups)
            link = espera.elemento(item, 'a.tl-documento:not([target="_blank"])', teto=0.5)
            if not link or not getattr(link, 'is_displayed', lambda: True)():
                continue

            raw_text = getattr(link, 'text', '') or ''
            doc_text = unicodedata.normalize('NFD', raw_text).encode('ascii', 'ignore').decode('ascii').lower()

            if not re.search(r'despacho|decisao|decisão|sentenca|sentença|conclusao|conclusão|embargos de declaracao', doc_text):
                continue

            if re.search(r'art\.?\s*112\s+do\s+cpc', doc_text, re.IGNORECASE):
                continue

            mag_icons = espera.elementos(item, 'div.tl-icon[aria-label*="Magistrado"]', teto=0.5)
            mag_ok = any('otavio' in (getattr(mag, 'get_attribute', lambda _: '')('aria-label') or '').lower() or
                        'mariana' in (getattr(mag, 'get_attribute', lambda _: '')('aria-label') or '').lower()
                        for mag in mag_icons)

            if mag_ok:
                return item, link, idx

        except Exception:
            continue

    return None, None, None


def ato_pesqliq_callback(driver):
    raise RuntimeError('ato_pesqliq_callback was removed; call atos.ato_pesqliq directly')


@dataclass
class RegraProcessamento:
    """Representa uma regra de processamento de documento."""
    keywords: list
    tipo_acao: Optional[str] = None
    parametros: Optional[str] = None
    acao_secundaria: Optional[callable] = None

    def aplicar(self, driver, texto_normalizado: str) -> bool:
        """Aplica a regra se encontrar match no texto."""
        for regex in self.keywords:
            if regex.search(texto_normalizado):
                return True
        return False


if __name__ == "__main__":

    teste = "TÊSTE ÁCÊNTÖS"
    resultado = normalizar_texto(teste)
    logger.info('normalizar_texto OK: "%s" -> "%s"', teste, resultado)

    pattern = gerar_regex_geral("teste regex")
    teste_texto = "Este é um teste de regex funcionando"
    match = pattern.search(teste_texto)
    if match:
        logger.info('gerar_regex_geral OK: encontrou "%s"', match.group())
    else:
        logger.info('gerar_regex_geral: sem match')
