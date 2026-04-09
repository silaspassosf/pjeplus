/**
 * Classe utilitária para manipulação e execução de chamadas de API com parâmetros dinâmicos.
 * movida para o mesmo arquivo de apis para simplificar os testes.
 */
class ApiWrapper {

  /**
   * Cria uma nova instância de ApiWrapper.
   * @param {string} path - Caminho da API, podendo conter parâmetros dinâmicos no formato `{param}`.
   * @param {Object} [defaultQueryParams={}] - Parâmetros de query padrão a serem incluídos em todas as requisições.
   * @param {string} [method='GET'] - Método HTTP a ser utilizado (GET, POST, etc).
   */
    constructor(path, defaultQueryParams = {}, method = 'GET') {
      /**
       * @type {string}
       * Caminho da API, podendo conter parâmetros dinâmicos.
       */
      this.path = path;
      /**
       * @type {Object}
       * Parâmetros de query padrão.
       */
      this.defaultQueryParams = defaultQueryParams;
      /**
       * @type {string}
       * Método HTTP.
       */
      this.method = method.toUpperCase();
    }

    #substituirParametrosDinamicos(params) {
        const regex = /{(\w+)}/g;
        let pathFinal = this.path;
        const parametrosRequeridos = [];
        let match;

        while ((match = regex.exec(this.path)) !== null) {
          parametrosRequeridos.push(match[1]);
        }

        // Verifica parâmetros faltantes
        const faltantes = parametrosRequeridos.filter(p => !(p in params));
        if (faltantes.length > 0) {
          throw new Error(`Parâmetros obrigatórios faltantes: ${faltantes.join(', ')}`);
        }

        // Substitui valores
        parametrosRequeridos.forEach(param => {
          pathFinal = pathFinal.replace(new RegExp(`{${param}}`, 'g'), encodeURIComponent(params[param]));
        });

        return pathFinal;
      }

      #normalizarDominio(dominio) {
        if (!dominio) {
          alert('mais PJe: Atenção usuário, a extensão identifica o seu TRT, instância e versão do sistema a partir da tela de login do PJe.\nAcesse a tela de login para normalizar suas congiurações básicas.');
          return 'ERRO';
        }
        if (!dominio.startsWith('http')) {
          return 'https://' + dominio;
        }
        return dominio;
      }
    /**
     * Monta a URL final substituindo parâmetros dinâmicos e adicionando query params.
     * @param {string} dominio - Domínio base da API.
     * @param {Object} [params={}] - Parâmetros para substituir no path e adicionar na query string.
     * @returns {string} URL final montada.
     * @throws {Error} Se algum parâmetro obrigatório do path estiver faltando.
     */
    montarUrl(dominio, params = {}, extraOptions = { replaceDev015: true }) {
      let urlBase = this.#normalizarDominio(dominio);
      if (extraOptions?.replaceDev015) {
        urlBase = urlBase.replace('dev015','pje');
      }
        const pathComParametros = this.#substituirParametrosDinamicos(params);
        const url = new URL(`${urlBase}${pathComParametros}`);

        // Filtra parâmetros que não são do path
        const queryParams = { ...this.defaultQueryParams };
        for (const key in params) {
          if (!this.path.includes(`{${key}}`)) {
            queryParams[key] = params[key];
          }
        }

        Object.entries(queryParams).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            value.forEach(v => url.searchParams.append(key, v));
          } else if (!!value) { // nao inclui parametro undefined ou null
            url.searchParams.append(key, value);
          }
        });

        return url.toString();
    }

  /**
   * Executa a chamada HTTP utilizando fetch.
   * @param {string} dominio - Domínio base da API.
   * @param {Object} [params={}] - Parâmetros do path e query string.
   * @param {Object} [fetchOptions={}] - Opções adicionais para o fetch (headers, body, etc).
   * @returns {Promise<any>} Resposta da API em JSON.
   * @throws {Error} Se a resposta HTTP não for OK.
   */
    async executar(dominio, params = {}, fetchOptions = {}, extraOptions = { replaceDev015: true, carregarRespostaJson: true}) {
      const url = this.montarUrl(dominio, params, extraOptions);

      // Mescla headers padrão com headers customizados, se houver
      const defaultHeaders = { 'Content-Type': 'application/json' };
      const headers = { ...defaultHeaders, ...(fetchOptions.headers || {}) };
      delete fetchOptions.headers;

      // Monta config base, incluindo mode, credentials, etc.
      const config = {
        method: this.method,
        headers,
        ...fetchOptions
      };
      const resposta = await fetch(url, config);
      // if (!resposta.ok || (resposta.status >= 400 )) throw new Error(`Erro HTTP ${resposta.status}`, { cause: resposta });
      if (!resposta.ok || (resposta.status >= 400 )) {
        console.error(`Erro HTTP ${resposta.status}`);
        return null;
        // throw new Error(`Erro HTTP ${resposta.status}`, { cause: resposta })
      }
      if( extraOptions.carregarRespostaJson ) {
        return await resposta.json();
      } else {
        return resposta;
      }
    }

    /**
     * Abre a URL gerada em uma nova aba/janela do navegador.
     * @param {string} dominio - Domínio base da API.
     * @param {Object} [params={}] - Parâmetros do path e query string.
     * @param {string} [target='_blank'] - Target da janela (ex: '_blank', '_self').
     * @returns {Window|null} Referência para a nova janela ou null.
     */
    abrir(dominio, params = {}, target = '_blank') {
      const url = this.montarUrl(dominio, params);
      return window.open(url, target);
    }

  }

