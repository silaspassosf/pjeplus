# TRINDEX — Mapa da Triagem Trabalhista

## Objetivo

Este arquivo documenta a nova organização da triagem de petição inicial trabalhista após a quebra do antigo `tr.py` monolítico em módulos temáticos menores.

Ele existe para responder rapidamente:

- onde fica cada regra;
- onde entra cada ajuste futuro;
- quais módulos são puros e quais dependem de API/PJe;
- qual arquivo deve ser alterado sem espalhar lógica em lugares errados.

---

## Visão Geral

### Contrato público mantido

O ponto de entrada funcional continua sendo:

```python
from tr import triagem_peticao
```

O arquivo `tr.py` passa a ser apenas uma fachada fina, reexportando `triagem_peticao` do pacote `triagem`.

---

## Estrutura proposta

```text
tr.py
triagem/
├── __init__.py
├── constants.py
├── utils.py
├── preprocess.py
├── coleta.py
├── regras.py
└── service.py
```

---

## Responsabilidade por arquivo

### `tr.py`
Fachada de compatibilidade.

**Responsabilidade:**
- manter compatibilidade com imports legados;
- evitar mexer em módulos consumidores antigos;
- centralizar apenas o reexport público.

**Deve conter apenas:**
- import do serviço principal;
- `__all__ = ["triagem_peticao"]`.

**Não deve conter:**
- regra de negócio;
- parsing;
- chamada de API;
- regex de domínio.

---

### `triagem/__init__.py`
Export público do pacote.

**Responsabilidade:**
- expor `triagem_peticao` como API principal do pacote.

**Não deve conter:**
- regra de negócio;
- helpers;
- imports pesados desnecessários além do ponto de entrada.

---

### `triagem/constants.py`
Base estática e semântica comum.

**Responsabilidade:**
- constantes monetárias e de rito;
- intervalos territoriais de CEP;
- regexes base reutilizáveis;
- listas de termos de classificação;
- rótulos de saída;
- função de normalização textual (`norm`).

**Mover para cá tudo que for:**
- literal estável;
- regex compartilhada;
- lista de palavras-chave usada em mais de um módulo;
- configuração sem dependência de driver, API ou texto do processo específico.

**Não deve conter:**
- acesso à API;
- montagem de saída final;
- decisões de fluxo.

---

### `triagem/utils.py`
Helpers puros e reutilizáveis.

**Responsabilidade:**
- formatação de saída;
- parsing de prefixo/status das linhas B1–B14;
- helpers de endereço;
- contexto de página;
- classificação contextual de CEP;
- extrações genéricas reutilizadas por mais de uma regra.

**Regra prática:**
se a função:
1. recebe texto/dict/lista,
2. devolve valor simples,
3. não fala com API,
4. não sabe qual etapa do fluxo a chamou,

ela tende a pertencer a `utils.py`.

**Não deve conter:**
- regra jurídica final;
- acesso à API PJe;
- orquestração principal.

---

### `triagem/preprocess.py`
Limpeza segura do texto bruto.

**Responsabilidade:**
- remover artefatos determinísticos do PJe/OCR;
- aprender fingerprint de cabeçalho do escritório;
- remover cabeçalho repetido por página;
- compactar excesso de linhas em branco;
- entregar texto limpo para as regras.

**Entrada típica:**
- texto bruto extraído do PDF.

**Saída típica:**
- texto limpo, preservando o corpo jurídico.

**Não deve conter:**
- decisão de rito;
- leitura de timeline;
- análise de reclamadas;
- montagem da triagem final.

---

### `triagem/coleta.py`
Infraestrutura de aquisição dos dados do processo.

**Responsabilidade:**
- montar sessão autenticada via `session_from_driver`;
- instanciar `PjeApiClient`;
- extrair `id_processo` da URL;
- buscar timeline;
- localizar petição inicial;
- extrair PDF nativo e OCR fallback;
- localizar certidão de distribuição;
- coletar anexos essenciais;
- enriquecer `capa_dados` com endpoints de partes, endereço, domicílio eletrônico e processo.

