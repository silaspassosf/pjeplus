// Limpa abas de REVIEW da sidebar direita, preservando as abas de ARQUIVO.
//
// O layout da sidebar fica no localStorage do navegador (nao em disco), chave
// `dsh.sidebar-right.v1.<sessionId>`. Cada aba salva tem {kind, contentId}:
//   - review  -> kind 'changes-review', contentId 'dsh-resource://changes-review/...'
//   - arquivo -> kind 'text'/'files'/..., contentId 'dsh-resource://file/...'
// Este script remove APENAS as de review e apaga um painel que fique vazio;
// as abas de arquivo continuam onde estavam.
//
// Uso: abra o DSH, aperte F12 -> Console, cole tudo e pressione Enter.
// Depois recarregue a pagina com Ctrl+Shift+R.

(function limparAbasReview() {
  const PREFIXO = 'dsh.sidebar-right.v1.';
  const KIND_REVIEW = 'changes-review';
  const URL_REVIEW = 'dsh-resource://changes-review/';

  function ehReview(tab) {
    if (!tab) return false;
    if (tab.kind === KIND_REVIEW) return true;
    return typeof tab.contentId === 'string' && tab.contentId.startsWith(URL_REVIEW);
  }

  const chaves = Object.keys(localStorage).filter(k => k.startsWith(PREFIXO));
  if (!chaves.length) {
    console.log('[limpar-review] nenhum layout salvo encontrado.');
    return;
  }

  let totalRemovidas = 0;
  let totalSessoes = 0;

  for (const chave of chaves) {
    let dados;
    try {
      dados = JSON.parse(localStorage.getItem(chave));
    } catch (e) {
      console.warn('[limpar-review] ignorado (JSON invalido):', chave);
      continue;
    }

    // envelope: { layout: { nodes:{}, tabs:{}, ... }, minted }
    const layout = dados && dados.layout;
    if (!layout || !layout.tabs || !layout.nodes) continue;

    const remover = new Set(
      Object.entries(layout.tabs).filter(([, tab]) => ehReview(tab)).map(([id]) => id)
    );
    if (!remover.size) continue;

    // 1) tira das listas de abas dos paineis
    for (const node of Object.values(layout.nodes)) {
      if (!node || node.kind !== 'pane' || !Array.isArray(node.tabs)) continue;
      node.tabs = node.tabs.filter(id => !remover.has(id));
      if (node.activeTabId && remover.has(node.activeTabId)) {
        node.activeTabId = node.tabs.length ? node.tabs[node.tabs.length - 1] : undefined;
      }
      if (!node.tabs.length) delete node.activeTabId;
    }

    // 2) apaga os registros das abas removidas
    for (const id of remover) delete layout.tabs[id];

    // 3) painel que ficou sem aba NAO pode ser removido: um split aponta para
    //    ele por id, e apagar deixaria o layout inconsistente (o que descarta a
    //    sessao inteira no proximo load). O painel continua existindo e vazio;
    //    a propria UI trata painel vazio recebendo a pagina padrao do guide.
    //    Fluxo float e' excecao: float exige exatamente 1 aba, entao sai.
    const raiz = layout.rootId;
    for (const [id, node] of Object.entries(layout.nodes)) {
      if (!node || node.kind !== 'pane') continue;
      if (id === raiz) continue;
      if (Array.isArray(node.tabs) && node.tabs.length === 0) {
        if (node.host === 'float') {
          delete layout.nodes[id];
          if (Array.isArray(layout.floats)) layout.floats = layout.floats.filter(f => f !== id);
        }
      }
    }

    // 4) a raiz pode ser um PAINEL (dock simples) ou um SPLIT (dividido).
    //    Checar "eh pane" aqui rejeitava qualquer layout dividido e apagava a
    //    sessao inteira. O que importa e' o no existir.
    const ehNoExistente = id => layout.nodes[id] !== undefined;
    const ehPaneValido = id => layout.nodes[id] && layout.nodes[id].kind === 'pane';
    if (!ehNoExistente(raiz)) {
      console.warn('[limpar-review] layout sem raiz valida, removendo a sessao:', chave);
      localStorage.removeItem(chave);
      totalSessoes++;
      continue;
    }

    // 4b) um split precisa de >= 2 filhos existentes; se sobrou menos, a raiz
    //     vira o unico painel restante para o layout continuar valido.
    const nos = layout.nodes;
    const filhosVivos = id => {
      const n = nos[id];
      if (!n || n.kind !== 'split') return null;
      return n.children.filter(c => nos[c] !== undefined);
    };
    let raizFinal = raiz;
    if (nos[raiz] && nos[raiz].kind === 'split') {
      const vivos = filhosVivos(raiz);
      if (vivos && vivos.length === 1) {
        raizFinal = vivos[0];
        layout.rootId = raizFinal;
      } else if (vivos && vivos.length === 0) {
        console.warn('[limpar-review] split sem filhos, removendo a sessao:', chave);
        localStorage.removeItem(chave);
        totalSessoes++;
        continue;
      }
    }

    // 5) floats apontando para paineis inexistentes
    if (Array.isArray(layout.floats)) {
      layout.floats = layout.floats.filter(id => ehPaneValido(id));
    }
    if (!layout.activePaneId || !ehPaneValido(layout.activePaneId)) {
      layout.activePaneId = raizFinal;
      if (!ehPaneValido(layout.activePaneId)) {
        const primeiroPane = Object.keys(nos).find(id => ehPaneValido(id));
        if (primeiroPane) layout.activePaneId = primeiroPane;
      }
    }

    localStorage.setItem(chave, JSON.stringify(dados));
    totalRemovidas += remover.size;
    totalSessoes++;
    console.log(`[limpar-review] ${chave.replace(PREFIXO, 'sessao ')}: ${remover.size} aba(s) de review removida(s)`);
  }

  if (totalRemovidas) {
    console.log(`[limpar-review] pronto: ${totalRemovidas} aba(s) em ${totalSessoes} sessao(oes). Recarregue com Ctrl+Shift+R.`);
  } else {
    console.log('[limpar-review] nenhuma aba de review encontrada.');
  }
})();
