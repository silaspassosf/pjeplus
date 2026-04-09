/**
 * @typedef {"primeirograu"|"segundograu"|"tst"|'não identificado'} GrauUsuario
 */
/**
 * Preferências/configurações da extensão.
 * (Muitas propriedades são opcionais antes de `checarVariaveis()` normalizar.)
 *
 * @typedef {Object} Preferencias
 *
 * @property {boolean} extensaoAtiva
 * @property {boolean} concordo
 * @property {boolean} [modoLGPD]
 * @property {boolean} [modoNoite]
 *
 * @property {string} [versao]
 * @property {string} [trt]
 * @property {number} [num_trt]
 *
 * @property {string} [nm_usuario]
 * @property {string} [papel_usuario]
 * @property {string} [oj_usuario]
 * @property {GrauUsuario} [grau_usuario]
 * @property {string} [oj_usuarioId]
 *
 * @property {boolean} [desativarAjusteJanelas]
 * @property {boolean} [videoAtualizacao]
 *
 * @property {string} [atalhosPlugin]
 *
 * @property {number} [gigsMonitorDetalhes]
 * @property {number} [gigsMonitorTarefas]
 * @property {number} [gigsMonitorGigs]
 * @property {number} [gigsAbrirGigs]
 * @property {number} [gigsAbrirDetalhes]
 * @property {number} [gigsAbrirTarefas]
 * @property {number} [gigsApreciarPeticoes]
 * @property {number} [gigsApreciarPeticoes2]
 * @property {number} [gigsApreciarPeticoes3]
 * @property {number} [gigsOcultarChips]
 * @property {number} [gigsOcultarLembretes]
 * @property {number} [gigsCriarMenu]
 * @property {number} [gigsCriarMenuGuardarNumeroProcesso]
 * @property {boolean} [gigsCriarMenuAbrirPainelCopiaECola]
 * @property {boolean} [gigsTirarSomLembretes]
 * @property {boolean} [sanearAJG]
 * @property {boolean} [mapeamentoDeIDs]
 *
 * @property {number} [gigsPesquisaDeDocumentos]
 * @property {number} [tempAuto]
 *
 * @property {Array} [filtros_Favoritos]
 * @property {Array} [pjExtension_depositos]
 *
 * @property {string} [tarefaResponsavel]
 * @property {string} [prazoResponsavel]
 * @property {string} [atividadeResponsavel]
 * @property {string} [guiaPersonalizadaDetalhes]
 * @property {boolean} [pesquisaRapidaDeProcessoEmAba]
 *
 * @property {string} [ocultarPublicacoesDJEN]
 * @property {string} [ocultarDocumentosExcluidos]
 * @property {string} [exibirFaseProcessualNaTimeline]
 *
 * @property {number} [gigsTipoAtencao]
 *
 * @property {number} [maisPje_velocidade_interacao] Velocidade em ms (no código você multiplica por 1000).
 *
 * @property {any[]} [aaAnexar]
 * @property {any[]} [aaComunicacao]
 * @property {any[]} [aaAutogigs]
 * @property {any[]} [aaDespacho]
 * @property {any[]} [aaMovimento]
 * @property {any[]} [aaChecklist]
 * @property {any[]} [aaNomearPerito]
 * @property {any[]} [aaLancarMovimentos]
 * @property {any[]} [aaVariados]
 *
 * @property {any[]} [meuFiltro]
 *
 * @property {boolean} [modulo5_juizDaMinuta]
 * @property {boolean} [modulo5_processosSemAudienciaDesignada]
 * @property {boolean} [modulo5_obterSaldoSIF]
 * @property {boolean} [modulo5_conferirTeimosinhaEmLote]
 * @property {boolean} [modulo5_processosSemGigsCadastrado]
 * @property {boolean} [modulo5_processosParadosHaMaisDeXXDias]
 * @property {boolean} [modulo5_conferirGarimpoEmLote]
 * @property {boolean} [modulo5_obterConcilia]
 *
 * @property {EmailAutomatizado} [emailAutomatizado]
 *
 * @property {number} [gigsDetalhesLeft]
 * @property {number} [gigsDetalhesTop]
 * @property {number} [gigsDetalhesWidth]
 * @property {number} [gigsDetalhesHeight]
 * @property {number} [gigsTarefaLeft]
 * @property {number} [gigsTarefaTop]
 * @property {number} [gigsTarefaWidth]
 * @property {number} [gigsTarefaHeight]
 * @property {number} [gigsGigsLeft]
 * @property {number} [gigsGigsTop]
 * @property {number} [gigsGigsWidth]
 * @property {number} [gigsGigsHeight]
 *
 * @property {boolean[]} [atalhosDetalhes]
 *
 * @property {string} [processo_memoria]
 *
 * @property {string} [tempAR]
 * @property {any[]} [tempBt]
 * @property {any[]} [tempAAEspecial]
 * @property {string} [tempF2]
 * @property {string} [tempF3]
 * @property {string} [tempF4]
 *
 * @property {any[]} [monitorGIGS]
 *
 * @property {PreferenciasSisbajud} [sisbajud]
 * @property {PreferenciasSerasajud} [serasajud]
 * @property {PreferenciasPrevjud} [prevjud]
 * @property {PreferenciasRenajud} [renajud]
 *
 * @property {number} [zoom_editor]
 *
 * @property {any[]} [modulo8]
 * @property {boolean} [modulo8_ignorarZero]
 *
 * @property {PreferenciasModulo9} [modulo9]
 * @property {PreferenciasSAJ} [saj]
 *
 * @property {any[]} [lista_monitores]
 * @property {any[]} [linksMenuLateral]
 *
 * @property {any[]} [modulo10]
 * @property {(boolean|string)[]} [modulo10_juntadaMidia] Ex.: [false, ''].
 * @property {boolean} [modulo10_painelCopiaeCola]
 * @property {string} [modulo10_salaFavorita]
 *
 * @property {any[]} [modulo11]
 * @property {boolean} [modulo11_AssinarAutomaticamente]
 *
 * @property {any[]} [modulo2]
 * @property {string} versaoPje
 * @property {MenuKaizen} [menu_kaizen]
 * @property {string} [AALote]
 * @property {string} [erros]
 * @property {boolean} [acionarKaizenComClique]
 * @property {boolean} [kaizenNaHorizontal]
 *
 * @property {string} [modulo4PaginaInicial]
 * @property {number} [anexadoDoctoEmSigilo]
 *
 * @property {PreferenciasTimeline} [timeline] Ex.: ['', []].
 * @property {string} extrasTiposDocumentoProcuracao
 * @property {string} extrasTiposDocumentoCustas
 * @property {string} extrasTiposDocumentoDepositoRecursal
 * @property {string} extrasTiposDocumentoSentencasAcordao
 * @property {boolean} extrasExibirPreviaDocumentoMouseOver
 * @property {boolean} extrasExibirPreviaDocumentoFocus
 * @property {boolean} extrasFocusSempre
 * @property {string} [extrasERecTipoGigsSemTema]
 * @property {boolean} [extrasFecharJanelaExpediente]
 * @property {boolean} [extrasSugerirTipoAoAnexar]
 * @property {boolean} [extrasSugerirDescricaoAoAnexar]
 * @property {string} [extrasProcurarExecucao]
 * @property {string[]} [extrasPrazoEmLote]
 *
 * @property {{ painelcopiaecola?: string }} [atalho]
 *
 * @property {ConfigURLs} [configURLs]
 * @property {ConciliaJTConfig} conciliajt
 */

