# MaisPJe Bookmarklets Corrigidos

Este conjunto de arquivos contém bookmarklets JavaScript para automação do sistema PJe, corrigidos e otimizados para resolver problemas de CSS e limitações de tamanho.

## Arquivos Criados

### 1. bookmarklet_completo_minificado.txt
- **Descrição**: Bookmarklet completo com todas as funcionalidades (Despacho, GIGS, Anexar)
- **Tamanho**: ~8KB (minificado)
- **Uso**: Para quem quer todas as funcionalidades em um único bookmarklet
- **Características**:
  - Interface completa com menu de grupos
  - Todos os botões configurados conforme `botoes_maispje.json`
  - Suporte ao campo de responsável no GIGS (adicionado)
  - CSS corrigido (sem pseudo-elementos `-ms-*`)

### 2. bookmarklet_ultra_minificado.txt
- **Descrição**: Versão ultra-compacta com funcionalidades essenciais
- **Tamanho**: ~4KB (extremamente otimizado)
- **Uso**: Para contornar limitações de tamanho em bookmarklets
- **Características**:
  - Apenas botões mais usados por categoria
  - Interface simplificada
  - Todas as funções principais preservadas

### 3. bookmarklet_despacho.txt
- **Descrição**: Bookmarklet específico para fluxos de Despacho
- **Tamanho**: ~2KB
- **Uso**: Para quem trabalha principalmente com despachos
- **Características**:
  - Todos os botões de despacho
  - Interface azul (#0080ff)
  - Fluxo otimizado: Análise → Conclusão → Modelo

### 4. bookmarklet_gigs.txt
- **Descrição**: Bookmarklet específico para GIGS/AutoGigs
- **Tamanho**: ~2KB
- **Uso**: Para quem trabalha principalmente com atividades GIGS
- **Características**:
  - Todos os botões de GIGS configurados
  - Interface laranja (#ff8040)
  - Suporte a responsável, observação e prazo
  - Tipos: prazo, comentário, lembrete

### 5. bookmarklet_anexar.txt
- **Descrição**: Bookmarklet específico para Anexar documentos
- **Tamanho**: ~2KB
- **Uso**: Para quem trabalha principalmente com anexos
- **Características**:
  - Todos os botões de anexar configurados
  - Interface verde (#008000)
  - Suporte a PDF, certidões, cartas, etc.
  - Preenchimento automático de tipo e descrição

## Correções Implementadas

### 1. CSS Corrigido
- **Problema**: Pseudo-elementos `-ms-*` causavam erros de parsing
- **Solução**: Removidos todos os pseudo-elementos não-padrão
- **Resultado**: CSS válido e compatível com todos os navegadores

### 2. Campo Responsável no GIGS
- **Problema**: Campo de responsável não era preenchido automaticamente
- **Solução**: Adicionado seletor `input[aria-label*="Responsável pela atividade"]`
- **Integração**: Funciona com o novo padrão `'prazo/responsável/observação'` do Fix.py

### 3. Otimização de Tamanho
- **Problema**: Bookmarklets muito grandes para alguns navegadores
- **Solução**: Criadas versões separadas e ultra-minificada
- **Benefícios**: Flexibilidade na escolha conforme a necessidade

## Como Usar

### Instalação
1. Copie o conteúdo do arquivo desejado
2. Crie um novo bookmark no navegador
3. Cole o código no campo URL
4. Dê um nome descritivo (ex: "MaisPJe Completo", "MaisPJe GIGS")

### Uso no PJe
1. Abra o processo no PJe
2. Clique no bookmark
3. Selecione a categoria (se aplicável)
4. Clique no botão desejado
5. O sistema executará o fluxo automaticamente

## Funcionalidades por Tipo

### Fluxo Despacho
1. Clica em "Análise"
2. Aguarda 1 segundo
3. Clica em "Conclusão ao Magistrado"
4. Aguarda 1 segundo
5. Preenche o campo de filtro com o modelo

### Fluxo GIGS
1. Abre o GIGS se estiver fechado
2. Para tipo "comentário": adiciona observação
3. Para tipo "prazo": cria nova atividade com:
   - Tipo de atividade
   - Observação
   - Responsável (se especificado)
   - Prazo em dias

### Fluxo Anexar
1. Clica no botão de anexar
2. Ativa switch PDF se necessário
3. Seleciona tipo de documento
4. Preenche descrição
5. Pressiona Enter para confirmar

## Dados Integrados

Os bookmarklets incluem todos os dados do arquivo `botoes_maispje.json`:
- **19 botões de Despacho** (Genérico, Meios, Homol, etc.)
- **13 botões de GIGS** (Pesq, IDPJ, Lib, pec, etc.)
- **22 botões de Anexar** (CP, DEVCP, PDF, Calc, etc.)

## Compatibilidade

- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Edge
- ✅ Safari
- ✅ Todos os navegadores modernos

## Logs e Debugging

Todos os bookmarklets incluem:
- `console.log()` para acompanhar execução
- `try/catch` para capturar erros
- `alert()` para notificar problemas
- Mensagens descritivas para cada etapa

## Recomendações de Uso

### Para Uso Geral
- Use `bookmarklet_completo_minificado.txt`

### Para Limitações de Tamanho
- Use `bookmarklet_ultra_minificado.txt`

### Para Fluxos Específicos
- Use os bookmarklets separados por função
- Ideal para usuários especializados em uma área

### Para Desenvolvimento
- Os arquivos podem ser editados para ajustar botões
- Mantenha a estrutura de dados para compatibilidade
- Teste sempre em ambiente de desenvolvimento primeiro

## Troubleshooting

### Bookmarklet não funciona
1. Verifique se colou o código completo
2. Certifique-se que começa com `javascript:`
3. Teste em uma página do PJe

### Botões não aparecem
1. Verifique se o PJe carregou completamente
2. Recarregue a página e tente novamente
3. Abra o console (F12) para ver erros

### Fluxo não executa
1. Verifique se está na tela correta do PJe
2. Alguns botões dependem do estado do processo
3. Aguarde o carregamento completo antes de usar

## Changelog

### v2.0 (Atual)
- CSS corrigido (sem pseudo-elementos `-ms-*`)
- Campo responsável GIGS adicionado
- Versões separadas por função
- Versão ultra-minificada
- Documentação completa

### v1.0 (Original)
- Versão inicial com todos os fluxos
- Dados integrados do JSON
- Interface básica
