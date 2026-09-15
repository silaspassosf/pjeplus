# PJeAutoActions — Motor Autônomo de Ações Automatizadas

Motor headless e programático de automação do PJe (KZ/Angular), desacoplado de extensões externas (como MaisPJe) e independente de APIs WebExtension (`browser.storage`, `chrome.runtime`).

Pode ser consumido por qualquer userscript (Tampermonkey), extensão de navegador (Chrome/Firefox) ou injetado via console DevTools.

---

## Estrutura do Pacote

```
Script/autoactions/
├── autoactions.js         # Fachada central (window.PjeAutoActions) e orquestrador de pipeline
├── gigs_engine.js         # Submotor GIGS (inclusão/conclusão de atividades, prazos, observações)
├── despacho_engine.js     # Submotor Despacho/Minuta (conclusão, magistrado, modelos, editor)
└── anexar_engine.js       # Submotor Anexar (certidões, tipo de documento, editor e assinatura)
```

---

## Contrato Público (`window.PjeAutoActions`)

### 1. Invocação Direta via Dispatcher
```javascript
await window.PjeAutoActions.executar(nomeAcao, params);
```

### 2. Submotor GIGS (`gigs`)
```javascript
// Criar atividade
await window.PjeAutoActions.gigs({
    acao: 'criar',                       // 'criar' (padrão) ou 'concluir'
    tipoAtividade: 'Cumprimento de Alvará',
    responsavel: 'DIRETOR',              // opcional
    prazo: '5',                          // dias ou data limite
    observacao: 'Alvarás expedidos para autor e perito'
});

// Concluir atividade existente
await window.PjeAutoActions.gigs({
    acao: 'concluir',
    tipoAtividade: 'Cumprimento de Alvará',
    observacao: 'expedidos'              // filtro por texto contido
});
```

### 3. Submotor Despacho (`despacho`)
```javascript
await window.PjeAutoActions.despacho({
    tipo: 'Despacho',                   // 'Despacho', 'Decisão' ou 'Sentença'
    juiz: 'Nome do Magistrado',         // opcional (seleciona no select de juiz)
    modelo: 'Alvará - Ciência e Liberação', // opcional (busca na árvore)
    texto: 'Conteúdo livre...',         // opcional (injeta no CKEditor)
    descricao: 'Ciência dos alvarás',
    salvar: true,                       // padrão true
    assinar: false                      // padrão false (true envia para assinatura)
});
```

### 4. Submotor Anexar (`anexar`)
```javascript
await window.PjeAutoActions.anexar({
    tipo: 'Certidão',                   // padrão 'Certidão'
    descricao: 'Certidão de Expedição',
    texto: 'Texto da certidão...',
    sigilo: false,
    assinar: false                      // true assina e junta imediatamente
});
```

### 5. Execução em Pipeline Sequencial
```javascript
await window.PjeAutoActions.executarPipeline([
    { acao: 'anexar', params: { tipo: 'Certidão', descricao: '...', texto: '...' } },
    { acao: 'gigs', params: { tipoAtividade: 'Cumprimento', prazo: '5', observacao: '...' } },
    { acao: 'despacho', params: { tipo: 'Despacho', modelo: '...' } }
], (passoAtual, total, passo) => {
    console.log(`Progresso: ${passoAtual}/${total} - ${passo.acao}`);
});
```