**Este é o módulo de infraestrutura.**

**Pode conter:**
- chamadas HTTP/API;
- tratamento controlado de 401 com reautenticação única;
- timeout de timeline;
- logs técnicos da coleta.

**Não deve conter:**
- regras B1–B14;
- formatação final do relatório;
- normalizações cosméticas de saída.

---

### `triagem/regras.py`
Núcleo das regras de triagem.

**Responsabilidade:**
- conter as checagens B1–B14;
- operar sobre `texto`, `anexos`, `capa_dados` e `associados_sistema`;
- gerar linhas padronizadas por bloco;
- concentrar a regra jurídica/técnica da triagem.

**Cada função aqui deve responder idealmente a uma pergunta objetiva**, por exemplo:
- há procuração e documento de identidade?
- o CEP aponta possível incompetência territorial?
- há PJDP no polo passivo?
- há tutela provisória?
- o rito é compatível com valor/partes?
- existe menção a art. 611-B?

**Deve conter:**
- lógica decisória;
- regexes locais muito específicas de uma única regra;
- retorno em formato textual padronizado por bloco.

**Não deve conter:**
- API PJe;
- OCR;
- compat layer de import;
- limpeza estrutural de cabeçalho/rodapé.

---

### `triagem/service.py`
Orquestração única da triagem.

**Responsabilidade:**
- chamar `coletar_textos_processo`;
- acionar regras na ordem oficial;
- consolidar resultados;
- aplicar formatação final;
- limitar tamanho de retorno;
- manter o contrato `triagem_peticao(driver) -> str`.

**Este é o módulo que conhece o fluxo completo.**

**Deve conter:**
- sequência das etapas;
- tratamento de falha macro;
- fallback de retorno quando a coleta falhar;
- composição final das linhas.

**Não deve conter:**
- implementação longa de cada regra;
- regexes volumosas de domínio;
- detalhes internos de OCR/PDF além da chamada ao módulo correto.

---

## Fluxo de execução

```text
driver autenticado
   ↓
tr.triagem_peticao(driver)
   ↓
triagem.service.triagem_peticao(driver)
   ↓
triagem.coleta.coletar_textos_processo(driver)
   ↓
texto/anexos/capa_dados/associados_sistema
   ↓
triagem.regras.checagens B1–B14
   ↓
triagem.utils.formatacao final
   ↓
string final de triagem
```

---

## Mapa por tema

### Compatibilidade
- `tr.py`
- `triagem/__init__.py`

### Constantes e vocabulário
- `triagem/constants.py`

### Helpers compartilhados
- `triagem/utils.py`

### Limpeza de texto
- `triagem/preprocess.py`

### API, timeline, PDF, OCR, anexos
- `triagem/coleta.py`

### Regras B1–B14
- `triagem/regras.py`

### Orquestração final
- `triagem/service.py`

---

## Onde alterar cada tipo de demanda

### 1. Mudou faixa de salário mínimo, alçada ou limite de sumaríssimo
Alterar em:
- `triagem/constants.py`

---

### 2. Mudou regex base de CNPJ/CPF/artefato PJe
Alterar em:
- `triagem/constants.py`

Se a regex for exclusiva de uma regra isolada e não reutilizada:
- `triagem/regras.py`

---

### 3. Cabeçalho novo de escritório está passando para o corpo
Alterar em:
- `triagem/preprocess.py`

Pontos prováveis:
- fingerprint de cabeçalho;
- critérios de linha de escritório;
- compactação pós-limpeza.

---

### 4. API mudou endpoint ou comportamento de timeline/partes
Alterar em:
- `triagem/coleta.py`

---

### 5. Falha em OCR ou heurística de extração de PDF
Alterar em:
- `triagem/coleta.py`

