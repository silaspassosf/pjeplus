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
    {id:14,url:['/pjekz/escaninho/'],regra:'.link-icone-kz',ativado:false}, //é o kaizen da janela Situação Alvará no escaninho
    {id:15,url:['/pjekz/escaninho/'],regra:'button[aria-label*="Visualizar comprovante"]',ativado:false},
    {id:16,url:['/pjekz/escaninho/'],regra:'button[aria-label*="Importar comprovante de alvará"]',ativado:false},
    {id:17,url:['/pjekz/escaninho/'],regra:'button[aria-label*="Remover alvará"]',ativado:false},
    //aria-label="Visualizar comprovante"

    //QUADRO AVISO
    {id:18,url:['/pjekz/quadro-avisos/visualizar'],regra:'.item-menu',ativado:false}, //janela principal > painel lateral
    {id:19,url:['/pjekz/quadro-avisos/visualizar'],regra:'button[aria-label="Menu Completo"]',ativado:false}, //botao do menu geral
    //MENU SUSPENSO
    {id:20,url:['/pjekz/gigs/meu-painel'],regra:'input[src*="assets/images/dock-menu/"]',ativado:false}, //botao do menu geral

    //JANELA DETALHES DO PROCESSO
    // {id:14,url:['/pjekz/processo/','/detalhe'],regra:'a[class*="tl-documento"][href*="/conteudo"]',ativado:false},
    // {id:15,url:['/pjekz/processo/','/detalhe'],regra:'button[mattooltip="Editar Atividade"]',ativado:false},
    // {id:16,url:['/pjekz/processo/','/detalhe'],regra:'button[mattooltip="Concluir Atividade"]',ativado:false},
];

var regrasUsuario;
/*
para adicionar a funcionalidade num botao basta acrescentar a classe maisPJe_CR com o comando "botao.classList.add('maisPje_CR');"
ou
chamar a função acionarCliqueRapido(elemento) passando o elemento desejado
*/
var tempo;
var configuracaoAtivada = false;
const verificarURL = (url) => document.location.href.includes(url);

