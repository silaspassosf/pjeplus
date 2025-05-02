var opcoes = {};
async function iniciar() {
	opcoesHandler = await browser.storage.local.get(null);
	Promise.all([opcoesHandler]).then(result => {
		opcoes = result[0];
		checarVariaveis();
	});
}

function checarVariaveis() {
	opcoes.concordo = typeof(opcoes.concordo) == "undefined" ? false : opcoes.concordo;	
	document.querySelector('#concordo').checked = opcoes.concordo;
	document.querySelector('#concordo').addEventListener('click', salvarOpcoes);
	
	document.querySelector('#naoconcordo').checked = false;
	document.querySelector('#naoconcordo').addEventListener('click', discordar);
}

async function salvarOpcoes() {
	console.log("salvando...");
	browser.storage.local.set({
		concordo : true
	}, function() {
		acao1();
	});
	
	function acao1() {
		browser.storage.local.set({extensaoAtiva : true}, function() {
			browser.runtime.sendMessage({tipo: 'abrirConfiguracoes'});
			browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
			acao2();
		});
	}
	
	function acao2() {
		const Toast = Swal.mixin({
			toast: true,
			position: 'bottom-end',
			showConfirmButton: false,
			timer: 1500,
			timerProgressBar: true,
			onOpen: (toast) => {
			toast.addEventListener('mouseenter', Swal.stopTimer)
			toast.addEventListener('mouseleave', Swal.resumeTimer)
			}
		})

		Toast.fire({
			icon: 'success',
			title: 'Informações salvas com sucesso!'
		})
		
		setTimeout(function() {window.close()}, 1000);
	}
}

function discordar() {
	function onCanceled(error) {
		console.debug("Canceled: " + error);
	}
	
	alert("Infelizmente a extensão não funciona sem a coleta de dados da tela do usuário. \n\n Mas fique tranquilo que ela será desinstalada automaticamente.");
	
	let uninstalling = browser.management.uninstallSelf({
		showConfirmDialog: true
	});
	
	uninstalling.then(null, onCanceled);
}


iniciar();