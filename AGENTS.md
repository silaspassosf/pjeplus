# PJePlus — Instruções para GitHub Copilot

## Organograma (mesma estrutura do `.claude/agents/` para Claude Code, portada para Copilot)

```
Você (Board)
  └─ ceo        — estratégia, decompõe o pedido em ordens de trabalho
      └─ cto    — arquitetura, atribui competência, gate de qualidade
          ├─ senior-dev-backend  — Python (Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/, Peticao/, bianca/, core/)
          ├─ senior-dev-webext   — JS/HTML (maispje/, AVJT/, Script/)
          └─ qa-lead             — gate final, caça-bugs/redundâncias, mantém idx.md
```

Agentes definidos em [`.github/agents/*.agent.md`](.github/agents/). Skills do projeto em [`.github/skills/*/SKILL.md`](.github/skills/) — mesmo formato usado pelos agentes, carregadas automaticamente quando relevantes.

## ⚠️ Diferença importante em relação ao Claude Code

O Copilot **não delega automaticamente entre agentes nomeados** (sem equivalente à ferramenta `Task`). Cada agente termina sua resposta dizendo qual agente rodar em seguida — **você precisa colar o resultado manualmente na próxima chamada**. Fluxo real:

```bash
copilot --agent ceo --prompt "seu pedido aqui"
# copie o plano que o ceo devolveu

copilot --agent cto --prompt "<cole o plano do ceo aqui>"
# copie a atribuição que o cto devolveu

copilot --agent senior-dev-backend --prompt "<cole a atribuição do cto aqui>"
# (ou senior-dev-webext / qa-lead, conforme o cto indicar)

copilot --agent cto --prompt "<cole o resultado do senior dev aqui, para o cto aprovar>"
```

Ou, interativo: digite `/agent` no Copilot CLI/Chat e escolha o agente na lista.

## Rota direta (pedidos triviais/pontuais)

Pedido pequeno, arquivo já identificado, 1 bug pontual → pule a diretoria e chame direto `senior-dev-backend` ou `senior-dev-webext`; feche com `qa-lead` só se quiser o gate formal.

## Regras de ouro

- Pedido vago ou feature nova → sempre comece por `ceo`.
- Bug/arquivo já localizado → pode começar direto no senior dev correspondente.
- Nunca pule o `qa-lead` antes de considerar algo pronto para commit.
- `idx.md` é o filtro de escopo primário do projeto — todo agente deve consultá-lo antes de buscar código livremente.
