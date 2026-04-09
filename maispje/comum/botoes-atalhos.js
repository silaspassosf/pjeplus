function getUrlBaseSiscondj() {
    const url = preferencias.configURLs.urlSiscondj;
    console.log(url)
    if (url && url.includes("/pages")) {
        return url.substring(0, url.search("/pages"));
    }
    return url;
}

class BotaoAtalhoNovaAba {
    constructor({ id, icone, texto='', aria, cor_de_fundo, gerarSufixo = '', onClick = undefined, condicao_adicionar = () => true,
                    gerarPrefixo = () => document.location.origin
    }) {
        this.id = id;
        this.icone = icone;
        this.texto = texto;
        this.aria = aria;
        this.cor_de_fundo = cor_de_fundo;
        this.gerarSufixo = gerarSufixo;
        this.condicao_adicionar = condicao_adicionar;
        this.onClick = onClick || this.abrirAtalhoemNovaJanela.bind(this);
        this.originalOnClick = onClick;
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
        const tag = !!this.originalOnClick ? 'button' : 'a';
        let link = document.createElement(tag);        
        link.setAttribute('aria-label', this.aria);
        link.setAttribute('maisPje-tooltip-menuEsquerda', this.aria);
        link.setAttribute('maisPje-tooltip-menuDireita', this.aria);
        link.setAttribute('maisPje-tooltip-menuAcima', this.aria);
        link.setAttribute('maisPje-tooltip-menuAbaixo', this.aria);
        link.style.backgroundColor = this.cor_de_fundo;
        link.onmouseenter = () => { link.style.filter = 'grayscale(1)' };
        link.onmouseleave = () => { link.style.filter = 'grayscale(0)' };
        const acao = this.onClick;
        const executarAcao =  (event) => {
            event.preventDefault();
            acao();
          };
        if (!!this.originalOnClick) {
            link.addEventListener('click',executarAcao);
        } else if (link instanceof HTMLAnchorElement) {
            if ( typeof this.gerarSufixo === 'function') {
                link.addEventListener('click',executarAcao);
                link.href = '#';
            } else {
                this.gerarUrl().then(url => link.href = url);
                link.target = '_blank';
            }
        }
        let i = document.createElement("i");
        i.className = this.icone;
        i.innerText = this.texto;
        link.appendChild(i);
        span.appendChild(link);
        return span;
    }
}

