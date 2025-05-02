browser.storage.local.get(['extensaoAtiva','concordo','versaoPje'], function(configuracoes){
	if (configuracoes.concordo) {
		if (configuracoes.extensaoAtiva) {			
			let versao = verificarVersaoPje(configuracoes.versaoPje);
			
			//VERIFICAR A VERSÃO DO PJE para executar o script adequado
			if (!versao) {
				browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Atual/options.html'});
			} else if (versao.includes("IMBIRUÇU")) {
				browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Old/options.html'});
			} else if (versao.includes("ANGICO")) {
				browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Old/options.html'});
			} else if (versao.includes("FLAMBOIÃ")) {
		
				if (['2.11.1 - FLAMBOIÃ','2.11.2 - FLAMBOIÃ','2.11.3 - FLAMBOIÃ'].includes(versao)) {
					browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Old/options.html'});
				} else {
					browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Atual/options.html'});
				}
				
			} else { //se nenhuma versão foi identificada roda a última versão lançada
				browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Atual/options.html'});			
			}
			setTimeout(function() {window.close()}, 1000);
		}
	} else {
		browser.runtime.sendMessage({tipo: 'permissao', icone: '6'});
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
	}
});

function verificarVersaoPje(versaoAtual) {
	if (document.location.href.includes('login.seam')) {
		let check = setInterval(function() {
			if (document.querySelector('div[class*="versaoSistema"]')) {
				clearInterval(check);
				let versao = document.querySelector('div[class*="versaoSistema"]').innerText;
				browser.storage.local.set({'versaoPje': versao});
				return 'nenhum';
			}
		}, 100);
		
		//DESCRIÇÃO: identifica qual o grau de jurisdição do usuário
		if (document.location.href.includes('jus.br/primeirograu')) {
			browser.storage.local.set({'grau_usuario': 'primeirograu'});
		} else if (document.location.href.includes('jus.br/segundograu')) {
			browser.storage.local.set({'grau_usuario': 'segundograu'});
		}
	} else {
		return 'nenhum';
	}
}