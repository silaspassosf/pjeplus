function pjeDetalhesDoProcessoOtimizarRolagem(){
	criarAreasDeRolagemDaTimeline()
	//criarAreasDeRolagemDoDocumento()

	function criarAreasDeRolagemDaTimeline(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.criarAreasDeRolagemDaTimeline) return
		let rolagem = null
		let id = 'timeline-rolagem-'
		criarSeta(id+'inicio',irParaInicio)
		criarSeta(id+'final',irParaFinal)
		criarSeta(id+'cima',rolarParaCima,pararRolagem)
		criarSeta(id+'baixo',rolarParaBaixo,pararRolagem)

		function selecionarTimeline(){
			let timeline = selecionar('.pje-timeline')
			return timeline
		}

		function irParaInicio(){
			let timeline = selecionarTimeline()
			if(!timeline) return
			timeline.scrollTo(0,0)
			esforcosPoupados(1)
		}

		function irParaFinal(){
			let timeline = selecionarTimeline()
			if(!timeline) return
			let altura = timeline.scrollHeight
			if(altura < 900) return
			timeline.scrollTo(0,altura)
			esforcosPoupados(1)
		}

		function rolarParaCima(){
			let timeline = selecionarTimeline()
			if(!timeline) return
			timeline.scrollTop = timeline.scrollTop - 50
			rolagem = setTimeout(rolarParaCima,100)
			esforcosPoupados(1)
		}

		function rolarParaBaixo(){
			let timeline = selecionarTimeline()
			if(!timeline) return
			timeline.scrollTop = timeline.scrollTop + 50
			rolagem = setTimeout(rolarParaBaixo,100)
			esforcosPoupados(1)
		}

		function pararRolagem(){
			clearTimeout(rolagem)
		}

	}

	function criarAreasDeRolagemDoDocumento(){
		if(!CONFIGURACAO?.pjeAoAbrirDetalhesDoProcesso?.criarAreasDeRolagemDoDocumento) return
		let documento = {}
		let rolagem = null
		let id = 'documento-rolagem-'
		criarSeta(id+'inicio',irParaInicio)
		criarSeta(id+'final',irParaFinal)
		criarSeta(id+'cima',rolarParaCima,pararRolagem)
		criarSeta(id+'baixo',rolarParaBaixo,pararRolagem)

		function selecionarDocumento(){
			documento.pje = document.querySelector('.conteudo-pdf')?.contentDocument?.querySelector('#viewerContainer') || ''
			documento.pdf = document.getElementsByClassName('ng2-pdf-viewer-container')[0] || ''
			if(!documento.pje && !documento.pdf) return ''
			return documento
		}

		function irParaInicio(){
			selecionarDocumento()
			if(documento.pje) documento.pje.scrollTo(0,0)
			if(documento.pdf) documento.pdf.scrollTo(0,0)
			esforcosPoupados(1)
		}

		function irParaFinal(){
			selecionarDocumento()
			if(documento.pdf){
				if(documento.pdf.scrollHeight > 900){
					documento.pdf.scrollTo(0,documento.pdf.scrollHeight)
					esforcosPoupados(1)
				}
				return
			}
			if(!documento.pje) return
			if(documento.pje.scrollHeight < 900) return
			documento.pje.scrollTo(0,documento.pje.scrollHeight)
			esforcosPoupados(1)
		}

		function rolarParaCima(){
			selecionarDocumento()
			if(!documento) return
			if(documento.pdf.scrollTop <= 0) return
			if(documento.pdf){
				documento.pdf.scrollTop = documento.pdf.scrollTop - 75
				rolagem = setTimeout(rolarParaCima,100)
				esforcosPoupados(1)
				return
			}
			if(documento.pje.scrollTop <= 0) return
			documento.pje.scrollTop = documento.pje.scrollTop - 75
			rolagem = setTimeout(rolarParaCima,100)
			esforcosPoupados(1)
		}

		function rolarParaBaixo(){
			selecionarDocumento()
			if(!documento) return
			if(documento.pdf){
				documento.pdf.scrollTop = documento.pdf.scrollTop + 75
				rolagem = setTimeout(rolarParaBaixo,100)
				acoes.cliques++
				return
			}
			documento.pje.scrollTop = documento.pje.scrollTop + 75
			rolagem = setTimeout(rolarParaBaixo,100)
			esforcosPoupados(1)
		}

		function pararRolagem(){
			clearTimeout(rolagem)
		}
	}

	function criarSeta(
		id = '',
		funcao = '',
		parar = ''
	){
		remover(id)
		let elemento = criar('area-de-rolagem',id)
		if(funcao) elemento.addEventListener('mouseenter',funcao)
		if(parar) elemento.addEventListener('mouseout',parar)
		return elemento
	}
}

function pjeDocumentoOtimizarRolagem(){
	if(!CONFIGURACAO?.pje?.criarAreasDeRolagemDaPaginaDeDocumento) return
	criarSeta('inicio',irParaInicio)
	criarSeta('final',irParaFinal)
	let inicio = {top:0,behavior:'smooth'}
	let fim = {top:1000000,behavior:'smooth'}

	function irParaInicio(){
		window?.scrollTo(inicio)
		document.querySelector('pdf-viewer .ng2-pdf-viewer-container')?.scrollTo(inicio)
		document.querySelector('mat-sidenav-content')?.scrollTo(inicio)
		document.querySelector('#visualizacao-documento')?.scrollTo(inicio)
		esforcosPoupados(1)
	}

	function irParaFinal(){
		window?.scrollTo(fim)
		document.querySelector('pdf-viewer .ng2-pdf-viewer-container')?.scrollTo(fim)
		document.querySelector('mat-sidenav-content')?.scrollTo(fim)
		document.querySelector('#visualizacao-documento')?.scrollTo(fim)
		esforcosPoupados(1)
	}

	function criarSeta(
		id			= '',
		funcao	= '',
		parar		= ''
	){
		remover(id)
		let elemento = criar('area-de-rolagem')
		elemento.id = 'pagina-rolagem-'+id
		elemento.className = 'area-de-rolagem'
		if(funcao) elemento.addEventListener('mouseenter',funcao)
		if(parar) elemento.addEventListener('mouseout',parar)
		return elemento
	}
}