/** @typedef {Object} PreferenciasSisbajud
 * @property {string} [juiz]
 * @property {string} [vara]
 * @property {string} [cnpjRaiz]
 * @property {string} [teimosinha]
 * @property {string} [contasalario]
 * @property {string} [naorespostas]
 * @property {string} [valor_desbloqueio]
 * @property {string} [banco_preferido]
 * @property {string} [agencia_preferida]
 * @property {string} [preencherValor]
 * @property {string} [confirmar]
 * @property {string} [executarAAaoFinal]
 * @property {string} [salvarEprotocolar]
 */

/** @typedef {Object} PreferenciasSerasajud
 * @property {string} [foro]
 * @property {string} [vara]
 * @property {string} [prazo_atendimento]
 * @property {string} [aa]
 */

/** @typedef {Object} PreferenciasPrevjud
 * @property {string} [aa]
 * @property {string} [aa2]
 * @property {boolean} [opt1]
 */

/** @typedef {Object} PreferenciasRenajud
 * @property {string} [tipo_restricao]
 * @property {string} [comarca]
 * @property {string} [tribunal]
 * @property {string} [orgao]
 * @property {string} [juiz]
 * @property {string} [juiz2]
 */

/**
 * @typedef {Object} PreferenciasModulo9
 * @property {boolean} [sisbajud]
 * @property {boolean} [renajud]
 * @property {Object} [cnib]
 * @property {(boolean|number|string)[]} [ccs]
 * @property {boolean} [crcjud]
 * @property {boolean} [onr]
 * @property {(boolean|number|string)[]} [gprec]
 * @property {(boolean|number|string)[]} [siscondj]
 * @property {(boolean|string)[]} [garimpo]
 * @property {(boolean|number|string)[]} [sif]
 * @property {boolean} [pjecalc]
 * @property {boolean} [prevjud]
 * @property {boolean} [protestojud]
 * @property {boolean} [sniper]
 * @property {boolean} [censec]
 * @property {boolean} [celesc]
 * @property {boolean} [casan]
 * @property {boolean} [sigef]
 * @property {boolean} [infoseg]
 * @property {boolean|any[]} [ecarta]
 * @property {boolean} [saj]
 */

