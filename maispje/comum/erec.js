const cacheERec = {
  despachoERec: undefined,
  documentos: undefined,
};

const urlFuncoes = [
    {
        test: (href) => href.includes(".jus.br/erec/assistente"),
        exec: configurarAssistente
    },
    {
        test: (href) => href.includes(".jus.br/erec/painel"),
        exec: configurarTelaPrincipalERec
    },
    {
        test: (href) => href.includes(".jus.br/erec/importacao"),
        exec: configurarImportarProcessosErec
    },
]

/**
 *
 * @param {number} idDespacho
 * @returns {Promise<DespachoERec>}
 */
async function carregarDespachoERec(idDespacho) {
  if (!cacheERec?.despachoERec) {
    cacheERec.despachoERec = await apis.eRecDespachoPorId.executar(preferencias.trt, {
      idDespacho,
    });
  }
  return cacheERec.despachoERec;
}

/**
 *
 * @param {number} idProcesso
 * @returns {Promise<Documento[]>}
 */
async function carregarDocumentosProcessoErec(idProcesso) {
  if (!cacheERec?.documentos) {
    cacheERec.documentos = await apis.timelineProcesso.executar(preferencias.trt, {
    idProcesso,
    buscarMovimentos: "false",
  });
  }
  return cacheERec.documentos;
}
/**
 *
 * @param {HTMLElement} abaPressupostosExtrinsecos
 */
async function carregarDadosERec(abaPressupostosExtrinsecos) {

  const aposAssistente = location.pathname.split("/").filter(Boolean).pop();
  const idDespacho = Number(aposAssistente);
  const despachoERec = await carregarDespachoERec(idDespacho);
  const idProcesso = despachoERec.idProcesso;
  const documentos = await carregarDocumentosProcessoErec(idProcesso);

  const nomeRecorrente = await getNomeRecorrenteERec(
    abaPressupostosExtrinsecos
  );

  const representantes = await getNomeRepresentantesERec(
    despachoERec.recursos,
    nomeRecorrente
  );
  const documentosJuntadosRepresentantes = filtrarDocumentosRepresentantes(
    documentos,
    representantes
  );

  const documentosEAnexos = documentosJuntadosRepresentantes.flatMap((d) => [
    d,
    ...(d.anexos ?? []),
  ]);
  console.info({
    documentos,
    documentosJuntadosRepresentantes,
    documentosEAnexos,
  });
  preencherProcuracoes(
    documentosEAnexos,
    despachoERec.numeroProcesso,
    idProcesso
  );
  preencherPreparoERec(
    documentosEAnexos,
    despachoERec.numeroProcesso,
    idProcesso
  );

}

