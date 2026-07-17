//o array de urls são as condições para verificar o botão. como se fosse um if. todas as condições de url tem que ser atendidas
const regrasGerais = [

    //JANELA MEU PAINEL
    {id:0,url:['/pjekz/gigs/meu-painel'],regra:'.item-menu',ativado:false}, //janela principal > painel lateral
    {id:1,url:['/pjekz/gigs/meu-painel'],regra:'button[aria-label="Menu Completo"]',ativado:false}, //botao do menu geral
    {id:2,url:['/pjekz/gigs/meu-painel'],regra:'[id*="maisPje_bt_principal"]',ativado:false}, //maisPje > botoes da janela principal
    {id:3,url:['/pjekz/gigs/meu-painel'],regra:'button[aria-label*="Detalhes do Processo"]',ativado:false}, //janela principal > icones kaizen que levam a Janela Detalhes do processo
    {id:4,url:['/pjekz/gigs/meu-painel'],regra:'button[aria-label*="Abrir o GIGS"]',ativado:false}, //janela principal > botoes do GIGS
    //JANELA PAINEL GLOBAL
    {id:5,url:['/pjekz/painel/'],regra:'button[aria-label*="Detalhes do Processo"]',ativado:false},
    {id:6,url:['/pjekz/painel/'],regra:'button[aria-label*="Abrir o GIGS"]',ativado:false},
    {id:7,url:['/pjekz/painel/'],regra:'pje-painel-item mat-card',ativado:false}, //painéis
    {id:8,url:['/pjekz/painel/'],regra:'.maisPje_CR',ativado:false}, //maisPJe > botões... criei a classe para inserir nos botoes criados por nós..
    //JANELA RELATORIO GIGS
    {id:9,url:['/pjekz/gigs/relatorios/'],regra:'button[aria-label*="Detalhes do Processo"]',ativado:false},
    {id:10,url:['/pjekz/gigs/relatorios/'],regra:'button[aria-label*="Abrir o GIGS"]',ativado:false},
    {id:11,url:['/pjekz/gigs/relatorios/'],regra:'.maisPje_CR',ativado:false},
    //JANELA ESCANINHO
    {id:12,url:['/pjekz/escaninho/'],regra:'button[aria-label*="Detalhes do Processo"]',ativado:false},
    {id:13,url:['/pjekz/escaninho/'],regra:'button[aria-label*="Abrir o GIGS"]',ativado:false},

    //JANELA DETALHES DO PROCESSO
    {id:14,url:['/pjekz/processo/','/detalhe'],regra:'a[class*="tl-documento"][href*="/conteudo"]',ativado:false},
    {id:15,url:['/pjekz/processo/','/detalhe'],regra:'button[mattooltip="Editar Atividade"]',ativado:false},
    {id:16,url:['/pjekz/processo/','/detalhe'],regra:'button[mattooltip="Concluir Atividade"]',ativado:false},
];

        // '[id*="maisPje_bt_principal_"]:not([maispje_acionarcliquerapido="true"])', //janela principal > painel lateral - botoes inseridos pela maisPJe
    // 'button[aria-label*="Detalhes do Processo"]:not([maispje_acionarcliquerapido="true"])', // menu do kaizen que leva a Janela Detalhes do processo
    // '#botao-menu:not([maispje_acionarcliquerapido="true"])', //janela principal > menu geral
    // '.mat-icon-button:not([maispje_acionarcliquerapido="true"])', //botoes gerais
    // 'i[role="button"]:not([maispje_acionarcliquerapido="true"])', //janela principal > filtros pje
    // 'pje-painel-item[linkpainel="/painel/global"] mat-card:not([maispje_acionarcliquerapido="true"])', //janela principal > filtros pje
    // 'pje-item-menu-sobreposto .item-menu:not([maispje_acionarcliquerapido="true"])', //item do submenu principal
    // 'pje-icone-clipboard:not([maispje_acionarcliquerapido="true"])', //não funciona por causa de questões de segurança

var regrasUsuario;
/*
para adicionar a funcionalidade num botao basta acrescentar a classe maisPJe_CR com o comando "botao.classList.add('maisPje_CR');"
ou
chamar a função acionarCliqueRapido(elemento) passando o elemento desejado
*/
var tempo;
var configuracaoAtivada = false;
const verificarURL = (url) => document.location.href.includes(url);

function iniciar() {
    if (!preferencias.extrasAcionarBotoesSemCliqueAtivar) { return }
    // console.log(preferencias.extrasAcionarBotoesSemCliqueRegras)
    regrasUsuario = preferencias.extrasAcionarBotoesSemCliqueRegras;
    // console.log(regrasUsuario)
    if (!regrasUsuario?.length) { regrasUsuario = [...regrasGerais] } //vazio, nulo ou undefined
    tempo = (preferencias.extrasAcionarBotoesSemCliqueTempo == null || preferencias.extrasAcionarBotoesSemCliqueTempo.trim() == '') ? '1' : preferencias.extrasAcionarBotoesSemCliqueTempo;
    browser.runtime.sendMessage({
        tipo: "insertCSS",
        file: "maisPJe_cliquerapido.css",
    });
    return;
}

