# Reorganizar `Fix/`

## Problem Statement
How Might We: Como reorganizar a pasta `Fix/` para reduzir complexidade, facilitar manutenção e tornar os imports previsíveis sem quebrar consumidores existentes?

## Contexto breve (análise rápida)
- `Fix/` contém 76 arquivos Python e ~17.6k linhas de código.
- Há 4 arquivos com >600 linhas: `Fix/monitoramento_progresso_unificado.py`, `Fix/documents/search.py`, `Fix/selenium_base/element_interaction.py`, `Fix/selenium_base/smart_selection.py`.
- Muitos módulos já estão parcialmente agrupados (`selenium_base`, `drivers`, `navigation`, `session`, `documents`, `gigs`, `forms`).

## Requisitos do dono (resumo das respostas)
- Objetivo: reduzir complexidade, facilitar manutenção e melhorar previsibilidade de imports.
- Mantenedor: apenas eu (mudanças podem ser disruptivas, mas com documentação).
- Restrições: manter compatibilidade; arquivos mortos podem ficar como *stubs* de redirecionamento.
- Estratégia preferida: limpeza sem excesso de arquivos (híbrida aceitável).

## 5 Opções de reorganização (curtas)

1) Minimal (recomendo como fase 1)
- O que: criar um layout por domínio+tipo, mover arquivos para pacotes claros e deixar *stubs* nos caminhos antigos que importam dos novos módulos e emitem DeprecationWarning.
- Pros: baixo risco, mudanças incrementais, compatibilidade preservada.
- Contras: não reduz tamanho interno de arquivos grandes; exige criar vários __init__.py e stubs.
- Esforço: S (3-6 arquivos afetados por pacote; total ~M).

2) Domain-driven (mais ambicioso)
- O que: reorganizar por domínio (extraction, navigation, session, progress, docs, selenium, drivers, utils) e refatorar funções para módulos menores.
- Pros: arquitetura limpa, fácil de testar e evoluir.
- Contras: alteração de imports ampla, maior esforço e risco.
- Esforço: L (várias PRs, testes manuais/automáticos necessários).

3) Layered (responsabilidade)
- O que: separar em `infra/` (drivers, selenium_base), `app/` (fluxos, extracao), `lib/` (utils), mantendo `Fix/` como entrada que reexporta API pública.
- Pros: clara separação de dependências; facilita swaps de implementação.
- Contras: reorganização conceitual maior; possíveis duplicações temporárias.
- Esforço: M-L.

4) Size-driven (prático)
- O que: mover arquivos grandes (>300-400 linhas) para pacotes com responsabilidades claras e dividir os maiores (>600) em submódulos; deixar pequenos arquivos em `Fix/utils`.
- Pros: reduz arquivos inchados rapidamente.
- Contras: pode criar muitos pequenos módulos se não controlado.
- Esforço: M.

5) Safe-copy then switch (zero-break)
- O que: criar `Fix/v2/` com nova organização (duplicando código), validar imports/tests, depois substituir gradualmente e manter `Fix/legacy/` com stubs.
- Pros: mínimo risco para produção; fácil rollback.
- Contras: duplicação temporária, maior custo inicial.
- Esforço: L-XL.

## Recomendação (Escolha)
- Começar por **Opção 1 — Minimal (híbrido domínio+tipo)** como fase 1 para reduzir desalinhamento com mínimo risco. Depois, em fases controladas, aplicar Option 4 para dividir arquivos grandes (>600) e, quando houver tempo, migrar para Option 2 parcialmente (refatoração profunda).

**Racional:** você pediu limpeza sem excesso de arquivos e compatibilidade. A estratégia incremental preserva funcionamento, permite rollback e produz documentação de migração.

## Key Assumptions to Validate
- [ ] Não existem consumidores externos que importem caminhos internos de forma não óbvia (como imports dinâmicos). — Test: executar importa massiva (script de validação).
- [ ] As mudanças de import podem ser aplicadas via *stubs* sem perda de performance crítica.
- [ ] Arquivos grandes podem ser divididos sem reescrever lógica de negócio.

## MVP Scope (fase 1)
- Criar pacotes-alvo (ex.: `Fix/progress`, `Fix/extraction`, `Fix/selenium_base` (mantido), `Fix/documents`, `Fix/utils`).
- Mover um conjunto piloto de arquivos (ex.: `monitoramento_progresso_unificado.py` → `Fix/progress/monitoramento.py`; `progress.py` → `Fix/progress/__init__.py`).
- Criar *stubs* em caminhos antigos que reexportam das novas localizações e emitem DeprecationWarning.
- Executar validação: `py -m py_compile` em arquivos afetados e script de import-check para todo o repo.

## Not Doing (por agora)
- Refatoração profunda de lógica interna (funções/algoritmos) — isso fica para fases posteriores.
- Remover arquivos retroativamente sem validação completa.

## Open Questions
- Confirmar nomes finais de pacotes (`Fix/progress` vs `Fix/progress_unificado`).
- Deseja que eu gere e aplique os patches automaticamente (mover + stubs), ou apenas gerar o plano e os patches para revisão manual?

## Implementation Tasks (ordenadas)

### Task 1: Preparar layout (S)
**Descrição:** Criar diretórios alvo e __init__.py mínimos.
**Acceptance criteria:** diretórios criados; `py -c "import Fix.progress"` não falha (após stubs).

### Task 2: Migrar piloto (M)
**Descrição:** Mover `Fix/monitoramento_progresso_unificado.py` → `Fix/progress/monitoramento.py` + criar stub em `Fix/monitoramento_progresso_unificado.py` apontando para novo local.
**Acceptance criteria:** `py -c "import Fix.monitoramento_progresso_unificado"` continua funcionando; `py -m py_compile` sem erros.

