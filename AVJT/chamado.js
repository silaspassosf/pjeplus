async function chamado(){
	if(!JANELA.includes(LINK.chamado)) return
	navigator.clipboard.readText().then(
		texto => {
			if(!texto) return
			let processo = obterNumeroDoProcessoPadraoCNJ(texto)
		}
	)
}


function chamadoAbrirPagina(processo=''){
	let pje = pjeObterContexto()
	let texto = ''
	if(pje){
		processo = PROCESSO?.numero || ''
		let tarefa = PROCESSO?.tarefa?.nomeTarefa || ''
		let orgao = PROCESSO?.orgaoJulgador?.descricao || ''
		let assinatura = CONFIGURACAO?.texto?.assinatura || ''
		texto =	'Erro: Processo ' + processo +
			'\n\nTarefa:\n' + tarefa +
			'\n\nÓrgão:\n' + orgao +
			'\n\nErro:\n' +
			'\n\nObservações:' +
			'\n\n\nSolicito suporte para o erro acima identificado.' +
			'\n\nAgradeço pela atenção.\n\n' +
			assinatura
	}
	copiar(processo+texto)
	let url = LINK.chamado
	abrirPagina(url,'','','','','chamado')
}