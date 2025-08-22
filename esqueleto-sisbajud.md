# Esqueleto do Módulo SISBAJUD - Preenchimento de Minuta de Bloqueio

## Visão Geral
O módulo SISBAJUD automatiza o preenchimento completo de uma minuta de bloqueio judicial, desde a abertura da página até a protocolação final. O fluxo é baseado na função principal `preenchercamposSisbajud()` que coordena uma série de ações sequenciais.

## Fluxo Principal de Preenchimento

### 1. INICIALIZAÇÃO E VERIFICAÇÃO
- **Função:** `preenchercamposSisbajud(inverterPolo)`
- **Verificação:** Se não está na página de cadastro de minuta (`/minuta/cadastrar`)
- **Ação:** Redireciona para nova minuta via menu
- **Seletor usado:** `'span[id="maisPje_menuKaizen_itemmenu_nova_minuta"] a'`
- **Espera:** Elemento `'sisbajud-cadastro-minuta input[placeholder="Juiz Solicitante"]'`

### 2. PREPARAÇÃO DOS DADOS
- **Função:** Criação da lista de executados
- **Ação:** `criarCaixaDeSelecaoComReclamados()` ou `criarCaixaDeSelecaoComReclamantes()`
- **Condição:** Depende do parâmetro `inverterPolo`
- **Configuração:** Identifica seção de monitoramento com ID `"maisPje_sisbajud_monitor"`

### 3. PREENCHIMENTO DO JUIZ SOLICITANTE
- **Função:** `acao1()`
- **Campo:** Juiz Solicitante
- **Seletor:** `'input[placeholder*="Juiz"]'`
- **Técnica:** `escolherOpcaoSISBAJUD(seletor, magistrado)`
- **Valor:** `preferencias.sisbajud.juiz` (pode usar módulo8 para busca automática)
- **Simulação de tecla:** SETA PARA BAIXO (keycode 40) para abrir dropdown
- **Espera:** Opções `'mat-option[role="option"]'`

### 4. SELEÇÃO DE VARA/JUÍZO
- **Função:** `acao2()`
- **Campo:** Vara/Juízo
- **Seletor:** `'mat-select[name*="varaJuizoSelect"]'`
- **Técnica:** Focus + click para abrir dropdown
- **Ação:** Busca por texto correspondente em `'mat-option[role="option"]'`
- **Valor:** `preferencias.sisbajud.vara`
- **Clique:** Elemento que contém o texto da vara

### 5. NÚMERO DO PROCESSO
- **Função:** `acao3()`
- **Campo:** Número do Processo
- **Seletor:** `'input[placeholder="Número do Processo"]'`
- **Técnica:** Focus + value + triggerEvent('input') + blur
- **Valor:** `preferencias.processo_memoria.numero`

### 6. TIPO DE AÇÃO
- **Função:** `acao4()`
- **Campo:** Tipo de Ação
- **Seletor:** `'mat-select[name*="acao"]'`
- **Técnica:** Focus + click para dropdown
- **Busca:** Opção "Ação Trabalhista" em `'mat-option[role="option"]'`
- **Clique:** Elemento com texto específico

### 7. CPF/CNPJ DO AUTOR
- **Função:** `acao5()`
- **Campo:** CPF/CNPJ do Autor
- **Seletor:** `'input[placeholder*="CPF"]'`
- **Técnica:** Focus + value + triggerEvent('input') + blur
- **Valor:** `preferencias.processo_memoria.autor[0].cpfcnpj` (formatado sem pontos e traços)
- **Lógica:** Inverte dados se `inverterPolo = true`
- **Delay:** 250ms antes do preenchimento

### 8. NOME DO AUTOR
- **Função:** `acao6()`
- **Campo:** Nome do Autor
- **Seletor:** `'input[placeholder="Nome do autor/exequente da ação"]'`
- **Técnica:** Focus + value + triggerEvent('input') + blur
- **Valor:** `preferencias.processo_memoria.autor[0].nome`
- **Delay:** 250ms antes do preenchimento

### 9. CONFIGURAÇÃO DA TEIMOSINHA
- **Função:** `acao7()`
- **Campo:** Opção "Repetir a ordem"
- **Condição:** Se não for requisição de informações (`req_endereco = false`)
- **Seletor:** `'mat-radio-button'` que contenha "Repetir a ordem"
- **Técnica:** `querySelector('label').click()`
- **Configuração:** Só ativa se `preferencias.sisbajud.teimosinha != "nao"`

### 10. CONFIGURAÇÃO DE ENDEREÇO (Se aplicável)
- **Função:** `acao7_1()` e `acao7_2()`
- **Campo:** Checkbox "Endereços"
- **Seletor:** `'span[class*="mat-checkbox-label"]'` com texto "Endereços"
- **Técnica:** `parentElement.firstElementChild.firstElementChild.click()`
- **Desmarcar:** Radio button "Não" para dados sobre contas

