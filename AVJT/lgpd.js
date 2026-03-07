function lgpd(){
	remover('avjt-lgpd')
	if(!CONFIGURACAO?.lgpd?.ativado) return

	let elementos = [
		'#depositosList',
		'[email]',
		'td.rich-table-cell',
		'div.usuario *',
		'[name="dataItemTimeline"]',
		'.cabecalho-esquerda mat-card-subtitle',
		'.container-html *',
		'.canvasWrapper',
		'.info-usuario',
		'painel-superior partes',
		'pje-data-table .sobrescrito',
		'pje-data-table .texto-sigilo',
		'pje-data-table[nametabela="Tabela de Processos"] tr > td:nth-child(5)',
		'pje-data-table[nametabela="Tabela de Processos"] tr > td:nth-child(7)',
		'pje-data-table[nametabela="Tabela de Processos"] tr > td:nth-child(8)',
		'pje-data-table[nametabela="Tabela de Processos"] tr > td:nth-child(9)',
		'pje-data-table[nametabela="Tabela de Atividades"] tr > td:nth-child(5)',
		'pje-data-table[nametabela="Tabela de Atividades"] tr > td:nth-child(8)',
		'pje-data-table[nametabela="Tabela de Expedientes"] tr > td:nth-child(4) span',
		'pje-data-table[nametabela="Tabela de Expedientes"] tr > td:nth-child(7) span',
		'pje-data-table[nametabela="Tabela de Expedientes"] .texto-vermelho',
		'pje-gigs-menu-relatorio pje-data-table[nametabela="Tabela de Atividades"] tr > td:nth-child(3)',
		'pje-gigs-menu-relatorio pje-data-table[nametabela="Tabela de Atividades"] tr > td:nth-child(6)',
		'pje-gigs-menu-relatorio pje-data-table[nametabela="Tabela de Comentários"] tr > td:nth-child(3)',
		'pje-gigs-menu-relatorio pje-data-table[nametabela="Tabela de Comentários"] tr > td:nth-child(4)',
		'pje-gigs-menu-relatorio pje-data-table[nametabela="Tabela de Comentários"] tr > td:nth-child(5)',
		'pje-data-table[nametabela="Tabela Petições"] tr > td:nth-child(10)',
		'pje-data-table[nametabela="Tabela de Perícias"] tr > td:nth-child(5)',
		'.mat-tooltip',
		'.rodape-post-it *',
		'.partes-corpo',
		'.partes-representante span',
		'pje-responsaveis-audiencia',
		'.post-it-conteudo',
		'section.partes'
	]

	let seletores = CONFIGURACAO?.lgpd?.seletores?.trim().replace(/[,]$/gi,'') || ''
	if(seletores) seletores += ','
	elementos.forEach(elemento => {
		seletores += elemento+','+elemento+'::selection,'
	})
	seletores = seletores.replace(/[,]$/gi,'')
	estilizar('',`${seletores}{filter:blur(6px) !important;}`,'avjt-lgpd')
}