const apis = {
    abrirGigs: new ApiWrapper(
      '/pjekz/gigs/abrir-gigs/{idProcesso}',
      {}
    ),

    tarefasProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/tarefas',
      { maisRecente: true }
    ),

    tarefaPorId: new ApiWrapper(
      '/pje-comum-api/api/tarefas/{idTarefa}',
      {}
    ),

    abrirTarefa: new ApiWrapper(
      '/pjekz/processo/{idProcesso}/tarefa/{idTarefa}',
      {}
    ),

    calculosProcesso: new ApiWrapper(
      '/pje-comum-api/api/calculos/processo',
      {
        idProcesso: '{idProcesso}',
        pagina: 1,
        tamanhoPagina: 10,
        ordenacaoCrescente: true,
        mostrarCalculosHomologados: true,
        incluirCalculosHomologados: true
      }
    ),

    extratoContaSIF: new ApiWrapper(
      '/sif-financeiro-api/api/contas/{processo}/104/{conta}/extrato/0/{dataAutuacao}/{dataFim}',
      {}
    ),

    detalhesContaSIF: new ApiWrapper(
      '/sif-financeiro-api/api/contas/{processo}/104/{conta}/detalhes',
      {}
    ),

    bndtProcesso: new ApiWrapper(
      '/pjekz/processo/{idProcesso}/bndt',
      { maisPje: 'excluir' }
    ),

    eRecDespachoPorId: new ApiWrapper(
      '/pje-erec-api/api/despachos/{idDespacho}',
      { titulos: true } //sem isso nao traz o nome da parte, que está no campo titulo, nos recursos
    ),

    eRecPartesPorRecursoId: new ApiWrapper(
      '/pje-erec-api/api/recursos/{idRecurso}/partes',
      {}
    ),

    processoPorId: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}',
      {}
    ),

    processoPorIdRapido: new ApiWrapper(
      '/pje-gigs-api/api/processo/{idProcesso}',
      {}
    ),

    processoSimplificadoPorId: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/simplificado',
      {}
    ),

    processoPorNumero: new ApiWrapper(
      '/pje-comum-api/api/processos/numero/{numeroProcesso}/completo',
      {}
    ),

    idProcessoPorNumero: new ApiWrapper(
      '/pje-comum-api/api/processos',
      {numero: undefined}
    ),

    idProcessoPorNumeroIncompleto: new ApiWrapper(
      '/pje-comum-api/api/agrupamentotarefas/processos',
      {numero: undefined}
    ),

    idProcessoPorNumeroValidandoSigilo: new ApiWrapper( // sem uso
      '/pje-comum-api/api/processos/numero/{numeroProcesso}/validacaosigilo',
      {}
    ),

    /**
     * valida se tem acesso ao processo ou a um de seus associados (o que permite acessar)
     */
    validaAcessoProcessoEAssociados: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/associados/permissaoassociado',
      {}
    ),

    pessoasJuridicas: new ApiWrapper(
      '/pje-comum-api/api/pessoas/juridicas',
      {
        esfera: undefined,
        tipoEntidade: undefined,
        idJurisdicao: undefined,
        apenasMPT: undefined
      }
    ),

    pessoasJuridicasCnpj: new ApiWrapper(
      '/pje-comum-api/api/pessoas/juridicas',
      {
        pagina: 1,
        tamanhoPagina: 10,
        situacao: 1
      }
    ),

    abrirDetalhesProcesso: new ApiWrapper(
      '/pjekz/processo/{idProcesso}/detalhe',
      {}
    ),

    pautaAudiencias: new ApiWrapper(
      '/pjekz/pauta-audiencias',
      {
        maisPje: true,
        numero: undefined,
        rito: undefined,
        fase: undefined
      }
    ),

    validacaoChave: new ApiWrapper(
      '/pjekz/validacao/{chave}',
      { instancia: '{grau_usuario}' }
    ),

    calendarioEventos: new ApiWrapper(
      '/pje-administracao-api/api/calendarioseventos/',
      {
        pagina: 1,
        ativo: true,
        tamanhoPagina: 1000,
        ano: undefined,
        mes: undefined
      }
    ),

    documentosProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/documentos',
      {
        idUnicoDocumento: undefined //pode pegar somente um documento pelo id de sete posições
      }
    ),

    documentoProcessoPorId: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}',
      {
        incluirAssinatura: false,
        incluirAnexos: false,
        incluirMovimentos: false,
        incluirApreciacao: false
      }
    ),
    abrirDocumentoEmNovaAba: new ApiWrapper(
      '/pjekz/processo/{idProcesso}/documento/{idDocumento}/conteudo',
      {}
    ),
    conteudoDocumento: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}/conteudo',
      {}
    ),

    documentoProcessoPorIdHtml: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}/html',
      {}
    ),

    documentoProcessoPreview: new ApiWrapper(
      '/pje-comum-api/api/processos/nrprocesso/{nrProcesso}/documentos/idUnico/{idUnicoDocumento}/preview',
      {
        incluirCapa: false,
        incluirAssinatura: true,
        incluirSumario: false,
        formato: '.jpeg'
      }
    ),

    associados: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/associados',
      {
        pagina: 1, //tem que por entre aspas pois se deixar sem elas o parametro não aparece na url
        tamanhoPagina: 100, //tem que por entre aspas pois se deixar sem elas o parametro não aparece na url
        ordenacaoCrescente: true
      }
    ),

    timelineProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/timeline',
      {
        somenteDocumentosAssinados: 'false', //tem que por entre aspas pois se deixar sem elas o parametro não aparece na url
        buscarMovimentos: 'false', //tem que por entre aspas pois se deixar sem elas o parametro não aparece na url
        buscarDocumentos: true
      }
    ),

    periciasProcesso: new ApiWrapper(
      '/pje-comum-api/api/pericias',
      {
        idProcesso: '{idProcesso}',
        situacao: ['D', 'L', 'P', 'S'],
        ordenar: 'prazoEntrega',
        ascendente: true
      }
    ),

    peritosPesquisa: new ApiWrapper(
      '/pje-comum-api/api/peritos',
      {
        parametroPesquisa: '{nome}',
        somenteAtivos: true
      }
    ),

    peritosEspecialidade: new ApiWrapper(
      '/pje-comum-api/api/peritos',
      {
        parametroPesquisa: '{nome}',
        idEspecialidade: '{especialidade}',
        somenteAtivos: true
      }
    ),

    consultaProcessosAdm: new ApiWrapper(
      '/pje-administracao-api/api/consultaprocessosadm',
      {
        pagina: 1,
        nomeParte: '{nomeParte}',
        tamanhoPagina: 1000
      }
    ),

    consultaProcessosTerceiros: new ApiWrapper(
      '/consultaprocessual/detalhe-processo/{numero}',
      {}
    ),

    consultaProcessosBasicos: new ApiWrapper(
      '/pje-consulta-api/api/processos/dadosbasicos/{numero}',
      {}
    ),

    pessoasFisicas: new ApiWrapper(
      '/pje-comum-api/api/pessoas/fisicas',
      {
        pagina: 1,
        tamanhoPagina: 10,
        situacao: 1
      }
    ),

    pessoasFisicasDetalhes: new ApiWrapper(
      '/pje-comum-api/api/pessoas/fisicas/{id}',
      {}
    ),

    tarefasCodigo: new ApiWrapper(
      '/pje-comum-api/api/tarefas/{idTarefa}',
      {}
    ),

    sobrestamentosProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/sobrestamentos',
      {}
    ),

    atividadeProcesso: new ApiWrapper(
      '/pje-gigs-api/api/atividade/processo/{idProcesso}',
      {}
    ),

    partesProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/partes',
      {}
    ),

    obrigacoesPagar: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/obrigacoespagar',
      {}
    ),

    prazoRelator: new ApiWrapper(
      '/pje-gigs-api/api/processo/{idProcesso}/prazoRelator'
    ),

    execucaoProcessoGigs: new ApiWrapper(
      '/pje-gigs-api/api/execucao/processo/{idProcesso}'
    ),

    movimentosProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/movimentos/',
      { ordemAscendente: false,
        codEventos: [] // vc pode passar uma lista que o montarUrl ajusta corretamente.
      }
    ),

    audienciasProcesso: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/audiencias',
      {
        status: 'M'
      }
    ),

    debitosTrabalhistas: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/debitostrabalhistas',
      {}
    ),

    documentosMinuta: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/documentos/minuta/A/metadados',
      {}
    ),

		comunicacoesMinutas: new ApiWrapper(
      '/pje-comum-api/api/comunicacoesprocessuais/minutas/',
      {
        idProcesso: undefined,
        temporario: true,
        origemExpedientes: ['PEC_FLUXO', 'PEC_MENU'],
        papeisSeguranca: 'MAGISTRADO'
      }
    ),

    permissaoPerfis: new ApiWrapper(
      '/pje-seguranca/api/token/perfis',
      {}
    ),

    permissaoPerfisOjUsuario: new ApiWrapper(
      '/pje-comum-api/api/orgaosjulgadores/{codigoOJ}',
      {}
    ),

    orgaosJulgadores: new ApiWrapper(
      '/pje-comum-api/api/orgaosjulgadores/',
      {}
    ),

    bloqueioTarefas: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/bloqueiotarefas',
      {},
      'POST'
    ),

    enderecosPessoa: new ApiWrapper(
      '/pje-comum-api/api/pessoas/{idPessoa}/enderecos',
      {
        tamanhoPagina: 10000
      }
    ),

    associarProcessos: new ApiWrapper(
      '/pjekz/retificacao',
      {
        maisPJe: undefined
      }
    ),

    domicilioEletronico: new ApiWrapper(
      '/pje-comum-api/api/pessoajuridicadomicilioeletronico/{idParte}',
      {}
    ),

    regrasImpedimento: new ApiWrapper(
      '/pje-comum-api/api/regrasimpedimentomagistrado/regrasimpedimento',
      {}
    ),

    listasContas: new ApiWrapper(
      '/sif-financeiro-api/api/listas/contas/{numero}',
      {}
    ),

    alvarasLista: new ApiWrapper(
      '/sif-financeiro-api/api/alvaras/lista/{numeroProcesso}/104/{contajudicial}',
      {
        pagina: 1,
        tamanhoPagina: 5,
        ordenacaoCrescente: false,
        ordenacaoColuna: 'dtHrSituacao'
      }
    ),

    prestacaoContas: new ApiWrapper(
      '/sif-financeiro-api/api/prestacaocontas/agrupador/alvaras',
      {
        situacoesAlvara: 'AGUARDANDO_CONFERENCIA',
        pagina: 1,
        tamanhoPagina: 50
      }
    ),

    nomeParteRepresentada: new ApiWrapper(
      '/pje-comum-api/api/processos/id/{idProcesso}/partes/representadas',
      {
        idRepresentante: '{idRepresentante}',
      }
    ),

    objetoECarta: new ApiWrapper(
      '/eCarta-web/impressaoDetalhesObjeto.xhtml',
      {
        codigo: '{codigo}',
      }
    ),

    retornaPrazoDiasUteis: new ApiWrapper(
        '/pje-gigs-api/api/atividade/retorna-prazo/{dias}',
        {
            idOj: '{codigoOJ}',
        }
    )
  };

/** @typedef {typeof apis} ApiMap */
