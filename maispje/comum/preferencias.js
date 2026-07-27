//ATIVAR LGPD
async function ativarLGPD(ligar) {
    let estiloInjetado = document.querySelector('#maisPJeEstiloLGPD')
    if (ligar) {
        console.log("maisPJe: ModoLGPD ativado");
        if (!estiloInjetado) {
            let link1 = document.createElement("link");
            link1.rel = "preconnect";
            link1.href = "https://fonts.googleapis.com";

            let link2 = document.createElement("link");
            link2.rel = "preconnect";
            link2.href = "https://fonts.gstatic.com";
            link2.setAttribute("crossorigin", "");

            let link3 = document.createElement("link");
            link3.rel = "stylesheet";
            link3.href = "https://fonts.googleapis.com/css2?family=Redacted+Script:wght@300;400;700&display=swap";

            document.body.appendChild(link1);
            document.body.appendChild(link2);
            document.body.appendChild(link3);

            let estiloLGPD = document.createElement("style");
            estiloLGPD.id = 'maisPJeEstiloLGPD'
            estiloLGPD.textContent = `
            /* *****PÁGINA PRINCIPAL***** */
            body {
                font-family: "Redacted Script", serif;
            }

            /* *****PÁGINA PRINCIPAL***** */

            /* Nome das partes nas listas da página principal */
            pje-data-table div[class*="sobrescrito"] {
                font-family: "Redacted Script", serif;
            }

            /* Descrição do GIGS nas listas da página principal */
            .texto-descricao {
                font-family: "Redacted Script", serif;
            }

            /* Responsável nas listas da página principal */
            input[aria-label*="Responsável"] {
                font-family: "Redacted Script", serif;
            }

            /* Descrição da petição no escaninho */
            a[aria-label*="Visualizar"] {
                font-family: "Redacted Script", serif;
            }

            /* Nome das partes na tabela de perícias */
            pje-celula-dados-basicos-processo div[class*="sobrescrito"] {
                font-family: "Redacted Script", serif;
            }

            /* Nome dos peritos na tabela de perícias */
            span[aria-label*="Perito"] {
                font-family: "Redacted Script", serif;
            }

            /* Nome dos destinatários no minutar despacho */
            span[class*="destinario"] {
                font-family: "Redacted Script", serif;
            }


            /* Nome dos responsável na tabela de designação automática de responsáveis */
            pje-designacao-automatica div[class*="mat-tooltip-trigger"] {
                font-family: "Redacted Script", serif;
            }

            /* Nome dos responsável na tabela do GIGS */
            pje-data-table[nametabela*="Tabela de Atividades"] td:nth-child(6) {
                font-family: "Redacted Script", serif;
            }

            /* Nome dos responsável na tabela do GIGS */
            pje-data-table[nametabela*="Tabela de Comentários"] td:nth-child(5) {
                font-family: "Redacted Script", serif;
            }


            /* *****GIGS***** */

            /* Descrição da atividade/Comentário GIGS  */
            pje-gigs-ficha-processo span[class*="descricao"] {
                font-family: "Redacted Script", serif;
            }

            /* Responsável na atividade GIGS  */
            pje-gigs-ficha-processo span[class*="texto-responsavel"] {
                font-family: "Redacted Script", serif;
            }

            /* Nome do executado Checklist GIGS  */
            pje-gigs-ficha-processo span[class*="font-label-executado"] {
                font-family: "Redacted Script", serif;
            }

            pje-gigs-dados-processo div[class*="wrapper"] div:nth-child(2) {
                font-family: "Redacted Script", serif;
            }


            /* *****MAT-OPTIONS***** */
            .mat-option-text {
                font-family: "Redacted Script", serif;
            }


            /* *****DETALHES DO PROCESSO***** */

            .partes {
                font-family: "Redacted Script", serif !important;
            }

            .oj-cargo {
                font-family: "Redacted Script", serif;
            }

            .campo-informacao {
                font-family: "Redacted Script", serif;
            }

            .tl-documento {
                font-family: "Redacted Script", serif;
            }

            div[class*="cabecalho-esquerda"] mat-card-title {
                font-family: "Redacted Script", serif;
            }

            div[class*="cabecalho-esquerda"] mat-card-subtitle {
                font-family: "Redacted Script", serif;
            }

            div[class*="cabecalho-central"] {
                font-family: "Redacted Script", serif;
            }

            .conteudo-pdf {
                filter: blur(5px);
            }

            pje-autuacao dd {
                font-family: "Redacted Script", serif;
            }

            pje-parte-processo .partes-corpo {
                font-family: "Redacted Script", serif;
            }

            pje-parte-processo .partes-representante {
                font-family: "Redacted Script", serif;
            }

            .post-it-conteudo {
                font-family: "Redacted Script", serif !important;
            }

            .rodape-post-it {
                font-family: "Redacted Script", serif !important;
            }

            .post-it-titulo {
                font-family: "Redacted Script", serif !important;
            }

            .nome-com-quebra {
                font-family: "Redacted Script", serif !important;
            }

            pje-dialogo-post-it [aria-label="Informações de Edição"] {
                font-family: "Redacted Script", serif !important;
            }

            /* *****TAREFA DO PROCESSO***** */

            pje-cabecalho-tarefa .nome-responsavel {
                font-family: "Redacted Script", serif;
            }

            /* *****SISBAJUD***** */

            .span-nome-juiz {
                font-family: "Redacted Script", serif;
            }

            .span-nome-assessor {
                font-family: "Redacted Script", serif;
            }

            .sisbajud-label-valor {
                font-family: "Redacted Script", serif;
            }

            .col-reu-dados {
                font-family: "Redacted Script", serif;
            }

            td[class*="cdk-column-juizSolicitante"] {
                font-family: "Redacted Script", serif;
            }

            #maisPje_caixa_de_selecao span[style*="cursor: pointer"] {
                font-family: "Redacted Script", serif;
            }

            input[placeholder*="Juiz Solicitante"] {
                font-family: "Redacted Script", serif;
            }

            mat-select[name*="varaJuizoSelect"] {
                font-family: "Redacted Script", serif;
            }

            input[placeholder*="CPF/CNPJ"] {
                font-family: "Redacted Script", serif;
            }

            input[placeholder*="Vara/Juízo:"] {
                font-family: "Redacted Script", serif;
            }

            input[placeholder*="Nome do autor"] {
                font-family: "Redacted Script", serif;
            }

            .cdk-column-identificacao {
                font-family: "Redacted Script", serif;
            }


            /* *****RETIFICAR AUTUAÇÃO***** */

            pje-nome-parte {
                font-family: "Redacted Script", serif;
            }

            #inputCPF {
                font-family: "Redacted Script", serif;
            }

            #inputCNPJ {
                font-family: "Redacted Script", serif;
            }

            #inputNome {
                font-family: "Redacted Script", serif;
            }

            #inputNomeFantasia {
                font-family: "Redacted Script", serif;
            }

            #inputNomeResponsavel {
                font-family: "Redacted Script", serif;
            }

            #inputCpfResponsavel {
                font-family: "Redacted Script", serif;
            }

            #inputNomePessoaPesquisada {
                font-family: "Redacted Script", serif;
            }

            #inputParteId {
                font-family: "Redacted Script", serif;
            }

            #inputCPFParteId {
                font-family: "Redacted Script", serif;
            }

            #inputGenitora {
                font-family: "Redacted Script", serif;
            }

            span[class*="label-parte"] span:nth-child(2) {
                font-family: "Redacted Script", serif;
            }

            .lista-selecao-partes {
                font-family: "Redacted Script", serif;
            }

            pje-endereco mat-card-title {
                font-family: "Redacted Script", serif;
            }



            /* *****PESQUISAR PROCESSO***** */

            mat-cell[class*="cdk-column-autor"] {
                font-family: "Redacted Script", serif;
            }

            mat-cell[class*="cdk-column-terceiro"] {
                font-family: "Redacted Script", serif;
            }

            /* *****COMUNICAÇÕES***** */
            pje-pec-partes-polo .nome-parte {
                font-family: "Redacted Script", serif;
            }

            pje-pec-partes-polo .partes-representante {
                font-family: "Redacted Script", serif;
            }

            pje-editor .cabecalho  {
                font-family: "Redacted Script", serif;
            }

            /* *****AUDIÊNCIAS***** */
            pje-listagem-dia .sobrescrito  {
                font-family: "Redacted Script", serif;
            }

            /* *****SIF***** */
            .mat-select-value-text {
                font-family: "Redacted Script", serif;
            }

            .mat-input-element {
                font-family: "Redacted Script", serif;
            }

            .mat-column-nomeEmissor {
                font-family: "Redacted Script", serif;
            }

            .formatacao-item-lista {
                font-family: "Redacted Script", serif;
            }

            /* *****ALVARÁS***** */
            pje-novo-alvara pje-dado-processo mat-card-content {
                font-family: "Redacted Script", serif;
            }

            /* *****CÁLCULOS***** */
            .texto-preto {
                font-family: "Redacted Script", serif;
            }

            /* *****OBRIGAÇÕES DE PAGAR***** */

            pje-obrigacao-pagar-cadastro td,.dd-cabecalho, .dt-rubrica {
                font-family: "Redacted Script", serif;
            }

            /* *****SEGUNDO GRAU PAUTA DE JULGAMENTO DE SESSÃO***** */
            .rich-table-cell {
                filter: blur(2px)
            }

            /* *****SNIPER***** */

            .truncate-text {
                font-family: "Redacted Script", serif;
            }

            .part-card__name, .part-card__document {
                font-family: "Redacted Script", serif;
            }

            .mat-column-nome_proprietario, .mat-column-documento {
                font-family: "Redacted Script", serif;
            }

            .section-container {
                font-family: "Redacted Script", serif;
            }

            .mdc-list-item {
                font-family: "Redacted Script", serif;
            }

            .grafo {
                filter: blur(4px)
            }

            /* *****CNIB***** */

            #txtDocumentNumber {
                font-family: "Redacted Script", serif;
            }

            .table-responsive td {
                font-family: "Redacted Script", serif;
            }

            .form-group-cnib span {
                font-family: "Redacted Script", serif !important;
            }

            .title-user-name-v5 {
                font-family: "Redacted Script", serif !important;
            }

            .msg-warning-cancellation {
                font-family: "Redacted Script", serif !important;
            }

            .form-control {
                font-family: "Redacted Script", serif !important;
            }

            .lblValorDescricao {
                font-family: "Redacted Script", serif !important;
            }

            .lblValorDescricao {
                font-family: "Redacted Script", serif !important;
            }

            .form-group span {
                font-family: "Redacted Script", serif !important;
            }

            .f-profile {
                font-family: "Redacted Script", serif !important;
            }

            .welcome-box h6 {
                font-family: "Redacted Script", serif !important;
            }

            `;

            document.body.appendChild(estiloLGPD);
        }
        if (document.querySelector('.maisPje-img')) { document.querySelector('.maisPje-img').style.filter = 'hue-rotate(170deg)' }
    } else {
        console.log("maisPJe: ModoLGPD desativado");
        if (estiloInjetado) {
            document.querySelector('#maisPJeEstiloLGPD').remove();
        }
        if (document.querySelector('.maisPje-img')) { document.querySelector('.maisPje-img').style.filter = 'hue-rotate(0deg)' }
    }
}

