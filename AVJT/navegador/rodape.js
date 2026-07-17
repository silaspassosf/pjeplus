function criarRodapeDePaginaDaExtensao(){
	let rodape = selecionar('footer')
	if(!rodape) return
	criarInformacoes()
	criarLinks()
	estilizar(rodape,`
	footer{
		background:
			var(--extensao-gradiente-branco-preto),
			linear-gradient(0deg,rgba(var(--extensao-cor-preto),0.8) 0%,rgba(var(--extensao-cor-preto),0.8) 100%),
			rgba(var(--extensao-cor-primaria),1)
		;
		bottom:0;
		color:rgba(var(--extensao-cor-branco),0.9);
		font-size:12px;
		height:auto;
		overflow:hidden;
		padding:0;
		position:fixed;
		text-align:center;
		width:100%;
	}
	footer,
	footer nav
	{
		align-items:center;
		display:flex;
		flex-wrap:wrap;
		justify-content:space-between;
	}
	footer dl,
	footer nav
	{
		height:30px;
		line-height:30px;
		margin:0 10px;
	}
	footer dl
	{
		display:flex;
		gap:3px;
	}
	esforcos-poupados{
		background:rgba(var(--extensao-cor-branco),0.05);
		flex-grow:1;
		font-size:13px;
		line-height:30px;
		text-align:center;
		width:100%;
	}
	esforcos-poupados *{
		cursor:pointer;
	}
	esforcos-poupados #esforcos{
		color:rgba(var(--extensao-cor-verde),1);
	}
	esforcos-poupados #data{
		color:rgba(var(--extensao-cor-amarelo),1);
	}
	.icone{
		cursor:pointer;
		display:block;
		opacity:0.8;
		background-position:center center;
		background-repeat:no-repeat;
		position:relative;
		transition:all 0.1s;
	}
	.icone:hover
	{
		background-color:rgba(var(--extensao-cor-branco),1);
		height:26px;
		opacity:1;
		margin:2px;
		width:26px;
	}
	.icone,
	.icone:active
	{
		height:20px;
		margin:5px;
		width:20px;
	}
	.icone:hover::before{
		animation:aparecer 0.5s ease-out 0s 1 both;
		border-radius:15px 15px 0 0;
		box-shadow:0px 2px 2px 2px rgba(var(--extensao-cor-preto), 0.3);
		content:attr(aria-label);
		background-color:rgba(var(--extensao-cor-preto),0.9);
		color:rgba(var(--extensao-cor-branco),1);
		display:block;
		font-size:12px;
		font-weight:600;
		line-height:1rem;
		right:30px;
		padding:7px;
		position:absolute;
		text-align:center;
		width:300px;
	}
	#configuracoes{
		background:var(--extensao-icone-engrenagem);
	}
	#github{
		background:var(--extensao-icone-github);
	}
	#pagina{
		background:var(--extensao-icone-branco);
	}
	#pix{
		background:var(--extensao-icone-pix);
	}
	#roadmap{
		background:var(--extensao-icone-estrada);
	}
	#telegram{
		background:var(--extensao-icone-telegram);
	}
	#termos{
		background:var(--extensao-icone-termos) center center / 90% 90% no-repeat;
	}
	#whatsapp{
		background:var(--extensao-icone-whatsapp);
	}
	#youtube{
		background:var(--extensao-icone-youtube);
	}
	`)

	function criarInformacoes(){
		exibirContagemDeEsforcosRepetitivosPoupados()
		criarListaDeDefinicoes('','',rodape,[
			{
				dt:"Versão:",
				dd:EXTENSAO.version+' '
			},
			{
				dt:"– Desenvolvido por",
				dd:EXTENSAO.author
			}
		])

		function exibirContagemDeEsforcosRepetitivosPoupados(){
			let p = selecionar('esforcos-poupados')
			if(!p) return
			let data = CONFIGURACAO?.esforcos?.data || DATA.hoje.curta
			criarLink('data', '', p, '', data, '',abrirPaginaContadorDeEsforcosRepetitivos)
			let declaracao = document.createTextNode(', esta extensão já te poupou mais de ')
			p.appendChild(declaracao)
			let contagem = criarLink('esforcos', '', p, '', '', '',abrirPaginaContadorDeEsforcosRepetitivos)
			let complemento = document.createTextNode(' esforços repetitivos!')
			p.appendChild(complemento)
			contabilizarEsforcosRepetitivosPoupados()

			function contabilizarEsforcosRepetitivosPoupados(){
				let cliques = Number(CONFIGURACAO?.esforcos?.cliques)			|| 0
				let movimentos = Number(CONFIGURACAO?.esforcos?.movimentos)	|| 0
				let teclas = Number(CONFIGURACAO?.esforcos?.teclas)			|| 0
				let toques = cliques + movimentos + teclas
				contagem.innerText = toques.toLocaleString()
				contagem.title = "\n AÇÕES REPETITIVAS POUPADAS: \n Cliques: "+cliques.toLocaleString()+"\n Movimentos: "+movimentos.toLocaleString()+"\n Digitações: " + teclas.toLocaleString() + "\n "
			}
		}
	}

	function criarLinks(){
		let rodapeLinks = criar('nav','','',rodape)
		criarLinkDoRodape('pagina', LINK.extensao, 'Página desta extensão')
		criarLinkDoRodape('termos', '', 'Termos de Uso',abrirPaginaTermosDeUso)
		criarLinkDoRodape('roadmap', LINK.roadmap, 'Lista de Funcionalidades')
		criarLinkDoRodape('youtube', LINK.youtube, 'Canal no Youtube')
		criarLinkDoRodape('telegram', LINK.telegram, 'Grupo de utilizadores no Telegram')
		criarLinkDoRodape('whatsapp', LINK.whatsapp.grupo, 'Grupo de utilizadores no WhatsApp')
		//criarLinkDoRodape('github', LINK.github, 'Código-Fonte desta Extensão no GitHub')
		criarLinkDoRodape('configuracoes', '', 'Configurações da extensão', abrirPaginaOpcoesDaExtensao)

		function criarLinkDoRodape(
			id = '',
			endereco = '',
			titulo = '',
			aoClicar = ''
		){
			criarLink(id, 'icone', rodapeLinks, endereco, '', titulo, aoClicar)
		}
	}
}