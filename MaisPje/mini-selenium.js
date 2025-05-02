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
	} else if (texto.includes('[ou]')) { //tem que ser a expressão exata.. sem estar incluída no texto
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
		style.textContent += '.pjextension_executando {animation: animacao 1s infinite;animation-fill-mode: both;}';
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