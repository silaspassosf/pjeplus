# GIGS XSXS Overlay - Script Tampermonkey

## Descrição

Script Tampermonkey que carrega dados de **GIGS** (Atividades) via API para todos os processos na tabela de **Atividades (XSXS)** e exibe um overlay compacto no campo **Responsável** de cada linha.

## Funcionalidade

- ✅ Lê automaticamente a tabela de Atividades do PJe (xsxs)
- ✅ Extrai número CNJ de cada processo
- ✅ Resolve ID interno via API `/pje-comum-api/api/processos?numero=`
- ✅ Busca dados de GIGS via API `/pje-gigs-api/api/atividade/processo/{idProcesso}`
- ✅ Renderiza overlay no campo Responsável com:
  - Contagem de GIGs encontrados
  - Tipo de atividade + Data prazo + Status
  - Nome do responsável em destaque (cores)
  - Observações resumidas
  - Indicador "+X mais" se houver muitos GIGs

## Instalação

1. Instale a extensão **Tampermonkey** no Firefox/Chrome
2. Crie um novo script
3. Cole o conteúdo de `gigs-xsxs-overlay.user.js`
4. Salve

## Uso

### Automático (ao carregar a página)
- Ao entrar na página de GIGS Atividades, o script aguarda ~1s e executa automaticamente
- O overlay aparece no campo Responsável de cada processo

### Manual (no console do navegador)
```javascript
window.gigsXsxsOverlayRecarregar()
```

## Estrutura do Script

```
gigs-xsxs-overlay.user.js
├── BLOCO 1: Regex e Helpers
│   └── extrairIdDoProcessoBruto(), getUrlBase()
├── BLOCO 2: Buscar ID do Processo
│   └── obterIdProcessoPorNumero(numeroProcesso)
├── BLOCO 3: Buscar GIGs
│   └── obterGigsDoProcesso(idProcesso)
├── BLOCO 4: Ler Tabela
│   └── lerProcessosDaTabelaXsxs()
├── BLOCO 5: Renderizar Overlay
│   └── renderizarOverlay(tdResponsavel, gigs)
├── BLOCO 6: Orquestrador
│   └── executarXsxsOverlay()
└── BLOCO 7: Ativa o Script
```

## APIs Utilizadas

| Endpoint | Descrição |
|----------|-----------|
| `/pje-comum-api/api/processos?numero={numero}` | Resolve ID interno do processo pelo número CNJ |
| `/pje-gigs-api/api/atividade/processo/{idProcesso}` | Lista de GIGs (atividades) do processo |

## Padrão Seguido

O script segue o padrão encontrado em:
- `pet.js` - estrutura de funções async e tratamento de erros
- `gigs-plugin.js` - funções auxiliares de renderização de overlay
- `apis.js` - padrão de chamadas HTTP com fetch + credentials

## Notas

- Pequena pausa de 200ms entre requisições para não sobrecarregar a API
- Suporta regex de data ISO (2025-05-19) e outros formatos
- Logged em console com prefixo `[gigs-xsxs]` para rastrear execução
- Trunca observações a 30 caracteres
- Mostra apenas os 3 primeiros GIGs no overlay, indicando se há mais

## Compatibilidade

- ✅ Firefox (Tampermonkey)
- ✅ Chrome (Tampermonkey)
- ✅ Qualquer navegador com Tampermonkey/Greasemonkey

## Debug

Abra o console do navegador (F12) para ver os logs:
```
[gigs-xsxs] Iniciando leitura de GIGS para tabela XSXS...
[gigs-xsxs] Encontrados 13 processos na tabela
[gigs-xsxs] Processando 1001861-91.2025.5.02.0601...
[gigs-xsxs] ✓ 1001861-91.2025.5.02.0601 atualizado com 5 GIGS
...
[gigs-xsxs] Conclusão: Overlay renderizado para todos os processos
```
