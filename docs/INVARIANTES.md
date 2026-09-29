# INVARIANTES ARQUITETURAIS DO PJEPLUS

> Fatos críticos e restrições operacionais que NÃO podem ser alterados durante a migração para Playwright nativo.
> Criado na Fase F0 conforme especificado em `pw.md` (Seção 11).

---

### 1. Ordem de Inicialização do Playwright (`pw.py`)
- `pjeplay.iniciar()` DEVE ser chamado **antes** de qualquer import do projeto.
- *Nota:* hoje `pw.py` viola essa regra ao importar `Fix.monitoramento_progresso_unificado` (que importa Selenium no topo) antes de `iniciar()`. Na Fase F4, essa ordem deve ser estritamente corrigida.

### 2. SISBAJUD — Throttle Anti-Detecção Intocável
- Os `time.sleep` de throttle / anti-detecção em `SISB/` são deliberados e vitais para evitar bloqueio pelo sistema do tribunal.
- A ferramenta `migrar_sleeps.py` recusa tocá-los, e qualquer refatoração manual também é expressamente proibida de alterá-los.

### 3. Autenticação e Sessão
- O login no PJe e no SISBAJUD é **manual** e realizado via navegador visível.
- A gestão de cookies de sessão e o fluxo OAuth (`login.seam` → `meu-painel`) são intocáveis e não devem ser automatizados ou modificados.

### 4. Teto de Espera Observável
- `espera.assentar` é limitada pelo mesmo `N` em segundos do `time.sleep` que substitui.
- O tempo total de espera nunca pode exceder o teto original; nenhum fluxo pode ficar mais lento.

### 5. Resiliência a Falhas HTTP do PJe
- Falhas HTTP do PJe (como ARQ-516, 403, 500) são ambientais e decorrem de instabilidade da infraestrutura do tribunal.
- Tratamento: aplicar retry/backoff exponencial onde já existir; nunca alterar lógica de negócio tentando "consertar" resposta de servidor instável.

### 6. Canais de Log e Diagnóstico de Falhas
- `erro.md` é o canal exclusivo de falha detalhada com rastreamento completo de stack trace.
- O log de execução é o canal de falha resumido (conforme contrato só-falha definido em `pw.md` Seção 5).
