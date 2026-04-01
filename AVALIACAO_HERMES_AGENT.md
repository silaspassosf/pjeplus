# Avaliação: NousResearch/hermes-agent — Aplicabilidade ao PJePlus

**Data:** 31/03/2026  
**Repositório:** https://github.com/NousResearch/hermes-agent  
**Stars:** 20.5k | **Licença:** MIT | **Linguagem:** Python 92.8%  
**Versão atual:** v0.6.0 (2026.3.30)  

---

## O que é o Hermes-agent

CLI agent de propósito geral da Nous Research — "the self-improving AI agent".  
Arquitetura: LLM + 40+ ferramentas + ciclo de aprendizado fechado.

### Recursos-chave

| Recurso | Descrição |
|---|---|
| **Skills System** | Criação autônoma de arquivos `.md` de habilidades após tarefas complexas. Skills se auto-melhoram durante uso. Compatível com agentskills.io. |
| **Memoria persistente** | `MEMORY.md`, `USER.md`: notas duráveis entre sessões. FTS5 full-text search em conversas anteriores. |
| **Honcho user modeling** | Modelo dialético do usuário: aprende preferências, contexto e padrões ao longo do tempo. |
| **Agendamento cron** | Tarefas agendadas com entrega em Telegram/Discord/Slack. |
| **Subagents** | Spawn de subagentes isolados para workstreams paralelos. |
| **Self-improving loop** | Nudges periódicos para persistir conhecimento. Skills evoluem com o uso. |
| **MCP Integration** | Conecta qualquer MCP server para capacidades estendidas. |

---

## Análise de Aplicabilidade ao PJePlus

### RELEVANTE: Conceito de Skills como `.md` files

O Hermes-agent usa um sistema de **Skills como arquivos Markdown** com conhecimento procedural.  
No PJePlus, **já temos exatamente isso** em `.github/agents/`:

| Hermes | PJePlus (atual) | Ação |
|---|---|---|
| `skills/<nome>.md` | `.github/agents/Analise.md`, `.github/agents/PJE.md` | Padrão já adotado |
| Skills criadas da experiência | Atualizações manuais após cada sprint | Oportunidade: automatizar |
| Skills auto-melhoram | Não implementado | Oportunidade |

**Recomendação**: Adotar o formato de `skills` do Hermes como padrão para novas habilidades PJePlus. Criar `skills/` dentro de `.github/`:

```
.github/
├── agents/
│   ├── Analise.md   ← mantém (agente principal)
│   └── PJE.md       ← mantém (agente cirúrgico)
└── skills/
    ├── prazo-ciclo2.md       ← NOVO: conhecimento sobre filtros/loop ciclo2
    ├── sisb-bloqueios.md     ← NOVO: padrões SISBAJUD
    └── debug-selenium.md    ← NOVO: técnicas de debug Selenium/Angular
```

### RELEVANTE: Memória Persistente estruturada

O Hermes usa `MEMORY.md` + `USER.md` para notas duráveis.  
No PJePlus, `idx.md` serve como memória arquitetural, mas não tem:
- Seção de "lições aprendidas operacionais" (bugs encontrados + causa raiz)
- Registro de padrões de falha recorrentes

**Recomendação**: Adicionar seção `## Lições Operacionais` ao `idx.md` com registro incremental de bugs críticos e suas causas raiz.

### NÃO RELEVANTE: Integração direta do Hermes-agent

O Hermes-agent é um **agente de IA de propósito geral** (CLI → LLM → ferramentas).  
O PJePlus é um **sistema de automação Selenium** (Python → Firefox → PJe).  
São arquiteturas fundamentalmente diferentes — não faz sentido integrar o Hermes como dependência.

**Usar como inspiração de padrões, não como biblioteca.**

### PARCIALMENTE RELEVANTE: Self-improving via Skills

O loop de auto-melhoria do Hermes (agent cria skill → skill melhora → agent usa skill melhorada) pode ser mapeado para o PJePlus como:

1. Após cada sprint, identificar padrões operacionais novos
2. Criar/atualizar arquivo `.md` de skill correspondente
3. Na próxima sessão, o agente (Analise/PJE) incorpora o conhecimento

Isso já acontece informalmente via `planos_executados.md` e `idx.md`. O Hermes formaliza com arquivo dedicado por domínio.

---

## Recomendações Concretas

### Imediato (baixo custo, alta utilidade)

1. **Criar `skills/` em `.github/`** com 3 skills prioritárias:
   - `prazo-loop.md`: padrões de ciclo 1/2/3, filtros, SmartFinder, bugs conhecidos
   - `sisb-workflow.md`: SISBAJUD bloqueios, processamento, relatórios
   - `selenium-angular.md`: padrões de espera, Angular SPA, overlays

2. **Adicionar seção `## Lições Operacionais` ao `idx.md`**  
   Registrar: bug encontrado → causa raiz → fix aplicado (ex: o bug `log=True` deste sprint)

### Médio prazo (opcional)

3. **Adotar formato agentskills.io** para compatibilidade com o ecossistema Hermes  
   (skills declarativas com metadados YAML frontmatter)

### NÃO fazer

- Instalar/integrar o Hermes-agent como dependência do PJePlus
- Clonar o repositório dentro do projeto (compatibilidade de ambiente WSL vs Windows)
- Tentar usar o Hermes como orquestrador do PJePlus (arquiteturas incompatíveis)

---

## Referências

- Repositório: https://github.com/NousResearch/hermes-agent
- Docs: https://hermes-agent.nousresearch.com/docs/user-guide/skills
- Skills Hub: https://agentskills.io/

---

## Status

- [x] Repositório avaliado
- [x] Análise de aplicabilidade concluída
- [ ] Skills prioritárias criadas em `.github/skills/`
- [ ] `idx.md` atualizado com seção Lições Operacionais
