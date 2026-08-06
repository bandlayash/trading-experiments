"""Check every markdown file for things that render wrong on GitHub.

    python tests/check_markdown.py

These are the failure modes that actually bite in practice: a stray `|` silently
splitting a table cell, a relative link or image pointing at a file that is not in the
repo, an unclosed code fence swallowing the rest of the page, and mermaid blocks with
mismatched brackets. All of them look fine in a local editor and break once pushed.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__", ".venv", "data"}

problems: list[str] = []


def report(path: str, line_no: int | None, msg: str) -> None:
    where = f"{os.path.relpath(path, ROOT)}" + (f":{line_no}" if line_no else "")
    problems.append(f"{where}: {msg}")


def check_tables(path: str, lines: list[str], in_fence: list[bool]) -> None:
    """Every row of a table must have the same cell count as its header.

    The usual cause of a mismatch is an unescaped pipe inside a cell -- maths like
    |x|, or a literal `a | b`. GitHub silently drops or shifts the extra cells.
    """
    i = 0
    while i < len(lines):
        if in_fence[i] or not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        # A table needs a header row followed by a |---|---| separator
        if i + 1 >= len(lines) or not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            i += 1
            continue

        expected = lines[i].strip().strip("|").count("|") + 1
        j = i + 2
        while j < len(lines) and lines[j].lstrip().startswith("|") and not in_fence[j]:
            got = lines[j].strip().strip("|").count("|") + 1
            if got != expected:
                report(path, j + 1,
                       f"table row has {got} cells, header has {expected} "
                       f"(unescaped '|' in a cell?)")
            j += 1
        i = j


def check_fences(path: str, lines: list[str]) -> list[bool]:
    """Return a per-line 'inside a fenced code block' mask, and flag unclosed fences."""
    mask, open_fence, opener_line = [], False, 0
    for n, line in enumerate(lines):
        if re.match(r"^\s*```", line):
            if not open_fence:
                open_fence, opener_line = True, n + 1
            else:
                open_fence = False
            mask.append(True)          # the fence line itself is not prose
        else:
            mask.append(open_fence)
    if open_fence:
        report(path, opener_line, "unclosed code fence ``` -- swallows the rest of the page")
    return mask


def check_links(path: str, lines: list[str], in_fence: list[bool], tracked: set[str]) -> None:
    """Relative links and images must point at files that exist in the repo."""
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for n, line in enumerate(lines):
        if in_fence[n]:
            continue
        for target in pattern.findall(line):
            target = target.split(" ")[0].strip()
            if (target.startswith(("http://", "https://", "#", "mailto:"))
                    or target.startswith("../../")):     # GitHub branch/tree shorthand
                continue
            clean = target.split("#")[0]
            if not clean:
                continue
            resolved = os.path.normpath(
                os.path.join(os.path.dirname(path), clean)).replace("\\", "/")
            rel = os.path.relpath(resolved, ROOT).replace("\\", "/")
            if rel not in tracked and not os.path.exists(resolved):
                report(path, n + 1, f"link target not found: {target}")


def check_mermaid(path: str, lines: list[str]) -> None:
    """Mermaid blocks: balanced brackets, and a declared diagram type."""
    n = 0
    while n < len(lines):
        if re.match(r"^\s*```\s*mermaid\s*$", lines[n]):
            start = n
            n += 1
            block: list[str] = []
            while n < len(lines) and not re.match(r"^\s*```", lines[n]):
                block.append(lines[n])
                n += 1
            body = "\n".join(block)
            if not block:
                report(path, start + 1, "empty mermaid block")
            elif not re.match(r"^\s*(flowchart|graph|sequenceDiagram|classDiagram|"
                              r"stateDiagram|erDiagram|journey|gantt|pie|xychart)",
                              block[0].strip()):
                report(path, start + 2,
                       f"mermaid block does not start with a diagram type: {block[0].strip()!r}")
            for open_c, close_c in (("[", "]"), ("(", ")"), ("{", "}")):
                if body.count(open_c) != body.count(close_c):
                    report(path, start + 1,
                           f"mermaid block has unbalanced '{open_c}{close_c}' "
                           f"({body.count(open_c)} vs {body.count(close_c)})")
        n += 1


def main() -> None:
    tracked = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT).replace("\\", "/")
            tracked.add(rel)

    md_files = sorted(f for f in tracked if f.endswith(".md"))
    if not md_files:
        print("No markdown files found.")
        raise SystemExit(1)

    for rel in md_files:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        in_fence = check_fences(path, lines)
        check_tables(path, lines, in_fence)
        check_links(path, lines, in_fence, tracked)
        check_mermaid(path, lines)
        print(f"  checked {rel} ({len(lines)} lines)")

    print()
    if problems:
        print(f"{len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print("Markdown OK — tables balanced, links resolve, fences closed, mermaid parses.")


if __name__ == "__main__":
    main()
