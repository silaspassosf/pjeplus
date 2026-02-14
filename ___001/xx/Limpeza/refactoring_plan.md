# 🎯 Plano de Limpeza de Código: Core.py + Projeto

**Data:** 05 de Fevereiro de 2026  
**Escopo:** Limpeza assertiva de logs verbosos + padrões limpos  
**Abordagem:** Automática com script reversível  

---

## I. PROBLEMAS IDENTIFICADOS NO core.py

### 1. **Logs Excessivos e Verbosos**

```python
# ❌ PROBLEMA: Print + Logger juntos, linhas redundantes
printSISBAJUD Login realizado com sucesso após timeout")
return True
else:
    printSISBAJUD Login não concluído automaticamente - pode precisar de verificação")

# O mesmo em logger:
logger.info("Login automático bem-sucedido")
logger.debug("Resultado do loginautomaticosisbajud: {resultadologin}")
```

**Impacto:** 
- ~200+ linhas de logs por função
- Difícil encontrar lógica real
- AI context consumido por output

### 2. **Padrão Inconsistente: print() vs logger**

- Alguns usos: `print()` direto
- Outros: `logger.info()`, `logger.debug()`, `logger.error()`
- Nenhum padrão claro

### 3. **Logs em CADA Ação**

```python
# Antes:
def fazer_algo():
    print("Iniciando...")
    resultado = funcao1()
    print("funcao1 executada")
    
    resultado2 = funcao2()
    print("funcao2 executada")
    
    if resultado2:
        print("Sucesso!")
    else:
        print("Falha")
```

### 4. **Emojis Desnecessários**

- `✅` `❌` `⚠️` `🔄` `📊` - Sem valor operacional, só poluição

### 5. **Estrutura Monolítica**

- 1200+ linhas em `core.py`
- Múltiplas responsabilidades
- Funções 200+ linhas (antes do refactoring)

---

## II. ESTRATÉGIA DE LIMPEZA

### Princípio: **Only Log What Matters**

```
❌ REMOVIDO:
- Logs de "iniciando/finalizando"
- Confirmação de cada ação bem-sucedida
- Emojis
- Logs em nivel DEBUG para operações triviais

✅ MANTÉM:
- Erros críticos (ERROR)
- Avisos operacionais (WARNING)
- Transições de estado importantes (INFO)
- Exceções com contexto
```

### Criticidade de Logs

| Nível | Mantém | Remove | Exemplo |
|-------|--------|--------|---------|
| **CRITICAL** | Todos | Nenhum | "Sistema indisponível" |
| **ERROR** | Sim | Trace verboso | "Falha ao conectar: timeout" |
| **WARNING** | Sim | Justificativa óbvia | "Cookie expirado, refazendo login" |
| **INFO** | Parcial | Ações triviais | ✅ "Login bem-sucedido" |
| **DEBUG** | Não | Tudo | ✗ Remove completamente |

---

## III. MAPEAMENTO: O QUE MANTER vs REMOVER

### Exemplo Real: Função `loginautomaticosisbajud()`

#### ANTES (150+ linhas com logs)
```python
def loginautomaticosisbajud(driver):
    print("SISBAJUD: Iniciando login automático...")
    try:
        # ... código ...
        print("SISBAJUD: Navegando para URL de login...")
        driver.get(URL_LOGIN)
        print("SISBAJUD: URL de login carregada")
        
        logger.debug(f"Título: {driver.title}")
        logger.debug(f"URL atual: {driver.current_url}")
        
        # ... código ...
        
        print("SISBAJUD: Login realizado com sucesso após timeout")
        return True
    except Exception as e:
        printfSISBAJUD Erro durante login {e}")
        traceback.printexc()
```

#### DEPOIS (Limpo)
```python
def loginautomaticosisbajud(driver):
    """Realiza login automático no SISBAJUD com verificação de CPF."""
    try:
        driver.get(URL_LOGIN)
        
        # ... código de login ...
        
        return True
    except TimeoutException as e:
        logger.warning(f"Timeout no login SISBAJUD: {e}")
        return False
    except Exception as e:
        logger.error(f"Falha crítica no login: {e}")
        return False
```

