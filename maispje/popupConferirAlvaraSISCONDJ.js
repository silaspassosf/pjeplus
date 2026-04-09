let urlSiscondj;

async function iniciar() {
    browser.storage.local.get(['tempAR','configURLs'], async function(result){
        document.querySelector('.titulo').innerText = 'Relatório de Alvarás SISCONDJ - Total: ' + result.tempAR.length;
        document.querySelector('.subtitulo').innerText = 'Gerado em: ' + agora();
        urlSiscondj = getUrlBaseSiscondj(result.configURLs.urlSiscondj);        
        await createTable(result.tempAR);
        await sleep(1000);        
        browser.runtime.sendMessage({tipo: 'storage_limpar', valor: 'tempAR'});
    });	
}

iniciar();

async function createTable(children) {
    console.log(children);
    console.log('criando a tabela - cabeçalho')
    let tabela = document.createElement('table');
    
    //cria o cabeçalho
    let cabecalho = document.createElement('thead');
    cabecalho.appendChild(inserirLinha("th",'BANCO/DATA/EMISSOR',"width: auto;"));
    cabecalho.appendChild(inserirLinha("th",'BENEFICIÁRIO',"width: auto;"));
    cabecalho.appendChild(inserirLinha("th",'TIPO',"width: auto;"));
    cabecalho.appendChild(inserirLinha("th",'VALOR',"width: auto;"));
   

    let conta = inserirLinha("th",'CONTA JUDICIAL',"width: auto;")
    let conferirEmLote = document.createElement("button");
    conferirEmLote.id = 'maisPje_bt_conferirEmAALote';
    conferirEmLote.style = "position: absolute; margin-left: 5px;width: 15px;height: 15px;cursor:pointer;";
    conferirEmLote.title = "Conferir em Lote";	
    conta.appendChild(conferirEmLote);
    cabecalho.appendChild(conta);
    
    let numero = inserirLinha("th",'NÚMERO DO PROCESSO',"width: auto;")
    let conferirEmLoteProcessos = document.createElement("button");
    conferirEmLoteProcessos.id = 'maisPje_bt_ProcessoConferirEmAALote';
    conferirEmLoteProcessos.style = "position: absolute; margin-left: 5px;width: 15px;height: 15px;cursor:pointer;";
    conferirEmLoteProcessos.title = "Copiar processos";	
    numero.appendChild(conferirEmLoteProcessos);
    cabecalho.appendChild(numero);

    cabecalho.appendChild(inserirLinha("th",' ',"width: auto;"));
    tabela.appendChild(cabecalho);

    let tbody = document.createElement('tbody')
    console.log('criando a tabela - corpo')
    for (const [pos, alvara] of children.entries()) {
        console.log(JSON.stringify(alvara))
        let linha = document.createElement("tr");
        linha.style.setProperty('line-height','3em');  

        //coluna1
        let coluna1 = document.createElement("td")        
        let em = inserirLinha("div",'',"display: grid; grid-template-rows: 1fr 1fr; gap: 5px; line-height: 1;padding: 5px 0;");
        em.appendChild(inserirLinha("span",alvara.banco,"font-size: 13px;"));
        em.appendChild(inserirLinha("span",alvara.data + ' - ' + alvara.emissor,"font-size: 11px;  font-style: italic;color: #35878a;"));
        coluna1.appendChild(em);
        linha.appendChild(coluna1);

        //coluna2
        linha.appendChild(inserirLinha("td",alvara.beneficiario,""));
        if (alvara.beneficiario.includes('NÃO IDENTIFICADA')) {
            linha.style.backgroundColor = 'tomato';
            linha.style.fontWeight = 'bold';
        }

        //coluna 3
        let coluna3 = document.createElement("td")
        let tp = document.createElement('span');
        tp.style = "font-size: 1em;padding: .5em;border-radius: .5em;font-weight: bold;";
        if (alvara.tipo.includes('Crédito em Conta')) {
            tp.innerText = 'TED'
            tp.style.backgroundColor = 'gold';				
        } else if (alvara.tipo == 'Pagamento de DARF') {
            tp.innerText = 'DARF'
            tp.style.backgroundColor = 'cadetblue';
        } else if (alvara.tipo == 'Pagamento de GRU') {
            tp.innerText = 'GRU'
            tp.style.backgroundColor = 'darkorange';
        } else if (alvara.tipo == 'Pagamento de GPS') {
            tp.innerText = 'GPS'
            tp.style.backgroundColor = 'burlywood';
        } else {
            tp.innerText = 'OUTROS'
            tp.style.backgroundColor = 'plum';
        }
        coluna3.appendChild(tp);
        linha.appendChild(coluna3);

        //coluna 4
        linha.appendChild(inserirLinha("td",alvara.valor,""));

        //coluna 5
        let coluna5 = document.createElement("td")
        let a2 = document.createElement('a');
        a2.id = 'maisPje_conferir_alvara_processo_conta_' + pos;
        a2.style.cursor = 'pointer';
        a2.setAttribute('maisPJeLink', urlSiscondj + '/pages/mandado/pagamento/exibirAcionadoPelaGrid/' + alvara.conta + '?maisPJeconferir');	
        a2.setAttribute('target', '_blank');
        a2.onclick = function() { this.parentElement.parentElement.style.backgroundColor = "skyblue";this.style.textDecoration = "line-through"; }
        a2.onmouseover = function() { this.firstElementChild.style.display = "unset" }
        a2.onmouseout = function() { this.firstElementChild.style.display = "none" }
        a2.innerText = alvara.conta;
        
        if (alvara.conteudoComprovante) {
            let linkfr = document.createElement('div');
            linkfr.style.display = 'none';
            let fr = document.createElement('iframe');
            fr.style = 'position: fixed; background-color: white; border: medium none;  width: 34vw; height: 90vh; transform: scale(0.8); top: 7vh;left: 5vw;outline: rgba(0, 0, 0, 0.5) solid 12vw;';
            fr.srcdoc = alvara.conteudoComprovante;
            linkfr.appendChild(fr);					
            
            a2.appendChild(linkfr);            
        }
        
        coluna5.appendChild(a2);
        linha.appendChild(coluna5);

        //coluna 6
        let coluna6 = document.createElement("td")
        let a1 = document.createElement('a');
        a1.innerText = alvara.processoFormatado;
        
        if (alvara.identificador) {
            a1.id = alvara.identificador;
            a1.href = 'https://' + alvara.trt + '/pjekz/processo/' + alvara.identificador + '/detalhe';
            a1.setAttribute('target', '_blank');
        } else {
            a1.id = 'numeroProcesso:' + alvara.processo;
            a1.style.cursor = 'pointer';

            //altera a cor da linha
            linha.style.backgroundColor = '#f009';
            linha.style.backgroundImage = 'repeating-linear-gradient(45deg, rgba(0,0,0,0.1) 0px, rgba(0,0,0,0.1) 5px, transparent 5px, transparent 10px)';
            linha.style.cursor = 'no-drop';
            linha.setAttribute('title','Processo em outro Órgão Julgador');
        }
        coluna6.appendChild(a1);
        linha.appendChild(coluna6);


        //coluna 7
        let coluna7 = document.createElement("td")
        let btExcluir = document.createElement('span');
        btExcluir.style = "color: #ddd;cursor: pointer;font-weight: bold;font-size: 1.5em;";
        btExcluir.id = 'btExcluir_' + pos;
        btExcluir.innerText = 'x';
        btExcluir.onmouseover = function() { this.style.color = "coral" }
        btExcluir.onmouseout = function() { this.style.color = "#ddd" }
        coluna7.appendChild(btExcluir);
        linha.appendChild(coluna7);

        tbody.appendChild(linha);
    }
   
    tabela.appendChild(tbody);    
    document.body.appendChild(tabela);

    window.addEventListener("beforeunload", function (e) {
        browser.storage.local.set({'tempAR': ''});
    });
}

function inserirLinha(tag, valor='', estilo='') {
    let el = document.createElement(tag);
    el.style = estilo;
    el.innerText = valor;
    return el;
}

//FUNÇÃO COMPLEMENTAR QUE RETORNA A HORA ATUAL AUXILIANDO NO LOG
function agora(){
	let dNow = new Date();
	return dNow.getDate() + '/' + (dNow.getMonth()+1) + '/' + dNow.getFullYear() + ' ' + dNow.getHours() + ':' + dNow.getMinutes() + ':' + dNow.getMilliseconds();
}

function getUrlBaseSiscondj(url) {
    if (url && url.includes("/pages")) {
        return url.substring(0, url.search("/pages"));
    }
    return url;
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}