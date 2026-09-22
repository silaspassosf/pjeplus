//FUNÇÃO RESPONSÁVEL POR CRIAR O KAIZEN COM ATALHOS
function kaizen(nome_janela) {
	if (!document.getElementById('maisPje_menuKaizen')) {
		//criar estrutura do menuConvenios
		let menuMaisPje = document.createElement("menumaispje");
		// menuMaisPje.setAttribute('aria-live','polite'); //***
		menuMaisPje.id = "maisPje_menuKaizen";
		menuMaisPje.draggable = true;

		let menuMaisPje_content = document.createElement("div");
		menuMaisPje_content.id = "maisPje_menuKaizen_content";
		menuMaisPje_content.style = "border-radius: 100px;";
		menuMaisPje_content.className = "menuMaisPje-content";

		let toggle_btn = document.createElement("button");
		toggle_btn.className = "toggle-btn";
		toggle_btn.accessKey = "+";
		let img = document.createElement("img");
		img.title = 'menu kaizen maisPJE';
		img.alt = 'menu kaizen maisPJE';
		img.draggable = false;
		img.className = "maisPje-img";
		img.src = browser.runtime.getURL("icons/ico_32.png");
		toggle_btn.appendChild(img);

		let divStatus = document.createElement("i");
		divStatus.id = 'menuMaisPje_status';
		divStatus.style.display = "none";

		let infoStatus1 = document.createElement("i");
		infoStatus1.style = 'position: absolute;width: 60%;height: 60%;background-color: #0e2431;border-radius: 25px;';
		divStatus.appendChild(infoStatus1);

		let infoStatus2 = document.createElement("i");
		infoStatus2.className = 'fan-solid maisPje-spin';
		infoStatus2.style = 'position: absolute;width: 70%;height: 70%;background-color: #00c1ff;';
		divStatus.appendChild(infoStatus2);

		toggle_btn.appendChild(divStatus);

		menuMaisPje_content.appendChild(toggle_btn);
		menuMaisPje.appendChild(menuMaisPje_content);

		bt_atalhos();

		//posição inicial do menu
		browser.storage.local.get('menu_kaizen', function(result){
			let temp = result.menu_kaizen;
			if (!temp) { return }
			switch(nome_janela) {
				case "PRINCIPAL":
					menuMaisPje.style.left = result.menu_kaizen.principal.posx;
					menuMaisPje.style.top = result.menu_kaizen.principal.posy;
					break;
				case "DETALHES":
					menuMaisPje.style.left = result.menu_kaizen.detalhes.posx;
					menuMaisPje.style.top = result.menu_kaizen.detalhes.posy;
					break;
				case "TAREFAS":
					menuMaisPje.style.left = result.menu_kaizen.tarefas.posx;
					menuMaisPje.style.top = result.menu_kaizen.tarefas.posy;
					break;
			}
            console.debug('posicao menu kaizen', menuMaisPje.style.left, menuMaisPje.style.top)
            if (!menuMaisPje.style.left.includes('%') && !menuMaisPje.style.top.includes('%')) {
                let posX = parseFloat(menuMaisPje.style.left);
                let posY = parseFloat(menuMaisPje.style.top);

                const windowWidth = window.innerWidth;
                const windowHeight = window.innerHeight;

                if (posX < 0 || posX > windowWidth) posX = 0;
                if (posY < 0 || posY > windowHeight) posY = 0;
                // volta para o padrao se ficou fora da tela.
                menuMaisPje.style.left = posX === 0 ? '96%' : posX + "px";
                menuMaisPje.style.top =  posY === 0 ? '92%' : posY + "px";
			}
			setTimeout(function() {direcaoItensMenu()}, 500);
		});

		document.body.appendChild(menuMaisPje);

		//cria o eventlistener
		let posx,posy;

		//área de drop
		let area_da_tela = document.createElement('div');
		area_da_tela.id = "maisPje_menuKaizen_area_da_tela";
		area_da_tela.style="width: 100%;height: 100%;z-index: 999;position: absolute; display: none;top: 0px;"
		area_da_tela.ondragover = function(e) {
			e.preventDefault();
			e.dataTransfer.dropEffect = "move";
			posx = e.clientX;
			posy = e.clientY;
		}
		area_da_tela.ondrop = function(e) {  e.preventDefault();}
		document.body.appendChild(area_da_tela);

		menuMaisPje.ondragstart = function() {
			area_da_tela.style.display = "flex";
		}

		menuMaisPje.ondragend = function(e) {
			area_da_tela.style.display = "none";
			menuMaisPje.style.top = (posy - 12) + "px";
			menuMaisPje.style.left = (posx - 12) + "px";
			direcaoItensMenu();
			let posmenu = window.getComputedStyle(document.querySelector("menumaispje"));
			browser.storage.local.get('menu_kaizen', function(result){
				let temp = result.menu_kaizen;
				if (!temp) { return }
				switch(nome_janela) {
					case "PRINCIPAL":
						temp.principal.posx = parseInt(posmenu.left) + 'px';
						temp.principal.posy = parseInt(posmenu.top) + 'px';
						break;
					case "DETALHES":
						temp.detalhes.posx = parseInt(posmenu.left) + 'px';
						temp.detalhes.posy = parseInt(posmenu.top) + 'px';
						break;
					case "TAREFAS":
						temp.tarefas.posx = parseInt(posmenu.left) + 'px';
						temp.tarefas.posy = parseInt(posmenu.top) + 'px';
						break;
				}
				browser.storage.local.set({'menu_kaizen': temp});
			});
		}

		function direcaoItensMenu() {
			//DESCRIÇÃO: REGRA DO TOOLTIP
			let faixaLimiteDaTela,posicaoDoMenuEmPixels;
			if (preferencias.kaizenNaHorizontal) {
				faixaLimiteDaTela = parseInt(window.innerHeight) * 0.04; //left 4vw... distancia convertida em pixels
				posicaoDoMenuEmPixels = menuMaisPje.style.top.replace('px','');
				// console.log(posicaoDoMenuEmPixels + " > " + faixaLimiteDaTela);
				if (parseInt(posicaoDoMenuEmPixels) > parseInt(faixaLimiteDaTela)) {
					if (!document.getElementById('maisPje_tooltip_menuAcima')) { tooltip('menuAcima') }
				} else {
					if (!document.getElementById('maisPje_tooltip_menuAbaixo')) { tooltip('menuAbaixo') }
				}
			} else {
				faixaLimiteDaTela = parseInt(window.innerWidth) * 0.05; //top 5vh... distancia convertida em pixels
				posicaoDoMenuEmPixels = menuMaisPje.style.left.replace('px','');
				// console.log(posicaoDoMenuEmPixels + " > " + faixaLimiteDaTela);
				if (parseInt(posicaoDoMenuEmPixels) > parseInt(faixaLimiteDaTela)) {
					if (!document.getElementById('maisPje_tooltip_menuEsquerda')) { tooltip('menuEsquerda') }
				} else {
					if (!document.getElementById('maisPje_tooltip_menuDireita')) { tooltip('menuDireita') }
				}

			}


			if (preferencias.kaizenNaHorizontal) {
				//o menu possui 390px de altura (30px por atalho)
				if (parseInt(window.getComputedStyle(menuMaisPje).left) < parseInt(window.innerWidth/2)) {//menu estiver na metade superior
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu,
						function(itemmenu) {
							itemmenu.style.setProperty("--d","1")
						}
					);
				} else {//menu estiver na metade horizontal
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu,
						function(itemmenu) {
							itemmenu.style.setProperty("--d","-1")
						}
					);
				}
			} else {
				//o menu possui 390px de altura (30px por atalho)
				if (parseInt(window.getComputedStyle(menuMaisPje).top) < parseInt(window.innerHeight/2)) {//menu estiver na metade superior
					//menu abre para baixo
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu,
						function(itemmenu) {
							itemmenu.style.setProperty("--d","1")
						}
					);
				} else {//menu estiver na metade superior
					//menu abre para cima
					let itensmenu = document.querySelectorAll('span[id*="maisPje_menuKaizen_itemmenu_"]');
					if (!itensmenu) { return }
					let map = [].map.call(
						itensmenu,
						function(itemmenu) {
							itemmenu.style.setProperty("--d","-1")
						}
					);
				}
			}

		}

		// console.log("preferencias.acionarKaizenComClique: " + preferencias.acionarKaizenComClique);
		const acionarMenuMaisPJe = (e) =>{
            direcao = preferencias.kaizenNaHorizontal ? "openh" : "openv";
            menuMaisPje.classList.toggle(direcao);
		};

		toggle_btn.addEventListener("click", acionarMenuMaisPJe);
        toggle_btn.addEventListener("dblclick", (e) => {
            if (e.getModifierState("Control")) {
                console.log(preferencias.modoLGPD);
                preferencias.modoLGPD = (preferencias.modoLGPD) ? false : true;
                ativarLGPD(preferencias.modoLGPD);
            }
         });
		// toggle_btn.addEventListener( "click", guardarOJdoUsuario);
		if (!preferencias.acionarKaizenComClique) { //se nao quer acionar com clique, aciona com mouseover
			toggle_btn.addEventListener( "mouseenter", acionarMenuMaisPJe);
		}

		async function bt_atalhos() {
			let posicao_itemmenu = 1;
			await sleep(1000); //comando para aguardar o carregamento de eventuais elementos condicionantes
			const atalhos = getAtalhosNovaAba();
			Object.values(atalhos).forEach(atalho => {
				if (atalho.condicao_adicionar()) {
					const botao = atalho.criar_botao(posicao_itemmenu++);
                    if (!preferencias.acionarKaizenComClique) { acionarCliqueRapido(botao) }
                    menuMaisPje_content.appendChild(botao);
				}
			});
		}

		//Se existir atalho na função F2 criar uma área de ação no canto inferior esquerdo da tela
		//se o usuário repousar o mouse ali em cima por 3 segundos, acionará a função F2 sem precisar usar o teclado
		criarAreaDoPreferenciasF2();
		criarAreaDoPreferenciasF3();
		criarAreaDoPreferenciasF4();
        criarAreaDoPreferenciasF6();
        criarAreaDoPreferenciasF7();
        criarAreaDoPreferenciasF8();
	}
}

