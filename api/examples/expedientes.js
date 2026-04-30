// Exemplo: api/examples/expedientes.js
// Uso em console do navegador autenticado:
// fetchExpedientesNormalizado(6108528).then(console.table)

async function fetchExpedientesNormalizado(processoId, opts = {}) {
  const paginaInicial = opts.pagina || 1;
  const tamanhoPagina = opts.tamanhoPagina || 50;
  const instancia = opts.instancia || 1;
  const resultados = [];

  function formatDDMMYY(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yy = String(d.getFullYear()).slice(-2);
    return `${dd}/${mm}/${yy}`;
  }

  async function fetchPage(pagina) {
    const url = `/pje-comum-api/api/processos/id/${processoId}/expedientes`;
    const params = new URLSearchParams({ pagina: String(pagina), tamanhoPagina: String(tamanhoPagina), instancia: String(instancia) });
    const res = await fetch(url + '?' + params.toString(), { credentials: 'include' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  let pagina = paginaInicial;
  while (true) {
    const body = await fetchPage(pagina);
    const items = body && body.resultado ? body.resultado : [];
    for (const it of items) {
      const prazo = (typeof it.prazoLegal === 'number') ? it.prazoLegal : (it.prazoLegal ? Number(it.prazoLegal) : null);
      let fimPrazoIso = it.fimDoPrazoLegal || null;
      if (!fimPrazoIso && prazo && (it.dataCiencia || it.dataCriacao)) {
        try {
          const base = new Date(it.dataCiencia || it.dataCriacao);
          fimPrazoIso = new Date(base.getTime() + prazo * 24 * 60 * 60 * 1000).toISOString();
        } catch (e) {
          fimPrazoIso = null;
        }
      }

      resultados.push({
        destinatario: it.nomePessoaParte || null,
        tipo: it.tipoExpediente || null,
        meio: it.meioExpediente || null,
        dataCriacao: formatDDMMYY(it.dataCriacao),
        dataCiencia: formatDDMMYY(it.dataCiencia),
        prazo: prazo,
        fimPrazo: formatDDMMYY(fimPrazoIso),
        fechado: !!it.fechado
      });
    }
    if (!Array.isArray(items) || items.length < tamanhoPagina) break;
    pagina += 1;
  }
  return resultados;
}

// Export for module environments (optional)
if (typeof module !== 'undefined') module.exports = { fetchExpedientesNormalizado };