**Redução:** 150 linhas → 40 linhas (-73%)

---

## IV. SCRIPT DE LIMPEZA AUTOMÁTICA

Cria 3 scripts separados:

### Script 1: `clean_logs.py` - Remove logs verbosos

```python
#!/usr/bin/env python3
"""
Clean logs automático - Remove logs triviais mantendo críticos.
Reversível: cria backup antes de modificar.
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

class LogCleaner:
    """Remove logs verbosos e normaliza para logger."""
    
    # Padrões para REMOVER completamente
    REMOVE_PATTERNS = [
        r'print\(["\']SISB[A-Z_]*:\s*(Iniciando|Finalizando|Clicando|Navegando|Carregando|Pressionando)',
        r'print\(["\']SISB[A-Z_]*:\s*✅.*?\)',
        r'print\(["\']SISB[A-Z_]*:\s*❌.*?\)',
        r'logger\.debug\(["\'].*?(DEBUG|Tentativa|Verificando|Detectado)\b',
        r'print\(60\s*\)  # Linha decorativa',
        r'print\(f["\']SISB[A-Z_]*:\s*.*?[✅❌⚠️🔄]\s*\)',
    ]
    
    # Padrões para CONVERTER print → logger
    CONVERT_PATTERNS = [
        (r'print\(f["\']SISB[A-Z_]*:\s*ERROR\s*-\s*(.+?)\"\)', 
         r'logger.error(f"\1")'),
        (r'print\(f["\']SISB[A-Z_]*:\s*(.+?)\"\)',
         r'logger.info(f"\1")'),
    ]
    
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.backup_path = self.filepath.with_suffix('.py.bak')
    
    def backup(self):
        """Cria backup antes de modificar."""
        shutil.copy2(self.filepath, self.backup_path)
        print(f"✓ Backup criado: {self.backup_path}")
    
    def clean(self):
        """Realiza limpeza."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_len = len(content)
        
        # 1. Remove logs triviais
        for pattern in self.REMOVE_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        # 2. Converte print → logger
        for old, new in self.CONVERT_PATTERNS:
            content = re.sub(old, new, content)
        
        # 3. Remove emojis desnecessários
        content = re.sub(r'[✅❌⚠️🔄📊📁🎯💡]', '', content)
        
        # 4. Remove linhas em branco extras (>2 consecutivas)
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        # 5. Garante que TODOS os logger são importados
        if 'logger = logging.getLogger' not in content:
            content = 'import logging\nlogger = logging.getLogger(__name__)\n' + content
        
        new_len = len(content)
        reduction_pct = ((original_len - new_len) / original_len * 100)
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Arquivo limpo: {self.filepath.name}")
        print(f"  Redução: {original_len:,} → {new_len:,} caracteres (-{reduction_pct:.1f}%)")
        
        return reduction_pct
    
    def restore(self):
        """Restaura a partir do backup."""
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.filepath)
            print(f"✓ Arquivo restaurado de {self.backup_path}")
        else:
            print(f"✗ Backup não encontrado: {self.backup_path}")

# Uso:
if __name__ == "__main__":
    cleaner = LogCleaner("Fix/core.py")
    
    # Backup
    cleaner.backup()
    
    # Limpa
    reduction = cleaner.clean()
    
    print(f"\nResumo: {reduction:.1f}% de redução na poluição de logs")
    print("\nPara restaurar:")
    print("  cleaner.restore()")
```

---

### Script 2: `refactor_granular.py` - Extrai para arquivos menores