/** @typedef {Object} PreferenciasSAJ
 * @property {string} [vara]
 * @property {string} [juiz]
 * @property {string} [prazoResposta]
 * @property {string} [extratomercantil]
 * @property {string} [extratomovimentacao]
 * @property {string} [extratomovfinanceira]
 * @property {string} [faturacartaocredito]
 * @property {string} [propostaaberturaconta]
 * @property {string} [contratocambio]
 * @property {string} [registrocambio]
 * @property {string} [copiacheque]
 * @property {string} [saldofgts]
 * @property {string} [recebernotificacao]
 * @property {string} [email]
 * @property {string} [telefone]
 */

/**
 * Representa as coordenadas de posicionamento de um elemento no menu.
 * @typedef {Object} MenuPosition
 * @property {string} posx - Posição horizontal (geralmente em porcentagem, ex: '96%').
 * @property {string} posy - Posição vertical (geralmente em porcentagem, ex: '92%').
 */

/** @typedef {Object} MenuKaizen
 * @property {MenuPosition} [principal]
 * @property {MenuPosition} [detalhes]
 * @property {MenuPosition} [tarefas]
 * @property {MenuPosition} [sisbajud]
 * @property {MenuPosition} [serasajud]
 * @property {MenuPosition} [renajud]
 * @property {MenuPosition} [cnib]
 * @property {MenuPosition} [ccs]
 * @property {MenuPosition} [prevjud]
 * @property {MenuPosition} [protestojud]
 * @property {MenuPosition} [sniper]
 * @property {MenuPosition} [censec]
 * @property {MenuPosition} [celesc]
 * @property {MenuPosition} [casan]
 * @property {MenuPosition} [sigef]
 * @property {MenuPosition} [infoseg]
 * @property {MenuPosition} [ajjt]
 * @property {MenuPosition} [saj]
 */

/** @typedef {[string, any[]]} PreferenciasTimeline */

