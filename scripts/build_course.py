# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/build_course.py
"""Assemble one complete Markdown and inject exact named source definitions."""

import ast
import re
import textwrap
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
Definition = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


class CourseBuildError(ValueError):
    """Course source data failed its deterministic build contract."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason: str = reason


def definition(source: str, dotted_name: str) -> Definition:
    """Find a class, function or method by syntax rather than fragile line numbers."""
    body = ast.parse(source).body
    found: Definition | None = None
    for name in dotted_name.split("."):
        found = None
        for node in body:
            match node:  # noqa: MATCH_OK
                # ast.stmt is an open hierarchy; unrelated nodes are skipped.
                case ast.ClassDef() | ast.FunctionDef() | ast.AsyncFunctionDef():
                    if node.name == name:
                        found = node
                        body = node.body
                        break
                case _:
                    continue
        if found is None:
            raise CourseBuildError(f"Missing definition {dotted_name}")
    if found is None:
        raise CourseBuildError("Empty definition name")
    return found


def inject(match: re.Match[str]) -> str:
    """Include real source, retaining decorators and a portable relative file link."""
    relative, name = match.group(1), match.group(2)
    source = (ROOT / relative).read_text(encoding="utf-8")
    node = definition(source, name)
    start = min([node.lineno, *(d.lineno for d in node.decorator_list)]) - 1
    if node.end_lineno is None:
        raise CourseBuildError("Parser did not return source range")
    code = textwrap.dedent("\n".join(source.splitlines()[start : node.end_lineno]))
    return f"[完整源码：{name}](../{relative})\n\n```python\n{code}\n```"


def main() -> None:
    """Fail assembly if source references drift or lesson/question inventory changes."""
    parts = sorted((ROOT / "course/authoring").glob("*.md"))
    text = "\n\n".join(path.read_text(encoding="utf-8").strip() for path in parts) + "\n"
    text = re.sub(r"\{\{snippet:([^:}]+):([^}]+)\}\}", inject, text)
    lessons = re.findall(r"^### 第 (\d+) 节", text, re.MULTILINE)
    questions = re.findall(r"^#### Q(\d+)｜", text, re.MULTILINE)
    if [int(n) for n in lessons] != list(range(1, 31)):
        raise CourseBuildError("Course must contain exactly 30 ordered lessons")
    if [int(n) for n in questions] != list(range(1, 81)):
        raise CourseBuildError("Course must contain exactly 80 ordered interview questions")
    if "{{snippet:" in text:
        raise CourseBuildError("Unresolved source snippet")
    (ROOT / "course/COURSE.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
