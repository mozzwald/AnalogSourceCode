#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


IGNORE_LOC_FILES = {
    "Fill Er Up.asm",
    "Fill Er Up II.asm",
}

RENAME_MAPS = {
    "Avalanche.asm": {
        "OPT": "OPTFLG",
        "ADD": "ADDVAL",
    },
    "Bonk.asm": {
        "SET": "SETLP",
        "ADD": "ADDPTS",
    },
}


def split_comment(line: str) -> tuple[str, str]:
    in_single = False
    in_double = False

    for index, char in enumerate(line):
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        elif char == ";" and not in_single and not in_double:
            return line[:index], line[index:]

    return line, ""


def convert_char_literals(code: str) -> str:
    return re.sub(
        r"'([^'\s])(?=(?:\s|$|,|\)|\]|\+|\-|\*|/|&|\^))",
        r"'\1'",
        code,
    )


def rename_symbols(code: str, source_name: str) -> str:
    mapping = RENAME_MAPS.get(source_name, {})
    for old, new in mapping.items():
        code = re.sub(
            rf"(?<![A-Za-z0-9_?.]){re.escape(old)}(?![A-Za-z0-9_?.])",
            new,
            code,
        )
    return code


def transform_source(source_name: str, source_text: str) -> str:
    out_lines: list[str] = []
    block_stack: list[str] = []
    pending_org: str | None = None
    pending_org_comment = ""
    ignore_loc = source_name in IGNORE_LOC_FILES

    for raw_line in source_text.splitlines():
        line = re.sub(r"^\d{4}\s+", "", raw_line.rstrip("\n"))
        code, comment = split_comment(line)

        code = convert_char_literals(code)
        code = rename_symbols(code, source_name)
        code = re.sub(r":([A-Za-z][A-Za-z0-9_]*)", r"__\1", code)
        code = re.sub(
            r"([#(]\s*[<>])\s*([A-Za-z_?.][A-Za-z0-9_?.]*)([+-]\d+)",
            r"\1[\2\3]",
            code,
        )
        stripped = code.strip()

        if pending_org is not None and stripped and not stripped.startswith(";"):
            match = re.match(r"^(\s*)LOC\b\s*(.+?)\s*$", code, re.IGNORECASE)
            if match and not ignore_loc:
                indent, expr = match.groups()
                out_lines.append(
                    f"{indent}org {pending_org},{expr}{pending_org_comment or comment}"
                )
                pending_org = None
                pending_org_comment = ""
                continue

            out_lines.append(f"org {pending_org}{pending_org_comment}")
            pending_org = None
            pending_org_comment = ""

        if not stripped:
            out_lines.append(line)
            continue

        if (
            re.match(r"^\.(OPT|ENABLE|NLIST|TITLE|SBTTL)\b", stripped, re.IGNORECASE)
            or re.match(r"^LIST\b", stripped, re.IGNORECASE)
            or re.match(r"^TITLE\s+['\"]", stripped, re.IGNORECASE)
        ):
            out_lines.append(";" + code + comment)
            continue

        match = re.match(r"^(\s*)(\S+)\s+MACRO\b(.*)$", code, re.IGNORECASE)
        if match:
            indent, label, args = match.groups()
            out_lines.append(f"{indent}{label} .macro{args}{comment}")
            block_stack.append("macro")
            continue

        if re.match(r"^\s*ENDM\b", code, re.IGNORECASE):
            if block_stack and block_stack[-1] == "macro":
                block_stack.pop()
            out_lines.append(re.sub(r"ENDM", ".endm", code, flags=re.IGNORECASE) + comment)
            continue

        match = re.match(r"^(\s*)(\S+)\s+PROC\b(.*)$", code, re.IGNORECASE)
        if match:
            indent, label, args = match.groups()
            out_lines.append(f"{indent}{label} .proc{args}{comment}")
            block_stack.append("proc")
            continue

        match = re.match(r"^(\s*)PROC\b(.*)$", code, re.IGNORECASE)
        if match:
            indent, args = match.groups()
            out_lines.append(f"{indent}.local{args}{comment}")
            block_stack.append("local")
            continue

        if re.match(r"^\s*EPROC\b", code, re.IGNORECASE):
            block_type = block_stack.pop() if block_stack else "proc"
            end_directive = ".endl" if block_type == "local" else ".endp"
            out_lines.append(
                re.sub(r"EPROC", end_directive, code, flags=re.IGNORECASE) + comment
            )
            continue

        if re.match(r"^\s*\.INCLUDE\b", code, re.IGNORECASE) or re.match(
            r"^\s*INCLUDE\b", code, re.IGNORECASE
        ):
            out_lines.append(";" + code + comment)
            continue

        match = re.match(r"^(\s*)ORG\b\s*(.+?)\s*$", code, re.IGNORECASE)
        if match:
            _, expr = match.groups()
            pending_org = expr
            pending_org_comment = comment
            continue

        match = re.match(r"^(\s*)\.org\b\s*(.+?)\s*$", code, re.IGNORECASE)
        if match:
            indent, expr = match.groups()
            out_lines.append(f"{indent}org {expr}{comment}")
            continue

        match = re.match(r"^(\s*)\.\s*=\s*(.+?)\s*$", code)
        if match:
            indent, expr = match.groups()
            out_lines.append(f"{indent}org {expr}{comment}")
            continue

        match = re.match(r"^(\s*)(\S+)\s+\.\=\s*(.+?)\s*$", code)
        if match:
            indent, label, expr = match.groups()
            out_lines.append(f"{indent}{label} = {expr}{comment}")
            continue

        match = re.match(r"^(\s*)(\S+)?\s*\*=\s*(.+?)\s*$", code)
        if match:
            indent, label, expr = match.groups()
            expr_no_space = expr.replace(" ", "")
            if label:
                if expr_no_space.startswith("*+"):
                    out_lines.append(
                        f"{indent}{label} .ds {expr_no_space[2:]}{comment}"
                    )
                else:
                    out_lines.append(f"{indent}{label} = {expr}{comment}")
            else:
                out_lines.append(f"{indent}org {expr}{comment}")
            continue

        match = re.match(
            r"^(\s*)(\S+)\s+(?:DS|\.DS)\b\s*(.+?)\s*$", code, re.IGNORECASE
        )
        if match:
            indent, label, args = match.groups()
            parts = args.split(None, 1)
            if len(parts) == 2 and not parts[1].startswith((";", '"', "'")):
                args = f"{parts[0]} ; {parts[1]}"
            out_lines.append(f"{indent}{label} .ds {args}{comment}")
            continue

        match = re.match(r"^(\s*)(\S+)?\s*\.SBYTE\b(.*)$", code, re.IGNORECASE)
        if match:
            indent, label, args = match.groups()
            label_prefix = f"{label} " if label else ""
            out_lines.append(f"{indent}{label_prefix}.SB{args}{comment}")
            continue

        match = re.match(r"^(\s*)(\S+)?\s+DB\b\s*(.*)$", code, re.IGNORECASE)
        if match:
            indent, label, args = match.groups()
            label_prefix = f"{label} " if label else ""
            out_lines.append(f"{indent}{label_prefix}.BYTE {args}{comment}")
            continue

        match = re.match(r"^(\s*)(\S+)?\s+DW\b\s*(.*)$", code, re.IGNORECASE)
        if match:
            indent, label, args = match.groups()
            label_prefix = f"{label} " if label else ""
            out_lines.append(f"{indent}{label_prefix}.WORD {args}{comment}")
            continue

        match = re.match(r"^(\s*)LOC\b\s*(.+?)\s*$", code, re.IGNORECASE)
        if match:
            if ignore_loc:
                out_lines.append(";" + line)
            else:
                indent, expr = match.groups()
                out_lines.append(f"{indent}; LOC {expr}{comment}")
            continue

        match = re.match(r"^(\s*)END\b\s+(\S+)\s*$", code, re.IGNORECASE)
        if match:
            indent, expr = match.groups()
            while block_stack:
                block_type = block_stack.pop()
                out_lines.append(".endl" if block_type == "local" else ".endp")
            out_lines.append(f"{indent}run {expr}{comment}")
            continue

        if re.match(r"^\s*\.END\b", code, re.IGNORECASE) or re.match(
            r"^\s*END\b\s*$", code, re.IGNORECASE
        ):
            if block_stack:
                block_type = block_stack.pop()
                out_lines.append(".endl" if block_type == "local" else ".endp")
            else:
                out_lines.append(";" + code + comment)
            continue

        code = re.sub(r"\b(ASL|LSR|ROL|ROR)\s+A\b", r"\1 @", code, flags=re.IGNORECASE)
        out_lines.append(code + comment)

    if pending_org is not None:
        out_lines.append(f"org {pending_org}{pending_org_comment}")

    return "\n".join(out_lines) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: madsify.py <input.asm> <output.asm>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_text = transform_source(input_path.name, input_path.read_text(errors="ignore"))
    output_path.write_text(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