//criar area do preferencias.F2
function criarAreaDoPreferenciasF2() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF2')) { return } //já tem a área definida?
	if (!preferencias.tempF2 || preferencias.tempF2 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF2";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF2] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF2]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF2); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF2]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF2 = document.createElement('div');
	containerAreaDeAtalhoF2.id = 'maisPje_ContainerAreaDeAtalhoF2';
	containerAreaDeAtalhoF2.style = 'position: absolute; top: 83vh; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 1vw; align-content: center;';
    containerAreaDeAtalhoF2.setAttribute('maisPje_tooltip_areaDeAtalhoF2',preferencias.tempF2);

	let areaDeAtalhoF2 = document.createElement('a');
    areaDeAtalhoF2.id = 'maisPje_areaDeAtalhoF2';
	areaDeAtalhoF2.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: rgb(28, 85, 54); border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; color: rgba(60, 179, 113, 0.65); box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; --color1: black; --color2: #1c5536; display: block; margin: 3vh auto;";
	areaDeAtalhoF2.setAttribute('aria-label', preferencias.tempF2);
	areaDeAtalhoF2.innerText = "F2";
	areaDeAtalhoF2.href = '#';
    areaDeAtalhoF2.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF2);
	}
	acionarSemClique(areaDeAtalhoF2,'black','#1c5536',preferencias.atalhosDelay);

	containerAreaDeAtalhoF2.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	};
	containerAreaDeAtalhoF2.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' };

	containerAreaDeAtalhoF2.appendChild(areaDeAtalhoF2);
	document.body.appendChild(containerAreaDeAtalhoF2);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF2.style.animation  = 'descer .5s 1 forwards';

	//se existe AA nele mudar a cor do botão
	if (document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f2')) { document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f2').firstChild.style.backgroundColor = 'rgb(47, 138, 88)' }

}