// concilia
/**
 * @typedef {Object} PotencialRest
 * @property {string} vl_predicao - Valor da predição.
 * @property {string} dt_predicao - Data da predição.
 * @property {string} ds_predicao - Descrição da predição.
 */
/**
 * @typedef {Object} ConciliaJTConfig
 * @property {string} ads_url - A URL do serviço de anúncios.
 * @property {boolean} ads_enabled - O status de habilitação do serviço de anúncios.
 * @property {boolean} enabled - O status de habilitação do sistema ConciliaJT.
 * @property {string} url - A URL principal do sistema ConciliaJT.
 */

/**
 * Configurações de URLs dos sistemas judiciais.
 * @typedef {Object} ConfigURLs
 *
 * @property {string} descricao
 * Descrição do tribunal ou sistema.
 * Exemplo: "Tribunal Regional do Trabalho da 1a Região"
 *
 * @property {string} urlSiscondj
 * URL de acesso ao sistema SISCONDJ para criação de movimentação de conta.
 *
 * @property {string} idSiscondj
 * Identificador interno do sistema SISCONDJ.
 * Exemplo: "siscondj"
 *
 * @property {string} urlSAOExecucao
 * URL do sistema SAO Execução (pode estar vazia caso não aplicável).
 *
 * @property {ConciliaJTConfig} conciliajt
 * Objeto contendo configurações relacionadas ao sistema ConciliaJT.
 */

// token autenticacao
/**
 * Representa um usuário autenticado no sistema PJE.
 * @typedef {Object} UsuarioPJE
 * @property {string} jti ID único do token JWT.
 * @property {string} iss Issuer do token (URL do sistema de segurança).
 * @property {number} iat Timestamp Unix da emissão do token.
 * @property {string} sub Subject do token (chave da aplicação).
 * @property {number} exp Timestamp Unix da expiração do token.
 * @property {string} uuid Identificador único do usuário.
 * @property {string} urlBase URL base do sistema de segurança.
 * @property {string} tokenChave Identificador da chave ou sessão.
 * @property {string} chaveAplicacao Chave da aplicação.
 * @property {string} tokenSessao ID da sessão autenticada.
 * @property {string} sid Session ID do token JWT.
 * @property {string} siglaSistema Sigla do sistema (ex: "PJE").
 * @property {number} instancia Número da instância (ex: 1, 2).
 * @property {string} tipo Tipo de entidade autenticada (ex: "USUARIO").
 * @property {number} id Identificador numérico do usuário.
 * @property {string} login Login do usuário (CPF).
 * @property {string} nome Nome completo do usuário.
 * @property {number} perfil Código do perfil do usuário.
 * @property {Papel} papel Papel principal do usuário.
 * @property {Papel} papelKz Papel complementar.
 * @property {Localizacao} localizacao Localização ou unidade associada.
 * @property {('LOGIN_SENHA'|'CERTIFICADO')} metodoAutenticacao Método de autenticação.
 * @property {OrgaoJulgador|null} orgaoJulgador Órgão julgador associado.
 * @property {OrgaoJulgador|null} orgaoJulgadorColegiado Órgão julgador colegiado.
 * @property {string} origem Sistema ou TRT de origem (ex: "TRT12").
 * @property {boolean} usuarioUnificado Indica usuário unificado.
 * @property {boolean} otpPersistido Indica se OTP foi persistido.
 */

/**
 * Representa o papel (função) de um usuário.
 * @typedef {Object} Papel
 * @property {number|null} id Identificador do papel.
 * @property {string|null} nome Nome do papel.
 * @property {string|null} identificador Identificador textual do papel.
 */

/**
 * Representa a localização associada a um usuário.
 * @typedef {Object} Localizacao
 * @property {number} id Identificador da unidade.
 * @property {string} descricao Descrição da localização.
 */

/**
 * Representa o órgão julgador associado.
 * @typedef {Object} OrgaoJulgador
 * @property {number} id Identificador do órgão.
 * @property {string} descricao Nome do órgão julgador.
 */

