import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from Fix.log import getmodulelogger
from Fix.utils import driver_pc, login_cpf
import json
import time

logger = getmodulelogger(__name__)

# JS que executa chamadas de API com debug detalhado por endpoint
_JS_FETCH_PROCESSO_APIS = """
const idProcesso = arguments[0];
const callback    = arguments[1];

// Simula a classe ApiWrapper montarUrl
function montarUrl(dominio, path, params = {}) {
  let urlBase = dominio;
  if (!urlBase.startsWith('http')) urlBase = 'https://' + urlBase;
  urlBase = urlBase.replace('dev015','pje');

  // Substitui parâmetros no path
  let pathFinal = path;
  for (const [key, value] of Object.entries(params)) {
    if (path.includes('{' + key + '}')) {
      pathFinal = pathFinal.replace('{' + key + '}', encodeURIComponent(value));
    }
  }

  const url = new URL(urlBase + pathFinal);

  // Adiciona params que sobraram como query string
  for (const [key, value] of Object.entries(params)) {
    if (!path.includes('{' + key + '}') && value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  }

  return url.toString();
}

(async function () {
  var base = location.origin;
  // Headers IGUAIS aos do maispje
  var hdrs = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Grau-Instancia': '2'  // 1=Primeiro grau (Vara), 2=Segundo grau (Tribunal)
  };
  var debug = [];

  try {
    // Agora vamos direto ao ponto - já temos o ID do processo
    console.log('[PROBE-API] EP1: usando ID do processo diretamente ' + idProcesso);
    debug.push('EP1_START: ID=' + idProcesso);

    // 1. Busca dados completos do processo
    console.log('[PROBE-API] EP2: buscando dados completos para ID ' + idProcesso);
    debug.push('EP2_START: idProcesso=' + idProcesso);

    var urlCompleto = montarUrl(base, '/pje-comum-api/api/processos/id/{idProcesso}/completo', {
      idProcesso: idProcesso
    });
    debug.push('EP2_URL: ' + urlCompleto);
    console.log('[PROBE-API] EP2_URL: ' + urlCompleto);

    var r2 = await fetch(urlCompleto, { credentials: 'include', headers: hdrs });
    debug.push('EP2_STATUS: ' + r2.status);
    console.log('[PROBE-API] EP2_STATUS: ' + r2.status);

    var processoCompleto = {};
    var processoItem = {};
    if (r2.ok) {
      var txtCompleto = await r2.text();
      debug.push('EP2_BODY_LEN: ' + txtCompleto.length);
      console.log('[PROBE-API] EP2_BODY_LEN: ' + txtCompleto.length);

      if (txtCompleto && txtCompleto.trim()) {
        try {
          processoCompleto = JSON.parse(txtCompleto);
          processoItem = processoCompleto; // Quando usamos /completo, o objeto completo é o processo
          debug.push('EP2_PARSE_OK');
          console.log('[PROBE-API] EP2_PARSE_OK');
        } catch (e) {
          debug.push('EP2_PARSE_ERR: ' + e.message);
          console.log('[PROBE-API] EP2_PARSE_ERR: ' + e.message);
        }
      } else {
        debug.push('EP2_EMPTY_BODY');
        console.log('[PROBE-API] EP2_EMPTY_BODY');
      }
    } else {
      var txtErr2 = await r2.text();
      debug.push('EP2_NOT_OK: ' + r2.status + ', len=' + txtErr2.length);
      console.log('[PROBE-API] EP2_NOT_OK: ' + r2.status);
      
      // Se o endpoint /completo falhar, tentar o endpoint básico
      console.log('[PROBE-API] EP2B: tentando endpoint básico para ID ' + idProcesso);
      var urlBasico = montarUrl(base, '/pje-comum-api/api/processos/id/{idProcesso}', {
        idProcesso: idProcesso
      });
      debug.push('EP2B_URL: ' + urlBasico);
      console.log('[PROBE-API] EP2B_URL: ' + urlBasico);

      var r2b = await fetch(urlBasico, { credentials: 'include', headers: hdrs });
      debug.push('EP2B_STATUS: ' + r2b.status);
      console.log('[PROBE-API] EP2B_STATUS: ' + r2b.status);

      if (r2b.ok) {
        var txtBasico = await r2b.text();
        debug.push('EP2B_BODY_LEN: ' + txtBasico.length);
        console.log('[PROBE-API] EP2B_BODY_LEN: ' + txtBasico.length);

        if (txtBasico && txtBasico.trim()) {
          try {
            processoCompleto = JSON.parse(txtBasico);
            processoItem = processoCompleto;
            debug.push('EP2B_PARSE_OK');
            console.log('[PROBE-API] EP2B_PARSE_OK');
          } catch (e) {
            debug.push('EP2B_PARSE_ERR: ' + e.message);
            console.log('[PROBE-API] EP2B_PARSE_ERR: ' + e.message);
          }
        } else {
          debug.push('EP2B_EMPTY_BODY');
          console.log('[PROBE-API] EP2B_EMPTY_BODY');
        }
      }
    }

    // 2. Busca tarefas
    var tarefas = [];
    console.log('[PROBE-API] EP3: buscando tarefas para ID ' + idProcesso);
    debug.push('EP3_START');

    var urlTarefas = montarUrl(base, '/pje-comum-api/api/processos/id/{idProcesso}/tarefas', {
      idProcesso: idProcesso,
      maisRecente: true
    });
    debug.push('EP3_URL: ' + urlTarefas);
    console.log('[PROBE-API] EP3_URL: ' + urlTarefas);

    var r3 = await fetch(urlTarefas, { credentials: 'include', headers: hdrs });
    debug.push('EP3_STATUS: ' + r3.status);
    console.log('[PROBE-API] EP3_STATUS: ' + r3.status);

    if (r3.ok) {
      var txtTarefas = await r3.text();
      debug.push('EP3_BODY_LEN: ' + txtTarefas.length);
      console.log('[PROBE-API] EP3_BODY_LEN: ' + txtTarefas.length);

      if (txtTarefas && txtTarefas.trim()) {
        try {
          var respTarefas = JSON.parse(txtTarefas);
          tarefas = Array.isArray(respTarefas) ? respTarefas : (respTarefas.resultado || []);
          debug.push('EP3_PARSE_OK: ' + tarefas.length + ' tarefas');
          console.log('[PROBE-API] EP3_PARSE_OK: ' + tarefas.length + ' tarefas');
        } catch (e) {
          debug.push('EP3_PARSE_ERR: ' + e.message);
          console.log('[PROBE-API] EP3_PARSE_ERR: ' + e.message);
        }
      } else {
        debug.push('EP3_EMPTY_BODY');
        console.log('[PROBE-API] EP3_EMPTY_BODY');
      }
    }

    // 3. Busca cálculos
    var calculos = [];
    console.log('[PROBE-API] EP4: buscando cálculos para ID ' + idProcesso);
    debug.push('EP4_START');

    var urlCalculos = montarUrl(base, '/pje-comum-api/api/calculos/processo', {
      idProcesso: idProcesso,
      pagina: 1,
      tamanhoPagina: 10,
      ordenacaoCrescente: true,
      mostrarCalculosHomologados: true,
      incluirCalculosHomologados: true
    });
    debug.push('EP4_URL: ' + urlCalculos);
    console.log('[PROBE-API] EP4_URL: ' + urlCalculos);

    var r4 = await fetch(urlCalculos, { credentials: 'include', headers: hdrs });
    debug.push('EP4_STATUS: ' + r4.status);
    console.log('[PROBE-API] EP4_STATUS: ' + r4.status);

    if (r4.ok) {
      var txtCalculos = await r4.text();
      debug.push('EP4_BODY_LEN: ' + txtCalculos.length);
      console.log('[PROBE-API] EP4_BODY_LEN: ' + txtCalculos.length);

      if (txtCalculos && txtCalculos.trim()) {
        try {
          var respCalculos = JSON.parse(txtCalculos);
          calculos = Array.isArray(respCalculos) ? respCalculos : (respCalculos.resultado || []);
          debug.push('EP4_PARSE_OK: ' + calculos.length + ' cálculos');
          console.log('[PROBE-API] EP4_PARSE_OK: ' + calculos.length + ' cálculos');
        } catch (e) {
          debug.push('EP4_PARSE_ERR: ' + e.message);
          console.log('[PROBE-API] EP4_PARSE_ERR: ' + e.message);
        }
      } else {
        debug.push('EP4_EMPTY_BODY');
        console.log('[PROBE-API] EP4_EMPTY_BODY');
      }
    }

    callback({
      processoItem: processoItem,
      processoCompleto: processoCompleto,
      tarefas: tarefas,
      calculos: calculos,
      debug: debug,
      endpoint: 'EP2_COMPLETO+EP3_TAREFAS+EP4_CALCULOS'
    });
  } catch (e) {
    console.log('[PROBE-API] EXCEPTION: ' + e.message);
    callback({ erro: 'ASYNC_ERR: ' + e.message, debug: debug, endpoint: 'EXCEPTION' });
  }
})();
"""

