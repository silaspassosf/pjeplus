"""SISB/conferencia_teimosinha.py — conferência das séries de Teimosinha e definição do fluxo.

Espelha, num só lugar, o que hoje está espalhado em:
  - `SISB/processamento/series_filtro.py`  (`_filtrar_series` — lê a tabela e filtra)
  - `SISB/core.py`, bloco "4. Determinar tipo de fluxo" (NEGATIVO / DESBLOQUEIO / POSITIVO)
  - `SISB/processamento/series_estrategia.py` (`_calcular_estrategia_bloqueio`)

A conferência é **DOM, não API** — igual ao botão "Conferir SISBAJUD(Teimosinha)" da
extensão +PJe (`+pje/PJe-Atual/gigs-plugin.js`: `conferirTeimosinhaEmLote()` ->
`obterResultadoTeimosinha()`): abre https://sisbajud.cnj.jus.br/teimosinha, clica
"Limpar", digita em `input[placeholder="Número do Processo"]` e clica "Consultar".

Extração **idêntica à real** (`_filtrar_series`): tabela `table.mat-table`, linhas
`tbody tr.mat-row` / `tbody tr[mat-row]`, células por `td[data-label="<campo>"]` com
fallback `td.cdk-column-<campo>`, texto via `textContent` normalizado (\\u00a0 -> espaço,
espaços colapsados). Datas lidas como `10 DE SETEMBRO DE 2026` (5 partes: dia, DE, mês,
DE, ano) — qualquer outro formato é descartado, como no código real.

Diferença em relação ao +PJe: **nenhuma janela oculta e nenhuma interface após o
resultado** — usa a própria página do driver SISBAJUD e devolve só a definição de fluxo
(dict), sem montar botão/lista/tela.

Contrato (condução tranquila: nunca levanta exceção):
    from SISB.conferencia_teimosinha import conferir_fluxo

    fluxo = conferir_fluxo(driver_sisb, numero_processo, dados_processo=dados)
    fluxo['tipo_fluxo']        # 'NEGATIVO' | 'DESBLOQUEIO' | 'POSITIVO'
    fluxo['estrategia']        # None | {'tipo': 'TRANSFERIR_TUDO'|'TRANSFERIR_PARCIAL', ...}
    fluxo['series_validas']    # séries encerradas dentro do prazo (formato do core.py)

Peças separadas, para quem já está na página da teimosinha:
    series  = ler_series(driver)                      # lê a tabela, sem navegar
    validas = filtrar_validas(series, data_limite)    # encerradas + prazo
    fluxo   = definir_fluxo(validas, dados_processo)  # NEGATIVO/DESBLOQUEIO/POSITIVO + estratégia
"""

import logging
from datetime import datetime, timedelta

from Fix import espera
from Fix.core import aguardar_renderizacao_nativa

logger = logging.getLogger(__name__)

URL_TEIMOSINHA = 'https://sisbajud.cnj.jus.br/teimosinha'
SEL_CAMPO = 'input[placeholder="Número do Processo"]'
SEL_TABELA = 'table.mat-table'
SEL_TABELA_FALLBACK = 'sisbajud-pesquisa-teimosinha'
SEL_LINHAS = SEL_TABELA + ' tbody tr.mat-row, ' + SEL_TABELA + ' tbody tr[mat-row]'
SEL_AVISO = 'sisbajud-snack-messenger, .mat-snack-bar-container, .snackbar'
SEL_LIMPAR = "//button[contains(normalize-space(.), 'Limpar')]"
SEL_CONSULTAR = "//button[contains(normalize-space(.), 'Consultar')]"

# Extração fiel ao script de `_filtrar_series` (mesmos data-label e fallback por classe).
JS_LER_SERIES = r"""
() => {
  function norm(text) {
    return String(text || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function getCell(row, dataLabel, legacyClass) {
    return row.querySelector('td[data-label="' + dataLabel + '"]') ||
           row.querySelector('td.' + legacyClass) || null;
  }
  const tabela = document.querySelector('table.mat-table') ||
                 document.querySelector('sisbajud-pesquisa-teimosinha');
  if (!tabela) return null;
  let linhas = tabela.querySelectorAll('tbody tr.mat-row, tbody tr[mat-row]');
  if (!linhas.length) linhas = tabela.querySelectorAll('tbody tr');
  return Array.from(linhas).map(function (linha, i) {
    const idCell = getCell(linha, 'sequencial', 'cdk-column-sequencial');
    const protCell = getCell(linha, 'protocolo', 'cdk-column-protocolo');
    const procCell = getCell(linha, 'processo', 'cdk-column-processo');
    const vbCell = getCell(linha, 'valorBloquear', 'cdk-column-valorBloquear');
    const vbdCell = getCell(linha, 'valorBloqueado', 'cdk-column-valorBloqueado');
    const dpCell = getCell(linha, 'dataProgramada', 'cdk-column-dataProgramada');
    const sfCell = getCell(linha, 'dataFim', 'cdk-column-dataFim');
    return {
      linha_index: i,
      tem_id: !!idCell,
      id_serie: idCell ? norm(idCell.textContent) : '',
      protocolo: protCell ? norm(protCell.textContent) : '',
      acao: procCell ? norm(procCell.textContent) : '',
      valor_bloquear_text: vbCell ? norm(vbCell.textContent) : '',
      valor_bloqueado_text: vbdCell ? norm(vbdCell.textContent) : '',
      data_conclusao_text: dpCell ? norm(dpCell.textContent) : '',
      situacao: sfCell ? norm(sfCell.textContent) : ''
    };
  });
}
"""