// processo
/**
 * Representa um processo judicial simplificado (resumo para performance).
 * @typedef {Object} ProcessoSimplificado
 * @property {number} id Identificador único do processo.
 * @property {string} numero Número completo CNJ (ex: "0001637-71.2024.5.12.0038").
 * @property {number|null} idOrgaoJulgador ID do órgão julgador principal (para `isMesmoOJOJCProcesso`).
 * @property {number|null} idOrgaoJulgadorColegiado ID do órgão colegiado (para `isMesmoOJOJCProcesso`).
 * @property {number} ano Ano do processo (ex: 2024).
 * @property {number} numeroSequencia Número sequencial do processo.
 * @property {number} numeroDigitoVerificador Dígito verificador CNJ.
 * @property {number} numeroOrigem Número de origem (vara).
 * @property {number} codigoFaseProcessual Código numérico da fase.
 * @property {string} codigoApreciadoSigilo Código apreciação sigilo (ex: "D").
 * @property {boolean} apreciadoTutelaLiminar Flag tutela liminar apreciada.
 * @property {boolean} mandadoDevolvido Flag mandado devolvido.
 * @property {string} faseProcessual Fase em texto (ex: "CONHECIMENTO").
 * @property {string} apreciadoSigilo Status apreciação sigilo (ex: "INDEFERIDO").
 * @property {string} status Status atual (ex: "DISTRIBUIDO").
 * @property {string} autuadoEm Data/hora autuação (ISO).
 * @property {boolean} segredoJustica Flag segredo de justiça.
 *
 */

/**
 * Representa um processo judicial no sistema PJE.
 * @typedef {Object} ProcessoPJE
 * @property {number} id Identificador único do processo.
 * @property {string} numero Número completo do processo (ex: "0000940-11.2024.5.12.0051").
 * @property {ClasseJudicial} classeJudicial Detalhes da classe judicial.
 * @property {string} autuadoEm Data/hora de autuação (ISO).
 * @property {number} numeroIdentificacaoJustica Código CNJ da Justiça.
 * @property {string} distribuidoEm Data/hora de distribuição (ISO).
 * @property {number} valorDaCausa Valor da causa em centavos.
 * @property {string} codigoClasseJudicialInicial Código inicial da classe.
 * @property {string} labelClasseJudicialInicial Label da classe inicial.
 * @property {string} codigoStatusProcesso Código do status atual.
 * @property {string} labelStatusProcesso Label do status (ex: "Distribuído").
 * @property {boolean} segredoDeJustica Flag de segredo de justiça.
 * @property {boolean} justicaGratuita Flag de justiça gratuita.
 * @property {boolean} tutelaOuLiminar Flag de tutela/liminar.
 * @property {boolean} juizoDigital Flag de juízo digital.
 * @property {number} instancia Número da instância (ex: 2).
 * @property {string} codigoApreciadoSegredo Código apreciação segredo.
 * @property {string} labelApreciadoSegredo Label apreciação segredo.
 * @property {OrgaoJulgadorCompleto} orgaoJulgador Órgão julgador principal.
 * @property {OrgaoJulgadorCompleto} orgaoJulgadorColegiado Órgão colegiado.
 * @property {OrgaoJulgadorCargo} orgaoJulgadorCargo Cargo do órgão julgador.
 * @property {Jurisdicao} jurisdicao Detalhes da jurisdição.
 * @property {boolean} apreciadoTutelaLiminar Flag tutela liminar apreciada.
 * @property {string} codigoApreciadoSigilo Código apreciação sigilo.
 * @property {string} labelApreciadoSigilo Label apreciação sigilo.
 * @property {boolean} mandadoDevolvido Flag mandado devolvido.
 * @property {number} codigoFaseProcessual Código da fase processual.
 * @property {string} labelFaseProcessual Label da fase (ex: "Conhecimento").
 * @property {string} dataInicio Data início da fase (ISO).
 * @property {UsuarioPJE} usuarioCadastroProcesso Usuário que cadastrou.
 * @property {boolean} selecionadoPauta Flag pauta selecionada.
 * @property {boolean} revisado Flag revisado.
 * @property {boolean} outraInstancia Flag outra instância.
 * @property {boolean} selecionadoJulgamento Flag julgamento selecionado.
 * @property {boolean} apreciadoJusticaGratuita Flag justiça gratuita apreciada.
 * @property {boolean} incidente Flag incidente processual.
 * @property {boolean} deveMarcarAudiencia Flag marcar audiência.
 * @property {boolean} inRevisao Flag em revisão.
 * @property {string} faseProcessual Fase processual em texto.
 * @property {Relator} relator Dados do relator.
 * @property {ProcessoJT} processoJT Dados específicos JT.
 * @property {string} codigoFluxo Código do fluxo processual.
 * @property {boolean} temAssociacao Flag processo associado.
 */