//criar area do preferencias.F3
function criarAreaDoPreferenciasF3() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF3')) { return } //já tem a área definida?
	if (!preferencias.tempF3 || preferencias.tempF3 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF3";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF3] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF3]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF3); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF3]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF3 = document.createElement('div');
	containerAreaDeAtalhoF3.id = 'maisPje_ContainerAreaDeAtalhoF3';
    containerAreaDeAtalhoF3.style = 'position: absolute; top: 83vh; left: 8vw; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 2vw; align-content: center;';
    containerAreaDeAtalhoF3.setAttribute('maisPje_tooltip_areaDeAtalhoF3',preferencias.tempF3);

	let areaDeAtalhoF3 = document.createElement('a');
	areaDeAtalhoF3.id = 'maisPje_areaDeAtalhoF3';
    areaDeAtalhoF3.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: #681d01; border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; color: rgba(255, 99, 71, 0.65); box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; --color1: black; --color2: #1c5536; display: block; margin: 3vh auto;"
	areaDeAtalhoF3.setAttribute('aria-label', preferencias.tempF3);
	areaDeAtalhoF3.innerText = "F3";
    areaDeAtalhoF3.href = '#';
    areaDeAtalhoF3.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF3);
	}
	acionarSemClique(areaDeAtalhoF3,'black','#681d01',preferencias.atalhosDelay);

	containerAreaDeAtalhoF3.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	};
	containerAreaDeAtalhoF3.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' };

	containerAreaDeAtalhoF3.appendChild(areaDeAtalhoF3);
	document.body.appendChild(containerAreaDeAtalhoF3);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF3.style.animation  = 'descer .5s 1 forwards';
	//se existe AA nele mudar a cor do botão
	if (document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f3')) { document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f3').firstChild.style.backgroundColor = 'rgb(159, 56, 18)' }
}

