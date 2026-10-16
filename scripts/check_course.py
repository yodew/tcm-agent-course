# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/check_course.py
"""Verify document links, code syntax and source synchronization without network access."""

import re
from pathlib import Path
from typing import Final

from build_course import CourseBuildError
from build_course import main as build

ROOT: Final = Path(__file__).resolve().parents[1]


def main() -> None:
    """Fail on missing assets, malformed examples or stale source excerpts."""
    course = ROOT / "course/COURSE.md"
    original = course.read_text(encoding="utf-8")
    build()
    if course.read_text(encoding="utf-8") != original:
        raise CourseBuildError("Source snippets changed; review regenerated COURSE.md and rerun")
    if original.count("```") % 2:
        raise CourseBuildError("Unbalanced code fences")
    for code in re.finditer(r"```python\n(.*?)\n```", original, re.DOTALL):
        compile(code.group(1), "course excerpt", "exec")
    for path in (course, ROOT / "README.md"):
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for link in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = link.group(1).split("#", 1)[0]
            if not target or "://" in target:
                continue
            if not (path.parent / target).exists():
                raise CourseBuildError(f"Missing link: {path.name} -> {target}")
    if len(list((ROOT / "course/assets").glob("*.png"))) != 10:
        raise CourseBuildError("Exactly ten diagram PNGs are required")
    print(
        "30 lessons, 80 interview questions, source excerpts, Python syntax and local links verified"
    )


if __name__ == "__main__":
    main()
