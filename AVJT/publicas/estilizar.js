function estilizarBotaoPjeCalcLimparMemoria(){
	let estilo = `
	#avjt-limpar-memoria{
		position:fixed;
		top:0;
		left:calc(50% - 100px - 25px) !important;
		width:200px;
		z-index:9999;
	}`
	estilizar('',estilo,'avjt-botao-limpar-memoria')
}

function estilizarBotaoCertificarNoPje(){
	let estilo = `
	botao[id^=avjt-]{
		animation:aparecer 1s ease-out 0s 1 both;
		border-radius:5px;
		color:rgba(var(--extensao-cor-branco),1);
		cursor:pointer;
		display:block;
		font-size:0.9rem;
		font-weight:600;
		line-height:20px;
		margin:0 auto;
		opacity:0.8 !important;
		padding:10px 10px 10px 25px;
		position:relative;
		text-align:center;
		width:fit-content;
	}
	botao[id^=avjt-]:hover{
		opacity:1 !important;
	}
	botao[id^=avjt-]:active{
		opacity:0.7 !important;
	}
	#avjt-certificar-devolvido,
	#avjt-certificar-email,
	#avjt-certificar-entregue,
	#avjt-certificar-sigeo,
	#avjt-certificar-siscondj	
	{
		bottom:10px;
		width:320px;
	}
	#avjt-certificar-devolvido,
	#avjt-certificar-email,
	#avjt-certificar-entregue
	{
		position:fixed;
	}

	#avjt-certificar-devolvido{
		right:10px;
	}
	#avjt-certificar-email{
		left:calc(50% - 160px - 25px);
	}
	#avjt-certificar-siscondj{
		margin-top:30px;
	}
	#avjt-certificar-entregue{
		left:10px;
	}
	botao[id^="avjt-certificar-siscondj"]{
		margin:20px auto 0 auto;
	}
	.sigeo-especialidades{
		padding:5px 10px 5px 30px !important;
	}
	`
	estilizar('',estilo,'avjt-botao-certificar')
}

function estilizarConectividadeSocial(){
	let estilo = `
	table#btn{
		background:rgba(var(--extensao-cor-branco),1);
		bottom:0;
		left:0;
		position:fixed;
	}
	table#btn br{
		display:none;
	}
	table#btn img{
		height:25px;
	}
	`
	estilizar('',estilo,'avjt-conectividade')
}

function estilizarSiscondj(){
	let estilo = `
	div#header{
		margin:0 !important;
	}
	#divmsg,
	.textoSubtituloHeaderEsquerda
	{
		display:none !important;
	}
	[aria-describedby="div_pdf_alvara"]{
		left:5% !important;
		width:90% !important;
	}
	#div_pdf_alvara{
		width:100% !important;
	}
	br,
	#rodape
	{
		display:none !important;
	}`
	estilizar('',estilo,'avjt-siscondj')
}

async function botaoCertificarOcultarAoClicar(){
	let botoes = document.querySelectorAll('[id*=avjt-certificar]')
	botoes.forEach(botao => botao.style.visibility = 'hidden')
	await aguardar(100)
	botoes.forEach(botao => botao.style.visibility = 'visible')	
}