_MESES = {
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12,
}

# limites do fluxo (idênticos ao bloco "4. Determinar tipo de fluxo" do core.py)
LIMITE_IRRISORIO = 100.0     # abaixo disto o bloqueado é resíduo
LIMITE_BLOQUEIO = 1000.0     # a partir disto houve ordem relevante
VALOR_EXECUCAO_FALLBACK = 1003.0  # fallback seguro do `_calcular_estrategia_bloqueio`


# ───────────────────────────── infra mínima ─────────────────────────────


def _log(mensagem, log=True, nivel='info'):
    if not log:
        return
    getattr(logger, nivel, logger.info)('Teimosinha: %s', mensagem)


def _pagina(driver):
    """Página do Playwright por trás da fachada do driver."""
    return getattr(driver, 'page', driver)


def _loc(driver, seletor):
    return _pagina(driver).locator(seletor).first


def _visivel(loc):
    try:
        return bool(loc.is_visible())
    except Exception:
        return False


def _clicar(driver, seletor, log=True):
    """Clica o primeiro elemento visível de `seletor` (CSS ou XPath)."""
    try:
        loc = _loc(driver, seletor)
        if not _visivel(loc):
            _log('botão não visível: %s' % seletor, log, 'debug')
            return False
        loc.click(timeout=5000)
        return True
    except Exception as e:
        _log('falha ao clicar em %s: %s' % (seletor, e), log, 'debug')
        return False


def _valor(texto):
    """'R$ 12.345,67' -> 12345.67 — igual a `extrair_valor_monetario` do código real."""
    texto_limpo = (texto or '').replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()
    texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
    try:
        return float(texto_limpo)
    except Exception:
        return 0.0


def _data(texto):
    """'10 DE SETEMBRO DE 2026' -> datetime(2026, 9, 10).

    Regra idêntica à real: exige 5 partes, mês na posição 2 e ano na posição 4;
    qualquer outro formato devolve None (a série é descartada, como no código real).
    """
    texto = (texto or '').strip()
    if not texto:
        return None
    partes = texto.upper().split()
    if len(partes) < 5:
        return None
    try:
        dia = int(partes[0])
        mes = _MESES.get(partes[2]) or _MESES.get(partes[2][:3])
        ano = int(partes[4])
        if not mes:
            return None
        return datetime(ano, mes, dia)
    except (ValueError, IndexError):
        return None


# ───────────────────────────── navegação ─────────────────────────────


def _garantir_pagina(driver, log=True):
    """Deixa o driver na página /teimosinha com o campo de número pronto."""
    try:
        atual = getattr(driver, 'current_url', '') or ''
        if 'teimosinha' in atual and espera.ate_aparecer(driver, SEL_CAMPO, teto=3):
            return True

        for tentativa in (1, 2):
            driver.get(URL_TEIMOSINHA)
            aguardar_renderizacao_nativa(driver, timeout=10)
            if espera.ate_aparecer(driver, SEL_CAMPO, teto=15):
                return True
            _log('campo de número não apareceu (tentativa %d/2)' % tentativa, log, 'warning')
        return False
    except Exception as e:
        _log('falha ao abrir %s: %s' % (URL_TEIMOSINHA, e), log, 'warning')
        return False


# ───────────────────────────── leitura da tabela ─────────────────────────────


