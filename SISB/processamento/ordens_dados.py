import logging
from datetime import datetime
from Fix import espera

logger = logging.getLogger(__name__)

"""
SISBAJUD Ordens - Dados e extracao de ordens
"""


def _carregar_dados_ordem():
    """Helper para carregar dados do processo para processamento de ordens."""
    try:
        from ..utils import carregar_dados_processo

        dados_arquivo = carregar_dados_processo()
        if not dados_arquivo or not isinstance(dados_arquivo, dict):
            return None, None

        numero_bruto = dados_arquivo.get('numero')
        if isinstance(numero_bruto, list) and len(numero_bruto) > 0:
            numero_processo = numero_bruto[0]
        elif isinstance(numero_bruto, str) and numero_bruto.strip():
            numero_processo = numero_bruto.strip()
        else:
            return None, None
        return dados_arquivo, numero_processo

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao carregar dados: {e}')
        return None, None


def _extrair_ordens_da_serie(driver, log=True):
    """Extrai ordens da pagina de detalhes da serie."""
    ordens = []
    try:
        # Aguarda a transição do SPA (evita pegar a tabela da série anterior que está sumindo do DOM)
        espera.ate_sumir(driver, 'table.mat-table tbody', teto=2)
        tabela = espera.elemento(driver, "table.mat-table tbody", teto=10)
        if not tabela:
            return []

        linhas = espera.elementos(tabela, "tr.mat-row, tr[mat-row]", teto=0.5)

        for linha in linhas:
            try:
                cols = espera.elementos(linha, "td", teto=0.2)
                if len(cols) < 6:
                    continue

                sequencial = int(cols[0].text.strip())
                data_txt = cols[2].text.strip()
                protocolo = cols[5].text.strip()

                # Extrair status da ordem (mas NAO pular ainda - identificar bloqueios primeiro)
                situacao = ""
                try:
                    all_text = ' '.join([c.text for c in cols]).strip()
                    if 'Respondida com minuta' in all_text:
                        situacao = "Respondida com minuta"
                    elif 'Respondida' in all_text:
                        situacao = "Respondida"
                except Exception:
                    situacao = ""

                valor_txt = cols[4].text.strip()

                data_ordem = None
                if "/" in data_txt:
                    partes = data_txt.split(",")
                    data_parte = partes[0].strip() if len(partes) > 0 else data_txt.strip()
                    data_split = data_parte.split("/")
                    if len(data_split) == 3:
                        try:
                            dia, mes, ano = map(int, data_split)
                            data_ordem = datetime(ano, mes, dia)
                        except Exception:
                            continue

                if not data_ordem:
                    continue

                try:
                    valor = float(valor_txt.replace("R$", "").replace("\u00a0", "").replace(".", "").replace(",", ".").strip())
                except Exception:
                    continue

                ordens.append({
                    "sequencial": sequencial,
                    "data": data_ordem,
                    "valor_bloquear": valor,
                    "protocolo": protocolo,
                    "situacao": situacao,
                    "linha_el": linha
                })

            except Exception as e:
                if log:
                    logger.error(f"[SISBAJUD] Ignorando linha: erro inesperado - {e}")
                continue

        ordens.sort(key=lambda x: x["data"])
        return ordens

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD] Erro ao extrair ordens: {e}")
        return []


def _identificar_ordens_com_bloqueio(ordens, valor_total_bloqueado_serie=None, log=True):
    """Identifica ordens que geraram bloqueio usando logica de diferenca de valores."""
    bloqueios = []

    if not ordens:
        return bloqueios

    for i in range(len(ordens) - 1):
        valor_atual = ordens[i]["valor_bloquear"]
        valor_posterior = ordens[i + 1]["valor_bloquear"]

        if valor_atual > valor_posterior:
            ordem_com_bloqueio = ordens[i].copy()
            valor_bloqueio = valor_atual - valor_posterior
            ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_bloqueio

            ordem_com_bloqueio['_relatorio'] = {
                'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                'valor_esperado': valor_bloqueio,
                'status': 'pendente',
                'discriminacao': None
            }

            bloqueios.append(ordem_com_bloqueio)

    # 2. Verificar ultima ordem usando diferenca de valores
    if len(ordens) > 0:
        ultima_ordem = ordens[-1]
        valor_original_a_bloquear = ordens[0]["valor_bloquear"] if ordens else 0
        valor_efetivamente_bloqueado = valor_total_bloqueado_serie or 0
        valor_ultima_ordem = ultima_ordem["valor_bloquear"]
        diferenca_esperada = valor_original_a_bloquear - valor_efetivamente_bloqueado
        diferenca_absoluta = abs(diferenca_esperada - valor_ultima_ordem)

        if diferenca_absoluta > 0.01:
            if ultima_ordem not in bloqueios:
                ordem_com_bloqueio = ultima_ordem.copy()
                ordem_com_bloqueio['valor_bloqueio_esperado'] = diferenca_esperada

                ordem_com_bloqueio['_relatorio'] = {
                    'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                    'valor_esperado': diferenca_esperada,
                    'status': 'pendente',
                    'discriminacao': None
                }

                bloqueios.append(ordem_com_bloqueio)

    if valor_total_bloqueado_serie and valor_total_bloqueado_serie > 0 and len(bloqueios) == 0 and len(ordens) > 0:
        ultima_ordem = ordens[-1]
        ordem_com_bloqueio = ultima_ordem.copy()
        ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_total_bloqueado_serie

        ordem_com_bloqueio['_relatorio'] = {
            'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
            'valor_esperado': valor_total_bloqueado_serie,
            'status': 'pendente',
            'discriminacao': None
        }

        bloqueios.append(ordem_com_bloqueio)

    _ = log
    return bloqueios
