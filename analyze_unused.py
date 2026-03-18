#!/usr/bin/env python3
"""
Análise de Funções Não Utilizadas - Projeto PjePlus
Identifica funções definidas mas nunca importadas/chamadas.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configuração
ROOTS = ["Fix", "SISB", "atos", "Mandado", "PEC", "Prazo"]
IGNORE_DIRS = {"ref", "__pycache__", ".git", "cookies_sessoes", "logs_execucao"}
IGNORE_FUNCTIONS = {"main", "setup", "run", "test_", "exemplo_"}


class FunctionAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.definitions = defaultdict(list)  # {func_name: [(file, line)]}
        self.usages = defaultdict(set)  # {func_name: set(files)}
        self.all_files = []

    def should_ignore_path(self, path: Path) -> bool:
        """Verifica se o caminho deve ser ignorado."""
        parts = path.parts
        return any(ignored in parts for ignored in IGNORE_DIRS)

    def is_private_function(self, name: str) -> bool:
        """Verifica se é função privada."""
        return name.startswith("_") and not name.startswith("__")

    def should_ignore_function(self, name: str) -> bool:
        """Verifica se a função deve ser ignorada."""
        if self.is_private_function(name):
            return True
        if name in IGNORE_FUNCTIONS:
            return True
        for pattern in IGNORE_FUNCTIONS:
            if pattern.endswith("_") and name.startswith(pattern):
                return True
        return False

    def extract_functions_ast(self, filepath: Path) -> List[Tuple[str, int]]:
        """Extrai definições de funções usando AST."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(filepath))
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Ignorar métodos de classes privadas
                    if self.should_ignore_function(node.name):
                        continue
                    functions.append((node.name, node.lineno))

            return functions
        except (SyntaxError, UnicodeDecodeError, Exception) as e:
            print(f"AVISO: Erro ao parsear {filepath}: {e}")
            return []

    def find_usages_in_file(self, filepath: Path, content: str) -> Set[str]:
        """Encontra usos de funções no arquivo."""
        usages = set()

        # Padrão 1: from module import function
        imports = re.finditer(r"from\s+[\w.]+\s+import\s+(.+)", content)
        for match in imports:
            import_list = match.group(1)
            # Remover parênteses e quebras de linha
            import_list = re.sub(r"[()]", "", import_list)
            items = [item.strip().split(" as ")[0] for item in import_list.split(",")]
            usages.update(items)

        # Padrão 2: Chamadas de função function(
        calls = re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
        for match in calls:
            func_name = match.group(1)
            usages.add(func_name)

        # Padrão 3: module.function
        attr_calls = re.finditer(r"\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
        for match in attr_calls:
            func_name = match.group(1)
            usages.add(func_name)

        return usages

    def scan_project(self):
        """Escaneia o projeto completo."""
        print("Escaneando projeto...")

        # Coletar todos os arquivos Python
        for root_dir in ROOTS:
            root_path = self.project_root / root_dir
            if not root_path.exists():
                print(f"AVISO: Diretorio nao encontrado: {root_path}")
                continue

            for py_file in root_path.rglob("*.py"):
                if self.should_ignore_path(py_file):
                    continue
                self.all_files.append(py_file)

        print(f"{len(self.all_files)} arquivos Python encontrados")

        # Fase 1: Extrair todas as definições de funções
        print("\nFase 1: Extraindo definicoes de funcoes...")
        for filepath in self.all_files:
            functions = self.extract_functions_ast(filepath)
            for func_name, line_no in functions:
                rel_path = filepath.relative_to(self.project_root)
                self.definitions[func_name].append((str(rel_path), line_no))

        print(
            f"OK - {sum(len(v) for v in self.definitions.values())} funcoes definidas"
        )

        # Fase 2: Encontrar usos
        print("\nFase 2: Buscando usos de funcoes...")
        for filepath in self.all_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                usages = self.find_usages_in_file(filepath, content)
                rel_path = filepath.relative_to(self.project_root)

                for func_name in usages:
                    if func_name in self.definitions:
                        self.usages[func_name].add(str(rel_path))

            except Exception as e:
                print(f"AVISO: Erro ao ler {filepath}: {e}")

        print(f"OK - Analise de usos concluida")

    def find_unused_functions(self) -> Dict[str, List[Tuple[str, int]]]:
        """Identifica funções sem uso."""
        unused = defaultdict(list)

        for func_name, locations in self.definitions.items():
            # Ignorar se tem múltiplas definições (pode ser sobrecarga/polimorfismo)
            if len(locations) > 3:
                continue

            # Verificar se a função é usada
            used_in = self.usages.get(func_name, set())

            # Considerar não usada se:
            # 1. Não tem usos OU
            # 2. Só é usada no próprio arquivo de definição
            for filepath, line_no in locations:
                if not used_in or used_in == {filepath}:
                    # Verificar se não é em __init__.py (export)
                    if "__init__.py" not in filepath:
                        module = (
                            filepath.split("\\")[0]
                            if "\\" in filepath
                            else filepath.split("/")[0]
                        )
                        unused[module].append((func_name, filepath, line_no))

        return unused

    def generate_report(self):
        """Gera relatório formatado."""
        unused = self.find_unused_functions()

        if not unused:
            print("\nOK - Nenhuma funcao sem uso detectada!")
            return

        print("\n" + "=" * 80)
        print("## Funcoes Sem Uso Detectadas")
        print("=" * 80)

        total = 0
        for module in sorted(unused.keys()):
            functions = sorted(unused[module], key=lambda x: (x[1], x[2]))
            if not functions:
                continue

            print(f"\n### {module}/")
            print(f"Total: {len(functions)} função(ões)")
            print()

            for func_name, filepath, line_no in functions:
                # Tentar identificar motivo
                reason = self._guess_reason(func_name, filepath)
                print(f"- `{func_name}` (linha {line_no}) - {reason}")
                print(f"  Arquivo: {filepath}")
                total += 1

        print("\n" + "=" * 80)
        print(f"TOTAL: {total} funcoes sem uso detectadas")
        print("=" * 80)

    def _guess_reason(self, func_name: str, filepath: str) -> str:
        """Tenta adivinhar o motivo da função não estar em uso."""

        # Verificar duplicações comuns
        if "backup" in filepath.lower():
            return "Arquivo de backup"

        if "test" in filepath.lower() or "exemplo" in filepath.lower():
            return "Arquivo de teste/exemplo"

        # Verificar padrões de nome
        if "legacy" in func_name.lower() or "old" in func_name.lower():
            return "Possivelmente obsoleta (nome sugere)"

        if "helper" in func_name.lower() or "util" in func_name.lower():
            return "Helper/utility nao utilizada"

        if func_name.startswith("get_") or func_name.startswith("set_"):
            return "Getter/Setter nao utilizado"

        if "wrapper" in func_name.lower():
            return "Wrapper nao utilizado"

        # Verificar se há funções similares
        if any(x in func_name for x in ["v2", "v3", "new", "refactor"]):
            return "Possivel versao duplicada/refatorada"

        return "Motivo desconhecido - verificar manualmente"


def main():
    """Função principal."""
    import sys

    # Determinar diretório do projeto
    script_dir = Path(__file__).parent
    project_root = script_dir

    print("=" * 80)
    print("ANALISE DE FUNCOES NAO UTILIZADAS - PjePlus")
    print("=" * 80)
    print(f"Diretorio: {project_root}")
    print(f"Modulos: {', '.join(ROOTS)}")
    print()

    analyzer = FunctionAnalyzer(project_root)
    analyzer.scan_project()
    analyzer.generate_report()

    print("\nOK - Analise concluida!")
    print("\nProximos passos:")
    print("1. Revisar manualmente cada funcao listada")
    print("2. Confirmar se realmente nao esta em uso")
    print("3. Decidir: remover, documentar como obsoleta, ou manter")
    print("4. Verificar se ha testes que dependem dessas funcoes")


if __name__ == "__main__":
    main()
