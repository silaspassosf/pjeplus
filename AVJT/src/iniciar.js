// Desenvolvido por:	Fernando Marcon e Sisenando Calixto
// E-mail:						sisenandosousa@trt15.jus.br


browser.storage.local.get(
	null,
	async (armazenamento) => {

		//publicas/definicoes.js
		EXTENSAO.ativada = armazenamento.ativada
		CONFIGURACAO = armazenamento

		otimizar()

	}
)


async function otimizar(){

	//publicas/definicoes.js
	if(!EXTENSAO.ativada) return

	//publicas/definicoes.js
	definicoesGlobais()

	//ad-hoc.js
	adHoc()
	
	//selecao.js
	assistenteDeSelecao()
	
	//pje/pje.js
	pje()
	
	//exe15.js
	exe15()
}

