# Mapeamento de Funções Externas - Pasta Peticao

Este documento mapeia todas as funções usadas pelos arquivos na pasta `/Peticao` que são definidas em outros arquivos do projeto.

## Arquivos Analisados
- `__init__.py`
- `api_client.py`
- `consolida_delete.py`
- `helpers.py`
- `orquestrador.py`
- `pet.py`
- `progresso.py`

### Funções de `logging` (usadas em `__init__.py`)
- `getLogger` - usada em `__init__.py`

### Funções de `Peticao.api_client`

## Funções Externas Utilizadas

### Funções de `Fix.log`
- `getmodulelogger` - usada em `api_client.py`, `orquestrador.py`, `pet.py`

### Funções de `Fix.extracao`
- `extrair_direto` - usada em `helpers.py`, `pet.py`
- `extrair_documento` - usada em `helpers.py`, `pet.py`
- `criar_gigs` - usada em `helpers.py`, `pet.py`
- `extrair_dados_processo` - usada em `helpers.py`, `orquestrador.py`

### Funções de `Fix.variaveis_client`
- `PjeApiClient` - usada em `helpers.py`
- `session_from_driver` - usada em `helpers.py`

### Funções de `api.variaveis_resolvers`
- `obter_chave_ultimo_despacho_decisao_sentenca` - usada em `helpers.py`

### Funções de `Fix.core`
- `aguardar_renderizacao_nativa` - usada em `helpers.py`, `orquestrador.py`, `pet.py`

### Funções de `atos.wrappers_ato`
- `ato_agpetidpj` - usada em `helpers.py`
- `ato_agpet` - usada em `helpers.py`
- `ato_agpinter` - usada em `helpers.py`
- `ato_assistente` - usada em `helpers.py`, `pet.py`
- `ato_instc` - usada em `pet.py`
- `ato_inste` - usada em `pet.py`
- `ato_gen` - usada em `pet.py`
- `ato_laudo` - usada em `pet.py`
- `ato_esc` - usada em `pet.py`
- `ato_escliq` - usada em `pet.py`
- `ato_datalocal` - usada em `pet.py`
- `ato_ceju` - usada em `pet.py`
- `ato_respcalc` - usada em `pet.py`
- `ato_concor` - usada em `pet.py`
- `ato_prevjud` - usada em `pet.py`
- `ato_naocoaf` - usada em `pet.py`
- `ato_naosimba` - usada em `pet.py`
- `ato_teim` - usada em `pet.py`
- `ato_adesivo` - usada em `pet.py`

### Funções de `Prazo.p2b_core`
- `normalizar_texto` - usada em `pet.py`
- `gerar_regex_geral` - usada em `pet.py`

### Funções de `Peticao.progresso`
- `carregar_progresso_pet` - usada em `orquestrador.py`, `pet.py`
- `salvar_progresso_pet` - usada em `pet.py`
- `marcar_processo_executado_pet` - usada em `orquestrador.py`, `pet.py`
- `processo_ja_executado_pet` - usada em `orquestrador.py`, `pet.py`

### Funções de `Fix.monitoramento_progresso_unificado` (usadas em `progresso.py`)
- `carregar_progresso_unificado` - usada em `progresso.py`
- `salvar_progresso_unificado` - usada em `progresso.py`
- `marcar_processo_executado_unificado` - usada em `progresso.py`
- `processo_ja_executado_unificado` - usada em `progresso.py`

### Funções de `Peticao.api_client`
- `PeticaoAPIClient` - usada em `orquestrador.py`
- `PeticaoItem` - usada em `orquestrador.py`
- `_normalizar` - usada em `api_client.py`
- `asArray` - usada em `api_client.py` (função auxiliar JavaScript)
- `fetch` - usada em `api_client.py` (função JavaScript)
- `texto_classificacao` - usada em `api_client.py` (propriedade da classe PeticaoItem)

### Funções de `Fix.utils`
- `driver_pc` - usada em `pet.py`
- `login_cpf` - usada em `pet.py`
- `configurar_recovery_driver` - usada em `pet.py`

### Funções de `Peticao.orquestrador`
- `executar_fluxo_pet` - usada em `pet.py`
- `PETOrquestrador` - usada em `orquestrador.py`

### Funções de `Fix.monitoramento_progresso_unificado`
- `carregar_progresso_unificado` - usada em `progresso.py`
- `salvar_progresso_unificado` - usada em `progresso.py`
- `marcar_processo_executado_unificado` - usada em `progresso.py`
- `processo_ja_executado_unificado` - usada em `progresso.py`