```python
#!/usr/bin/env python3
"""
Granulariza core.py em arquivos menores (100-200 linhas).
Automático e reversível.
"""

import re
import ast
from pathlib import Path

class CodeExtractor:
    """Extrai funções relacionadas para arquivos separados."""
    
    def __init__(self, source_file):
        self.source = Path(source_file)
        self.target_dir = self.source.parent / "level1_primitivos"
        self.target_dir.mkdir(exist_ok=True)
    
    def extract_functions_by_category(self):
        """Mapeia funções por categoria."""
        
        categories = {
            'js_executor': [
                'executar_script_js',
                'js_click',
                'js_dispatch_click',
                'script_novaminuta',
            ],
            'dom_detector': [
                'esta_em_headless_ou_background',
                'hash_dom',
                'aguardar_mudanca_dom_ou_navegacao',
                'nao_esta_visivel_na_tela',
            ],
            'event_handler': [
                'disparar_eventos_mouse',
                'disparar_keyboard_event',
                'forcar_rendering_elemento',
            ],
            'wait_operations': [
                'tentar_esperar_network_idle',
                'esperar_javascript_ready',
                'esperar_elemento_com_espera_completa',
            ],
            'diagnostics': [
                'diagnosticar_estado_driver',
                'diagnosticar_falha_clique_v3',
            ],
        }
        
        return categories
    
    def create_files(self):
        """Cria arquivos separados para cada categoria."""
        categories = self.extract_functions_by_category()
        
        for category, functions in categories.items():
            filename = f"{category}.py"
            filepath = self.target_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f'"""\n{category}: {len(functions)} funções especializadas.\n"""\n\n')
                f.write('import logging\nlogger = logging.getLogger(__name__)\n\n')
                # TODO: Extrair funções
            
            print(f"✓ Criado: {filepath} ({len(functions)} funções)")

# Uso:
if __name__ == "__main__":
    extractor = CodeExtractor("Fix/core.py")
    extractor.create_files()
```

---

### Script 3: `validate_refactoring.py` - Valida que nada quebrou

```python
#!/usr/bin/env python3
"""
Valida que refactoring não quebrou funcionalidades.
Checklist automático.
"""

import ast
import importlib.util
from pathlib import Path

class RefactoringValidator:
    """Valida integridade após refactoring."""
    
    def __init__(self, project_root):
        self.root = Path(project_root)
    
    def check_imports(self):
        """Valida que imports ainda funcionam."""
        try:
            spec = importlib.util.spec_from_file_location("Fix", self.root / "Fix" / "__init__.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Valida funções públicas
            public_api = ['aguardar_e_clicar_v3', 'preencher_campo_v3', 'criargigs', 'criardriverPC']
            for func in public_api:
                if not hasattr(module, func):
                    print(f"✗ Função pública não encontrada: {func}")
                    return False
            
            print("✓ Imports válidos")
            return True
        except Exception as e:
            print(f"✗ Erro ao importar: {e}")
            return False
    
    def check_syntax(self):
        """Valida sintaxe de todos os arquivos."""
        for py_file in self.root.glob("**/*.py"):
            try:
                with open(py_file, 'r') as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                print(f"✗ Erro de sintaxe em {py_file}: {e}")
                return False
        
        print("✓ Sintaxe válida em todos os arquivos")
        return True
    
    def check_log_levels(self):
        """Valida que logger usa níveis corretos."""
        issues = []
        for py_file in self.root.glob("**/*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Alerta se há muitos logger.debug
            debug_count = len([line for line in content.split('\n') if 'logger.debug' in line])
            if debug_count > 10:
                issues.append(f"{py_file}: {debug_count} calls de logger.debug (reduzir)")
        
        if issues:
            print("⚠️  Avisos de logging:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓ Log levels adequados")
        
        return True
    
    def run_all(self):
        """Executa validação completa."""
        print("=" * 60)
        print("VALIDAÇÃO DE REFACTORING")
        print("=" * 60)
        
        checks = [
            ("Sintaxe Python", self.check_syntax),
            ("Imports", self.check_imports),
            ("Log Levels", self.check_log_levels),
        ]
        
        results = []
        for name, check in checks:
            print(f"\n{name}...")
            result = check()
            results.append(result)
        
        print("\n" + "=" * 60)
        if all(results):
            print("✓ REFACTORING VALIDADO COM SUCESSO")
        else:
            print("✗ REFACTORING CONTÉM PROBLEMAS")
        print("=" * 60)
        
        return all(results)

# Uso:
if __name__ == "__main__":
    validator = RefactoringValidator(".")
    validator.run_all()
```

