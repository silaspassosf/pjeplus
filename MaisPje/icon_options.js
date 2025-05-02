var opcoes = {}
var itensModulo1SemAtalhos = getItensModulo1SemAtalhos(salvarOpcoes)
itensModulo1SemAtalhos.push(new ItemCheckboxMenu('gigsAbrirDetalhes', salvarOpcoes))

async function iniciar() {
	opcoesHandler = await browser.storage.local.get(null);
	
	Promise.all([opcoesHandler]).then(result => {
		opcoes = result[0]
		mostrarOpcoes()
	});
}

function mostrarOpcoes() {
	
	browser.storage.local.get('concordo', function(result){
		if (!result.concordo) {
			document.getElementById('gigsLigarDesligar').setAttribute('disabled', true);
		}
	});
	
	document.getElementById('gigsLigarDesligar').checked = opcoes.extensaoAtiva
	document.getElementById('gigsLigarDesligar').addEventListener('click', ligarDesligar)
	
	itensModulo1SemAtalhos.forEach(item => item.configurar(opcoes));

	document.getElementById('opcoes').addEventListener('click', configuracoes)	
	
	document.getElementById("versao").innerText = "v. " + chrome.runtime.getManifest().version;
	criarAtalhosPlugin();
	ligarDesligar();
}

async function salvarOpcoes() {
	const preferenciasUsuario = mergeItensMenu(itensModulo1SemAtalhos);
	await browser.storage.local.set(preferenciasUsuario);
}

function configuracoes() {
	browser.storage.local.get('concordo', function(result){
		if (result.concordo) {
			window.close();
			return browser.runtime.sendMessage({tipo: 'abrirConfiguracoes'});
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

		// REMOVEU LOGICA DE COR
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
		Promise.all([var1,var2,var3,var4,var5,var6,var7,var8]).then(values => {
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
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
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
