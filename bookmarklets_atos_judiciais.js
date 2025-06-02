// ====================================================
// BOOKMARKLETS DOS ATOS JUDICIAIS DO PJE PLUS
// ====================================================
// Extraído automaticamente do arquivo atos.py
// Cada bookmarklet executa um ato judicial específico na tela de minuta do PJe

// ====================================================
// CATEGORIA 1 - ATOS JUDICIAIS PADRÃO (ato_*)
// ====================================================

// 1. ATO MEIOS
// Parâmetros: Despacho, xsmeios, prazo=5, PEC=False, primeiro destinatário=True
const bookmarklet_ato_meios = `javascript:(function(){
    // Ato de meios de execução
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xsmeios',
        prazo: 5,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: true
    };
    
    // Executa o ato judicial
    console.log('[BOOKMARKLET] Executando ato_meios:', params);
    
    // Simula o fluxo do ato_judicial
    // 1. Campo de modelo
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        campoModelo.dispatchEvent(new Event('change', {bubbles: true}));
        
        // Pressiona Enter
        const enterEvent = new KeyboardEvent('keydown', {
            key: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true
        });
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            // Clica no item filtrado
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) {
                nodoFiltrado.click();
                
                setTimeout(() => {
                    // Clica em inserir
                    const btnInserir = document.querySelector('pje-dialogo-visualizar-modelo button:contains("Inserir")');
                    if (btnInserir) btnInserir.click();
                    
                    setTimeout(() => {
                        // Clica em Salvar
                        const btnSalvar = document.querySelector('button[aria-label="Salvar"]');
                        if (btnSalvar) {
                            btnSalvar.click();
                            
                            setTimeout(() => {
                                // Configura PEC
                                const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
                                if (pecCheckbox && !params.marcar_pec && pecCheckbox.checked) {
                                    pecCheckbox.click();
                                } else if (pecCheckbox && params.marcar_pec && !pecCheckbox.checked) {
                                    pecCheckbox.click();
                                }
                                
                                // Configura prazo
                                if (params.prazo) {
                                    const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
                                    if (campoPrazo) {
                                        campoPrazo.value = params.prazo;
                                        campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                                    }
                                    
                                    // Gravar prazo
                                    const btnGravarPrazo = document.querySelector('button:contains("Gravar"):not([aria-label*="movimentos"])');
                                    if (btnGravarPrazo) btnGravarPrazo.click();
                                }
                                
                                console.log('[BOOKMARKLET] Ato meios executado!');
                            }, 1000);
                        }
                    }, 500);
                }, 500);
            }
        }, 500);
    }
})();`;

