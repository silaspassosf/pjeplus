from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PASS_LINE_RE = re.compile(r"^pass(\s+#.*)?$")
IF_HEADER_RE = re.compile(r"^(if|elif)\b.*:\s*(#.*)?$")
ELSE_HEADER_RE = re.compile(r"^else:\s*(#.*)?$")


def _leading_ws(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _is_blank_or_comment(line: str) -> bool:
    stripped = line.strip()
    return stripped == "" or stripped.startswith("#")


def _find_prev_same_indent(lines: list[str], start: int, indent: str) -> bool:
    i = start - 1
    while i >= 0:
        if _is_blank_or_comment(lines[i]):
            i -= 1
            continue
        current_indent = _leading_ws(lines[i])
        if len(current_indent) < len(indent):
            return False
        if current_indent == indent:
            return True
        i -= 1
    return False


def _find_next_same_indent(lines: list[str], start: int, indent: str) -> bool:
    i = start + 1
    total = len(lines)
    while i < total:
        if _is_blank_or_comment(lines[i]):
            i += 1
            continue
        current_indent = _leading_ws(lines[i])
        if len(current_indent) < len(indent):
            return False
        if current_indent == indent:
            return True
        i += 1
    return False


def _is_noop_block(lines: list[str], header_index: int, indent: str) -> bool:
    i = header_index + 1
    total = len(lines)
    found_statement = False
    while i < total:
        if _is_blank_or_comment(lines[i]):
            i += 1
            continue
        current_indent = _leading_ws(lines[i])
        if len(current_indent) <= len(indent):
            break
        if current_indent == indent + " " or current_indent == indent + "\t":
            pass
        stripped = lines[i].strip()
        if PASS_LINE_RE.match(stripped):
            found_statement = True
        else:
            return False
        i += 1
    return found_statement


def _next_same_indent_header(lines: list[str], start: int, indent: str) -> str | None:
    i = start + 1
    total = len(lines)
    while i < total:
        if _is_blank_or_comment(lines[i]):
            i += 1
            continue
        current_indent = _leading_ws(lines[i])
        if len(current_indent) < len(indent):
            return None
        if current_indent == indent:
            return lines[i].strip()
        i += 1
    return None


def remove_redundant_passes(lines: list[str]) -> tuple[list[str], int]:
    removed_indices: set[int] = set()
    total = len(lines)

    for i in range(total):
        stripped = lines[i].strip()
        if not PASS_LINE_RE.match(stripped):
            continue

        indent = _leading_ws(lines[i])
        if _find_prev_same_indent(lines, i, indent) or _find_next_same_indent(lines, i, indent):
            removed_indices.add(i)

    new_lines = [line for idx, line in enumerate(lines) if idx not in removed_indices]
    return new_lines, len(removed_indices)


def remove_noop_if_blocks(lines: list[str]) -> tuple[list[str], int]:
    removed_indices: set[int] = set()
    total = len(lines)
    i = 0
    while i < total:
        stripped = lines[i].strip()
        indent = _leading_ws(lines[i])

        if IF_HEADER_RE.match(stripped):
            header_type = stripped.split()[0]
            if header_type == "elif":
                i += 1
                continue
            if _is_noop_block(lines, i, indent):
                next_header = _next_same_indent_header(lines, i, indent)
                if next_header and (next_header.startswith("elif") or next_header.startswith("else")):
                    i += 1
                    continue
                removed_indices.add(i)
                j = i + 1
                while j < total:
                    if _is_blank_or_comment(lines[j]):
                        removed_indices.add(j)
                        j += 1
                        continue
                    current_indent = _leading_ws(lines[j])
                    if len(current_indent) <= len(indent):
                        break
                    removed_indices.add(j)
                    j += 1
        elif ELSE_HEADER_RE.match(stripped):
            if _is_noop_block(lines, i, indent):
                removed_indices.add(i)
                j = i + 1
                while j < total:
                    if _is_blank_or_comment(lines[j]):
                        removed_indices.add(j)
                        j += 1
                        continue
                    current_indent = _leading_ws(lines[j])
                    if len(current_indent) <= len(indent):
                        break
                    removed_indices.add(j)
                    j += 1
        i += 1

    new_lines = [line for idx, line in enumerate(lines) if idx not in removed_indices]
    return new_lines, len(removed_indices)


def should_skip(path: Path, include_backups: bool) -> bool:
    if "__pycache__" in path.parts:
        return True
    if not include_backups and "backup" in path.name.lower():
        return True
    return False


def process_file(path: Path, write: bool, backup_suffix: str | None) -> int:
    original_text = path.read_text(encoding="utf-8")
    lines = original_text.splitlines(keepends=True)
    new_lines, removed_pass = remove_redundant_passes(lines)
    new_lines, removed_noop = remove_noop_if_blocks(new_lines)
    removed = removed_pass + removed_noop

    if removed and write:
        if backup_suffix:
            backup_path = path.with_name(path.name + backup_suffix)
            shutil.copy2(path, backup_path)
        path.write_text("".join(new_lines), encoding="utf-8")

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove redundant 'pass' statements.")
    parser.add_argument(
        "--root",
        default="xx/SISB",
        help="Root folder to scan (default: xx/SISB).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes to files (default: dry-run).",
    )
    parser.add_argument(
        "--backup-suffix",
        default=None,
        help="Optional backup suffix (e.g., .bak) before writing.",
    )
    parser.add_argument(
        "--include-backups",
        action="store_true",
        help="Include files with 'backup' in the name.",
    )

    args = parser.parse_args()
    root = Path(args.root)

    if not root.exists():
        raise SystemExit(f"Root not found: {root}")

    changed_files: list[tuple[Path, int]] = []
    if root.is_file():
        if not should_skip(root, args.include_backups) and root.suffix == ".py":
            removed = process_file(root, args.write, args.backup_suffix)
            if removed:
                changed_files.append((root, removed))
    else:
        for path in root.rglob("*.py"):
            if should_skip(path, args.include_backups):
                continue
            removed = process_file(path, args.write, args.backup_suffix)
            if removed:
                changed_files.append((path, removed))

    if changed_files:
        print("CHANGED_FILES:")
        for path, removed in changed_files:
            print(f"- {path} (removed: {removed})")
    else:
        print("CHANGED_FILES: none")


if __name__ == "__main__":
    main()