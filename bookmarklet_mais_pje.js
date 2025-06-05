// Bookmarklet para caixa flutuante dinâmica de grupos e botões do MaisPJe
(function(){
  // Primeiro, carregar o automacao.js se não estiver carregado
  if (!window.executarFluxoMaisPje) {
    var script = document.createElement('script');
    script.src = 'file:///c:/Users/s164283/Desktop/pjeplus/automacao.js';
    script.onerror = function() {
      // Se falhar carregar do arquivo, tentar do GitHub ou usar código inline
      console.log('[MAISPJE] Erro ao carregar automacao.js do arquivo local');
      alert('Erro: automacao.js não carregado. Verifique se o arquivo existe em: c:/Users/s164283/Desktop/pjeplus/automacao.js');
    };
    document.head.appendChild(script);
    
    // Aguardar carregamento
    setTimeout(function() {
      if (!window.executarFluxoMaisPje) {
        alert('Erro: automacao.js não foi carregado corretamente');
        return;
      }
    }, 1000);
  }  // Dados dos botões extraídos de botoes_maispje.json com mapeamento completo
  var botoesCompletos = {
    'aaDespacho': [
      {nm_botao:'Genérico', tipo:'Despacho', descricao:'Despacho', sigilo:'não', modelo:'xsgen', juiz:'', responsavel:'', assinar:'não', cor:'#0080ff', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Meios', tipo:'Despacho', descricao:'Indicação de meios', sigilo:'nao', modelo:'xsmeios', juiz:'', responsavel:'', assinar:'nao', cor:'#008000', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'EmpreTermo', tipo:'Despacho', descricao:'Indicar meios', sigilo:'nao', modelo:'xempresatermo', juiz:'', responsavel:'', assinar:'sim', cor:'#ff8040', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'SócioTermo', tipo:'Despacho', descricao:'Indicar meios', sigilo:'nao', modelo:'xsociotermo', juiz:'', responsavel:'', assinar:'sim', cor:'#ff8040', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Homol', tipo:'Homologação de C', descricao:'Homologação de Cálculos', sigilo:'nao', modelo:'homol. cálculos', juiz:'', responsavel:'', assinar:'nao', cor:'#228b22', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Parcial', tipo:'Despacho', descricao:'Despacho', sigilo:'não', modelo:'XSPARCIAL', juiz:'', responsavel:'', assinar:'não', cor:'#ff8040', vinculo:'AutoGigs|pecG,Nenhum', visibilidade:'sim'},
      {nm_botao:'Rosto sob', tipo:'Sobrest', descricao:'', sigilo:'nao', modelo:'x180', juiz:'', responsavel:'', assinar:'nao', cor:'#8080ff', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'SuspPROV', tipo:'Sobrestamento /', descricao:'Sobrestamento', sigilo:'não', modelo:'xsuspPROV', juiz:'', responsavel:'', assinar:'não', cor:'#ff8040', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Meios P/Exec', tipo:'Homologação de C', descricao:'indcar meios - mudança para exec', sigilo:'nao', modelo:'xsmeios', juiz:'', responsavel:'', assinar:'nao', cor:'#228b22', vinculo:'AutoGigs|mover exec,Nenhum', visibilidade:'sim'},
      {nm_botao:'Pesq P/Exec', tipo:'Homologação de C', descricao:'PESQUISAS - mudança para exec', sigilo:'nao', modelo:'xsmeios', juiz:'', responsavel:'', assinar:'nao', cor:'#ff8040', vinculo:'AutoGigs|Pesq,Nenhum', visibilidade:'sim'},
      {nm_botao:'UnaP', tipo:'Despacho', descricao:'', sigilo:'nao', modelo:'-Aud una presen', juiz:'', responsavel:'', assinar:'sim', cor:'#0080ff', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'UnaP100%', tipo:'Despacho', descricao:'', sigilo:'nao', modelo:'al 100', juiz:'', responsavel:'', assinar:'sim', cor:'#800000', vinculo:'AutoGigs|citar,Nenhum', visibilidade:'sim'},
      {nm_botao:'SuspSEM', tipo:'Sobrestamento', descricao:'Sobrestamento', sigilo:'não', modelo:'suspf', juiz:'', responsavel:'', assinar:'não', cor:'#c0c0c0', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'IDPJ', tipo:'IDPJ', descricao:'Julgamento IDPJ', sigilo:'não', modelo:'IDPJsemdef', juiz:'', responsavel:'', assinar:'não', cor:'#0080ff', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Edital', tipo:'Despacho', descricao:'Determina Edital', sigilo:'não', modelo:'xsedit', juiz:'', responsavel:'', assinar:'não', cor:'#0000a0', vinculo:'AutoGigs|pecG,Nenhum', visibilidade:'sim'},
      {nm_botao:'CUMPRIR CP', tipo:'Despacho', descricao:'CUMPRIR CP', sigilo:'nao', modelo:'. depre', juiz:'', responsavel:'', assinar:'sim', cor:'#0080ff', vinculo:'AutoGigs|pec,Nenhum', visibilidade:'sim'},
      {nm_botao:'CALCrcte', tipo:'Despacho', descricao:'Reitera Calc Rcte', sigilo:'nao', modelo:'xreiteracalcrcte', juiz:'', responsavel:'', assinar:'sim', cor:'#008080', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'CALCrcda', tipo:'Despacho', descricao:'Intima Rcda Calc', sigilo:'nao', modelo:'a reclda', juiz:'', responsavel:'', assinar:'sim', cor:'#008080', vinculo:'Nenhum', visibilidade:'sim'},
      {nm_botao:'Parcela', tipo:'Despacho', descricao:'Despacho', sigilo:'nao', modelo:'xsparcela', juiz:'', responsavel:'', assinar:'nao', cor:'#ff8000', vinculo:'Nenhum', visibilidade:'sim'}
    ],
    'aaAutogigs': [
      {nm_botao:'Pesq', tipo:'prazo', tipo_atividade:'Pesquisas Patrimoniais', responsavel:'', observacao:'Aguardar pesquisas', prazo:'30', salvar:'sim', cor:'#008000', vinculo:'Nenhum'},
      {nm_botao:'IDPJ', tipo:'prazo', tipo_atividade:'IDPJ', responsavel:'', observacao:'Aguardar IDPJ', prazo:'15', salvar:'sim', cor:'#ff8040', vinculo:'Nenhum'},
      {nm_botao:'Lib', tipo:'prazo', tipo_atividade:'Liberação', responsavel:'', observacao:'Processo liberado', prazo:'0', salvar:'sim', cor:'#708090', vinculo:'Nenhum'},
      {nm_botao:'Homol', tipo:'prazo', tipo_atividade:'Homologação', responsavel:'', observacao:'Homologação de cálculos', prazo:'15', salvar:'sim', cor:'#008040', vinculo:'Nenhum'},
      {nm_botao:'pec', tipo:'comentario', observacao:'PEC processada', prazo:'Magistrado', salvar:'sim', cor:'#ff0000', vinculo:'Nenhum'},
      {nm_botao:'pecG', tipo:'comentario', observacao:'PEC processada - Gabinete', prazo:'Gabinete', salvar:'sim', cor:'#ff0000', vinculo:'Nenhum'},
      {nm_botao:'recado', tipo:'lembrete', tipo_atividade:'Recado', observacao:'Lembrete importante', prazo:'7', salvar:'sim', cor:'#ff0000', vinculo:'Nenhum'},
      {nm_botao:'arq1', tipo:'prazo', tipo_atividade:'Arquivo', responsavel:'', observacao:'Processo arquivado', prazo:'0', salvar:'sim', cor:'#804040', vinculo:'Nenhum'},
      {nm_botao:'Lib Silvia', tipo:'prazo', tipo_atividade:'Liberação', responsavel:'Silvia', observacao:'Processo liberado para Silvia', prazo:'0', salvar:'sim', cor:'#008040', vinculo:'Nenhum'},
      {nm_botao:'CalcArgos', tipo:'prazo', tipo_atividade:'Cálculos', responsavel:'', observacao:'Cálculo de Argos', prazo:'30', salvar:'sim', cor:'#ff8000', vinculo:'Nenhum'},
      {nm_botao:'ConfG', tipo:'comentario', observacao:'Confirmação do Gabinete', prazo:'Gabinete', salvar:'sim', cor:'#800040', vinculo:'Nenhum'},
      {nm_botao:'CartaG', tipo:'prazo', tipo_atividade:'Carta Precatória', responsavel:'', observacao:'Carta Precatória - Gabinete', prazo:'60', salvar:'sim', cor:'#008080', vinculo:'Nenhum'},
      {nm_botao:'Lib0', tipo:'prazo', tipo_atividade:'Liberação', responsavel:'', observacao:'Liberação imediata', prazo:'0', salvar:'sim', cor:'#c0c0c0', vinculo:'Nenhum'}
    ],
    'aaAnexar': [
      {nm_botao:'CP', tipo:'Carta Precatória', descricao:'Carta Precatória', sigilo:'nao', modelo:'carta precatoria', assinar:'nao', cor:'#c0c0c0'},
      {nm_botao:'DEVCP', tipo:'Certidão', descricao:'Devolução de CP', sigilo:'nao', modelo:'devolucao cp', assinar:'nao', cor:'#0080ff'},
      {nm_botao:'Parcial+Desp', tipo:'Despacho', descricao:'Parcial + Despacho', sigilo:'nao', modelo:'parcial despacho', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'SBJNEG', tipo:'Certidão', descricao:'SBJ Negativo', sigilo:'nao', modelo:'sbj negativo', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'transf pedida', tipo:'Certidão', descricao:'Transferência Pedida', sigilo:'nao', modelo:'transferencia', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'Carta', tipo:'Carta', descricao:'Carta', sigilo:'nao', modelo:'carta', assinar:'nao', cor:'#008080'},
      {nm_botao:'PDF TRANSF', tipo:'PDF', descricao:'PDF Transferência', sigilo:'nao', modelo:'pdf', assinar:'nao', cor:'#1fe059'},
      {nm_botao:'OficMalote', tipo:'Ofício', descricao:'Ofício Malote', sigilo:'nao', modelo:'oficio malote', assinar:'nao', cor:'#c0c0c0'},
      {nm_botao:'Recibo PDF', tipo:'PDF', descricao:'Recibo PDF', sigilo:'nao', modelo:'pdf', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'Calc', tipo:'Cálculo', descricao:'Cálculo', sigilo:'nao', modelo:'calculo', assinar:'nao', cor:'#008000'},
      {nm_botao:'Extrato', tipo:'Extrato', descricao:'Extrato', sigilo:'nao', modelo:'extrato', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'ARISP', tipo:'Certidão', descricao:'ARISP', sigilo:'nao', modelo:'arisp', assinar:'nao', cor:'#c0c0c0'},
      {nm_botao:'Arq', tipo:'Arquivo', descricao:'Arquivo', sigilo:'nao', modelo:'arquivo', assinar:'nao', cor:'#0080c0'},
      {nm_botao:'Teimosinha consulta', tipo:'Certidão', descricao:'Consulta Teimosinha', sigilo:'nao', modelo:'teimosinha', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'t2', tipo:'Certidão', descricao:'T2', sigilo:'nao', modelo:'t2', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'GENÉRICA', tipo:'Certidão', descricao:'Certidão Genérica', sigilo:'nao', modelo:'generica', assinar:'nao', cor:'#c0c0c0'},
      {nm_botao:'Infojud', tipo:'Certidão', descricao:'Infojud', sigilo:'sim', modelo:'infojud', assinar:'nao', cor:'#ff0000'},
      {nm_botao:'juntadaPROV', tipo:'Juntada', descricao:'Juntada Provisória', sigilo:'nao', modelo:'juntada prov', assinar:'nao', cor:'#ff8040'},
      {nm_botao:'Provdocs', tipo:'Juntada', descricao:'Documentos Provisórios', sigilo:'nao', modelo:'prov docs', assinar:'nao', cor:'#ff8040'},
      {nm_botao:'EMAIL', tipo:'E-mail', descricao:'E-mail', sigilo:'nao', modelo:'email', assinar:'nao', cor:'#c0c0c0'},
      {nm_botao:'Transf+Lib', tipo:'Certidão', descricao:'Transferência + Liberação', sigilo:'nao', modelo:'transf lib', assinar:'nao', cor:'#ff8000'},
      {nm_botao:'Reg$', tipo:'Registro', descricao:'Registro Financeiro', sigilo:'nao', modelo:'reg financeiro', assinar:'nao', cor:'#ff80c0'}
    ]
  };

  // Remove caixa anterior, se existir
  var old = document.getElementById('maisPjeBox');
  if(old) old.remove();

  // Cria caixa flutuante
  var box = document.createElement('div');
  box.id = 'maisPjeBox';
  box.style.position = 'fixed';
  box.style.top = '30px';
  box.style.right = '30px';
  box.style.zIndex = 99999;
  box.style.background = '#fff';
  box.style.border = '2px solid #0080ff';
  box.style.borderRadius = '10px';
  box.style.boxShadow = '0 2px 10px #0003';
  box.style.padding = '16px 12px 12px 12px';
  box.style.minWidth = '220px';
  box.style.fontFamily = 'sans-serif';
  box.style.maxHeight = '80vh';
  box.style.overflowY = 'auto';
  box.style.transition = 'all 0.2s';

  // Título
  var titulo = document.createElement('div');
  titulo.textContent = 'MaisPJe';
  titulo.style.fontWeight = 'bold';
  titulo.style.fontSize = '16px';
  titulo.style.marginBottom = '10px';
  box.appendChild(titulo);

  // Área dos botões
  var botoesArea = document.createElement('div');
  box.appendChild(botoesArea);

  // Botão voltar
  var voltar = document.createElement('button');
  voltar.textContent = '← Voltar';
  voltar.style.display = 'none';
  voltar.style.marginBottom = '8px';
  voltar.style.background = '#eee';
  voltar.style.color = '#0080ff';
  voltar.style.border = 'none';
  voltar.style.borderRadius = '6px';
  voltar.style.padding = '6px 10px';
  voltar.style.fontWeight = 'bold';
  voltar.style.cursor = 'pointer';
  voltar.onclick = function(){ exibirGrupos(); };
  box.appendChild(voltar);

  // Botão fechar
  var fechar = document.createElement('span');
  fechar.textContent = '×';
  fechar.title = 'Fechar';
  fechar.style.position = 'absolute';
  fechar.style.top = '6px';
  fechar.style.right = '10px';
  fechar.style.cursor = 'pointer';
  fechar.style.fontSize = '18px';
  fechar.style.color = '#0080ff';
  fechar.onclick = function(){ box.remove(); };
  box.appendChild(fechar);

  document.body.appendChild(box);

  // Função para exibir os grupos principais
  function exibirGrupos() {
    botoesArea.innerHTML = '';
    voltar.style.display = 'none';
    grupos.forEach(function(g) {
      var b = document.createElement('button');
      b.textContent = g.nome;
      b.style.background = '#0080ff';
      b.style.color = '#fff';
      b.style.border = 'none';
      b.style.borderRadius = '6px';
      b.style.padding = '10px 18px';
      b.style.margin = '6px 0';
      b.style.fontSize = '16px';
      b.style.cursor = 'pointer';
      b.style.width = '100%';
      b.onclick = function(){ exibirBotoesGrupo(g); };
      botoesArea.appendChild(b);
    });
  }

  // Função para exibir os botões de um grupo
  function exibirBotoesGrupo(grupo) {
    botoesArea.innerHTML = '';
    voltar.style.display = '';
    var lista = botoesPorGrupo[grupo.chave] || [];
    lista.forEach(function(btn) {
      var b = document.createElement('button');
      b.textContent = btn.nome;
      b.style.background = btn.cor || '#0080ff';
      b.style.color = '#fff';
      b.style.border = 'none';
      b.style.borderRadius = '6px';
      b.style.padding = '8px 14px';
      b.style.margin = '4px 0';
      b.style.fontSize = '15px';
      b.style.cursor = 'pointer';
      b.style.width = '100%';
      b.onclick = function(){
        var funcName = 'fluxo_' + btn.nome.replace(/[^a-zA-Z0-9_]/g,'_');
        if(typeof window[funcName]==='function') window[funcName]();
        else alert('Executar: '+funcName+'()');
      };
      botoesArea.appendChild(b);
    });
  }

  // Inicializa com os grupos principais
  exibirGrupos();
})();
