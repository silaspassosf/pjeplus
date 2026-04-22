function infojud(){
	if(!JANELA.includes(LINK.infojud.dominio)) return
	solicitar()

	function solicitar(){
		if(!JANELA.includes(LINK.infojud.solicitar)) return
		let vara = obterParametroDeUrl('vara')
		let documento = obterParametroDeUrl('novocpfcnpj')
		let cpf = (documento.length === 11)
		let doi = {}
		doi.inicio = '01/1980'
		doi.fim = DATA.mesAnterior.primeiroDia.replace(/^.../,'')
		selecionarOpcao('#tipoProcesso','Ação Trabalhista')
		if(!vara) return
		selecionarOpcao('#siglavara',vara)
		preencherDoi()
		preencherDitr()

		function preencherDirpf(){
			if(!cpf) return
			let lista = selecionar('#novotipo')
			if(!lista) return
			let selecionada = lista.options[lista.selectedIndex].innerText || ''
			if(!selecionada?.includes('DIRPF')) selecionarOpcao('#novotipo','DIRPF')
		}

		function preencherDitr(){
			let lista = selecionar('#novotipo')
			if(!lista) return
			let selecionada = lista.options[lista.selectedIndex].innerText || ''
			if(!selecionada?.includes('DITR')){
				setTimeout(
					() => selecionarOpcao('#novotipo','DITR'),
					2000
				)
				setTimeout(
					() => window.wrappedJSObject.carregarExercicios(),
					3000
				)
			}
			let observador = new MutationObserver(() => {
				let observado = selecionar('#novoano')
				if(observado){
					let ano1 = observado.options[1].innerText || ''
					let ano2 = observado.options[2].innerText || ''
					if(!verificarExistenciaDeSolicitacao('DITR.*?'+ano1)){
						observado.selectedIndex = 1
						observador.disconnect()
						return
					}
					if(!verificarExistenciaDeSolicitacao('DITR.*?'+ano2)){
						observado.selectedIndex = 2
						observador.disconnect()
						return
					}
					preencherDirpf()
				}
			})
			observador.observe(document.body,{
				childList:true,
				subtree:true
			})
		}

		function preencherDoi(){
			let observador = new MutationObserver(() => {
				let observado = selecionar('#novaDataFim')
				if(observado){
					if(verificarExistenciaDeSolicitacao(doi.inicio)){
						observador.disconnect()
						return
					}
					selecionarOpcao('#novotipo','DOI')
					window.wrappedJSObject.carregarExercicios()
					let campoDoiDataInicio = selecionar('#novaDataInicio')
					let campoDoiDataFim = selecionar('#novaDataFim')
					if(campoDoiDataInicio	&& campoDoiDataFim){
						campoDoiDataInicio.removeAttribute('disabled')
						campoDoiDataFim.removeAttribute('disabled')
						preencher(campoDoiDataInicio,	doi.inicio)
						preencher(campoDoiDataFim,		doi.fim)
						clicar('[value="Incluir Pedido"]')
						observador.disconnect()
					}
				}
			})
			observador.observe(document.body,{
				childList:	true,
				subtree:		true
			})
		}

		function verificarExistenciaDeSolicitacao(expressao=''){
			if(!expressao) return ''
			let solicitacoes = document.querySelectorAll('tr')
			if(vazio(solicitacoes)) return ''
			let dirpf = [...solicitacoes].filter(solicitacao => solicitacao.innerText.match(/dirpf/gi))
			let solicitacao = [...solicitacoes].filter(solicitacao => solicitacao.innerText.match(expressao))
			if(vazio(solicitacao)) return ''
			return true
		}
	}
}

function infojudRegistrarSolicitacao(consulta = {}){
	if(vazio(consulta)) return
	let processo = consulta?.processo	|| ''
	let documento = consulta?.documento	|| ''
	let vara = consulta?.vara	|| ''
	let justificativa = 'Cumprimento de Mandado de Penhora'
	let url = LINK.infojud.solicitar + encodeURI('?' + 'processo=' + numeros(processo) + '&novocpfcnpj=' + numeros(documento) + '&justificativa=' + justificativa + '&vara=' + vara)
	abrirPagina(url,'','','','','infojud')
	esforcosPoupados(3,3,contarCaracteres(processo + documento + justificativa))
}

function infojudConsultarDocumento(consulta = {}){
	if(vazio(consulta)) return
	let documento = consulta?.documento	|| ''
	let cpf = obterCPF(documento)
	let cnpj = obterCNPJ(documento)
	let tipo = 'detalheNI'
	if(cpf) tipo += 'CPF'
	if(cnpj) tipo += 'CNPJ'
	let url = LINK.infojud.consultarDocumento + tipo + encodeURI('.asp?NI=' + numeros(documento))
	abrirPagina(url, '', '', screen.width / 2, '', 'infojud')
	esforcosPoupados(3,3,contarCaracteres(documento))
}

function infojudConsultarNomePessoaFisica(consulta = {}){
	if(vazio(consulta)) return
	let nome = consulta?.nome	|| ''
	let url = LINK.infojud.consultarNomePessoaFisica + encodeURI(nome)
	abrirPagina(url,'','','','','infojud')
	esforcosPoupados(3,3,contarCaracteres(nome))
}

function infojudConsultarNomePessoaJuridica(consulta = {}){
	if(vazio(consulta)) return
	let nome = consulta?.nome	|| ''
	let url = LINK.infojud.consultarNomePessoaJuridica + encodeURI(nome)
	abrirPagina(url,'','','','','infojud')
	esforcosPoupados(3,3,contarCaracteres(nome))
}

function infojudConsultarRedeSim(cnpj=''){
	if(!cnpj) return
	let url = LINK.infojud.sim + encodeURI(cnpj)
	abrirPagina(url,'','','','','infojud')
	esforcosPoupados(3,3,contarCaracteres(cnpj))
}