### 11. CALENDÁRIO DA TEIMOSINHA
- **Função:** `acao8()`
- **Campo:** Data limite para repetição
- **Seletor inicial:** `'button[aria-label="Open calendar"]'`
- **Sequência de cliques:**
  1. Abrir calendário
  2. `'mat-calendar button[aria-label="Choose month and year"]'`
  3. `'mat-calendar td[aria-label="' + ano + '"]'` (selecionar ano)
  4. `'mat-calendar td[aria-label="' + mes + '"]'` (selecionar mês disponível)
  5. `'mat-calendar td[aria-label="' + dia + ' de ' + mes + '"]'` (selecionar dia)
- **Cálculo:** Data atual + número de dias da teimosinha + 2 dias (regra do SISBAJUD)

### 12. INSERÇÃO DOS EXECUTADOS
- **Função:** `acao10()` → `cadastro()`
- **Campo:** CPF/CNPJ dos réus/executados
- **Seletores:**
  - Input: `'input[placeholder="CPF/CNPJ do réu/executado"]'` ou `'input[placeholder="CPF/CNPJ da pessoa pesquisada"]'`
  - Botão: `'button[class*="btn-adicionar"]'`
- **Técnica:** 
  - Focus no input
  - Verificar se deve usar CNPJ raiz (primeiros 10 dígitos)
  - Preencher valor + triggerEvent('input')
  - Click no botão adicionar
- **Monitoramento:** MutationObserver para detectar adição na tabela
- **Tratamento de erros:** Observer para mensagens de erro do sistema

### 13. PREENCHIMENTO DO VALOR
- **Função:** `acao11()`
- **Campo:** Valor aplicado a todos
- **Condição:** Se não for requisição de endereço
- **Valor:** `preferencias.processo_memoria.divida.valor` formatado como moeda
- **Seletor:** `'input[placeholder*="Valor aplicado a todos"]'`
- **Interface:** Cria span clicável com o valor para facilitar preenchimento
- **Auto-preenchimento:** Se `preferencias.sisbajud.preencherValor == "sim"`

### 14. CONTA-SALÁRIO
- **Função:** `acao12()`
- **Campo:** Toggles de conta-salário
- **Seletor:** `'mat-slide-toggle label'`
- **Técnica:** Click em todos os labels (ativa todos os toggles)
- **Condição:** Se `preferencias.sisbajud.contasalario == "sim"`

### 15. SALVAMENTO E PROTOCOLAÇÃO
- **Função:** `acao13()`
- **Sequência:**
  1. **Salvar:** `'sisbajud-cadastro-minuta button'` com texto "Salvar"
  2. **Aguardar:** Mensagem em `'SISBAJUD-SNACK-MESSENGER'`
  3. **Protocolar:** `'sisbajud-detalhamento-minuta button'` com texto "Protocolar"
- **Tratamento de erro:** Se mensagem contém "não possui Instituição Financeira associada"
- **Condição:** Se `preferencias.sisbajud.salvarEprotocolar == "sim"`

## Funções Auxiliares Importantes

### `escolherOpcaoSISBAJUD(seletor, valor)`
- Simula seta para baixo para abrir dropdown
- Aguarda carregamento das opções
- Realiza múltiplas tentativas se necessário
- Clica na opção correta

### `clicarBotao(seletor, texto)`
- Aguarda elemento estar disponível
- Verifica se não está desabilitado
- Executa o clique
- Suporte a monitoramento opcional

### `esperarElemento(seletor, texto, timeout)`
- Usa MutationObserver para aguardar elementos
- Verifica se elemento não está desabilitado
- Timeout configurável

### `criarCaixaDeSelecaoComReclamados/Reclamantes()`
- Cria interface para seleção de partes do processo
- Acessa dados do processo em memória
- Permite seleção múltipla ou única

## Configurações e Preferências

### Estrutura `preferencias.sisbajud`
```javascript
{
  juiz: '',           // Nome do juiz ou 'modulo8' para busca automática
  vara: '',           // Nome da vara
  cnpjRaiz: 'não',    // Usar CNPJ raiz (10 dígitos)
  teimosinha: 'não',  // Ativar repetição da ordem (ou número de dias)
  contasalario: 'não',// Incluir contas salário
  preencherValor: 'não', // Auto-preencher valor do débito
  confirmar: 'não',   // Confirmação automática
  salvarEprotocolar: 'não' // Salvar e protocolar automaticamente
}
```

## Tratamento de Erros

### MutationObserver para Erros
- Monitora `'div[class="cdk-overlay-container"]'`
- Detecta mensagens específicas:
  - "CPF ou CNPJ inválidos."
  - "O Réu/Executado já foi incluído."
  - "CPF/CNPJ informado não está com situação cadastral regular"
  - "Falha ao obter retorno do sistema CCS."

### Recuperação de Erros
- Fecha mensagem de erro automaticamente
- Tenta novamente com CNPJ completo se CNPJ raiz falhar
- Continue processamento com próximo executado

## Pontos de Interrupção
- Tecla ESC interrompe o processo a qualquer momento
- Variável `interromper` é verificada em cada função
- Chama `fundo(false)` para limpar overlay