/**
 * Classe judicial do processo.
 * @typedef {Object} ClasseJudicial
 * @property {number} id ID da classe.
 * @property {string} codigo Código CNJ (ex: "1009").
 * @property {string} descricao Descrição completa.
 * @property {string} sigla Sigla (ex: "ROT").
 */

/**
 * Órgão julgador completo com todos detalhes.
 * @typedef {Object} OrgaoJulgadorCompleto
 * @property {number} id ID do órgão.
 * @property {string} descricao Descrição do órgão.
 * @property {string} sigla Sigla do órgão.
 * @property {boolean} ativo Status ativo.
 * @property {boolean} novoOrgaoJulgador Flag novo formato.
 * @property {number} idJurisdicao ID jurisdição.
 * @property {string} instancia Instância.
 * @property {string} email Email do órgão.
 */

/**
 * Cargo no órgão julgador.
 * @typedef {Object} OrgaoJulgadorCargo
 * @property {number} id ID do cargo.
 * @property {string} descricao Descrição completa.
 * @property {string} siglaCargo Sigla cargo.
 */

/**
 * Jurisdição do processo.
 * @typedef {Object} Jurisdicao
 * @property {number} id ID jurisdição.
 * @property {string} descricao Nome da jurisdição (ex: "TRT 12ª Região").
 * @property {string} estado Estado UF.
 */

/**
 * Relator do processo.
 * @typedef {Object} Relator
 * @property {number} id ID do relator.
 * @property {string} nome Nome completo.
 * @property {string} genero Gênero.
 * @property {string} email Email.
 */

/**
 * Dados específicos do processo.
 * @typedef {Object} ProcessoJT
 * @property {number} idProcesso ID processo.
 * @property {Object} atividade Atividade econômica.
 * @property {Object} municipio Dados município.
 */

/**
 * Dados capturados na tela do e-Rec.
 * @typedef {Object} DadosERec
 * @property {string} numeroProcesso numero do processo.
 * @property {string} nomeRecorrente numero do processo.
 */

/**
 * Recurso de um despacho no E-Rec.
 *
 * @typedef {Object} RecursoERec
 * @property {number} id
 * @property {number} ordem
 * @property {string} idPublicacaoAcordao
 * @property {string} dataCiencia ISO-8601 datetime string (ex.: "2025-07-14T23:59:59.999999").
 * @property {string} dataLimite ISO-8601 datetime string (ex.: "2025-07-24T23:59:59.999999").
 * @property {boolean} tempestivo
 * @property {string} dataProtocolo ISO-8601 date/datetime string (ex.: "2025-07-24T00:00:00").
 * @property {string} idProtocolo
 * @property {string} [titulo] atualmente, é o nome da parte que recorreu (só vem se a api for chamada com query param titulos=true)
 */

/**
 * Tipo da parte (papel no recurso).
 *
 * @typedef {Object} TipoParteERec
 * @property {string} codigo Ex.: "E" (Recorrente), "I" (Recorrido).
 * @property {string} nome
 */