/** @type {(s: string | null) => string} */
function semAcento(s) {
  return (s ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleUpperCase()
    .trim();
}
/** @type {(doc: Documento, s: string | null) => boolean} */
function incluiTexto(doc, s) {
  return (
    semAcento(doc.tipo).includes(semAcento(s)) ||
    semAcento(doc.titulo).includes(semAcento(s))
  );
}
/** @type {(s: string | null) => string} */
const getIdLista = (idLista) => "maisPJE_eRec_lista_" + (idLista || "");

/**
 *
 * @param {Documento[]} documentosEAnexos
 * @param {string} numeroProcesso
 * @param {number} idProcesso
 * @param {string} idListaHTML
 * @param {HTMLElement} container
 * @param {string[]} tiposDocumento
 * @returns
 */
async function preencherDocumentos(
  documentosEAnexos,
  numeroProcesso,
  idProcesso,
  idListaHTML,
  container,
  tiposDocumento
) {
  // nao cria a lista 2x
  if (container?.querySelector(getIdLista(idListaHTML))) {
    return;
  }
  container.classList.add("erec-documentos-titulo");
  const filtrados = documentosEAnexos.filter((doc) => {
    return tiposDocumento.some((s) => incluiTexto(doc, s));
  });
  const ul = criarListaDocumentosERec(
    idListaHTML,
    filtrados,
    numeroProcesso,
    idProcesso
  );
  container.appendChild(ul);
}

/**
 *
 * @param {Documento[]} documentosEAnexos
 * @param {string} numeroProcesso
 * @param {number} idProcesso
 * @returns
 */
async function preencherSentencasEAcordaos(
  documentosEAnexos,
  numeroProcesso,
  idProcesso
) {
  const idListaRep = "sentencasAcordaos";
  const tituloBloco = "Sentenças e Acórdãos";
  const tiposDocumento = preferenciasParaLista(
    preferencias.extrasTiposDocumentoSentencasAcordao
  ); //["Sentença", "Acórdão"];
  const bloco = document.createElement("section");
  bloco.id = "maisPJE_section_" + idListaRep;
  bloco.classList = 'fonte-20';
  const titulo = document.createElement("h2");
  titulo.classList = 'fonte-20';
  titulo.textContent = tituloBloco;
  bloco.appendChild(titulo);
  preencherDocumentos(
    documentosEAnexos,
    numeroProcesso,
    idProcesso,
    idListaRep,
    bloco,
    tiposDocumento
  );

  const matCardContent = await esperarElemento("mat-card-content", "");
  matCardContent.insertAdjacentElement('afterbegin', bloco);
//   const preparo = await esperarElemento("mat-card-title", "Preparo");
//   const header = preparo.closest('mat-card-header');
//   header.insertAdjacentElement('afterend', bloco);
  // preparo.parentElement.appendChild(bloco);
}

/**
 *
 * @param {string} texto
 * @returns {string[]} lista com as opcoes
 */
function preferenciasParaLista(texto) {
  return texto?.split(",")?.map(semAcento)?.filter(Boolean) || [];
}
/**
 *
 * @param {Documento[]} documentosEAnexos
 * @param {string} numeroProcesso
 * @param {number} idProcesso
 * @returns
 */
async function preencherProcuracoes(
  documentosEAnexos,
  numeroProcesso,
  idProcesso
) {
  const idListaRep = "representacao";
  const tituloBloco = "Representação";
  const tiposDocumento = preferenciasParaLista(
    preferencias.extrasTiposDocumentoProcuracao
  ); // ["Procuração", "Substabelecimento"];
  const bloco = await esperarElemento("mat-card-title", tituloBloco);
  preencherDocumentos(
    documentosEAnexos,
    numeroProcesso,
    idProcesso,
    idListaRep,
    bloco,
    tiposDocumento
  );
}

/**
 *
 * @param {Documento[]} documentosEAnexos
 * @param {string} numeroProcesso
 * @param {number} idProcesso
 * @returns
 */
async function preencherPreparoERec(
  documentosEAnexos,
  numeroProcesso,
  idProcesso
) {
  const idListaRep = "guias";
  const documentosRelevantes =
    preferencias.extrasTiposDocumentoCustas +
    ", " +
    preferencias.extrasTiposDocumentoDepositoRecursal;
  const tiposDocumento = preferenciasParaLista(documentosRelevantes); // ["Guia", "emolumentos", "Custas", "Recursal", "GRU ", " GRU."]; // GRU acaba pegando grupo
  const tituloBloco = "Preparo";
  const bloco = await esperarElemento("mat-card-title", tituloBloco);
  preencherDocumentos(
    documentosEAnexos,
    numeroProcesso,
    idProcesso,
    idListaRep,
    bloco,
    tiposDocumento
  );
}

/**
 *
 * @param {string} idLista
 * @param {Documento[]} documentos
 * @param {string} numeroProcesso
 * @param {number} idProcesso
 * @returns {HTMLUListElement}
 */
function criarListaDocumentosERec(
  idLista,
  documentos,
  numeroProcesso,
  idProcesso
) {
  const ul = document.createElement("ul");
  ul.classList.add("erec-documentos-lista");
  ul.id = getIdLista(idLista);
  const itens = documentos.map((doc) => {
    const metadadosLink = montarURLsDocumentos(numeroProcesso, doc, idProcesso);
    const linkDoc = criarLinkComPreviewDocumento(metadadosLink);
    linkDoc.textContent = metadadosLink.documento.idUnicoDocumento;
    const li = document.createElement("li");
    li.id = "maisPJEdoc_" + doc.idUnicoDocumento;
    li.classList.add("erec-documento-item");
    // o acórdão eh HTML atualmente, por isso, abrimos a página do PJE para visualizar.
    // Para os PDFs, carregamos diretamente o documento, já que escala melhor (a janela do PJE tem um tamanho mínimo e corta parte do PDF se a largura for pequena)
    const pdfUrl = doc.tipo === 'Acórdão' ? metadadosLink.link : metadadosLink.conteudoDocumento;
    const botaoAbrirVisualizadorDocumento = configurarBotaoPDF(pdfUrl, doc.idUnicoDocumento)
    li.appendChild(botaoAbrirVisualizadorDocumento);
    li.appendChild(linkDoc);
    li.appendChild(criarBotaoCopiar(doc.idUnicoDocumento));
    return li;
  });
  ul.replaceChildren(...itens);
  return ul;
}

/**
 *
 * @param {HTMLElement} abaPressupostosExtrinsecos
 * @returns
 */
async function getNomeRecorrenteERec(abaPressupostosExtrinsecos) {
  console.info(abaPressupostosExtrinsecos);
  const card = abaPressupostosExtrinsecos.closest("mat-card");
  if (card) {
    const recurso = card.querySelector("mat-card-title");
    const tituloRecurso = recurso.textContent;
    // const recurso = await esperarElemento('td[class="titulo-recurso"]');
    // const tituloRecurso = recurso.innerText;
    const prefixoRecurso = "Recurso de ";
    const nomeRecorrente = tituloRecurso
      .substring(tituloRecurso.indexOf(prefixoRecurso) + prefixoRecurso.length)
      .trim();
    return nomeRecorrente;
  }
}

/**
 *
 * @param {RecursoERec[]} recursos
 * @param {string} nomeRecorrente
 * @returns {Promise<string[]>} nomes dos representantes da parte que interpos o recurso
 */
async function getNomeRepresentantesERec(recursos, nomeRecorrente) {
  const recursosRecorrente = recursos
    .filter((r) => r.titulo == nomeRecorrente)
    ?.map((r) => r.id);
  if (recursosRecorrente && recursosRecorrente.length) {
    const idRecurso = recursosRecorrente[0]; // nao precisa buscar mais ja que, as partes sao as mesmas nos recurso, so muda a denominação
    /** @type {ParteERec[]} */
    const partes = await apis.eRecPartesPorRecursoId.executar(
      preferencias.trt,
      { idRecurso }
    );
    const advogados = partes
      .filter((p) => p.nomePessoa == nomeRecorrente)
      .flatMap((p) => p.advogados);
    const nomesAdvs = advogados.map((adv) => semAcento(adv.nome));
    console.info({ advogados, nomesAdvs, partes });
    return nomesAdvs;
  }
  return [];
}
let abaPressupostosExtrinsecosAtual = undefined;
/**
 *
 * @param {HTMLElement} abaPressupostosExtrinsecos
 */
async function configurarPressupostosExtrinsecos(abaPressupostosExtrinsecos) {
  const obs = new MutationObserver(() => {
    const selected =
      abaPressupostosExtrinsecos.getAttribute("aria-selected") === "true";
    if (selected) {
      carregarDadosERec(abaPressupostosExtrinsecos);
      // obs.disconnect();
    }
  });
  obs.observe(abaPressupostosExtrinsecos, {
    attributes: true,
    attributeFilter: ["aria-selected"],
  });
}

function configurarBotaoPDF(pdfUrl, idDocumento) {
    // Criar o botão
    const button = document.createElement('button');
    button.id = 'maisPJE_verDoc' + idDocumento;
    // button.innerText = 'PDF';
    button.classList = 'matish-icon-button';
    const icone = document.createElement('i');
    icone.classList = 'far fa-file-alt';
    button.appendChild(icone);
    vincularTooltipAcessivel(button, 'Visualizar documento ' + idDocumento +' na mesma janela');
    // Lógica de esconder/exibir
    button.addEventListener('click', () => abrirFecharVisualizador(pdfUrl, true));

    return button;
}

async function configurarERec(href) {
    browser.runtime.sendMessage({
        tipo: "insertCSS",
        file: "maisPJe_erec.css",
    });
    browser.runtime.sendMessage({
        tipo: "insertCSS",
        file: "maisPJe_icones.css",
    });
    const match = urlFuncoes.find(u => u.test(href));
    match?.exec();
}

async function configurarAssistente() {
    criarContainerVisualizadorDocumentos(true);
    configurarObservablePressupostos();
    const processo = await obterIdNumeroProcessoDaTelaErec();
    const documentos = await carregarDocumentosProcessoErec(processo.idProcesso);
    const documentosEAnexos = documentos.flatMap((d) => [
        d,
        ...(d.anexos ?? []),
    ]);
    preencherSentencasEAcordaos(
        documentosEAnexos,
        processo.numeroProcesso,
        processo.idProcesso
    );
  configurarBotaoAdicionarGigsSemTese(processo.idProcesso);
}
/** @returns {idNumeroProcesso} id do processo. */
async function obterIdNumeroProcessoDaTelaErec() {
    const tituloProcesso = await esperarElemento(
        'span[class="texto-numero-processo"]'
    );
    const numeroProcesso = await extrairNumeroProcesso(tituloProcesso.innerText);
    const idProcesso = await obterIdProcessoViaApi(numeroProcesso);
    // console.info({ numeroProcesso, titulo: tituloProcesso, idProcesso });
    return {idProcesso, numeroProcesso};
}

async function configurarObservablePressupostos() {
  const assistente = await esperarElemento("pje-erec-assistente");
  const obs = new MutationObserver(async () => {
    const abaPressupostosExtrinsecos = await esperarElemento(
      'div[id*="mat-tab-label"]',
      "Pressup. Extrínsecos"
    );
    if (abaPressupostosExtrinsecos !== abaPressupostosExtrinsecosAtual) {
      abaPressupostosExtrinsecosAtual = abaPressupostosExtrinsecos;
      configurarPressupostosExtrinsecos(abaPressupostosExtrinsecos);
    }
  });
  obs.observe(assistente, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["aria-selected"],
  });
}
/**
 * abre o detalhes do processo e adiciona um GIGS com o tipo definido pelo usuários nas preferências da aplicação
 * @param {number} idProcesso
 */
