window.addEventListener('load',programa)

async function programa(){
	pjeCriarBotaoFixoConfigurarDimensoesDaJanela()
	let processo = obterParametroDeUrl('processo')
	PROCESSO = JSON.parse(processo)
	console.debug('PROCESSO',PROCESSO)
	
	CONFIGURACAO = await browser.storage.local.get(null)
	CONFIGURACAO.assistenteDeSelecao.copiar = true
	definicoesGlobais()
	criarCabecalhoDePaginaDaExtensao()
	selecionar('h1').innerText = 'DADOS DO PROCESSO'
	let lgpd = CONFIGURACAO?.lgpd?.ativado || false
	listarDadosDoProcesso()
	listarPartes()
	assistenteDeSelecao()
	setInterval(contarEsforcosRepetitivosPoupados,100)

	function listarDadosDoProcesso(){
		let base = selecionar('processo')
		criarTitulo('Processo',base)
		if(PROCESSO?.numero){
			document.title = 'Dados do Processo ' + PROCESSO.numero
			let secao = criar('numero','','subsecao',base)
			criarCampo('Número:','largura49',PROCESSO.numero,secao)
			criarCampo('Número sem separadores:','largura49',numeros(PROCESSO.numero),secao)
		}
		if(PROCESSO?.valor?.causa){
			let secao = criar('valor','','subsecao',base)
			criarCampo('Valor da Causa:','largura49',PROCESSO.valor.causa,secao)
			if(PROCESSO?.autuadoEm){
				criarCampo('Data de Autuação:','largura49',PROCESSO.autuadoEm,secao)
			}
		}
	}

	function listarPartes(){
		let base = selecionar('partes')
		if(PROCESSO?.partes?.ATIVO){
			let polo = PROCESSO.partes.ATIVO
			let secao = criar('polo-ativo','','subsecao',base)
			criarTitulo('Polo Ativo ' + `(${polo.length})`,secao)
			criarCampos(polo,secao)
		}
		if(PROCESSO?.partes?.PASSIVO){
			let polo = PROCESSO.partes.PASSIVO
			let secao = criar('polo-passivo','','subsecao',base)
			criarTitulo('Polo Passivo ' + `(${polo.length})`,secao)
			criarCampos(polo,secao)
		}
		if(PROCESSO?.partes?.TERCEIROS){
			let polo = PROCESSO.partes.TERCEIROS
			let secao = criar('terceiro','','subsecao',base)
			criarTitulo('Terceiros ' + `(${polo.length})`,secao)
			criarCampos(polo,secao)
		}

		function criarCampos(polo,secao){
			polo.forEach(parte => {
				let subsecao = criar('parte','','',secao)
				if(!parte?.nome) return
				let nome = parte.nome
				if(lgpd) nome = 'NOME DA PARTE'
				let rotulo = 'Nome'
				if(parte?.tipo.includes('PERITO')) rotulo = 'Perit(a)o'
				criarCampo(rotulo+':','largura100',nome,subsecao)
				let classe = 'largura49'
				if(parte?.documento){
					let documento = parte.documento
					let cnpj = obterCNPJ(documento)
					if(cnpj) classe = 'largura32'
					if(lgpd){
						if(cnpj) documento = '00.000.000/0000-00'
						else documento = '000.000.000-00'
					}
					criarCampo('Documento:',classe,documento,subsecao)
					if(cnpj) criarCampo('Raiz do CNPJ:',classe,obterRaizCNPJ(documento),subsecao)
					criarCampo('Sem separadores:',classe,numeros(documento),subsecao)
				}
			}
		)}
	}

	function criarTitulo(
		texto = '',
		ancestral = ''
	){
		let titulo = criar('h2','','',ancestral)
		titulo.innerText = texto
	}

	function criarCampo(
		titulo = '',
		classe = '',
		texto = '',
		ancestral = ''
	){
		let rotulo = criar('rotulo','',classe,ancestral)
		rotulo.setAttribute('aria-label',titulo)
		let campo = criar('campo','','',rotulo)
		campo.innerText = texto
		campo.contentEditable = true
		campo.spellcheck = false
		campo.addEventListener('click',evento => {
			let elemento = evento.target
			window.getSelection().selectAllChildren(elemento)
		})
		return campo
	}
}