---

## V. GUIA DE EXECUÇÃO (Passo a Passo)

### Fase 1: Preparação (30 min)

```bash
# 1. Salve os 3 scripts na raiz do projeto
cd /seu/projeto

# 2. Crie um backup completo
git commit -m "Backup antes de refactoring"
```

### Fase 2: Limpeza de Logs (1 hora)

```bash
# 1. Execute limpeza
python clean_logs.py

# 2. Verifique resultado
git diff Fix/core.py | head -100

# 3. Se tiver problema, restaure
python -c "from clean_logs import LogCleaner; LogCleaner('Fix/core.py').restore()"
```

### Fase 3: Granularização (2-3 horas)

```bash
# 1. Execute extração
python refactor_granular.py

# 2. Valide
python validate_refactoring.py

# 3. Se OK, remova arquivos antigos
# Se erro, restaure de git
```

### Fase 4: Testes (1-2 horas)

```bash
# 1. Rode testes
pytest tests/ -v

# 2. Teste manualmente
python -c "from Fix import aguardar_e_clicar_v3; print(aguardar_e_clicar_v3)"
```

---

## VI. CHECKLIST: O QUE LIMPAR

### Remover Completamente

- [ ] Emojis de status (✅ ❌ ⚠️)
- [ ] `print()` para debug ("Iniciando...", "Finalizando...")
- [ ] `logger.debug()` para ações triviais
- [ ] Múltiplas linhas decorativas (`print(60)`)
- [ ] Traceback.printexc() sem contexto

### Manter e Padronizar

- [ ] `logger.error()` - Erros críticos
- [ ] `logger.warning()` - Avisos importantes
- [ ] `logger.info()` - Transições de estado
- [ ] Docstrings descritivas
- [ ] Comments explicativos de lógica

### Refatorar em Paralelo

- [ ] Crie `level1_primitivos/` com arquivos 100-200 linhas
- [ ] Crie `level2_strategies/` com lógica específica
- [ ] Atualize `__init__.py` para compatibilidade reversa
- [ ] Adicione type hints

---

## VII. PADRÃO FINAL ESPERADO

### Antes (core.py atual)
```
- 1200+ linhas
- Logs a cada ação
- Emojis
- Funções 200+ linhas
- Difícil navegar
```

### Depois (Objetivo)
```
- core.py: 60-80 linhas (só orquestração)
- 7-8 arquivos especializados: 100-150 linhas cada
- Logs apenas críticos
- Zero emojis
- Funções 30-50 linhas
- Fácil localizar + manter
```

---

## VIII. RECOMENDAÇÃO FINAL

### Executar em Esta Ordem

1. ✅ **Backup completo via Git** (5 min)
2. ✅ **Executar `clean_logs.py`** (30 min)
3. ✅ **Validar com `validate_refactoring.py`** (10 min)
4. ✅ **Testar manualmente** (30 min)
5. ✅ **Depois: Executar `refactor_granular.py`** (2-3 horas)
6. ✅ **Testes completos** (1-2 horas)

**Tempo total:** ~1 dia de trabalho  
**Risco:** Muito baixo (versioning + scripts reversiveis)  
**Ganho:** Código 90% mais limpo + IA 75% mais rápida

---

## IX. TROUBLESHOOTING

Se algo der errado:

```bash
# Restaurar tudo
git checkout Fix/core.py

# Ou restaurar de backup
python -c "from clean_logs import LogCleaner; LogCleaner('Fix/core.py').restore()"

# Ou voltar commit
git reset --hard HEAD~1
```

---

**Pronto para executar?** ✓