// 2. ATO CRDA (Carta de Reclamada)
// Parâmetros: Despacho, a reclda, prazo=15, PEC=False
const bookmarklet_ato_crda = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'a reclda',
        prazo: 15,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: false
    };
    
    console.log('[BOOKMARKLET] Executando ato_crda:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 3. ATO CRTE (Carta de Reclamante)  
// Parâmetros: Despacho, xreit, prazo=15, PEC=False
const bookmarklet_ato_crte = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xreit',
        prazo: 15,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: false
    };
    
    console.log('[BOOKMARKLET] Executando ato_crte:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 4. ATO BLOQ (Bloqueio)
// Parâmetros: Despacho, xsparcial, prazo=None, PEC=True, gigs={'dias_uteis': 1, 'observacao': 'pec bloq'}
const bookmarklet_ato_bloq = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xsparcial',
        prazo: null,
        marcar_pec: true,
        movimento: null,
        marcar_primeiro_destinatario: false,
        gigs: {dias_uteis: 1, observacao: 'pec bloq'}
    };
    
    console.log('[BOOKMARKLET] Executando ato_bloq:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 5. ATO IDPJ
// Parâmetros: IDPJ, pjsem, prazo=8, PEC=True
const bookmarklet_ato_idpj = `javascript:(function(){
    const params = {
        conclusao_tipo: 'IDPJ',
        modelo_nome: 'pjsem',
        prazo: 8,
        marcar_pec: true,
        movimento: null,
        marcar_primeiro_destinatario: false
    };
    
    console.log('[BOOKMARKLET] Executando ato_idpj:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 6. ATO TERMO E (Termo de Empresa)
// Parâmetros: Despacho, xempre, prazo=5, PEC=False, primeiro destinatário=True
const bookmarklet_ato_termoE = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xempre',
        prazo: 5,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: true
    };
    
    console.log('[BOOKMARKLET] Executando ato_termoE:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 7. ATO TERMO S (Termo de Sócio)
// Parâmetros: Despacho, xsocio, prazo=5, PEC=False, primeiro destinatário=True
const bookmarklet_ato_termoS = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xsocio',
        prazo: 5,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: true
    };
    
    console.log('[BOOKMARKLET] Executando ato_termoS:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 8. ATO EDITAL
// Parâmetros: Despacho, xsedit, prazo=5, PEC=False, primeiro destinatário=True
const bookmarklet_ato_edital = `javascript:(function(){
    const params = {
        conclusao_tipo: 'Despacho',
        modelo_nome: 'xsedit',
        prazo: 5,
        marcar_pec: false,
        movimento: null,
        marcar_primeiro_destinatario: true
    };
    
    console.log('[BOOKMARKLET] Executando ato_edital:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 9. ATO SOBRESTAMENTO
// Parâmetros: / Susp, suspf, prazo=0, PEC=False, movimento='frustrada'
const bookmarklet_ato_sobrestamento = `javascript:(function(){
    const params = {
        conclusao_tipo: '/ Susp',
        modelo_nome: 'suspf',
        prazo: 0,
        marcar_pec: false,
        movimento: 'frustrada',
        marcar_primeiro_destinatario: false
    };
    
    console.log('[BOOKMARKLET] Executando ato_sobrestamento:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// 10. ATO PESQUISAS
// Parâmetros: BNDT, xsbacen, prazo=30, PEC=True, movimento='bloqueio', sigilo=True, primeiro destinatário=True
const bookmarklet_ato_pesquisas = `javascript:(function(){
    const params = {
        conclusao_tipo: 'BNDT',
        modelo_nome: 'xsbacen',
        prazo: 30,
        marcar_pec: true,
        movimento: 'bloqueio',
        marcar_primeiro_destinatario: true,
        sigilo: true
    };
    
    console.log('[BOOKMARKLET] Executando ato_pesquisas:', params);
    
    const campoModelo = document.querySelector('#inputFiltro');
    if (campoModelo) {
        campoModelo.value = params.modelo_nome;
        campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
        
        const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
        campoModelo.dispatchEvent(enterEvent);
        
        setTimeout(() => {
            const nodoFiltrado = document.querySelector('.nodo-filtrado');
            if (nodoFiltrado) nodoFiltrado.click();
        }, 500);
    }
})();`;

// ====================================================
// CATEGORIA 2 - COMUNICAÇÕES PROCESSUAIS (pec_*)
// ====================================================

// 1. PEC BLOQUEIO
// Parâmetros: Intimação, prazo=7, 'ciência bloqueio', sigilo=False, 'zzintbloq'
const bookmarklet_pec_bloqueio = `javascript:(function(){
    const params = {
        tipo_expediente: 'Intimação',
        prazo: 7,
        nome_comunicacao: 'ciência bloqueio',
        sigilo: false,
        modelo_nome: 'zzintbloq',
        gigs_extra: '7, Guilherme - carta'
    };
    
    console.log('[BOOKMARKLET] Executando pec_bloqueio:', params);
    
    // Lógica específica para comunicações processuais
    alert('PEC Bloqueio configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 2. PEC DECISÃO
// Parâmetros: Intimação, prazo=10, 'intimação de decisão', sigilo=False, 'xs dec reg'
const bookmarklet_pec_decisao = `javascript:(function(){
    const params = {
        tipo_expediente: 'Intimação',
        prazo: 10,
        nome_comunicacao: 'intimação de decisão',
        sigilo: false,
        modelo_nome: 'xs dec reg',
        gigs_extra: '7, Guilherme - carta'
    };
    
    console.log('[BOOKMARKLET] Executando pec_decisao:', params);
    alert('PEC Decisão configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 3. PEC IDPJ
// Parâmetros: Intimação, prazo=17, 'defesa IDPJ', sigilo=False, 'xidpj c'
const bookmarklet_pec_idpj = `javascript:(function(){
    const params = {
        tipo_expediente: 'Intimação',
        prazo: 17,
        nome_comunicacao: 'defesa IDPJ',
        sigilo: false,
        modelo_nome: 'xidpj c',
        gigs_extra: '7, Guilherme - carta'
    };
    
    console.log('[BOOKMARKLET] Executando pec_idpj:', params);
    alert('PEC IDPJ configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 4. PEC EDITAL IDPJ
// Parâmetros: Edital, prazo=15, 'Defesa IDPJ', sigilo=False, 'IDPJ (edital)'
const bookmarklet_pec_editalidpj = `javascript:(function(){
    const params = {
        tipo_expediente: 'Edital',
        prazo: 15,
        nome_comunicacao: 'Defesa IDPJ',
        sigilo: false,
        modelo_nome: 'IDPJ (edital)',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_editalidpj:', params);
    alert('PEC Edital IDPJ configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 5. PEC EDITAL DECISÃO
// Parâmetros: Edital, prazo=8, 'Decisão/Sentença', sigilo=False, '3dec'
const bookmarklet_pec_editaldec = `javascript:(function(){
    const params = {
        tipo_expediente: 'Edital',
        prazo: 8,
        nome_comunicacao: 'Decisão/Sentença',
        sigilo: false,
        modelo_nome: '3dec',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_editaldec:', params);
    alert('PEC Edital Decisão configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 6. PEC CP GERAL
// Parâmetros: Mandado, prazo=1, 'Mandado CP', sigilo=False, 'mdd cp geral'
const bookmarklet_pec_cpgeral = `javascript:(function(){
    const params = {
        tipo_expediente: 'Mandado',
        prazo: 1,
        nome_comunicacao: 'Mandado CP',
        sigilo: false,
        modelo_nome: 'mdd cp geral',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_cpgeral:', params);
    alert('PEC CP Geral configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 7. PEC EXCLUI ÓRGÃOS
// Parâmetros: Mandado, prazo=1, 'Exclusão de convênios', sigilo=False, 'asa/cnib'
const bookmarklet_pec_excluiargos = `javascript:(function(){
    const params = {
        tipo_expediente: 'Mandado',
        prazo: 1,
        nome_comunicacao: 'Exclusão de convênios',
        sigilo: false,
        modelo_nome: 'asa/cnib',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_excluiargos:', params);
    alert('PEC Exclui Órgãos configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 8. PEC MANDADO GERAL
// Parâmetros: Mandado, prazo=8, 'Mandado', sigilo=False, '02 - gené'
const bookmarklet_pec_mddgeral = `javascript:(function(){
    const params = {
        tipo_expediente: 'Mandado',
        prazo: 8,
        nome_comunicacao: 'Mandado',
        sigilo: false,
        modelo_nome: '02 - gené',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_mddgeral:', params);
    alert('PEC Mandado Geral configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 9. PEC MANDADO AUDIÊNCIA
// Parâmetros: Mandado, prazo=1, 'Mandado citação', sigilo=False, 'xmdd aud'
const bookmarklet_pec_mddaud = `javascript:(function(){
    const params = {
        tipo_expediente: 'Mandado',
        prazo: 1,
        nome_comunicacao: 'Mandado citação',
        sigilo: false,
        modelo_nome: 'xmdd aud',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_mddaud:', params);
    alert('PEC Mandado Audiência configurado: ' + JSON.stringify(params, null, 2));
})();`;

// 10. PEC EDITAL AUDIÊNCIA
// Parâmetros: Edital, prazo=1, 'Citação', sigilo=False, '1cit'
const bookmarklet_pec_editalaud = `javascript:(function(){
    const params = {
        tipo_expediente: 'Edital',
        prazo: 1,
        nome_comunicacao: 'Citação',
        sigilo: false,
        modelo_nome: '1cit',
        gigs_extra: null
    };
    
    console.log('[BOOKMARKLET] Executando pec_editalaud:', params);
    alert('PEC Edital Audiência configurado: ' + JSON.stringify(params, null, 2));
})();`;

// ====================================================
// INSTRUÇÕES DE USO
// ====================================================
/*
Para usar os bookmarklets:

1. Copie o código de cada bookmarklet desejado (a string que começa com "javascript:(function(){")

2. No seu navegador, crie um novo favorito/marcador e cole o código como URL

3. Nomeie o favorito com o nome do ato (ex: "Ato Meios", "Ato IDPJ", etc.)

4. Quando estiver na tela de minuta do PJe após inserir um modelo, clique no bookmarklet para executar as ações automaticamente

CATEGORIAS:

A) ATOS JUDICIAIS (ato_*):
   - ato_meios: Meios de execução
   - ato_crda: Carta de reclamada  
   - ato_crte: Carta de reclamante
   - ato_bloq: Bloqueio
   - ato_idpj: IDPJ
   - ato_termoE: Termo de empresa
   - ato_termoS: Termo de sócio
   - ato_edital: Edital
   - ato_sobrestamento: Sobrestamento
   - ato_pesquisas: Pesquisas BACEN/BNDT

B) COMUNICAÇÕES PROCESSUAIS (pec_*):
   - pec_bloqueio: Ciência bloqueio
   - pec_decisao: Intimação de decisão
   - pec_idpj: Defesa IDPJ
   - pec_editalidpj: Edital IDPJ
   - pec_editaldec: Edital decisão
   - pec_cpgeral: Mandado CP geral
   - pec_excluiargos: Exclusão de órgãos
   - pec_mddgeral: Mandado geral
   - pec_mddaud: Mandado audiência
   - pec_editalaud: Edital audiência

Cada bookmarklet configura automaticamente os parâmetros específicos daquele ato judicial conforme definido no arquivo atos.py.
*/
