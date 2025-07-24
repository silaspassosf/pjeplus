function aguardarCarregamentoTabela() {
	return new Promise(resolve => {
		let desapareceu = false;
		let apareceu = false;
		let check = setInterval(function() {
			let barraIdentificadora = document.querySelector('tr mat-progress-bar');
			if (barraIdentificadora) {
				apareceu = true;
			} else {
				desapareceu = true;
			}
			
			if (apareceu && desapareceu) {
				clearInterval(check);	
				return resolve(true);
			}
		}, 100);
	});		
}

function getGrauAsNumber(grau_usuario) {
	const graus = {
		"primeirograu": 1,
		"segundograu": 2,
		"tst": 3
	};

	return graus[grau_usuario] || 1; //TODO: deveria retornar 1 por padrão? Não deveria retornar um erro?
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

function querySelectorByText(tagname, texto){
	if (texto.includes('[MMA]')) { //observar maiuscula, minúsula e acento
		texto = texto.replace('[MMA]','');
		return Array.from(document.querySelectorAll(tagname)).find(el => el.textContent.trim() == texto);
	} else if (texto.includes('[exato]')) { //tem que ser a expressão exata.. sem estar incluída no texto
		texto = texto.replace('[exato]','');
		return Array.from(document.querySelectorAll(tagname)).find(el => removeAcento(el.textContent.trim().toLowerCase()) == removeAcento(texto.toLowerCase()));
	} else if (texto.includes('[ou]')) { //mais de uma opção separado por vírgula...tem que ser a expressão exata.. sem estar incluída no texto.. 
		texto = texto.replace('[ou]','');
		let opcoes = texto.split(',');
		return Array.from(document.querySelectorAll(tagname)).find( function (el) {
			for (let i = 0; i < opcoes.length; i++) {
				console.log(removeAcento(el.textContent.trim().toLowerCase()))
				console.log(opcoes[i].toLowerCase())
				if ( removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(opcoes[i].toLowerCase()))) {
					return el;
				}
			}
			return null;
		});
	} else {
		return Array.from(document.querySelectorAll(tagname)).find(el => removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(texto.toLowerCase())));
	}
}

function nextParent(el, tagName) {
	tagName = tagName.toLowerCase();
	while (el && el.parentNode) {
		el = el.parentNode;
		if (el.tagName && el.tagName.toLowerCase() == tagName) {
			return el;
		}
	}
	return null;
}

function removeAcento(text){
	let stringComAcentos = "ÄÅÁÂÀÃäáâàãÉÊËÈéêëèÍÎÏÌíîïìÖÓÔÒÕöóôòõÜÚÛüúûùÇç";
	let stringSemAcentos = "AAAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUuuuuCc";
	
	for (let i = 0; i<stringComAcentos.length; i++) {
		while(true) {	
			if (text.search(stringComAcentos[i].toString()) > -1) {				
				text = text.replace(stringComAcentos[i].toString(), stringSemAcentos[i].toString());
			} else {
				break;
			}
		}
	}
    return text;                 
}

function esperarElemento(seletor, texto, tempo_espera) {
	return new Promise(resolve => {
		let elemento = texto ? querySelectorByText(seletor, texto) : document.querySelector(seletor);
		if (elemento) {
			// console.log("                        achou de pronto : " + seletor + (texto ? ">" + texto : "") + " : " + elemento.toString());
			return resolve(elemento);
		} else {
			let observer = new MutationObserver(mutations => {
				// console.log("                        esperando o elemento " + seletor + (texto ? ">" + texto : ""));
				let elemento_esperado = texto ? querySelectorByText(seletor, texto) : document.querySelector(seletor);
				if (elemento_esperado) {
					observer.disconnect();
					// console.log("                             |___achou após esperar : " + seletor + (texto ? ">" + texto : "") + " : " + elemento_esperado.toString());
					return resolve(elemento_esperado);
				}
			});
			
			tempo_espera = (tempo_espera) ? tempo_espera : 10000;
			observer.observe(document.body, { childList: true, subtree: true });
			setTimeout(function() { 
				observer.disconnect(); 
				resolve(null); 
			}, tempo_espera);  //se não tiver qualquer mudança em 10 segundos, significa que o elemento não aparecerá
		}
    });
}

