# Relatório: Script Tampermonkey "Documentos Execução"

## Resumo
Criado script Tampermonkey que identifica e lista documentos específicos de execução na timeline do PJe TRT2, baseado na lógica de leitura de timeline do fluxo Argos do `m1.py`.

## Funcionalidades Implementadas

### 1. **Ativação Condicional**
- ✅ Executa apenas em páginas que contêm `/detalhe` de `https://pje.trt2.jus.br`
- ✅ Verifica presença da timeline antes de ativar
- ✅ Log detalhado no console para depuração

### 2. **Interface do Usuário**
- ✅ Botão "Check" no canto inferior direito, posicionado um pouco acima
- ✅ Estilo moderno com efeitos hover e transições
- ✅ Feedback visual durante a análise (botão fica amarelo "Analisando...")
- ✅ Posição fixa que não interfere com a interface do PJe

### 3. **Leitura da Timeline**
Baseado na lógica do `m1.py`, implementa:
- ✅ Múltiplos seletores CSS para compatibilidade: `'li.tl-item-container'`, `'.tl-data .tl-item-container'`, `'.timeline-item'`
- ✅ Busca por links de documento: `'a.tl-documento, a[href*="documento"]'`
- ✅ Processamento robusto com tratamento de erros por item

### 4. **Documentos Identificados**
O script procura e armazena os seguintes documentos:
- ✅ **Alvará**: termos `['alvará', 'alvara']`
- ✅ **Certidão de pesquisa patrimonial**: termos `['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial']`
- ✅ **Carta Ação**: termos `['carta ação', 'carta acao', 'carta de ação']`
- ✅ **Serasa**: termos `['serasa']`
- ✅ **CNIB**: termos `['cnib']`

### 5. **Relatório Interativo**
- ✅ Modal centralizado com tabela organizada
- ✅ Exibe: Tipo, Nome do Documento, ID único, Botão de Ação
- ✅ Design responsivo com scroll automático
- ✅ Botão de fechar (✕) no cabeçalho
- ✅ Efeitos hover nas linhas da tabela

### 6. **Funcionalidade de Seleção**
- ✅ Cada item possui botão "Selecionar" clicável
- ✅ **Clique seleciona APENAS o item na timeline** (não abre)
- ✅ Scroll automático até o documento selecionado
- ✅ Destaque visual temporário (border azul + fundo amarelo)
- ✅ Feedback no botão (muda para "✓ Selecionado" temporariamente)

## Características Técnicas

### Estrutura do Código
```javascript
// Funções principais:
- verificarPagina()           // Verifica compatibilidade da página
- criarBotaoCheck()           // Cria interface do usuário
- lerTimelineCompleta()       // Extrai documentos da timeline
- gerarRelatorio()            // Exibe tabela interativa
- selecionarDocumentoTimeline() // Seleciona item na timeline
- executarAnaliseTimeline()   // Função principal de execução
```

### Tratamento de Erros
- ✅ Try-catch em todas as funções críticas
- ✅ Logs detalhados no console
- ✅ Fallbacks para elementos não encontrados
- ✅ Restauração do estado da interface em caso de erro

### Performance
- ✅ Inicialização assíncrona aguarda carregamento da página
- ✅ Verificação de elementos antes de tentar interagir
- ✅ Remoção de relatórios anteriores para evitar duplicação
- ✅ Timeouts apropriados para estabilização da interface

## Como Usar

### Instalação
1. Instalar extensão Tampermonkey no navegador
2. Criar novo script e colar o conteúdo de `Documentos_execucao.user.js`
3. Salvar e ativar o script

### Utilização
1. Navegar para página de detalhes de processo no PJe TRT2
2. Aguardar carregamento da timeline
3. Clicar no botão "Check" (canto inferior direito)
4. Analisar relatório gerado
5. Clicar em "Selecionar" para destacar documentos na timeline

## Logs de Depuração
O script gera logs detalhados no console:
```
[DOCS-EXEC] Script carregado
[DOCS-EXEC] Página de detalhes com timeline detectada
[DOCS-EXEC] Botão Check criado
[DOCS-EXEC] Encontrados X itens com seletor: li.tl-item-container
[DOCS-EXEC] Documento encontrado: Alvará - [nome do documento]
[DOCS-EXEC] Total de documentos encontrados: X
[DOCS-EXEC] Relatório exibido
[DOCS-EXEC] Selecionando documento: [nome]
[DOCS-EXEC] Documento selecionado com sucesso: [nome]
```

## Baseado em
- **Arquivo fonte**: `d:\PjePlus\m1.py`
- **Função de referência**: `lerTimelineCompleta()`, `buscar_documentos_sequenciais()`
- **Seletores adaptados**: `li.tl-item-container`, `a.tl-documento`

## Status
✅ **Implementado e testado** - Pronto para uso

---
**Data:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Arquivo:** Documentos_execucao.user.js
**Compatibilidade:** PJe TRT2 (https://pje.trt2.jus.br/pjekz/processo/detalhe/*)
