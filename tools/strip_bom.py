import sys
from pathlib import Path

def fix_file(p: Path):
    b = p.read_bytes()
    orig = b
    # Detect common BOMs
    if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
        # UTF-16 (LE/BE)
        text = b.decode('utf-16')
        p.write_text(text, encoding='utf-8')
        print('CONVERTED_UTF16->UTF8', p)
        return
    if b.startswith(b"\xef\xbb\xbf"):
        # UTF-8 with BOM
        text = b.decode('utf-8-sig')
        p.write_text(text, encoding='utf-8')
        print('STRIPPED_UTF8_BOM', p)
        return

    # Try reading as utf-8; if text begins with odd characters produced by previous mis-decode, strip them
    try:
        text = b.decode('utf-8')
    except Exception:
        # fallback: try latin-1 then re-encode
        try:
            text = b.decode('latin-1')
            p.write_text(text, encoding='utf-8')
            print('CONVERTED_LATIN1->UTF8', p)
            return
        except Exception as e:
            print('UNREADABLE', p, e)
            return

    changed = False
    if text.startswith('\ufeff'):
        text = text.lstrip('\ufeff')
        changed = True
    if text.startswith('ÿþ'):
        text = text[2:]
        changed = True

    if changed:
        p.write_text(text, encoding='utf-8')
        print('CLEANED_LEADING', p)
    else:
        print('NO_CHANGE', p)


def main():
    paths = sys.argv[1:] or [
        'd:/PjePlus/atos/judicial_bloqueios.py',
        'd:/PjePlus/atos/judicial_wrappers.py',
    ]
    for pp in paths:
        p = Path(pp)
        if not p.exists():
            print('MISSING', p)
            continue
        # backup
        bak = p.with_suffix(p.suffix + '.bak')
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
        fix_file(p)


if __name__ == '__main__':
    main()
