# CLAUDE.md — Regras de Orquestração DeepSeek + Claude Code

## STACK ATIVA
- Orquestrador: DeepSeek V4 Pro (esta sessão)
- Agentes: DeepSeek Flash (subagents — mais baratos)

***

## REGRAS DE DELEGAÇÃO — OBRIGATÓRIO

**DELEGAR via subagent `flash-worker` SEMPRE que a tarefa for:**
- Leitura ou exploração de arquivos (`Read`, `Glob`, `Grep`)
- Mapeamento de estrutura do projeto
- Checagem de código existente antes de planejar
- Verificação pós-implementação (lint, testes, review pontual)
- Qualquer tarefa isolada com resultado único e bem definido
- Busca de imports, dependências, configurações

**NÃO EXECUTAR diretamente como orquestrador:**
- Greps, Globs ou Reads para "entender o contexto" antes de agir
- Comparações ou validações pontuais de arquivos
- Verificações de saída de comandos simples

**PERMITIDO executar diretamente como orquestrador:**
- Síntese e planejamento (após receber resumos dos agentes)
- Decisões de arquitetura e estratégia
- Coordenação entre múltiplos agentes
- Escrita de código complexo após o plano estar definido

***

## FLUXO DE PLANEJAMENTO (OBRIGATÓRIO)

Antes de qualquer implementação, siga este fluxo:

1. **EXPLORAÇÃO** → Delegar ao `flash-worker`: mapeamento de arquivos relevantes
2. **ANÁLISE** → Delegar ao `flash-worker`: leitura e resumo dos arquivos identificados
3. **PLANO** → Orquestrador sintetiza o plano baseado nos resumos recebidos
4. **REVISÃO DO PLANO** → Delegar ao `flash-worker`: checar viabilidade técnica pontual
5. **IMPLEMENTAÇÃO** → Delegar tarefas isoladas ao `flash-worker`; orquestrador integra

**Checklist de delegação antes de agir:**
- [ ] Isso é leitura/exploração/verificação? → `flash-worker`
- [ ] O resultado é um resumo pontual? → `flash-worker`
- [ ] Isso requer síntese, estratégia ou decisão? → Orquestrador direto

***

## AGENTES DISPONÍVEIS

| Agente | Quando usar |
|--------|-------------|
| `flash-worker` | Leitura, grep, análise de arquivos, checagem, lint |

***

## COMPORTAMENTO PADRÃO

- Respostas de agentes devem ser **resumidas e objetivas** — sem contexto redundante
- Nunca expandir escopo de uma tarefa delegada
- Nunca pedir confirmação dentro de uma subtarefa
- Retornar apenas o resultado solicitado, sem explicações extras