function getUrlBaseSiscondj() {
    const url = preferencias.configURLs.urlSiscondj;
    if (url && url.includes("/pages")) {
        return url.substring(0, url.search("/pages"));
    }
    return url;
}

class BotaoAtalhoNovaAba {
    constructor({ id, icone, aria, cor_de_fundo, gerarSufixo = '', onClick, condicao_adicionar = () => true,
                    gerarPrefixo = () => document.location.href.substring(0, document.location.href.search("/pjekz/"))
    }) {
        this.id = id;
        this.icone = icone;
        this.aria = aria;
        this.cor_de_fundo = cor_de_fundo;
        this.gerarSufixo = gerarSufixo;
        this.condicao_adicionar = condicao_adicionar;
        this.onClick = onClick || this.abrirAtalhoemNovaJanela.bind(this);
        this.getPrefixo = gerarPrefixo;
    }

    async gerarUrl(idProcesso, idDocumento, nrProcesso) {
		let prefixo = '';
        let sufixo;

        if (typeof this.getPrefixo === 'function') {
            prefixo = this.getPrefixo();
        } else if (typeof this.getPrefixo === 'string') {
            prefixo = this.getPrefixo;
        }
    
        if (typeof this.gerarSufixo === 'function') {
            sufixo = await this.gerarSufixo(idProcesso, idDocumento, nrProcesso);
        } else if (typeof this.gerarSufixo === 'string') {
            sufixo = this.gerarSufixo;
        }
		
		if (sufixo.includes(prefixo)) {
			return `${sufixo}`;
		} else {
			return `${prefixo}${sufixo}`;
		}
    }

    async abrirAtalhoemNovaJanela(idProcesso, idDocumento, nrProcesso) {
		const url = await this.gerarUrl(idProcesso, idDocumento, nrProcesso);
		let win = window.open(decodeURI(url), '_blank');
        win.focus();
	}

    criar_botao(posicao) {
        let span = document.createElement("span");
        span.id = this.id;
        span.style = `--p:${posicao};--d:-1;--c:0;`;
        let link = document.createElement("a");
        link.setAttribute('aria-label', this.aria);
        link.setAttribute('maisPje-tooltip-menuEsquerda', this.aria);
        link.setAttribute('maisPje-tooltip-menuDireita', this.aria);
        link.setAttribute('maisPje-tooltip-menuAcima', this.aria);
        link.setAttribute('maisPje-tooltip-menuAbaixo', this.aria);
        link.style.backgroundColor = this.cor_de_fundo;
        link.onmouseenter = () => { link.style.backgroundColor = 'dimgray'; };
        link.onmouseleave = () => { link.style.backgroundColor = this.cor_de_fundo; };
        link.onclick = this.onClick;
        let i = document.createElement("i");
        i.className = this.icone;
        link.appendChild(i);
        span.appendChild(link);
        return span;
    }
}