//criar area do preferencias.F4
function criarAreaDoPreferenciasF4() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF4')) { return } //já tem a área definida?
	if (!preferencias.tempF4 || preferencias.tempF4 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF4";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF4] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF4]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF4); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF4]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF4 = document.createElement('div');
	containerAreaDeAtalhoF4.id = 'maisPje_ContainerAreaDeAtalhoF4';
    containerAreaDeAtalhoF4.style = 'position: absolute; top: 83vh; left: 16vw; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 3vw; align-content: center;';
    containerAreaDeAtalhoF4.setAttribute('maisPje_tooltip_areaDeAtalhoF4',preferencias.tempF4);

    let areaDeAtalhoF4 = document.createElement('a');
	areaDeAtalhoF4.id = 'maisPje_areaDeAtalhoF4';
    areaDeAtalhoF4.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: #03629b; border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; color: rgba(1, 147, 234, 0.65); box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; --color1: black; --color2: #1c5536; display: block; margin: 3vh auto;"
	areaDeAtalhoF4.setAttribute('aria-label', preferencias.tempF4);
	areaDeAtalhoF4.innerText = "F4";
    areaDeAtalhoF4.href = '#';
    areaDeAtalhoF4.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF4);
	}
    acionarSemClique(areaDeAtalhoF4,'black','#03629b',preferencias.atalhosDelay);

	containerAreaDeAtalhoF4.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	};
	containerAreaDeAtalhoF4.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' };

	containerAreaDeAtalhoF4.appendChild(areaDeAtalhoF4);
	document.body.appendChild(containerAreaDeAtalhoF4);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF4.style.animation  = 'descer .5s 1 forwards';
	//se existe AA nele mudar a cor do botão
	if (document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f4')) { document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f4').firstChild.style.backgroundColor = 'rgb(15, 131, 200)' }
}

