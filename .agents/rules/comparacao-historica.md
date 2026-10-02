# PJePlus — Comparação histórica para diagnóstico

> **Aplicável a Copilot e Antigravity/Gemini. Atualizado: 2026-10-01.**

## Branch e fonte

- Trabalhe somente em `main`; confirme com `git branch --show-current`.
- Não consulte, compare ou busque código em branches anteriores.
- Em caso de dúvida, falha ou regressão, compare o código atual com o estado imediatamente anterior ao commit `968047a`:

```bash
git show 968047a^:CAMINHO/DO/ARQUIVO
```

O pai de `968047a` (`4f0a3f5`) representa essa fonte principal pré-limpeza. Consulte somente o trecho necessário.

## Uso da comparação

- A comparação serve apenas para entender diferenças e informar o diagnóstico. **Não existe modo de restauração automática:** não copie nem reaplique código só porque existia no snapshot.
- A correção deve atender ao pedido atual e seguir a arquitetura Playwright e os padrões vigentes em `idx.md`.
- Se o objeto Git ou o arquivo não estiver disponível, reporte exatamente a lacuna e peça acesso. Não procure outra branch, tag ou fonte histórica como substituta.
- `gigs-plugin.js`, `LEGADO.md`, `legado.md`, `ref/` e `ORIGINAIS/` só podem ser consultados quando o prompt mencionar expressamente aquela fonte.