def ler_series(driver, log=True):
    """Lê a tabela de séries já carregada (sem navegar nem consultar).

    Devolve o mesmo conteúdo de `series_bruto` em `_filtrar_series`, acrescido dos
    campos já convertidos (valor_bloqueado, valor_bloquear, data_conclusao, encerrada).
    """
    try:
        brutos = _pagina(driver).evaluate(JS_LER_SERIES)
    except Exception as e:
        _log('falha ao ler a tabela: %s' % e, log, 'warning')
        return []

    if brutos is None:
        _log('tabela de séries não encontrada (table.mat-table)', log, 'debug')
        return []

    series = []
    for indice, bruto in enumerate(brutos or []):
        serie = {'linha_index': bruto.get('linha_index', indice)}
        if bruto.get('tem_id'):
            for campo in ('id_serie', 'protocolo', 'acao', 'valor_bloquear_text',
                          'valor_bloqueado_text', 'data_conclusao_text', 'situacao'):
                serie[campo] = bruto.get(campo, '')

        serie['valor_bloqueado'] = _valor(serie.get('valor_bloqueado_text'))
        serie['valor_bloquear'] = _valor(serie.get('valor_bloquear_text'))
        serie['data_conclusao'] = _data(serie.get('data_conclusao_text'))
        serie['encerrada'] = 'encerrada' in (serie.get('situacao') or '').lower()
        series.append(serie)

    _log('%d série(s) na tabela' % len(series), log, 'debug')
    return series


# ───────────────────────────── fluxo ─────────────────────────────


def filtrar_validas(series, data_limite=None, log=True):
    """Séries encerradas e dentro do prazo — mesma saída de `_filtrar_series`."""
    validas = []
    for idx, serie in enumerate(series or [], 1):
        id_serie = serie.get('id_serie') or 'DESCONHECIDA'
        _log('analisando série %d: %s' % (idx, id_serie), log, 'debug')

        situacao = (serie.get('situacao') or '').strip()
        if 'encerrada' not in situacao.lower():
            continue

        data_texto = (serie.get('data_conclusao_text') or '').strip()
        if not data_texto:
            continue

        data_serie = serie.get('data_conclusao')
        if data_serie is None:
            _log('série %s com data ilegível (%r) — descartada' % (id_serie, data_texto),
                 log, 'debug')
            continue

        if isinstance(data_limite, datetime) and data_serie < data_limite:
            continue

        valor_bloqueado_text = serie.get('valor_bloqueado_text') or 'R$ 0,00'
        valor_bloquear_text = serie.get('valor_bloquear_text') or 'R$ 0,00'

        validas.append({
            'id_serie': id_serie,
            'protocolo': serie.get('protocolo', ''),
            'acao': serie.get('acao', ''),
            'data_conclusao': data_serie,
            'data_conclusao_text': data_texto,
            'situacao': situacao,
            'valor_bloqueado': _valor(valor_bloqueado_text),
            'valor_bloquear': _valor(valor_bloquear_text),
            'valor_bloqueado_text': valor_bloqueado_text,
            'valor_bloquear_text': valor_bloquear_text,
            'linha_index': serie.get('linha_index', idx - 1),
        })

    _log('filtradas %d série(s) válida(s) de %d' % (len(validas), len(series or [])), log)
    return validas


def _estrategia(series_validas, dados_processo=None, log=True):
    """TRANSFERIR_TUDO / TRANSFERIR_PARCIAL — mesma conta de `_calcular_estrategia_bloqueio`."""
    valor_execucao_str = (dados_processo or {}).get('divida', {}).get('valor', 'R$ 0,00')
    valor_execucao = _valor(valor_execucao_str) or VALOR_EXECUCAO_FALLBACK

    total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)
    tipo = 'TRANSFERIR_TUDO' if total_bloqueado <= valor_execucao else 'TRANSFERIR_PARCIAL'

    if log:
        logger.info('[SISBAJUD] Estratégia de bloqueio: execução R$ %.2f | bloqueado R$ %.2f',
                    valor_execucao, total_bloqueado)
        logger.info('[SISBAJUD] Estratégia: %s', tipo)

    return {
        'tipo': tipo,
        'valor_execucao': valor_execucao,
        'total_bloqueado': total_bloqueado,
        'acumulado_limite': valor_execucao,
    }