//criar area do preferencias.F6
function criarAreaDoPreferenciasF6() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF6')) { return } //já tem a área definida?
	if (!preferencias.tempF6 || preferencias.tempF6 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF6";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF6] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF6]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF6); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF6]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF6 = document.createElement('div');
	containerAreaDeAtalhoF6.id = 'maisPje_ContainerAreaDeAtalhoF6';
	containerAreaDeAtalhoF6.style = 'position: absolute; top: 83vh; left: 24vw; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 4vw; align-content: center;';
    containerAreaDeAtalhoF6.setAttribute('maisPje_tooltip_areaDeAtalhoF6',preferencias.tempF6);

	let areaDeAtalhoF6 = document.createElement('a');
    areaDeAtalhoF6.id = 'maisPje_areaDeAtalhoF6';
	areaDeAtalhoF6.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: rgb(138, 131, 35); color: rgba(223, 193, 38, 0.65); --color1: black; --color2: #8a8323; border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; display: block; margin: 3vh auto;";
	areaDeAtalhoF6.setAttribute('aria-label', preferencias.tempF6);
	areaDeAtalhoF6.innerText = "F6";
	areaDeAtalhoF6.href = '#';
    areaDeAtalhoF6.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF6);
	}
	acionarSemClique(areaDeAtalhoF6,'black','#8a8323',preferencias.atalhosDelay);

	containerAreaDeAtalhoF6.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	};
	containerAreaDeAtalhoF6.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' };

	containerAreaDeAtalhoF6.appendChild(areaDeAtalhoF6);
	document.body.appendChild(containerAreaDeAtalhoF6);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF6.style.animation  = 'descer .5s 1 forwards';
}

//criar area do preferencias.F7
function criarAreaDoPreferenciasF7() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF7')) { return } //já tem a área definida?
	if (!preferencias.tempF7 || preferencias.tempF7 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF7";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF7] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF7]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF7); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF7]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF7 = document.createElement('div');
	containerAreaDeAtalhoF7.id = 'maisPje_ContainerAreaDeAtalhoF7';
	containerAreaDeAtalhoF7.style = 'position: absolute; top: 83vh; left: 32vw; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 5vw; align-content: center;';
    containerAreaDeAtalhoF7.setAttribute('maisPje_tooltip_areaDeAtalhoF7',preferencias.tempF7);

	let areaDeAtalhoF7 = document.createElement('a');
    areaDeAtalhoF7.id = 'maisPje_areaDeAtalhoF7';
	areaDeAtalhoF7.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: rgb(85, 28, 71); color: rgba(179, 60, 144, 0.65); --color1: black; --color2: #551947; border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; display: block; margin: 3vh auto;";
	areaDeAtalhoF7.setAttribute('aria-label', preferencias.tempF7);
	areaDeAtalhoF7.innerText = "F7";
	areaDeAtalhoF7.href = '#';
    areaDeAtalhoF7.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF7);
	}
	acionarSemClique(areaDeAtalhoF7,'black','#551947',preferencias.atalhosDelay);

	containerAreaDeAtalhoF7.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	};
	containerAreaDeAtalhoF7.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' };

	containerAreaDeAtalhoF7.appendChild(areaDeAtalhoF7);
	document.body.appendChild(containerAreaDeAtalhoF7);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF7.style.animation  = 'descer .5s 1 forwards';
}

