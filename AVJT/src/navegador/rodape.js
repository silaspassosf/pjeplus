function criarRodapeDePaginaDaExtensao(){

	let rodape = selecionar('footer')
	if(!rodape)
		return

	criarEstilo()
	criarInformacoes()
	criarLinks()

	function criarEstilo(){

		estilizar(
			rodape,
			`
				footer{
					background:
						var(--quinzinho-gradiente-branco-preto),
						linear-gradient(0deg,rgba(var(--quinzinho-cor-preto),0.8) 0%,rgba(var(--quinzinho-cor-preto),0.8) 100%),
						rgba(var(--quinzinho-cor-primaria),1)
					;
					bottom:0;
					color:rgba(var(--quinzinho-cor-branco),0.9);
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
					background-color:rgba(var(--quinzinho-cor-branco),1);
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
					box-shadow:0px 2px 2px 2px rgba(var(--quinzinho-cor-preto), 0.3);
					content:attr(aria-label);
					background-color:rgba(var(--quinzinho-cor-preto),0.9);
					color:rgba(var(--quinzinho-cor-branco),1);
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
					background:var(--quinzinho-icone-engrenagem);
				}
				#github{
					background:var(--quinzinho-icone-github);
				}
				#pagina{
					background:var(--quinzinho-icone-branco);
				}
				#pix{
					background:var(--quinzinho-icone-pix);
				}
				#roadmap{
					background:var(--quinzinho-icone-estrada);
				}
				#telegram{
					background:var(--quinzinho-icone-telegram);
				}
				#termos{
					background:var(--quinzinho-icone-termos) center center / 90% 90% no-repeat;
				}
				#whatsapp{
					background:var(--quinzinho-icone-whatsapp);
				}
				#youtube{
					background:var(--quinzinho-icone-youtube);
				}

			`
		)

	}


	function criarInformacoes(){

		criarListaDeDefinicoes(
			'',
			'',
			rodape,
			[
				{
					dt:"Versão:",
					dd:EXTENSAO.version+' '
				},
				{
					dt:"– Desenvolvido por",
					dd:EXTENSAO.author
				}
			]
		)

	}


	function criarLinks(){

		let rodapeLinks = criar('nav','','',rodape)

		criarLinkDoRodape('github', '', 'GitHub deste Projeto',() => criarJanela(LINK.github))
		criarLinkDoRodape('termos', '', 'Termos de Uso',abrirPaginaTermosDeUso)
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