async function configurarBotaoAdicionarGigsSemTese(idProcesso) {
  const tipoAtividadeGigs = preferencias.extrasERecTipoGigsSemTema;
  if (!tipoAtividadeGigs) {
    return;
  }
  const idGigs = "maisPJE_Gigs_sem_tese";
  if (document.getElementById(idGigs)) {
    return;
  }
  const botaoGigs = document.createElement("button");
  botaoGigs.id = idGigs;

  botaoGigs.classList = "matish-icon-button botao-gigs";
  const iconeGigs = document.createElement("i");
  iconeGigs.classList = "fa fa-tag";
  botaoGigs.appendChild(iconeGigs);
  const span = document.createElement('span');
  const label = `Gigs ${tipoAtividadeGigs} - Adicionar`;
  span.textContent = label;
  botaoGigs.appendChild(span);
    // vincularTooltipAcessivel(botaoGigs, label + '. A extensão criará automaticamente. Caso não exista GIGS desse tipo, peça ao gestor da sua unidade para criar.');
  botaoGigs.addEventListener("click", () => {

    const aa = {"nm_botao":"erec_semTese_inclusao_automatica","tipo":"preparo","tipo_atividade":tipoAtividadeGigs,"prazo":"","responsavel":"","responsavel_processo":"","observacao":"Incluído automaticamente a partir do e-Rec","salvar":"Sim","cor":"#008b8b","vinculo":"FecharJanelaGIGS","visibilidade":"sim"}
    const aaGigs = browser.storage.local.set({'monitorGIGS': ['acao_bt_aaAutogigs', aa]});
    Promise.all([aaGigs]).then(() => {
      apis.abrirGigs.abrir(preferencias.trt, {idProcesso});
    });

  });
  const toolbarPrincipal = await esperarElemento(
    'pje-erec-menu'
  );
  toolbarPrincipal.appendChild(botaoGigs);
}