### Task 3: Criar script de validação (S)
**Descrição:** Script que tenta importar todos os módulos do repo e lista falhas.
**Acceptance criteria:** script executa e reporta 0 novas falhas após migração piloto.

### Task 4: Ampliar migração por pacotes (M x N)
**Descrição:** Repetir para `documents/search.py`, `selenium_base/element_interaction.py` (mover para `Fix/selenium_base/element_interaction.py` mantendo path se preferir dividir internamente), e `smart_selection.py`.
**Acceptance criteria:** import-check sem falhas; testes locais básicos funcionam.

### Task 5: Split dos arquivos >600 (L)
**Descrição:** Para cada arquivo >600 linhas, criar subtarefas para dividir por responsabilidade com testes/validação.
**Acceptance criteria:** cada split tem teste de import e `py -m py_compile` passa.

### Task 6: Documentação & Notas de migração (XS)
**Descrição:** Atualizar README e adicionar `docs/migration/fix-reorg.md` com lista de renames e stubs.
**Acceptance criteria:** README contém instruções de como atualizar imports e localizar stubs.

## Verificação rápida (comandos)
```bash
# Validar sintaxe geral
py -m py_compile Fix/**/*.py
# Checar imports (exemplo de script rápido)
py tools/check_imports.py
```

## Riscos e Mitigações
- Risco: imports dinâmicos quebram (Med) — Mitigação: rodar script de import-check e validar cenários manuais críticos.
- Risco: mudanças causam regressão em produção (High) — Mitigação: aplicar em pequena fase piloto, monitorar logs e ter rollback com stubs.

## Próximo passo proposto
- Se concordar: eu gero os patches para a Fase 1 (criar pacotes + mover `monitoramento_progresso_unificado.py` + stubs) e executo um `py -m py_compile` + import-check. Diga se quer que eu aplique os patches automaticamente ou apenas gere para revisão.


## Consolidação de arquivos pequenos — redução agressiva do número de módulos

### Objetivo
Consolidar módulos pequenos do `Fix/` em módulos por domínio para reduzir o número total de arquivos. Meta inicial sugerida: reduzir de 76 para ~12–18 arquivos/pacotes (ajustável conforme revisão humana).

### Diretrizes e regras
- Alvo primário: arquivos com menos de 600 linhas são candidatos; priorizar arquivos com <300 linhas para ganho rápido.
- Agrupar por domínio/diretório e por padrão de nome (`utils_*`, `variaveis_*`, `extracao_*`, etc.). Exemplo de grupos: `utils`, `variaveis`, `extracao`, `progress`, `documents`, `session`.
- Evitar criar arquivos monolíticos enormemente maiores que 1.200 linhas; se necessário, dividir em submódulos (ex.: `Fix/utils/io.py`, `Fix/utils/format.py`).
- Preservar API pública: reexportar nomes públicos (`__all__`) e fornecer *stubs* de compatibilidade antes de remover originais.
- Backup obrigatório: mover as versões originais para `Fix/legacy/` antes de qualquer remoção.
- Scripts e módulos com side-effects top-level devem ser analisados isoladamente — converter em funções iniciais ou manter em `Fix/scripts/`.

### Processo prático (por lotes)
1. Gerar mapa de candidaturas (script): lista de arquivos <600 e sugestão de grupo automático.
2. Revisão humana do mapa e ajuste manual dos grupos propostos.
3. Piloto: consolidar 3 grupos (ex.: `utils`, `progress`, `extracao`) seguindo:
	- Criar `Fix/<group>.py` (ou pacote `Fix/<group>/`) contendo o código consolidado.
	- Atualizar imports no repositório com um script (dry-run primeiro).
	- Mover originais para `Fix/legacy/` como backup (não apagar ainda).
	- Rodar `py -m py_compile` e `tools/check_imports.py`.
4. Se piloto OK: repetir por lotes até concluir a consolidação total.
5. Documentar mapeamento final e, após período de confiança, remover `Fix/legacy/`.

### Ferramentas/skripts sugeridos
- `tools/propose_fix_merges.py` — gera JSON/CSV com grupos sugeridos e métricas (linhas, dependências).
- `tools/apply_merge_dryrun.py` — simula atualização de imports e reporta conflitos sem alterar arquivos.
- `tools/perform_merge.py` — aplica merges (cria módulos consolidados, atualiza imports, move originais para `Fix/legacy/`).
- `tools/check_imports.py` — valida importabilidade do repo (usar após cada lote).

### Critérios de aceitação (por lote)
- [ ] `py -m py_compile` passa em todo o repo.
- [ ] `tools/check_imports.py` reporta 0 erros.
- [ ] Execução de 2–3 fluxos manuais críticos (smoke) não falha.
- [ ] `Fix/legacy/` contém os arquivos originais compactados (backup).

### Riscos e mitigações específicas
- Conflitos de nomes públicos: script detecta duplicatas e exige revisão humana antes do merge.
- Top-level side-effects: detectar e isolar automaticamente; executar revisão manual para cada caso.
- Regressão funcional: piloto pequeno e checkpoints frequentes; manter backups e stubs para rollback.
- Performance de import: medir tempo de import dos módulos críticos antes/depois.

### Entrega proposta (passos imediatos)
- Se aprovar: eu gero os scripts `tools/propose_fix_merges.py` e `tools/apply_merge_dryrun.py` e executo um dry-run piloto para os 3 grupos sugeridos. Depois trago o relatório com o mapeamento proposto e diffs para revisão.

---
Gerado automaticamente em resposta à análise da pasta `Fix/` (76 arquivos, ~17.6k linhas).