/**
 * Advogado vinculado à parte.
 *
 * @typedef {Object} AdvogadoERec
 * @property {number} id
 * @property {number} idPessoa
 * @property {string} nome
 * @property {string} oab
 * @property {number} idUsuarioCriacao
 * @property {string} dataCriacao ISO-8601 datetime string.
 */

/**
 * Parte no E-Rec (com recurso, tipo de parte e advogados).
 *
 * @typedef {Object} ParteERec
 * @property {number} id
 * @property {RecursoERec} recurso
 * @property {number} ordem
 * @property {TipoParteERec} tipoParte
 * @property {number} idPessoa
 * @property {string} nomePessoa
 * @property {string} loginPessoa
 * @property {number} idUsuarioCriacao
 * @property {string} dataCriacao ISO-8601 datetime string.
 * @property {AdvogadoERec[]} [advogados]
 */

/**
 * @typedef {Object} idNumeroProcesso
 * @property {number} idProcesso
 * @property {string} numeroProcesso
 **/

/**
 * Despacho E-Rec.
 *
 * @typedef {Object} DespachoERec
 * @property {number} id
 * @property {boolean} exibirPesquisa
 * @property {number} idTipoDespacho
 * @property {number} idProcesso
 * @property {string} numeroProcesso
 * @property {number} idOrgaoJulgadorAcordao
 * @property {number} idUsuarioRedator
 * @property {number} idUsuarioAtual
 * @property {string} dataCriacao ISO-8601 datetime string (ex.: "2026-02-24T16:27:04.462106").
 * @property {number} codigoStatus
 * @property {string} dataStatus ISO-8601 datetime string (ex.: "2026-02-24T16:29:01.082907").
 * @property {number} idClasseJudicial
 * @property {boolean} check
 * @property {boolean} recursoAdesivo
 * @property {RecursoERec[]} recursos
 */

/**
 * Informações relacionadas a expedientes do documento.
 *
 * @typedef {Object} DocumentoInfoExpedientes
 * @property {boolean} expediente
 * @property {boolean} expedienteAberto
 * @property {boolean} hasMandadoDevolucaoPendente
 * @property {boolean} mandadoDistribuido
 */

/**
 * Campos comuns (base) de um Documento no contexto da sua lista.
 * (Um Anexo também é um Documento e reaproveita estes campos.)
 *
 * @typedef {Object} Documento
 * @property {Documento[] | undefined} anexos
 * @property {number} id
 * @property {string} idUnicoDocumento
 * @property {string} titulo
 * @property {number} idTipo
 * @property {string} tipo
 * @property {string} codigoDocumento
 * @property {string} data ISO-8601 datetime string (ex.: "2023-04-04T17:15:27.087").
 * @property {boolean} documento
 * @property {number} idUsuario
 * @property {number} especializacoes
 * @property {string} nomeResponsavel
 *
 * @property {string} [tipoPolo] Ex.: "ambos".
 * @property {string} [participacaoProcesso] Ex.: "Ambos os polos, ADVOGADO".
 * @property {boolean} [favorito]
 * @property {boolean} [ativo]
 * @property {boolean} [documentoSigiloso]
 * @property {boolean} [usuarioInterno]
 * @property {boolean} [documentoApreciavel]
 * @property {string} [instancia] Ex.: "1º Grau".
 * @property {string} [nomeSignatario]
 * @property {boolean} [expediente]
 * @property {number} [numeroOrdem]
 * @property {number} [codigoInstancia]
 * @property {boolean} [pendenciaDocInstanciaOrigem]
 * @property {DocumentoInfoExpedientes} [infoExpedientes]
 * @property {boolean} [copia]
 * @property {boolean} [permiteCooperacaoJudiciaria]
 * @property {boolean} [dataJuntadaFutura]
 */

/**
 * @typedef {Object} LinksDocumento
 * @property {number} id
 * @property {string} link
 * @property {string} preview
 * @property {string} conteudoDocumento
 * @property {Documento} documento
 */