def fetch_processo_completo(driver, id_processo: str):
    """Busca dados completos de processo usando as APIs como maispje faz."""
    try:
        driver.set_script_timeout(30)
        res = driver.execute_async_script(_JS_FETCH_PROCESSO_APIS, id_processo)
    finally:
        try:
            driver.set_script_timeout(30)
        except:
            pass

    if not res:
        logger.error(f"[API] Sem resposta para processo ID {id_processo}")
        return None

    # Log do debug detalhado
    debug_info = res.get('debug', [])
    endpoint_failed = res.get('endpoint', '?')

    if debug_info:
        logger.info(f"[API-DEBUG] Endpoint: {endpoint_failed}")
        for i, log in enumerate(debug_info):
            logger.info(f"[API-DEBUG] {i:02d}: {log}")

    if res.get('erro'):
        logger.error(f"[API] Erro: {res['erro']}")
        return None

    processo_item = res.get('processoItem', {})
    processo_completo = res.get('processoCompleto', {})
    tarefas = res.get('tarefas', [])
    calculos = res.get('calculos', [])

    logger.info(f"[API] ✅ Sucesso")
    logger.info(f"[API] ID: {processo_item.get('id', '?')}, Número: {processo_item.get('numero', processo_item.get('numeroProcesso', '?'))}")
    logger.info(f"[API] Dados completos: {len(str(processo_completo))} chars")
    logger.info(f"[API] Tarefas: {len(tarefas)}, Cálculos: {len(calculos)}")

    return {
        'id': id_processo,
        'processoItem': processo_item,
        'processoCompleto': processo_completo,
        'tarefas': tarefas,
        'calculos': calculos
    }

