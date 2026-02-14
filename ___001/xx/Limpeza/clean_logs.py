#!/usr/bin/env python3
"""
clean_logs.py - Remove logs verbosos mantendo críticos.
Reversível: cria backup antes de modificar.

Uso:
    python clean_logs.py Fix/core.py
    python clean_logs.py Fix/  # Processa toda pasta
"""

import re
import shutil
import sys
from pathlib import Path
from datetime import datetime


class LogCleaner:
    """Remove logs triviais, mantém críticos, normaliza para logger (sem quebrar sintaxe)."""
    
    EMOJI_PATTERN = re.compile(r'[✅❌⚠️🔄📊📁🎯💡🚀]')
    PRINT_LINE = re.compile(r'^(?P<indent>\s*)print\((?P<msg>.*)\)\s*$')
    LOGGER_DEBUG_LINE = re.compile(r'^(?P<indent>\s*)logger\.debug\((?P<msg>.*)\)\s*$')
    LOGGER_INFO_LINE = re.compile(r'^(?P<indent>\s*)logger\.info\((?P<msg>.*)\)\s*$')
    LOGGER_WARNING_LINE = re.compile(r'^(?P<indent>\s*)logger\.warning\((?P<msg>.*)\)\s*$')
    LOGGER_ERROR_LINE = re.compile(r'^(?P<indent>\s*)logger\.error\((?P<msg>.*)\)\s*$')
    DECORATIVE_PRINT = re.compile(r'^(?P<indent>\s*)print\(["\']?=+.*\)\s*$')
    
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.backup_path = self.filepath.with_suffix('.py.backup')
        self.stats = {
            'files_processed': 0,
            'lines_removed': 0,
            'lines_total': 0,
            'chars_before': 0,
            'chars_after': 0,
        }
    
    def backup(self):
        """Cria backup do arquivo original."""
        if self.filepath.is_file():
            shutil.copy2(self.filepath, self.backup_path)
            pass
    
    def clean_file(self, filepath):
        """Limpa um arquivo específico sem quebrar blocos de indentação."""
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original = ''.join(lines)
        self.stats['chars_before'] += len(original)
        self.stats['lines_total'] += len(lines)
        
        cleaned_lines = []
        in_triple = False
        triple_delim = None
        
        for line in lines:
            stripped = line.strip()
            
            # Toggle triple-quoted string state (simple heuristic)
            if ('"""' in line or "'''" in line):
                if not in_triple:
                    in_triple = True
                    triple_delim = '"""' if '"""' in line else "'''"
                else:
                    if triple_delim and triple_delim in line:
                        in_triple = False
                        triple_delim = None
                cleaned_lines.append(line)
                continue
            
            if in_triple:
                cleaned_lines.append(line)
                continue
            
            # Remove emojis (safe)
            line_no_emoji = self.EMOJI_PATTERN.sub('', line)
            
            # Replace logger.debug lines with pass (preserve indentation)
            m_debug = self.LOGGER_DEBUG_LINE.match(line_no_emoji)
            if m_debug:
                cleaned_lines.append(f"{m_debug.group('indent')}pass\n")
                continue

            # Replace logger.info lines with pass (keep only critical)
            m_info = self.LOGGER_INFO_LINE.match(line_no_emoji)
            if m_info:
                cleaned_lines.append(f"{m_info.group('indent')}pass\n")
                continue
            
            # Decorative prints -> pass
            if self.DECORATIVE_PRINT.match(line_no_emoji):
                indent = self.DECORATIVE_PRINT.match(line_no_emoji).group('indent')
                cleaned_lines.append(f"{indent}pass\n")
                continue
            
            # Print lines -> logger or pass based on content
            m_print = self.PRINT_LINE.match(line_no_emoji)
            if m_print:
                indent = m_print.group('indent')
                msg = m_print.group('msg')
                lowered = msg.lower()
                if 'erro' in lowered or 'error' in lowered or 'fatal' in lowered:
                    cleaned_lines.append(f"{indent}logger.error({msg})\n")
                elif 'warn' in lowered or 'alerta' in lowered:
                    cleaned_lines.append(f"{indent}logger.warning({msg})\n")
                else:
                    cleaned_lines.append(f"{indent}pass\n")
                continue
            
            cleaned_lines.append(line_no_emoji)
        
        content = ''.join(cleaned_lines)
        
        # Garante logger importado
        if 'import logging' not in content:
            imports = re.search(r'^(.*?(?=\n(?:def |class |if __name__|#)))', content, re.DOTALL)
            if imports:
                content = 'import logging\nlogger = logging.getLogger(__name__)\n\n' + content
        
        self.stats['chars_after'] += len(content)
        self.stats['lines_removed'] += len(original.split('\n')) - len(content.split('\n'))
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    
    def clean(self):
        """Executa limpeza."""
        if self.filepath.is_file():
            # Arquivo único
            self.backup()
            if self.clean_file(self.filepath):
                self.stats['files_processed'] = 1
                pass
                self._print_stats(self.filepath)
                return True
            else:
                pass
                return False
        
        elif self.filepath.is_dir():
            # Pasta - processa recursivamente
            py_files = list(self.filepath.glob('**/*.py'))
            if not py_files:
                pass
                return False
            
            pass
            changed = 0
            
            for py_file in py_files:
                # Backup por arquivo antes de limpar
                backup_path = py_file.with_suffix('.py.backup')
                if not backup_path.exists():
                    shutil.copy2(py_file, backup_path)
                if self.clean_file(py_file):
                    changed += 1
                    pass
            
            self.stats['files_processed'] = changed
            pass
            self._print_stats()
            return changed > 0
    
    def _print_stats(self, filepath=None):
        """Mostra estatísticas de limpeza."""
        if self.stats['chars_before'] == 0:
            return
        
        reduction_pct = ((self.stats['chars_before'] - self.stats['chars_after']) 
                        / self.stats['chars_before'] * 100)
        
        print(f"\n  Estatísticas:")
        print(f"    Arquivos: {self.stats['files_processed']}")
        print(f"    Linhas removidas: {self.stats['lines_removed']}")
        print(f"    Caracteres: {self.stats['chars_before']:,} → {self.stats['chars_after']:,}")
        print(f"    Redução: {reduction_pct:.1f}%")
    
    def restore(self):
        """Restaura de backup."""
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.filepath)
            pass
        else:
            pass


def main():
    if len(sys.argv) < 2:
        pass
        pass
        pass
        pass
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if not target.exists():
        pass
        sys.exit(1)
    
    pass
    pass
    pass
    
    cleaner = LogCleaner(target)
    success = cleaner.clean()
    
    if success:
        pass
        pass
    else:
        pass
    
    pass


if __name__ == "__main__":
    main()
