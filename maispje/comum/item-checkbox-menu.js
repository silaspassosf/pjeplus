class ItemCheckboxMenu {
    constructor(id, salvarOpcoes) {
        this.id = id;
		this.salvarOpcoes = salvarOpcoes
    }

	configurar(opcoes) {
		document.querySelector('#' + this.id).checked = opcoes[this.id]
		document.querySelector('#' + this.id).addEventListener('click', this.salvarOpcoes)
	}

	recuperarValor() {
		return { [this.id]: document.querySelector('#' + this.id).checked }
	}
}

function mergeItensMenu(menu) {
    return menu.reduce((acc, item) => {
        return { ...acc, ...item.recuperarValor() };
    }, {});
}


function getItensModulo1SemAtalhos(salvarOpcoes) {
    var itensMenu = [
        new ItemCheckboxMenu('gigsAbrirGigs', salvarOpcoes),
        new ItemCheckboxMenu('gigsAbrirTarefas', salvarOpcoes),
        new ItemCheckboxMenu('gigsApreciarPeticoes', salvarOpcoes),
        new ItemCheckboxMenu('gigsApreciarPeticoes2', salvarOpcoes),
        new ItemCheckboxMenu('gigsApreciarPeticoes3', salvarOpcoes),
        new ItemCheckboxMenu('gigsOcultarChips', salvarOpcoes),
        new ItemCheckboxMenu('gigsOcultarLembretes', salvarOpcoes),
        new ItemCheckboxMenu('gigsTirarSomLembretes', salvarOpcoes),
        new ItemCheckboxMenu('gigsCriarMenu', salvarOpcoes),
        new ItemCheckboxMenu('gigsCriarMenuGuardarNumeroProcesso', salvarOpcoes),
        new ItemCheckboxMenu('gigsCriarMenuAbrirPainelCopiaECola', salvarOpcoes),
        new ItemCheckboxMenu('sanearAJG', salvarOpcoes),
        new ItemCheckboxMenu('gigsPesquisaDeDocumentos', salvarOpcoes),
        new ItemCheckboxMenu('mapeamentoDeIDs', salvarOpcoes),
        new ItemCheckboxMenu('gigsCriarMenuAbrirPainelCopiaECola', salvarOpcoes),
        new ItemCheckboxMenu('guiaPersonalizadaDetalhes', salvarOpcoes),
        new ItemCheckboxMenu('ocultarPublicacoesDJEN', salvarOpcoes),
        new ItemCheckboxMenu('ocultarDocumentosExcluidos', salvarOpcoes),
    ]
    return itensMenu    
}