//criar area do preferencias.F8
function criarAreaDoPreferenciasF8() {
	if (!(document.location.href.includes('.jus.br/pjekz/') && document.location.href.includes("/detalhe"))) { return }	//tá na Janela Detalhes?
	if (document.getElementById('maisPje_areaDeAtalhoF8')) { return } //já tem a área definida?
	if (!preferencias.tempF8 || preferencias.tempF8 == 'Nenhum') { return } //existe AA atrelada?

    let style = document.createElement("style");
	style.id = "maisPje_tooltip_areaDeAtalhoF8";
	style.textContent = '[maisPje_tooltip_areaDeAtalhoF8] {position: relative; display: inline-block; cursor: pointer; min-height: 2rem;}';
	style.textContent += '[maisPje_tooltip_areaDeAtalhoF8]:before {';
    style.textContent += 'content: attr(maisPje_tooltip_areaDeAtalhoF8); position: absolute; pointer-events: none; white-space: nowrap;';
    style.textContent += 'z-index: 100000; text-decoration: none; font-family: "NunitoSans Regular", "Arial", sans-serif; font-size: .6vw;';
    style.textContent += 'align-content: center; text-shadow: none; font-weight: 500; background: white; opacity: 1; color: black; border-radius: 5px;';
    style.textContent += 'padding: 5px; display:none; border: 1px dashed black; margin: -5vh 1vw; width: -moz-available; text-align: center; overflow-wrap: break-word;';
    style.textContent += 'white-space: break-spaces; min-height: 4vh; max-height: 4vh;}';
    style.textContent += '[maisPje_tooltip_areaDeAtalhoF8]:hover:before {display: inline-block;}';
    document.body.appendChild(style);

	let containerAreaDeAtalhoF8 = document.createElement('div');
	containerAreaDeAtalhoF8.id = 'maisPje_ContainerAreaDeAtalhoF8';
	containerAreaDeAtalhoF8.style = 'position: absolute; top: 83vh; left: 40vw; z-index: 1; display: block; animation: 0.5s forwards descer; width: 8vw; height: 8vw; margin-left: 6vw; align-content: center;';
    containerAreaDeAtalhoF8.setAttribute('maisPje_tooltip_areaDeAtalhoF8',preferencias.tempF8);

	let areaDeAtalhoF8 = document.createElement('a');
    areaDeAtalhoF8.id = 'maisPje_areaDeAtalhoF8';
	areaDeAtalhoF8.style = "text-decoration-line: none; width: 6vw; height: 6vw; background-color: rgb(73, 72, 72); color: rgba(175, 175, 175, 0.65); --color1: black; --color2: #494848; border-radius: 5px; font-weight: bold; outline: white solid 1vw; cursor: pointer; animation: unset; font-size: 4vw; text-align: center; align-content: space-between; box-shadow: rgb(0, 0, 0) 0px 0px 80px, rgb(0, 0, 0) 0px 0px 60px, rgb(0, 0, 0) 0px 0px 0px, rgba(4, 4, 4, 0) 0px 0px 100px; display: block; margin: 3vh auto;";
	areaDeAtalhoF8.setAttribute('aria-label', preferencias.tempF8);
	areaDeAtalhoF8.innerText = "F8";
	areaDeAtalhoF8.href = '#';
    areaDeAtalhoF8.onclick = (event) => {
        event.preventDefault();
		acao_vinculo(preferencias.tempF8);
	}
	acionarSemClique(areaDeAtalhoF8,'black','#494848',preferencias.atalhosDelay); //aciona o botão

	containerAreaDeAtalhoF8.onmouseenter = function () { this.style.animation  = 'subir .5s 1 forwards'	}; //faz o botão subir
	containerAreaDeAtalhoF8.onmouseleave = function () { this.style.animation  = 'descer .5s 1 forwards' }; //faz o botão descer

	containerAreaDeAtalhoF8.appendChild(areaDeAtalhoF8);
	document.body.appendChild(containerAreaDeAtalhoF8);
	document.body.style.overflowY = 'hidden';

	containerAreaDeAtalhoF8.style.animation  = 'descer .5s 1 forwards';
}