def main():
    # O ID do processo é 8025011 e o número correspondente precisa ser determinado
    id_processo = '8025011'
    numero_processo = ''  # O número será obtido dos dados do processo

    print(f"\n[API] Iniciando busca completa do processo ID: {id_processo}...")

    # Cria driver headless
    drv = driver_pc(headless=True)
    if not drv:
        logger.error("[API] Falha ao criar driver")
        return

    print(f"[API] Driver headless criado, aguardando login...")
    ok = login_cpf(drv)
    if not ok:
        logger.error("[API] Login falhou")
        try: drv.quit()
        except: pass
        return

    print(f"[API] Login OK, buscando dados completos...")
    time.sleep(2)

    # Busca dados completos - usando o ID diretamente
    resultado = fetch_processo_completo(drv, id_processo)
    
    if resultado:
        # Salva em JSON
        arquivo_saida = f'0probe.json'
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Dados salvos em: {arquivo_saida}")

        item = resultado.get('processoItem', {})
        completo = resultado.get('processoCompleto', {})

        if item:
            print(f"\nProcesso Item:")
            print(f"  ID: {item.get('id', '?')}")
            print(f"  Número: {item.get('numero', item.get('numeroProcesso', '?'))}")
            print(f"  Chaves: {list(item.keys())}")

        if completo:
            print(f"\nProcesso Completo:")
            print(f"  ID: {completo.get('id', completo.get('idProcesso', '?'))}")
            print(f"  Número: {completo.get('numero', completo.get('numeroProcesso', '?'))}")
            print(f"  Chaves: {list(completo.keys())[:15]}")

        if resultado.get('tarefas'):
            print(f"\nTarefas: {len(resultado['tarefas'])} tarefas")
            for tarefa in resultado['tarefas'][:3]:
                print(f"  - {tarefa.get('nome', tarefa.get('descricao', '?'))}")

        if resultado.get('calculos'):
            print(f"\nCálculos: {len(resultado['calculos'])} cálculos")
    else:
        print(f"\n❌ Falha ao obter dados")

    try:
        drv.quit()
    except:
        pass

if __name__ == '__main__':
    main()
