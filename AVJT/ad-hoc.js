async function adHoc(){

	return
	triagemInicial()
	async function triagemInicial(){
		esperar('#avjt-botao-documento-notificar',true,true).then(async (botao) => {
			clicar(botao)
			await aguardar(15000)
			fechar()
		})
		esperar('[aria-label="Inserir modelo de documento"]',true,true).then(async (botao) => {
			await aguardar(100)
			clicar(botao)
			await aguardar(1000)
			clicar('.metadados [aria-label="Salvar"]')
			await aguardar(1000)
			clicar('[aria-label="Finalizar minuta"]')

		})
		esperar('pje-transicao-tarefa',true,true).then(async (corpo) => {
			window.onfocus = async () => {
				await aguardar(1000)
				irParaTarefa('Análise')
				irParaTarefa('Aguardando prazo')
				await aguardar(4000)
				fechar()
			}
		})
		async function irParaTarefa(tarefa=''){
			let botao = await esperar('[aria-label="'+tarefa+'"]',true,true)
			await aguardar(500)
			clicar(botao)
		}
	}
/*
	notificacaoVolkswagen()

	async function notificacaoVolkswagen(){
		esperar('[data-tooltip="Enviar"]',true,true).then(async (botao) => {
			await aguardar(1500)
			window.focus()
			await aguardar(250)
			clicar(botao)
		})
		esperar('#avjt-botao-enviar-documento-por-email-citacao-especial',true,true).then(async (botao) => {
			clicar(botao)
			await aguardar(5000)
			fechar()
		})
		esperar('.area-conteudo .corpo',true,true).then(async (corpo) => {
			window.onfocus = async () => {
				colar()
			}
		})
		esperar('pje-transicao-tarefa',true,true).then(async (corpo) => {
			window.onfocus = async () => {
				irParaTarefa('Análise')
				await aguardar(3000)
				fechar()
			}
		})
		esperar('#avjt-certificar-email,pje-autuacao-dialogo',true,true).then(async (botao) => {
			await aguardar(1000)
			fechar()
		})
		esperar('[mattooltip="Confeccionar ato"]',true,true).then(async (botao) => {
			await aguardar(500)
			clicar('[mattooltip="Salva os expedientes"]')
			await aguardar(1000)
			clicar('[aria-label="Assinar ato(s)"]')
		})
		esperar('mat-dialog-container .alinhamento-div-botoes button',true,true).then(async (botao) => {
			await aguardar(250)
			clicar(botao)
			await aguardar(500)
			clicar('.metadados [aria-label="Salvar"]')
			await aguardar(500)
			clicar('[aria-label="Finalizar minuta"]')
		})
		esperar('[aria-label="Finalizar minuta"]',true,true).then(async (botao) => {
			botao.addEventListener('click',async () => {
				await aguardar(500)
				clicar('[name="btnIntimarSomentePoloPassivo"]')
				
			})
		})
		esperar('[aria-label="Descrição"]',true,true).then(campo => preencher('[aria-label="Descrição"]','Notificação por e-mail'))
		await aguardar(500)
		//irParaTarefa('Análise')
		irParaTarefa('Aguardando prazo')
	
	}

	async function irParaTarefa(tarefa=''){
		let botao = await esperar('[aria-label="'+tarefa+'"]',true,true)
		await aguardar(500)
		clicar(botao)
	}
*/
	/*
	//decisão Sobrestamento acordo
	await aguardar(500)
	irParaTarefa('Iniciar liquidação')
	await aguardar(700)
	irParaTarefa('Conclusão ao magistrado')
	irParaConclusao('Homologação de Cálculos')

	esperar('Meus Modelos',true,false,true).then(async () => {
		await aguardar(500)
		clicar('004. Sobrestamento por convenção das partes para cumprimento voluntário da obrigação',true)
	})
	
	esperar('[aria-label="Inserir modelo de documento"]',true,true).then(async (botao) => {
		await aguardar(500)
		clicar(botao)
		await aguardar(500)
		clicar('pje-duas-colunas button[aria-label="Salvar"]')
		esperar('[aria-label="Gravar os movimentos a serem lançados"]',true,true).then(async (gravar) => {
			await aguardar(500)
			clicar(gravar)
			await aguardar(1500)
			clicar('[mattooltip="Iniciar intimação automática?"] label')
			await aguardar(2000)
			clicar('[aria-label="14. Suspensão do Feito"]')
			await aguardar(3000)
			clicar('[aria-label="Enviar para assinatura"]')
		})
	})

	

	
	async function irParaConclusao(tarefa=''){
		let botao = await esperar(tarefa,true,true,true)
		await aguardar(500)
		clicar(botao)
	}
*/
	/*
		await esperar('[data-message-id]',true,true)

		//cumprimento()
		//analise()
		async function cumprimento(){
			let botao = await esperar('[aria-label="Cumprimento de providências"]',true,true)
			await aguardar(500)
			clicar(botao)
		}
	*/

	return

}