function getMatFormFieldsDoFormulario(formulario) {
    //TODO: verificar se precisamos mapear mais campos. O que fazer qdo nao se trata de mat-form-field?
    const elementos = Array.from(formulario.querySelectorAll('mat-radio-group, mat-form-field'));
    const elems = elementos.map(e => {
        const tagName = e.nodeName.toLowerCase();
        //TODO: verificar se outros tipos sao necessarios
        return tagName == 'mat-form-field' ? e.querySelector('mat-select, textarea, input') : e
    });

    // console.info('elementos', elems)
    return elems;
}

function criarElemento(tag, styleString, texto) {
    const element = document.createElement(tag);
    
    // Adiciona o texto ao elemento
    element.textContent = texto; 
    
    // Adiciona estilos ao elemento
    const styles = styleString.split(';');
    styles.forEach(style => {
        if (style.trim()) {
            const [key, value] = style.split(':');
            element.style[key.trim()] = value.trim();
        }
    });

    return element;
}

function insertAfter(referenceNode, newNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

async function esperarColecao(seletor, qtde_minima=1, tempo_espera=0) {
	return new Promise(async resolve => {
		let elemento = document.querySelectorAll(seletor);
		if (elemento && elemento.length >= qtde_minima) {
			// console.log("                        achou de pronto : " + seletor + " : " + elemento.toString());
			resolve(elemento);
			return;
        } else {
			let observer = new MutationObserver(mutations => {
				// console.log("                        esperando o elemento " + seletor + " " + qtde_minima);
				let elemento_esperado = document.querySelectorAll(seletor);
				if (elemento_esperado && elemento_esperado.length >= qtde_minima) {
					observer.disconnect();
					// console.log("                             |___achou após esperar : " + seletor + " " + qtde_minima + " : " + elemento_esperado.toString() + " : tamanho ---> " + elemento_esperado.length);
					resolve(elemento_esperado);
					return;
				}
			});
			
			tempo_espera = (tempo_espera) ? tempo_espera : 10000;
			observer.observe(document.body, { childList: true, subtree: true });
			setTimeout(function() { 
				observer.disconnect(); 
				resolve(null); 
			}, tempo_espera);  //se não tiver qualquer mudança em 10 segundos, significa que o elemento não aparecerá
		}
    });
}

async function esperarDesaparecer(el, intervalo=100) {
	return new Promise(resolve => {
		let check1 = setInterval(async function() {
			// console.log('************** ' + el.isConnected);
			if (!el.isConnected) {
				clearInterval(check1);
				// console.log('desapareceu1')
				resolve(true);
			}
		}, intervalo);
		
		if (el.style?.display) {
			let check2 = setInterval(async function() {
				// console.log('************** ' + el.style.display);
				if (el.style.display == 'none') {
					clearInterval(check1);
					clearInterval(check2);
					// console.log('desapareceu2')
					resolve(true);
				}
			}, intervalo);
		}
		
	});
}

async function preencherTextArea(seletor, valor) {
	await sleep(preferencias.maisPje_velocidade_interacao);
	let elemento;
	if (seletor instanceof HTMLElement) {
		elemento = seletor;
	} else {
		elemento = await esperarElemento(seletor)
	}
	elemento.focus();
	elemento.value = valor;	
	triggerEvent(elemento, 'input');
	triggerEvent(elemento, 'change');
	triggerEvent(elemento, 'dateChange');
	triggerEvent(elemento, 'keyup');
	console.log("                   |---> TEXTAREA " + seletor + ">" + valor);
}

//FUNÇÃO PARA CRIAÇÃO DOS TOOLTIPS
function tooltip(posicao, ativarFundo) {
	let style = document.createElement("style");
	style.id = "maisPje_tooltip_" + posicao;
	style.textContent = '[maisPje-tooltip-' + posicao + '] {position: relative; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje-tooltip-' + posicao + ']:before {content: attr(maisPje-tooltip-' + posicao + '); display: none; position: absolute; vertical-align: middle; pointer-events: none; width: auto;  height: auto; min-height: 1rem; white-space:nowrap; z-index: 6; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: 14px; font-weight: 500; background: black; opacity: 1; color: white; border-radius: 5px; box-shadow: 3px 3px 10px grey;';
	switch (posicao) {
		case 'oculto':
			style.textContent += 'top: 0; left: 0;}';
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: none;}';
			break
		case 'acima':
			style.textContent += 'top: 0; left: 2.5vw;}';
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'menuEsquerda':
			style.textContent += 'padding: 10px; top: 0; right: 4vw;}';
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			style.textContent += '.maisPje-fade-out {animation: fadeout 0.3s;}';
			break
		case 'menuDireita':
			style.textContent += 'padding: 10px; top: 0; left: 4vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			style.textContent += '.maisPje-fade-out {animation: fadeout 0.3s;}';
			break
		case 'menuAcima':
			style.textContent += 'padding: 10px;top: -5vh; left: -4vw;}';
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			style.textContent += '.maisPje-fade-out {animation: fadeout 0.3s;}';
			break
		case 'menuAbaixo':
			style.textContent += 'padding: 10px; top: 5vh; left: -4vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			style.textContent += '.maisPje-fade-out {animation: fadeout 0.3s;}';
			break
		case 'abaixo':
			style.textContent += 'padding: 10px; top: 6vh; left: -4vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'abaixo2':
			style.textContent += 'padding: 0 10px 0 10px; top: 5vh; left: -1vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'abaixo3':
			style.textContent += 'padding: 0 10px 0 10px; top: 6.1vh; left: -5vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'abaixo4':
			style.textContent += 'padding: 0 10px 0 10px; top: 6.1vh; right: 0vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'abaixo5':
			style.textContent += 'padding: 0 10px 0 10px; top: 5vh; left: 0vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'direita':
			style.textContent += 'padding: 0 10px 0 10px; top: 0; left: 3vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'direita2':
			style.textContent += 'padding: 10px; top: 0; left: 7vw;}'; //*
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			break
		case 'esquerda':
			style.textContent += 'padding: 10px; top: 0; right: 4vw;}';
			style.textContent += '[maisPje-tooltip-' + posicao + ']:hover:before {display: inline-block;}';
			style.textContent += '.maisPje-fade-out {animation: fadeout 0.3s;}';
			break
		case 'fundo':
			style.textContent = '';
			break
	}
	
	if (ativarFundo) {
		style.textContent += '.pjextension_executando {animation: animacao 1s infinite;animation-fill-mode: both;margin-top:-15vh;}';
		style.textContent += '@keyframes animacao {0% {transform: scale3d(1, 1, 1);}30% {transform: scale3d(1.25, 0.75, 1);}40% {transform: scale3d(0.75, 1.25, 1);}50% {transform: scale3d(1.15, 0.85, 1);}65% {transform: scale3d(.95, 1.05, 1);}75% {transform: scale3d(1.05, .95, 1);}100% {transform: scale3d(1, 1, 1);}}';
		style.textContent += '@keyframes pulse {0% {box-shadow: 0 0 0 0px rgba(255, 0, 0, .7);}50% {box-shadow: 0 0 0 10px rgba(255, 0, 0, .3);	background: rgba(255, 0, 0, .7);} 100% {box-shadow: 0 0 25px 20px rgba(255, 0, 0, .05);}}';
		style.textContent += '@keyframes pulseLeve {0% {box-shadow: 0 0 0 0px rgba(80, 119, 164, .7);}50% {box-shadow: 0 0 0 0px rgba(80, 119, 164, .3); background: rgba(80, 119, 164, .7);} 100% {box-shadow: 0 0 0px 0px rgba(80, 119, 164, .05);}}';
	}
	document.body.appendChild(style);	
}

