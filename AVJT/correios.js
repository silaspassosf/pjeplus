async function correios(){
	if(!JANELA.includes('correios.com.br')) return
	otimizarLayout()
	acionarBotaoVerMais()
	consultarObjeto()
	otimizarResultado()
	
	
	async function acionarBotaoVerMais(){
		let botao = await esperar('#a-ver-mais')
		clicar(botao)
	}
	
	async function otimizarLayout(){
		if(!JANELA.includes('avjtConsultarObjetoNosCorreios')) return
		estilizar('',`
			informacao,
			rotulo
			{
				display:block;
				text-align:left;
			}
			informacao{
				margin:5px 0 10px 10px;
			}
			rotulo{
				font-weight:bold;
				margin:5px 0;
			}
			#alerta,
			#menu,
			#rodape,
			.bannersro,
			#acessibilidade,
			#titulo-pagina,
			[aria-label="breadcrumb"]
			{
				display:none;
			}
			`,
			'avjt-corrreios-informacao'
		)
	}

	async function consultarObjeto(){
		if(!JANELA.includes('avjtConsultarObjetoNosCorreios')) return
		let objeto = obterParametroDeUrl('avjtConsultarObjetoNosCorreios')
		if(!objeto) return
		let campo = selecionar('#objeto')
		if(!campo) return
		preencher(campo,maiusculas(objeto))
		await aguardar(1000)
		focar('#captcha')
	}

	async function otimizarResultado(){
		if(!JANELA.includes('rastreamento.correios.com.br/app/index.php')) return
		await esperar('.ship-steps')
		await aguardar(1000)
		let processo = obterParametroDeUrl('processo')
		let idDocumento = obterParametroDeUrl('idDocumento')
		let dados = await pjeApiConsultaPublicaObterProcessoId(processo)
		PROCESSO = dados[0]
		PROCESSO.objeto = obterParametroDeUrl('avjtConsultarObjetoNosCorreios')
		PROCESSO.destinatario = obterParametroDeUrl('parte')
		criarInformacao('processo','Processo: ',processo)
		criarInformacao('parte','Parte: ',PROCESSO.destinatario)
		criarInformacao('documento','Documento Id: ',idDocumento)
		criarInformacao('objeto','Objeto: ',PROCESSO.objeto)
		criarBotoesCertificar()
	}
	
	async function criarInformacao(
		id='',
		rotulo='',
		dado=''
	){
		let cabecalho = selecionar('#cabecalho-rastro')
		console.debug('cabecalho',cabecalho)
		let titulo = criar('rotulo','rotulo-'+id,'',cabecalho)
		let texto = criar('informacao','dado-'+id,'',cabecalho)
		titulo.innerText = rotulo
		texto.innerText = dado
	}
	
	function criarBotoesCertificar(){
		estilizarBotaoCertificarNoPje()
		criarBotaoCertificar('entregue','azul')
		criarBotaoCertificar('devolvido','vermelho')
	
		function criarBotaoCertificar(
			texto = '',
			classe = ''
		){
			criarBotao(
				'avjt-certificar-'+texto,
				'avjt-'+classe,
				'',
				'CERTIFICAR "OBJETO "' + maiusculas(texto) + '" NO PJE',
				'Abre a Tarefa Anexar Documento',
				() => {
					let tipo = 'Certidão'
					let descricao = 'Correios - Objeto ' + titularizar(texto) + ' - ' + PROCESSO.destinatario
					let corpo = 'Certifico que, em consulta à página na Internet dos Correios, o objeto ' + PROCESSO.objeto + ' retornou o seguinte relatório:'
					let certidao = pjeCertificar(descricao,tipo,corpo,'','','',true)
					LINK.pje.anexar = LINK.pje.processo + PROCESSO.id + '/documento/anexar?certificar='+encodeURIComponent(JSON.stringify(certidao))
					document.querySelector('.jumbotron').remove()
					botaoCertificarOcultarAoClicar()
					capturarImagemDeElemento('.container')
					pjeAbrirAnexar()
				}
			)
		}
	}
}