### Funções de `Peticao.helpers`
- `checar_habilitacao` - usada em `pet.py`
- `agravo_peticao` - usada em `pet.py`
- `def_quesitos` - usada em `pet.py`
- `apagar` - usada em `orquestrador.py`
- `_buscar_documento_relevante_timeline` - usada em `helpers.py`
- `_desp_assist` - usada em `helpers.py`
- `_extrair_texto_despacho` - usada em `helpers.py`
- `_extrair_nome_assinante` - usada em `helpers.py`
- `_extrair_texto_peticao` - usada em `helpers.py`
- `_extrair_id_doc_peticao` - usada em `helpers.py`
- `_obter_lista_advogados` - usada em `helpers.py`
- `_normalizar_delete_processes` - usada em `helpers.py`

### Funções de `Peticao.consolida_delete`
- `consolidar_delete_com_bookmarklet` - usada em `orquestrador.py`
- `extrair_processos_delete` - usada em `consolida_delete.py`
- `gerar_bookmarklet_apagar` - usada em `consolida_delete.py`

### Outras funções e métodos utilizados
- `selenium.webdriver.remote.webdriver.WebDriver`
- `selenium.webdriver.common.by.By`
- `selenium.webdriver.support.ui.WebDriverWait`
- `json.loads` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `json.dumps` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `json.load` - usada em `helpers.py`
- `json.dump` - usada em `helpers.py`, `consolida_delete.py`
- `re.search` - usada em `helpers.py`, `pet.py`
- `re.match` - usada em `helpers.py`, `pet.py`
- `re.sub` - usada em `helpers.py`
- `reversed` - usada em `helpers.py`
- `datetime.datetime` - usada em `helpers.py`
- `datetime.timedelta` - usada em `helpers.py`
- `time.sleep` - usada em `helpers.py`
- `pathlib.Path` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `Path.exists` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `Path.read_text` - usada em `helpers.py`, `consolida_delete.py`
- `Path.write_text` - usada em `helpers.py`
- `Path.absolute` - usada em `consolida_delete.py`
- `str.strip` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `str.lower` - usada em `helpers.py`, `pet.py`, `consolida_delete.py`
- `str.upper` - usada em `helpers.py`
- `str.replace` - usada em `helpers.py`
- `str.isdigit` - usada em `consolida_delete.py`
- `len` - usada em `helpers.py`, `pet.py`, `orquestrador.py`, `consolida_delete.py`
- `any` - usada em `helpers.py`, `pet.py`
- `isinstance` - usada em `helpers.py`, `pet.py`, `orquestrador.py`, `consolida_delete.py`
- `getattr` - usada em `helpers.py`, `pet.py`
- `print` - usada em `helpers.py`, `pet.py`, `orquestrador.py`, `consolida_delete.py`
- `open` - usada em `helpers.py`, `consolida_delete.py`
- `sys.path.insert` - usada em `pet.py`
- `os.path.abspath` - usada em `pet.py`
- `os.path.dirname` - usada em `pet.py`
- `list.append` - usada em `consolida_delete.py`
- `list.split` - usada em `consolida_delete.py`
- `list.join` - usada em `consolida_delete.py`
- `list.forEach` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `list.some` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `Array.isArray` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `String` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `function` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `console.log` - usada em `consolida_delete.py` (JavaScript no bookmarklet)
- `console.error` - usada em `consolida_delete.py` (JavaScript no bookmarklet)

## Dependências do Módulo Peticao

O módulo Peticao depende dos seguintes módulos do projeto:
- `Fix` - para funcionalidades básicas de log, extração e utils
- `atos` - para as ações específicas que podem ser executadas nos processos
- `Prazo` - para funcionalidades compartilhadas de processamento
- `api` - para resolução de variáveis
- `selenium` - para automação web
- `json` - para manipulação de dados JSON
- `re` - para expressões regulares
- `datetime` - para manipulação de datas
- `pathlib` - para manipulação de caminhos de arquivos

## Entry Points

Funções que servem como pontos de entrada para o módulo Peticao:
- `run_pet` - função principal para execução do pipeline de petições
- `executar_fluxo_pet` - entry point do pipeline de petições (compatível com x.py)
- `classificar` - função para classificar petições em buckets
- `resolver_acao` - função para resolver a ação a ser executada com base na classificação
- `analise_pet` - função para análise de petições que caíram no bucket de análise
- `PETOrquestrador` - classe principal do orquestrador de petições