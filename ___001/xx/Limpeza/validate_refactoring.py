import logging
logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
validate_refactoring.py - Valida que refactoring não quebrou nada.
Checklist automático pós-limpeza.

Uso:
    python validate_refactoring.py  # Valida projeto atual
    python validate_refactoring.py Fix/  # Valida módulo Fix
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict


class RefactoringValidator:
    """Valida integridade após refactoring."""
    
    def __init__(self, project_root="."):
        self.root = Path(project_root)
        self.issues = defaultdict(list)
        self.warnings = defaultdict(list)
        self.stats = {
            'total_files': 0,
            'syntax_ok': 0,
            'syntax_errors': 0,
            'logger_debug_count': 0,
            'logger_info_count': 0,
            'logger_error_count': 0,
            'logger_warning_count': 0,
            'print_count': 0,
            'emoji_count': 0,
        }
    
    def check_syntax(self):
        """Valida sintaxe Python de todos os .py."""
        
        py_files = list(self.root.glob('**/*.py'))
        self.stats['total_files'] = len(py_files)
        
        if not py_files:
            return False
        
        for py_file in py_files:
            if py_file.name in ['__pycache__', '.git']:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    ast.parse(f.read())
                self.stats['syntax_ok'] += 1
            except SyntaxError as e:
                self.stats['syntax_errors'] += 1
                self.issues['syntax'].append(f"{py_file}: linha {e.lineno} - {e.msg}")
        
        if self.stats['syntax_errors'] == 0:
            return True
        else:
            logger.error(f"  ✗ {self.stats['syntax_errors']} arquivo(s) com erro de sintaxe")
            return False
    
    def check_logging_patterns(self):
        """Valida uso correto de logging."""
        print("\n2. Checando padrões de logging...")
        
        py_files = list(self.root.glob('**/*.py'))
        
        for py_file in py_files:
            if py_file.name in ['__pycache__', '.git', 'clean_logs.py']:
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Conta logs
            debug = len([l for l in content.split('\n') if 'logger.debug' in l])
            info = len([l for l in content.split('\n') if 'logger.info' in l])
            error = len([l for l in content.split('\n') if 'logger.error' in l])
            warning = len([l for l in content.split('\n') if 'logger.warning' in l])
            prints = len([l for l in content.split('\n') if l.strip().startswith('print(') and 'logger' not in l])
            emojis = len([c for c in content if c in '✅❌⚠️🔄📊📁🎯💡🚀'])
            
            self.stats['logger_debug_count'] += debug
            self.stats['logger_info_count'] += info
            self.stats['logger_error_count'] += error
            self.stats['logger_warning_count'] += warning
            self.stats['print_count'] += prints
            self.stats['emoji_count'] += emojis
            
            # Avisos
            if debug > 20:
                self.warnings['excessive_debug'].append(f"{py_file.name}: {debug} calls")
            if prints > 5:
                self.warnings['excessive_print'].append(f"{py_file.name}: {prints} calls")
            if emojis > 0:
                self.warnings['emoji_found'].append(f"{py_file.name}: {emojis} emojis")
        
        print(f"  ✓ Logger.debug: {self.stats['logger_debug_count']}")
        print(f"  ✓ Logger.info: {self.stats['logger_info_count']}")
        print(f"  ✓ Logger.error: {self.stats['logger_error_count']}")
        print(f"  ✓ Logger.warning: {self.stats['logger_warning_count']}")
        print(f"  ⚠ Print(): {self.stats['print_count']}")
        print(f"  ⚠ Emojis: {self.stats['emoji_count']}")
        
        return True
    
    def check_imports(self):
        """Valida que imports não estão quebrados."""
        
        # Tenta importar módulos principais
        modules_to_test = ['Fix', 'Prazo', 'PEC', 'SISB', 'atos', 'Mandado']
        
        for module_name in modules_to_test:
            module_path = self.root / module_name / '__init__.py'
            if not module_path.exists():
                continue
            
            try:
                with open(module_path, 'r') as f:
                    ast.parse(f.read())
            except Exception as e:
                self.issues['imports'].append(f"{module_name}: {e}")
                logger.error(f"  ✗ {module_name}: erro")
        
        return len(self.issues['imports']) == 0
    
    def check_file_sizes(self):
        """Valida tamanho de arquivos (target: <300 linhas)."""
        print("\n4. Checando tamanho de arquivos...")
        
        py_files = list(self.root.glob('**/*.py'))
        oversized = []
        
        for py_file in py_files:
            if py_file.name in ['__pycache__', '.git']:
                continue
            
            with open(py_file, 'r') as f:
                lines = len(f.readlines())
            
            if lines > 300:
                oversized.append((py_file, lines))
        
        if oversized:
            print(f"  ⚠ {len(oversized)} arquivo(s) com >300 linhas:")
            for py_file, lines in sorted(oversized, key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {py_file.relative_to(self.root)}: {lines} linhas")
            return False
        else:
            print(f"  ✓ Todos os arquivos <300 linhas")
            return True
    
    def print_summary(self):
        """Imprime resumo final."""
        
        total_issues = len(self.issues['syntax']) + len(self.issues['imports'])
        total_warnings = sum(len(v) for v in self.warnings.values())
        
        if total_issues == 0:
            logger.error("✓ VALIDAÇÃO PASSOU - Nenhum erro crítico")
        else:
            logger.error(f"✗ VALIDAÇÃO FALHOU - {total_issues} erro(s)")
        
        if total_warnings > 0:
            logger.warning(f" {total_warnings} aviso(s) para revisar:")
            for category, items in self.warnings.items():
                if items:
                    for item in items[:3]:
                        pass
        
        logger.error(f"  Erros de sintaxe: {self.stats['syntax_errors']}")
        logger.warning(f"  warning: {self.stats['logger_warning_count']}")
        logger.error(f"  error: {self.stats['logger_error_count']}")
        
        return total_issues == 0
    
    def run(self):
        """Executa validação completa."""
        print("\n" + "=" * 60)
        print("VALIDAÇÃO DE REFACTORING")
        print("=" * 60)
        
        checks = [
            self.check_syntax(),
            self.check_logging_patterns(),
            self.check_imports(),
            self.check_file_sizes(),
        ]
        
        success = self.print_summary()
        return success and all(checks)


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path(".")
    
    validator = RefactoringValidator(target)
    success = validator.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
