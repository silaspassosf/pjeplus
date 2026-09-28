class EditorDocumento {
    variaveisParaEditorDeTexto = [
	['[maisPje:exequente]',''],
	['[maisPje:executado]',''],
	['[maisPje:valorDivida]',''],
	['[maisPje:dataDaDivida]',''],
	['[maisPje:justiçagratuita]',''],
	['[maisPje:justiçagratuitaData]',''],
	['[maisPje:transitoJulgado]',''],
	['[maisPje:custasArbitradas]',''],
	['[maisPje:audiencia:data]',''],
	['[maisPje:audiencia:hora]',''],
	['[maisPje:chaveDeAcesso:id]','Chave de Acesso'],
	['[maisPje:chaveDeAcesso:chave]','Chave de Acesso'],
	['[maisPje:petiçãoInicial:id]','Petição Inicial'],
	['[maisPje:petiçãoInicial:chave]','Petição Inicial'],
	['[maisPje:últimaContestação:id]','Contestação'],
	['[maisPje:últimaContestação:chave]','Contestação'],
	['[maisPje:últimaManifestação:id]','Manifestação'],
	['[maisPje:últimaManifestação:chave]','Manifestação'],
	['[maisPje:últimaSentença:id]','Sentença'],
	['[maisPje:últimaSentença:chave]','Sentença'],
	['[maisPje:últimoAcórdão:id]','Acórdão'],
	['[maisPje:últimoAcórdão:chave]','Acórdão'],
	['[maisPje:últimoDespacho:id]','Despacho'],
	['[maisPje:últimoDespacho:chave]','Despacho'],
	['[maisPje:últimaDecisão:id]','Decisão'],
	['[maisPje:últimaDecisão:chave]','Decisão'],
	['[maisPje:últimaAta:id]','Ata da Audiência'],
	['[maisPje:últimaAta:chave]','Ata da Audiência'],
	['[maisPje:últimaCertidão:id]','Certidão'],
	['[maisPje:últimaCertidão:chave]','Certidão'],
	['[maisPje:últimoCálculo:id]','Planilha de Cálculos'],
	['[maisPje:últimoCálculo:chave]','Planilha de Cálculos'],
    ['[maisPje:últimoAlvará:id]','Alvará'],
	['[maisPje:últimoAlvará:chave]','Alvará'],
	['[maisPje:último:id]','*'],
	['[maisPje:último:chave]','*'],
	['[maisPje:último:anexos]','*'], //traz a lista de ids dos anexos "Id.xxx, Id.xxx, Id.xxx", contendo a lista de ids dos anexos do último documento juntado
	['[maisPje:perito]',''],
	['[maisPje:exequente:telefone]',''],
    ['[maisPje:perguntar:texto]',''],
    ['[maisPje:perguntar:data]',''],
    ['[maisPje:perguntar:valor]',''],
    ['[maisPje:magistrado:modulo8]','']
    ];
    async habilitarSubstituirAoColar() {
        const editorDiv = await esperarElemento(SELETORES.editor.areaConteudo);
        if (editorDiv) {
            editorDiv.addEventListener('paste', () => {
                setTimeout(async () => {
                    const conteudo = editorDiv.textContent;
                    if (conteudo.includes('[maisPje:')) {
                        await substituirVariaveisEditorTexto();
                    }
                }, 0);
            });
        }
    }
}
