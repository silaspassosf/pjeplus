async function assistenteDeSelecao(){
	if(!CONFIGURACAO.assistenteDeSelecao.ativado) return
	document.addEventListener('selectionchange',aoSelecionar)

	async function aoSelecionar(){
		let selecao = document.getSelection() || ''
		if(!selecao) return
		let conteudo = ''
		if(selecao && selecao.rangeCount > 0) conteudo = selecao?.getRangeAt(0)
		if(!conteudo) return
		let retangulo = conteudo.getBoundingClientRect()
		let posicao = {}
		posicao.horizontal = Math.ceil(retangulo.left)
		posicao.vertical = Math.ceil(retangulo.top)
		let texto = selecao.toString() || ''
		if(!texto){
			fecharMenu()
			return
		}
		let textoAparado = texto.trim()
		let bbContaJudicial = obterContaJudicialBancoDoBrasil(texto)
		let caracteres = contarCaracteres(texto)
		let chassi = obterChassi(texto)
		let cnpj = obterCNPJ(texto)
		let contexto = pjeObterContexto()
		let cpf = obterCPF(texto)
		let correiosObjeto = obterCorreiosObjeto(texto)
		let data = obterData(texto)
		let hora = obterHora(texto)
		let documento = obterDocumento(texto)
		let email = obterEmail(texto.replace(/(.*?mail[:]|[()<>{}]|\s|\t|\[|\])/gi,'').trim())
		let letra = texto.match(/[A-Za-zÀ-ȕ]/)
		let mandado = texto.match(/mandado/gi)
		let nomeCompleto = textoAparado.includes(' ')
		let numero = numeros(texto)
		let pje = pjeObterContexto()
		let pjeDocumento = selecaoPjeObterDocumento(textoAparado)
		let pjeNumeroDoProcessoParcial = obterNumeroDoProcessoParcial(texto)
		let pjeNumeroDoProcessoCompleto = obterNumeroDoProcessoPadraoCNJ(texto)
		let placa = obterPlacaDeVeiculoAutomotor(texto)
		let valor = obterValorMonetario(texto)
		let uri = encodeURI(textoAparado)
		let menu = criarMenu()
		if(pjeDocumento){
			criarBotao(
				'pje-documento',
				'solido',
				'Abrir Documento do PJe',
				() => {
					let url = LINK.pje.processo + pjeDocumento.processo + '/documento/' + pjeDocumento.id + '/conteudo'
					esforcosPoupados(1,3)
					abrirPagina(url,850,850,50,0)
				}
			)
		}
		criarBotao('copiar','solido','Copiar texto selecionado',copiarTextoSelecionado)
		if(data) criarBotao('copiar-data','solido','Copiar apenas a Data no texto selecionado',copiarDataNoTextoSelecionado)
		if(hora) criarBotao('copiar-hora','solido','Copiar apenas o Horário no texto selecionado',copiarHoraNoTextoSelecionado)
		if(documento) criarBotao('copiar-documento','solido','Copiar apenas o número do documento no texto selecionado',copiarDocumentoNoTextoSelecionado)
		if(letra){
			criarBotao('maiusculas','','Converter texto para letras maiúsculas',converterTextoParaMaiusculas)
			criarBotao('minusculas','','Converter texto para letras minúsculas',converterTextoParaMinusculas)
			criarBotao('titularizar','','Converter texto para Título',converterTextoParaTitulo)
			criarBotao('pje-consultar','','Consultar Parte ou Representante no PJe',
				() => pjeAbrirPainelDeConsultaProcessual({nomeParte:maiusculas(textoAparado)})
			)
			criarBotao('tst','','Consultar Jurisprudência no Tribunal Superior do Trabalho',
				() => tstConsultarJurisprudencia(textoAparado)
			)
			if(CONFIGURACAO.instituicao.tribunal === '15'){
				criarBotao('trt','','Consultar Jurisprudência no Tribunal Regional do Trabalho da 15ª Região',
					() => trt15ConsultarJurisprudencia(textoAparado)
				)
			}
			if(nomeCompleto){
				if(!texto.match(/(CPF|CNPJ)[:]/gi)){
					let consulta = {}
					consulta.nome = textoAparado || ''
					criarBotao('infojud','','InfoJud - Consultar Nome de Pessoa Física',
						() => infojudConsultarNomePessoaFisica(consulta)
					)
					criarBotao('infojud-nome','','InfoJud - Consultar Nome de Pessoa Jurídica',
						() => infojudConsultarNomePessoaJuridica(consulta)
					)
					criarBotao('siscondj','','Polo Ativo - Consultar Nome no Banco do Brasil',
						() => bbConsultarNomePoloAtivo(textoAparado)
					)
					criarBotao('bb','','Polo Passivo - Consultar Nome no Banco do Brasil',
						() => bbConsultarNomePoloPassivo(textoAparado)
					)
					criarBotao('cefJudiciais','','Polo Ativo - Consultar Nome na Caixa Econômica Federal',
						() => cefConsultarNomePoloAtivo(textoAparado)
					)
					criarBotao('cefJudiciais2','','Polo Passivo - Consultar Nome na Caixa Econômica Federal',
						() => cefConsultarNomePoloPassivo(textoAparado)
					)
					criarBotao('cefRecursais','','Consultar Depósitos Recursais na Caixa Econômica Federal',
						() => cefConsultarDepositosRecursaisPorNomeDoPoloAtivo(textoAparado)
					)
				}
			}
		}
		if(bbContaJudicial){
			criarBotao('bb','','Consultar Conta Judicial no Banco do Brasil',
				() => bbConsultarContaJudicial(bbContaJudicial)
			)
		}
		if(cnpj){
			criarBotao('pje-consultar','','Consultar CNPJ no PJe',
				() => pjeAbrirPainelDeConsultaProcessual({cnpj})
			)
			criarBotao('simples-consultar','','Consultar CNPJ no Simples Nacional',
				() => simplesConsultarPessoa(cnpj)
			)
		}
		if(cpf){
			criarBotao('pje-consultar','','Consultar CPF no PJe',
				() => pjeAbrirPainelDeConsultaProcessual({cpf})
			)
		}
		if(pjeNumeroDoProcessoParcial){
			criarBotao('pje-consultar','','Consultar Processo no PJe',
				() => pjeAbrirPaginaDeConsultaProcessual(pjeNumeroDoProcessoParcial)
			)
		}
		if(mandado || valor || data){
			criarBotao('penhora-online','','Penhora Online',
				() => {
					let consulta = {}
					if(contexto.includes('pje-mandados')){
						consulta.mandado = {}
						consulta.mandado.id = pjeObterDocumentoId()
						consulta.mandado.data = pjeObterDocumentoData()
					}
					consulta.valor = valor || ''
					penhoraOnlineRegistrar(consulta)
					copiarDadosDoProcesso()
					clicar('#avjt-botao-dados-do-processo')
				}
			)
		}
		if(pjeNumeroDoProcessoCompleto){
			criarBotao('pje-consultar','','Consultar Detalhes do Processo no PJe',
				(evento) => pjeConsultarProcesso(pjeNumeroDoProcessoCompleto,evento)
			)
			criarBotao('pje-instancia-1','','Consulta Pública do Processo na 1ª Instância',
				() => pjeConsultaPublicaProcessoInstancia(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('pje-instancia-2','','Consulta Pública do Processo na 2ª Instância',
				() => pjeConsultaPublicaProcessoInstancia(pjeNumeroDoProcessoCompleto,2)
			)
			criarBotao('tst','','Consultar Processo no Tribunal Superior do Trabalho',
				() => tstConsultarProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('trt','','Consultar Processo no Tribunal Regional do Trabalho',
				() => trtConsultarProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('correios','','Consultar Processo no E-Carta',
				() => ecartaConsultarProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('siscondj','','Consultar Processo no SISCONDJ-JT',
				() => siscondjConsultarProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('bb','','Consultar Processo no Banco do Brasil',
				() => bbConsultarProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('cefJudiciais','','Consultar Depósitos Judiciais na Caixa Econômica Federal',
				() => cefConsultarDepositosJudiciaisProcesso(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('cefRecursais','','Consultar Depósitos Recursais na Caixa Econômica Federal',
				() => cefConsultarDepositosRecursaisPorNomeDoPoloAtivo(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('penhora-online','','Consultar Respostas de Penhora',
				() => penhoraOnlineConsultarRespostasDePenhora(pjeNumeroDoProcessoCompleto)
			)
			criarBotao('penhora-respostas','','Consultar Respostas de Certidões',
				() => penhoraOnlineConsultarRespostasDeCertidoes(pjeNumeroDoProcessoCompleto)
			)
		}
		if(pjeNumeroDoProcessoCompleto || valor){
			criarBotao('sisbajud','','SISBAJUD - Abrir Minuta de Bloqueio',
				() => sisbajudAbrirCadastroDeMinuta(pjeNumeroDoProcessoCompleto)
			)
		}
		if(documento){
			let consulta = {}
			consulta.documento = documento || ''
			criarBotao('infojud-documento','','InfoJud - Consultar Documento',
				() => {
					infojudConsultarDocumento(consulta)
				}
			)
			criarBotao('infojud','','InfoJud - Registrar Solicitação',
				() => {
					consulta.processo = PROCESSO?.numero || ''
					consulta.vara = PROCESSO?.orgaoJulgador?.descricao || ''
					infojudRegistrarSolicitacao(consulta)
				}
			)
			if(cnpj){
				criarBotao('receita','','Consultar CNPJ na Rede SIM',
					() => infojudConsultarRedeSim(documento)
				)
			}
			criarBotao('cndt','','CNDT - Certidão Negativa de Débitos Trabalhistas (Utilize Control + V para colar no campo de consulta)',cndtConsultar)
			criarBotao('siscondj','','Polo Ativo - Consultar Documento no Banco do Brasil',
				() => bbConsultarDocumentoPoloAtivo(documento)
			)
			criarBotao('bb','','Polo Passivo - Consultar Documento no Banco do Brasil',
				() => bbConsultarDocumentoPoloPassivo(documento)
			)
			criarBotao('cefJudiciais','','Polo Ativo - Consultar Documento na Caixa Econômica Federal',
				() => cefConsultarDocumentoPoloAtivo(documento)
			)

			criarBotao('cefJudiciais2','','Polo Passivo - Consultar Documento na Caixa Econômica Federal',
				() => cefConsultarDocumentoPoloPassivo(documento)
			)
			criarBotao('renajud','','Consultar / Inserir Restrição no RENAJUD',
				() => renajudInserirRestricao({documento})
			)
			criarBotao('infoseg','','Consultar Documento no INFOSEG',
				() => infosegPesquisarDocumento(documento)
			)
		}
		if(chassi){
			criarBotao('renajud','','Consultar / Inserir Restrição no RENAJUD',
				() => renajudInserirRestricao({chassi})
			)
		}
		if(placa){
			criarBotao('renajud','','Consultar / Inserir Restrição no RENAJUD',
				() => renajudInserirRestricao({placa})
			)
		}
		if(correiosObjeto) criarBotao('correios','','Rastrear Objeto nos Correios',abrirCorreiosRastrearObjeto)
		if(valor) criarBotao('valor-por-extenso','','Valor Monetário por Extenso',escreverValorPorExtenso)
		if(numero){
			if(!letra) criarBotao('numero-por-extenso','','Número Inteiro por Extenso',escreverNumeroPorExtenso)
		}
		if(email){
			let rotulo = 'Escrever E-mail'
			if(pje) rotulo = 'Baixar Documento Ativo do PJe e Escreve E-mail'
			criarBotao('webmail','',rotulo,
				() => {
					if(email.includes('@caixa.gov.br')) emailEscreverOficioCaixaEconomicaFederalBaixarDocumento(email)
					else emailEscreverBaixarDocumentoAtivo(email)
				}
			)
		}
		criarBotao('google','','Pesquisar texto selecionado no Google',abrirGoogle)
		criarBotao('google-tradutor','','Traduzir texto selecionado',abrirGoogleTradutor)
		criarBotao('whatsapp','','Enviar mensagem por WhatsApp para o número selecionado',
			() => whatsappMontarMensagem(textoAparado)
		)
		criarBotao('transparencia','','Consultar Texto Selecionado no Portal da Transparência',abrirPortalTransparencia)

		menu.style.left = posicao.horizontal + 'px'
		menu.style.top = (posicao.vertical - menu.offsetHeight) + 'px'
		menu.style.opacity = '1'

		copiarAutomaticamenteTextoSelecionado()

		if(pjeNumeroDoProcessoCompleto){
			let dados = await pjeApiConsultaPublicaObterProcessoId(numero) || ''
			let id = dados[0]?.id || ''
			LINK.pje.historico = LINK.pje.processo + id + '/historicotarefa'
			if(id){
				criarBotao('pje-historico','','Abrir Histórico de Tarefas do Processo',
					() => pjeAbrirHistoricoDeTarefas()
				)
			}
		}

		function escreverValorPorExtenso(){
			let prefixo = ''
			if(!texto.includes('$')) prefixo = 'R$ '
			let porExtenso = prefixo + texto + ' (' + extenso(valor,true) + ')'
			inserirTexto(porExtenso)
			esforcosPoupados(0,1,contarCaracteres(porExtenso))
		}

		function escreverNumeroPorExtenso(){
			let porExtenso = texto + ' (' + extenso(texto) + ')'
			inserirTexto(porExtenso)
			esforcosPoupados(0,1,contarCaracteres(porExtenso))
		}

		function converterTextoParaMaiusculas(){
			inserirTexto(maiusculas(texto))
			esforcosPoupados(0,1,caracteres)
		}

		function converterTextoParaMinusculas(){
			inserirTexto(minusculas(texto))
			esforcosPoupados(0,1,caracteres)
		}

		function converterTextoParaTitulo(){
			inserirTexto(titularizar(texto))
			esforcosPoupados(0,1,caracteres)
		}

		function abrirGoogle(){
			abrirPagina(LINK.google.raiz + '/search?q=' + uri)
			esforcosPoupados(1,2,caracteres)
		}

		function abrirGoogleTradutor(){
			abrirPagina(LINK.google.tradutor + uri)
			esforcosPoupados(1,2,caracteres)
		}

		function abrirCorreiosRastrearObjeto(){
			let url = LINK.correios.rastrear + correiosObjeto
			let ecarta = selecionar('[action="/consultarProcesso.xhtml"]')
			if(ecarta){
				let alvo = selecionarPorTexto(correiosObjeto)
				let linha = alvo.parentElement.parentElement.parentElement
				let processo = obterTextoDaCelula(2)
				let id = obterTextoDaCelula(3)
				let idDocumento = id.substring(3)
				let parte = obterTextoDaCelula(6)
				url += `&processo=${processo}&parte=${parte}&idDocumento=${idDocumento}`		
				function obterTextoDaCelula(celula=0){
					let texto = linha.cells[celula].innerText || ''
					return texto.trim()
				}
			}
			abrirPagina(url,800)
			esforcosPoupados(1,2,caracteres)
		}

		function abrirPortalTransparencia(){
			abrirPagina(LINK.transparencia + uri)
			esforcosPoupados(1,2,caracteres)
		}

		function cndtConsultar(){
			let codigo = 'avjtConsultarCNDT='+documento
			copiar(codigo)
			abrirPagina(LINK.cndt + encodeURI(codigo))
			esforcosPoupados(1,2,contarCaracteres(documento))
		}

		function copiarAutomaticamenteTextoSelecionado(){
			if(!textoAparado) return
			if(CONFIGURACAO.assistenteDeSelecao.copiar) clicar('assistente-de-selecao > #copiar')
			if(CONFIGURACAO.assistenteDeSelecao.copiarData) clicar('assistente-de-selecao > #copiar-data')
			if(CONFIGURACAO.assistenteDeSelecao.copiarHora) clicar('assistente-de-selecao > #copiar-hora')
			if(CONFIGURACAO.assistenteDeSelecao.copiarDocumento) clicar('assistente-de-selecao > #copiar-documento')
		}

		function copiarTextoSelecionado(){
			if(textoAparado) copiar(textoAparado)
		}

		function copiarDataNoTextoSelecionado(){
			if(data){
				copiar(data)
				if(TAREFA?.nome?.includes('SISCONDJ')) copiar(data+';'+PROCESSO.numero)
			}
		}

		function copiarHoraNoTextoSelecionado(){
			if(hora) copiar(hora)
		}

		function copiarDocumentoNoTextoSelecionado(){
			if(documento) copiar(documento)
		}

		function inserirTexto(texto=''){
			let pjeEditor = selecionar('pje-editor')
			if(pjeEditor){
				document.execCommand(
					'insertText',
					false,
					texto
				)
			}
			else{
				conteudo.deleteContents()
				conteudo.insertNode(document.createTextNode(texto))
				copiar(texto)
			}
		}

		function criarMenu(){
			let elemento = criar(
				'assistente-de-selecao',
				'assistente-de-selecao'
			)
			elemento.addEventListener('click',fecharMenu)
			return elemento
		}

		function criarBotao(
			id = '',
			classe = '',
			titulo = '',
			aoClicar = ''
		){
			let botao = criar('botao',id,'link',menu)
			if(id){
				botao.id = id
				botao.classList.add(id)
			}
			if(classe) botao.classList.add(classe)
			if(titulo) botao.setAttribute('aria-label',titulo)
			if(aoClicar) botao.addEventListener('click',aoClicar)
			botao.addEventListener('click',evento => evento.stopPropagation())
			if(id.includes('copiar')){
				botao.addEventListener('click',() => {
					botao.classList.toggle('copiado')
					setTimeout(
						() => botao.classList.toggle('copiado'),
						1000
					)
				})
			}
		}

		function fecharMenu(){
			remover('assistente-de-selecao')
		}
	}
}

function selecaoPjeObterDocumento(texto){
	let dados = selecionar('#json-dados-do-processo') || parent?.document?.head?.querySelector('#json-dados-do-processo') || ''
	if(!dados) return ''
	let conteudo = dados?.content || ''
	if(!conteudo) return ''
	let processo = JSON.parse(conteudo) || ''
	if(!processo) return ''
	let documentos = processo?.documentos || ''
	if(!documentos) return ''
	let documento = documentos.filter(documento => documento.idUnicoDocumento === texto.trim())[0] || ''
	if(!documento) return ''
	let pjeDocumento = {}
	pjeDocumento.id = documento.id
	pjeDocumento.processo = processo.id
	return pjeDocumento
}