//FUNÇÃO QUE MONITORA O APARECIMENTO E DESAPARECIMENTO DO OBJETO DE PROCESSAMENTO, PARA QUANDO FOR NECESSÁRIO ESPERAR O CARREGAMENTO DE ALGO
async function aguardarCarregamentoPje() {
	return new Promise(async resolve => {					
		let spinner = await esperarElemento('PJE-DIALOGO-STATUS-PROGRESSO',null,1000);
		// console.log('**entrou spinner: ' + spinner)
		if (spinner) {
			let check = setInterval(function() {					
				if (!document.querySelector('PJE-DIALOGO-STATUS-PROGRESSO')) {
				// console.log('**saiu spinner ')
				 clearInterval(check);
				return resolve(true);
			  }
			}, 100);
		} else {
			return resolve(false);
		}
	});
}

function extrairTRT(url) {
	let padraoTRT = /trt\d{1,2}/; //eliminar urls que possuem numero. por exemplo: https://pjehom2.trt12.jus.br
	let padraoSoNumero = /\d{1,}/;

	let urlTRT = url.match(padraoTRT).join();
	return urlTRT.match(padraoSoNumero).join();
}

function extrairNumeros(texto) {
	let padrao = /\d{1,}/;	
	if (padrao.test(texto)) {
		return texto.match(padrao).join();
	} else {
		return texto;
	}
}

