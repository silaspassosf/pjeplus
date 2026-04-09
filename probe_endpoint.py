# Script de sonda: descobre o endpoint exato que responde no seu ambiente
import sys, os
sys.path.insert(0, r'D:\PjePlus')
from Fix.utils import driver_pc, login_cpf
import json, time

JS_PROBE = """
const cb = arguments[0];
const base = location.origin;
const paths = [
  '/pje-comum-api/api/escaninhos/peticoesjuntadas',
  '/pje-comum-api/api/escaninhos/peticoes-juntadas',
  '/pje-comum-api/api/escaninhos/peticoes',
  '/pje-comum-api/api/escaninhos/documentosinternos?peticoesJuntadas=true'
];
(async function() {
  var results = [];
  for (var p of paths) {
    var sep = p.includes('?') ? '&' : '?';
    var url = base + p + sep + 'pagina=1&tamanhoPagina=5&ordenacaoCrescente=true';
    try {
      var r = await fetch(url, { credentials: 'include', headers: { Accept: 'application/json' } });
      var body = null;
      try { body = await r.json(); } catch(e) {}
      var arr = Array.isArray(body) ? body : (body && (body.resultado || body.conteudo || body.dados) || []);
      if (!Array.isArray(arr)) arr = [];
      results.push({ path: p, status: r.status, ok: r.ok, itens: arr.length });
    } catch(e) {
      results.push({ path: p, status: 0, ok: false, erro: e.message });
    }
  }
  cb(results);
})().catch(e => cb([{erro: e.message}]));
"""

drv = driver_pc()
login_cpf(drv)
drv.get('https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas')
time.sleep(3)
drv.set_script_timeout(60)
r = drv.execute_async_script(JS_PROBE)
print(json.dumps(r, indent=2))
drv.quit()
