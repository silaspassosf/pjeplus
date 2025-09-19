# BOOKMARKLETS PJePlus - Coleção Consolidada

## 📁 Estrutura dos Arquivos

Esta pasta contém os bookmarklets organizados e documentados para automação do sistema PJE e SISBAJUD:

```
bookmarklets/
├── minuta_pje.js           # Automação de minutas no PJE
├── series_teimosinha.js    # Extração de séries SISBAJUD
├── sisbajud_ordens.js      # Ordens judiciais SISBAJUD
└── README.md              # Este arquivo
```

## 🚀 Como Usar os Bookmarklets

### Passo 1: Copiar o Código
1. Abra o arquivo do bookmarklet desejado
2. Copie TODO o código JavaScript (a partir de `javascript: (function () {`)

### Passo 2: Criar Bookmarklet no Navegador
1. Abra o navegador (Chrome, Firefox, Edge, etc.)
2. Clique com botão direito na barra de favoritos
3. Selecione "Adicionar página" ou "Novo marcador"
4. Cole o código copiado no campo **URL**
5. Dê um nome descritivo no campo **Nome**
6. Salve o bookmarklet

### Passo 3: Executar
1. Abra a página do sistema correspondente
2. Clique no bookmarklet criado na barra de favoritos
3. Aguarde a execução e notificação

## 📋 Bookmarklets Disponíveis

### 1. Minuta PJE (`minuta_pje.js`)
- **Sistema**: PJE (Processo Judicial Eletrônico)
- **Função**: Automação completa de geração de minutas
- **Recursos**:
  - Extração automática de dados do processo
  - Geração de minuta formatada
  - Inserção automática no editor
  - Sistema anti-conflito

### 2. Séries Teimosinha (`series_teimosinha.js`)
- **Sistema**: SISBAJUD
- **Função**: Extração de séries elegíveis
- **Recursos**:
  - Detecção automática de séries
  - Extração de protocolo, data e valor
  - Geração de relatório HTML
  - Múltiplas estratégias de detecção

### 3. Ordens SISBAJUD (`sisbajud_ordens.js`)
- **Sistema**: SISBAJUD
- **Função**: Extração de ordens judiciais
- **Recursos**:
  - Extração de ordens executadas
  - Cálculo de valores bloqueados
  - Sistema de acumulação
  - Relatórios consolidados

## 🔧 Funcionalidades Comuns

Todos os bookmarklets incluem:
- ✅ Sistema de proteção contra conflitos
- ✅ Notificações visuais de status
- ✅ Cópia automática para clipboard
- ✅ Logs detalhados no console
- ✅ Tratamento de erros robusto
- ✅ Compatibilidade com múltiplos layouts

## 📊 Sistemas Suportados

| Sistema | Bookmarklets | Status |
|---------|-------------|---------|
| PJE | Minuta PJE | ✅ Ativo |
| SISBAJUD | Séries Teimosinha | ✅ Ativo |
| SISBAJUD | Ordens Judiciais | ✅ Ativo |

## 🐛 Depuração

Para depurar problemas:
1. Abra o console do navegador (F12)
2. Procure mensagens com os prefixos:
   - `[MINUTA PJE]`
   - `[TEIMOSINHA]`
   - `[SISBAJUD ORDENS]`
3. Verifique se há erros JavaScript

## ⚠️ Limitações

- Funcionam apenas nas páginas específicas dos sistemas
- Requerem JavaScript habilitado
- Dados são processados localmente (sem transmissão externa)
- Compatíveis apenas com navegadores modernos

## 🔄 Atualizações

- **Última atualização**: Dezembro 2024
- **Total de bookmarklets**: 3
- **Versões**: Todas otimizadas e testadas

## 📞 Suporte

Para problemas ou sugestões:
1. Verifique os logs do console
2. Teste em diferentes navegadores
3. Confirme se está na página correta do sistema

---

**Nota**: Estes bookmarklets são ferramentas de automação para facilitar o trabalho jurídico. Use conforme as normas éticas e legais aplicáveis.