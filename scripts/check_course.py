# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.10,<3"]
# ///
# Run: uv run python scripts/check_course.py
"""Verify document links, code syntax and source synchronization without network access."""

import re
from pathlib import Path
from typing import ClassVar, Final

from build_course import CourseBuildError
from build_course import main as build
from pydantic import BaseModel, ConfigDict, TypeAdapter

ROOT: Final = Path(__file__).resolve().parents[1]


class FigureName(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    name: str


def anchors(text: str) -> set[str]:
    """Resolve explicit IDs and the heading slugs used by these course documents."""
    clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    result = set(re.findall(r'<a id="([^"]+)"', clean))
    for heading in re.findall(r"^#{1,6} (.+)$", clean, re.MULTILINE):
        slug = re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
        result.add(slug)
    return result


def check_document(path: Path) -> None:
    """Validate excerpt syntax and real local targets, including course anchors."""
    original = path.read_text(encoding="utf-8")
    if original.count("```") % 2:
        raise CourseBuildError(f"Unbalanced code fences: {path.name}")
    for code in re.finditer(r"```python\n(.*?)\n```", original, re.DOTALL):
        compile(code.group(1), "course excerpt", "exec")
    text = re.sub(r"```.*?```", "", original, flags=re.DOTALL)
    for link in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        target, _, anchor = link.group(1).partition("#")
        if "://" in target:
            continue
        destination = (path.parent / target) if target else path
        if not destination.exists():
            raise CourseBuildError(f"Missing link: {path.name} -> {target}")
        if (
            anchor
            and destination.suffix == ".md"
            and anchor not in anchors(destination.read_text())
        ):
            raise CourseBuildError(f"Missing anchor: {path.name} -> {link.group(1)}")


def check_learning_structure(text: str) -> None:
    """Every learning node must teach mechanisms before presenting project code."""
    labels = (
        "问题与目标",
        "原理与机制",
        "最小实验",
        "代码详解",
        "项目映射",
        "练习与验收",
        "面试关联",
    )
    for lesson in re.finditer(
        r"^### 第 (\d+) 节：.*?(?=^#{2,3} |\Z)", text, re.MULTILINE | re.DOTALL
    ):
        body = lesson.group()
        if any(f"**{label}。**" not in body for label in labels):
            raise CourseBuildError(f"Lesson {lesson[1]} lacks a teaching section")
        if "uv run" not in body:
            raise CourseBuildError(f"Lesson {lesson[1]} lacks an executable experiment")
        prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        if len(re.findall(r"[\u4e00-\u9fff]", prose)) < 400:
            raise CourseBuildError(f"Lesson {lesson[1]} lacks a substantive explanation")
    for question in re.finditer(
        r"^#### Q(\d+)｜.*?(?=^<a |^### |\Z)", text, re.MULTILINE | re.DOTALL
    ):
        for label in (
            "核心回答",
            "原理解释",
            "项目证据",
            "常见错误",
            "考察要点解析",
            "追问方向与应答",
        ):
            if f"**{label}。**" not in question.group():
                raise CourseBuildError(f"Question {question[1]} lacks {label}")
    mapping = TypeAdapter(dict[str, int]).validate_json(
        (ROOT / "course/question-map.json").read_bytes()
    )
    if set(mapping) != {str(n) for n in range(1, 81)} or set(mapping.values()) != set(range(1, 81)):
        raise CourseBuildError("Interview migration must preserve every question exactly once")


def main() -> None:
    """Fail on missing assets, malformed examples or stale source excerpts."""
    course = ROOT / "course/COURSE.md"
    original = course.read_text(encoding="utf-8")
    reference = ROOT / "course/ENGINEERING_REFERENCE.md"
    original_reference = reference.read_text(encoding="utf-8")
    build()
    if (
        course.read_text(encoding="utf-8") != original
        or reference.read_text(encoding="utf-8") != original_reference
    ):
        raise CourseBuildError("Source snippets changed; review regenerated COURSE.md and rerun")
    check_learning_structure(original)
    for path in (
        course,
        reference,
        ROOT / "README.md",
        ROOT / "course/MIGRATION.md",
        ROOT / "labs/README.md",
        ROOT / "course/STUDY_GUIDE.md",
        ROOT / "course/OPERATIONS_LAB.md",
        ROOT / "course/DEFENSE.md",
        ROOT / "exercises/README.md",
        ROOT / "knowledge/clinical/README.md",
        ROOT / "knowledge/clinical/ATTRIBUTION.md",
        ROOT / "knowledge/clinical/INTEGRATION.md",
        ROOT / "evidence/clinical-knowledge-validation.md",
    ):
        check_document(path)
    figures = TypeAdapter(list[FigureName]).validate_json(
        (ROOT / "course/assets/figures.json").read_bytes()
    )
    expected = {figure.name for figure in figures}
    for extension in ("png", "svg", "mmd"):
        if {path.stem for path in (ROOT / "course/assets").glob(f"*.{extension}")} != expected:
            raise CourseBuildError(f"Figure {extension} files do not match the inventory")
    print(
        f"30 learning nodes, 80 complete interview answers, {len(figures)} figures, teaching structure, source excerpts, syntax and local anchors verified"
    )


if __name__ == "__main__":
    main()