/**
 *
 * @param {Documento[]} documentos
 * @param {string[]} pessoasSignatarias
 * @returns {Documento[]} documentos juntados pelas pessoas signatárias
 */
function filtrarDocumentosRepresentantes(documentos, pessoasSignatarias) {
  return documentos.filter((doc) =>
    pessoasSignatarias.includes(semAcento(doc.nomeSignatario))
  );
}

async function configurarTelaPrincipalERec() {
    /** @type {HTMLDivElement} */
    const menuPrincipal = await esperarElemento('.menu-principal');
    if (menuPrincipal) {
        menuPrincipal.style.alignItems = 'baseline';
        configurarMarcarMeusProcessosERec(menuPrincipal, 1, 3);
    }
}

async function configurarMarcarMeusProcessosERec(container, colunaCheck = 1, colunaNumero = 2) {
    const importarProcessosHtml = `
    <button class="mat-icon-button importar-processos" id="importarMeusProcessos"
        title="Marcar processos em lote - maisPJE" aria-label="Marcar processos em lote - maisPJE"
    >
        <i class="fas fa-user-check"></i>
    </button>
    `
    const domParser = new DOMParser();
    const documentoTratado = domParser.parseFromString(importarProcessosHtml, 'text/html');
    const importarProcessos = documentoTratado.querySelector('button#importarMeusProcessos');
    importarProcessos.addEventListener('click', async () => {
        const processos = await listaProcessoParaAcoesEmLote();
        if (processos) {
            selecionarProcessosNaTabela('table', processos, colunaCheck, colunaNumero);
        }
    });
    container.appendChild(importarProcessos);
}