function porExtenso(valor){
	console.debug('------------------------------------------------')
	let listaDeExcecoes = {
		"010":"dez",
		"011":"onze",
		"012":"doze",
		"013":"treze",
		"014":"catorze",
		"015":"quinze",
		"016":"dezesseis",
		"017":"dezessete",
		"018":"dezoito",
		"019":"dezenove",
		"020":"vinte",
		"030":"trinta",
		"040":"quarenta",
		"050":"cinquenta",
		"060":"sessenta",
		"070":"setenta",
		"080":"oitenta",
		"090":"noventa",
		"100":"cem",
		"200":"duzentos",
		"300":"trezentos",
		"400":"quatrocentos",
		"500":"quinhentos",
		"600":"seiscentos",
		"700":"setecentos",
		"800":"oitocentos",
		"900":"novecentos",
	};

	let arrayDeReferencia = {
		"unidade":["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"],
		"dezena":["","", "vinte e ", "trinta e ", " quarenta e ", " cinquenta e ", " sessenta e ", " setenta e ", " oitenta e ", " noventa e "],
		"centena":["", "cento e ", "duzentos e ", "trezentos e ", "quatrocentos e ", "quinhentos e ", "seiscentos e ", "setecentos e ", "oitocentos e ", "novecentos e "]
	};
	
	let soNumero = valor.replace(/\D/g, "");	
	soNumero = soNumero.padStart(14,"0"); //999 bilhão possui 14 zeros, incluindo os centavos	
	let nCentavos = soNumero.slice(soNumero.length-2, soNumero.length);
	let nReais = soNumero.slice(soNumero.length-5, soNumero.length-2);
	let nMilhar = soNumero.slice(soNumero.length-8, soNumero.length-5);
	let nMilhao = soNumero.slice(soNumero.length-11, soNumero.length-8);
	let nBilhao = soNumero.slice(soNumero.length-14, soNumero.length-11);
	
	//regras do centavos	
	let centavos = '';
	nCentavos = nCentavos.padStart(3,"0"); //acrescena mais um zero nos centavos para não ficar criando exceções repetidas na listaDeExcecoes
	if (nCentavos == '000') {
		centavos = '';
	} else if (nCentavos == '001') {
		centavos = 'um centavo'
	} else if (listaDeExcecoes.hasOwnProperty(nCentavos)) { //se está na lista de exceções
		centavos = listaDeExcecoes[nCentavos] + ' centavos';
	} else {
		centavos = arrayDeReferencia.centena[parseInt(nCentavos[0])] + arrayDeReferencia.dezena[parseInt(nCentavos[1])] + arrayDeReferencia.unidade[parseInt(nCentavos[2])] + ' centavos';
	}
	
	//regras do reais
	let reais = '';
	if (nReais == '000') {
		reais = '';
	} else if (nReais == '001') {
		reais = 'um real';
	} else if (listaDeExcecoes.hasOwnProperty(nReais)) { //se está na lista de exceções
		reais = listaDeExcecoes[nReais] + ' reais';
	} else {
		let x = '0' + nReais[1] + nReais[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nReais[1])] + arrayDeReferencia.unidade[parseInt(nReais[2])];
		reais = arrayDeReferencia.centena[parseInt(nReais[0])] + x + ' reais';
	}
	
	//regras do milhar	
	let milhar = '';
	if (nMilhar == '000') {
		milhar = '';
	} else if (listaDeExcecoes.hasOwnProperty(nMilhar)) { //se está na lista de exceções
		milhar = listaDeExcecoes[nMilhar] + ' mil';
	} else {
		let x = '0' + nMilhar[1] + nMilhar[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nMilhar[1])] + arrayDeReferencia.unidade[parseInt(nMilhar[2])];
		milhar = arrayDeReferencia.centena[parseInt(nMilhar[0])] + x + ' mil';
	}
	
	//regras do milhao
	let milhao = '';
	if (nMilhao == '000') {
		milhao = '';
	} else if (nMilhao == '001') {
		milhao = 'um milhão ';
	} else if (listaDeExcecoes.hasOwnProperty(nMilhao)) { //se está na lista de exceções
		milhao = listaDeExcecoes[nMilhao] + ' milhões ';
	} else {
		let x = '0' + nMilhao[1] + nMilhao[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nMilhao[1])] + arrayDeReferencia.unidade[parseInt(nMilhao[2])];
		milhao = arrayDeReferencia.centena[parseInt(nMilhao[0])] + x + ' milhões, ';
	}
	
	//regras do bilhao
	let bilhao = '';
	if (nBilhao == '000') {
		bilhao = '';
	} else if (nBilhao == '001') {
		bilhao = 'um bilhão ';
	} else if (listaDeExcecoes.hasOwnProperty(nBilhao)) { //se está na lista de exceções
		bilhao = listaDeExcecoes[nBilhao] + ' bilhões ';
	} else {
		let x = '0' + nBilhao[1] + nBilhao[2]; //exceção da dezena
		x = (listaDeExcecoes.hasOwnProperty(x)) ? listaDeExcecoes[x] : arrayDeReferencia.dezena[parseInt(nBilhao[1])] + arrayDeReferencia.unidade[parseInt(nBilhao[2])];
		bilhao = arrayDeReferencia.centena[parseInt(nBilhao[0])] + x + ' bilhões, ';
	}
	
	//montando a frase
	if (centavos) {
		if (reais || milhar || milhao || bilhao) {
			centavos = ' e ' + centavos;
		}
	}
	
	if (reais) {
		if (milhar || milhao || bilhao) {
			reais = (centavos ? ', ' : ' e ') + reais;
		}
	}
	
	if (milhar) {
		if (!reais) {
			milhar += ' reais';
		}
	}
	
	if (milhao) {
		if (!reais && !milhar) {
			milhao += ' de reais';
		}
	}
	
	if (bilhao) {
		if (!reais && !milhar && !milhao) {
			bilhao += ' de reais';
		}
	}
	
	console.debug('regras do bilhao: ' +  bilhao)
	console.debug('regras do milhao: ' + milhao)
	console.debug('regras do milhar: ' + milhar)
	console.debug('regras dos reais: ' + reais)
	console.debug('regras dos centavos: ' + centavos)
	
	let frase = bilhao + milhao + milhar + reais + centavos;
	frase = frase.replace(/\s{2,}/gm,' '); //exclui os espaços duplicados
	console.debug(valor + ": " + frase.trim());
	return frase.trim();
}

async function extrairNumeroProcesso(texto) {
	let padrao = /\d{7}\-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/g;
	let n = '';
	if (padrao.test(texto)) {
		n = texto.match(padrao).join();
	}	
	return n;
}

function decomporNumeroProcesso(numero) {
	return new Promise(
		resolver => {
			let campos = numero.replace(/\.|\-/g,'.').split('.');
			let reduzido = campos[0].replace(/^0+/, "") + '-' + campos[1] + '.' + campos[2];
			return resolver({
				'numero':campos[0],				
				'digito':campos[1],
				'ano':campos[2],
				'jurisdicao':campos[3],
				'regiao':campos[4],
				'vara':campos[5],
				'reduzido':reduzido,
			});
		}
	);
}