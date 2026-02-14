import logging
from datetime import datetime

from ..utils import criar_js_otimizado

logger = logging.getLogger(__name__)

"""
SISB Series - Filtro de series
"""


def _filtrar_series(driver, data_limite):
    """
    Helper para filtrar series validas da tabela.
    """
    try:
        script_extrair = f"""
        {criar_js_otimizado()}

        async function extrairSeries() {{
            try {{
                let tabela = await esperarElemento('table.mat-table', 10000);
                if (!tabela) return {{sucesso: false, erro: 'Tabela nao encontrada'}};

                let linhas = tabela.querySelectorAll('tbody tr.mat-row');
                let series = [];

                for (let i = 0; i < linhas.length; i++) {{
                    let linha = linhas[i];
                    let colunas = linha.querySelectorAll('td');

                    let serie = {{
                        linha_index: i
                    }};

                    if (colunas.length >= 8) {{
                        serie.id_serie = colunas[0].textContent.trim();
                        serie.protocolo = colunas[1].textContent.trim();
                        serie.acao = colunas[2].textContent.trim();
                        serie.valor_bloquear_text = colunas[3].textContent.trim();
                        serie.valor_bloqueado_text = colunas[4].textContent.trim();
                        serie.data_conclusao = colunas[5].textContent.trim();
                        serie.situacao = colunas[6].textContent.trim();
                    }}

                    series.push(serie);
                }}

                return {{sucesso: true, series: series}};
            }} catch(e) {{
                return {{sucesso: false, erro: e.message}};
            }}
        }}

        return extrairSeries().then(arguments[arguments.length - 1]);
        """

        resultado = driver.execute_async_script(script_extrair)
        if not resultado or not resultado.get('sucesso'):
            logger.error(f'[SISBAJUD]  Erro na extracao: {resultado.get("erro")}')
            return []

        series_bruto = resultado.get('series', [])

        series_validas = []
        meses_map = {
            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
        }

        def extrair_valor_monetario(texto):
            texto_limpo = texto.replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()
            texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
            try:
                return float(texto_limpo)
            except Exception:
                return 0.0

        for idx, serie_raw in enumerate(series_bruto, 1):
            try:
                id_serie = serie_raw.get('id_serie', 'DESCONHECIDA')
                print(f'[SISBAJUD] Analisando serie {idx}: {id_serie}')

                situacao = serie_raw.get('situacao', '').strip()
                if 'encerrada' not in situacao.lower():
                    continue

                data_texto = serie_raw.get('data_conclusao', '').strip()
                if not data_texto:
                    continue

                partes = data_texto.upper().split()
                if len(partes) < 5:
                    continue

                try:
                    dia = int(partes[0])
                    mes_nome = partes[2]
                    ano = int(partes[4])
                    mes = meses_map.get(mes_nome)

                    if not mes:
                        continue

                    data_serie = datetime(ano, mes, dia)
                except (ValueError, IndexError):
                    continue

                if isinstance(data_limite, datetime) and data_serie < data_limite:
                    continue

                valor_bloqueado_text = serie_raw.get('valor_bloqueado_text', 'R$ 0,00')
                valor_bloquear_text = serie_raw.get('valor_bloquear_text', 'R$ 0,00')

                valor_bloqueado = extrair_valor_monetario(valor_bloqueado_text)
                valor_bloquear = extrair_valor_monetario(valor_bloquear_text)

                serie_valida = {
                    'id_serie': id_serie,
                    'protocolo': serie_raw.get('protocolo', ''),
                    'acao': serie_raw.get('acao', ''),
                    'data_conclusao': data_serie,
                    'data_conclusao_text': data_texto,
                    'situacao': situacao,
                    'valor_bloqueado': valor_bloqueado,
                    'valor_bloquear': valor_bloquear,
                    'valor_bloqueado_text': valor_bloqueado_text,
                    'valor_bloquear_text': valor_bloquear_text,
                    'linha_index': serie_raw.get('linha_index', idx - 1)
                }

                series_validas.append(serie_valida)

            except Exception as e:
                print(f'[SISBAJUD] Erro processando serie {idx}: {e}')
                continue

        print(f'[SISBAJUD] Filtradas {len(series_validas)} series validas de {len(series_bruto)}')
        return series_validas

    except Exception as e:
        print(f'[SISBAJUD] Erro ao filtrar series: {e}')
        import traceback
        traceback.print_exc()
        return []