async function configurarImportarProcessosErec() {
    /** @type {HTMLDivElement} */
    const botaoPesquisar = await esperarElemento('pje-erec-importacao-filtros button[aria-label="Pesquisar"]');
    configurarMarcarMeusProcessosERec(botaoPesquisar.parentElement);
}

async function selecionarProcessosNaTabela(tabelaSelector, processos, colunaCheck = 1, colunaNumero = 2) {
    // Seleciona a tabela e as linhas (ignorando o cabeçalho se houver <thead>)
    const tabela = document.querySelector(tabelaSelector);
    if (!tabela) {
        console.error("Tabela não encontrada!");
        return;
    }

    const linhas = tabela.querySelectorAll('tr');
    linhas.forEach(async linha => {
        const colunas = linha.querySelectorAll('td');

        // Verificamos se a linha tem colunas suficientes
        // Coluna 2 (índice 1) é o Checkbox
        // Coluna 3 (índice 2) é o Número do Processo
        if (colunas.length >= 3) {
            const numeroProcesso = colunas[colunaNumero].innerText.trim();
            // const checkbox = colunas[1].querySelector('input[type="checkbox"]');
            const checkbox = colunas[colunaCheck].querySelector('mat-checkbox');

            // Se o número estiver na lista e o checkbox existir, clicamos
            if (processos.includes(numeroProcesso) && checkbox) {
                if (!checkbox.className.includes('mat-checkbox-checked')) {
                    checkbox.firstElementChild.click()
                }
            }
        }
    });
}