//ATIVAR MODO NOITE
/**
 *
 * @param {boolean} ligar
 */
async function ativarModoNoite(ligar) {
  let filtro = "";
  ligarMOModoNoite();

  if (ligar) {
    console.log("maisPJe: ModoNoite ativado");
    filtro = "invert(.93) hue-rotate(180deg) brightness(.8)";
    document.querySelector("html").style.filter = filtro;

    if (document.location.href.includes(".jus.br/pjekz/")) {
      //elementos excluídos do modo noturno
      inverterCor("pje-cabecalho", filtro);
      inverterCor("pje-resumo-processo", filtro);
      inverterCor("menumaispje", filtro);
      inverterCor("#brasao-republica", "revert");
      inverterCor('img[alt="Foto do perfil do usuário"]', "revert");
    }
  } else {
    console.log("maisPJe: ModoNoite desativado");
    filtro = "revert";
    document.querySelector("html").style.filter = filtro;

    if (document.location.href.includes(".jus.br/pjekz/")) {
      //elementos excluídos do modo noturno
      inverterCor("pje-cabecalho", "revert");
      inverterCor("pje-resumo-processo", "revert");
      inverterCor("menumaispje", "revert");
      inverterCor("#brasao-republica", "revert");
      inverterCor('img[alt="Foto do perfil do usuário"]', "revert");

      let icos = document.querySelectorAll('img[src*="icone-KZ"]');
      let limparIcos = [].map.call(icos, function (ico) {
        ico.style.filter = "revert";
      });
    }
  }

  async function inverterCor(seletor, filtro) {
    return new Promise(async (resolve) => {
      // console.log(seletor + ': ' + filtro)
      let elemento = await esperarElemento(seletor);
      if (elemento) {
        elemento.style.filter = filtro;
      }
      return resolve(true);
    });
  }

  function ligarMOModoNoite() {
    return new Promise(async (resolve) => {
      if (!document.body) {
        return null;
      }
      let observer = new MutationObserver(function (mutationsDocumento) {
        mutationsDocumento.forEach(function (mutation) {
          const primeiroItem = mutation.addedNodes[0];
          if (primeiroItem && primeiroItem instanceof HTMLElement) {
            // console.log("***[ADD] tagName(" + primeiroItem.tagName + ") id(" + primeiroItem.id + ") className(" + primeiroItem.className + ")");

            if (primeiroItem.tagName == "PJE-CABECALHO") {
              primeiroItem.style.filter = filtro;
              const brasao = primeiroItem.querySelector("#brasao-republica");
              if (brasao && brasao instanceof HTMLElement) {
                brasao.style.filter = "revert";
              }
            }

            if (primeiroItem.tagName == "PJE-RESUMO-PROCESSO") {
              primeiroItem.style.filter = filtro;
            }

            if (primeiroItem.tagName == "MENUMAISPJE") {
              primeiroItem.style.filter = filtro;
            }

            if (primeiroItem.tagName == "IMG") {
              if (primeiroItem.className.includes("foto-perfil")) {
                primeiroItem.style.filter = "revert";
              }
            }

            if (primeiroItem.tagName == "TR") {
              const icone = primeiroItem.querySelector('img[src*="icone-KZ"]');
              if (icone && icone instanceof HTMLElement) {
                icone.style.filter = filtro;
              }
            }
          }
        });
      });
      let configDocumento = { childList: true, subtree: true };
      observer.observe(document.body, configDocumento);
    });
  }
}
