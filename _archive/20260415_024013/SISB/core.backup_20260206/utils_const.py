"""
SISB Core - Constantes
"""

SISBAJUD_URLS = {
    'base': 'https://sisbajud.cnj.jus.br',
    'login': 'https://sisbajud.cnj.jus.br/login',
    'teimosinha': 'https://sisbajud.cnj.jus.br/teimosinha',
    'minuta_cadastrar': 'https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar'
}

TIMEOUTS = {
    'elemento_padrao': 10,
    'elemento_rapido': 5,
    'elemento_lento': 20,
    'pagina_carregar': 30,
    'script_executar': 15
}

SELECTORS = {
    'input_juiz': 'input[placeholder*="Juiz"]',
    'input_processo': 'input[placeholder="Numero do Processo"]',
    'input_cpf': 'input[placeholder*="CPF"]',
    'input_nome_autor': 'input[placeholder="Nome do autor/exequente da acao"]',
    'botao_consultar': 'button.mat-fab.mat-primary',
    'botao_salvar': 'button.mat-fab.mat-primary mat-icon.fa-save',
    'tabela_ordens': 'table.mat-table',
    'cabecalho_tabela': 'th.cdk-column-sequencial'
}