def definir_fluxo(series_validas, dados_processo=None, log=True):
    """Define NEGATIVO / DESBLOQUEIO / POSITIVO e, no POSITIVO, a estratégia.

    Regras idênticas ao bloco "4. Determinar tipo de fluxo" do `SISB/core.py`.
    No POSITIVO com TRANSFERIR_PARCIAL, devolve também as séries ordenadas por valor
    bloqueado (decrescente), como o core.py faz antes de processar.
    """
    series_validas = series_validas or []
    total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)
    total_bloquear = sum(float(s.get('valor_bloquear', 0)) for s in series_validas)

    if total_bloqueado == 0.0:
        tipo_fluxo = 'NEGATIVO'
    elif total_bloqueado < LIMITE_IRRISORIO and total_bloquear >= LIMITE_BLOQUEIO:
        tipo_fluxo = 'DESBLOQUEIO'
    else:
        tipo_fluxo = 'POSITIVO'

    estrategia = None
    series_ordenadas = None
    if tipo_fluxo == 'POSITIVO':
        estrategia = _estrategia(series_validas, dados_processo, log=log)
        if estrategia['tipo'] == 'TRANSFERIR_PARCIAL':
            series_ordenadas = sorted(
                series_validas, key=lambda s: float(s.get('valor_bloqueado', 0)), reverse=True)

    if log:
        logger.info('[SISBAJUD] Conferência: %d série(s) válida(s) | bloqueado R$ %.2f | '
                    'a bloquear R$ %.2f', len(series_validas), total_bloqueado, total_bloquear)
        logger.info('[SISBAJUD] Tipo de fluxo determinado: %s', tipo_fluxo)

    return {
        'tipo_fluxo': tipo_fluxo,
        'total_bloqueado': total_bloqueado,
        'total_bloquear': total_bloquear,
        'estrategia': estrategia,
        'series_ordenadas': series_ordenadas,
    }


# ───────────────────────────── API pública ─────────────────────────────


def conferir(driver, numero, log=True):
    """Consulta a teimosinha de `numero` e devolve as séries (DOM, sem janela oculta)."""
    numero = (numero or '').strip()
    if not numero:
        _log('conferir: número vazio', log, 'warning')
        return []

    if not _garantir_pagina(driver, log):
        return []

    try:
        _clicar(driver, SEL_LIMPAR, log)
        campo = _loc(driver, SEL_CAMPO)
        campo.click(timeout=5000)
        campo.fill('')
        campo.fill(numero)
        try:
            campo.press('Tab')
        except Exception:
            pass

        if not _clicar(driver, SEL_CONSULTAR, log):
            try:
                campo.press('Enter')
            except Exception:
                pass

        espera.assentar(driver, 0.8, motivo='teimosinha: consulta')
        espera.ate_aparecer(driver, SEL_LINHAS, teto=15)
        series = ler_series(driver, log)

        if series:
            _log('%s: %d série(s)' % (numero, len(series)), log)
        else:
            avisou = espera.ate_texto(driver, SEL_AVISO, 'nhuma s', teto=2)
            _log('%s: nenhuma série%s'
                 % (numero, '' if avisou else ' (sem aviso na tela — conferir manualmente)'),
                 log, 'info' if avisou else 'warning')
        return series
    except Exception as e:
        _log('conferir(%s) falhou: %s' % (numero, e), log, 'warning')
        return []


def conferir_fluxo(driver, numero=None, dados_processo=None, data_limite=None, log=True):
    """Conferência completa: séries -> válidas -> fluxo/estratégia.

    `numero` None = já estamos na página da teimosinha com a tabela carregada
    (caso do `core.py`, que insere o processo no SISBAJUD logo antes).
    """
    if data_limite is None:
        data_limite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) \
            - timedelta(days=30)

    series = conferir(driver, numero, log=log) if numero else ler_series(driver, log)
    series_validas = filtrar_validas(series, data_limite, log=log)
    fluxo = definir_fluxo(series_validas, dados_processo, log=log)
    fluxo['series'] = series
    fluxo['series_validas'] = series_validas
    fluxo['data_limite'] = data_limite
    return fluxo


def conferir_lote(driver, numeros, dados_processo=None, log=True):
    """`conferir_fluxo` para vários números -> {numero: fluxo}."""
    resultado = {}
    for numero in numeros or []:
        limpo = (numero or '').strip()
        if not limpo:
            continue
        resultado[limpo] = conferir_fluxo(driver, limpo, dados_processo=dados_processo, log=log)
    return resultado


def tem_teimosinha(driver, numero, log=False):
    """True se houver pelo menos uma série na teimosinha de `numero`."""
    return bool(conferir(driver, numero, log=log))


def resumo(fluxo_ou_series):
    """Totais curtos para log/relatório."""
    if isinstance(fluxo_ou_series, dict):
        return {
            'tipo_fluxo': fluxo_ou_series.get('tipo_fluxo'),
            'series': len(fluxo_ou_series.get('series_validas') or []),
            'valor_bloqueado': round(fluxo_ou_series.get('total_bloqueado', 0.0), 2),
            'valor_bloquear': round(fluxo_ou_series.get('total_bloquear', 0.0), 2),
            'estrategia': (fluxo_ou_series.get('estrategia') or {}).get('tipo'),
        }
    series = fluxo_ou_series or []
    return {
        'series': len(series),
        'valor_bloqueado': round(sum(float(s.get('valor_bloqueado', 0)) for s in series), 2),
        'valor_bloquear': round(sum(float(s.get('valor_bloquear', 0)) for s in series), 2),
    }