function getAtalhosNovaAba() {
    const atalhos = {
        consultaRapidaPJe: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consulta_rapida",
            icone: "icone bolt t100 tamanho45",
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
            gerarSufixo: '/pjekz/pessoa-fisica?pagina=1&tamanhoPagina=10&especializacao=1&situacao=1'
        }),
        consultarPeritos: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_consultar_peritos",
            icone: "icone user-md-solid t100 tamanho60",
            aria: "Consultar Peritos",
            cor_de_fundo: "orangered",
            gerarSufixo: '/pjekz/pessoa-fisica?pagina=1&tamanhoPagina=10&tipoPerito=AJJT&especializacao=32&situacao=1'
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
            icone: "icone search t100 tamanho65",
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
            icone: "textoComoIcone t100 tamanho70",
            texto: "F2",
            aria: (!preferencias.tempF2) ? "Atalho F2: [definir]" : "Atalho F2: " + preferencias.tempF2,
            cor_de_fundo: (!preferencias.tempF2) ? "darkcyan" : "rgb(47, 138, 88)",
            onClick: async function () {
                const button = document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f2 button');
                preferencias.tempF2 = await criarCaixaDeSelecaoComAAs(preferencias, 'Escolha uma Ação Automatizada para guardar no atalho "F2"', preferencias.tempF2, button);
                let guardarStorage1 = browser.storage.local.set({ 'tempF2': preferencias.tempF2 });
                Promise.all([guardarStorage1]).then(values => {
                    browser.runtime.sendMessage({ tipo: 'criarAlerta', valor: 'Janela Detalhes do Processo: definida a tecla F2 como atalho da AA ' + preferencias.tempF2 + '...', icone: '5' });
                    tempTitle = (!preferencias.tempF2 || preferencias.tempF2 == 'Nenhum') ? "Atalho F2: [definir]" : "Atalho F2: " + preferencias.tempF2;
                    button?.setAttribute('aria-label', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuEsquerda', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuDireita', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAcima', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAbaixo', tempTitle);
					criarAreaDoPreferenciasF2();
                });
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        preferenciaF3: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_preferencia_f3",
            icone: "textoComoIcone t100 tamanho70",
            texto: "F3",
            aria: (!preferencias.tempF3) ? "Atalho F3: [definir]" : "Atalho F3: " + preferencias.tempF3,
            cor_de_fundo: (!preferencias.tempF3) ? "darkcyan" : "rgb(159, 56, 18)",            
            onClick: async function () {
                const button = document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f3 button');
                preferencias.tempF3 = await criarCaixaDeSelecaoComAAs(preferencias, 'Escolha uma Ação Automatizada para guardar no atalho "F3"', preferencias.tempF3, button);
                let guardarStorage1 = browser.storage.local.set({ 'tempF3': preferencias.tempF3 });
                Promise.all([guardarStorage1]).then(values => {
                    browser.runtime.sendMessage({ tipo: 'criarAlerta', valor: 'Janela Detalhes do Processo: definida a tecla F3 como atalho da AA ' + preferencias.tempF3 + '...', icone: '5' });
                    tempTitle = (!preferencias.tempF3 || preferencias.tempF3 == 'Nenhum') ? "Atalho F3: [definir]" : "Atalho F3: " + preferencias.tempF3;
                    button?.setAttribute('aria-label', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuEsquerda', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuDireita', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAcima', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAbaixo', tempTitle);
					criarAreaDoPreferenciasF3();
                });
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        preferenciaF4: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_preferencia_f4",
            icone: "textoComoIcone t100 tamanho70",
            texto: "F4",
            aria: (!preferencias.tempF4) ? "Atalho F4: [definir]" : "Atalho F4: " + preferencias.tempF4,
            cor_de_fundo: (!preferencias.tempF4) ? "darkcyan" : "rgb(15, 131, 200)",
            onClick: async function () {
                const button = document.querySelector('#maisPje_menuKaizen_itemmenu_preferencia_f4 button');
                preferencias.tempF4 = await criarCaixaDeSelecaoComAAs(preferencias, 'Escolha uma Ação Automatizada para guardar no atalho "F4"', preferencias.tempF4, button);
                let guardarStorage1 = browser.storage.local.set({ 'tempF4': preferencias.tempF4 });
                Promise.all([guardarStorage1]).then(values => {
                    browser.runtime.sendMessage({ tipo: 'criarAlerta', valor: 'Janela Detalhes do Processo: definida a tecla F4 como atalho da AA ' + preferencias.tempF4 + '...', icone: '5' });
                    tempTitle = (!preferencias.tempF4 || preferencias.tempF4 == 'Nenhum') ? "Atalho F4: [definir]" : "Atalho F4: " + preferencias.tempF4;
                    button?.setAttribute('aria-label', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuEsquerda', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuDireita', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAcima', tempTitle);
                    button?.setAttribute('maisPje-tooltip-menuAbaixo', tempTitle);
					criarAreaDoPreferenciasF4();
                });
            },
            condicao_adicionar: () => document.location.href.search("/detalhe") > -1
        }),
        acoesAutomatizadasLote: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_aa_lote",
            icone: "icone aaLote t100 tamanho70",
            aria: "Ações automatizadas em lote",
            cor_de_fundo: "darkcyan",
            onClick: () => acoesEmLote(),
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
            gerarSufixo: (nome,documento) => {
                let gigsURL = preferencias.configURLs.urlSAOExecucao;
                if (gigsURL == "") {
                    criarCaixaDeAlerta("DICA", 'Consulte o relatório do SAO e verifique se o seu TRT possui um relatório específico para este atividade. Caso exista encaminhe um email para fernando.marcon@trt12.jus.br que adicionaremos o atalho aqui.', 20);
                    return;
                } else if (gigsURL.includes('?maisPje=true')) {  
                    return gigsURL + `&cpfcnpj=${documento}&fase=Execução`;
                } else {
                    return gigsURL + `?maisPje=true&cpfcnpj=${documento}&fase=Execução`;
                }
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
                if (!idProcesso) {
                    idProcesso = await obterIdProcessoViaApi(nrProcesso);
                }

                if (!idProcesso) {
                    criarCaixaDeAlerta('ALERTA', 'Não foi possível obter o ID do processo através do número encontrado (' + nrProcesso + ').', 15);
                    return;
                }
                
                return `/pjekz/processo/${idProcesso}/documento/anexar`;
            },
            condicao_adicionar: () => false
        }),
		abrirPJeCalc: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_abrir_pjecalc",
            icone: "icone calculator t100 tamanho60",
            aria: "Pesquisa Textual",
            cor_de_fundo: "orangered",
            gerarSufixo: async (parametro) => `/pjecalc/pages/principal.jsf${parametro}`,
            condicao_adicionar: () => false
        }),
        conferirAlvaras: new BotaoAtalhoNovaAba({
            id: "maisPje_menuKaizen_itemmenu_conferir_alvara",
            icone: "icone search-dollar2 t100 tamanho70",
            aria: "Conferir Alvarás",
            cor_de_fundo: "#0078aa",
            onClick: async function () { 
                let opcoes = await criarCaixaSelecao(['Caixa Econômica Federal','Banco do Brasil'],titulo='Escolha a Instituição Financeira');
                if (opcoes == 'Caixa Econômica Federal') {
                    janelaAlvarasSIF('SIF');
                } else {

                    // let opcoes = await criarCaixaSelecao(['Sim','Não'], 'Você já efetuou o login no sistema SISCONDJ?','Nenhum',false,true);
			        // if (!opcoes) {
                        janelaAlvarasSISCONDJ('SISCONDJ');
                    // } else {
                    //     fundo(false)
                    //     await criarCaixaDeAlerta('Atenção','Para utilizar a funcionalidade de CONFERIR ALVARÁS é obrigatório que vc já esteja logado no sistema SISCONDJ!\n Faça o login e execute novamente a função.',60,0,"Fazer login");
                    //     browser.runtime.sendMessage({tipo: 'criarJanela', url: preferencias.configURLs.urlSiscondj, posx: preferencias.gigsTarefaLeft, posy: preferencias.gigsTarefaTop, width: preferencias.gigsTarefaWidth, height: preferencias.gigsTarefaHeight});                        
                    // }
                    
                }

            }
        })
    };
    return atalhos;
}