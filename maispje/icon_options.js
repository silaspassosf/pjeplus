var opcoes = {}
var itensModulo1SemAtalhos = getItensModulo1SemAtalhos(salvarOpcoes)
itensModulo1SemAtalhos.push(new ItemCheckboxMenu('gigsAbrirDetalhes', salvarOpcoes))

async function iniciar() {
	const opcoesHandler = await browser.storage.local.get(null);

	Promise.all([opcoesHandler]).then(result => {
		opcoes = result[0]
		mostrarOpcoes()
	});
}

function mostrarOpcoes() {

	browser.storage.local.get('concordo').then(function(result){
		if (!result.concordo) {
			document.getElementById('gigsLigarDesligar').setAttribute('disabled', 'true');
		}
	});

	const ligaDesliga = /** @type {HTMLInputElement} */ (document.getElementById('gigsLigarDesligar'));
	ligaDesliga.checked = opcoes.extensaoAtiva
	ligaDesliga.addEventListener('click', ligarDesligar)

	itensModulo1SemAtalhos.forEach(item => item.configurar(opcoes));

	document.getElementById('opcoes').addEventListener('click', configuracoes)

	document.getElementById("versao").innerText = "v. " + browser.runtime.getManifest().version;
	criarAtalhosPlugin();
	ligarDesligar();
}

async function salvarOpcoes() {
	const preferenciasUsuario = mergeItensMenu(itensModulo1SemAtalhos);
	await browser.storage.local.set(preferenciasUsuario);
}

function configuracoes() {
	browser.storage.local.get('concordo').then(async function(result){
		if (result.concordo) {
            await browser.runtime.sendMessage({tipo: 'abrirConfiguracoes'})
            window.close()
		}
	});
}

function criarAtalhosPlugin() {
	var ul = document.getElementById("atalhosPlugin");
	var arr1 = typeof(opcoes.atalhosPlugin) == "undefined" ? "" : opcoes.atalhosPlugin.split("|");
	for(var i = 0; i < arr1.length; i++ ){
		arr1[i] = arr1[i].replace(":", "|");
		var arr2 = arr1[i].split("|");
		var li = document.createElement("li");
		var a = document.createElement("a");

		let padraoEmoji = /^(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/;
		if (padraoEmoji.test(arr2[0])) {
			// console.log('entrou')
			let icone =  arr2[0].match(padraoEmoji)[0];
			arr2[0] = arr2[0].replace(icone,'');
			// console.log(icone)
			if (icone) {
				let ico = document.createElement("span");
				ico.textContent = icone;
				li.appendChild(ico);
			}
		}
		//COR DOS ATALHOS
		let listaDeCores = ['[azul]','[verde]','[vermelho]','[amarelo]'];
		let listaDeCoresHexadecimal = ['[#2778c4]','[#33c427]','[#c42727]','[#c4ab27]'];
		let cor = arr2[0];

		let padrao = /\[(.*?)\]/gm
		if (padrao.test(arr2[0])) {
			cor = arr2[0].match(padrao).join();
			arr2[0] = arr2[0].replace(cor,'');
			let pos = listaDeCores.indexOf(cor);
			cor = (pos > -1) ? listaDeCoresHexadecimal[pos] : cor;
			cor = cor.replace(/\[|\]/g,'');
			li.style.borderLeft = '3px solid ' + cor;
			li.style.backgroundImage = 'linear-gradient(to right, ' + cor + '4f , #e0e0e0)'
		}

		a.innerText = arr2[0];
		a.href = arr2[1];
		a.target = "_blank";
		li.appendChild(a);
		ul.appendChild(li);
	}
}

function ligarDesligar() {
	if (!document.getElementById('gigsLigarDesligar').checked) {
		let var1 = browser.storage.local.set({'AALote': ''});
		let var2 = browser.storage.local.set({'processo_memoria': ''});
		let var3 = browser.storage.local.set({'temp_expediente_especial': ''});
		let var4 = browser.storage.local.set({'tempAR': ''});
        let var5 = browser.storage.local.set({'tempBt': []});
		let var6 = browser.storage.local.set({'tempAAEspecial': []});
		let var7 = browser.storage.local.set({'anexadoDoctoEmSigilo': false});
		let var8 = browser.storage.local.set({'extensaoAtiva': false});
        let var9 = browser.storage.local.set({'clipboard': ''});
		Promise.all([var1,var2,var3,var4,var5,var6,var7,var8,var9]).then(values => {
			document.querySelector('span[class="slider round"]').textContent = "desligado";
			document.querySelector('span[class="slider round"]').style.color = "#545454";
			document.querySelectorAll('nav[class="categorias"]')[1].style.display = "none";
			document.querySelectorAll('nav[class="categorias"]')[2].style.display = "none";
			document.querySelectorAll('nav[class="categorias"]')[3].style.display = "none";
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
		});
	} else {
		browser.storage.local.set({extensaoAtiva : true}, function() {
			document.querySelector('span[class="slider round"]').textContent = "ligado";
			document.querySelector('span[class="slider round"]').style.color = "white";
			document.querySelectorAll('nav[class="categorias"]')[1].style.display = "flex";
			document.querySelectorAll('nav[class="categorias"]')[2].style.display = "flex";
			document.querySelectorAll('nav[class="categorias"]')[3].style.display = "flex";
			document.getElementById('atalhosPlugin').style.setProperty('overflow-y', 'scroll');
			if (!opcoes.trt || !opcoes.grau_usuario || !opcoes.versaoPje) {
				browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atenção', icone: 'ico_16_alerta.png'});
			} else {
				browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
			}
		});
	}
}

document.addEventListener("DOMContentLoaded", iniciar);

document.body.addEventListener('click', function(event) {
	if (event.target.className.includes('slider round') || event.target.id.includes('opcoes')) {
		browser.storage.local.get('concordo', function(result){
			if (!result.concordo) {
				browser.runtime.sendMessage({tipo: 'permissao', icone: '6'});
			}
		});
	}
});