async function obterRegrasUsuario() {
    return new Promise(resolver => {
        let resposta = "";
        regrasUsuario.forEach((item) => {
            // console.log('Regra Usuário*******' + item.url + ' > ' + item.url.every(verificarURL) + '   -   ' + item.regra + '   -   ' + (item.ativado ? 'ativado+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++' : 'desativado'))
            if (item.url.every(verificarURL) && item.regra != "" && item.ativado) {
                resposta += (resposta != "" ? ',' : '') + item.regra + ':not([maispje_acionarcliquerapido="true"])';
            }
        });
        console.debug('REGRAS USUARIO: ' + resposta)
        return resolver(resposta);
    });
}

async function mapearElementosParaCliqueRapido() {
	return new Promise(async resolver => {
        if (!iniciar()) { return }
        let seletor = await obterRegrasUsuario();
        if (!seletor) { return }
        // console.log('maisPJe: mapearElementosParaCliqueRapido()');

        await sleep(1000); //eséra 1 segundo antes de mapear
        //PRIMEIRA ETAPA: MAPEIA DE IMEDIATO
        document.querySelectorAll(seletor).forEach((item) => {
            // console.debug('    |___*' + item.tagName + ' id=' + item.id  + ' name=' + item.name + ' class=' + item.className + ' : mapeado!')
            acionarCliqueRapido(item);
        });


        //SEGUNDA ETAPA: MAPEIA CONFORME OS ELEMENTOS VÃO SURGINDO
        let timer; //faz com que a função de obeservar novos documentos seja executada apenas quando o intervalo entre cada mutation seja maior que 1 segundo
        let trocaURL = ""; //sempre que troca a URL, refaz as regras do usuario
        let observerCliqueRapido = new MutationObserver(async function(mutationsDocumento) {
            if (document.location.href != trocaURL) { console.log('*******************trocou a url');console.log('*******************era ' + trocaURL); console.log('*******************ficou ' + document.location.href); trocaURL = document.location.href; seletor = await obterRegrasUsuario();}
            if (timer) clearTimeout(timer);
			timer = setTimeout(() => {
                mutationsDocumento.forEach(async function(mutation) {
                    if (!mutation.addedNodes[0]) { return }
                    if (!mutation.addedNodes[0].tagName) { return }
                    if (mutation.addedNodes[0].hasAttribute('maispje_acionarcliquerapido')) { return } //itens já mapeados
                    if(!seletor?.length) { return }
                    for (const [pos, item] of document.querySelectorAll(seletor).entries()) {
                        // console.debug('    |___**' + item.tagName + ' id=' + item.id  + ' name=' + item.name + ' class=' + item.className + ' : mapeado!')
                        await acionarCliqueRapido(item);
                    }
                });
            }, 1000);
        });
        observerCliqueRapido.observe(document.body, { childList: true, subtree: true });

        return resolver(true)
	});
}

async function acionarCliqueRapido(elemento) {
    return new Promise(async resolver => {
        if (elemento) {
            //define os alvos do clique.. elementos que possuam event listener de click
            // if (elemento.tagName == 'DIV' && elemento.className.includes('item-menu')) { //EXCEÇÃO > item de submenu da janela principal
            //     console.log(elemento?.firstChild.tagName)
            //     let novo = elemento.querySelector('a');
            //     if (novo) {
            //         elemento = novo; //ALVO DO CLIQUE
            //     }

            // } else if (elemento.tagName.includes('PJE-ICONE')) { //EXCEÇÃO > filtros da janela principal
            // } else if (elemento.tagName == 'I' && elemento?.getAttribute('role') == 'button') { //EXCEÇÃO > filtros da janela principal
            // } else if (elemento.tagName == 'MAT-CARD' && elemento?.getAttribute('role') == 'list') { //painéis do painel global
            // } else {
                if (!['BUTTON','A','MAT-CARD'].includes(elemento.tagName)) { //menu kaizen e gerais
                    // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                    elemento = elemento.firstChild;
                    if (elemento && !['BUTTON','A','MAT-CARD'].includes(elemento.tagName)) {
                        // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                        elemento = elemento.firstChild;
                        if (elemento && !['BUTTON','A','MAT-CARD'].includes(elemento.tagName)) {
                            // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                            elemento = elemento.firstChild;
                            if (elemento && !['BUTTON','A','MAT-CARD'].includes(elemento.tagName)) {
                                // console.debug('    |___"' + elemento.tagName + '" não compatível. Encerrar acionarSemClique()!')
                                return;
                            }
                        }
                    }
                }
            //}
            if (!tempo) { tempo = 2}
            let temporizador = parseFloat(tempo);
            let mouseEmCima = false;
            let check99;

            elemento.classList.remove('maisPJe-cliqueRapido-desativado');
            elemento.setAttribute('maispje_acionarcliquerapido','true');

            elemento.addEventListener("click", function (event) {
                if (configuracaoAtivada) { return }
                let el = event.target;
                clearInterval(check99);
                mouseEmCima = false;
                el.querySelector('maisPJeLoader')?.remove();
                el.style.visibility = 'hidden'; //desaparece para não ficar acionando caso o usuário fique com o mouse parado. volta apenas após 4 segundos
                setTimeout(function() {el.style.visibility = 'visible';}, 4000); //retorna após 4 segundos
            });

            elemento.onmouseenter = async function (event) {
                if (configuracaoAtivada) { return }
                event.preventDefault();
                if (mouseEmCima) { return }
                let el = event.target;
                if (!el.querySelector('maisPJeLoader')) {
                    let loader = document.createElement('maisPJeLoader');
                    loader.style.setProperty('--tempo',temporizador+'s');
                    el.appendChild(loader)
                }
                mouseEmCima = true;
                let seg = 1;
                check99 = setInterval(function() {
                    seg--;
                    if (mouseEmCima && seg < 1) {
                        clearInterval(check99);
                        mouseEmCima = false;
                        window.focus(); // garante o clique mesmo que o usuário clique em outra janela
                        el.click();
                    }
                }, temporizador*1000);
            };

            elemento.onmouseleave = function (event) {
                if (configuracaoAtivada) { return }
                event.preventDefault();
                let el = event.target;
                el.querySelector('maisPJeLoader')?.remove();
                mouseEmCima = false;
                clearInterval(check99);
            };
        }
        return resolver(true);
    });
}

