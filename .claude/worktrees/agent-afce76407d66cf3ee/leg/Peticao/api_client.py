from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from dataclasses import dataclass
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver

# ---------------------------------------------------------------------------
# Modelo de dados — campos compatíveis com pet_novo.PeticaoLinha
# ---------------------------------------------------------------------------

@dataclass
class PeticaoItem:
    numero_processo: str
    tipo_peticao: str
    descricao: str
    tarefa: str
    fase: str
    data_juntada: str
    eh_perito: bool = False          # nomePapelUsuarioDocumento == "Perito"
    parte: str = ""                  # "Ativo (Advogado)", "Terceiro (Perito)" etc.
    id_processo: str = ""
    id_item: str = ""
    data_audiencia: Optional[str] = None
    polo: Optional[str] = None       # "ativo" | "passivo" (compat. pet_novo)

    @property
    def texto_classificacao(self) -> str:
        return f"{self.tipo_peticao} {self.descricao} {self.tarefa} {self.fase}"


# ---------------------------------------------------------------------------
# JS executado no browser
# ---------------------------------------------------------------------------

_JS_FETCH = """
const tamPag   = arguments[0] || 100;
const callback = arguments[1];

function asArray(d) {
  if (!d) return [];
  if (Array.isArray(d)) return d;
  if (Array.isArray(d.resultado)) return d.resultado;
  if (d.resultado && Array.isArray(d.resultado.conteudo)) return d.resultado.conteudo;
  if (Array.isArray(d.conteudo)) return d.conteudo;
  if (Array.isArray(d.dados)) return d.dados;
  return [];
}

(async function () {
  var base = location.origin;
  var hdrs = { 'Accept': 'application/json' };
  var ep   = base + '/pje-comum-api/api/escaninhos/peticoesjuntadas';
  try {
    var r = await fetch(ep + '?pagina=1&tamanhoPagina=' + tamPag + '&ordenacaoCrescente=true',
                        { credentials: 'include', headers: hdrs });
    if (!r.ok) { callback({ erro: 'STATUS_' + r.status, resultado: [] }); return; }
    var data  = await r.json();
    var todos = asArray(data);
    if (!todos.length) { callback({ erro: 'SEM_DADOS', resultado: [] }); return; }
    var totalPags = (data.totalPaginas || data.quantidadePaginas) || 1;
    for (var pg = 2; pg <= Math.min(totalPags, 10); pg++) {
      try {
        var r2 = await fetch(ep + '?pagina=' + pg + '&tamanhoPagina=' + tamPag + '&ordenacaoCrescente=true',
                             { credentials: 'include', headers: hdrs });
        if (r2.ok) todos = todos.concat(asArray(await r2.json()));
      } catch (e) { break; }
    }
    callback({ endpoint: 'peticoesjuntadas', resultado: todos });
  } catch (e) {
    callback({ erro: 'ASYNC_ERR: ' + e.message, resultado: [] });
  }
})();
"""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class PeticaoAPIClient:
    """Busca petições do escaninho via JavaScript direto (como pet.js)."""

    def fetch(self, driver: WebDriver, tamanho_pagina: int = 100) -> List[PeticaoItem]:
        try:
            driver.set_script_timeout(60)
            res = driver.execute_async_script(_JS_FETCH, tamanho_pagina)
        finally:
            try:
                driver.set_script_timeout(30)
            except Exception:
                pass

        if not res or res.get('erro'):
            logger.warning(f"[PET_API] {(res or {}).get('erro', 'sem_resposta')}")
            return []

        dados = res.get('resultado', [])
        logger.info(f"[PET_API] {len(dados)} petições via '{res.get('endpoint', '?')}'")
        return [_normalizar(raw) for raw in dados if raw]


def _normalizar(raw: dict) -> PeticaoItem:
    proc = raw.get('processo') or raw.get('processoJudicial') or {}
    numero = (proc.get('numero') or proc.get('numeroProcesso') or
              raw.get('numeroProcesso') or raw.get('nrProcesso') or '')

    polo_raw = (raw.get('poloPeticionante') or '').upper()
    polo_label = ('Ativo'    if 'ATIVO'     in polo_raw else
                  'Passivo'  if 'PASSIVO'   in polo_raw else
                  'Terceiro' if 'TERCEIRO'  in polo_raw else polo_raw)
    polo_key   = ('ativo'    if 'ATIVO'     in polo_raw else
                  'passivo'  if 'PASSIVO'   in polo_raw else None)
    papel = (raw.get('nomePapelUsuarioDocumento') or '').strip()
    parte = f"{polo_label} ({papel})" if polo_label and papel else polo_label or papel

    tarefa_obj = raw.get('tarefa') or raw.get('tarefaAtual')
    if not isinstance(tarefa_obj, dict):
        tarefa_obj = {}
    tarefa = (raw.get('nomeTarefa') or tarefa_obj.get('nome') or
              tarefa_obj.get('descricao') or '')

    return PeticaoItem(
        numero_processo=numero,
        tipo_peticao=(raw.get('nomeTipoProcessoDocumento') or raw.get('nomeTipoPeticao') or
                      raw.get('descricaoTipoPeticao') or raw.get('tipoPeticao') or ''),
        descricao=(raw.get('descricao') or raw.get('descricaoPeticao') or ''),
        tarefa=tarefa,
        fase=(raw.get('faseProcessual') or raw.get('fase') or raw.get('nomeFase') or
              proc.get('fase') or ''),
        data_juntada=(raw.get('dataJuntada') or raw.get('dataCadastro') or ''),
        eh_perito=(papel.lower() == 'perito'),
        parte=parte,
        polo=polo_key,
        id_processo=(proc.get('id') or proc.get('idProcesso') or raw.get('idProcesso') or ''),
        id_item=(raw.get('idDocumento') or raw.get('idPeticao') or raw.get('id') or ''),
    )
