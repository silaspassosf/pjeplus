async function exe15(){
	if(!JANELA.includes(LINK.tribunal.exe15.raiz)) return
	let processoNumero = obterUrlParametro('processo')
	let documento = obterUrlParametro('documento')
	let processo = obterDadosDoNumeroDoProcesso(processoNumero)
	let cnpj = obterCNPJ(documento)
	let cpf = obterCPF(documento)
	await esperar('[id="corpo:formulario:tipoOrdenacao"]',true,true)
	exe15PreencherDados()
	if(documento || processo?.ordenador) clicar('[id="corpo:formulario:botaoAcaoPesquisar"]')
	
	function exe15PreencherDados(){
		if(cpf){
			clicar('[id="corpo:formulario:tipoPessoaPesquisa:_0"]')
			preencher('[id="corpo:formulario:cpfPesquisa"]',cpf)
		}
		if(cnpj){
			clicar('[id="corpo:formulario:tipoPessoaPesquisa:_1"]')
			preencher('[id="corpo:formulario:cnpjPesquisa"]',cnpj)
		}
		if(processo?.ordenador){
			preencher('[id="corpo:formulario:numeroProc"]',processo.ordenador)
			preencher('[id="corpo:formulario:digitoProc"]',processo.digito)
			preencher('[id="corpo:formulario:anoProc"]',processo.ano)
			preencher('[id="corpo:formulario:origemProc"]',processo.origem)
		}
	}
}