async function configurarBotoesMapeados() {
    if (!iniciar()) { return }
    console.debug('maisPje: configurarBotoesMapeados()');
    configuracaoAtivada = true;
    document.querySelector('menumaispje').style.display = 'none';//oculta o menu kaizen para não atrapalhar
    regrasGerais.forEach((item) => {
        if (item.url.every(verificarURL)) { //separa apenas as regras cabíveis à URL
            document.querySelectorAll(item.regra).forEach((elemento) => {
                // console.debug('    |___*' + item.tagName + ' id=' + item.id + ' name=' + item.name + ' aria=' + item.aria);
                elemento.classList.add('maisPJe-cliqueRapido-desativado'); //essa classe adiciona o pointereventes
                criarSombra(elemento.getBoundingClientRect(), [item.id,item.url,item.regra,item.ativado]);
            });
        }
    });
}

async function criarSombra(rect, dados) {
	return new Promise(async resolve => {
		if (!document.querySelector('maisPje_bloquearTela')) {
            let fundo = document.createElement("maisPje_bloquearTela");
            let btSalvar = document.createElement('maisPje_bloquearTela_btSalvar');
            btSalvar.aria = 'Salvar regras';
            btSalvar.onclick = function () {//salvar
                let limparStorage = browser.storage.local.set({'extrasAcionarBotoesSemCliqueRegras': regrasUsuario});
                Promise.all([limparStorage]).then(async values => {
                    preferencias.extrasAcionarBotoesSemCliqueRegras = regrasUsuario;
                    // criarCaixaDeAlerta('Atenção','Regra de preferência copiada para a memória...\n\nAtualize a página (F5) para aplicar as mudanças.',5);
                    browser.runtime.sendMessage({tipo: 'criarAlerta', valor: 'Regra de preferência copiada para a memória...', icone: '5'});
                    window.location.reload();
                });
            }
            fundo.appendChild(btSalvar);
            document.body.prepend(fundo);
        }

        let maispjeMap = document.createElement("maispjeMap");
        maispjeMap.style.top = rect.top+'px';
        maispjeMap.style.left = rect.left+'px';
        maispjeMap.style.width = rect.width+'px';
        maispjeMap.style.height = rect.height+'px';
        console.log('                                        dados: ' + dados[0] + ': ' + dados[1] + '(' + dados[1].every(verificarURL) + ')   -   '+ dados[2] + '   -   '+ dados[3])
        let regraGeralNumero = dados[0];
        maispjeMap.setAttribute('regraGeralNumero',regraGeralNumero);
        maispjeMap.className = (regrasUsuario[regraGeralNumero].ativado) ? 'ativado' : 'desativado';
        maispjeMap.onclick = async function() {
            let p = this.getAttribute('regraGeralNumero');
            if (!this.classList.contains('ativado')) { //ativado
                document.querySelectorAll('maispjeMap[regraGeralNumero="' + p + '"]').forEach((item) => { item.className = 'ativado' });
                regrasUsuario[regraGeralNumero].ativado = true;
            } else { //desativado
                document.querySelectorAll('maispjeMap[regraGeralNumero="' + p + '"]').forEach((item) => { item.className = 'desativado' });
                regrasUsuario[regraGeralNumero].ativado = false;
            }
        }
        document.querySelector('maisPje_bloquearTela').appendChild(maispjeMap);

        return resolve(true);
	});
}
