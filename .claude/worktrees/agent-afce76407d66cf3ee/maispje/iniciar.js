browser.storage.local.get(['extensaoAtiva','concordo','versaoPje'], async function(configuracoes){
	if (configuracoes.concordo) {
		if (configuracoes.extensaoAtiva) {
			if (document.location.href.includes('login.seam') || !configuracoes.versaoPje) {
				configuracoes.versaoPje = await verificarVersaoPje(configuracoes.versaoPje);
			}
			executarVersao(configuracoes.versaoPje);
		}
	} else {
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Desligado', icone: 'ico_16_off.png'});
	}
});

async function verificarVersaoPje(versaoAtual) {
	return new Promise(
		resolver => {
			if (document.location.href.includes('login.seam')) {
				let check = setInterval(function() {
					let ancora = document.querySelector('div[class*="versaoSistema"]') || document.getElementById('modulo-versao');
					if (ancora) {
						clearInterval(check);
						versaoAtual = guardarInformacoesBasicasDoUsuario(ancora.innerText);
						return resolver(versaoAtual);
					}
				}, 500);
			} else {
				return resolver('nenhum');
			}
		}
	);
}

function executarVersao(versao) {
	console.log('versao: ' + versao)
	window.addEventListener('afterprint', handleAssistenteDeImpressora); //ativa o assistente de impressão para os convênios que executam windows.print no load
	browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Atual/gigs-plugin.js'});
}

function guardarInformacoesBasicasDoUsuario(versaoAtual) {
	const trt = document.location.hostname;
	const path = document.location.pathname
	const partesPath = path.split('/', 2);
	let grauUsuario = partesPath[1] ?? 'não identificado';

	let var1 = browser.storage.local.set({
		'trt': trt,
		'grau_usuario': grauUsuario,
		'versaoPje': versaoAtual
	});

	Promise.all([var1]).then(values => {
		console.log("maisPJE: Dados Básicos do Usuário");
		console.log("    |____Url Padrão: " + trt);
		console.log("    |____Instância: " + grauUsuario);
		console.log("    |____Versão do PJe: " + versaoAtual);
		browser.runtime.sendMessage({tipo: 'iconeNavegador', valor: '+PJe: Atalho Rápido', icone: 'ico_16.png'});
		return versaoAtual;
	});
}

function handleAssistenteDeImpressora() {

	// //TESTE DA IMPRESSÃO DA PAGINA DO SNIPER
	let padrao = /(sniper.pdpj.jus.br\/investigacao-de-bens\/)(\d{4,})/g; //corresponde a impressão dos grafos e do relatório geral.. funciona automaticamente
	if (padrao.test(document.location.href)) {
		console.log('handleAssistenteDeImpressora')
		browser.storage.local.get('impressoraVirtual', function(result){
			let listapaginasTemp = result.impressoraVirtual;
			console.log(result.impressoraVirtual.length)

			if (result.impressoraVirtual.length > 0 && browser.tabs) {
				browser.tabs.create({ url: document.location.href });
				return
			}

			listapaginasTemp.push(document.body.innerHTML);
			let var2 = browser.storage.local.set({'impressoraVirtual': listapaginasTemp});
			Promise.all([var2]).then(values => {
				console.log("Nova Página adicionada à impressora virtual");
			});
		});
	}

}
