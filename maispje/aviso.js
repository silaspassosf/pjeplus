async function iniciar() {
	document.querySelector('#concordo').addEventListener('click', salvarOpcoes);
	document.querySelector('#naoconcordo').addEventListener('click', discordar);
}

async function salvarOpcoes() {
	let guardarStorage = browser.storage.local.set({'extensaoAtiva': true, 'concordo' : true });
	Promise.all([guardarStorage]).then(values => { 
		browser.runtime.sendMessage({tipo: 'abrirConfiguracoes'});
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
		setTimeout(function() {window.close()}, 1000);
	 });	
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