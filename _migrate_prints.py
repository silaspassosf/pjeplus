"""
Migração automática de print() -> logger.*() para Fix/utils.py, Fix/extracao.py, Fix/core.py.
Regras do xcode/10-padronizacao-logs.md.
"""
import re
import sys

def classify_print(line, context_lines_before, context_lines_after, file_path):
    """Classifica um print() call para determinar o nível de log correto."""
    line_lower = line.lower()

    # Se já usa logger, pular
    if 'logger.' in line or 'logging.' in line:
        return None, None

    # R5: _executar_fluxo / wrappers — não logar
    # Verificar se está dentro de função wrapper
    for ctx in context_lines_before[-5:]:
        if any(w in ctx for w in ['_executar_fluxo', 'def _executar_', 'def executar_fluxo']):
            # Verificar se o print está no except block
            if 'except' in ctx or 'print' in ctx:
                return 'remove', None  # wrapper não loga erro (R5)

    # Detectar erro fatal / todas estratégias falharam
    errors = ['[ERRO]', '[FATAL]', '❌', 'falha', 'todas as', 'todas os',
              'falharam', 'timeout', 'não encontrado', 'nao encontrado',
              'não foi possível', 'nao foi possivel', 'excecao', 'exceção',
              'exception', 'traceback', 'erro critico', 'erro crítico',
              'ERRO em', 'FALHA em', 'Falha ao', 'Falha na',
              'não encontrou', 'nao encontrou', 'não conseguiu', 'nao conseguiu']
    warnings = ['⚠️', '⚠', '[WARN]', '[AVISO]', '[ALERTA]', 'aviso', 'retry',
                'tentativa', 'assumindo', 'fallback', 'pulando', 'continuando',
                'pode não', 'pode nao']
    success_markers = ['✅', '✓', '[OK]', 'sucesso', 'conclu', 'detectado',
                       'clicado com', 'encontrado', 'carregado', 'aberto',
                       'selecionado', 'salvo', 'criado', 'copiado']
    info_markers = ['iniciando', '[FLUXO]', '[COOKIES]', '[LOGIN', '[INDEXAR]',
                    '[PROCESSAR]', '[REINDEXAR]', '[EXTRAI]',
                    '[DRIVER]', '[SELENIUM]', '[LEMBRETE]', '[BLOCO]',
                    'iniciou', 'navegando para', 'aguardando']

    # Se contém marcador de erro
    if any(e.lower() in line_lower for e in errors):
        # Extrair nome da função do contexto
        fn_name = None
        for ctx in reversed(context_lines_before):
            m = re.search(r'def\s+(\w+)', ctx)
            if m:
                fn_name = m.group(1)
                break
        if fn_name:
            return 'error', fn_name
        return 'error', None

    # Se contém marcador de warning
    if any(w.lower() in line_lower for w in warnings):
        return 'warning', None

    # Se contém marcador de sucesso — debug
    if any(s.lower() in line_lower for s in success_markers):
        return 'debug', None

    # Info markers — debug (sucesso silencioso em produção)
    if any(i.lower() in line_lower for i in info_markers):
        return 'debug', None

    # Default: debug
    return 'debug', None


def rewrite_file(filepath):
    """Reescreve um arquivo convertendo print() para logger.*()"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    prints_removed = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Verifica se a linha contém print(
        if re.search(r'\bprint\s*\(', stripped) and not stripped.startswith('#'):
            # Pega contexto (linhas anteriores)
            ctx_before = []
            for j in range(max(0, i-10), i):
                ctx_before.append(lines[j].strip())
            ctx_after = []
            for j in range(i+1, min(len(lines), i+3)):
                ctx_after.append(lines[j].strip())

            level, fn_name = classify_print(line, ctx_before, ctx_after, filepath)

            if level == 'remove':
                # Remover a linha completamente
                prints_removed += 1
                continue
            elif level is not None:
                # Determinar indentação
                indent = re.match(r'^(\s*)', line).group(1)

                # Transformar print() em logger.X()
                # Padrões comuns:
                # print(f"...") -> logger.debug("...")
                # print("[TAG] mensagem") -> logger.debug("[TAG] mensagem")
                # print(f"[TAG] {var}") -> logger.debug("[TAG] %s", var)

                new_line = convert_print_to_logger(line, level, fn_name, indent)
                if new_line:
                    new_lines.append(new_line)
                    prints_removed += 1
                    continue

        new_lines.append(line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return prints_removed


def convert_print_to_logger(line, level, fn_name, indent):
    """Converte uma linha print() para logger.X() call."""
    # Extrair o conteúdo do print
    m = re.search(r'print\s*\((.*)\)\s*$', line)
    if not m:
        # Tenta multi-linha (print começando nesta linha)
        content = line.split('print(', 1)[1] if 'print(' in line else None
        if not content:
            return None
    else:
        content = m.group(1)

    content = content.strip()

    if not content:
        return None

    # Se é f-string, converter para %s format
    if content.startswith('f"') or content.startswith("f'"):
        # Extrai a string f
        string_content = content[1:]  # remove f

        # Tentar manter como f-string para logger (logging suporta % formatting,
        # mas logger.debug aceita f-string diretamente também)
        new_line = f'{indent}logger.{level}({content[2:]}\n' if content.startswith('f"') else f'{indent}logger.{level}({content[2:]}\n'

        # Ajustar: usar %s para interpolação lazy
        # Mas para simplificar, vamos manter como está e só trocar print por logger
        # O Python logging é lazy com % formatting, mas com f-string faz eager eval
        # Para compatibilidade, mantemos o f-string (é aceitável para debug)
        pass

    # Substituir print( por logger.X(
    new_line = re.sub(r'\bprint\s*\(', f'logger.{level}(', line, count=1)

    # Se temos fn_name, adicionar contexto no erro
    if level == 'error' and fn_name:
        # Adiciona "ERRO em <fn>:" se ainda não tiver
        if 'ERRO em' not in line:
            new_line = new_line.replace(
                'logger.error(',
                f'logger.error("ERRO em {fn_name}: " + '
            )

    return new_line


if __name__ == '__main__':
    files = [
        r'd:\PjePlus\Fix\utils.py',
        r'd:\PjePlus\Fix\extracao.py',
        r'd:\PjePlus\Fix\core.py',
    ]

    for fp in files:
        print(f'Processando {fp}...')
        count = rewrite_file(fp)
        print(f'  -> {count} prints convertidos/removidos')
        # Verificar compilação
        import py_compile
        try:
            py_compile.compile(fp, doraise=True)
            print(f'  -> Compilação OK')
        except py_compile.PyCompileError as e:
            print(f'  -> ERRO DE COMPILAÇÃO: {e}')
            sys.exit(1)

    print('\nMigração concluída!')
