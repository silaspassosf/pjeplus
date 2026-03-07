browser.storage.local.get(['extensaoAtiva','concordo','versaoPje'], function(configuracoes){
	if (configuracoes.concordo) {
		if (configuracoes.extensaoAtiva) {			
			browser.runtime.sendMessage({tipo: 'abrirOpcoes', script: './PJe-Atual/options.html'});
			setTimeout(function() {window.close()}, 1000);
		}
	} else {
		browser.runtime.sendMessage({tipo: 'permissao', icone: '6'});
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
	}
});