async function iniciar() {
    if (!preferencias.extrasAcionarBotoesSemCliqueAtivar) { return }
    configuracaoAtivada = preferencias.extrasAcionarBotoesSemCliqueAtivar
    regrasUsuario = preferencias.extrasAcionarBotoesSemCliqueRegras;
    if (!regrasUsuario?.length) { regrasUsuario = [...regrasGerais] } //vazio, nulo ou undefined
    tempo = (preferencias.extrasAcionarBotoesSemCliqueTempo == null || preferencias.extrasAcionarBotoesSemCliqueTempo.trim() == '') ? '1' : preferencias.extrasAcionarBotoesSemCliqueTempo;

    //CSS
    if (!document.querySelector('#maisPje_cliquerapido_css')) {
        let scriptCcs = `maisPje_bloquearTela {
            position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 999; background-color: #0000;
        }

        maisPje_bloquearTela_btSalvar {
            position: absolute;
            cursor: pointer;
            right: 48vw;
            top: 90vh;
            border: none;
            background-color: white;
            font-size: 2rem;
            scale: 1;
            border-radius: 50%;
            width: 4rem;
            height: 4rem;
            align-content: center;
            text-align: center;
            box-shadow: rgba(0, 0, 0, 0.25) 0px 54px 55px, rgba(0, 0, 0, 0.12) 0px -12px 30px, rgba(0, 0, 0, 0.12) 0px 4px 6px, rgba(0, 0, 0, 0.17) 0px 12px 13px, rgba(0, 0, 0, 0.09) 0px -3px 5px;
        }

        maisPje_bloquearTela_btSalvar::before {
            content: "💾";
        }

        maisPje_bloquearTela_btSalvar:hover {
            scale: 1.2;
        }

        maispjeMap {
            position: absolute;
            z-index: 9;
        }

        maispjeMap.desativado {
            outline: .2rem dashed orangered;
            background-color: unset;
        }

        maispjeMap.ativado {
            outline: .2rem solid orangered;
            background-color: #ff45002e;
        }

        maispjeMap:hover {
            background-color: #ff450099;
            cursor: pointer;
        }

        .maisPJe-cliqueRapido-bloqueio {
            pointer-events: none;
        }

        maisPJeLoader {
            position: absolute;
            display:block;
            top:0;
            left:0;
            width:1em;
            height:1em;
            border-radius: 50%;
            transform:rotate(45deg);
            background: #fff;
            outline: .1rem solid dodgerblue;
        }

        maisPJeLoader::before {
            content: "";
            box-sizing: border-box;
            position: absolute;
            inset: 0px;
            border-radius: 50%;
            border:.5em solid dodgerblue;
            animation: maisPJe_acionarCliqueRapido var(--tempo) linear;
        }

        @keyframes maisPJe_acionarCliqueRapido {
            0% { clip-path:polygon(50% 50%,0 0,0 0,0 0,0 0,0 0) }
            25% { clip-path:polygon(50% 50%,0 0,100% 0,100% 0,100% 0,100% 0) }
            50% { clip-path:polygon(50% 50%,0 0,100% 0,100% 100%,100% 100%,100% 100%) }
            75% { clip-path:polygon(50% 50%,0 0,100% 0,100% 100%,0 100%,0 100%) }
            100% { clip-path:polygon(50% 50%,0 0,100% 0,100% 100%,0 100%,0 0) }
        }

        @keyframes maisPJe_acionarCliqueRapido_mapeado {
            0% { outline: 0px solid #ff450082 }
            25% { outline: 2.5px solid #ff450082 }
            50% { outline: 5px solid #ff450082 }
            75% { outline: 2.5px solid #ff450082 }
            100% { outline: 0px solid #ff450082 }
        }

        .div-coluna-processo-esquerda {
            position: relative !important;
        }`;

        let style = document.createElement("style");
        style.id = "maisPje_cliquerapido_css";
        style.textContent = scriptCcs;
        document.body.appendChild(style);
    }
    return;

    //não funcionou muito bem a injeção pelo background
    // let injecaoCCS = await browser.runtime.sendMessage({ tipo: "insertCSS", file: "maisPJe_cliquerapido.css" });
    // return injecaoCCS;
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

        //primeiro acesso.. quando faz login
        if (document.location.href.slice(-7) == '/pjekz/') { await esperarLogin() }

        let seletor = await obterRegrasUsuario();
        if (!seletor) { return }
        // console.log('maisPJe: mapearElementosParaCliqueRapido()');

        // await sleep(1000); //espera 1 segundo antes de mapear
        //PRIMEIRA ETAPA: MAPEIA DE IMEDIATO DOS ITENS QUE JÁ ESTÃO NA TELA
        document.querySelectorAll(seletor).forEach((item) => {
            // console.debug('    |___*' + item.tagName + ' id=' + item.id  + ' name=' + item.name + ' class=' + item.className + ' : mapeado!')
            acionarCliqueRapido(item);
        });


        //SEGUNDA ETAPA: MAPEIA CONFORME OS ELEMENTOS VÃO SURGINDO
        // let timer; //faz com que a função de observar novos documentos seja executada apenas quando o intervalo entre cada mutation seja maior que 1 segundo
        let trocaURL = ""; //sempre que troca a URL, refaz as regras do usuario
        let observerCliqueRapido = new MutationObserver(async function(mutationsDocumento) {

            if (document.location.href != trocaURL) {
                console.log('*******************trocou a url');console.log('*******************era ' + trocaURL);
                console.log('*******************ficou ' + document.location.href);
                trocaURL = document.location.href;
                seletor = await obterRegrasUsuario();
            }

            // if (timer) clearTimeout(timer);
			// timer = setTimeout(() => {
                mutationsDocumento.forEach(async function(mutation) {
                    if (!mutation.addedNodes[0]) { return }
                    if (!mutation.addedNodes[0].tagName) { return }

                    // console.debug('    |___**' + mutation.addedNodes[0].tagName + ' id=' + mutation.addedNodes[0].id  + ' name=' + mutation.addedNodes[0].name + ' class=' + mutation.addedNodes[0].className)

                    if (mutation.addedNodes[0].hasAttribute('maispje_acionarcliquerapido')) { return } //itens já mapeados
                    if(!seletor?.length) { return }
                    for (const [pos, item] of document.querySelectorAll(seletor).entries()) {
                        // console.debug('    |___**' + item.tagName + ' id=' + item.id  + ' name=' + item.name + ' class=' + item.className + ' : mapeado!')
                        await acionarCliqueRapido(item);
                    }
                });
            // }, 1000);
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
                if (!['BUTTON','A','MAT-CARD','INPUT'].includes(elemento.tagName)) { //menu kaizen e gerais
                    // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                    elemento = elemento.firstChild;
                    if (elemento && !['BUTTON','A','MAT-CARD','INPUT'].includes(elemento.tagName)) {
                        // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                        elemento = elemento.firstChild;
                        if (elemento && !['BUTTON','A','MAT-CARD','INPUT'].includes(elemento.tagName)) {
                            // console.debug('    |___"' + elemento.tagName + '" não compatível. Trocar por firstChild')
                            elemento = elemento.firstChild;
                            if (elemento && !['BUTTON','A','MAT-CARD','INPUT'].includes(elemento.tagName)) {
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
            elemento.style.animation = 'maisPJe_acionarCliqueRapido_mapeado 0.5s linear';

            elemento.addEventListener("click", function (event) {
                if (!configuracaoAtivada) { return }
                let el = event.target;
                clearInterval(check99);
                mouseEmCima = false;
                el.querySelector('maisPJeLoader')?.remove();
                el.style.pointerEvents = 'none'; //desativa os eventos do mouse caso o usuário fique com o mouse parado. volta apenas após 6 segundos
                setTimeout(function() {el.style.pointerEvents = 'auto';}, 6000); //retorna após 6 segundos
            });

            elemento.onmouseenter = async function (event) {
                if (!configuracaoAtivada) { return }
                event.preventDefault();
                if (mouseEmCima) { return }
                let el = event.target;
                if (!el.querySelector('maisPJeLoader')) {
                    let loader = document.createElement('maisPJeLoader');
                    loader.style.setProperty('--tempo',temporizador+'s');
                    let elementoAncora = (el.tagName == 'INPUT') ? el.parentElement : el; //pq o input não exibe o loader dentro dele
                    elementoAncora.appendChild(loader)
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
                if (!configuracaoAtivada) { return }
                event.preventDefault();
                let el = event.target.parentElement; // usei o parentelement por causa dos inputs, ver listener onmouseenter desse elemento
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
    await esperarElemento('#maisPje_cliquerapido_css')

    console.debug('maisPje: configurarBotoesMapeados()');
    configuracaoAtivada = true;
    const estiloAntigo = document.querySelector('menumaispje').style.display;
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
    document.querySelector('menumaispje').style.display = estiloAntigo;//volta o menu kaizen para que ele nao fique sumido
}

async function criarSombra(rect, dados) {
	return new Promise(async resolve => {
		if (!document.querySelector('maisPje_bloquearTela')) {
            let fundo = document.createElement("maisPje_bloquearTela");
            let btSalvar = document.createElement('maisPje_bloquearTela_btSalvar');
            btSalvar.ariaLabel = 'Salvar regras';
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

async function esperarLogin() {
    return new Promise(async resolve => {
        let check = setInterval(function() {
            if (document.location.href.includes('/pjekz/gigs/meu-painel') || document.location.href.includes('/pjekz/quadro-avisos/visualizar')) {
                clearInterval(check);
                return resolve(true);
            }
        }, 100);
    });
}


