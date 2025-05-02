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
	if (!versao) {
		browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Atual/gigs-plugin.js'});
	} else if (versao.includes("IMBIRUÇU")) {
		browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Old/gigs-plugin.js'});
	} else if (versao.includes("ANGICO")) {
		browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Old/gigs-plugin.js'});
	} else if (versao.includes("FLAMBOIÃ")) {

		if (['2.11.1 - FLAMBOIÃ','2.11.2 - FLAMBOIÃ','2.11.3 - FLAMBOIÃ'].includes(versao)) {
			browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Old/gigs-plugin.js'});
		} else {
			browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Atual/gigs-plugin.js'});
		}
		
	} else { //se nenhuma versão foi identificada roda a última versão lançada
		browser.runtime.sendMessage({tipo: 'iniciar', script: './PJe-Atual/gigs-plugin.js'});
	}
}

function guardarInformacoesBasicasDoUsuario(versaoAtual) {
	const trt = document.location.hostname;
	const path = document.location.pathname
	const partesPath = path.split('/', 2); // [ "", "primeirograu", "login.seam" ], o 2 pega so ate o grau, que eh o que precisamos.
	let grauUsuario = partesPath[1] ?? 'não identificado';
	// let ignorarProtocolo = document.location.href.includes('https:') ? 8 : 7;
	// let trt = document.location.href.substring(ignorarProtocolo,document.location.href.search(".jus.br")+7);
	// let configURLs = await obterUrlTribunais(trt);

	// let grauUsuario = 'não identificado';
	// if (document.location.href.includes('jus.br/primeirograu')) {
	// 	grauUsuario = 'primeirograu';
	// } else if (document.location.href.includes('jus.br/segundograu')) {
	// 	grauUsuario = 'segundograu';
	// } else if (document.location.href.includes('jus.br/tst')) { //TODO: como fica o TST? perguntar pra Marcon se pode assim
	// 	grauUsuario = 'tst';
	// } 
	
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
		return versaoAtual;
	});	
}

function obterUrlTribunais(numTrt) { //TODO: Aparentemente ha uma duplicacao aqui e no configURLs.json
	let padraoInicial = /trt\d{1,2}/; //eliminar urls que possuem numero. por exemplo: https://pjehom2.trt12.jus.br
	let padrao = /\d{1,2}/;
	if (padraoInicial.test(numTrt)) {
		numTrt = numTrt.match(padraoInicial).join();
		if (padrao.test(numTrt)) {
			numTrt = numTrt.match(padrao).join();
		} else {
			numTrt = '-1';
		}
	}
	
	//TODO: parece duplicado com o o configURLs.json.
	switch (parseInt(numTrt)) {		
		case 1:
			return {
				descricao:"Tribunal Regional do Trabalho da 1a Região",
				urlSiscondj:"https://pje.trt1.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 2:
			return {
				descricao:"Tribunal Regional do Trabalho da 2a Região",
				urlSiscondj:"https://alvaraeletronico.trt2.jus.br/portaltrtsp",
				idSiscondj:"alvaraeletronico",
				urlSAOExecucao:"Nenhum"
			};
		case 3:
			return {
				descricao:"Tribunal Regional do Trabalho da 3a Região",
				urlSiscondj:"https://siscondj.trt3.jus.br/portaltrtmg",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/T121?maisPje=true"
			};
		case 4:
			return {
				descricao:"Tribunal Regional do Trabalho da 4a Região",
				urlSiscondj:"https://siscondj.trt4.jus.br/portaltrtrs",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 5:
			return {
				descricao:"Tribunal Regional do Trabalho da 5a Região",
				urlSiscondj:"https://siscondj.trt5.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 6:
			return {
				descricao:"Tribunal Regional do Trabalho da 6a Região",
				urlSiscondj:"https://apps3.trt6.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/MP01?maisPje=true"
			};
		case 7:
			return {
				descricao:"Tribunal Regional do Trabalho da 7a Região",
				urlSiscondj:"https://pje.trt7.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/PCCF?maisPje=true"
			};
		case 8:
			return {
				descricao:"Tribunal Regional do Trabalho da 8a Região",
				urlSiscondj:"https://siscondj.trt8.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 9:
			return {
				descricao:"Tribunal Regional do Trabalho da 9a Região",
				urlSiscondj:"https://www.trt9.jus.br/siscondjtrtpr",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 10:
			return {
				descricao:"Tribunal Regional do Trabalho da 10a Região",
				urlSiscondj:"https://siscondj.trt10.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
		case 11:
			return {
				descricao:"Tribunal Regional do Trabalho da 11a Região",
				urlSiscondj:"https://pje.trt11.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/VT99?maisPje=true"
			};
		case 12:
			return {
				descricao:"Tribunal Regional do Trabalho da 12a Região",
				urlSiscondj:"https://siscondj.trt12.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/T125?maisPje=true"
			};
		case 13:
			return {
				descricao:"Tribunal Regional do Trabalho da 13a Região",
				urlSiscondj:"https://siscondj.trt13.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/MP01?maisPje=true"
			};
			
		case 14:
			return {
				descricao:"Tribunal Regional do Trabalho da 14a Região",
				urlSiscondj:"https://pje.trt14.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 15:
			return {
				descricao:"Tribunal Regional do Trabalho da 15a Região",
				urlSiscondj:"https://siscondj.trt15.jus.br/portaltrt15",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 16:
			return {
				descricao:"Tribunal Regional do Trabalho da 16a Região",
				urlSiscondj:"https://pje.trt16.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 17:
			return {
				descricao:"Tribunal Regional do Trabalho da 17a Região",
				urlSiscondj:"https://siscondj.trt17.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 18:
			return {
				descricao:"Tribunal Regional do Trabalho da 18a Região",
				urlSiscondj:"https://pje.trt18.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/L922?maisPje=true"
			};
			
		case 19:
			return {
				descricao:"Tribunal Regional do Trabalho da 19a Região",
				urlSiscondj:"https://siscondj.trt19.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 20:
			return {
				descricao:"Tribunal Regional do Trabalho da 20a Região",
				urlSiscondj:"https://siscondj.trt20.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 21:
			return {
				descricao:"Tribunal Regional do Trabalho da 21a Região",
				urlSiscondj:"https://siscondj.trt21.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"/sao/execucao/MP01?maisPje=true"
			};
			
		case 22:
			return {
				descricao:"Tribunal Regional do Trabalho da 22a Região",
				urlSiscondj:"https://aplicacoes.trt22.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 23:
			return {
				descricao:"Tribunal Regional do Trabalho da 23a Região",
				urlSiscondj:"https://solucoes.trt23.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		case 24:
			return {
				descricao:"Tribunal Regional do Trabalho da 24a Região",
				urlSiscondj:"https://siscondj.trt24.jus.br/siscondj",
				idSiscondj:"siscondj",
				urlSAOExecucao:"Nenhum"
			};
			
		default:
			return {
				descricao:"ERRO",
				urlSiscondj:"ERRO",
				idSiscondj: "ERRO",
				urlSAOExecucao:"ERRO"
			};
			
	}
}
