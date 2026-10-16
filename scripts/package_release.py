# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/package_release.py
"""Package a reviewable source release, excluding runtime state and credentials."""

from pathlib import Path
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile

ROOT: Final = Path(__file__).resolve().parents[1]
DIRECTORIES: Final = (
    "src",
    "tests",
    "examples",
    "scripts",
    "knowledge",
    "migrations",
    "course",
    "evidence",
    ".github",
    "ui",
    "docs/images",
)
FILES: Final = (
    "README.md",
    "LICENSE",
    "COURSE-LICENSE.md",
    "SECURITY.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".chainlit/config.toml",
    "chainlit.md",
    "Makefile",
    "alembic.ini",
    "compose.yaml",
    "Dockerfile",
    "docs/product-requirements.md",
    "docs/resource-feasibility.md",
)


def main() -> None:
    """An explicit inclusion list prevents accidentally exporting a local .env or DB."""
    destination = ROOT / "dist/tcm-agent-course-v1.zip"
    destination.parent.mkdir(exist_ok=True)
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(
            path
            for path in (ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.name != "SHA256SUMS.txt"
            and path.suffix not in {".pyc", ".pyo", ".pdf"}
        )
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            if not path.is_symlink():
                archive.write(path, "tcm-agent-course/" + path.relative_to(ROOT).as_posix())
    print(
        f"Source release: {destination.name}; {len(paths)} files; {destination.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
