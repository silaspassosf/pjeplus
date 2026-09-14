#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comprimir_pdf.py - Compressor de PDF para PJe v5.0
===================================================
Estrategia: rasterizacao direta por pagina (rapido, eficaz para qualquer PDF).

Uso:
    py comprimir_pdf.py arquivo.pdf
    py comprimir_pdf.py -- "Processo - 1234.pdf"
    py comprimir_pdf.py arquivo.pdf --max-mb 9.5 --out ./saida

Requisitos: pip install pymupdf pillow
"""

import sys, os, argparse, time, shutil
from pathlib import Path
from io import BytesIO

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

try:
    import pymupdf as fitz
except ImportError:
    import fitz

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

DEFAULT_MAX_MB    = 9.5
DEFAULT_MAX_BYTES = int(DEFAULT_MAX_MB * 1024 * 1024)

# DPI e qualidade por nivel (do melhor ao mais comprimido)
NIVEIS = [
    (150, 82),
    (130, 72),
    (110, 62),
     (96, 52),
     (80, 42),
]


# ──────────────────────────────────────────────
def _mb(n): return f"{n/1024/1024:.2f} MB"
def _sep(): print("=" * 60, flush=True)

def _pr_pag(i, total, t0, label=""):
    pct = (i / total) * 100
    el  = time.time() - t0
    pps = i / el if el > 0.1 else 0
    eta = int((total - i) / pps) if pps > 0 else 0
    bar_w = 35
    filled = int(bar_w * pct / 100)
    bar = "#" * filled + "-" * (bar_w - filled)
    linha = f"\r[{bar}] {pct:5.1f}%  pag {i}/{total}  {pps:.1f}pag/s  ETA:{eta}s  {label}"
    print(linha.ljust(90), end="", flush=True)


# ──────────────────────────────────────────────
# Rasterizacao por pagina
# ──────────────────────────────────────────────
def _rasterizar(src_path: Path, dpi: int, quality: int) -> bytes:
    src   = fitz.open(str(src_path))
    out   = fitz.open()
    total = len(src)
    mat   = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    t0    = time.time()

    for i, page in enumerate(src):
        _pr_pag(i + 1, total, t0)
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        rect = page.rect

        if HAS_PILLOW:
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, stream=buf.getvalue())
        else:
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, pixmap=pix)
        pix = None

    print()  # quebra de linha
    result = out.tobytes(garbage=4, deflate=True)
    src.close()
    out.close()
    return result


# ──────────────────────────────────────────────
# Split em partes
# ──────────────────────────────────────────────
def _split(src_bytes: bytes, max_bytes: int, base: str, out_dir: Path) -> list:
    doc   = fitz.open(stream=src_bytes, filetype="pdf")
    total = len(doc)
    parts = []
    idx, num = 0, 1

    print(f"\nDividindo {total} paginas em partes de ate {_mb(max_bytes)}...")

    while idx < total:
        lo, hi, best_b, best_n = 1, total - idx, None, 0
        while lo <= hi:
            mid   = (lo + hi) // 2
            chunk = fitz.open()
            chunk.insert_pdf(doc, from_page=idx, to_page=idx + mid - 1)
            b = chunk.tobytes(garbage=4, deflate=True)
            chunk.close()
            if len(b) <= max_bytes:
                best_b, best_n, lo = b, mid, mid + 1
            else:
                hi = mid - 1

        if best_b is None:
            chunk = fitz.open()
            chunk.insert_pdf(doc, from_page=idx, to_page=idx)
            best_b, best_n = chunk.tobytes(garbage=4, deflate=True), 1
            chunk.close()

        fname = out_dir / f"{base}_parte{str(num).zfill(2)}.pdf"
        fname.write_bytes(best_b)
        print(f"  Parte {num}: {_mb(len(best_b))} ({best_n} pags) -> {fname.name}")
        parts.append(fname)
        idx += best_n
        num += 1

    doc.close()
    return parts


# ──────────────────────────────────────────────
# Principal
# ──────────────────────────────────────────────
def comprimir(src_path: Path, max_bytes: int, out_dir: Path) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    orig  = src_path.stat().st_size
    base  = src_path.stem
    t0    = time.time()

    _sep()
    print(f"Arquivo : {src_path.name}")
    print(f"Tamanho : {_mb(orig)}")
    print(f"Limite  : {_mb(max_bytes)}")
    _sep()

    if orig <= max_bytes:
        print("Ja dentro do limite. Copiando...")
        out = out_dir / f"{base}_ok.pdf"
        shutil.copy2(src_path, out)
        return [out]

    best_bytes, best_label = None, None

    for dpi, quality in NIVEIS:
        label = f"{dpi}dpi Q{quality}"
        print(f"\nNivel: {label}")
        try:
            rb = _rasterizar(src_path, dpi, quality)
        except Exception as e:
            print(f"  ERRO: {e}")
            continue

        ratio   = (1 - len(rb) / orig) * 100
        elapsed = time.time() - t0
        sign    = "-" if ratio > 0 else "+"
        print(f"  Resultado: {_mb(len(rb))} ({sign}{abs(ratio):.1f}%) em {elapsed:.0f}s")

        best_bytes, best_label = rb, label

        if len(rb) <= max_bytes:
            print(f"  OK! Dentro do limite.")
            break
        else:
            print(f"  Ainda acima do limite. Tentando nivel mais agressivo...")

    if best_bytes is None:
        print("FALHA: nenhum nivel funcionou.")
        return []

    elapsed = time.time() - t0

    if len(best_bytes) <= max_bytes:
        out_path = out_dir / f"{base}_comprimido.pdf"
        out_path.write_bytes(best_bytes)
        ratio = (1 - len(best_bytes) / orig) * 100
        _sep()
        print(f"PRONTO em {elapsed:.0f}s")
        print(f"  {_mb(orig)} -> {_mb(len(best_bytes))} ({'-' if ratio>0 else '+'}{abs(ratio):.1f}%)")
        print(f"  Nivel: {best_label}")
        print(f"  Saida: {out_path}")
        return [out_path]

    # Ainda grande: divide
    print(f"\nAinda {_mb(len(best_bytes))} — dividindo em partes...")
    parts = _split(best_bytes, max_bytes, base, out_dir)
    _sep()
    print(f"PRONTO em {elapsed:.0f}s | {len(parts)} parte(s)")
    for p in parts:
        sz = p.stat().st_size if p.exists() else 0
        print(f"  {p.name}  ({_mb(sz)})")
    return parts


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Compressor PDF PJe v5.0")
    p.add_argument("input",    help="PDF ou pasta")
    p.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB)
    p.add_argument("--out",    default=None)
    p.add_argument("--overwrite", action="store_true")

    args, extras = p.parse_known_args()
    inp = (args.input + " " + " ".join(extras)).strip() if extras else args.input
    src = Path(inp)

    print(f"\nPJeTools - Compressor PDF v5.0 (PyMuPDF {fitz.version[0]})")
    print(f"Pillow: {'OK' if HAS_PILLOW else 'AUSENTE (pip install pillow)'}")

    if not src.exists():
        print(f"\nERRO: nao encontrado: {src}")
        sys.exit(1)

    max_bytes = int(args.max_mb * 1024 * 1024)
    pdfs = sorted(src.glob("*.pdf")) if src.is_dir() else [src]

    resultados = []
    for pdf in pdfs:
        od  = Path(args.out) if args.out else pdf.parent
        res = comprimir(pdf, max_bytes, od)
        if args.overwrite and len(res) == 1 and res[0].exists():
            shutil.copy2(res[0], pdf)
            res[0].unlink()
            print(f"  Substituiu: {pdf.name}")
        resultados.extend(res)

    print(f"\nTotal: {len(resultados)} arquivo(s) gerado(s)")

if __name__ == "__main__":
    main()
