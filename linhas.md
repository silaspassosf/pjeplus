# Função de Marcação de Linhas Clicadas - Análise Estrutural

## Contexto
Esta função está localizada no `gigs-plugin.js` (linha ~32510) e é executada dentro de um event listener global de clique.

## Estrutura da Função

### Condição de Ativação
```javascript
} else if (document.location.href.includes('/pjekz/gigs/relatorios/')) { //Relatorio GIGS: deixa linhas clicadas em azul background-color:#a8e5ff
```

**Quando ativa:**
- URL contém `/pjekz/gigs/relatorios/` (página de relatórios GIGS)
- Exemplo: `https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades`

### Lógica de Detecção
```javascript
let tabela = document.querySelector('pje-data-table tbody');
if (tabela?.contains(event.target)) {
```

**Verificações:**
1. Seleciona o tbody da tabela `pje-data-table`
2. Verifica se o elemento clicado (`event.target`) está dentro dessa tabela

### Processamento da Linha
```javascript
let linha = event.target.closest('tr');
```

**Como encontra a linha:**
- Usa `closest('tr')` para subir na árvore DOM até encontrar a linha `<tr>` mais próxima

### Alternância de Cores
```javascript
if (linha.style.backgroundColor == 'rgb(240, 240, 240)') {
    linha.style.backgroundColor = 'rgb(168, 230, 255)';
} else if(linha.style.backgroundColor == 'rgb(168, 230, 255)') {
    linha.style.backgroundColor = 'rgb(240, 240, 240)';
} else if(linha.style.backgroundColor == 'white') {
    linha.style.backgroundColor = 'rgb(168, 229, 255)';
} else if(linha.style.backgroundColor == 'rgb(168, 229, 255)') {
    linha.style.backgroundColor = 'white';
}
```

**Mapeamento de cores:**
- `rgb(240, 240, 240)` (cinza claro) ↔ `rgb(168, 230, 255)` (azul claro)
- `white` ↔ `rgb(168, 229, 255)` (azul um pouco diferente)

## Possíveis Motivos para Não Funcionar

### 1. URL Incorreta
- A função só ativa se `document.location.href.includes('/pjekz/gigs/relatorios/')`
- Verificar se a URL atual corresponde exatamente

### 2. Estrutura DOM Diferente
- Espera `pje-data-table tbody` como seletor da tabela
- Se a estrutura mudou, `tabela` será `null`

### 3. Event Target Fora da Tabela
- `tabela?.contains(event.target)` retorna `false`
- Clique pode estar em elementos fora da tabela (cabeçalho, paginação, etc.)

### 4. Linha Não Encontrada
- `event.target.closest('tr')` retorna `null`
- Elemento clicado pode não estar dentro de uma `<tr>`

### 5. Estilo Inline Já Aplicado
- Se `linha.style.backgroundColor` não corresponde aos valores esperados
- Outros estilos CSS podem estar sobrescrevendo

### 6. Event Listener Não Registrado
- O código precisa estar carregado antes dos cliques
- Extensões ou scripts podem interferir

## Versão Similar para Meu Painel
Há uma versão quase idêntica para `/pjekz/gigs/meu-painel` que usa duas tabelas:

```javascript
} else if (document.location.href.includes('/pjekz/gigs/meu-painel')) {
    let tabela1 = document.querySelectorAll('pje-data-table tbody')[0];
    let tabela2 = document.querySelectorAll('pje-data-table tbody')[1];

    if (tabela1?.contains(event.target) || tabela2?.contains(event.target)) {
        // Lógica idêntica de alternância
    }
}
```

## Bookmarklet Equivalente

```javascript
javascript:document.addEventListener('click', function(e) {let tabela = document.querySelector('pje-data-table tbody');if (tabela && tabela.contains(e.target)) {let linha = e.target.closest('tr');if (linha) {let cor = linha.style.backgroundColor;if (cor === 'rgb(240, 240, 240)') {linha.style.backgroundColor = 'rgb(168, 230, 255)';} else if (cor === 'rgb(168, 230, 255)') {linha.style.backgroundColor = 'rgb(240, 240, 240)';} else if (cor === 'white') {linha.style.backgroundColor = 'rgb(168, 229, 255)';} else if (cor === 'rgb(168, 229, 255)') {linha.style.backgroundColor = 'white';}}}});
```

**Como usar:**
1. Criar um novo bookmark no navegador
2. Colar o código acima no campo URL
3. Nomear como "Marcar Linhas GIGS" 
4. Executar na página de relatórios GIGS (`/pjekz/gigs/relatorios/`)
5. Clicar nas linhas da tabela para alternar entre branco/cinza e azul