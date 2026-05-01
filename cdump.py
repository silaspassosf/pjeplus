"""cdump.py

Gera um dump Markdown de todos os arquivos em um diretório de código.
Uso:
    py cdump.py --src Script/calc/BASE --out cc.md

Se nenhum caminho for informado, o script tenta usar `Script/calc/BASE`.
"""

import argparse
from pathlib import Path


def gerar_dump(src_dir: Path, output_file: Path) -> None:
    if not src_dir.exists() or not src_dir.is_dir():
        raise FileNotFoundError(f"Diretório não encontrado: {src_dir}")

    files = sorted([p for p in src_dir.iterdir() if p.is_file()])
    if not files:
        raise ValueError(f"Nenhum arquivo encontrado em: {src_dir}")

    linhas = [f"# Dump de {src_dir}", ""]
    for arquivo in files:
        linhas.append('---')
        linhas.append(f"## {arquivo.name}")
        linhas.append('')
        try:
            texto = arquivo.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            texto = f"# ERRO ao ler {arquivo}: {e}"
        linhas.extend(texto.splitlines())
        linhas.append('')

    output_file.write_text("\n".join(linhas), encoding='utf-8')
    print(f"✅ Dump salvo em: {output_file}")
    print(f"Arquivos processados: {len(files)}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Gerar dump Markdown de uma pasta de código.')
    parser.add_argument('--src', default='Script/calc/BASE', help='Diretório de origem a ser dumpado.')
    parser.add_argument('--out', default='cc.md', help='Arquivo de saída Markdown.')
    args = parser.parse_args()

    src_dir = Path(args.src)
    output_file = Path(args.out)

    try:
        gerar_dump(src_dir, output_file)
    except Exception as e:
        print(f"ERRO: {e}")
        raise


if __name__ == '__main__':
    main()