function getAtalhosNovaAba() {
    const atalhos = {
        consultaRapidaPJe: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consulta_rapida",
            icone: "icone bolt t100 tamanho40",
            aria: "Consulta Rápida de Processo",
            cor_de_fundo: "orangered",
            onClick: () => consultaRapidaPJE(),
        }),
        consultarProcessos: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_processo",
            icone: "icone menuConvenio_search t100 tamanho60",
            aria: "Consultar Processo",
            cor_de_fundo: "orangered",
            gerarSufixo: '/administracao/consulta/processo/index'
        }),
        consultarProcessosTerceiros: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_processo_terceiros",
            icone: "icone search-plus t100 tamanho60",
            aria: "Consultar Processo Terceiros",
            cor_de_fundo: "orangered",
            gerarSufixo: '/consultaprocessual/consulta-terceiros'
        }),
        consultarPesquisaTextual: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_pesquisa_textual",
            icone: "icone search-textual t100 tamanho60",
            aria: "Pesquisa Textual",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pesquisa-textual',
            condicao_adicionar: () => preferencias.grau_usuario === 'segundograu'
        }),
        abrirPJeAntigo: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_pje_antigo",
            icone: "icone archive t100 tamanho60",
            aria: "PJe Antigo",
            cor_de_fundo: "orangered",
            gerarSufixo: `/${preferencias.grau_usuario}/Painel/painel_usuario/list.seam`
        }),
        abrirPauta: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_pauta",
            icone: "icone calendar t100 tamanho60",
            aria: "Abrir Pauta",
            cor_de_fundo: "orangered",
            gerarSufixo: async (idProcesso, idDocumento, nrProcesso) => {
                if (document.location.href.includes('/detalhe')) {
                    idProcesso = document.location.href.substring(
                        document.location.href.search("/processo/") + 10,
                        document.location.href.search("/detalhe")
                    );
                    let dados = await obterDadosProcessoViaApi(idProcesso);
                    return `/pjekz/pauta-audiencias?maisPje=true&numero=${dados.numero}&rito=${dados.classeJudicial.sigla}&fase=${dados.labelFaseProcessual}`;
                } else {
                    return '/pjekz/pauta-audiencias';
                }
            }
        }),
        aviso: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_criar_avisos",
            icone: "icone comment t100 tamanho60",
            aria: "Criar/Editar Avisos",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/quadro-avisos'
        }),
        consultarModelos: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_modelos",
            icone: "icone file t100 tamanho50",
            aria: "Modelos",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/configuracao/modelos-documentos'
        }),
        consultarAdvogados: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_consultar_advogados",
            icone: "icone user-tie t100 tamanho60",
            aria: "Consultar Advogados",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pessoa-fisica?advogado'
        }),
        consultarPeritos: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_peritos",
            icone: "icone user-md-solid t100 tamanho60",
            aria: "Consultar Peritos",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pessoa-fisica?perito'
        }),
        consultarPessoaFisica: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_pessoas",
            icone: "icone user t100 tamanho60",
            aria: "Consultar Pessoa Física",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pessoa-fisica'
        }),
        consultarPessoaJuridica: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_pessoa_juridica",
            icone: "icone building t100 tamanho60",
            aria: "Consultar Pessoa Jurídica",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pessoa-juridica'
        }),
        abrirDetalhesPainelAntigo: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_detalhes_pje_antigo",
            icone: "icone search t100 tamanho60",
            aria: "Abrir Processo no Painel Antigo",
            cor_de_fundo: "darkcyan",
            gerarSufixo: (idProcesso, idDocumento, nrProcesso) => {
                idProcesso = document.location.href.substring(
                    document.location.href.search("/processo/") + 10,
                    document.location.href.search("/detalhe")
                );
                return `/${preferencias.grau_usuario}/Processo/ConsultaProcesso/Detalhe/list.seam?id=${idProcesso}`;
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        preferenciaF2: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_preferencia_f2",
            icone: "icone keyboard t100 tamanho60",
            aria: (!preferencias.tempF2) ? "Atalho F2: [definir]" : "Atalho F2: " + preferencias.tempF2,
            cor_de_fundo: "darkcyan",
            onClick: async function () {
                preferencias.tempF2 = await criarCaixaDeSelecaoComAAs('Escolha uma Ação Automatizada para guardar no atalho "F2"');
                let guardarStorage1 = browser.storage.local.set({ 'tempF2': preferencias.tempF2 });
                Promise.all([guardarStorage1]).then(values => {
                    browser.runtime.sendMessage({ tipo: 'criarAlerta', valor: 'Janela Detalhes do Processo: definida a tecla F2 como atalho da AA ' + preferencias.tempF2 + '...', icone: '5' });
                    tempTitle = (!preferencias.tempF2 || preferencias.tempF2 == 'Nenhum') ? "Atalho F2: [definir]" : "Atalho F2: " + preferencias.tempF2;
                    this.setAttribute('aria-label', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuEsquerda', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuDireita', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuAcima', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuAbaixo', tempTitle);
					criarAreaDoPreferenciasF2();
                });
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        preferenciaF3: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_preferencia_f3",
            icone: "icone keyboard t100 tamanho60",
            aria: (!preferencias.tempF3) ? "Atalho F3: [definir]" : "Atalho F3: " + preferencias.tempF3,
            cor_de_fundo: "darkcyan",
            onClick: async function () {
                preferencias.tempF3 = await criarCaixaDeSelecaoComAAs('Escolha uma Ação Automatizada para guardar no atalho "F3"');
                let guardarStorage1 = browser.storage.local.set({ 'tempF3': preferencias.tempF3 });
                Promise.all([guardarStorage1]).then(values => {
                    browser.runtime.sendMessage({ tipo: 'criarAlerta', valor: 'Janela Detalhes do Processo: definida a tecla F3 como atalho da AA ' + preferencias.tempF3 + '...', icone: '5' });
                    tempTitle = (!preferencias.tempF3 || preferencias.tempF3 == 'Nenhum') ? "Atalho F3: [definir]" : "Atalho F3: " + preferencias.tempF3;
                    this.setAttribute('aria-label', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuEsquerda', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuDireita', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuAcima', tempTitle);
                    this.setAttribute('maisPje-tooltip-menuAbaixo', tempTitle);
					criarAreaDoPreferenciasF3();
                });
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        acoesAutomatizadasLote: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_aa_lote",
            icone: "icone aaLote t100 tamanho60",
            aria: "Ações automatizadas em lote",
            cor_de_fundo: "darkcyan",
            onClick: function () { acoesEmLote() },
        }),
		// os itens abaixo atualmente nao fazem parte dos botoes de atalho, logo a condicao_adicionar sera sempre false para eles.
        abrirDocumento: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_documento",
            icone: "icone file-alt t100 tamanho60",
            aria: "Abrir Documento",
            cor_de_fundo: "orangered",
            gerarSufixo: (idProcesso, idDocumento, nrProcesso) => `/pjekz/processo/${idProcesso}/documento/${idDocumento}/conteudo`,
            condicao_adicionar: () => false
        }),
        consultarExtrato: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_extrato",
            icone: "icone file-invoice-dollar t100 tamanho60",
            aria: "Consultar Extrato",
            cor_de_fundo: "orangered",
            gerarSufixo: async (idProcesso, idDocumento, nrProcesso) => {
                let dados = await obterDadosProcessoViaApi(idProcesso);
                let dataAutuacao = new Date(dados.autuadoEm);
                let dataAutuacaoFormatada = ("0" + dataAutuacao.getDate()).slice(-2) + '.' +
                    ("0" + (dataAutuacao.getMonth() + 1)).slice(-2) + '.' +
                    dataAutuacao.getFullYear();
                return `/sif/consultar-extrato/${nrProcesso}/104/${idDocumento}?maisPJe_SIF_bt_extrato&dtAutuacao=${dataAutuacaoFormatada}`;
            },
            condicao_adicionar: () => false
        }),
        procurarExecucao: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_procurar_execucao",
            icone: "icone gavel t100 tamanho60",
            aria: "Procurar Execução",
            cor_de_fundo: "orangered",
            gerarSufixo: async (idProcesso, idDocumento, nrProcesso) => {
                let gigsURL = preferencias.configURLs.urlSAOExecucao;
                if (gigsURL == "") {
                    criarCaixaDeAlerta("DICA", 'Consulte o relatório do SAO e verifique se o seu TRT possui um relatório específico para este atividade. Caso exista encaminhe um email para fernando.marcon@trt12.jus.br que adicionaremos o atalho aqui.', 20);
                    return;
                }
                return gigsURL;
            },
            condicao_adicionar: () => false
        }),
        abrirSiscondj: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_siscondj",
            icone: "icone balance-scale t100 tamanho60",
            aria: "Abrir Siscondj",
            cor_de_fundo: "orangered",
            gerarPrefixo: getUrlBaseSiscondj,
            gerarSufixo: '/pages/movimentacao/conta/new',
            condicao_adicionar: () => false
        }),
        abrirSIFNovoBoleto: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_sif_novo_boleto",
            icone: "icone money-check-alt t100 tamanho60",
            aria: "Abrir SIF Novo Boleto",
            cor_de_fundo: "orangered",
            gerarSufixo: '/sif/boleto/novo',
            condicao_adicionar: () => false
        }),
		abrirSISCONDJNovoBoleto: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_siscondj_novo_boleto",
            icone: "icone money-check-alt t100 tamanho60",
            aria: "Abrir SISCONDJ Novo Boleto",
            cor_de_fundo: "orangered",
            gerarPrefixo: getUrlBaseSiscondj,
            gerarSufixo: '/pages/guia/publica/',
            condicao_adicionar: () => false
        }),
		anexarDocumentos: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_anexar_documentos",
            icone: "icone paperclip t100 tamanho60",
            aria: "Anexar Documentos",
            cor_de_fundo: "orangered",
            gerarSufixo: async (idProcesso, idDocumento, nrProcesso) => {
                let dados = await obterIdProcessoViaApi(nrProcesso);
                if (!dados[0].idProcesso) {
                    criarCaixaDeAlerta('ALERTA', 'Não foi possível obter o ID do processo através do número encontrado (' + nrProcesso + ').', 15);
                    return;
                }
                return `/pjekz/processo/${dados[0].idProcesso}/documento/anexar`;
            },
            condicao_adicionar: () => false
        }),
		abrirPJeCalc: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_pjecalc",
            icone: "icone calculator t100 tamanho60",
            aria: "Pesquisa Textual",
            cor_de_fundo: "orangered",
            gerarSufixo: async (parametro) => {
               
                return `/pjecalc/pages/principal.jsf${parametro}`;
            },
            condicao_adicionar: () => false
        }),
        conferirAlvaras: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_conferir_alvara",
            icone: "icone search-dollar2 t100 tamanho60",
            aria: "Conferir Alvarás",
            cor_de_fundo: "#0078aa",
            onClick: async function () { 
                let opcoes = await criarCaixaSelecao(['Caixa Econômica Federal','Banco do Brasil'],titulo='Escolha a Instituição Financeira');
                let url;
                if (opcoes == 'Caixa Econômica Federal') {
                    janelaAlvarasSIF('AGUARDANDO_CONFERENCIA');
                    //https://pje.trt12.jus.br/pjekz/escaninho/situacao-alvara
                } else {
                    //https://siscondj.trt12.jus.br/siscondj/pages/mandado/acompanhamento/new
                    url = getUrlBaseSiscondj();
                    url += '/pages/mandado/acompanhamento/new?conferirAlvara';
                    let win = window.open(decodeURI(url), '_blank');
                    win.focus();
                }

            },
            condicao_adicionar: () => document.querySelector('pje-cabecalho-perfil span[class="papel-usuario"]')?.innerText == 'Diretor de Secretaria'
        })
    };
    return atalhos;
}