---

### 6. Ajuste de regra B1–B14
Alterar em:
- `triagem/regras.py`

**Exemplos:**
- tutela provisória;
- segredo de justiça;
- rito;
- competência territorial;
- litispendência;
- responsabilidade subsidiária/solidária.

---

### 7. Mudou apenas o texto final exibido ao usuário
Primeiro verificar:
- `triagem/utils.py` para formatação padronizada;
- `triagem/regras.py` se a frase estiver embutida na própria regra;
- `triagem/service.py` se a mudança for na composição final.

---

### 8. Mudou a ordem dos blocos de triagem
Alterar em:
- `triagem/service.py`

---

## Regras de manutenção

### 1. Não recolapsar o pacote em arquivo único
Se uma mudança nova surgir, encaixar no módulo temático correto em vez de voltar a colocar tudo em `tr.py`.

### 2. Evitar duplicação de regra
Se uma checagem Bx já existe em `triagem/regras.py`, expandir a função existente em vez de criar uma segunda versão.

### 3. Helpers puros não devem virar regra
Se o código apenas formata, normaliza, classifica ou extrai contexto sem decidir resultado jurídico, ele deve ficar em `utils.py`.

### 4. Infraestrutura não decide regra
`coleta.py` pode enriquecer dados, mas não deve assumir conclusões finais de triagem.

### 5. `service.py` só orquestra
Quando `service.py` começar a crescer demais, a correção é extrair para `regras.py` ou `utils.py`, não duplicar lógica.

### 6. Preservar contrato externo
Sempre manter funcional:
```python
from tr import triagem_peticao
```

---

## Convenções recomendadas

### Prefixos de função
- `checar_*` para regra de negócio;
- `extrair_*` para parsing/aquisição;
- `formatar_*` para saída;
- `remover_*` ou `strip_*` para limpeza;
- `parsear_*` para transformação estruturada de texto em dict.

### Tipos de retorno
- `str` para bloco único;
- `list[str]` para bloco com múltiplas linhas;
- `dict` para dados intermediários estruturados;
- nunca misturar retorno estrutural com impressão final se a função ainda for reutilizável.

### Logs
- logs técnicos de coleta em `coleta.py`;
- logs de limpeza somente quando necessários em `preprocess.py`;
- evitar verbosidade em `regras.py`, salvo gatilho crítico de depuração.

---

## Checklist de alteração segura

Antes de editar qualquer módulo da triagem, validar:

- o ajuste é de constante? → `constants.py`
- o ajuste é utilitário puro? → `utils.py`
- o ajuste é limpeza de texto? → `preprocess.py`
- o ajuste fala com API/PDF/OCR? → `coleta.py`
- o ajuste é decisão de triagem B1–B14? → `regras.py`
- o ajuste é ordem/encadeamento/retorno final? → `service.py`
- o ajuste precisa manter compatibilidade legada? → `tr.py`

---

## Exemplo de leitura rápida

### “Quero corrigir a lógica de tutela provisória”
Arquivo alvo:
- `triagem/regras.py`

### “Quero mudar a forma como o cabeçalho do escritório é removido”
Arquivo alvo:
- `triagem/preprocess.py`

### “Quero ajustar o texto final de saída de B2_CEP”
Arquivo alvo provável:
- `triagem/utils.py`
- ou `triagem/regras.py`, conforme o texto esteja sendo montado lá.

### “Quero trocar a origem do valor da causa”
Arquivo alvo:
- `triagem/coleta.py`

### “Quero manter o import legado funcionando”
Arquivo alvo:
- `tr.py`

---

## Observação final

Se um módulo ultrapassar novamente o limite operacional de manutenção, a próxima quebra deve seguir o mesmo critério desta refatoração:

- separar por pertinência temática;
- preservar contrato externo;
- evitar refatoração horizontal ampla;
- manter coleta, regra e formatação desacopladas.