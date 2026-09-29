# Manual Técnico: Catálogo de Seletores, Observabilidade e Modelos
## Especificação dos Componentes Centrais Introduzidos

---

## 1. Catálogo Central de Seletores (`Fix/seletores_catalogo.py`)

### 1.1. Motivação e Arquitetura
Historicamente, cada módulo de negócio (Mandado, PEC, P2B, Atos) definia suas próprias listas locais de seletores CSS/XPath, iterando sobre eles em loops imperativos com blocos `try/except` individuais. Se o primeiro seletor estivesse obsoleto em determinada versão do PJe, a automação acumulava até 18 segundos de espera em cada ação por processo.

O módulo [Fix/seletores_catalogo.py](file:///d:/PjePlus/Fix/seletores_catalogo.py) resolve esse problema através de:
1. **Contrato Semântico:** O chamador não especifica seletores CSS/XPath, apenas o identificador da ação semântica desejada (ex: `mandado_checkbox_prazo_30`).
2. **Memória de Vencedores (Cache em Sessão):** O seletor que funcionou é promovido a **vencedor**, sendo executado prioritariamente nas próximas requisições.
3. **Parada Imediata:** No primeiro sucesso, a cadeia de avaliação é interrompida imediatamente.
4. **Invalidação Dinâmica Segura:** Caso o vencedor falhe (devido a mudança de aba, renderização assíncrona ou mutação do DOM), ele é imediatamente descartado e os fallbacks restantes são executados no mesmo ciclo sem falha perceptível para o usuário.

### 1.2. Estrutura de Dados `SeletorAcao`
```python
@dataclass
class SeletorAcao:
    seletor: str
    tipo: str = "css"  # 'css' ou 'xpath'
    timeout: float = 3.0
    descricao: str = ""
```

### 1.3. Ações Semânticas Cadastradas

O catálogo central inicializou com 16 ações semânticas homologadas:

| Ação Semântica | Contexto | Seletor Principal | Fallbacks Homologados |
|---|---|---|---|
| `mandado_menu_flutuante` | `mandado` | `#botao-menu` | Nenhum (ID fixo rápido) |
| `mandado_btn_expedientes` | `mandado` | `button[aria-label="Expedientes"]` | Nenhum |
| `mandado_checkbox_prazo_30` | `mandado` | `//tr[contains(., '30')]//mat-checkbox//input[@type='checkbox']` | 1. `//tr[contains(., '30')]//mat-checkbox`<br>2. `mat-checkbox input[type="checkbox"]` |
| `mandado_btn_fechar_expedientes` | `mandado` | `button[aria-label="Fechar Expedientes"]` | `//button[contains(., 'Fechar Expedientes')]` |
| `mandado_confirmar_sim` | `mandado` | `//mat-dialog-container//button[normalize-space(.)='Sim']` | `//div[contains(@class,'cdk-overlay-pane')]//button[normalize-space(.)='Sim']` |
| `comunicacao_btn_minutar` | `comunicacao` | `pje-botoes-transicao button[aria-label="Minutar"]` | 1. `button[aria-label="Minutar"]`<br>2. `button[mattooltip*="Minutar"]` |
| `comunicacao_select_tipo_expediente`| `comunicacao` | `mat-select[placeholder="Tipo de Expediente"]` | 1. `mat-select[formcontrolname="tipoExpediente"]`<br>2. `pje-tipo-expediente mat-select` |
| `comunicacao_input_prazo` | `comunicacao` | `input[aria-label="Prazo em dias úteis"]` | 1. `input[placeholder*="dias úteis"]`<br>2. `mat-form-field input[type="number"]` |
| `comunicacao_checkbox_sigilo` | `comunicacao` | `input[name="sigiloso"]` | `mat-checkbox[formcontrolname="sigiloso"]` |
| `comunicacao_btn_confeccionar` | `comunicacao` | `button[aria-label="Confeccionar ato agrupado"]` | `button[mattooltip="Confeccionar ato agrupado"]` |
| `comunicacao_btn_salvar_final` | `comunicacao` | `button[aria-label="Salvar"], button[aria-label="Gravar"]` | 1. `//button[contains(., 'Salvar')]`<br>2. `button.btn-primary` |
| `tarefa_btn_abrir` | `geral` | `button[mattooltip="Abre a tarefa do processo"]` | 1. `button[mattooltip*='tarefa']`<br>2. `button[aria-label*='tarefa']` |
| `pec_carta_btn_anexar` | `pec_carta` | `button[aria-label="Anexar documentos"]` | `//button[contains(., 'Anexar')]` |
| `pec_carta_input_tipo_anexo` | `pec_carta` | `input[data-placeholder="Tipo de Documento"]` | `mat-select[formcontrolname="tipoDocumento"]` |
| `p2b_iniciar_exec_btn` | `geral` | `button[aria-label="Iniciar execução"]` | `//button[contains(., 'Iniciar execução')]` |
| `geral_fechar_modal` | `geral` | `button[aria-label="Fechar"]` | `button.mat-dialog-close, button.close` |

---

## 2. Observabilidade Estruturada e Sanitização (`Fix/diagnostico_runtime.py`)

### 2.1. Sanitização de Dados Sensíveis
Para evitar que informações protegidas por sigilo ou dados pessoais vazem em logs de exceção ou relatórios de erros compartilhados, a função `sanitizar_dados_sensiveis` aplica expressões regulares para mascarar dados sensíveis:

```python
def sanitizar_dados_sensiveis(texto: str) -> str:
    """Mascara CPFs, CNPJs e Bearer tokens em mensagens de log."""
    # CPF: 123.456.789-00 -> ***.456.789-**
    texto = re.sub(r'\b\d{3}\.(\d{3}\.\d{3}-)\d{2}\b', r'***.\1**', texto)
    # CNPJ: 12.345.678/0001-90 -> **.345.678/0001-**
    texto = re.sub(r'\b\d{2}\.(\d{3}\.\d{3}/\d{4}-)\d{2}\b', r'**.\1**', texto)
    # Tokens de autenticação: Bearer eyJhb... -> Bearer eyJh***[REDACTED]
    texto = re.sub(r'(Bearer\s+[A-Za-z0-9_\-\.]{5})[A-Za-z0-9_\-\.]+', r'\1***[REDACTED]', texto)
    return texto
```

### 2.2. Formato Canônico de Erro Estruturado
A função `log_erro_estruturado` padroniza o registro de incidentes operacionais, gerando blocos estruturados que facilitam o diagnóstico sem poluir o console com tracebacks repetitivos:

```python
def log_erro_estruturado(
    fluxo: str,
    modulo: str,
    funcao: str,
    excecao: Exception,
    processo: str = "",
    etapa: str = "",
    acao: str = "",
    seletor: str = "",
    codigo_erro: str = "",
    retry: bool = False,
    logger_instance: Optional[logging.Logger] = None,
) -> None:
    ...
```

**Exemplo de Saída Estruturada Gerada:**
```
ERRO [MANDADO-INTIMACAO-01]
fluxo=Mandado
modulo=Mandado.entrada_api
funcao=fechar_intimacao
processo=1000123-45.2024.5.02.0001
etapa=fechamento_expedientes
acao=mandado_checkbox_prazo_30
seletor=//tr[contains(., '30')]//mat-checkbox//input[@type='checkbox']
excecao=TimeoutException
causa=Elemento não encontrado no tempo limite de 3.0s
retry=False
```

---

## 3. Inserção Segura de Modelos no CKEditor (`atos/judicial_modelos.py`)

### 3.1. Problema de Corrida no Editor Angular Material
Nas versões anteriores, o preenchimento de minutas judiciais no CKEditor sofria com condições de corrida: se o script tentasse enviar o texto imediatamente antes da inicialização completa dos plugins internos do CKEditor, o conteúdo era ignorado ou truncado pelo Angular.

### 3.2. Solução com Guarda de Baseline Anti-Corrida
A função `inserir_modelo_no_editor` consolidada em [atos/judicial_modelos.py](file:///d:/PjePlus/atos/judicial_modelos.py) opera com uma estratégia em três etapas:
1. **Medição de Baseline:** Detecta se a instância ativa é CKEditor 4 ou CKEditor 5 e calcula a contagem de caracteres inicial.
2. **Injeção Nativa de Dados:** Aplica o conteúdo via API interna do CKEditor (`editor.setData(...)` no CK4 ou `editor.data.set(...)` no CK5).
3. **Guarda de Assentamento:** Utiliza `espera.ate_verdadeiro` para verificar se o comprimento do texto no DOM aumentou substancialmente e se manteve estável por no mínimo 300ms, assegurando que eventos assíncronos não sobrescrevam a minuta.

```python
def inserir_modelo_no_editor(driver, texto_modelo: str, timeout: float = 8.0) -> bool:
    """Insere modelo no CKEditor (4 ou 5) com medicao de baseline e guarda anti-corrida."""
    ...
```

---
*Fim do Manual Técnico dos Componentes.*
